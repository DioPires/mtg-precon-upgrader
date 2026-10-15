// DEC-1102, DEC-1131: the limiter that sends every request to api.scryfall.com,
// the batch of the card cache, and the 429 rule. Fake clock (Date and
// performance.now()), fake fetch; each case of the first block runs with answers
// after 0 ms and after 150 ms.

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createCardCache } from '../../data/cardCache';
import {
  autocompleteUrl,
  collectionRequest,
  COLLECTION_URL,
  createScryfallLimiter,
  LAST_START_KEY,
  STOP_KEY,
  type ScryfallLimiter,
  type SendOptions,
} from '../../data/scryfallLimiter';
import {
  cardJson,
  collectionJson,
  fakeLocks,
  fakeScryfall,
  gaps,
  MemoryStorage,
  peakInClosedWindow,
  type Outcome,
} from './scryfallFakes';

const T0 = Date.UTC(2026, 9, 14, 12, 0, 0);
const HOUR_MS = 3_600_000;
const NAMES_88 = Array.from({ length: 88 }, (_, i) => `Card ${String(i + 1).padStart(2, '0')}`);

let storage: MemoryStorage;

beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(T0);
  storage = new MemoryStorage();
});

afterEach(() => {
  vi.useRealTimers();
});

function setup(delayMs: number, outcome?: (n: number, url: string) => Outcome) {
  const scry = fakeScryfall({ delayMs, outcome });
  const limiter = createScryfallLimiter({ fetchImpl: scry.fetch, storage, locks: null });
  const cache = createCardCache({ storage, limiter });
  return { scry, limiter, cache };
}

/** The options of limiter.fetch() for one batch. */
function post(names: string[], signal?: AbortSignal): SendOptions {
  const { method, headers, body } = collectionRequest(names);
  return { method, headers, body, signal };
}

const advance = (ms: number) => vi.advanceTimersByTimeAsync(ms);
const storedStop = () => JSON.parse(storage.getItem(STOP_KEY) ?? 'null') as { until: number; ms: number; n: number } | null;

/** A fetch whose answers the case gives by hand, in any order. */
function manualFetch() {
  const sends: Array<{ url: string; at: number; signal?: AbortSignal; answer: (r: Response | Error) => void }> = [];
  const fetchImpl = ((input: RequestInfo | URL, init?: RequestInit) =>
    new Promise<Response>((resolve, reject) => {
      sends.push({
        url: String(input),
        at: Date.now(),
        signal: init?.signal ?? undefined,
        answer: (r) => (r instanceof Error ? reject(r) : resolve(r)),
      });
    })) as typeof fetch;
  return { sends, fetchImpl };
}
const status = (code: number) => new Response('{"object":"error"}', { status: code });
const batchOk = (names: string[]) => new Response(JSON.stringify(collectionJson(names)), { status: 200 });

