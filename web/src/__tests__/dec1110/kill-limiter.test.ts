// DEC-1110 reviewer's kill cases for scryfallLimiter.ts and cardCache.ts.
// Each case passes on 58ca0b3 and fails on the mutant named in its title.
// DEC-1131 moved them to batches (POST /cards/collection) and to the stop
// record's number; each case keeps the mutant that it kills.
import { createCardCache } from '../../data/cardCache';
import {
  autocompleteUrl,
  collectionRequest,
  COLLECTION_URL,
  createScryfallLimiter,
  STOP_KEY,
} from '../../data/scryfallLimiter';
import type { RawCardMetadata } from '../../data/types';
import {
  collectionJson,
  fakeScryfall,
  MemoryStorage,
} from '../data/scryfallFakes';

const T0 = Date.UTC(2026, 9, 14, 12, 0, 0);
const DAY_MS = 24 * 60 * 60 * 1000;
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

/** A fetch whose answers the case gives by hand, in any order. */
function manualFetch() {
  const sends: Array<{ url: string; at: number; answer: (r: Response | Error) => void }> = [];
  const fetchImpl = ((input: RequestInfo | URL) =>
    new Promise<Response>((resolve, reject) => {
      sends.push({
        url: String(input),
        at: Date.now(),
        answer: (r) => (r instanceof Error ? reject(r) : resolve(r)),
      });
    })) as typeof fetch;
  return { sends, fetchImpl };
}
const ok = (name: string) => new Response(JSON.stringify(collectionJson([name])), { status: 200 });
/** limiter.fetch() of one batch. */
const batch = (names: string[]) => {
  const { method, headers, body } = collectionRequest(names);
  return [COLLECTION_URL, { method, headers, body }] as const;
};
const status = (code: number) => new Response('{"object":"error"}', { status: code });
const stored = () => JSON.parse(storage.getItem(STOP_KEY) ?? 'null') as { until: number; ms: number; n: number } | null;

describe('K1 fail(): a request that was out when the stop started', () => {
  it('K1: a second 429 from a request that was already out does not double the stop', async () => {
    const { sends, fetchImpl } = manualFetch();
    const limiter = createScryfallLimiter({ fetchImpl, storage, locks: null });
    void limiter.fetch(autocompleteUrl('sol'));
    void limiter.fetch(autocompleteUrl('sol r'));
    await advance(120);
    expect(sends).toHaveLength(2);
    sends[0].answer(status(429));
    await advance(0);
    expect(stored()).toEqual({ until: T0 + 120 + 30_000, ms: 30_000, n: expect.any(Number) });
    const first = stored();
    sends[1].answer(status(429));
    await advance(0);
    expect(stored()).toEqual(first);
  });
});

describe('K2 succeed(): a request that was out when the stop started', () => {
  it('K2: its success does not end the stop', async () => {
    const { sends, fetchImpl } = manualFetch();
    const limiter = createScryfallLimiter({ fetchImpl, storage, locks: null });
    void limiter.fetch(...batch(['Sol Ring']));
    const suggest = limiter.fetch(autocompleteUrl('sol'));
    await advance(0);
    const sent = (path: string) => sends.find((s) => new URL(s.url).pathname === path)!;
    expect(sends.map((s) => new URL(s.url).pathname).sort()).toEqual(['/cards/autocomplete', '/cards/collection']);
    sent('/cards/collection').answer(status(429));
    await advance(0);
    sent('/cards/autocomplete').answer(new Response('{"object":"catalog","data":[]}', { status: 200 }));
    await suggest;
    expect(limiter.stoppedUntil()).toBe(T0 + 30_000);
    expect(stored()).toEqual({ until: T0 + 30_000, ms: 30_000, n: expect.any(Number) });
    // Nothing goes before the end of the stop.
    await advance(30_000 - 1);
    expect(sends).toHaveLength(2);
  });
});

describe('K4 readStop(): a clock that went back', () => {
  it('K4: the reported end of a stop is at most its length ahead', () => {
    storage.setItem(STOP_KEY, JSON.stringify({ until: T0 + 10 * 3_600_000, ms: 30_000 }));
    const limiter = createScryfallLimiter({ fetchImpl: fakeScryfall().fetch, storage, locks: null });
    expect(limiter.stoppedUntil()).toBe(T0 + 30_000);
  });
});

describe('K10 enqueue(): a queued name asked for first', () => {
  it('K10: moves to the front of the queue, into the next batch', async () => {
    const scry = fakeScryfall();
    const cache = createCardCache({ storage, limiter: createScryfallLimiter({ fetchImpl: scry.fetch, storage, locks: null }) });
    const names = Array.from({ length: 80 }, (_, i) => `Q${i + 1}`);
    names.forEach((name) => cache.enqueue(name));
    cache.enqueue('Q80', { first: true });
    await advance(5_000);
    expect(scry.batches()).toEqual([['Q80', ...names.slice(0, 74)], names.slice(74, 79)]);
  });
});

