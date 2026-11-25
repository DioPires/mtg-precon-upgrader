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
  indexedDbTurns,
  LAST_START_KEY,
  STOP_KEY,
  TURN_KEY,
  type ScryfallLimiter,
  type SendOptions,
  type TurnStore,
} from '../../data/scryfallLimiter';
import {
  cardJson,
  collectionJson,
  CountingEvents,
  fakeIndexedDb,
  fakeLocks,
  fakeScryfall,
  fakeTurns,
  gaps,
  laggingStorages,
  MemoryStorage,
  peakInClosedWindow,
  turnDb,
  type FakeScryfall,
  type LaggingTab,
  type Outcome,
  type TurnDb,
  type TurnTiming,
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

// DEC-1153 (N5 of DEC-1149): bucket 1 frees its lock only after the caller has
// stored the answer, so the other tab's batch finds those names in storage. The
// lock frees 20 s after the start at the latest.
describe('DEC-1153: bucket 1 holds its lock until the answer is stored', () => {
  const NAMES_16 = Array.from({ length: 16 }, (_, i) => `Held ${i + 1}`);

  it('two tabs ask for the same 16 names, and the body of the answer takes 1,500 ms: each name goes once', async () => {
    const sends: Array<{ at: number; names: string[] }> = [];
    // The answer's head comes at once; its body ends 1,500 ms later.
    const fetchImpl = (async (_url: string, init?: RequestInit) => {
      const names = (JSON.parse(String(init?.body)) as { identifiers: Array<{ name: string }> }).identifiers.map((id) => id.name);
      sends.push({ at: Date.now() - T0, names });
      const bytes = new TextEncoder().encode(JSON.stringify(collectionJson(names)));
      const body = new ReadableStream<Uint8Array>({
        start(controller) {
          setTimeout(() => {
            controller.enqueue(bytes);
            controller.close();
          }, 1_500);
        },
      });
      return new Response(body, { status: 200 });
    }) as unknown as typeof fetch;
    const locks = fakeLocks();
    const tabs = [0, 1].map(() =>
      createCardCache({ storage, limiter: createScryfallLimiter({ fetchImpl, storage, locks }) }),
    );
    for (const tab of tabs) NAMES_16.forEach((name) => tab.enqueue(name));
    await advance(10_000);
    expect(sends).toEqual([{ at: 0, names: NAMES_16 }]);
    for (const tab of tabs) {
      expect(NAMES_16.map((name) => tab.get(name)?.status)).toEqual(NAMES_16.map(() => 'loaded'));
    }
  });

  it('next() resolves with the answer after `settle` has run, and leaves no timer', async () => {
    const { sends, fetchImpl } = manualFetch();
    const limiter = createScryfallLimiter({ fetchImpl, storage, locks: fakeLocks() });
    const order: string[] = [];
    const out = limiter
      .next('lookup', () => collectionRequest(['A']), {
        settle: async ({ response }) => {
          await new Promise((resolve) => setTimeout(resolve, 500));
          order.push(`settled ${response.status}`);
        },
      })
      .then((sent) => {
        order.push('resolved');
        return sent;
      });
    await advance(0);
    sends[0].answer(batchOk(['A']));
    await advance(499);
    expect(order).toEqual([]);
    await advance(1);
    expect(order).toEqual(['settled 200', 'resolved']);
    expect((await out)?.url).toBe(COLLECTION_URL);
    expect(vi.getTimerCount()).toBe(0);
  });

  it("a caller that never settles frees the other tab's turn 20 s after its own start", async () => {
    const scry = fakeScryfall({ delayMs: 150 });
    const locks = fakeLocks();
    const [left, right] = [0, 1].map(() => createScryfallLimiter({ fetchImpl: scry.fetch, storage, locks }));
    let leftDone = false;
    void left
      .next('lookup', () => collectionRequest(['L']), { settle: () => new Promise<void>(() => undefined) })
      .then(() => (leftDone = true));
    await advance(0);
    const rightOut = right.fetch(COLLECTION_URL, post(['R']));
    await advance(20_000 - 1);
    expect(scry.batches()).toEqual([['L']]);
    await advance(1);
    expect(scry.batches()).toEqual([['L'], ['R']]);
    expect(scry.times().map((t) => t - T0)).toEqual([0, 20_000]);
    await advance(150);
    expect((await rightOut).status).toBe(200);
    expect(leftDone).toBe(false);
    expect(storedStop()).toBeNull();
  });

  it('a `settle` that throws rejects next() and frees the turn at once, with no stop', async () => {
    const scry = fakeScryfall({ delayMs: 150 });
    const locks = fakeLocks();
    const [left, right] = [0, 1].map(() => createScryfallLimiter({ fetchImpl: scry.fetch, storage, locks }));
    const leftOut = left.next('lookup', () => collectionRequest(['L']), {
      settle: () => {
        throw new Error('the cache could not store it');
      },
    });
    const caught = leftOut.catch((err: Error) => err.message);
    await advance(0);
    const rightOut = right.fetch(COLLECTION_URL, post(['R']));
    await advance(1_200 + 150);
    expect(await caught).toBe('the cache could not store it');
    expect(scry.times().map((t) => t - T0)).toEqual([0, 1_200]);
    expect((await rightOut).status).toBe(200);
    expect(storedStop()).toBeNull();
  });
});

// The hand-over: Chrome and WebKit bring one tab's localStorage writes to
// another tab late, after the lock has passed to it (the two-tab e2e case of
// dec1153-card-data-followups.spec.ts, 2026-11-24). Each tab here reads its own
// copy of storage, which gets the other tabs' writes 5 ms late, in order
// (laggingStorages), and the tabs share one turn store (fakeTurns over one
// turnDb), whose operations keep IndexedDB's order. The allowance of a turn is
// 1,000 ms; bucket 1 spaces starts 1,200 ms.
describe('the hand-over: the next holder of bucket 1 reads what the last one wrote', () => {
  const NAMES_16 = Array.from({ length: 16 }, (_, i) => `Held ${i + 1}`);
  const LOCK = 'grimoire-scryfall-bucket-1';
  type Timing = { read?: TurnTiming; write?: TurnTiming; ready?: () => boolean };

  /** A card cache per tab, over its own lagging storage, sharing the locks and `db`. */
  function cacheTabs(scry: FakeScryfall, db: TurnDb, tabs: LaggingTab[], timings: Timing[] = []) {
    const locks = fakeLocks();
    const caches = tabs.map(({ storage: own, events }, i) =>
      createCardCache({
        storage: own,
        limiter: createScryfallLimiter({ fetchImpl: scry.fetch, storage: own, locks, events, turns: fakeTurns(db, timings[i]) }),
      }),
    );
    return { caches, locks };
  }

  /** One tab's limiter over `own` storage and `turns`. */
  function oneTab(scry: FakeScryfall, turns: TurnStore, own: Storage | null = storage, monotonic?: () => number) {
    const locks = fakeLocks();
    const events = new CountingEvents();
    const limiter = createScryfallLimiter({ fetchImpl: scry.fetch, storage: own, locks, events, turns, monotonic });
    return { limiter, locks, events };
  }

  /** The time (ms after T0) at which the limiter's lock comes free for a holder that asks now. */
  function lockFreesAt(locks: LockManager): { at: number | null } {
    const probe: { at: number | null } = { at: null };
    void locks.request(LOCK, async () => {
      probe.at = Date.now() - T0;
    });
    return probe;
  }

  it('two tabs ask for the same 16 names: each name goes once; the second holder frees the lock 5 ms after the first, when the mark arrives, and leaves no listener or timer', async () => {
    const scry = fakeScryfall({ delayMs: 1_500 });
    const db = turnDb();
    const tabs = laggingStorages(5);
    const { caches, locks } = cacheTabs(scry, db, tabs);
    for (const cache of caches) NAMES_16.forEach((name) => cache.enqueue(name));
    await advance(0);
    const probe = lockFreesAt(locks);
    // The first turn ends at 1,500 ms with the answer; its mark reaches the other tab at 1,505.
    await advance(1_504);
    expect(probe.at).toBeNull();
    await advance(1);
    expect(probe.at).toBe(1_505);
    await advance(10_000);
    expect(scry.batches()).toEqual([NAMES_16]);
    // Only the turn that sent a request wrote a token.
    expect(db.landed).toHaveLength(1);
    for (const cache of caches) {
      expect(NAMES_16.map((name) => cache.get(name)?.status)).toEqual(NAMES_16.map(() => 'loaded'));
    }
    expect(tabs.map((tab) => tab.events.listening)).toEqual([0, 0]);
    expect(vi.getTimerCount()).toBe(0);
  });

  it("a store whose writes take 50 ms: the first holder keeps the lock until its write commits at 1,550 ms, and the next holder's batch finds every name", async () => {
    const scry = fakeScryfall({ delayMs: 1_500 });
    const db = turnDb();
    const {
      caches: [first, second],
      locks,
    } = cacheTabs(scry, db, laggingStorages(5), [{ write: 50 }, { write: 50 }]);
    NAMES_16.forEach((name) => first.enqueue(name));
    await advance(0);
    // Asked before the second tab asks: it comes free when the first holder frees the lock.
    const probe = lockFreesAt(locks);
    NAMES_16.forEach((name) => second.enqueue(name));
    // The answer at 1,500 ms; the write commits 50 ms later.
    await advance(1_549);
    expect(probe.at).toBeNull();
    await advance(1);
    expect(probe.at).toBe(1_550);
    await advance(10_000);
    expect(scry.batches()).toEqual([NAMES_16]);
    expect(db.landed).toHaveLength(1);
  });

  it('a store whose write never settles: the lock frees at the end of the allowance, the hand-over goes off, and the next turn goes without it (sends at 0 and 1,200 ms)', async () => {
    const scry = fakeScryfall();
    const db = turnDb();
    const turns = fakeTurns(db, { write: 'never' });
    const { limiter } = oneTab(scry, turns);
    const outs = [limiter.fetch(COLLECTION_URL, post(['A'])), limiter.fetch(COLLECTION_URL, post(['B']))];
    await advance(5_000);
    await Promise.all(outs);
    expect(scry.times().map((t) => t - T0)).toEqual([0, 1_200]);
    expect({ reads: db.reads, writes: db.writes, landed: db.landed, closed: turns.closed }).toEqual({
      reads: 1,
      writes: 1,
      landed: [],
      closed: true,
    });
  });

  it('a read that answers at 900 ms and a mark that never comes: the request goes at 1,000 ms, the wait leaves no listener, the turn writes its token without waiting, and the next turn reads it and does not wait', async () => {
    const scry = fakeScryfall();
    const db = turnDb('a token no tab shows');
    const { limiter, events } = oneTab(scry, fakeTurns(db, { read: 900 }));
    const outs = [limiter.fetch(COLLECTION_URL, post(['A'])), limiter.fetch(COLLECTION_URL, post(['B']))];
    await advance(5_000);
    await Promise.all(outs);
    // The second turn: 1,200 ms after the first start, then its own 900 ms read.
    expect(scry.times().map((t) => t - T0)).toEqual([1_000, 3_100]);
    expect(db.reads).toBe(2);
    expect(db.landed).toHaveLength(2);
    expect(db.token).toBe(storage.getItem(TURN_KEY));
    expect(events.listening).toBe(0);
  });

  it('a mark that never comes, and a clock that leaves half a millisecond of the allowance: the end write is still the one nobody waits for, and the hand-over stays on', async () => {
    const scry = fakeScryfall();
    const db = turnDb('a token no tab shows');
    // The tab's clock reads 0.5 ms short once the allowance has run, as real timers can.
    const base = performance.now();
    const monotonic = () => {
      const t = performance.now();
      return t - base >= 1_000 ? t - 0.5 : t;
    };
    const { limiter } = oneTab(scry, fakeTurns(db, { write: 1 }), storage, monotonic);
    const outs = [limiter.fetch(COLLECTION_URL, post(['A'])), limiter.fetch(COLLECTION_URL, post(['B']))];
    await advance(5_000);
    await Promise.all(outs);
    expect(db.reads).toBe(2);
    expect(db.landed).toHaveLength(2);
  });

  it('a read that answers at 900 ms and a write that never settles: the lock frees at 1,000 ms', async () => {
    const scry = fakeScryfall();
    const turns = fakeTurns(turnDb(), { read: 900, write: 'never' });
    const { limiter, locks } = oneTab(scry, turns);
    void limiter.fetch(COLLECTION_URL, post(['A']));
    await advance(0);
    const probe = lockFreesAt(locks);
    await advance(5_000);
    expect(scry.times().map((t) => t - T0)).toEqual([900]);
    expect(probe.at).toBe(1_000);
    expect(turns.closed).toBe(true);
  });

  it('a read that blocks the tab 250 ms and then answers at 900 ms more: the request goes at 1,000 ms, and the hand-over goes off', async () => {
    const scry = fakeScryfall();
    let reads = 0;
    const turns: TurnStore = {
      read: () => {
        reads += 1;
        vi.advanceTimersByTime(250);
        return new Promise((resolve) => setTimeout(() => resolve('a token no tab shows'), 900));
      },
      write: async () => undefined,
      ready: () => true,
      close: () => undefined,
    };
    const { limiter } = oneTab(scry, turns);
    const outs = [limiter.fetch(COLLECTION_URL, post(['A'])), limiter.fetch(COLLECTION_URL, post(['B']))];
    await advance(5_000);
    await Promise.all(outs);
    expect(scry.times().map((t) => t - T0)).toEqual([1_000, 2_200]);
    expect(reads).toBe(1);
  });

  it('a read that holds the tab past the allowance and then answers at once counts as late: the hand-over goes off', async () => {
    const scry = fakeScryfall();
    // A call that blocks: the tab's clock moves 1,100 ms, and no timer can fire meanwhile.
    let blocked = 0;
    const monotonic = () => performance.now() + blocked;
    let reads = 0;
    const turns: TurnStore = {
      read: () => {
        reads += 1;
        blocked += 1_100;
        return Promise.resolve('a token no tab shows');
      },
      write: async () => undefined,
      ready: () => true,
      close: () => undefined,
    };
    const { limiter } = oneTab(scry, turns, storage, monotonic);
    const outs = [limiter.fetch(COLLECTION_URL, post(['A'])), limiter.fetch(COLLECTION_URL, post(['B']))];
    await advance(5_000);
    await Promise.all(outs);
    expect(reads).toBe(1);
  });

  it("a local mark that blocks the tab 250 ms and a write that never settles: the lock frees at 1,000 ms, the mark's time counted", async () => {
    class SlowMark extends MemoryStorage {
      setItem(k: string, v: string): void {
        if (k === TURN_KEY) vi.advanceTimersByTime(250);
        super.setItem(k, v);
      }
    }
    const scry = fakeScryfall();
    const turns = fakeTurns(turnDb(), { write: 'never' });
    const { limiter, locks } = oneTab(scry, turns, new SlowMark());
    void limiter.fetch(COLLECTION_URL, post(['A']));
    await advance(0);
    const probe = lockFreesAt(locks);
    await advance(5_000);
    expect(scry.times().map((t) => t - T0)).toEqual([0]);
    expect(probe.at).toBe(1_000);
    expect(turns.closed).toBe(true);
  });

  it('a write that does not settle in the allowance is aborted at the deadline, before the lock frees: it never lands', async () => {
    const scry = fakeScryfall();
    const db = turnDb();
    const store = fakeTurns(db, { write: 1_500 });
    const order: string[] = [];
    const turns: TurnStore = {
      ...store,
      write: (token, signal) => {
        signal.addEventListener('abort', () => order.push(`write aborted at ${Date.now() - T0}`));
        return store.write(token, signal);
      },
    };
    const { limiter, locks } = oneTab(scry, turns);
    void limiter.fetch(COLLECTION_URL, post(['A']));
    await advance(0);
    void locks.request(LOCK, async () => {
      order.push(`lock free at ${Date.now() - T0}`);
    });
    await advance(5_000);
    expect(order).toEqual(['write aborted at 1000', 'lock free at 1000']);
    expect({ writes: db.writes, landed: db.landed }).toEqual({ writes: 1, landed: [] });
  });

  it('a mark that never comes, and the connection that the read used has closed: the turn writes no token, and the hand-over goes off', async () => {
    const scry = fakeScryfall();
    const db = turnDb('a token no tab shows');
    const turns = fakeTurns(db, { ready: () => false });
    const { limiter } = oneTab(scry, turns);
    const outs = [limiter.fetch(COLLECTION_URL, post(['A'])), limiter.fetch(COLLECTION_URL, post(['B']))];
    await advance(5_000);
    await Promise.all(outs);
    expect(scry.times().map((t) => t - T0)).toEqual([1_000, 2_200]);
    expect({ mark: storage.getItem(TURN_KEY), reads: db.reads, writes: db.writes, closed: turns.closed }).toEqual({
      mark: null,
      reads: 1,
      writes: 0,
      closed: true,
    });
  });

  it('a write nobody waits for, still pending when the next turn turns the hand-over off: it never lands', async () => {
    const scry = fakeScryfall();
    const db = turnDb('a token no tab shows');
    // The first turn's mark never comes, so its write goes unwaited; it takes 3,000 ms,
    // and the second turn's read waits behind it past its own allowance.
    const turns = fakeTurns(db, { write: 3_000 });
    const { limiter } = oneTab(scry, turns);
    const outs = [limiter.fetch(COLLECTION_URL, post(['A'])), limiter.fetch(COLLECTION_URL, post(['B']))];
    await advance(10_000);
    await Promise.all(outs);
    expect(scry.times().map((t) => t - T0)).toEqual([1_000, 3_200]);
    expect({ writes: db.writes, landed: db.landed, closed: turns.closed }).toEqual({ writes: 1, landed: [], closed: true });
  });

  it.each([
    ['never settles', 'never' as const, [1_000, 2_200, 3_400]],
    ['fails', 'fail' as const, [0, 1_200, 2_400]],
  ])('a read that %s turns the hand-over off: the later turns read no store and do not wait', async (_label, read, sends) => {
    const scry = fakeScryfall();
    const db = turnDb('a token no tab shows');
    const turns = fakeTurns(db, { read });
    const { limiter } = oneTab(scry, turns);
    const outs = ['A', 'B', 'C'].map((name) => limiter.fetch(COLLECTION_URL, post([name])));
    await advance(10_000);
    await Promise.all(outs);
    expect(scry.times().map((t) => t - T0)).toEqual(sends);
    expect({ reads: db.reads, writes: db.writes, closed: turns.closed }).toEqual({ reads: 1, writes: 0, closed: true });
  });

  it('when localStorage refuses the mark while the store holds a token this tab does not show, the turn writes no token and the hand-over goes off: one wait, then none', async () => {
    class RefusesTheMark extends MemoryStorage {
      setItem(k: string, v: string): void {
        if (k === TURN_KEY) throw new DOMException('The quota is full.', 'QuotaExceededError');
        super.setItem(k, v);
      }
    }
    const own = new RefusesTheMark();
    // The last mark that reached this tab, and a store token that differs from it.
    MemoryStorage.prototype.setItem.call(own, TURN_KEY, 'the mark this tab shows');
    const scry = fakeScryfall();
    const db = turnDb('a token no tab shows');
    const turns = fakeTurns(db);
    const { limiter } = oneTab(scry, turns, own);
    const outs = ['A', 'B', 'C', 'D'].map((name) => limiter.fetch(COLLECTION_URL, post([name])));
    await advance(20_000);
    await Promise.all(outs);
    // The first turn waits its allowance for the mark; the later ones go 1,200 ms apart.
    expect(scry.times().map((t) => t - T0)).toEqual([1_000, 2_200, 3_400, 4_600]);
    expect({ reads: db.reads, writes: db.writes, closed: turns.closed }).toEqual({ reads: 1, writes: 0, closed: true });
  });

  it('when localStorage refuses the mark after the last mark came in time, the hand-over goes off too: no wait, then none', async () => {
    class RefusesTheMark extends MemoryStorage {
      setItem(k: string, v: string): void {
        if (k === TURN_KEY) throw new DOMException('The quota is full.', 'QuotaExceededError');
        super.setItem(k, v);
      }
    }
    const own = new RefusesTheMark();
    // This tab shows the store's token: the mark came.
    MemoryStorage.prototype.setItem.call(own, TURN_KEY, 'the last token');
    const scry = fakeScryfall();
    const db = turnDb('the last token');
    const turns = fakeTurns(db);
    const { limiter } = oneTab(scry, turns, own);
    const outs = ['A', 'B'].map((name) => limiter.fetch(COLLECTION_URL, post([name])));
    await advance(5_000);
    await Promise.all(outs);
    expect(scry.times().map((t) => t - T0)).toEqual([0, 1_200]);
    expect({ reads: db.reads, writes: db.writes, closed: turns.closed }).toEqual({ reads: 1, writes: 0, closed: true });
  });

  it('a first access to indexedDB that blocks the tab 250 ms, then an open that never ends: the request goes at 1,000 ms, not 1,250', async () => {
    const idb = fakeIndexedDb();
    idb.state.holdOpens = true;
    let blocked = false;
    Object.defineProperty(globalThis, 'indexedDB', {
      configurable: true,
      get() {
        if (!blocked) {
          blocked = true;
          vi.advanceTimersByTime(250);
        }
        return idb.factory;
      },
    });
    try {
      const scry = fakeScryfall();
      const limiter = createScryfallLimiter({ fetchImpl: scry.fetch, storage, locks: fakeLocks(), events: new CountingEvents() });
      const outs = [limiter.fetch(COLLECTION_URL, post(['A'])), limiter.fetch(COLLECTION_URL, post(['B']))];
      await advance(5_000);
      await Promise.all(outs);
      expect(scry.times().map((t) => t - T0)).toEqual([1_000, 2_200]);
      expect(idb.state.opens).toBe(1);
    } finally {
      delete (globalThis as { indexedDB?: unknown }).indexedDB;
    }
  });

  it('localStorage that blocks the tab 250 ms when the turn ends asks for it, then a write that never settles: the lock frees at 1,000 ms, not 1,250', async () => {
    // The page's own localStorage, through a getter that blocks once, when armed.
    const page = window.localStorage;
    for (const key of [LAST_START_KEY, STOP_KEY, TURN_KEY]) page.removeItem(key);
    let armed = false;
    Object.defineProperty(window, 'localStorage', {
      configurable: true,
      enumerable: true,
      get() {
        if (armed) {
          armed = false;
          vi.advanceTimersByTime(250);
        }
        return page;
      },
    });
    try {
      const scry = fakeScryfall();
      const turns = fakeTurns(turnDb(), { write: 'never' });
      const locks = fakeLocks();
      const limiter = createScryfallLimiter({ fetchImpl: scry.fetch, locks, events: new CountingEvents(), turns });
      // The answer is stored at 0 ms; the next access to localStorage is the turn's end.
      void limiter.next('lookup', () => collectionRequest(['A']), {
        settle: () => {
          armed = true;
        },
      });
      await advance(0);
      const probe = lockFreesAt(locks);
      await advance(5_000);
      expect(scry.times().map((t) => t - T0)).toEqual([0]);
      expect(probe.at).toBe(1_000);
      expect(turns.closed).toBe(true);
    } finally {
      Object.defineProperty(window, 'localStorage', { configurable: true, enumerable: true, value: page });
      for (const key of [LAST_START_KEY, STOP_KEY, TURN_KEY]) page.removeItem(key);
    }
  });

  it('the hand-over goes off while a turn reads (the last turn\'s unwaited write fails behind it): that turn does not wait for the mark', async () => {
    const scry = fakeScryfall();
    // The token no tab shows; each write fails 1,500 ms after it starts, and a read waits for any write before it.
    const db = turnDb('a token no tab shows');
    let pendingWrite: Promise<unknown> = Promise.resolve();
    let reads = 0;
    const store: TurnStore = {
      read: (signal) => {
        reads += 1;
        return pendingWrite.then(
          () =>
            new Promise<string | null>((resolve, reject) => {
              if (signal.aborted) return reject(signal.reason);
              resolve(db.token);
            }),
        );
      },
      write: () => {
        const written = new Promise<void>((_resolve, reject) =>
          setTimeout(() => reject(new DOMException('The disk is full.', 'QuotaExceededError')), 1_500),
        );
        pendingWrite = written.catch(() => undefined);
        return written;
      },
      ready: () => true,
      close: () => undefined,
    };
    const { limiter } = oneTab(scry, store);
    const outs = ['A', 'B', 'C'].map((name) => limiter.fetch(COLLECTION_URL, post([name])));
    await advance(10_000);
    await Promise.all(outs);
    // Turn 1: the mark never comes, the request at 1,000; its write fails at 2,500. Turn 2
    // begins at 2,200, and its read answers at 2,500, after the hand-over went off.
    expect(scry.times().map((t) => t - T0)).toEqual([1_000, 2_500, 3_700]);
    expect(reads).toBe(2);
  });

  it("a write nobody waits for that fails turns the hand-over off: the next turn reads no store and does not wait", async () => {
    const scry = fakeScryfall();
    const db = turnDb('a token no tab shows');
    const turns = fakeTurns(db, { write: 'fail' });
    const { limiter } = oneTab(scry, turns);
    const outs = [limiter.fetch(COLLECTION_URL, post(['A'])), limiter.fetch(COLLECTION_URL, post(['B']))];
    await advance(5_000);
    await Promise.all(outs);
    expect(scry.times().map((t) => t - T0)).toEqual([1_000, 2_200]);
    expect({ reads: db.reads, writes: db.writes, closed: turns.closed }).toEqual({ reads: 1, writes: 1, closed: true });
  });

  // A browser shows Scryfall's 429, which has no CORS header, as a rejected fetch.
  it.each([
    ['a 429', 429 as Outcome, 30_000],
    ['a rejected fetch', 'reject' as Outcome, 30_000],
    ['no answer in 20 s', 'hang' as Outcome, 20_000 + 30_000],
  ])('%s in one tab: the other tab, waiting for the lock, sees the stop and sends nothing until it ends', async (_label, first, stopEnds) => {
    const scry = fakeScryfall({ outcome: (n) => (n === 1 ? first : 200) });
    const db = turnDb();
    const locks = fakeLocks();
    const [one, other] = laggingStorages(5).map(({ storage: own, events }) =>
      createScryfallLimiter({ fetchImpl: scry.fetch, storage: own, locks, events, turns: fakeTurns(db) }),
    );
    const outOne = one.fetch(COLLECTION_URL, post(['A']));
    await advance(0);
    const outOther = other.fetch(COLLECTION_URL, post(['B']));
    await advance(stopEnds + 10_000);
    await Promise.all([outOne, outOther]);
    const times = scry.times().map((t) => t - T0);
    expect(times[0]).toBe(0);
    // The second send (the other tab's, or the first tab's again) goes when the stop ends, not 5 ms after the failure.
    expect(times[1]).toBeGreaterThanOrEqual(stopEnds);
  });

  it("a request that its caller aborts: the other tab's start comes 1,200 ms or more after it", async () => {
    const scry = fakeScryfall({ delayMs: 100 });
    const db = turnDb();
    const locks = fakeLocks();
    const [first, second] = laggingStorages(5).map(({ storage: own, events }) =>
      createScryfallLimiter({ fetchImpl: scry.fetch, storage: own, locks, events, turns: fakeTurns(db) }),
    );
    const controller = new AbortController();
    const outFirst = first.fetch(COLLECTION_URL, post(['A'], controller.signal)).catch(() => 'aborted');
    await advance(0);
    const outSecond = second.fetch(COLLECTION_URL, post(['B']));
    await advance(1);
    controller.abort();
    await advance(5_000);
    expect(await outFirst).toBe('aborted');
    await outSecond;
    const times = scry.times().map((t) => t - T0);
    expect(times[0]).toBe(0);
    expect(times[1]).toBeGreaterThanOrEqual(1_200);
  });

  it('when reading the mark throws, the turn has no hand-over: no store read, no wait, no token', async () => {
    class MarkUnreadable extends MemoryStorage {
      getItem(k: string): string | null {
        if (k === TURN_KEY) throw new DOMException('The storage is gone.', 'SecurityError');
        return super.getItem(k);
      }
    }
    const scry = fakeScryfall();
    const db = turnDb('a token no tab shows');
    const own = new MarkUnreadable();
    const { limiter } = oneTab(scry, fakeTurns(db), own);
    const outs = [limiter.fetch(COLLECTION_URL, post(['A'])), limiter.fetch(COLLECTION_URL, post(['B']))];
    await advance(5_000);
    await Promise.all(outs);
    expect(scry.times().map((t) => t - T0)).toEqual([0, 1_200]);
    expect({ reads: db.reads, writes: db.writes }).toEqual({ reads: 0, writes: 0 });
  });

  it('without localStorage the hand-over reads no store and waits for nothing', async () => {
    const scry = fakeScryfall();
    const db = turnDb('a token no tab shows');
    const { limiter } = oneTab(scry, fakeTurns(db), null);
    const out = limiter.fetch(COLLECTION_URL, post(['A']));
    await advance(2_000);
    expect((await out).status).toBe(200);
    expect(scry.times().map((t) => t - T0)).toEqual([0]);
    expect(db.reads).toBe(0);
  });

  it('an indexedDB that the browser denies (its getter throws): no hand-over, and the lookup goes', async () => {
    Object.defineProperty(globalThis, 'indexedDB', {
      configurable: true,
      get() {
        throw new DOMException('The user denied storage.', 'SecurityError');
      },
    });
    try {
      const scry = fakeScryfall();
      const limiter = createScryfallLimiter({ fetchImpl: scry.fetch, storage, locks: fakeLocks() });
      const out = limiter.fetch(COLLECTION_URL, post(['A']));
      await advance(0);
      expect(scry.times().map((t) => t - T0)).toEqual([0]);
      expect((await out).status).toBe(200);
    } finally {
      delete (globalThis as { indexedDB?: unknown }).indexedDB;
    }
  });

  it("a write that fails, then a healthy turn: the next holder waits for that turn's own token, and its batch finds every name", async () => {
    const scry = fakeScryfall({ delayMs: 1_500 });
    const db = turnDb();
    // The first tab's write fails (its hand-over goes off); the other two tabs' store is healthy.
    const {
      caches: [first, second, third],
    } = cacheTabs(scry, db, laggingStorages(5, 3), [{ write: 'fail' }]);
    first.enqueue('Alpha');
    await advance(2_000);
    NAMES_16.forEach((name) => second.enqueue(name));
    await advance(0);
    NAMES_16.forEach((name) => third.enqueue(name));
    await advance(10_000);
    expect(scry.batches()).toEqual([['Alpha'], NAMES_16]);
    expect(NAMES_16.map((name) => third.get(name)?.status)).toEqual(NAMES_16.map(() => 'loaded'));
  });

  it("a mark in localStorage that the store does not hold (the store's data lost) does not turn the wait off", async () => {
    const scry = fakeScryfall({ delayMs: 1_500 });
    const db = turnDb();
    const pair = laggingStorages(5);
    pair[0].storage.setItem(TURN_KEY, 'a token the store lost');
    await advance(10);
    expect(pair[1].storage.getItem(TURN_KEY)).toBe('a token the store lost');
    const { caches } = cacheTabs(scry, db, pair);
    for (const cache of caches) NAMES_16.forEach((name) => cache.enqueue(name));
    await advance(10_000);
    expect(scry.batches()).toEqual([NAMES_16]);
  });
});

// The IndexedDB side of the hand-over (indexedDbTurns), over a hand-written
// IndexedDB (fakeIndexedDb): jsdom has none. The e2e cases of
// dec1153-card-data-followups.spec.ts run it on the browsers' own.
describe('indexedDbTurns: the turn store in IndexedDB', () => {
  const never = () => new AbortController().signal;

  it('a first read creates the database and its store and gives null; a write, with relaxed durability, and a read give the token', async () => {
    const idb = fakeIndexedDb();
    const turns = indexedDbTurns(idb.factory)!;
    const first = turns.read(never());
    await advance(10);
    expect(await first).toBeNull();
    expect([...idb.state.stores]).toEqual(['turn']);
    const written = turns.write('t1', never());
    await advance(10);
    await written;
    const read = turns.read(never());
    await advance(10);
    expect(await read).toBe('t1');
    expect(idb.state.transactions.map((t) => [t.mode, t.durability])).toEqual([
      ['readonly', undefined],
      ['readwrite', 'relaxed'],
      ['readonly', undefined],
    ]);
  });

  it('on an open connection a write begins its transaction at once, before the caller frees the lock', async () => {
    const idb = fakeIndexedDb();
    const turns = indexedDbTurns(idb.factory)!;
    const read = turns.read(never());
    await advance(10);
    await read;
    expect(turns.ready()).toBe(true);
    void turns.write('t1', never());
    expect(idb.state.transactions.map((t) => t.mode)).toEqual(['readonly', 'readwrite']);
  });

  it('another tab upgrades the database to version 2: the connection closes, and the next operation, which opens version 1 again, fails with VersionError', async () => {
    const idb = fakeIndexedDb();
    const turns = indexedDbTurns(idb.factory)!;
    const read = turns.read(never());
    await advance(10);
    await read;
    idb.versionChange();
    expect(idb.state.connections.map((c) => c.closed)).toEqual([true]);
    expect(turns.ready()).toBe(false);
    const again = turns.read(never()).catch((e: DOMException) => e.name);
    await advance(10);
    expect(await again).toBe('VersionError');
    expect(idb.state.opens).toBe(2);
  });

  it('another tab upgrades the database between two turns: the next turn turns the hand-over off, and the turn after it uses no IndexedDB', async () => {
    const idb = fakeIndexedDb();
    const scry = fakeScryfall();
    const adapter = indexedDbTurns(idb.factory)!;
    // The limiter closes the store when the hand-over goes off.
    let closed = false;
    const turns: TurnStore = {
      ...adapter,
      close: () => {
        closed = true;
        adapter.close();
      },
    };
    const limiter = createScryfallLimiter({ fetchImpl: scry.fetch, storage, locks: fakeLocks(), events: new CountingEvents(), turns });
    const firstOut = limiter.fetch(COLLECTION_URL, post(['A']));
    await advance(10);
    await firstOut;
    idb.versionChange();
    const outs = [limiter.fetch(COLLECTION_URL, post(['B'])), limiter.fetch(COLLECTION_URL, post(['C']))];
    await advance(5_000);
    await Promise.all(outs);
    // The fake's opens and transactions each take one timer tick; the third turn takes none.
    const times = scry.times().map((t) => t - T0);
    expect(times).toHaveLength(3);
    expect(times[2] - times[1]).toBe(1_200);
    // The first turn's read and write; the second turn's failed open; nothing after.
    expect({ closed, opens: idb.state.opens, transactions: idb.state.transactions.map((t) => t.mode) }).toEqual({
      closed: true,
      opens: 2,
      transactions: ['readonly', 'readwrite'],
    });
  });

  it("the abort listener of a write goes when its transaction settles: aborting the write's signal after three writes touches none of them", async () => {
    const idb = fakeIndexedDb();
    const turns = indexedDbTurns(idb.factory)!;
    // One signal for every write, as the page's signal of the writes that nobody waits for.
    const page = new AbortController();
    for (const token of ['t1', 't2', 't3']) {
      const written = turns.write(token, page.signal);
      await advance(10);
      await written;
    }
    page.abort(new DOMException('The hand-over is off.', 'AbortError'));
    expect(idb.state.transactions.map((t) => [t.state, t.aborts])).toEqual([
      ['complete', 0],
      ['complete', 0],
      ['complete', 0],
    ]);
  });

  it("the abort listener goes also when the browser aborts a transaction, and when a request fails, as soon as its error arrives: aborting the writes' signal touches neither", async () => {
    const idb = fakeIndexedDb();
    const turns = indexedDbTurns(idb.factory)!;
    const opened = turns.read(never());
    await advance(10);
    await opened;
    const page = new AbortController();
    idb.state.holdTransactions = true;
    const settled = (written: Promise<void>) => written.then(() => 'landed', () => 'rejected');
    const aborted = settled(turns.write('t1', page.signal));
    idb.endTransactions('abort');
    expect(await aborted).toBe('rejected');
    const failed = settled(turns.write('t2', page.signal));
    idb.endTransactions('error');
    // The request's error has reached the transaction; its abort event has not come yet.
    page.abort(new DOMException('The hand-over is off.', 'AbortError'));
    await advance(10);
    expect(await failed).toBe('rejected');
    expect(idb.state.transactions.slice(1).map((t) => [t.state, t.aborts])).toEqual([
      ['aborted', 0],
      ['failed', 0],
    ]);
  });

  it('the browser closes the connection (site data cleared): the next operation opens again', async () => {
    const idb = fakeIndexedDb();
    const turns = indexedDbTurns(idb.factory)!;
    const read = turns.read(never());
    await advance(10);
    await read;
    idb.forceClose();
    expect(turns.ready()).toBe(false);
    const again = turns.write('t2', never());
    await advance(10);
    await again;
    expect(idb.state.opens).toBe(2);
    expect(idb.state.values.get('last')).toBe('t2');
  });

  it('an operation whose time ran out while the open waited is never issued', async () => {
    const idb = fakeIndexedDb();
    idb.state.holdOpens = true;
    const turns = indexedDbTurns(idb.factory)!;
    const controller = new AbortController();
    const write = turns.write('late', controller.signal).catch((e: DOMException) => e.name);
    await advance(10);
    controller.abort(new DOMException('out of time', 'TimeoutError'));
    idb.releaseOpens();
    await advance(10);
    expect(await write).toBe('TimeoutError');
    expect(idb.state.transactions).toEqual([]);
  });

  it('an abort before the transaction completes stops it: the write does not land', async () => {
    const idb = fakeIndexedDb();
    const turns = indexedDbTurns(idb.factory)!;
    const read = turns.read(never());
    await advance(10);
    await read;
    idb.state.holdTransactions = true;
    const controller = new AbortController();
    const write = turns.write('aborted', controller.signal).catch(() => 'rejected');
    controller.abort(new DOMException('out of time', 'TimeoutError'));
    idb.releaseTransactions();
    await advance(10);
    expect(await write).toBe('rejected');
    expect(idb.state.transactions.map((t) => t.state)).toEqual(['complete', 'aborted']);
    expect(idb.state.values.has('last')).toBe(false);
  });

  it.each([
    ['a new database: the upgrade is aborted and creates no store', false],
    ['a database that exists: the connection is closed at once', true],
  ])('close() while an open waits, then the open succeeds; %s', async (_label, exists) => {
    const idb = fakeIndexedDb();
    if (exists) {
      idb.state.stores.add('turn');
      idb.state.version = 1;
    }
    idb.state.holdOpens = true;
    const turns = indexedDbTurns(idb.factory)!;
    const read = turns.read(never()).catch((e: DOMException) => e.name);
    await advance(10);
    turns.close();
    idb.releaseOpens();
    await advance(10);
    expect(await read).toBe('AbortError');
    expect(idb.state.connections.map((c) => c.closed)).toEqual([true]);
    expect([...idb.state.stores]).toEqual(exists ? ['turn'] : []);
    expect(idb.state.transactions).toEqual([]);
  });
});
