// DEC-1150 review kill cases for PR #60 (DEC-1141). Each case passes on the
// merged head and fails on the named survivor mutant of Shopping.tsx.
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Shopping, parseOwnedFile } from '../../components/organisms/Shopping';
import type { DeckFull } from '../../data/types';

const STORAGE_KEY = 'grimoire-owned-cards';

const ALPHA = {
  idx: 1,
  slug: 'alpha',
  deckName: 'Alpha',
  commander: 'Alpha Commander',
  commanderMv: '—',
  type: 'Commander · Theme',
  colors: '🔴',
  bracket: '4',
  status: 'physical',
  pt: '—',
  winTurn: '—',
  winRate: null,
  flavor: '',
  oracle: [],
  strategy: '',
  wincons: [],
  engine: [],
  combos: [],
  apothecary: null,
  curve: [],
  func: [],
  sources: [],
  list: [
    {
      name: 'Ramp (2)',
      cards: ['Sol Ring', 'Arcane Signet'].map((n) => ({ n, mv: '—', type: 'Artifact', price: '—', gc: false })),
    },
  ],
  health: { score: 70, grade: 'B' },
  assessment: null,
  composition: { totalCards: 100, lands: 36, avgCmc: 2.8 },
  sim: null,
  rawDecklist: [],
  physicalDecklist: [],
  synergies: [],
  gameChangers: 0,
  tokens: [],
} as DeckFull;

describe('DEC-1150 kill cases: CSV quantity cell', () => {
  // Kills R1 (Math.max(read, 1)) and R2 (read < 1 ? 1 : read): both give NaN.
  it('K1: counts a quantity cell with text as 1', () => {
    expect(parseOwnedFile('Name,Quantity\nSol Ring,abc\n').get('Sol Ring')).toBe(1);
  });

  // Kills R8 (parseInt without the radix 10): it reads 0x10 as 16.
  it('K2: reads a 0x cell in base 10, so 0x10 counts as 1', () => {
    expect(parseOwnedFile('Name,Quantity\nSol Ring,0x10\n').get('Sol Ring')).toBe(1);
  });
});

describe('DEC-1150 kill cases: stored list', () => {
  beforeEach(() => localStorage.removeItem(STORAGE_KEY));
  afterEach(() => localStorage.removeItem(STORAGE_KEY));

  // Kills R5 (typeof n === 'number'): null.trim() throws and empties the list.
  it('K3: drops a stored entry whose name is null, an object or an array, and keeps the rest', () => {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify([[null, 2], [{ n: 'Sol Ring' }, 2], [['Sol Ring'], 2], ['Arcane Signet', 1]]),
    );
    render(<Shopping decks={[ALPHA]} />);
    expect(screen.getByText('1 card loaded — saved locally')).toBeInTheDocument();
  });

  // Kills R13 (q < 0): it keeps a quantity of 0, and the bar reads `0 cards loaded`.
  it('K4: drops a stored quantity of 0', () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify([['Sol Ring', 0]]));
    render(<Shopping decks={[ALPHA]} />);
    expect(screen.queryByText(/loaded —/)).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Clear owned' })).not.toBeInTheDocument();
  });
});
