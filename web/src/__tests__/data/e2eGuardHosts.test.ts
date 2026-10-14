// DEC-1071 — the host tests of the e2e harness (tests/support/guard.ts).
//
// The stub's route and the per-test check ask these tests which requests are
// theirs. `new URL('https://api.scryfall.com./cards').hostname` keeps the root
// dot, so a test that missed the dotted name let such a request pass every check
// (DEC-1087 verdict, N4). The cases build no request.

import { describe, it, expect } from 'vitest';
import { BLOCK_SCRYFALL_DNS, isMoxfieldHost, isScryfallHost } from '../../../tests/support/guard';

describe('e2e harness: host tests', () => {
  it('isScryfallHost takes a Scryfall name that ends in the root dot, and no other name', () => {
    for (const host of ['api.scryfall.com.', 'scryfall.io.', 'cards.scryfall.io.']) {
      expect(isScryfallHost(host), host).toBe(true);
    }
    for (const host of ['notscryfall.com.', 'scryfall.com.evil.test']) {
      expect(isScryfallHost(host), host).toBe(false);
    }
  });

  it('isMoxfieldHost takes a Moxfield name with or without the root dot, and no other name', () => {
    for (const host of ['api2.moxfield.com', 'api2.moxfield.com.', 'moxfield.com']) {
      expect(isMoxfieldHost(host), host).toBe(true);
    }
    for (const host of ['notmoxfield.com', 'moxfield.com.evil.test', 'api.scryfall.com']) {
      expect(isMoxfieldHost(host), host).toBe(false);
    }
  });

  it('BLOCK_SCRYFALL_DNS fails the lookup of each Scryfall and Moxfield name, with and without the root dot', () => {
    const prefix = '--host-resolver-rules=';
    expect(BLOCK_SCRYFALL_DNS.startsWith(prefix)).toBe(true);
    expect(BLOCK_SCRYFALL_DNS.slice(prefix.length).split(', ').sort()).toEqual([
      'MAP *.moxfield.com ~NOTFOUND',
      'MAP *.moxfield.com. ~NOTFOUND',
      'MAP *.scryfall.com ~NOTFOUND',
      'MAP *.scryfall.com. ~NOTFOUND',
      'MAP *.scryfall.io ~NOTFOUND',
      'MAP *.scryfall.io. ~NOTFOUND',
      'MAP moxfield.com ~NOTFOUND',
      'MAP moxfield.com. ~NOTFOUND',
      'MAP scryfall.com ~NOTFOUND',
      'MAP scryfall.com. ~NOTFOUND',
      'MAP scryfall.io ~NOTFOUND',
      'MAP scryfall.io. ~NOTFOUND',
    ]);
  });
});