describe.each([0, 150])('scryfallLimiter, answers after %i ms', (delay) => {
  it('sends 88 names outside the file in 2 POSTs of 75 and 13 names; at two starts a POST, no 1 s window holds more than 2', async () => {
    const { scry, cache } = setup(delay);
    NAMES_88.forEach((name) => cache.enqueue(name));
    await advance(10_000);

    expect(scry.sends.map((s) => [s.method, s.url, s.names.length])).toEqual([
      ['POST', COLLECTION_URL, 75],
      ['POST', COLLECTION_URL, 13],
    ]);
    expect(scry.names()).toEqual(NAMES_88);
    expect(gaps(scry.times())).toEqual([1_200]);
    // Each POST counts as two starts at its send time: the preflight and the POST.
    expect(peakInClosedWindow(scry.times().flatMap((t) => [t, t]))).toBeLessThanOrEqual(2);
    expect(NAMES_88.every((name) => cache.get(name)?.status === 'loaded')).toBe(true);
  });

  for (const failure of [429, 'reject', 'hang'] as const) {
    const label = failure === 429 ? 'a 429' : failure === 'reject' ? 'a rejected fetch' : 'no answer in 20 s';
    // The time from a send to its failure.
    const failsAfter = failure === 'hang' ? 20_000 : delay;

    it(`a batch that meets ${label} keeps its names first: 0 requests in 30 s, then the same batch, then the names that came in the stop`, async () => {
      const { scry, cache, limiter } = setup(delay, (n) => (n === 1 ? failure : 200));
      ['A1', 'A2', 'A3'].forEach((name) => cache.enqueue(name));
      await advance(failsAfter);
      const failedAt = T0 + failsAfter;
      expect(limiter.stoppedUntil()).toBe(failedAt + 30_000);
      // The names that met the stop are no errors: they wait, first.
      expect(cache.get('A1')?.status).toBe('loading');
      cache.enqueue('B1');

      await advance(failedAt + 30_000 - 1 - Date.now());
      expect(scry.sends).toHaveLength(1);
      await advance(1);
      expect(scry.sends).toHaveLength(2);
      await advance(5_000);
      expect(scry.batches()).toEqual([['A1', 'A2', 'A3'], ['A1', 'A2', 'A3'], ['B1']]);
      expect(scry.times()[1]).toBe(failedAt + 30_000);
      expect(scry.times()[2] - scry.times()[1]).toBe(1_200);
      expect(['A1', 'A2', 'A3', 'B1'].every((name) => cache.get(name)?.status === 'loaded')).toBe(true);
      expect(limiter.stoppedUntil()).toBeNull();
    });

    it(`after ${label}: the stop doubles to 300 s, and a success resets it to 30 s`, async () => {
      // Sends 1 to 6 fail (six stops), send 7 succeeds, send 9 fails again.
      const { scry, cache } = setup(delay, (n) => (n <= 6 || n === 9 ? failure : 200));
      cache.enqueue('A');
      await advance(40 * 60_000);
      const times = scry.times();
      // From each failure to the next start.
      const stops = [1, 2, 3, 4, 5, 6].map((n) => times[n] - (times[n - 1] + failsAfter));
      expect(stops).toEqual([30_000, 60_000, 120_000, 240_000, 300_000, 300_000]);
      expect(scry.batches()).toEqual(Array(7).fill(['A']));

      cache.enqueue('B');
      await advance(failsAfter + 5_000);
      cache.enqueue('C');
      await advance(failsAfter + 5_000 + 30_000);
      const after = scry.times();
      expect(scry.batches().slice(7)).toEqual([['B'], ['C'], ['C']]);
      expect(after[9] - (after[8] + failsAfter)).toBe(30_000);
    });
  }

  for (const code of [400, 422]) {
    it(`a ${code} fails the batch's names alone and starts no stop; nobody asks for them again inside 30 s`, async () => {
      const { scry, cache, limiter } = setup(delay, (n) => (n === 1 ? code : 200));
      cache.enqueue('Nonesuch');
      await advance(delay);
      cache.enqueue('Sol Ring');
      await advance(1_200);
      expect(scry.batches()).toEqual([['Nonesuch'], ['Sol Ring']]);
      expect(scry.times()[1] - scry.times()[0]).toBe(1_200);
      expect(limiter.stoppedUntil()).toBeNull();
      expect(storage.getItem(STOP_KEY)).toBeNull();
      expect(cache.get('Nonesuch')).toMatchObject({ status: 'error', errorStatus: code });

      await advance(10_000);
      cache.enqueue('Nonesuch');
      await advance(2_000);
      expect(scry.sends).toHaveLength(2);
      await advance(20_000);
      cache.enqueue('Nonesuch');
      await advance(delay);
      expect(scry.batches()).toEqual([['Nonesuch'], ['Sol Ring'], ['Nonesuch']]);
    });
  }

  it('a new cache instance reads the stop from storage and sends nothing until its end', async () => {
    const scry = fakeScryfall({ delayMs: delay, outcome: (n) => (n === 1 ? 429 : 200) });
    const first = createScryfallLimiter({ fetchImpl: scry.fetch, storage, locks: null });
    const tab = new AbortController();
    const out = first.fetch(COLLECTION_URL, post(['Sol Ring'], tab.signal)).catch(() => 'closed');
    await advance(delay);
    const failedAt = Date.now();
    // The first page goes away; its request leaves with it.
    tab.abort();
    expect(await out).toBe('closed');

    // A reload: a new limiter and a new cache, on the same storage.
    const second = createCardCache({
      storage,
      limiter: createScryfallLimiter({ fetchImpl: scry.fetch, storage, locks: null }),
    });
    await advance(1_000);
    second.enqueue('Mana Crypt');
    await advance(failedAt + 30_000 - 1 - Date.now());
    expect(scry.sends).toHaveLength(1);
    await advance(1);
    expect(scry.batches()).toEqual([['Sol Ring'], ['Mana Crypt']]);
  });

  it('the hover and the commander art go first in the next batch', async () => {
    const { scry, cache } = setup(delay);
    ['Q1', 'Q2', 'Q3'].forEach((name) => cache.enqueue(name));
    await advance(0);
    cache.enqueue('Art Card', { first: true });
    cache.enqueue('Q4');
    cache.enqueue('Hover Card', { first: true });
    await advance(10_000);
    expect(scry.batches()).toEqual([['Q1', 'Q2', 'Q3'], ['Hover Card', 'Art Card', 'Q4']]);
    expect(Math.min(...gaps(scry.times()))).toBeGreaterThanOrEqual(1_200);
  });

  it('bucket 2 keeps 120 ms between starts, and a stop holds it', async () => {
    const { scry, limiter, cache } = setup(delay, (n) => (n === 6 ? 429 : 200));
    const answers = ['so', 'sol', 'sol r', 'sol ri', 'sol rin'].map((q) => limiter.fetch(autocompleteUrl(q)));
    await advance(1_000);
    await Promise.all(answers);
    expect(gaps(scry.times())).toEqual([120, 120, 120, 120]);

    // A batch meets a 429, and the stop holds bucket 2 too.
    cache.enqueue('Sol Ring');
    await advance(delay);
    const failedAt = Date.now();
    expect(limiter.stoppedUntil()).toBe(failedAt + 30_000);
    const suggest = limiter.fetch(autocompleteUrl('mana'));
    await advance(30_000 - 1);
    expect(scry.sends).toHaveLength(6);
    await advance(1_000);
    await suggest;
    expect(scry.names().slice(5)).toEqual(['Sol Ring', 'Sol Ring', 'mana']);
    expect(scry.times()[6]).toBe(failedAt + 30_000);
    // After the stop, one request goes and its answer comes before the next start.
    expect(scry.times()[7]).toBeGreaterThanOrEqual(scry.times()[6] + delay);
  });

  it('a request that the caller aborts starts no stop', async () => {
    const { scry, limiter } = setup(delay);
    // Aborted while it waits for its turn: it never goes.
    const waiting = new AbortController();
    const a = limiter.fetch(autocompleteUrl('sol'));
    const b = limiter.fetch(autocompleteUrl('sol r'), { signal: waiting.signal });
    waiting.abort();
    await expect(b).rejects.toThrow();
    await advance(1_000);
    await a;
    expect(scry.names()).toEqual(['sol']);
    expect(limiter.stoppedUntil()).toBeNull();
    expect(storage.getItem(STOP_KEY)).toBeNull();
  });

  // Delta N4 of the PR #38 review: the spacing inside a tab runs on performance.now().
  it('delta N4: a forward step of 1 s of the wall clock, 50 ms after the first send, leaves 1,200 ms to the next', async () => {
    const { scry, cache } = setup(delay);
    cache.enqueue('A');
    await advance(50);
    vi.setSystemTime(Date.now() + 1_000);
    cache.enqueue('B');
    await advance(5_000);
    expect(scry.batches()).toEqual([['A'], ['B']]);
    expect(scry.sends[1].elapsed - scry.sends[0].elapsed).toBe(1_200);
  });
});

