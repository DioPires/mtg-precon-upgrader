// DEC-1170 kill cases for PR #70 (DEC-1153): the card-metadata envelope of the loader.
// 2b: a dated envelope older than 1 h: both files come, and the envelope is written again with the new date.
// 2d: a stored pricesAsOf that is not a readable date (a number, null, "", "not a date") counts as none.
// K1: a meta file whose prices_as_of is a string that Date.parse cannot read ("", "not a date"):
//     the loader keeps the file in memory, stores nothing, and the next load asks again (B1).
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createDeckLoader } from '../../data/loader';

const OLD_DATE = '2026-10-13T21:56:40+00:00';
const NEW_DATE = '2026-10-14T21:56:40+00:00';
const FILE = { 'Sol Ring': { mana_cost: '{1}' } };
const HOUR_MS = 3_600_000;

function memStorage(): Storage {
  const map = new Map<string, string>();
  return {
    get length() {
      return map.size;
    },
    key: (i: number) => [...map.keys()][i] ?? null,
    getItem: (k: string) => map.get(k) ?? null,
    setItem: (k: string, v: string) => void map.set(k, v),
    removeItem: (k: string) => void map.delete(k),
    clear: () => map.clear(),
  } as unknown as Storage;
}

let storage: Storage;
let date: unknown;
let fetchImpl: ReturnType<typeof vi.fn>;
let clock: number;

beforeEach(() => {
  storage = memStorage();
  date = OLD_DATE;
  clock = Date.UTC(2026, 9, 15, 12, 0, 0);
  fetchImpl = vi.fn(async (url: string) => {
    const body = url.endsWith('/card-metadata.meta.json') ? { prices_as_of: date } : url.endsWith('/card-metadata.json') ? FILE : {};
    return { ok: true, status: 200, json: async () => body };
  });
});

const requests = (suffix: string) => fetchImpl.mock.calls.filter(([url]) => String(url).endsWith(suffix)).length;
const counts = () => [requests('/card-metadata.json'), requests('/card-metadata.meta.json')];
const envelopeKey = () => [...Array(storage.length).keys()].map((i) => storage.key(i)!).find((k) => k.endsWith(':card-metadata'));
const envelope = () => JSON.parse(storage.getItem(envelopeKey()!)!);
function visit(seed = vi.fn()) {
  const deckLoader = createDeckLoader({ fetchImpl: fetchImpl as unknown as typeof fetch, storage, cardCache: { seed }, now: () => clock });
  return { deckLoader, seed };
}

describe('DEC-1170 2b: a dated envelope older than 1 h', () => {
  it('fetches both files, writes the envelope again with the new date and the new time, and the next load inside 1 h sends nothing', async () => {
    const t1 = clock;
    await visit().deckLoader.loadCardMetadata();
    expect(counts()).toEqual([1, 1]);
    expect(envelope()).toMatchObject({ fetchedAt: t1, pricesAsOf: OLD_DATE });

    date = NEW_DATE;
    clock = t1 + HOUR_MS + 1;
    const second = visit();
    await second.deckLoader.loadCardMetadata();
    expect(counts()).toEqual([2, 2]);
    expect(second.seed).toHaveBeenCalledWith(FILE, NEW_DATE);
    expect(envelope()).toMatchObject({ fetchedAt: t1 + HOUR_MS + 1, pricesAsOf: NEW_DATE, payload: FILE });

    clock = t1 + HOUR_MS + 30 * 60_000;
    const third = visit();
    expect(await third.deckLoader.loadCardMetadataMeta()).toEqual({ prices_as_of: NEW_DATE });
    expect(counts()).toEqual([2, 2]);
    expect(third.seed).toHaveBeenCalledWith(FILE, NEW_DATE);
  });
});

