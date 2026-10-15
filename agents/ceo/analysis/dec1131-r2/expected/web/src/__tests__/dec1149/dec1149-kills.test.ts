// DEC-1149 kill cases (reviewer of PR #54) for the mutants that survive the
// pull request's suites. Each passes on the head and fails on its mutant.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createCardCache } from '../../data/cardCache';
import { createScryfallLimiter, STOP_KEY } from '../../data/scryfallLimiter';
import type { RawCardMetadata } from '../../data/types';
import { cardJson, fakeLocks, fakeScryfall, MemoryStorage, type Outcome } from '../data/scryfallFakes';

const T0 = Date.UTC(2026, 9, 14, 12, 0, 0);
const HOUR_MS = 3_600_000;
const OLD = new Date(T0 - 25 * HOUR_MS).toISOString();

const FILE: RawCardMetadata = {
  'Sol Ring': {
    cmc: 1,
    colors: [],
    image: 'front/8/e/8ee443cc-e17a-493b-9c93-1f9e141a30e4.jpg?1789644446',
    mana_cost: '{1}',
    type_line: 'Artifact',
    usd: 1.42,
    eur: 1.06,
  },
};

let storage: MemoryStorage;
beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(T0);
  storage = new MemoryStorage();
});
afterEach(() => {
  vi.useRealTimers();
});
const advance = (ms: number) => vi.advanceTimersByTimeAsync(ms);
const priced = (usd: string) => (name: string) => ({ ...cardJson(name), prices: { usd } });

function tab(scry: ReturnType<typeof fakeScryfall>, locks: LockManager | null = null) {
  return createCardCache({ storage, limiter: createScryfallLimiter({ fetchImpl: scry.fetch, storage, locks }) });
}

describe.each([0, 150])('reviewer kills, answers after %i ms', (delay) => {
  it('R1, R2: a refresh that waited for the lock takes the price that the other tab stored, and sends nothing', async () => {
    const locks = fakeLocks();
    const scryA = fakeScryfall({ delayMs: delay, card: priced('2.50') });
    const scryB = fakeScryfall({ delayMs: delay, card: priced('9.99') });
    const a = tab(scryA, locks);
    const b = tab(scryB, locks);
    a.seed(FILE, OLD);
    b.seed(FILE, OLD);
    a.refreshPrice('Sol Ring');
    b.refreshPrice('Sol Ring');
    await advance(10_000);
    expect(scryA.batches()).toEqual([['Sol Ring']]);
    expect(scryB.sends).toHaveLength(0);
    expect(b.get('Sol Ring')).toMatchObject({ price: '$2.50', priceAsOf: T0 + delay });
    expect(b.pricePending('Sol Ring')).toBe(false);
  });

  it('R3: a stored refresh with the same date as the file loses to the file', () => {
    const at = Date.parse(OLD);
    storage.setItem('gv1-card:sol ring', JSON.stringify({ fetchedAt: T0, priceCheckedAt: T0, price: '$9.99', priceAsOf: at }));
    const cache = tab(fakeScryfall());
    cache.seed(FILE, OLD);
    expect(cache.get('Sol Ring')).toMatchObject({ price: '$1.42', priceAsOf: at });
  });

  it('R4: a picture that fails after a price refresh keeps the refreshed price, in memory and in storage', async () => {
    const scry = fakeScryfall({ delayMs: delay, card: priced('2.50') });
    const cache = tab(scry);
    cache.seed(FILE, OLD);
    cache.refreshPrice('Sol Ring');
    await advance(delay);
    expect(cache.get('Sol Ring')?.price).toBe('$2.50');
    await advance(5_000);
    cache.imageFailed('Sol Ring');
    expect(cache.get('Sol Ring')?.price).toBe('$2.50');
    expect(JSON.parse(storage.getItem('gv1-card:sol ring')!)).toMatchObject({ price: '$2.50', priceCheckedAt: T0 + delay });
    await advance(5_000);
    // A reload: the price stays, and nobody asks for it again.
    const reloaded = tab(fakeScryfall({ card: priced('7.00') }));
    reloaded.seed(FILE, OLD);
    expect(reloaded.get('Sol Ring')?.price).toBe('$2.50');
  });

  it('R5: a price refresh after a picture refresh keeps the new pictures, in memory and in storage', async () => {
    const scry = fakeScryfall({ delayMs: delay, card: priced('2.50') });
    const cache = tab(scry);
    cache.seed(FILE, OLD);
    cache.imageFailed('Sol Ring');
    await advance(delay);
    const looked = cardJson('Sol Ring').image_uris;
    expect(cache.get('Sol Ring')?.image_normal).toBe(looked.normal);
    await advance(5_000);
    cache.refreshPrice('Sol Ring');
    await advance(delay);
    expect(scry.sends).toHaveLength(2);
    expect(cache.get('Sol Ring')).toMatchObject({ price: '$2.50', image_normal: looked.normal });
    const reloaded = tab(fakeScryfall());
    reloaded.seed(FILE, OLD);
    expect(reloaded.get('Sol Ring')).toMatchObject({ price: '$2.50', image_normal: looked.normal });
  });

  it('R7: a name whose front face is already in a full batch goes in that batch', async () => {
    const giant = {
      ...cardJson('Bonecrusher Giant // Stomp'),
      card_faces: [
        { name: 'Bonecrusher Giant', mana_cost: '{2}{R}', type_line: 'Creature — Giant' },
        { name: 'Stomp', mana_cost: '{1}{R}', type_line: 'Instant — Adventure' },
      ],
    };
    const scry = fakeScryfall({ delayMs: delay, card: (name) => (name === 'Bonecrusher Giant' ? giant : cardJson(name)) });
    const cache = tab(scry);
    const looks = Array.from({ length: 75 }, (_, i) => `Look ${i + 1}`);
    cache.enqueue('Bonecrusher Giant // Stomp');
    looks.forEach((name) => cache.enqueue(name));
    cache.enqueue('Bonecrusher Giant');
    await advance(delay);
    expect(scry.batches()[0]).toEqual(['Bonecrusher Giant', ...looks.slice(0, 74)]);
    expect(cache.get('Bonecrusher Giant')).toMatchObject({ status: 'loaded', name: 'Bonecrusher Giant // Stomp' });
    await advance(1_200 + delay);
    expect(scry.batches()).toEqual([['Bonecrusher Giant', ...looks.slice(0, 74)], ['Look 75']]);
  });
});

