// DEC-942: the localStorage envelope must carry deck + sim + metrics only.
// The four large per-deck artifacts (candidates, spellbook-combos,
// synergy-candidates, tier-b-loops) are 11.7M chars fleet-wide against a ~5.2M
// browser quota — caching them starved the user's owned-cards map (DEC-941).

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createCardCache } from '../../data/cardCache';
import { createDeckLoader } from '../../data/loader';
import { createScryfallLimiter } from '../../data/scryfallLimiter';
import type { RawCardMetadata } from '../../data/types';
import { cardJson, fakeScryfall, MemoryStorage } from './scryfallFakes';

const INDEX = { commanders: [{ id: 'alpha', name: 'Alpha', theme: 'T', colors: ['G'] }] };
const PRICES_AS_OF = '2026-10-13T21:56:40+00:00';

function payloadFor(url: string): unknown {
  if (url.endsWith('/index.json')) return INDEX;
  if (url.endsWith('/card-metadata.json')) return { 'Sol Ring': { mana_cost: '{1}' } };
  if (url.endsWith('/card-metadata.meta.json')) return { prices_as_of: PRICES_AS_OF };
  if (url.endsWith('/deck.json')) return { id: 'alpha', name: 'Alpha', decklist: [] };
  if (url.endsWith('/simulation.json')) return { deck_id: 'alpha' };
  if (url.endsWith('/metrics.json')) return { deck_id: 'alpha' };
  if (url.endsWith('/candidates.json')) return { candidates: ['BIG'] };
  if (url.endsWith('/spellbook-combos.json')) return { included: ['BIG'] };
  if (url.endsWith('/synergy-candidates.json')) return { groups: ['BIG'] };
  if (url.endsWith('/tier-b-loops.json')) return { engines: ['BIG'] };
  throw new Error('unexpected url ' + url);
}

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

let fetchImpl: ReturnType<typeof vi.fn>;
let storage: Storage;

beforeEach(() => {
  storage = memStorage();
  fetchImpl = vi.fn(async (url: string) => ({
    ok: true,
    status: 200,
    json: async () => payloadFor(url),
  }));
});

function loader() {
  return createDeckLoader({ fetchImpl: fetchImpl as unknown as typeof fetch, storage });
}

function deckEnvelope(): Record<string, unknown> {
  const key = [...Array(storage.length).keys()]
    .map((i) => storage.key(i)!)
    .find((k) => k.includes('deck:alpha'));
  expect(key, 'deck envelope was written').toBeTruthy();
  return JSON.parse(storage.getItem(key!)!).payload;
}

