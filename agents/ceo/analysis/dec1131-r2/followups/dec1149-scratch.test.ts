// DEC-1149 scratch cases (reviewer of PR #54). Not a file of the pull request.
// 3c: the answer in reverse order, with a `//` card that the app asked for by its front face.
// 3d: a 400 or 422 holds a lookup 30 s in memory, and no stop starts.
// 3e: a PR #38 picture entry reads correctly, and a price refresh keeps its pictures.
// P2: a stored card-metadata.json (younger than 1 h) with a newer meta file.
// P5: the identifiers that the app builds from odd names.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createCardCache } from '../../data/cardCache';
import { createDeckLoader } from '../../data/loader';
import { createScryfallLimiter, STOP_KEY } from '../../data/scryfallLimiter';
import type { RawCardMetadata } from '../../data/types';
import { cardJson, fakeScryfall, identifiersOf, MemoryStorage, type Outcome } from '../data/scryfallFakes';

const T0 = Date.UTC(2026, 9, 14, 12, 0, 0);
const HOUR_MS = 3_600_000;
const DAY_MS = 24 * HOUR_MS;

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

function setup(outcome?: (n: number, url: string) => Outcome, delayMs = 0, card?: (name: string) => object | null) {
  const scry = fakeScryfall({ delayMs, outcome, card });
  const cache = createCardCache({ storage, limiter: createScryfallLimiter({ fetchImpl: scry.fetch, storage, locks: null }) });
  return { scry, cache };
}

describe.each([0, 150])('3c: the answer in reverse order, answers after %i ms', (delay) => {
  it('matches each name by the fold, also a `//` card asked by its front face', async () => {
    const GIANT = {
      ...cardJson('Bonecrusher Giant // Stomp'),
      card_faces: [
        { name: 'Bonecrusher Giant', mana_cost: '{2}{R}', type_line: 'Creature — Giant' },
        { name: 'Stomp', mana_cost: '{1}{R}', type_line: 'Instant — Adventure' },
      ],
    };
    const FIRE = {
      ...cardJson('Fire // Ice'),
      card_faces: [
        { name: 'Fire', mana_cost: '{1}{R}', type_line: 'Instant' },
        { name: 'Ice', mana_cost: '{1}{U}', type_line: 'Instant' },
      ],
    };
    const sent: string[][] = [];
    const fetchImpl = (async (_url: string, init?: RequestInit) => {
      const names = identifiersOf(init?.body);
      sent.push(names);
      await new Promise((resolve) => setTimeout(resolve, delay));
      // The answer in reverse order of the request.
      const byName: Record<string, object> = { 'bonecrusher giant': GIANT, fire: FIRE, 'arcane signet': cardJson('Arcane Signet') };
      const data = names.map((n) => byName[n.toLowerCase()]).filter(Boolean).reverse();
      return new Response(JSON.stringify({ object: 'list', not_found: [], data }), { status: 200 });
    }) as unknown as typeof fetch;
    const cache = createCardCache({ storage, limiter: createScryfallLimiter({ fetchImpl, storage, locks: null }) });
    cache.enqueue('Bonecrusher Giant'); // a front face, as an owned-cards CSV names it
    cache.enqueue('Arcane Signet');
    cache.enqueue('Fire // Ice'); // a full name: goes out as "Fire"
    await advance(delay);
    expect(sent).toEqual([['Bonecrusher Giant', 'Arcane Signet', 'Fire']]);
    expect(cache.get('Bonecrusher Giant')).toMatchObject({ status: 'loaded', name: 'Bonecrusher Giant // Stomp', mana_cost: '{2}{R}' });
    expect(cache.get('Bonecrusher Giant')?.image_small).toBe(GIANT.image_uris.small);
    expect(cache.get('Arcane Signet')).toMatchObject({ status: 'loaded', name: 'Arcane Signet', image_small: cardJson('Arcane Signet').image_uris.small });
    expect(cache.get('Fire // Ice')).toMatchObject({ status: 'loaded', name: 'Fire // Ice', image_small: FIRE.image_uris.small });
  });
});

