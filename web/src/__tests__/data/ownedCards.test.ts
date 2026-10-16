// DEC-942 regression: an owned-cards import must never be silently dropped.
//
// Before the fix, `saveOwned` swallowed QuotaExceededError, the UI still said
// "saved locally", and /atlas read nothing (DEC-941).

import { describe, expect, it } from 'vitest';
import { isOwnedQuantity, readOwnedEntries, saveOwned } from '../../data/ownedCards';

const OWNED_KEY = 'grimoire-owned-cards';

/** Minimal Storage stub whose `setItem` throws for the first `failures` calls. */
function makeStorage(failures: number, seed: Record<string, string> = {}): Storage & {
  setCalls: number;
} {
  const map = new Map(Object.entries(seed));
  let setCalls = 0;
  const stub = {
    get length() {
      return map.size;
    },
    get setCalls() {
      return setCalls;
    },
    key: (i: number) => [...map.keys()][i] ?? null,
    getItem: (k: string) => map.get(k) ?? null,
    removeItem: (k: string) => {
      map.delete(k);
    },
    clear: () => map.clear(),
    setItem: (k: string, v: string) => {
      setCalls += 1;
      if (setCalls <= failures) {
        throw new DOMException('quota', 'QuotaExceededError');
      }
      map.set(k, v);
    },
  };
  return stub as unknown as Storage & { setCalls: number };
}

const OWNED = new Map([['Sol Ring', 2], ['Arcane Signet', 1]]);

describe('saveOwned quota handling (DEC-942)', () => {
  it('writes straight through when there is room', () => {
    const storage = makeStorage(0);
    expect(saveOwned(OWNED, storage)).toBe(true);
    expect(JSON.parse(storage.getItem(OWNED_KEY)!)).toEqual([
      ['Sol Ring', 2],
      ['Arcane Signet', 1],
    ]);
    expect(storage.setCalls).toBe(1);
  });

  it('evicts deck + card caches and retries once after a quota error', () => {
    const storage = makeStorage(1, {
      'gv1-deck-data-v144:deck:titan-convergence': 'x'.repeat(50),
      'gv1-deck-data-v144:card-metadata': 'x'.repeat(50),
      'gv1-card:sol ring': 'x'.repeat(50),
      'grimoire-built-decks': 'keep-me',
    });

    expect(saveOwned(OWNED, storage)).toBe(true);
    expect(storage.setCalls).toBe(2);
    expect(storage.getItem(OWNED_KEY)).not.toBeNull();
    // Derivable caches gone...
    expect(storage.getItem('gv1-deck-data-v144:deck:titan-convergence')).toBeNull();
    expect(storage.getItem('gv1-deck-data-v144:card-metadata')).toBeNull();
    expect(storage.getItem('gv1-card:sol ring')).toBeNull();
    // ...other user data untouched.
    expect(storage.getItem('grimoire-built-decks')).toBe('keep-me');
  });

  it('returns false when the retry also fails, instead of reporting success', () => {
    const storage = makeStorage(2, { 'gv1-card:sol ring': 'x' });
    expect(saveOwned(OWNED, storage)).toBe(false);
    expect(storage.setCalls).toBe(2);
    expect(storage.getItem(OWNED_KEY)).toBeNull();
  });

  it('does not loop past a single retry', () => {
    const storage = makeStorage(99);
    expect(saveOwned(OWNED, storage)).toBe(false);
    expect(storage.setCalls).toBe(2);
  });
});

describe('readOwnedEntries (DEC-1150)', () => {
  const read = (stored: string | null) =>
    readOwnedEntries(makeStorage(0, stored === null ? {} : { [OWNED_KEY]: stored }));

  it('gives [] for an empty store and for a store that is not a JSON array', () => {
    expect(read(null)).toEqual([]);
    expect(read('')).toEqual([]);
    expect(read('not json')).toEqual([]);
    for (const value of [{}, 'x', 5, null]) expect(read(JSON.stringify(value))).toEqual([]);
  });

  it('keeps the entries in store order with their names as stored, and writes nothing back', () => {
    const stored = JSON.stringify([['Brazen Borrower // Petty Theft', 2], ['Sol Ring', 1]]);
    const storage = makeStorage(0, { [OWNED_KEY]: stored });
    expect(readOwnedEntries(storage)).toEqual([['Brazen Borrower // Petty Theft', 2], ['Sol Ring', 1]]);
    expect(storage.setCalls).toBe(0);
    expect(storage.getItem(OWNED_KEY)).toBe(stored);
  });

  it('reads localStorage when no storage is given', () => {
    localStorage.setItem(OWNED_KEY, JSON.stringify([['Sol Ring', 1]]));
    try {
      expect(readOwnedEntries()).toEqual([['Sol Ring', 1]]);
    } finally {
      localStorage.removeItem(OWNED_KEY);
    }
  });

  it('keeps a stored name with spaces around it as stored', () => {
    localStorage.setItem(OWNED_KEY, JSON.stringify([[' Sol Ring ', 1]]));
    try {
      expect(readOwnedEntries()).toEqual([[' Sol Ring ', 1]]);
    } finally {
      localStorage.removeItem(OWNED_KEY);
    }
  });

  it.each([
    [[null, 2]],
    [[{ n: 'Sol Ring' }, 2]],
    [[['Sol Ring'], 2]],
    [['  ', 2]],
    [['Sol Ring', 0]],
    [['Sol Ring', -1]],
    [['Sol Ring', 0.5]],
    [['Sol Ring', 1.5]],
    [['Sol Ring', '2']],
    [['Sol Ring']],
    [['Sol Ring', 2, 'foil']],
    [null],
  ])('drops the entry %j and keeps the entry beside it', (entry) => {
    expect(read(JSON.stringify([entry, ['Arcane Signet', 1]]))).toEqual([['Arcane Signet', 1]]);
  });
});

describe('isOwnedQuantity (DEC-1150)', () => {
  it('is true for a whole number of 1 or more', () => {
    expect(isOwnedQuantity(1)).toBe(true);
    expect(isOwnedQuantity(2)).toBe(true);
  });

  it.each([0, -1, 0.5, 1.5, NaN, Infinity, '2', null, undefined])('is false for %o', (q) => {
    expect(isOwnedQuantity(q)).toBe(false);
  });
});
