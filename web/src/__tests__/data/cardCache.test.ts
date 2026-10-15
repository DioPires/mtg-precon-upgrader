import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createCardCache, type CardEntry } from '../../data/cardCache';
import { createScryfallLimiter } from '../../data/scryfallLimiter';
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

function setup(outcome?: (n: number, url: string) => Outcome, delayMs = 0) {
  const scry = fakeScryfall({ delayMs, outcome });
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

  it('records a failed lookup without persisting it', async () => {
    const { cache } = setup(() => 404);
    cache.enqueue('Nonesuch');
    await advance(0);
    expect(cache.get('Nonesuch')).toMatchObject({ status: 'error', errorStatus: 404 });
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