describe.each([400, 422])('3d: a %i on a batch of lookups', (status) => {
  it('fails the lookups for 30 s in memory, keeps nothing in storage, and starts no stop', async () => {
    const { scry, cache } = setup((n) => (n === 1 ? status : 200));
    cache.enqueue('Nonesuch');
    await advance(0);
    expect(cache.get('Nonesuch')).toMatchObject({ status: 'error', errorStatus: status });
    expect(storage.getItem('gv1-card:nonesuch')).toBeNull();
    expect(storage.getItem(STOP_KEY)).toBeNull();
    await advance(30_000 - 1);
    cache.enqueue('Nonesuch');
    await advance(0);
    expect(scry.sends).toHaveLength(1);
    await advance(1);
    cache.enqueue('Nonesuch');
    await advance(0);
    expect(scry.batches()).toEqual([['Nonesuch'], ['Nonesuch']]);
    expect(cache.get('Nonesuch')).toMatchObject({ status: 'loaded' });
  });
});

describe('3e: a PR #38 picture entry', () => {
  const OLD = new Date(T0 - 25 * HOUR_MS).toISOString();
  it('shows its pictures with the file price; a price refresh keeps the pictures, also after a reload', async () => {
    const at = T0 - HOUR_MS;
    // What PR #38 wrote after a picture refresh: the whole entry, with refreshedAt.
    storage.setItem(
      'gv1-card:sol ring',
      JSON.stringify({
        status: 'loaded',
        name: 'Sol Ring',
        mana_cost: '{1}',
        cmc: 1,
        type_line: 'Artifact',
        image_small: 'https://cards.scryfall.io/small/pr38/sol.jpg',
        image_normal: 'https://cards.scryfall.io/normal/pr38/sol.jpg',
        image_large: 'https://cards.scryfall.io/large/pr38/sol.jpg',
        art_crop: 'https://cards.scryfall.io/art_crop/pr38/sol.jpg',
        price: '$0.99',
        refreshedAt: at,
        fetchedAt: at,
      }),
    );
    const { scry, cache } = setup(undefined, 0, (name) => ({ ...cardJson(name), prices: { usd: '2.50' } }));
    cache.seed(FILE, OLD);
    expect(cache.get('Sol Ring')).toMatchObject({
      status: 'loaded',
      image_small: 'https://cards.scryfall.io/small/pr38/sol.jpg',
      price: '$1.42',
      priceAsOf: Date.parse(OLD),
      mana_cost: '{1}',
    });
    // The picture is not asked again inside 24 h.
    cache.imageFailed('Sol Ring');
    cache.refreshPrice('Sol Ring');
    await advance(0);
    expect(scry.batches()).toEqual([['Sol Ring']]);
    expect(cache.get('Sol Ring')).toMatchObject({ price: '$2.50', image_small: 'https://cards.scryfall.io/small/pr38/sol.jpg' });
    const stored = JSON.parse(storage.getItem('gv1-card:sol ring')!);
    expect(stored).toEqual({
      refreshedAt: at,
      image_small: 'https://cards.scryfall.io/small/pr38/sol.jpg',
      image_normal: 'https://cards.scryfall.io/normal/pr38/sol.jpg',
      image_large: 'https://cards.scryfall.io/large/pr38/sol.jpg',
      art_crop: 'https://cards.scryfall.io/art_crop/pr38/sol.jpg',
      fetchedAt: T0,
      priceCheckedAt: T0,
      price: '$2.50',
      priceAsOf: T0,
    });
    const { cache: reloaded } = setup();
    reloaded.seed(FILE, OLD);
    expect(reloaded.get('Sol Ring')).toMatchObject({ price: '$2.50', image_small: 'https://cards.scryfall.io/small/pr38/sol.jpg' });
    // 24 h after the picture refresh the pictures go back to the file's; the price part stays live.
    await advance(DAY_MS - HOUR_MS + 1);
    const { cache: later } = setup();
    later.seed(FILE, OLD);
    expect(later.get('Sol Ring')?.image_small).toMatch(/^https:\/\/cards\.scryfall\.io\/small\/front\//);
    expect(later.get('Sol Ring')?.price).toBe('$2.50');
  });
});

describe('P2: a stored card-metadata.json with a newer meta file', () => {
  it("pairs the stored file's old prices with the new date, so they win over a fresh stored refresh and ask nothing", async () => {
    const OLD_DATE = new Date(T0 - 30 * HOUR_MS).toISOString(); // the date of the file the user's tab stored
    const NEW_DATE = new Date(T0 - 25 * 60_000).toISOString(); // a deploy 25 min ago: new file, new meta
    const NEW_FILE: RawCardMetadata = { 'Sol Ring': { ...FILE['Sol Ring'], usd: 3 } };
    const loaderStorage = new MemoryStorage();
    // Visit 1, 40 min ago: the old file and its meta; the cache refreshes Sol Ring.
    vi.setSystemTime(T0 - 40 * 60_000);
    let deployed = false;
    const fetchImpl = vi.fn(async (url: string) => {
      const body = url.endsWith('/card-metadata.meta.json')
        ? { prices_as_of: deployed ? NEW_DATE : OLD_DATE }
        : url.endsWith('/card-metadata.json')
          ? deployed ? NEW_FILE : FILE
          : {};
      return { ok: true, status: 200, json: async () => body } as Response;
    });
    const scry = fakeScryfall({ card: (name) => ({ ...cardJson(name), prices: { usd: '2.50' } }) });
    const visit = () => {
      const cache = createCardCache({ storage, limiter: createScryfallLimiter({ fetchImpl: scry.fetch, storage, locks: null }) });
      const loader = createDeckLoader({ fetchImpl: fetchImpl as unknown as typeof fetch, storage: loaderStorage, cardCache: cache });
      return { cache, loader };
    };
    const first = visit();
    await first.loader.loadCardMetadata();
    expect(first.cache.get('Sol Ring')).toMatchObject({ price: '$1.42', priceAsOf: Date.parse(OLD_DATE) });
    first.cache.refreshPrice('Sol Ring');
    await advance(0);
    expect(first.cache.get('Sol Ring')).toMatchObject({ price: '$2.50', priceAsOf: T0 - 40 * 60_000 });

    // The deploy, then visit 2 now: the stored file is 40 min old (younger than 1 h), the meta file is new.
    deployed = true;
    vi.setSystemTime(T0);
    const second = visit();
    await second.loader.loadCardMetadata();
    const fileFetches = fetchImpl.mock.calls.filter(([url]) => String(url).endsWith('/card-metadata.json'));
    expect(fileFetches).toHaveLength(1); // the stored old file is used
    // The old file's price ($1.42, 30 h old) shows with the new date and wins over the 40-min-old refresh ($2.50).
    expect(second.cache.get('Sol Ring')).toMatchObject({ price: '$1.42', priceAsOf: Date.parse(NEW_DATE) });
    second.cache.refreshPrice('Sol Ring');
    await advance(10_000);
    expect(scry.sends).toHaveLength(1); // nothing asks: the price looks 25 min old

    // An hour after visit 1 the stored file goes, and the new file comes.
    vi.setSystemTime(T0 + 21 * 60_000);
    const third = visit();
    await third.loader.loadCardMetadata();
    expect(third.cache.get('Sol Ring')).toMatchObject({ price: '$3.00', priceAsOf: Date.parse(NEW_DATE) });
  });
});

describe('P5: the identifier of odd names', () => {
  for (const [name, expected] of [
    [' // Back', ''],
    ['// Back', '// Back'],
    ['Front // ', 'Front'],
    ['   ', ''],
    ['—', '—'],
    ['#123', '#123'],
  ] as const) {
    it(`enqueue(${JSON.stringify(name)}) sends ${JSON.stringify(expected)}`, async () => {
      const { scry, cache } = setup();
      cache.enqueue(name);
      await advance(0);
      expect(scry.batches()).toEqual([[expected]]);
    });
  }
});