describe('DEC-1170 2d: a stored pricesAsOf that is not a readable date', () => {
  for (const [label, stored] of [
    ['a number', Date.parse(OLD_DATE)],
    ['null', null],
    ['an object', { prices_as_of: OLD_DATE }],
    ['an empty string', ''],
    ['a string that is not a date', 'not a date'],
  ] as const) {
    it(`counts ${label} as no date: both files come, the seed has the meta file's date, and the envelope is written again`, async () => {
      await visit().deckLoader.loadCardMetadata();
      storage.setItem(envelopeKey()!, JSON.stringify({ fetchedAt: clock, payload: FILE, pricesAsOf: stored }));
      date = NEW_DATE;
      const second = visit();
      expect(await second.deckLoader.loadCardMetadataMeta()).toEqual({ prices_as_of: NEW_DATE });
      expect(counts()).toEqual([2, 2]);
      expect(second.seed.mock.calls).toEqual([[FILE, NEW_DATE]]);
      expect(envelope()).toMatchObject({ pricesAsOf: NEW_DATE });
    });
  }
});

describe('DEC-1170 K1: a meta file whose prices_as_of is not a readable date', () => {
  for (const value of ['', 'not a date'] as const) {
    it(`keeps the file dated ${JSON.stringify(value)} in memory, stores nothing, and a load inside 1 h asks again`, async () => {
      date = value;
      const first = visit();
      await first.deckLoader.loadCardMetadata();
      expect(first.seed).toHaveBeenCalledWith(FILE, value);
      expect(counts()).toEqual([1, 1]);
      expect(envelopeKey()).toBeUndefined();

      clock += 30 * 60_000;
      const second = visit();
      expect(await second.deckLoader.loadCardMetadataMeta()).toEqual({ prices_as_of: value });
      expect(counts()).toEqual([2, 2]);
      expect(second.seed.mock.calls).toEqual([[FILE, value]]);
      expect(envelopeKey()).toBeUndefined();
    });
  }
});

// K2: the kill case of the mutant U-D11 (DEC-1170): a card-metadata.json that
// answers 500, or a fetch of it that rejects, rejects the load. The pages show
// their error; the loader keeps and stores nothing, and seeds nothing.
describe('DEC-1170 K2: a failed card-metadata.json', () => {
  for (const [label, answer] of [
    ['a 500', async () => ({ ok: false, status: 500, json: async () => ({}) })],
    ['a fetch that rejects', async () => {
      throw new TypeError('Failed to fetch');
    }],
  ] as const) {
    it(`rejects loadCardMetadata() after ${label}, seeds nothing and stores nothing; the next load asks again`, async () => {
      fetchImpl.mockImplementation(async (url: string) =>
        url.endsWith('/card-metadata.json') ? answer() : { ok: true, status: 200, json: async () => ({ prices_as_of: OLD_DATE }) },
      );
      const first = visit();
      await expect(first.deckLoader.loadCardMetadata()).rejects.toThrow();
      expect(first.seed).not.toHaveBeenCalled();
      expect(envelopeKey()).toBeUndefined();
      expect(await first.deckLoader.loadCardMetadataMeta()).toBeNull();
      expect(requests('/card-metadata.json')).toBe(2);
    });
  }
});

// K3: the kill case of the mutants H5 and H6 (DEC-1153 fix round 1): a date
// that Date.parse reads as 0 or less is still a readable date, as in
// cardCache.seed(). The loader stores the file with it.
describe('DEC-1153 K3: a meta file whose prices_as_of is a readable date at or before 1970-01-01', () => {
  for (const value of ['1970-01-01T00:00:00Z', '1969-12-31T00:00:00Z'] as const) {
    it(`stores the file dated ${value}, and a load inside 1 h reads it and sends nothing`, async () => {
      date = value;
      const first = visit();
      await first.deckLoader.loadCardMetadata();
      expect(first.seed).toHaveBeenCalledWith(FILE, value);
      expect(counts()).toEqual([1, 1]);
      expect(envelope()).toMatchObject({ pricesAsOf: value, payload: FILE });

      clock += 30 * 60_000;
      const second = visit();
      expect(await second.deckLoader.loadCardMetadataMeta()).toEqual({ prices_as_of: value });
      expect(counts()).toEqual([1, 1]);
      expect(second.seed.mock.calls).toEqual([[FILE, value]]);
    });
  }
});
