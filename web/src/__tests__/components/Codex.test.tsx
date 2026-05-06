import { describe, expect, it } from 'vitest';
import { fireEvent, render, screen, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { Codex } from '../../components/organisms/Codex';
import type { DeckFull } from '../../data/types';

function makeDeck(over: Partial<DeckFull>): DeckFull {
  const base: DeckFull = {
    idx: 1,
    slug: 'alpha',
    deckName: 'Alpha',
    commander: 'Commander A',
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
    physicalDecklist: [],
    synergies: [],
    gameChangers: 1,
  };
  return { ...base, ...over };
}

const DECKS: DeckFull[] = [
  makeDeck({
    idx: 1,
    slug: 'alpha',
    deckName: 'Alpha',
    colors: '🔴',
    bracket: 'IV',
    health: { score: 80, grade: 'A' },
    composition: { totalCards: 100, lands: 36, avgCmc: 3.5 },
    wincons: [{ title: ['x', 'y'], prob: '', desc: '', cards: [] }],
    combos: [],
  }),
  makeDeck({
    idx: 2,
    slug: 'beta',
    deckName: 'Beta',
    colors: '🔴🟢',
    bracket: 'III',
    health: { score: 60, grade: 'C' },
    composition: { totalCards: 99, lands: 35, avgCmc: 2.5 },
    wincons: [],
    combos: [{ title: ['c', 'd'], desc: '', cards: [], src: '', tag: '' }],
  }),
];

function renderCodex(decks: DeckFull[]) {
  return render(
    <MemoryRouter initialEntries={['/codex']}>
      <Routes>
        <Route path="/codex" element={<Codex decks={decks} />} />
        <Route path="/deck/:id" element={<div data-testid="guide-page">guide</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('Codex', () => {
  it('renders one card per deck plus aggregate stats', () => {
    renderCodex(DECKS);
    expect(screen.getByRole('heading', { name: /codex/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /open alpha guide/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /open beta guide/i })).toBeInTheDocument();
    // Aggregate: 2 tomes shelved.
    expect(screen.getByText('2', { selector: '.gv1-serif-xxl' })).toBeInTheDocument();
  });

  it('navigates to the deck guide when a card is clicked', () => {
    renderCodex(DECKS);
    fireEvent.click(screen.getByRole('button', { name: /open beta guide/i }));
    expect(screen.getByTestId('guide-page')).toBeInTheDocument();
  });

  it('filters to bracket IV decks', () => {
    renderCodex(DECKS);
    fireEvent.click(screen.getByRole('button', { name: /bracket iv/i, pressed: false }));
    expect(screen.getByRole('button', { name: /open alpha guide/i })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /open beta guide/i })).not.toBeInTheDocument();
  });

  it('filters to multicolor decks', () => {
    renderCodex(DECKS);
    fireEvent.click(screen.getByRole('button', { name: /multicolor/i, pressed: false }));
    expect(screen.getByRole('button', { name: /open beta guide/i })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /open alpha guide/i })).not.toBeInTheDocument();
  });

  it('sorts by health (descending)', () => {
    renderCodex(DECKS);
    fireEvent.click(screen.getByRole('button', { name: /^health$/i, pressed: false }));
    const grid = document.querySelector('.gv1-codex-grid')!;
    const titles = within(grid as HTMLElement).getAllByRole('heading', { level: 3 });
    expect(titles[0]).toHaveTextContent('Alpha');
    expect(titles[1]).toHaveTextContent('Beta');
  });
});
