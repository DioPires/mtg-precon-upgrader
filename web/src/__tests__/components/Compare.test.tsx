import { describe, expect, it } from 'vitest';
import { fireEvent, render, screen, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { Compare } from '../../components/organisms/Compare';
import type { DeckFull, RawDeckHealthScore } from '../../data/types';

function makeHealth(score: number, components: Record<string, number> = {}): RawDeckHealthScore {
  return {
    score,
    grade: score >= 75 ? 'A' : score >= 50 ? 'C' : 'F',
    components,
  };
}

function makeDeck(over: Partial<DeckFull>): DeckFull {
  const base: DeckFull = {
    idx: 1,
    slug: 'alpha',
    deckName: 'Alpha',
    commander: 'Commander A',
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
    health: makeHealth(80, {
      manaReliability: 90,
      threatDeployment: 70,
      interactionDensity: 60,
      comboConsistency: 50,
      commanderIndependence: 80,
    }),
    assessment: null,
    composition: { totalCards: 100, lands: 36, avgCmc: 3.5 },
    sim: null,
    rawDecklist: [],
    physicalDecklist: [],
    synergies: [],
    gameChangers: 2,
    tokens: [],
  };
  return { ...base, ...over };
}

const DECKS: DeckFull[] = [
  makeDeck({ idx: 1, slug: 'alpha', deckName: 'Alpha', health: makeHealth(80) }),
  makeDeck({ idx: 2, slug: 'beta', deckName: 'Beta', health: makeHealth(40) }),
  makeDeck({ idx: 3, slug: 'gamma', deckName: 'Gamma', health: makeHealth(60) }),
];

function renderCompare(decks: DeckFull[]) {
  return render(
    <MemoryRouter initialEntries={['/compare']}>
      <Routes>
        <Route path="/compare" element={<Compare decks={decks} />} />
        <Route path="/deck/:id" element={<div data-testid="guide-page">guide</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

function getRowDeckButtons(): HTMLElement[] {
  const tbody = document.querySelector('tbody')!;
  return within(tbody as HTMLElement).getAllByRole('button');
}

function getRowDeckNames(): string[] {
  return getRowDeckButtons().map((btn) => btn.textContent?.replace(/↗/g, '').trim() ?? '');
}

describe('Compare', () => {
  it('renders an empty state when no decks are loaded', () => {
    renderCompare([]);
    expect(screen.getByText(/no decks loaded/i)).toBeInTheDocument();
  });

  it('hides the sigil of the empty state from screen readers, so the state reads its message alone (DEC-1177)', () => {
    // The state's text without the elements that aria-hidden takes out of the accessibility tree.
    const spoken = (el: Element) => {
      const copy = el.cloneNode(true) as Element;
      copy.querySelectorAll('[aria-hidden="true"]').forEach((hidden) => hidden.remove());
      return copy.textContent;
    };
    renderCompare([]);
    const empty = screen.getByText('No decks loaded.').closest('.gv1-empty')!;
    expect(empty.children).toHaveLength(2);
    const [glyph, text] = empty.children;
    expect(glyph).toHaveAttribute('aria-hidden', 'true');
    expect(glyph.textContent).toBe('◇');
    expect(text).not.toHaveAttribute('aria-hidden');
    expect(spoken(empty)).toBe('No decks loaded.');
  });

  it('renders one row per deck with sticky thead', () => {
    renderCompare(DECKS);
    const tbody = document.querySelector('tbody')!;
    expect(tbody.querySelectorAll('tr')).toHaveLength(3);
    expect(screen.getByRole('heading', { name: /comparative codex/i })).toBeInTheDocument();
  });

  it('sorts by idx ascending by default', () => {
    renderCompare(DECKS);
    expect(getRowDeckNames()).toEqual(['Alpha', 'Beta', 'Gamma']);
  });

  it('sorts numerically descending when a numeric column is clicked', () => {
    renderCompare(DECKS);
    const healthHeader = screen
      .getAllByRole('columnheader')
      .find((h) => /health/i.test(h.textContent ?? ''))!;
    const healthBtn = healthHeader.querySelector('button')!;
    fireEvent.click(healthBtn);
    expect(getRowDeckNames()).toEqual(['Alpha', 'Gamma', 'Beta']);
    // Click again toggles direction.
    fireEvent.click(healthBtn);
    expect(getRowDeckNames()).toEqual(['Beta', 'Gamma', 'Alpha']);
  });

  it('navigates to the deck guide when a deck-name button is clicked', () => {
    renderCompare(DECKS);
    const betaBtn = getRowDeckButtons().find((b) => /beta/i.test(b.textContent ?? ''))!;
    fireEvent.click(betaBtn);
    expect(screen.getByTestId('guide-page')).toBeInTheDocument();
  });

  it('applies score band classes by threshold', () => {
    renderCompare(DECKS);
    expect(document.querySelector('.gv1-cmp-score--good')).not.toBeNull();
    expect(document.querySelector('.gv1-cmp-score--mid')).not.toBeNull();
    expect(document.querySelector('.gv1-cmp-score--poor')).not.toBeNull();
  });

  it('marks active sort header with aria-sort', () => {
    renderCompare(DECKS);
    const headers = screen.getAllByRole('columnheader');
    const idxHeader = headers.find((h) => /^#/.test(h.textContent ?? ''))!;
    expect(idxHeader.getAttribute('aria-sort')).toBe('ascending');
    fireEvent.click(idxHeader.querySelector('button')!);
    expect(idxHeader.getAttribute('aria-sort')).toBe('descending');
  });

  it('renders Vitals + Norm. columns from apothecary diagnosis (DEC-390)', () => {
    renderCompare([
      makeDeck({
        slug: 'delta',
        deckName: 'Delta',
        apothecary: {
          diagnosis: { score: 85, scoreNormalized: 64, methodology: 'deck-metrics-v2', components: {} },
          maladies: [],
          remedies: [],
          pins: [],
        },
      }),
    ]);
    const headers = screen.getAllByRole('columnheader').map((h) => h.textContent ?? '');
    expect(headers.some((t) => /vitals/i.test(t))).toBe(true);
    expect(headers.some((t) => /norm\./i.test(t))).toBe(true);
    expect(screen.getByText('85')).toBeInTheDocument();
    expect(screen.getByText('64')).toBeInTheDocument();
  });

  it('renders em-dash in Vitals/Norm. when apothecary or normalized score is missing (DEC-390)', () => {
    renderCompare([
      makeDeck({
        slug: 'epsilon',
        deckName: 'Epsilon',
        apothecary: {
          diagnosis: { score: 77, scoreNormalized: null, methodology: 'deck-metrics-v2', components: {} },
          maladies: [],
          remedies: [],
          pins: [],
        },
      }),
    ]);
    expect(screen.getByText('77')).toBeInTheDocument();
    // Norm. column has no normalized score yet → em-dash placeholder.
    expect(screen.getAllByText('—').length).toBeGreaterThanOrEqual(1);
  });

  it('sorts by the Norm. column when its header is clicked (DEC-390)', () => {
    const withNorm = (slug: string, name: string, norm: number): DeckFull =>
      makeDeck({
        slug,
        deckName: name,
        apothecary: {
          diagnosis: { score: 50, scoreNormalized: norm, methodology: 'deck-metrics-v2', components: {} },
          maladies: [],
          remedies: [],
          pins: [],
        },
      });
    renderCompare([
      withNorm('alpha', 'Alpha', 40),
      withNorm('beta', 'Beta', 90),
      withNorm('gamma', 'Gamma', 65),
    ]);
    const normHeader = screen
      .getAllByRole('columnheader')
      .find((h) => /norm\./i.test(h.textContent ?? ''))!;
    fireEvent.click(normHeader.querySelector('button')!);
    expect(getRowDeckNames()).toEqual(['Beta', 'Gamma', 'Alpha']);
  });

  it('renders partner alongside commander in the Commander cell (DEC-190)', () => {
    renderCompare([
      makeDeck({
        slug: 'turtle-power',
        deckName: 'Turtle Power',
        commander: 'Leonardo, the Balance',
        partner: 'Donatello, the Brains',
      }),
    ]);
    expect(
      document.querySelector('[data-card-name="Leonardo, the Balance"]'),
    ).not.toBeNull();
    expect(
      document.querySelector('[data-card-name="Donatello, the Brains"]'),
    ).not.toBeNull();
  });
});
