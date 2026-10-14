// DEC-1071 — the host tests of the e2e harness (tests/support/guard.ts).
//
// The stub's route and the per-test check ask these tests which requests are
// theirs. `new URL('https://api.scryfall.com./cards').hostname` keeps the root
// dot, so a test that missed the dotted name let such a request pass every check
// (DEC-1087 verdict, N4). The cases build no request.

import { describe, it, expect } from 'vitest';
import { isScryfallHost } from '../../../tests/support/guard';

describe('e2e harness: host tests', () => {
  it('isScryfallHost takes a Scryfall name that ends in the root dot, and no other name', () => {
    for (const host of ['api.scryfall.com.', 'scryfall.io.', 'cards.scryfall.io.']) {
      expect(isScryfallHost(host), host).toBe(true);
    }
    for (const host of ['notscryfall.com.', 'scryfall.com.evil.test']) {
      expect(isScryfallHost(host), host).toBe(false);
    }
  });
});
