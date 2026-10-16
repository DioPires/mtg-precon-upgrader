// DEC-1170 kill cases for PR #70 (DEC-1153): bucket 1's lock and the blank identifier.
// 6b: a fetch of 19.9 s (or 19.999 s), then a `settle` of 1 s: the lock frees at 20 s after the start.
// 8b: a subscriber of a blank name that asks for a new name while takeBatch() settles the blank one.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createCardCache } from '../../data/cardCache';
import { collectionRequest, COLLECTION_URL, createScryfallLimiter, type ScryfallLimiter } from '../../data/scryfallLimiter';
import { fakeLocks, fakeScryfall, MemoryStorage } from '../data/scryfallFakes';

const T0 = Date.UTC(2026, 9, 14, 12, 0, 0);
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
const postOf = (names: string[]) => {
  const { method, headers, body } = collectionRequest(names);
  return { method, headers, body };
};

describe('DEC-1170 6b: a long fetch, then a `settle` of 1 s', () => {
  for (const fetchMs of [19_900, 19_999]) {
    it(`fetch ${fetchMs} ms + settle 1,000 ms: the other tab starts at 20,000 ms, and next() resolves after settle`, async () => {
      const scry = fakeScryfall({ delayMs: fetchMs });
      const locks = fakeLocks();
      const [left, right] = [0, 1].map(() => createScryfallLimiter({ fetchImpl: scry.fetch, storage, locks }));
      let leftResolvedAt: number | null = null;
      let settledAt: number | null = null;
      void left
        .next('lookup', () => collectionRequest(['L']), {
          settle: async () => {
            await new Promise((resolve) => setTimeout(resolve, 1_000));
            settledAt = Date.now() - T0;
          },
        })
        .then(() => (leftResolvedAt = Date.now() - T0));
      await advance(0);
      void right.fetch(COLLECTION_URL, postOf(['R']));
      await advance(20_000 - 1);
      expect(scry.batches()).toEqual([['L']]);
      await advance(1);
      expect(scry.batches()).toEqual([['L'], ['R']]);
      expect(scry.times().map((t) => t - T0)).toEqual([0, 20_000]);
      await advance(fetchMs + 1_000);
      expect(settledAt).toBe(fetchMs + 1_000);
      expect(leftResolvedAt).toBe(fetchMs + 1_000);
    });
  }
});

describe('DEC-1170 8b: a subscriber of a blank name asks for a new name during takeBatch()', () => {
  function countingLimiter(inner: ScryfallLimiter) {
    const stats = { calls: 0, out: 0, maxOut: 0 };
    const limiter: ScryfallLimiter = {
      ...inner,
      next: (bucket, pick, options) => {
        stats.calls += 1;
        stats.out += 1;
        stats.maxOut = Math.max(stats.maxOut, stats.out);
        return inner.next(bucket, pick, options).finally(() => {
          stats.out -= 1;
        });
      },
    };
    return { limiter, stats };
  }

  for (const [label, others, first] of [
    ['with another name in the batch', ['Arcane Signet'], false],
    ['alone in the queue', [], false],
    ['alone in the queue, the new name asked `first`', [], true],
  ] as const) {
    it(`${label}: the new name goes in a later batch, once, and one pump runs`, async () => {
      const scry = fakeScryfall();
      const { limiter, stats } = countingLimiter(createScryfallLimiter({ fetchImpl: scry.fetch, storage, locks: null }));
      const cache = createCardCache({ storage, limiter });
      const heard: Array<string | undefined> = [];
      cache.subscribe('   ', (entry) => {
        heard.push(entry?.error);
        if (entry?.status === 'error') cache.enqueue('Fresh Name', { first });
      });
      cache.enqueue('   ');
      others.forEach((name) => cache.enqueue(name));
      await advance(5_000);
      const observed = {
        batches: scry.batches(),
        times: scry.times().map((t) => t - T0),
        heard,
        fresh: cache.get('Fresh Name')?.status,
        others: others.map((name) => cache.get(name)?.status),
        blank: cache.get('   ')?.errorStatus,
        nextCalls: stats.calls,
        maxNextOut: stats.maxOut,
      };
      console.log(`DEC-1170 8b observed (${label})`, JSON.stringify(observed));
      expect(observed.batches).toEqual(others.length ? [[...others], ['Fresh Name']] : [['Fresh Name']]);
      expect(observed.heard).toEqual(['not_found']);
      expect(observed.fresh).toBe('loaded');
      expect(observed.blank).toBe(404);
      expect(observed.maxNextOut).toBe(1);
      // Nothing waits: a later enqueue of a new name goes in its own batch.
      cache.enqueue('Later Name');
      await advance(5_000);
      expect(scry.batches().at(-1)).toEqual(['Later Name']);
      expect(stats.maxOut).toBe(1);
    });
  }
});

