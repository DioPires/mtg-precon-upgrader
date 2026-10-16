// DEC-1188 (N1 of DEC-1170): the body of the answer counts as part of the
// request. When a caller stores the answer (next() with `settle`), the limiter
// reads the body inside the request's 20 s. A body that has not ended then is a
// request with no answer: the limiter stops, the same batch goes first when the
// stop ends, and the tab's later names go after it.
// 8a: an answer whose body never ends (scratch case 8a of the PR #70 review).
// B1: a body that ends 1 ms before the deadline is an answer; one that ends at the deadline is not.
// B2: a body that fails before the deadline is the caller's to read: no stop, as before.
// B3: fetch() gives the answer at its head; the caller reads the body itself.
// B4: a 400 or a 422 whose body never ends is no answer either; a 429 stops at its head.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createCardCache } from '../../data/cardCache';
import { collectionRequest, COLLECTION_URL, createScryfallLimiter, STOP_KEY } from '../../data/scryfallLimiter';
import { collectionJson, fakeLocks, fakeScryfall, identifiersOf, MemoryStorage } from '../data/scryfallFakes';

const T0 = Date.UTC(2026, 9, 16, 12, 0, 0);
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
const storedStop = () => {
  const raw = storage.getItem(STOP_KEY);
  return raw ? (JSON.parse(raw) as { until: number; ms: number }) : null;
};

/** The body of the first answer; every later answer comes whole at once. */
type FirstBody =
  | 'never ends'
  | 'never ends, and errors at the abort'
  | 'one chunk, and never ends'
  | { endsAfter: number }
  | { failsAfter: number };

/** A fetch whose head comes `headMs` after the send, and whose first answer has `status` and the body `first`. */
function bodyFetch(first: FirstBody, headMs = 0, status = 200) {
  const sends: Array<{ at: number; names: string[] }> = [];
  const fetchImpl = ((_input: RequestInfo | URL, init?: RequestInit) => {
    const names = identifiersOf(init?.body);
    sends.push({ at: Date.now() - T0, names });
    const kind: FirstBody | 'whole' = sends.length === 1 ? first : 'whole';
    const bytes = new TextEncoder().encode(JSON.stringify(collectionJson(names)));
    const signal = init?.signal;
    // The body starts with the head, so `endsAfter` and `failsAfter` count from the head.
    const head = () => new Response(new ReadableStream<Uint8Array>({
      start(controller) {
        const end = () => {
          controller.enqueue(bytes);
          controller.close();
        };
        if (kind === 'whole') end();
        else if (kind === 'one chunk, and never ends') controller.enqueue(bytes.slice(0, 10));
        // A browser's fetch errors the body when the request is aborted.
        else if (kind === 'never ends, and errors at the abort') signal?.addEventListener('abort', () => controller.error(signal.reason));
        else if (typeof kind === 'object' && 'endsAfter' in kind) setTimeout(end, kind.endsAfter);
        else if (typeof kind === 'object') setTimeout(() => controller.error(new TypeError('network error')), kind.failsAfter);
      },
    }), { status: kind === 'whole' ? 200 : status });
    if (headMs === 0) return Promise.resolve(head());
    return new Promise<Response>((resolve) => setTimeout(() => resolve(head()), headMs));
  }) as typeof fetch;
  return { sends, fetchImpl };
}

describe('DEC-1188 8a: an answer whose body never ends', () => {
  for (const first of ['never ends', 'never ends, and errors at the abort', 'one chunk, and never ends'] as const) {
    it(`(the body ${first}) stops the limiter at 20 s; the batch goes again first, and the tab's later name goes after it`, async () => {
      const a = bodyFetch(first);
      const scryB = fakeScryfall();
      const locks = fakeLocks();
      const tabA = createCardCache({ storage, limiter: createScryfallLimiter({ fetchImpl: a.fetchImpl, storage, locks }) });
      const tabB = createCardCache({ storage, limiter: createScryfallLimiter({ fetchImpl: scryB.fetch, storage, locks }) });
      tabA.enqueue('A1');
      await advance(1_000);
      tabB.enqueue('B1');
      await advance(19_000 - 1);
      const before = { stop: storedStop(), tabB: scryB.sends.length };
      await advance(1);
      // 20 s after the start: no answer. A1 still waits for its batch; it has no error.
      const at20 = { stop: storedStop(), A1: tabA.get('A1') };
      await advance(11_000);
      tabA.enqueue('A2');
      await advance(60_000);

      expect({
        before,
        at20,
        tabA: a.sends,
        tabB: scryB.sends.map((s) => ({ at: s.at - T0, names: s.names })),
        A1: tabA.get('A1')?.status,
        A2: tabA.get('A2')?.status ?? null,
        B1: tabB.get('B1')?.status,
        stop: storedStop(),
      }).toEqual({
        before: { stop: null, tabB: 0 },
        at20: { stop: expect.objectContaining({ until: T0 + 50_000, ms: 30_000 }), A1: { status: 'loading', name: 'A1' } },
        tabA: [
          { at: 0, names: ['A1'] },
          { at: 51_200, names: ['A1'] },
          { at: 52_400, names: ['A2'] },
        ],
        tabB: [{ at: 50_000, names: ['B1'] }],
        A1: 'loaded',
        A2: 'loaded',
        B1: 'loaded',
        stop: null,
      });
    });
  }
});

