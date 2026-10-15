// DEC-1151 kill case (reviewer scratch, not for the tree): the Need to buy and
// Already own headers when the two sections hold different counts.

import { afterEach, describe, expect, it } from 'vitest';
import { fireEvent, render, screen, within } from '@testing-library/react';
import { Shopping } from '../../components/organisms/Shopping';
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
    list: [],
    health: { score: 70, grade: 'B' },
    assessment: null,
    composition: { totalCards: 100, lands: 36, avgCmc: 2.8 },
    sim: null,
    rawDecklist: [],
    physicalDecklist: [],
    synergies: [],
    gameChangers: 0,
    tokens: [],
    ...over,
  };
}

function group(name: string, names: string[], type = 'Creature'): DeckListGroup {
  return {
    name,
    cards: names.map((n) => ({ n, mv: '—', type, price: '—', gc: false })),
  };
}

const STORAGE_KEY = 'grimoire-owned-cards';

const SOLO_A = makeDeck({
  slug: 'solo-a',
  deckName: 'Solo A',
  commander: 'Solo A Commander',
  list: [group('Commander', ['Solo A Commander']), group('Ramp (1)', ['Sol Ring'])],
});
const SOLO_B = makeDeck({
  idx: 2,
  slug: 'solo-b',
  deckName: 'Solo B',
  commander: 'Solo B Commander',
  list: [group('Commander', ['Solo B Commander']), group('Ramp (1)', ['Sol Ring'])],
});

describe('the Shopping headers when the two sections hold different counts (DEC-1151 kill)', () => {
  afterEach(() => localStorage.removeItem(STORAGE_KEY));

  // Both decks selected, the user owns Solo A Commander alone. Need to buy holds
  // Solo B Commander and two Sol Rings (2 unique, 3 cards); Already own holds one
  // card. Each header must read its own counts.
  it('reads `2 unique · 3 cards` to buy and `1 unique · 1 card` owned', () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify([['Solo A Commander', 1]]));
    render(<Shopping decks={[SOLO_A, SOLO_B]} />);
    fireEvent.click(screen.getByRole('button', { name: /Select all/i }));
    const buyHead = screen.getByRole('heading', { name: 'Need to buy' }).parentElement!;
    const ownHead = screen.getByRole('button', { name: /Already own/ });
    expect(within(buyHead).getByText('· 2 unique · 3 cards')).toBeInTheDocument();
    expect(within(ownHead).getByText('· 1 unique · 1 card')).toBeInTheDocument();
  });
});
