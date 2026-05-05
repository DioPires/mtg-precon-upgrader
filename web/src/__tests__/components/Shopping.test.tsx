import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import {
  Shopping,
  aggregateCards,
  parseCsvRows,
  parseOwnedFile,
  splitOwnership,
} from '../../components/organisms/Shopping';
import type { DeckFull, DeckListGroup } from '../../data/types';

function makeDeck(over: Partial<DeckFull>): DeckFull {
  return {
    idx: 1,
    slug: 'alpha',
    deckName: 'Alpha',
    commander: 'Alpha Commander',
    commanderMv: '—',
    type: 'Commander · Theme',
    colors: '🔴',
    bracket: 'IV',
    pt: '—',
    price: '$200-300',
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
    list: [],
    health: { score: 70, grade: 'B' },
    assessment: null,
    composition: { totalCards: 100, lands: 36, avgCmc: 2.8 },
    sim: null,
    rawDecklist: [],
    synergies: [],
    gameChangers: 0,
    ...over,
  };
}

function group(name: string, names: string[], type = 'Creature'): DeckListGroup {
  return {
    name,
    cards: names.map((n) => ({ n, mv: '—', type, price: '—', gc: false })),
  };
}

const ALPHA: DeckFull = makeDeck({
  slug: 'alpha',
  deckName: 'Alpha',
  commander: 'Alpha Commander',
  list: [
    group('Commander', ['Alpha Commander']),
    group('Ramp (3)', ['Sol Ring', 'Arcane Signet', 'Forest']),
    group('Removal (1)', ['Swords to Plowshares']),
  ],
});

const BETA: DeckFull = makeDeck({
  idx: 2,
  slug: 'beta',
  deckName: 'Beta',
  commander: 'Beta Commander',
  colors: '🔵',
  list: [
    group('Commander', ['Beta Commander']),
    group('Ramp (1)', ['Sol Ring', 'Island']),
    group('Draw (1)', ['Rhystic Study']),
  ],
});

describe('parseCsvRows', () => {
  it('parses basic CSV', () => {
    expect(parseCsvRows('a,b,c\n1,2,3')).toEqual([
      ['a', 'b', 'c'],
      ['1', '2', '3'],
    ]);
  });

  it('respects quoted fields with commas inside', () => {
    expect(parseCsvRows('Name,Quantity\n"Smith, John",2')).toEqual([
      ['Name', 'Quantity'],
      ['Smith, John', '2'],
    ]);
  });
});

describe('parseOwnedFile', () => {
  it('reads the CSV path with Name,Quantity headers', () => {
    const map = parseOwnedFile('Name,Quantity\nSol Ring,1\nRhystic Study,1\n');
    expect(map.get('Sol Ring')).toBe(1);
    expect(map.get('Rhystic Study')).toBe(1);
    expect(map.size).toBe(2);
  });

  it('reads the text path with `1x Card` lines', () => {
    const map = parseOwnedFile('1x Sol Ring\n2x Forest\nIsland\n');
    expect(map.get('Sol Ring')).toBe(1);
    expect(map.get('Forest')).toBe(2);
    expect(map.get('Island')).toBe(1);
  });

  it('sums duplicates', () => {
    const map = parseOwnedFile('Name,Quantity\nSol Ring,1\nSol Ring,2\n');
    expect(map.get('Sol Ring')).toBe(3);
  });
});

describe('aggregateCards', () => {
  it('skips basic lands and the Commander group', () => {
    const map = aggregateCards(new Set(['alpha']), [ALPHA, BETA]);
    expect(map.has('Forest')).toBe(false);
    // Commander still added (via deck.commander, isCommander=true)
    expect(map.get('Alpha Commander')?.isCommander).toBe(true);
    // Cards from non-Commander groups are present
    expect(map.has('Sol Ring')).toBe(true);
    expect(map.has('Swords to Plowshares')).toBe(true);
  });

  it('dedupes shared cards across decks and tracks deck attribution', () => {
    const map = aggregateCards(new Set(['alpha', 'beta']), [ALPHA, BETA]);
    const sol = map.get('Sol Ring');
    expect(sol).toBeTruthy();
    expect(sol!.decks.has('alpha')).toBe(true);
    expect(sol!.decks.has('beta')).toBe(true);
  });
});

describe('splitOwnership', () => {
  it('routes cards to buy or own based on owned quantity', () => {
    const cardMap = aggregateCards(new Set(['alpha']), [ALPHA, BETA]);
    const owned = new Map<string, number>([['Sol Ring', 1]]);
    const { buy, own } = splitOwnership(cardMap, owned);
    expect(buy.find((c) => c.name === 'Sol Ring')).toBeUndefined();
    expect(own.find((c) => c.name === 'Sol Ring')?.qty).toBe(1);
    expect(buy.find((c) => c.name === 'Swords to Plowshares')).toBeTruthy();
  });
});

const STORAGE_KEY = 'grimoire-owned-cards';

describe('Shopping organism', () => {
  beforeEach(() => {
    localStorage.removeItem(STORAGE_KEY);
  });
  afterEach(() => {
    localStorage.removeItem(STORAGE_KEY);
  });

  function renderShopping(decks: DeckFull[]) {
    return render(<Shopping decks={decks} />);
  }

  it('preselects the first deck and renders its non-basic non-commander cards in the buy list', () => {
    renderShopping([ALPHA, BETA]);
    expect(screen.getByRole('heading', { name: /Shopping List/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /Need to buy/i })).toBeInTheDocument();
    // Sol Ring + Arcane Signet + Swords to Plowshares from alpha (Forest excluded as basic)
    expect(screen.getByText('Sol Ring')).toBeInTheDocument();
    expect(screen.getByText('Arcane Signet')).toBeInTheDocument();
    expect(screen.getByText('Swords to Plowshares')).toBeInTheDocument();
    expect(screen.queryByText('Forest')).not.toBeInTheDocument();
  });

  it('toggles a deck chip selection via aria-pressed', () => {
    renderShopping([ALPHA, BETA]);
    const betaChip = screen.getByRole('button', { name: /Add Beta/i });
    expect(betaChip).toHaveAttribute('aria-pressed', 'false');
    fireEvent.click(betaChip);
    expect(screen.getByRole('button', { name: /Remove Beta/i })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByText('Rhystic Study')).toBeInTheDocument();
  });

  it('selects all decks with the Select all action', () => {
    renderShopping([ALPHA, BETA]);
    fireEvent.click(screen.getByRole('button', { name: /Select all/i }));
    expect(screen.getByRole('button', { name: /Remove Alpha/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Remove Beta/i })).toBeInTheDocument();
  });

  it('persists imported owned cards in localStorage on mount and removes them from the buy list', () => {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify([['Sol Ring', 1], ['Swords to Plowshares', 1]]),
    );
    renderShopping([ALPHA, BETA]);
    expect(screen.getByText(/cards loaded — saved locally/i)).toBeInTheDocument();
    // Pre-owned cards should not appear in the Need-to-buy list
    expect(screen.queryByText('Swords to Plowshares')).not.toBeInTheDocument();
  });
});