describe('scryfallLimiter', () => {
  it('aborts a request in flight without a stop', async () => {
    const { scry, limiter } = setup(150);
    const typing = new AbortController();
    const out = limiter.fetch(autocompleteUrl('sol'), { signal: typing.signal });
    await advance(50);
    typing.abort();
    await expect(out).rejects.toThrow(/abort/i);
    expect(limiter.stoppedUntil()).toBeNull();
    const next = limiter.fetch(autocompleteUrl('sol ring'));
    await advance(70 + 150);
    await next;
    expect(gaps(scry.times())).toEqual([120]);
  });

  it('sends the method, the headers and the body that the caller gives', async () => {
    const { fetchImpl } = manualFetch();
    const spy = vi.fn(fetchImpl);
    const limiter = createScryfallLimiter({ fetchImpl: spy as typeof fetch, storage, locks: null });
    void limiter.fetch(COLLECTION_URL, post(['Sol Ring']));
    await advance(0);
    expect(spy).toHaveBeenCalledTimes(1);
    expect(String(spy.mock.calls[0][0])).toBe(COLLECTION_URL);
    const init = spy.mock.calls[0][1]!;
    expect(init.method).toBe('POST');
    expect(init.headers).toEqual({ 'Content-Type': 'application/json' });
    expect(JSON.parse(String(init.body))).toEqual({ identifiers: [{ name: 'Sol Ring' }] });
  });

  it('starts no bucket 1 request while an answer is out', async () => {
    // Three callers at once: the cache hands over one batch at a time, so the
    // limiter itself must hold the other callers.
    const { scry, limiter, cache } = setup(2_000);
    const direct = [limiter.fetch(COLLECTION_URL, post(['A'])), limiter.fetch(COLLECTION_URL, post(['B']))];
    cache.enqueue('C');
    await advance(10_000);
    await Promise.all(direct);
    expect(scry.batches()).toEqual([['A'], ['B'], ['C']]);
    expect(gaps(scry.times())).toEqual([2_000, 2_000]);
  });

  it('two tabs share bucket 1 through navigator.locks and the last start in storage', async () => {
    const scry = fakeScryfall({ delayMs: 150 });
    const locks = fakeLocks();
    const tabs = [0, 1].map(() =>
      createCardCache({ storage, limiter: createScryfallLimiter({ fetchImpl: scry.fetch, storage, locks }) }),
    );
    for (let i = 0; i < 80; i += 1) {
      tabs[0].enqueue(`Left ${i}`);
      tabs[1].enqueue(`Right ${i}`);
    }
    await advance(4 * 1_200 + 2_000);
    expect(scry.sends.map((s) => s.names.length).sort((a, b) => a - b)).toEqual([5, 5, 75, 75]);
    expect(Math.min(...gaps(scry.times()))).toBeGreaterThanOrEqual(1_200);
    expect(Number(storage.getItem(LAST_START_KEY))).toBe(scry.times()[3]);
  });

  it('reports the end of the stop to a reader and to subscribers', async () => {
    const { limiter, cache } = setup(0, (n) => (n === 1 ? 429 : 200));
    const heard: Array<number | null> = [];
    const unsubscribe = limiter.subscribe((until) => heard.push(until));
    cache.enqueue('Sol Ring');
    await advance(0);
    expect(limiter.stoppedUntil()).toBe(T0 + 30_000);
    expect(storedStop()).toEqual({ until: T0 + 30_000, ms: 30_000, n: expect.any(Number) });
    await advance(30_000);
    expect(limiter.stoppedUntil()).toBeNull();
    expect(heard).toEqual([T0 + 30_000, null]);
    unsubscribe();
  });

  it('keeps the stop in memory when there is no storage', async () => {
    const scry = fakeScryfall({ outcome: (n) => (n === 1 ? 'reject' : 200) });
    const limiter: ScryfallLimiter = createScryfallLimiter({ fetchImpl: scry.fetch, storage: null, locks: null });
    const out = limiter.fetch(COLLECTION_URL, post(['Sol Ring']));
    await advance(0);
    expect(limiter.stoppedUntil()).toBe(T0 + 30_000);
    await advance(30_000);
    await out;
    expect(gaps(scry.times())).toEqual([30_000]);
  });

  it('refuses an address on another host', async () => {
    const { limiter } = setup(0);
    await expect(limiter.fetch('https://cards.scryfall.io/large/front/x.jpg')).rejects.toThrow(TypeError);
  });

  // DEC-1110 B1: a clock that went back. The cap is written back on the first
  // read, so it holds when the clock moves on.
  it('a stored stop 10 h ahead with `ms` 30 s lets the next request go at T0 + 30 s', async () => {
    storage.setItem(STOP_KEY, JSON.stringify({ until: T0 + 10 * HOUR_MS, ms: 30_000, n: 5 }));
    const { scry, limiter, cache } = setup(0);
    cache.enqueue('Sol Ring');
    const readings = [limiter.stoppedUntil()];
    const stored = storedStop();
    await advance(10_000);
    readings.push(limiter.stoppedUntil());
    await advance(20_000 - 1);
    const sentBefore = scry.sends.length;
    await advance(10 * HOUR_MS);

    expect(sentBefore).toBe(0);
    expect(scry.times()[0] - T0).toBe(30_000);
    expect(readings).toEqual([T0 + 30_000, T0 + 30_000]);
    expect(stored).toEqual({ until: T0 + 30_000, ms: 30_000, n: 5 });
  });

  it('a stored last start 1 h ahead lets the next batch go at T0 + 1,200 ms', async () => {
    storage.setItem(LAST_START_KEY, String(T0 + HOUR_MS));
    const { scry, cache } = setup(0);
    cache.enqueue('Sol Ring');
    await advance(1_200 - 1);
    const sentBefore = scry.sends.length;
    await advance(HOUR_MS + 1_000);

    expect(sentBefore).toBe(0);
    expect(scry.times()[0] - T0).toBe(1_200);
    expect(Number(storage.getItem(LAST_START_KEY))).toBeLessThanOrEqual(T0 + 1_200);
  });
});

