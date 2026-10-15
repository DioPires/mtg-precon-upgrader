import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createCardCache, type CardEntry } from '../../data/cardCache';
import { createScryfallLimiter, STOP_KEY } from '../../data/scryfallLimiter';
import type { RawCardMetadata } from '../../data/types';
import { cardJson, fakeScryfall, MemoryStorage, type Outcome } from './scryfallFakes';

const T0 = Date.UTC(2026, 9, 14, 12, 0, 0);
const DAY_MS = 24 * 60 * 60 * 1000;

// Three entries as data/card-metadata.json holds them.
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
  'Bonecrusher Giant': {
    cmc: 3,
    colors: ['R'],
    image: 'front/0/9/09ebe6b5-2a6b-4f0b-9d8b-0e5a2b2a7b11.jpg?1700000000',
    layout: 'adventure',
    mana_cost: '{2}{R} // {1}{R}',
    type_line: 'Creature — Giant // Instant — Adventure',
    usd: 0.5,
    eur: 0.4,
  },
  'Nameless Relic': {
    cmc: 2,
    colors: [],
    image: 'front/a/b/ab000000-0000-0000-0000-000000000000.jpg?1',
    mana_cost: '{2}',
    type_line: 'Artifact',
    usd: null,
    eur: null,
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

function setup(outcome?: (n: number, url: string) => Outcome, delayMs = 0, card?: (name: string) => object | null) {
  const scry = fakeScryfall({ delayMs, outcome, card });
  const cache = createCardCache({
    storage,
    limiter: createScryfallLimiter({ fetchImpl: scry.fetch, storage, locks: null }),
  });
  return { scry, cache };
}

const advance = (ms: number) => vi.advanceTimersByTimeAsync(ms);

describe('cardCache lookups', () => {
  it('looks a card up and notifies subscribers with the loaded entry', async () => {
    const { scry, cache } = setup();
    const listener = vi.fn();
    cache.subscribe('Mana Crypt', listener);
    cache.enqueue('Mana Crypt');
    await advance(0);
    expect(scry.names()).toEqual(['Mana Crypt']);
    const entry = cache.get('Mana Crypt')!;
    expect(entry).toMatchObject({
      status: 'loaded',
      name: 'Mana Crypt',
      image_small: cardJson('Mana Crypt').image_uris.small,
      image_large: cardJson('Mana Crypt').image_uris.large,
      price: '$0.42',
    });
    expect(listener.mock.calls.map(([e]) => (e as CardEntry).status)).toEqual(['loading', 'loaded']);
  });

  it('dedupes a name that is queued, out or loaded', async () => {
    const { scry, cache } = setup(undefined, 150);
    cache.enqueue('Mana Crypt');
    cache.enqueue('Mana Crypt');
    await advance(50);
    cache.enqueue('Mana Crypt');
    await advance(5_000);
    cache.enqueue('Mana Crypt');
    await advance(5_000);
    expect(scry.sends).toHaveLength(1);
  });

  it('persists a loaded lookup and rehydrates it on get()', async () => {
    const { cache } = setup();
    cache.enqueue('Mana Crypt');
    await advance(0);
    const parsed = JSON.parse(storage.getItem('gv1-card:mana crypt')!) as CardEntry;
    expect(parsed).toMatchObject({ status: 'loaded', fetchedAt: T0 });

    const { scry: second, cache: reloaded } = setup();
    expect(reloaded.get('Mana Crypt')?.image_small).toBe(cardJson('Mana Crypt').image_uris.small);
    reloaded.enqueue('Mana Crypt');
    await advance(1_000);
    expect(second.sends).toHaveLength(0);
  });

  it('discards persisted entries older than 24h', () => {
    storage.setItem('gv1-card:mana crypt', JSON.stringify({ status: 'loaded', name: 'Mana Crypt', fetchedAt: T0 - DAY_MS - 1 }));
    const { cache } = setup();
    expect(cache.get('Mana Crypt')).toBeNull();
    expect(storage.getItem('gv1-card:mana crypt')).toBeNull();
  });

  it('records a batch that fails with a 500 without persisting it', async () => {
    const { cache } = setup(() => 500);
    cache.enqueue('Nonesuch');
    await advance(0);
    expect(cache.get('Nonesuch')).toMatchObject({ status: 'error', errorStatus: 500 });
    expect(storage.getItem('gv1-card:nonesuch')).toBeNull();
  });

  it('asks for a card once per failure: no in-place retry', async () => {
    const { scry, cache } = setup(() => 500);
    cache.enqueue('Nonesuch');
    await advance(10_000);
    expect(scry.names()).toEqual(['Nonesuch']);
  });

  it('survives malformed localStorage payloads gracefully', () => {
    storage.setItem('gv1-card:sol ring', '{not json');
    const { cache } = setup();
    expect(cache.get('Sol Ring')).toBeNull();
  });
});

describe('cardCache.seed (card-metadata.json)', () => {
  it('holds a name of the file as loaded at once, and enqueue sends nothing for it', async () => {
    const { scry, cache } = setup();
    cache.seed(FILE);
    expect(cache.get('Sol Ring')?.status).toBe('loaded');
    expect(cache.get('sol ring')?.price).toBe('$1.42');
    cache.enqueue('Sol Ring');
    cache.enqueue('Bonecrusher Giant', { first: true });
    await advance(5_000);
    expect(scry.sends).toHaveLength(0);
  });

  it("builds Scryfall's four picture addresses from the file's path", () => {
    const { cache } = setup();
    cache.seed(FILE);
    const path = FILE['Sol Ring'].image;
    expect(cache.get('Sol Ring')).toMatchObject({
      image_small: `https://cards.scryfall.io/small/${path}`,
      image_normal: `https://cards.scryfall.io/normal/${path}`,
      image_large: `https://cards.scryfall.io/large/${path}`,
      art_crop: `https://cards.scryfall.io/art_crop/${path}`,
    });
  });

  it("shows the front half's cost of a two-part card, and the file's type line and mana value", () => {
    const { cache } = setup();
    cache.seed(FILE);
    expect(cache.get('Bonecrusher Giant')).toMatchObject({
      mana_cost: '{2}{R}',
      cmc: 3,
      type_line: 'Creature — Giant // Instant — Adventure',
    });
  });

  it('gives a card without a USD price a null price', () => {
    const { cache } = setup();
    cache.seed(FILE);
    expect(cache.get('Nameless Relic')?.status).toBe('loaded');
    expect(cache.get('Nameless Relic')?.price).toBeNull();
  });

  it("removes the gv1-card: entries of the names it seeds and writes none, so storage holds each card once", () => {
    const lookup = { status: 'loaded', name: 'Sol Ring', image_small: 'old', fetchedAt: T0 - 1_000 };
    storage.setItem('gv1-card:sol ring', JSON.stringify(lookup));
    storage.setItem('gv1-card:bonecrusher giant', JSON.stringify({ ...lookup, name: 'Bonecrusher Giant' }));
    storage.setItem('gv1-card:mana crypt', JSON.stringify({ ...lookup, name: 'Mana Crypt' }));
    const { cache } = setup();
    cache.seed(FILE);
    expect(storage.getItem('gv1-card:sol ring')).toBeNull();
    expect(storage.getItem('gv1-card:bonecrusher giant')).toBeNull();
    expect(storage.getItem('gv1-card:nameless relic')).toBeNull();
    // A name outside the file keeps its lookup.
    expect(storage.getItem('gv1-card:mana crypt')).not.toBeNull();
    expect(cache.get('Sol Ring')?.image_small).toContain('cards.scryfall.io/small/front/8/e/');
  });

  it('notifies a subscriber of a seeded name', () => {
    const { cache } = setup();
    const listener = vi.fn();
    cache.subscribe('Sol Ring', listener);
    cache.seed(FILE);
    expect(listener).toHaveBeenCalledWith(expect.objectContaining({ status: 'loaded', name: 'Sol Ring' }));
  });
});

describe('cardCache.imageFailed', () => {
  it("looks a seeded card up once when its picture fails, and the answer's addresses replace the file's for 24 h", async () => {
    const { scry, cache } = setup();
    cache.seed(FILE);
    cache.imageFailed('Sol Ring');
    await advance(0);
    expect(scry.names()).toEqual(['Sol Ring']);
    const refreshed = cache.get('Sol Ring')!;
    expect(refreshed).toMatchObject({
      status: 'loaded',
      image_normal: cardJson('Sol Ring').image_uris.normal,
      art_crop: cardJson('Sol Ring').image_uris.art_crop,
      // The file's facts stay.
      price: '$1.42',
      refreshedAt: T0,
    });
    expect(JSON.parse(storage.getItem('gv1-card:sol ring')!)).toMatchObject({ refreshedAt: T0, fetchedAt: T0 });

    // A second failure inside 24 h sends nothing, also after a reload.
    await advance(60_000);
    cache.imageFailed('Sol Ring');
    const { scry: afterReload, cache: reloaded } = setup();
    reloaded.seed(FILE);
    expect(reloaded.get('Sol Ring')?.image_normal).toBe(cardJson('Sol Ring').image_uris.normal);
    reloaded.imageFailed('Sol Ring');
    await advance(10_000);
    expect(scry.sends).toHaveLength(1);
    expect(afterReload.sends).toHaveLength(0);
  });

  it('sends nothing more inside 24 h when the lookup after a failed picture fails too', async () => {
    const { scry, cache } = setup(() => 404);
    cache.seed(FILE);
    cache.imageFailed('Sol Ring');
    await advance(0);
    expect(cache.get('Sol Ring')).toMatchObject({ status: 'loaded', price: '$1.42' });
    cache.imageFailed('Sol Ring');
    await advance(DAY_MS - 1_000);
    cache.imageFailed('Sol Ring');
    await advance(1_000);
    expect(scry.sends).toHaveLength(1);
    // After 24 h one more try.
    await advance(1);
    cache.imageFailed('Sol Ring');
    await advance(0);
    expect(scry.sends).toHaveLength(2);
  });

  it('sends nothing for a name outside the file', async () => {
    const { scry, cache } = setup();
    cache.imageFailed('Mana Crypt');
    await advance(1_000);
    expect(scry.sends).toHaveLength(0);
  });
});

// DEC-1131: every lookup is a batch of up to 75 names (POST /cards/collection).
describe.each([0, 150])('cardCache batches, answers after %i ms', (delay) => {
  // A card with two halves, as Scryfall answers it: the full name, and the faces.
  const GIANT = {
    ...cardJson('Bonecrusher Giant // Stomp'),
    mana_cost: '{2}{R} // {1}{R}',
    card_faces: [
      { name: 'Bonecrusher Giant', mana_cost: '{2}{R}', type_line: 'Creature — Giant' },
      { name: 'Stomp', mana_cost: '{1}{R}', type_line: 'Instant — Adventure' },
    ],
  };
  // Scryfall matches a front face; a full `//` name goes to not_found.
  const byFront = (name: string) =>
    name.toLowerCase() === 'bonecrusher giant' ? GIANT : name.includes('//') ? null : cardJson(name);

  it('sends a `//` name as its front face and stores the answer under the name asked', async () => {
    const { scry, cache } = setup(undefined, delay, byFront);
    cache.enqueue('Bonecrusher Giant // Stomp');
    await advance(delay);
    expect(scry.batches()).toEqual([['Bonecrusher Giant']]);
    expect(cache.get('Bonecrusher Giant // Stomp')).toMatchObject({
      status: 'loaded',
      name: 'Bonecrusher Giant // Stomp',
      mana_cost: '{2}{R}',
    });
    expect(JSON.parse(storage.getItem('gv1-card:bonecrusher giant // stomp')!)).toMatchObject({ status: 'loaded', fetchedAt: T0 + delay });
  });

  it('sends two names with one front face once, and both get the answer', async () => {
    const { scry, cache } = setup(undefined, delay, byFront);
    cache.enqueue('Bonecrusher Giant // Stomp');
    cache.enqueue('Bonecrusher Giant');
    await advance(delay);
    expect(scry.batches()).toEqual([['Bonecrusher Giant']]);
    expect(cache.get('Bonecrusher Giant // Stomp')?.name).toBe('Bonecrusher Giant // Stomp');
    expect(cache.get('Bonecrusher Giant')?.name).toBe('Bonecrusher Giant // Stomp');
  });

  it('matches the answer to the names by the fold of their names, not by position', async () => {
    // The answer holds its cards in another order, and with the accent that the app's name lacks.
    const fetchImpl = (async () => {
      await new Promise((resolve) => setTimeout(resolve, delay));
      return new Response(
        JSON.stringify({
          object: 'list',
          not_found: [],
          data: [cardJson('Zuran Orb'), cardJson("Lim-Dûl's Vault"), cardJson('Arcane Signet')],
        }),
        { status: 200 },
      );
    }) as typeof fetch;
    const cache = createCardCache({ storage, limiter: createScryfallLimiter({ fetchImpl, storage, locks: null }) });
    ['Arcane Signet', "Lim-Dul's Vault", 'Zuran Orb'].forEach((name) => cache.enqueue(name));
    await advance(delay);
    expect(cache.get('Arcane Signet')?.image_small).toBe(cardJson('Arcane Signet').image_uris.small);
    expect(cache.get("Lim-Dul's Vault")?.name).toBe("Lim-Dûl's Vault");
    expect(cache.get('Zuran Orb')?.image_small).toBe(cardJson('Zuran Orb').image_uris.small);
  });

  it('a name in not_found is not asked again inside 24 h, also from a new cache on the same storage; after 24 h, once', async () => {
    const { scry, cache } = setup(undefined, delay, () => null);
    cache.enqueue('Nonesuch');
    await advance(delay);
    expect(cache.get('Nonesuch')).toMatchObject({ status: 'error', errorStatus: 404 });
    await advance(60_000);
    cache.enqueue('Nonesuch');
    await advance(2_000);
    expect(scry.sends).toHaveLength(1);

    // A reload: a new cache on the same storage.
    const { scry: second, cache: reloaded } = setup(undefined, delay, () => null);
    expect(reloaded.get('Nonesuch')).toMatchObject({ status: 'error', errorStatus: 404 });
    await advance(T0 + delay + DAY_MS - 1 - Date.now());
    reloaded.enqueue('Nonesuch');
    await advance(0);
    expect(second.sends).toHaveLength(0);
    await advance(1);
    reloaded.enqueue('Nonesuch');
    reloaded.enqueue('Nonesuch');
    await advance(5_000);
    expect(second.batches()).toEqual([['Nonesuch']]);
  });
});

// DEC-1131 rulings 1, 3, 7 and 8: a price older than 24 h is asked again.
describe.each([0, 150])('cardCache.refreshPrice, answers after %i ms', (delay) => {
  const HOUR_MS = 3_600_000;
  const OLD = new Date(T0 - 25 * HOUR_MS).toISOString();
  const FRESH = new Date(T0 - HOUR_MS).toISOString();
  // An answer with another cost, type line and pictures than the file's.
  const priced = (usd: string | null) => (name: string) => ({
    ...cardJson(name),
    mana_cost: '{9}',
    type_line: 'Answer Type',
    prices: { usd },
  });

  it('asks once for a file price older than 24 h; the refresh changes only the price and its date', async () => {
    const { scry, cache } = setup(undefined, delay, priced('2.50'));
    cache.seed(FILE, OLD);
    const before = cache.get('Sol Ring')!;
    expect(before).toMatchObject({ price: '$1.42', priceAsOf: Date.parse(OLD) });
    cache.refreshPrice('Sol Ring');
    cache.refreshPrice('Sol Ring');
    expect(cache.pricePending('Sol Ring')).toBe(true);
    await advance(delay);
    expect(scry.batches()).toEqual([['Sol Ring']]);
    expect(cache.pricePending('Sol Ring')).toBe(false);
    expect(cache.get('Sol Ring')).toEqual({ ...before, price: '$2.50', priceAsOf: T0 + delay, priceCheckedAt: T0 + delay });
    cache.refreshPrice('Sol Ring');
    await advance(10_000);
    expect(scry.sends).toHaveLength(1);
  });

  it('does not ask for a file price younger than 24 h', async () => {
    const { scry, cache } = setup(undefined, delay, priced('2.50'));
    cache.seed(FILE, FRESH);
    cache.refreshPrice('Sol Ring');
    expect(cache.pricePending('Sol Ring')).toBe(false);
    await advance(10_000);
    expect(scry.sends).toHaveLength(0);
    // 24 h after the file's date the price is old: one try.
    await advance(T0 + 23 * HOUR_MS + 1 - Date.now());
    cache.refreshPrice('Sol Ring');
    await advance(0);
    expect(scry.batches()).toEqual([['Sol Ring']]);
  });

  it('seed() keeps a refreshed price, so a reload inside 24 h asks nothing; after 24 h, once', async () => {
    const { cache } = setup(undefined, delay, priced('2.50'));
    cache.seed(FILE, OLD);
    cache.refreshPrice('Sol Ring');
    await advance(delay);
    const at = T0 + delay;
    expect(JSON.parse(storage.getItem('gv1-card:sol ring')!)).toEqual({
      fetchedAt: at,
      priceCheckedAt: at,
      price: '$2.50',
      priceAsOf: at,
    });

    await advance(23 * HOUR_MS);
    const { scry: second, cache: reloaded } = setup(undefined, delay, priced('3.00'));
    reloaded.seed(FILE, OLD);
    expect(reloaded.get('Sol Ring')).toMatchObject({ price: '$2.50', priceAsOf: at, mana_cost: '{1}' });
    reloaded.refreshPrice('Sol Ring');
    await advance(10_000);
    expect(second.sends).toHaveLength(0);

    await advance(HOUR_MS);
    reloaded.refreshPrice('Sol Ring');
    await advance(delay);
    expect(second.batches()).toEqual([['Sol Ring']]);
    expect(reloaded.get('Sol Ring')?.price).toBe('$3.00');
  });

  it("the file's price wins when the file is newer than the stored refresh", () => {
    const refreshedAt = T0 - 2 * HOUR_MS;
    storage.setItem(
      'gv1-card:sol ring',
      JSON.stringify({ fetchedAt: refreshedAt, priceCheckedAt: refreshedAt, price: '$9.99', priceAsOf: refreshedAt }),
    );
    const { cache: newer } = setup();
    newer.seed(FILE, FRESH);
    expect(newer.get('Sol Ring')).toMatchObject({ price: '$1.42', priceAsOf: Date.parse(FRESH) });
    const { cache: older } = setup();
    older.seed(FILE, new Date(T0 - 3 * HOUR_MS).toISOString());
    expect(older.get('Sol Ring')).toMatchObject({ price: '$9.99', priceAsOf: refreshedAt });
  });

  const noPrice: Array<[string, ((n: number, url: string) => Outcome) | undefined, ((name: string) => object | null) | undefined]> = [
    ['not_found', undefined, () => null],
    ['a 400', () => 400, undefined],
    ['a 422', () => 422, undefined],
    ['usd null', undefined, priced(null)],
  ];
  for (const [label, outcome, card] of noPrice) {
    it(`a refresh that gets ${label} keeps the price shown, and nobody asks again inside 24 h`, async () => {
      const { scry, cache } = setup(outcome, delay, card);
      cache.seed(FILE, OLD);
      cache.refreshPrice('Sol Ring');
      await advance(delay);
      expect(cache.get('Sol Ring')).toMatchObject({
        status: 'loaded',
        price: '$1.42',
        priceAsOf: Date.parse(OLD),
        priceCheckedAt: T0 + delay,
      });
      expect(cache.pricePending('Sol Ring')).toBe(false);
      await advance(DAY_MS - 1);
      cache.refreshPrice('Sol Ring');
      const { scry: second, cache: reloaded } = setup(outcome, delay, card);
      reloaded.seed(FILE, OLD);
      reloaded.refreshPrice('Sol Ring');
      await advance(0);
      expect(scry.sends).toHaveLength(1);
      expect(second.sends).toHaveLength(0);
      expect(storage.getItem(STOP_KEY)).toBeNull();
    });
  }

  it('a price refresh that meets a stop waits, first, for the batch after the stop', async () => {
    const { scry, cache } = setup((n) => (n === 1 ? 429 : 200), delay, priced('2.50'));
    cache.seed(FILE, OLD);
    cache.refreshPrice('Sol Ring');
    await advance(delay);
    expect(cache.pricePending('Sol Ring')).toBe(true);
    expect(cache.get('Sol Ring')?.price).toBe('$1.42');
    await advance(30_000 + delay);
    expect(scry.batches()).toEqual([['Sol Ring'], ['Sol Ring']]);
    expect(cache.pricePending('Sol Ring')).toBe(false);
    expect(cache.get('Sol Ring')).toMatchObject({ price: '$2.50', priceAsOf: T0 + delay + 30_000 + delay });
  });

  it('the names asked first go first, then the lookups, then the refreshes', async () => {
    const { scry, cache } = setup(undefined, delay, priced('2.50'));
    cache.seed(FILE, OLD);
    cache.refreshPrice('Sol Ring');
    cache.enqueue('Mana Crypt');
    cache.imageFailed('Nameless Relic');
    cache.enqueue('Hover Card', { first: true });
    await advance(0);
    expect(scry.batches()).toEqual([['Hover Card', 'Mana Crypt', 'Sol Ring', 'Nameless Relic']]);
  });

  it('with more than 75 names waiting, the lookups take the batch and the refreshes go in the next', async () => {
    const { scry, cache } = setup(undefined, delay, priced('2.50'));
    cache.seed(FILE, OLD);
    cache.refreshPrice('Sol Ring');
    const lookups = Array.from({ length: 75 }, (_, i) => `Look ${i + 1}`);
    lookups.forEach((name) => cache.enqueue(name));
    await advance(1_200);
    expect(scry.batches()).toEqual([lookups, ['Sol Ring']]);
  });

  it('a price and a picture refresh of one card go in one batch, and each keeps the other', async () => {
    const { scry, cache } = setup(undefined, delay, priced('2.50'));
    cache.seed(FILE, OLD);
    cache.refreshPrice('Sol Ring');
    cache.imageFailed('Sol Ring');
    await advance(delay);
    expect(scry.batches()).toEqual([['Sol Ring']]);
    expect(cache.get('Sol Ring')).toMatchObject({
      price: '$2.50',
      image_normal: cardJson('Sol Ring').image_uris.normal,
      mana_cost: '{1}',
      type_line: 'Artifact',
    });
    const { cache: reloaded } = setup();
    reloaded.seed(FILE, OLD);
    expect(reloaded.get('Sol Ring')).toMatchObject({ price: '$2.50', image_normal: cardJson('Sol Ring').image_uris.normal });
  });

  it('does not refresh a name outside the file: its lookup dates its price', async () => {
    const { scry, cache } = setup(undefined, delay, priced('2.50'));
    cache.enqueue('Mana Crypt');
    await advance(delay);
    expect(cache.get('Mana Crypt')).toMatchObject({ price: '$2.50', priceAsOf: T0 + delay });
    cache.refreshPrice('Mana Crypt');
    await advance(10_000);
    expect(scry.sends).toHaveLength(1);
  });
});
