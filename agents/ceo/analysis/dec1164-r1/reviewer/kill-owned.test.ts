// DEC-1164 kill case for R9 (`out.push([n.trim(), q])`) at ownedCards.ts:42.
// Ruling 1: readOwnedEntries gives the kept entries with their names as stored.
// Route A: add this case to describe('readOwnedEntries (DEC-1150)') in
// src/__tests__/data/ownedCards.test.ts.

import { expect, it } from 'vitest';
import { readOwnedEntries } from '../../data/ownedCards';

const OWNED_KEY = 'grimoire-owned-cards';

it('keeps a stored name with spaces around it as stored', () => {
  localStorage.setItem(OWNED_KEY, JSON.stringify([[' Sol Ring ', 1]]));
  try {
    expect(readOwnedEntries()).toEqual([[' Sol Ring ', 1]]);
  } finally {
    localStorage.removeItem(OWNED_KEY);
  }
});
