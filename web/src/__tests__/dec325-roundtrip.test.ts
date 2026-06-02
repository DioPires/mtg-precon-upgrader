// DEC-325 — integration: owned-cards round-trip from Shopping save → Atlas read.
//
// Reproduces the user-reported flow: upload owned CSV on Shopping, navigate to
// Atlas, look up a card, expect OWNED qty > 0.

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { parseOwnedFile } from '../components/organisms/Shopping';
import { loadOwnedMap } from '../data/cardAtlas';
import { frontFace } from '../data/cardName';

const KEY = 'grimoire-owned-cards';

describe('DEC-325: owned cards round-trip', () => {
  beforeEach(() => localStorage.removeItem(KEY));
  afterEach(() => localStorage.removeItem(KEY));

  it('CSV import → save → Atlas lookup finds the card', () => {
    const csv = 'Name,Quantity\nSol Ring,3\nBrazen Borrower,1\n';
    const parsed = parseOwnedFile(csv);
    // Mirror Shopping.saveOwned exactly
    localStorage.setItem(KEY, JSON.stringify([...parsed]));

    const owned = loadOwnedMap();
    expect(owned.get(frontFace('Sol Ring').toLowerCase())).toBe(3);
    expect(owned.get(frontFace('Brazen Borrower').toLowerCase())).toBe(1);
  });

  it('text-format `3x Sol Ring` round-trips', () => {
    const txt = '3x Sol Ring\nArcane Signet\n';
    const parsed = parseOwnedFile(txt);
    localStorage.setItem(KEY, JSON.stringify([...parsed]));
    const owned = loadOwnedMap();
    expect(owned.get('sol ring')).toBe(3);
    expect(owned.get('arcane signet')).toBe(1);
  });

  it('DFC `Brazen Borrower // Petty Theft` in CSV reconciles to front face', () => {
    const csv = 'Name,Quantity\nBrazen Borrower // Petty Theft,2\n';
    const parsed = parseOwnedFile(csv);
    localStorage.setItem(KEY, JSON.stringify([...parsed]));
    const owned = loadOwnedMap();
    expect(owned.get('brazen borrower')).toBe(2);
  });
});