describe('deck loader persisted envelope (DEC-942)', () => {
  it('returns a complete bundle but persists only deck + sim + metrics', async () => {
    const bundle = await loader().loadDeck('alpha');

    // Callers still see every artifact.
    expect(bundle?.candidates).toEqual({ candidates: ['BIG'] });
    expect(bundle?.spellbookCombos).toEqual({ included: ['BIG'] });
    expect(bundle?.synergyCandidates).toEqual({ groups: ['BIG'] });
    expect(bundle?.tierBLoops).toEqual({ engines: ['BIG'] });
    expect(bundle?.cardMetadata).toBeTruthy();

    // Storage does not.
    const persisted = deckEnvelope();
    expect(Object.keys(persisted).sort()).toEqual(['deck', 'id', 'index', 'metrics', 'sim']);
    expect(JSON.stringify(persisted)).not.toContain('BIG');
  });

  it('re-fetches the stripped artifacts when a bundle hydrates from storage', async () => {
    await loader().loadDeck('alpha');
    fetchImpl.mockClear();

    // Fresh loader, same storage — simulates a returning user.
    const bundle = await loader().loadDeck('alpha');
    expect(bundle?.tierBLoops).toEqual({ engines: ['BIG'] });
    expect(bundle?.synergyCandidates).toEqual({ groups: ['BIG'] });

    const fetched = fetchImpl.mock.calls.map((c) => String(c[0]));
    expect(fetched.some((u) => u.endsWith('/candidates.json'))).toBe(true);
    expect(fetched.some((u) => u.endsWith('/spellbook-combos.json'))).toBe(true);
    // deck/sim/metrics came from the cache.
    expect(fetched.some((u) => u.endsWith('/deck.json'))).toBe(false);
    expect(fetched.some((u) => u.endsWith('/simulation.json'))).toBe(false);
    expect(fetched.some((u) => u.endsWith('/metrics.json'))).toBe(false);
  });

  it('reclaims envelopes from an earlier STORAGE_PREFIX on first write', async () => {
    // A prefix bump alone orphans the old keys; the fat v143 envelope would
    // otherwise sit there forever and re-create the DEC-941 quota wall.
    storage.setItem('gv1-deck-data-v143:deck:alpha', 'STALE'.repeat(100));
    storage.setItem('gv1-deck-data-v1:card-metadata', 'STALE');
    storage.setItem('gv1-card:sol ring', 'KEEP');
    storage.setItem('grimoire-owned-cards', 'KEEP');

    await loader().loadDeck('alpha');

    expect(storage.getItem('gv1-deck-data-v143:deck:alpha')).toBeNull();
    expect(storage.getItem('gv1-deck-data-v1:card-metadata')).toBeNull();
    // Only this loader's own family is swept.
    expect(storage.getItem('gv1-card:sol ring')).toBe('KEEP');
    expect(storage.getItem('grimoire-owned-cards')).toBe('KEEP');
    expect(deckEnvelope().deck).toBeTruthy();
  });

  it('survives a storage that refuses writes', async () => {
    storage = {
      ...memStorage(),
      setItem: () => {
        throw new DOMException('quota', 'QuotaExceededError');
      },
    } as unknown as Storage;
    const bundle = await loader().loadDeck('alpha');
    expect(bundle?.deck).toBeTruthy();
    expect(bundle?.candidates).toEqual({ candidates: ['BIG'] });
  });
});

// DEC-1102: every deck bundle waits for card-metadata.json, and the loader seeds
// the card cache with it before the bundle resolves. A page takes its card
// names from a bundle, so it cannot ask the cache for a name of the file first.
describe('deck loader seeds the card cache (DEC-1102)', () => {
  it('seeds before the first bundle resolves, from the network and from storage', async () => {
    for (const round of ['network', 'storage']) {
      let resolved = false;
      const seeds: Array<{ metadata: unknown; beforeBundle: boolean; pricesAsOf?: string | null }> = [];
      const seed = (metadata: unknown, pricesAsOf?: string | null) =>
        seeds.push({ metadata, beforeBundle: !resolved, pricesAsOf });
      const deckLoader = createDeckLoader({
        fetchImpl: fetchImpl as unknown as typeof fetch,
        storage,
        cardCache: { seed },
      });
      const bundle = await deckLoader.loadDeck('alpha').then((b) => {
        resolved = true;
        return b;
      });
      // DEC-1131: the seed carries the date of the file's prices from the meta file.
      expect(seeds, round).toEqual([
        { metadata: { 'Sol Ring': { mana_cost: '{1}' } }, beforeBundle: true, pricesAsOf: PRICES_AS_OF },
      ]);
      expect(bundle?.cardMetadata).toBe(seeds[0].metadata);
      await deckLoader.loadAll();
      expect(seeds, `${round}: one seed per loader`).toHaveLength(1);
    }
    // The second round read the persisted copy, not the network.
    const metadataFetches = fetchImpl.mock.calls.filter(([url]) => String(url).endsWith('/card-metadata.json'));
    expect(metadataFetches).toHaveLength(1);
  });

  // DEC-1131 N6: a failed or empty file is not kept, and the next load asks again.
  for (const [label, answer] of [
    ['a 404', { ok: false, status: 404, json: async () => ({}) }],
    ['an empty file', { ok: true, status: 200, json: async () => ({}) }],
  ] as const) {
    it(`persists no card-metadata.json after ${label}, and the next load asks again`, async () => {
      fetchImpl.mockImplementation(async (url: string) =>
        url.endsWith('/card-metadata.json') ? answer : { ok: true, status: 200, json: async () => payloadFor(url) },
      );
      const seed = vi.fn();
      const deckLoader = createDeckLoader({ fetchImpl: fetchImpl as unknown as typeof fetch, storage, cardCache: { seed } });
      expect(await deckLoader.loadCardMetadata()).toEqual({});
      const keys = [...Array(storage.length).keys()].map((i) => storage.key(i)!);
      expect(keys.filter((k) => k.endsWith(':card-metadata'))).toEqual([]);
      expect(seed).not.toHaveBeenCalled();

      fetchImpl.mockImplementation(async (url: string) => ({ ok: true, status: 200, json: async () => payloadFor(url) }));
      expect(await deckLoader.loadCardMetadata()).toEqual({ 'Sol Ring': { mana_cost: '{1}' } });
      const fetches = fetchImpl.mock.calls.filter(([url]) => String(url).endsWith('/card-metadata.json'));
      expect(fetches).toHaveLength(2);
      expect(seed).toHaveBeenCalledTimes(1);
    });
  }

  it('takes an empty card-metadata.json that an earlier version stored for no file', async () => {
    // The loader writes its own envelope; the case empties it, as PR #38 left it after a 404.
    await loader().loadCardMetadata();
    const key = [...Array(storage.length).keys()].map((i) => storage.key(i)!).find((k) => k.endsWith(':card-metadata'))!;
    storage.setItem(key, JSON.stringify({ fetchedAt: Date.now(), payload: {} }));
    expect(await loader().loadCardMetadata()).toEqual({ 'Sol Ring': { mana_cost: '{1}' } });
    expect(fetchImpl.mock.calls.filter(([url]) => String(url).endsWith('/card-metadata.json'))).toHaveLength(2);
  });

  it('writes its envelopes under v159', async () => {
    await loader().loadDeck('alpha');
    const keys = [...Array(storage.length).keys()].map((i) => storage.key(i)!);
    expect(keys.filter((k) => k.startsWith('gv1-deck-data-')).every((k) => k.startsWith('gv1-deck-data-v159:'))).toBe(true);
  });
});