// N3 of the PR #38 review: a request with no answer.
describe('N3: the 20 s timeout', () => {
  it('aborts a request that has no answer after 20 s; that starts the stop, and the batch goes again after it', async () => {
    const { sends, fetchImpl } = manualFetch();
    const limiter = createScryfallLimiter({ fetchImpl, storage, locks: null });
    const cache = createCardCache({ storage, limiter });
    cache.enqueue('A');
    await advance(20_000 - 1);
    expect(sends[0].signal?.aborted).toBe(false);
    expect(limiter.stoppedUntil()).toBeNull();
    await advance(1);
    expect(sends[0].signal?.aborted).toBe(true);
    expect(limiter.stoppedUntil()).toBe(T0 + 20_000 + 30_000);
    expect(cache.get('A')?.status).toBe('loading');
    await advance(30_000 - 1);
    expect(sends).toHaveLength(1);
    await advance(1);
    expect(sends).toHaveLength(2);
    sends[1].answer(batchOk(['A']));
    await advance(0);
    expect(cache.get('A')?.status).toBe('loaded');
    expect(limiter.stoppedUntil()).toBeNull();
  });

  it('a request that never answers holds bucket 1 of the other tab for 20 s, not for ever', async () => {
    const scry = fakeScryfall({ outcome: (n) => (n === 1 ? 'hang' : 200) });
    const locks = fakeLocks();
    const [left, right] = [0, 1].map(() =>
      createCardCache({ storage, limiter: createScryfallLimiter({ fetchImpl: scry.fetch, storage, locks }) }),
    );
    left.enqueue('L');
    await advance(0);
    right.enqueue('R');
    await advance(20_000 + 30_000 - 1);
    expect(scry.batches()).toEqual([['L']]);
    await advance(1 + 1_200 + 100);
    expect(scry.batches()).toEqual([['L'], ['R'], ['L']]);
    expect(scry.times().map((t) => t - T0)).toEqual([0, 50_000, 51_200]);
  });

  it("the caller's own abort is no failure", async () => {
    const { sends, fetchImpl } = manualFetch();
    const limiter = createScryfallLimiter({ fetchImpl, storage, locks: null });
    const caller = new AbortController();
    const out = limiter.fetch(COLLECTION_URL, post(['A'], caller.signal));
    await advance(5_000);
    caller.abort();
    sends[0].answer(new DOMException('aborted', 'AbortError'));
    await expect(out).rejects.toThrow(/abort/i);
    await advance(30_000);
    expect(limiter.stoppedUntil()).toBeNull();
    expect(storage.getItem(STOP_KEY)).toBeNull();
  });
});

