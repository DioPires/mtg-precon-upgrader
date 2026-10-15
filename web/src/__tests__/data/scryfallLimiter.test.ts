// DEC-1102: the limiter that sends every request to api.scryfall.com, and the
// 429 rule. Fake clock, fake fetch; each case runs with answers after 0 ms and
// after 150 ms.

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createCardCache } from '../../data/cardCache';
import {
  autocompleteUrl,
  createScryfallLimiter,
  lookupUrl,
  LAST_START_KEY,
  STOP_KEY,
  type ScryfallLimiter,
} from '../../data/scryfallLimiter';
import {
  fakeLocks,
  fakeScryfall,
  gaps,
  MemoryStorage,
  peakInClosedWindow,
  type Outcome,
} from './scryfallFakes';

const T0 = Date.UTC(2026, 9, 14, 12, 0, 0);
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

const advance = (ms: number) => vi.advanceTimersByTimeAsync(ms);

describe.each([0, 150])('scryfallLimiter, answers after %i ms', (delay) => {
  it('sends 88 lookups with no 1 s window that holds more than 2 starts', async () => {
    const { scry, cache } = setup(delay);
    NAMES_88.forEach((name) => cache.enqueue(name));
    await advance(88 * 600 + 5_000);

    expect(scry.names()).toEqual(NAMES_88);
    expect(Math.min(...gaps(scry.times()))).toBeGreaterThanOrEqual(600);
    expect(peakInClosedWindow(scry.times())).toBeLessThanOrEqual(2);
    expect(NAMES_88.every((name) => cache.get(name)?.status === 'loaded')).toBe(true);
  });

  for (const failure of [429, 'reject'] as const) {
    const label = failure === 429 ? 'a 429' : 'a rejected fetch';
    it(`after ${label}: 0 requests in 30 s and then 1; the stop doubles to 300 s; a success resets it`, async () => {
      // Sends 3 to 8 fail (six stops), send 9 succeeds, send 11 fails again.
      const { scry, cache } = setup(delay, (n) => (n >= 3 && n <= 8) || n === 11 ? failure : 200);
      const names = Array.from({ length: 12 }, (_, i) => `Card ${i + 1}`);
      names.forEach((name) => cache.enqueue(name));

      await advance(1_200 + delay);
      expect(scry.sends).toHaveLength(3);
      const failedAt = scry.times()[2] + delay;
      await advance(failedAt + 30_000 - 1 - Date.now());
      expect(scry.sends).toHaveLength(3);
      // The card that met the stop is no error: it waits, first in the queue.
      expect(cache.get('Card 3')?.status).toBe('loading');
      await advance(1);
      expect(scry.sends).toHaveLength(4);

      await advance(30 * 60_000);
      const times = scry.times();
      // From each failed answer to the next start.
      const stops = [3, 4, 5, 6, 7, 8].map((n) => times[n] - (times[n - 1] + delay));
      expect(stops).toEqual([30_000, 60_000, 120_000, 240_000, 300_000, 300_000]);
      // The card that met the first stop goes again after each stop, and loads on send 9.
      expect(scry.names().slice(2, 9)).toEqual(Array(7).fill('Card 3'));
      expect(cache.get('Card 3')?.status).toBe('loaded');
      // After the success: the normal spacing, and the next failure stops for 30 s again.
      expect(times[9] - times[8]).toBe(600);
      expect(times[11] - (times[10] + delay)).toBe(30_000);
      expect(scry.names().slice(9)).toEqual(['Card 4', 'Card 5', 'Card 5', 'Card 6', 'Card 7', 'Card 8', 'Card 9', 'Card 10', 'Card 11', 'Card 12']);
    });
  }

  it('starts no stop on a 404: the card fails alone, and nobody asks for it again inside 30 s', async () => {
    const { scry, cache, limiter } = setup(delay, (n) => (n === 1 ? 404 : 200));
    cache.enqueue('Nonesuch');
    cache.enqueue('Sol Ring');
    await advance(600 + delay);
    expect(scry.names()).toEqual(['Nonesuch', 'Sol Ring']);
    expect(scry.times()[1] - scry.times()[0]).toBe(600);
    expect(limiter.stoppedUntil()).toBeNull();
    expect(storage.getItem(STOP_KEY)).toBeNull();
    expect(cache.get('Nonesuch')).toMatchObject({ status: 'error', errorStatus: 404 });

    await advance(10_000);
    cache.enqueue('Nonesuch');
    await advance(1_000);
    expect(scry.sends).toHaveLength(2);
    await advance(20_000);
    cache.enqueue('Nonesuch');
    await advance(delay);
    expect(scry.names()).toEqual(['Nonesuch', 'Sol Ring', 'Nonesuch']);
  });

  it('a new cache instance reads the stop from storage and sends nothing until its end', async () => {
    const scry = fakeScryfall({ delayMs: delay, outcome: (n) => (n === 1 ? 429 : 200) });
    const first = createScryfallLimiter({ fetchImpl: scry.fetch, storage, locks: null });
    const tab = new AbortController();
    const out = first.fetch(lookupUrl('Sol Ring'), { signal: tab.signal }).catch(() => 'closed');
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
    expect(scry.names()).toEqual(['Sol Ring', 'Mana Crypt']);
  });

  it('the hover, the commander art and the queue share bucket 1, and the hover goes first', async () => {
    const { scry, cache } = setup(delay);
    ['Q1', 'Q2', 'Q3'].forEach((name) => cache.enqueue(name));
    await advance(0);
    cache.enqueue('Art Card', { first: true });
    cache.enqueue('Hover Card', { first: true });
    await advance(10_000);
    expect(scry.names()).toEqual(['Q1', 'Hover Card', 'Art Card', 'Q2', 'Q3']);
    expect(Math.min(...gaps(scry.times()))).toBeGreaterThanOrEqual(600);
  });

  it('bucket 2 keeps 120 ms between starts, and a stop holds it', async () => {
    const { scry, limiter } = setup(delay, (n) => (n === 6 ? 429 : 200));
    const answers = ['so', 'sol', 'sol r', 'sol ri', 'sol rin'].map((q) => limiter.fetch(autocompleteUrl(q)));
    await advance(1_000);
    await Promise.all(answers);
    expect(gaps(scry.times())).toEqual([120, 120, 120, 120]);

    // A lookup meets a 429, and the stop holds bucket 2 too.
    const lookup = limiter.fetch(lookupUrl('Sol Ring'));
    await advance(delay);
    const failedAt = Date.now();
    expect(limiter.stoppedUntil()).toBe(failedAt + 30_000);
    const suggest = limiter.fetch(autocompleteUrl('mana'));
    await advance(30_000 - 1);
    expect(scry.sends).toHaveLength(6);
    await advance(1_000);
    await Promise.all([lookup, suggest]);
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

  it('starts no bucket 1 request while an answer is out', async () => {
    // Three callers at once: the cache hands over one name at a time, so the
    // limiter itself must hold the other callers.
    const { scry, limiter, cache } = setup(2_000);
    const direct = [limiter.fetch(lookupUrl('A')), limiter.fetch(lookupUrl('B'))];
    cache.enqueue('C');
    await advance(10_000);
    await Promise.all(direct);
    expect(scry.names()).toEqual(['A', 'B', 'C']);
    expect(gaps(scry.times())).toEqual([2_000, 2_000]);
  });

  it('two tabs share bucket 1 through navigator.locks and the last start in storage', async () => {
    const scry = fakeScryfall({ delayMs: 150 });
    const locks = fakeLocks();
    const tabs = [0, 1].map(() =>
      createCardCache({ storage, limiter: createScryfallLimiter({ fetchImpl: scry.fetch, storage, locks }) }),
    );
    for (let i = 0; i < 10; i += 1) {
      tabs[0].enqueue(`Left ${i}`);
      tabs[1].enqueue(`Right ${i}`);
    }
    await advance(20 * 600 + 2_000);
    expect(scry.sends).toHaveLength(20);
    expect(Math.min(...gaps(scry.times()))).toBeGreaterThanOrEqual(600);
    expect(Number(storage.getItem(LAST_START_KEY))).toBe(scry.times()[19]);
  });

  it('reports the end of the stop to a reader and to subscribers', async () => {
    const { limiter } = setup(0, (n) => (n === 1 ? 429 : 200));
    const heard: Array<number | null> = [];
    const unsubscribe = limiter.subscribe((until) => heard.push(until));
    const out = limiter.fetch(lookupUrl('Sol Ring'));
    await advance(0);
    expect(limiter.stoppedUntil()).toBe(T0 + 30_000);
    expect(JSON.parse(storage.getItem(STOP_KEY)!)).toEqual({ until: T0 + 30_000, ms: 30_000 });
    await advance(30_000);
    await out;
    expect(limiter.stoppedUntil()).toBeNull();
    expect(heard).toEqual([T0 + 30_000, null]);
    unsubscribe();
  });

  it('keeps the stop in memory when there is no storage', async () => {
    const scry = fakeScryfall({ outcome: (n) => (n === 1 ? 'reject' : 200) });
    const limiter: ScryfallLimiter = createScryfallLimiter({ fetchImpl: scry.fetch, storage: null, locks: null });
    const out = limiter.fetch(lookupUrl('Sol Ring'));
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
    storage.setItem(STOP_KEY, JSON.stringify({ until: T0 + 36_000_000, ms: 30_000 }));
    const { scry, limiter, cache } = setup(0);
    cache.enqueue('Sol Ring');
    const readings = [limiter.stoppedUntil()];
    const stored = JSON.parse(storage.getItem(STOP_KEY)!);
    await advance(10_000);
    readings.push(limiter.stoppedUntil());
    await advance(20_000 - 1);
    const sentBefore = scry.sends.length;
    await advance(36_000_000);

    expect(sentBefore).toBe(0);
    expect(scry.times()[0] - T0).toBe(30_000);
    expect(readings).toEqual([T0 + 30_000, T0 + 30_000]);
    expect(stored).toEqual({ until: T0 + 30_000, ms: 30_000 });
  });

  it('a stored last start 1 h ahead lets the next lookup go at T0 + 600 ms', async () => {
    storage.setItem(LAST_START_KEY, String(T0 + 3_600_000));
    const { scry, cache } = setup(0);
    cache.enqueue('Sol Ring');
    await advance(600 - 1);
    const sentBefore = scry.sends.length;
    await advance(3_600_000 + 1_000);

    expect(sentBefore).toBe(0);
    expect(scry.times()[0] - T0).toBe(600);
    expect(Number(storage.getItem(LAST_START_KEY))).toBeLessThanOrEqual(T0 + 600);
  });
});