// DEC-1153 (N4 of DEC-1149): the loader fetches the meta file only with
// card-metadata.json, and stores the file with the date of its prices in one
// envelope. A load from storage takes the date from there and sends no request.
describe('a stored card-metadata.json keeps its own date (DEC-1153)', () => {
  const requests = (suffix: string) => fetchImpl.mock.calls.filter(([url]) => String(url).endsWith(suffix)).length;
  const envelopeKey = () =>
    [...Array(storage.length).keys()].map((i) => storage.key(i)!).find((k) => k.endsWith(':card-metadata'));

  it('a cold load sends 1 meta request and stores the date; a load from storage sends none and seeds that date', async () => {
    const seed = vi.fn();
    const cold = createDeckLoader({ fetchImpl: fetchImpl as unknown as typeof fetch, storage, cardCache: { seed } });
    await cold.loadCardMetadata();
    expect(await cold.loadCardMetadataMeta()).toEqual({ prices_as_of: PRICES_AS_OF });
    expect([requests('/card-metadata.json'), requests('/card-metadata.meta.json')]).toEqual([1, 1]);
    expect(JSON.parse(storage.getItem(envelopeKey()!)!)).toMatchObject({ pricesAsOf: PRICES_AS_OF });

    // A reload: a new loader on the same storage.
    const reloaded = createDeckLoader({ fetchImpl: fetchImpl as unknown as typeof fetch, storage, cardCache: { seed } });
    expect(await reloaded.loadCardMetadataMeta()).toEqual({ prices_as_of: PRICES_AS_OF });
    await reloaded.loadDeck('alpha');
    expect([requests('/card-metadata.json'), requests('/card-metadata.meta.json')]).toEqual([1, 1]);
    expect(seed.mock.calls).toEqual([
      [{ 'Sol Ring': { mana_cost: '{1}' } }, PRICES_AS_OF],
      [{ 'Sol Ring': { mana_cost: '{1}' } }, PRICES_AS_OF],
    ]);
  });

  for (const [label, envelope] of [
    ['an envelope from before DEC-1153 (no date)', { payload: { 'Sol Ring': { mana_cost: '{1}' } } }],
    ['an envelope with a date and an empty file', { pricesAsOf: PRICES_AS_OF, payload: {} }],
    ['an envelope with a date and no file', { pricesAsOf: PRICES_AS_OF, payload: null }],
  ] as const) {
    it(`takes ${label} for none: it fetches the file and the meta file, and stores both`, async () => {
      await loader().loadCardMetadata();
      storage.setItem(envelopeKey()!, JSON.stringify({ fetchedAt: Date.now(), ...envelope }));
      const seed = vi.fn();
      const reloaded = createDeckLoader({ fetchImpl: fetchImpl as unknown as typeof fetch, storage, cardCache: { seed } });
      expect(await reloaded.loadCardMetadata()).toEqual({ 'Sol Ring': { mana_cost: '{1}' } });
      expect([requests('/card-metadata.json'), requests('/card-metadata.meta.json')]).toEqual([2, 2]);
      expect(seed).toHaveBeenCalledWith({ 'Sol Ring': { mana_cost: '{1}' } }, PRICES_AS_OF);
      expect(JSON.parse(storage.getItem(envelopeKey()!)!)).toMatchObject({
        pricesAsOf: PRICES_AS_OF,
        payload: { 'Sol Ring': { mana_cost: '{1}' } },
      });
    });
  }

  for (const [label, answer] of [
    ['a 404', { ok: false, status: 404, json: async () => ({}) }],
    ['a 500', { ok: false, status: 500, json: async () => ({}) }],
    ['no date', { ok: true, status: 200, json: async () => ({ count: 1 }) }],
  ] as const) {
    it(`keeps the file without a date in memory after ${label} for the meta file, stores nothing, and the next load asks for both`, async () => {
      fetchImpl.mockImplementation(async (url: string) =>
        url.endsWith('/card-metadata.meta.json') ? answer : { ok: true, status: 200, json: async () => payloadFor(url) },
      );
      const seed = vi.fn();
      const first = createDeckLoader({ fetchImpl: fetchImpl as unknown as typeof fetch, storage, cardCache: { seed } });
      expect(await first.loadCardMetadata()).toEqual({ 'Sol Ring': { mana_cost: '{1}' } });
      expect(seed).toHaveBeenCalledWith({ 'Sol Ring': { mana_cost: '{1}' } }, undefined);
      expect(await first.loadCardMetadataMeta()).toEqual(label === 'no date' ? { count: 1 } : null);
      expect(envelopeKey()).toBeUndefined();

      fetchImpl.mockImplementation(async (url: string) => ({ ok: true, status: 200, json: async () => payloadFor(url) }));
      const second = createDeckLoader({ fetchImpl: fetchImpl as unknown as typeof fetch, storage, cardCache: { seed } });
      await second.loadCardMetadata();
      expect([requests('/card-metadata.json'), requests('/card-metadata.meta.json')]).toEqual([2, 2]);
      expect(seed).toHaveBeenLastCalledWith({ 'Sol Ring': { mana_cost: '{1}' } }, PRICES_AS_OF);
    });
  }

  it('gives no meta when card-metadata.json fails, and the date of the next file after a reset', async () => {
    fetchImpl.mockImplementation(async (url: string) => {
      if (url.endsWith('/card-metadata.json')) throw new TypeError('Failed to fetch');
      return { ok: true, status: 200, json: async () => payloadFor(url) };
    });
    const deckLoader = loader();
    expect(await deckLoader.loadCardMetadataMeta()).toBeNull();

    // A file that loads, then a reset and a file that is missing: no date stays from before.
    fetchImpl.mockImplementation(async (url: string) => ({ ok: true, status: 200, json: async () => payloadFor(url) }));
    expect(await deckLoader.loadCardMetadataMeta()).toEqual({ prices_as_of: PRICES_AS_OF });
    deckLoader._reset();
    storage.clear();
    fetchImpl.mockImplementation(async (url: string) =>
      url.endsWith('/card-metadata.json') ? { ok: false, status: 404, json: async () => ({}) } : { ok: true, status: 200, json: async () => payloadFor(url) },
    );
    expect(await deckLoader.loadCardMetadataMeta()).toBeNull();
  });
});

