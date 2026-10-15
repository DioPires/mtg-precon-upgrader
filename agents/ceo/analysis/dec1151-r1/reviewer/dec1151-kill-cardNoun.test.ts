// DEC-1151 kill case (reviewer scratch, not for the tree): a count between 1 and 2.

import { describe, expect, it } from 'vitest';
import { cardNoun } from '../../lib/cardNoun';

describe('cardNoun between 1 and 2 (DEC-1151 kill)', () => {
  // 0.5 fails Math.round and Math.ceil; 1.5 fails Math.floor and Math.trunc.
  it('gives `cards` for a count of 1.5', () => {
    expect(cardNoun(1.5)).toBe('cards');
  });
});