// N4 of the PR #38 review: an old stop record goes.
describe('N4: a stop record that ended long ago', () => {
  for (const [endedAgo, expected] of [[301_000, 30_000], [299_000, 120_000]] as const) {
    it(`a record of 60 s that ended ${endedAgo / 1000} s ago: the next failure stops for ${expected / 1000} s`, async () => {
      storage.setItem(STOP_KEY, JSON.stringify({ until: T0 - endedAgo, ms: 60_000, n: 3 }));
      const { cache, limiter } = setup(0, () => 429);
      cache.enqueue('A');
      await advance(0);
      expect(storedStop()).toMatchObject({ until: T0 + expected, ms: expected });
      expect(limiter.stoppedUntil()).toBe(T0 + expected);
    });
  }
});

// Delta N1 of the PR #38 review: the cap holds for a stop in memory.
describe('delta N1: a stop in memory after the clock goes back 10 h', () => {
  class RefusingStorage extends MemoryStorage {
    setItem(k: string, v: string): void {
      if (k === STOP_KEY) throw new DOMException('full', 'QuotaExceededError');
      super.setItem(k, v);
    }
  }
  for (const [label, make] of [
    ['no storage', () => null],
    ['a storage that refuses the write', () => new RefusingStorage()],
  ] as const) {
    it(`with ${label}: the stop ends 30 s after the jump, not 10 h later`, async () => {
      const scry = fakeScryfall({ outcome: (n) => (n === 1 ? 429 : 200) });
      const limiter = createScryfallLimiter({ fetchImpl: scry.fetch, storage: make(), locks: null });
      const cache = createCardCache({ storage: null, limiter });
      cache.enqueue('A');
      await advance(0);
      expect(limiter.stoppedUntil()).toBe(T0 + 30_000);
      const back = T0 - 10 * HOUR_MS;
      vi.setSystemTime(back);
      expect(limiter.stoppedUntil()).toBe(back + 30_000);
      await advance(30_000 - 1);
      expect(scry.sends).toHaveLength(1);
      // The last start in storage lies ahead after the jump too, so the batch
      // may wait one spacing more.
      await advance(1 + 1_200);
      expect(scry.batches()).toEqual([['A'], ['A']]);
      expect(scry.times()[1] - back).toBeLessThanOrEqual(30_000 + 1_200);
      expect(cache.get('A')?.status).toBe('loaded');
    });
  }
});