// P2 of DEC-1149, the reviewer's case: a deploy changes card-metadata.json and
// its meta file inside the hour of a stored file. Before DEC-1153 the stored
// file's old prices took the new date, won over a stored refresh younger than
// 24 h, and asked nothing until the stored file's hour ended.
describe('P2: a deploy inside the hour of a stored card-metadata.json (DEC-1153)', () => {
  const T0 = Date.UTC(2026, 9, 14, 12, 0, 0);
  const HOUR_MS = 3_600_000;
  const SOL_RING = {
    cmc: 1,
    colors: [],
    image: 'front/8/e/8ee443cc-e17a-493b-9c93-1f9e141a30e4.jpg?1789644446',
    mana_cost: '{1}',
    type_line: 'Artifact',
    usd: 1.42,
    eur: 1.06,
  };
  const OLD_FILE: RawCardMetadata = { 'Sol Ring': SOL_RING };
  const NEW_FILE: RawCardMetadata = { 'Sol Ring': { ...SOL_RING, usd: 3 } };
  const OLD_DATE = new Date(T0 - 30 * HOUR_MS).toISOString();
  const NEW_DATE = new Date(T0 - 25 * 60_000).toISOString();

  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it("the stored file keeps its own date: the stored refresh wins and asks nothing; the new file comes when the hour ends", async () => {
    const cardStorage = new MemoryStorage();
    let deployed = false;
    fetchImpl.mockImplementation(async (url: string) => {
      const body = url.endsWith('/card-metadata.meta.json')
        ? { prices_as_of: deployed ? NEW_DATE : OLD_DATE }
        : url.endsWith('/card-metadata.json')
          ? deployed ? NEW_FILE : OLD_FILE
          : payloadFor(url);
      return { ok: true, status: 200, json: async () => body };
    });
    const scry = fakeScryfall({ card: (name) => ({ ...cardJson(name), prices: { usd: '2.50' } }) });
    const visit = () => {
      const cache = createCardCache({
        storage: cardStorage,
        limiter: createScryfallLimiter({ fetchImpl: scry.fetch, storage: cardStorage, locks: null }),
      });
      const deckLoader = createDeckLoader({ fetchImpl: fetchImpl as unknown as typeof fetch, storage, cardCache: cache });
      return { cache, deckLoader };
    };
    const requests = (suffix: string) => fetchImpl.mock.calls.filter(([url]) => String(url).endsWith(suffix)).length;

    // Visit 1, 40 min before T0: the old file and its meta; the cache refreshes Sol Ring.
    vi.setSystemTime(T0 - 40 * 60_000);
    const first = visit();
    await first.deckLoader.loadCardMetadata();
    expect(first.cache.get('Sol Ring')).toMatchObject({ price: '$1.42', priceAsOf: Date.parse(OLD_DATE) });
    first.cache.refreshPrice('Sol Ring');
    await vi.advanceTimersByTimeAsync(0);
    expect(first.cache.get('Sol Ring')).toMatchObject({ price: '$2.50', priceAsOf: T0 - 40 * 60_000 });

    // The deploy, then visit 2 at T0: the stored file is 40 min old.
    deployed = true;
    vi.setSystemTime(T0);
    const second = visit();
    await second.deckLoader.loadCardMetadata();
    expect([requests('/card-metadata.json'), requests('/card-metadata.meta.json')]).toEqual([1, 1]);
    expect(await second.deckLoader.loadCardMetadataMeta()).toEqual({ prices_as_of: OLD_DATE });
    // The stored file's prices are 30 h old, so the refresh of 40 min ago shows.
    expect(second.cache.get('Sol Ring')).toMatchObject({ price: '$2.50', priceAsOf: T0 - 40 * 60_000 });
    second.cache.refreshPrice('Sol Ring');
    await vi.advanceTimersByTimeAsync(10_000);
    expect(scry.sends).toHaveLength(1);

    // An hour after visit 1 the stored file goes, and the new file comes with its own date.
    vi.setSystemTime(T0 + 21 * 60_000);
    const third = visit();
    await third.deckLoader.loadCardMetadata();
    expect([requests('/card-metadata.json'), requests('/card-metadata.meta.json')]).toEqual([2, 2]);
    expect(third.cache.get('Sol Ring')).toMatchObject({ price: '$3.00', priceAsOf: Date.parse(NEW_DATE) });
  });
});