describe('K11 imageFailed(): the mark goes to storage before the lookup', () => {
  it('K11: after a refresh that fails, a reload inside 24 h sends nothing', async () => {
    const scry = fakeScryfall({ outcome: () => 404 });
    const first = createCardCache({ storage, limiter: createScryfallLimiter({ fetchImpl: scry.fetch, storage, locks: null }) });
    first.seed(FILE);
    first.imageFailed('Sol Ring');
    await advance(1_000);
    expect(scry.sends).toHaveLength(1);
    // A reload: a new cache on the same storage, seeded again; the picture fails again.
    const reloaded = createCardCache({ storage, limiter: createScryfallLimiter({ fetchImpl: scry.fetch, storage, locks: null }) });
    reloaded.seed(FILE);
    reloaded.imageFailed('Sol Ring');
    await advance(DAY_MS - 2_000);
    expect(scry.sends).toHaveLength(1);
  });

  it('K11: a reload while the refresh waits in a stop does not queue a second one', async () => {
    storage.setItem(STOP_KEY, JSON.stringify({ until: T0 + 30_000, ms: 30_000 }));
    const scry = fakeScryfall();
    const first = createCardCache({ storage, limiter: createScryfallLimiter({ fetchImpl: scry.fetch, storage, locks: null }) });
    first.seed(FILE);
    first.imageFailed('Sol Ring');
    await advance(1_000);
    expect(scry.sends).toHaveLength(0);
    first._reset();
    const reloaded = createCardCache({ storage, limiter: createScryfallLimiter({ fetchImpl: scry.fetch, storage, locks: null }) });
    reloaded.seed(FILE);
    reloaded.imageFailed('Sol Ring');
    await advance(60_000);
    expect(scry.sends).toHaveLength(0);
  });
});

describe('A2 subscribe(): another tab', () => {
  it('A2: a listener hears a stop that another tab writes', () => {
    const limiter = createScryfallLimiter({ fetchImpl: fakeScryfall().fetch, storage, locks: null });
    const heard: Array<number | null> = [];
    const unsubscribe = limiter.subscribe((until) => heard.push(until));
    storage.setItem(STOP_KEY, JSON.stringify({ until: T0 + 30_000, ms: 30_000, n: 1 }));
    window.dispatchEvent(new StorageEvent('storage', { key: STOP_KEY }));
    expect(heard).toEqual([T0 + 30_000]);
    unsubscribe();
  });
});

describe('A3 drain(): bucket 2 after a 429', () => {
  it('A3: an autocomplete that met a 429 goes again when the stop ends, and resolves', async () => {
    const scry = fakeScryfall({ delayMs: 150, outcome: (n) => (n === 1 ? 429 : 200) });
    const limiter = createScryfallLimiter({ fetchImpl: scry.fetch, storage, locks: null });
    const suggest = limiter.fetch(autocompleteUrl('sol'));
    await advance(150 + 30_000 + 150);
    expect(scry.names()).toEqual(['sol', 'sol']);
    expect((await suggest).status).toBe(200);
  });
});

describe('A4 settle(): the seed arrives while a lookup is out', () => {
  it("A4: the file's entry stays, and no gv1-card: entry is written", async () => {
    const { sends, fetchImpl } = manualFetch();
    const cache = createCardCache({ storage, limiter: createScryfallLimiter({ fetchImpl, storage, locks: null }) });
    cache.enqueue('Sol Ring');
    await advance(0);
    expect(sends).toHaveLength(1);
    cache.seed(FILE);
    sends[0].answer(ok('Sol Ring'));
    await advance(0);
    expect(cache.get('Sol Ring')?.image_normal).toBe(`https://cards.scryfall.io/normal/${FILE['Sol Ring'].image}`);
    expect(storage.getItem('gv1-card:sol ring')).toBeNull();
  });
});

describe('A5 imageFailed(): a name outside the file', () => {
  it('A5: a looked-up card whose picture fails sends nothing more', async () => {
    const scry = fakeScryfall();
    const cache = createCardCache({ storage, limiter: createScryfallLimiter({ fetchImpl: scry.fetch, storage, locks: null }) });
    cache.enqueue('Mana Crypt');
    await advance(1_000);
    expect(cache.get('Mana Crypt')?.status).toBe('loaded');
    cache.imageFailed('Mana Crypt');
    await advance(5_000);
    expect(scry.sends).toHaveLength(1);
  });
});

describe('A11 writeStop(): storage that refuses the write', () => {
  it('A11: the stop lives in memory and holds', async () => {
    class FullStorage extends MemoryStorage {
      setItem(k: string, v: string): void {
        if (k === STOP_KEY) throw new DOMException('full', 'QuotaExceededError');
        super.setItem(k, v);
      }
    }
    const full = new FullStorage();
    const scry = fakeScryfall({ outcome: (n) => (n === 1 ? 429 : 200) });
    const limiter = createScryfallLimiter({ fetchImpl: scry.fetch, storage: full, locks: null });
    const out = limiter.fetch(...batch(['Sol Ring']));
    await advance(0);
    expect(limiter.stoppedUntil()).toBe(T0 + 30_000);
    await advance(30_000 - 1);
    expect(scry.sends).toHaveLength(1);
    await advance(1);
    await out;
    expect(scry.sends).toHaveLength(2);
  });
});

describe('A13 formatPricesDate(): the time zone of the machine', () => {
  it('A13: gives the UTC date in Pacific/Kiritimati (UTC+14) and Pacific/Pago_Pago (UTC-11)', async () => {
    const { formatPricesDate } = await import('../../lib/pricesDate');
    const tz = process.env.TZ;
    try {
      process.env.TZ = 'Pacific/Kiritimati';
      expect(formatPricesDate('2026-10-13T21:56:40+00:00')).toBe('13 Oct 2026');
      process.env.TZ = 'Pacific/Pago_Pago';
      expect(formatPricesDate('2026-10-14T05:00:00+00:00')).toBe('14 Oct 2026');
    } finally {
      if (tz === undefined) delete process.env.TZ;
      else process.env.TZ = tz;
    }
  });
});