// Delta N3 of the PR #38 review: the stop number. The clock jumps back by more
// than the stop's length while a request that started before the stop is out.
describe('delta N3: only the request that went after a stop can double or end it', () => {
  it('K1: a 429 from a request that was out when the stop started does not double it', async () => {
    const { sends, fetchImpl } = manualFetch();
    const limiter = createScryfallLimiter({ fetchImpl, storage, locks: null });
    void limiter.fetch(autocompleteUrl('sol')).catch(() => undefined);
    void limiter.fetch(autocompleteUrl('sol r')).catch(() => undefined);
    await advance(120);
    expect(sends).toHaveLength(2);
    sends[0].answer(status(429));
    await advance(0);
    const first = storedStop()!;
    expect(first).toMatchObject({ until: T0 + 120 + 30_000, ms: 30_000 });
    vi.setSystemTime(T0 - 10 * HOUR_MS);
    sends[1].answer(status(429));
    await advance(0);
    expect(storedStop()).toEqual({ until: T0 - 10 * HOUR_MS + 30_000, ms: 30_000, n: first.n });
  });

  it('K2: a success of a request that was out when the stop started does not end it', async () => {
    const { sends, fetchImpl } = manualFetch();
    const limiter = createScryfallLimiter({ fetchImpl, storage, locks: null });
    const lookup = limiter.fetch(COLLECTION_URL, post(['Sol Ring']));
    void limiter.fetch(autocompleteUrl('sol')).catch(() => undefined);
    await advance(0);
    const sent = (path: string) => sends.find((s) => new URL(s.url).pathname === path)!;
    sent('/cards/autocomplete').answer(status(429));
    await advance(0);
    expect(limiter.stoppedUntil()).toBe(T0 + 30_000);
    vi.setSystemTime(T0 - 10 * HOUR_MS);
    sent('/cards/collection').answer(batchOk(['Sol Ring']));
    await lookup;
    expect(limiter.stoppedUntil()).toBe(T0 - 10 * HOUR_MS + 30_000);
    expect(storedStop()).toMatchObject({ ms: 30_000 });
  });

  it('the request that went after the stop doubles it, and its success ends it', async () => {
    const { sends, fetchImpl } = manualFetch();
    const limiter = createScryfallLimiter({ fetchImpl, storage, locks: null });
    const cache = createCardCache({ storage, limiter });
    cache.enqueue('A');
    await advance(0);
    sends[0].answer(status(429));
    await advance(30_000);
    expect(sends).toHaveLength(2);
    sends[1].answer(status(429));
    await advance(0);
    expect(storedStop()).toMatchObject({ until: T0 + 30_000 + 60_000, ms: 60_000 });
    await advance(60_000);
    sends[2].answer(batchOk(['A']));
    await advance(0);
    expect(storedStop()).toBeNull();
    expect(cache.get('A')).toMatchObject({ status: 'loaded', name: cardJson('A').name });
  });
});