describe('S11: the limiter, with two requests waiting in bucket 1', () => {
  it('the request that met the stop goes first when the stop ends', async () => {
    const outcome = (n: number): Outcome => (n === 1 ? 429 : 200);
    const scry = fakeScryfall({ outcome });
    const limiter = createScryfallLimiter({ fetchImpl: scry.fetch, storage, locks: null });
    const first = limiter.fetch('https://api.scryfall.com/cards/named?exact=One');
    const second = limiter.fetch('https://api.scryfall.com/cards/named?exact=Two');
    await advance(0);
    expect(storage.getItem(STOP_KEY)).not.toBeNull();
    await advance(30_000);
    await advance(1_200);
    expect(scry.sends.map((s) => s.url)).toEqual([
      'https://api.scryfall.com/cards/named?exact=One',
      'https://api.scryfall.com/cards/named?exact=One',
      'https://api.scryfall.com/cards/named?exact=Two',
    ]);
    expect((await first).status).toBe(200);
    expect((await second).status).toBe(200);
  });
});

describe('R13: a stop record that PR #38 stored (no number)', () => {
  it('is stop 0: the request that goes after it and meets a 429 doubles it', async () => {
    storage.setItem(STOP_KEY, JSON.stringify({ until: T0 + 10_000, ms: 30_000 }));
    const scry = fakeScryfall({ outcome: () => 429 });
    const limiter = createScryfallLimiter({ fetchImpl: scry.fetch, storage, locks: null });
    void limiter.fetch('https://api.scryfall.com/cards/named?exact=One').catch(() => undefined);
    await advance(10_000);
    expect(scry.sends).toHaveLength(1);
    expect(JSON.parse(storage.getItem(STOP_KEY)!)).toMatchObject({ until: T0 + 10_000 + 60_000, ms: 60_000 });
    // Nothing goes in the doubled stop.
    await advance(60_000 - 1);
    expect(scry.sends).toHaveLength(1);
  });
});

describe('R15: a stored card-metadata.json keeps its own hour', () => {
  it('a load that reads the stored file does not write it again, so the file comes again an hour after it was fetched', async () => {
    const { createDeckLoader } = await import('../../data/loader');
    const fetchImpl = vi.fn(async (url: string) => {
      const body = url.endsWith('/card-metadata.meta.json') ? { prices_as_of: OLD } : url.endsWith('/card-metadata.json') ? FILE : {};
      return { ok: true, status: 200, json: async () => body } as Response;
    });
    const loaderStorage = new MemoryStorage();
    const load = () => createDeckLoader({ fetchImpl: fetchImpl as unknown as typeof fetch, storage: loaderStorage }).loadCardMetadata();
    const fileFetches = () => fetchImpl.mock.calls.filter(([url]) => String(url).endsWith('/card-metadata.json')).length;
    await load();
    expect(fileFetches()).toBe(1);
    vi.setSystemTime(T0 + 30 * 60_000);
    await load();
    expect(fileFetches()).toBe(1);
    vi.setSystemTime(T0 + HOUR_MS + 1);
    await load();
    expect(fileFetches()).toBe(2);
  });
});

describe('R21: a refresh tried inside 24 h, during a stop', () => {
  it('does not count as waiting, so /shopping neither holds its estimate nor shows the stop line for it', async () => {
    const scry = fakeScryfall({ card: (name) => ({ ...cardJson(name), prices: { usd: null } }) });
    const cache = tab(scry);
    cache.seed(FILE, OLD);
    cache.refreshPrice('Sol Ring');
    await advance(0);
    expect(cache.get('Sol Ring')).toMatchObject({ price: '$1.42', priceCheckedAt: T0 });
    storage.setItem(STOP_KEY, JSON.stringify({ until: T0 + 120_000, ms: 60_000, n: 3 }));
    await advance(1_000);
    cache.refreshPrice('Sol Ring');
    expect(cache.pricePending('Sol Ring')).toBe(false);
  });
});
