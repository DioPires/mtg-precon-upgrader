// DEC-1142 — the noun for a count of cards.

import { describe, expect, it } from 'vitest';
import { cardNoun } from '../../lib/cardNoun';

describe('cardNoun', () => {
  it('gives `card` for a count of 1', () => {
    expect(cardNoun(1)).toBe('card');
  });

  // Each count holds the helper to its declared type (`count: number`): 0 and 0.5
  // fail `count <= 1` and `count < 2`, 2 fails `count > 1 ? 'cards' : 'card'`, and
  // -1 fails `Math.abs(count) === 1`. 0.5 fails `Math.round` and `Math.ceil`, and
  // 1.5 fails `Math.floor` and `Math.trunc`.
  it.each([0, 2, -1, 0.5, 1.5, NaN])('gives `cards` for a count of %s', (count) => {
    expect(cardNoun(count)).toBe('cards');
  });
});
