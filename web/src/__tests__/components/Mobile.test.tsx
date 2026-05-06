import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Mobile } from '../../components/organisms/Mobile';
import type { DeckFull } from '../../data/types';

function makeDeck(over: Partial<DeckFull>): DeckFull {
  return {
    idx: 3,
    slug: 'gamma',
    deckName: 'Cascading Inevitability',
    commander: 'Gamma Commander',
    commanderMv: '—',
    type: 'Commander · Theme',
    colors: '🔴⚫',
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
    physicalDecklist: [],
    synergies: [],
    gameChangers: 0,
    ...over,
  };
}

describe('Mobile organism', () => {
  it('renders deck idx, bracket, commander, and italicized last word', () => {
    render(<Mobile deck={makeDeck({})} />);
    expect(screen.getByText(/№ 03 · BRACKET IV/)).toBeInTheDocument();
    const heading = screen.getByRole('heading', { level: 1 });
    expect(heading).toHaveTextContent('Cascading Inevitability');
    expect(heading.querySelector('em')).toHaveTextContent('Inevitability');
    expect(screen.getByText(/Gamma Commander/)).toBeInTheDocument();
  });

  it('renders the first wincon when present', () => {
    const deck = makeDeck({
      wincons: [
        {
          title: ['Cascade', 'Storm'],
          desc: 'Stack the deck and resolve free spells.',
          prob: 'T6',
          cards: [],
        },
        { title: ['B', 'b'], desc: '', prob: '', cards: [] },
      ],
    });
    render(<Mobile deck={deck} />);
    expect(screen.getByText('WIN · 01 / 02')).toBeInTheDocument();
    expect(screen.getByText(/Stack the deck/)).toBeInTheDocument();
    expect(screen.getByText('T6')).toBeInTheDocument();
  });

  it('renders the curve when curve entries exist', () => {
    const deck = makeDeck({
      curve: [
        { cmc: '0', n: 1, peak: false },
        { cmc: '1', n: 5, peak: true },
        { cmc: '2', n: 4, peak: false },
      ],
    });
    render(<Mobile deck={deck} />);
    expect(screen.getByText('ROLE DISTRIBUTION')).toBeInTheDocument();
    const cols = document.querySelectorAll('.gv1-curve-col');
    expect(cols.length).toBe(3);
    expect(document.querySelectorAll('.gv1-curve-col.gv1-peak').length).toBe(1);
  });

  it('exposes the four mobile tabs as a tablist with one selected', () => {
    render(<Mobile deck={makeDeck({})} />);
    const tablist = screen.getByRole('tablist');
    const tabs = tablist.querySelectorAll('[role="tab"]');
    expect(tabs.length).toBe(4);
    expect(tablist.querySelectorAll('[aria-selected="true"]').length).toBe(1);
  });
});