describe('DEC-1188 B1: the deadline counts from the start, the body included', () => {
  for (const [endsAfter, sends, status, stop] of [
    [9_999, 1, 'loaded', null],
    [10_000, 2, 'loaded', 30_000],
  ] as const) {
    it(`a head at 10 s and a body ${endsAfter} ms later: ${sends === 1 ? 'one batch, no stop' : 'a stop, and the batch goes again'}`, async () => {
      const a = bodyFetch({ endsAfter }, 10_000);
      const cache = createCardCache({ storage, limiter: createScryfallLimiter({ fetchImpl: a.fetchImpl, storage, locks: fakeLocks() }) });
      cache.enqueue('Late Body');
      await advance(20_000);
      expect(storedStop()?.ms ?? null).toBe(stop);
      await advance(60_000);
      expect(a.sends.map((s) => s.at)).toEqual(sends === 1 ? [0] : [0, 50_000]);
      expect(cache.get('Late Body')?.status).toBe(status);
    });
  }
});

describe('DEC-1188 B2: a body that fails before the deadline', () => {
  it("is the caller's to read: the lookup fails in the tab's memory only, and no stop starts", async () => {
    const a = bodyFetch({ failsAfter: 1_000 });
    const cache = createCardCache({ storage, limiter: createScryfallLimiter({ fetchImpl: a.fetchImpl, storage, locks: fakeLocks() }) });
    cache.enqueue('Broken Body');
    await advance(25_000);
    expect(a.sends).toHaveLength(1);
    expect(cache.get('Broken Body')).toMatchObject({ status: 'error', errorStatus: 0 });
    expect(storage.getItem('gv1-card:broken body')).toBeNull();
    expect(storedStop()).toBeNull();
  });
});

describe('DEC-1188 B3: fetch() gives the answer at its head', () => {
  it('resolves with a body that never ends, and starts no stop', async () => {
    const a = bodyFetch('never ends');
    const limiter = createScryfallLimiter({ fetchImpl: a.fetchImpl, storage, locks: fakeLocks() });
    const { method, headers, body } = collectionRequest(['Head Only']);
    let status: number | null = null;
    void limiter.fetch(COLLECTION_URL, { method, headers, body }).then((response) => (status = response.status));
    await advance(0);
    expect(status).toBe(200);
    await advance(30_000);
    expect(storedStop()).toBeNull();
    expect(a.sends).toHaveLength(1);
  });
});

describe('DEC-1188 B4: an answer of another status whose body never ends', () => {
  for (const status of [400, 422]) {
    it(`a ${status}: no answer at 20 s, a stop, and the batch goes again first`, async () => {
      const a = bodyFetch('never ends', 0, status);
      const cache = createCardCache({ storage, limiter: createScryfallLimiter({ fetchImpl: a.fetchImpl, storage, locks: fakeLocks() }) });
      cache.enqueue('Open Body');
      await advance(20_000 - 1);
      expect(storedStop()).toBeNull();
      await advance(1);
      expect(storedStop()).toMatchObject({ until: T0 + 50_000, ms: 30_000 });
      await advance(31_000);
      expect(a.sends.map((s) => s.at)).toEqual([0, 50_000]);
      expect(cache.get('Open Body')?.status).toBe('loaded');
    });
  }

  it('a 429: the stop starts at its head, as for any 429', async () => {
    const a = bodyFetch('never ends', 0, 429);
    const cache = createCardCache({ storage, limiter: createScryfallLimiter({ fetchImpl: a.fetchImpl, storage, locks: fakeLocks() }) });
    cache.enqueue('Open Body');
    await advance(0);
    expect(storedStop()).toMatchObject({ until: T0 + 30_000, ms: 30_000 });
    await advance(31_000);
    expect(a.sends.map((s) => s.at)).toEqual([0, 30_000]);
    expect(cache.get('Open Body')?.status).toBe('loaded');
  });
});
