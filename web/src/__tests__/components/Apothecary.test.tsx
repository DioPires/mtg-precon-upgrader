import { describe, expect, it } from 'vitest';
import { fireEvent, render, screen, within } from '@testing-library/react';
import { Apothecary } from '../../components/organisms/Apothecary';
import type { DeckApothecary, DeckPin, RawCandidate } from '../../data/types';

function makeApothecary(over: Partial<DeckApothecary> = {}): DeckApothecary {
  return {
    diagnosis: {
      score: 72,
      scoreNormalized: null,
      methodology: 'deck-metrics-v1',
      generatedAt: '2026-05-01T00:00:00Z',
      mirrorUpdatedAt: '2026-05-01T00:00:00Z',
      components: {
        manabase_health: { score: 80 },
        role_coverage_health: { score: 60 },
        curve_health: { score: 70 },
        interaction_density: { score: 40 },
        gameplan_cohesion: { score: 90 },
      },
      ...over.diagnosis,
    },
    maladies: over.maladies ?? [
      { role: 'ramp', actual: 6, target: 10, score: 60 },
      { role: 'card-draw', actual: 4, target: 10, score: 40 },
    ],
    remedies: over.remedies ?? [
      {
        name: 'Sol Ring',
        cmc: 1,
        mana_cost: '{1}',
        type_line: 'Artifact',
        score: 48,
        deck_role: 'ramp',
        mitigates_gap: 'ramp',
        strategy_line: 'Iconic mana rock.',
      },
      {
        name: 'Rhystic Study',
        cmc: 3,
        mana_cost: '{2}{U}',
        type_line: 'Enchantment',
        score: 45,
        deck_role: 'card-draw',
        mitigates_gap: 'card-draw',
      },
      {
        name: 'Generic Filler',
        cmc: 4,
        mana_cost: '{3}{G}',
        type_line: 'Creature — Beast',
        score: 30,
        deck_role: 'ramp',
        mitigates_gap: null,
      },
    ],
    pins: over.pins ?? [],
  };
}

// DEC-1000 — the anvil-chorus pool entry seated by `candidate_pins` (DEC-992).
const HOUND: RawCandidate = {
  name: 'Flickering Hound',
  cmc: 4,
  mana_cost: '{3}{W}',
  type_line: 'Creature — Dog',
  score: 33.7,
  matched_archetypes: ['ETB Value / Flicker'],
  strategy_line: 'ETB Value / Flicker',
  mitigates_gap: null,
  pinned: true,
};
const HOUND_REASON = 'DEC-987 board decision 2026-10-12: skip in the 99, keep in the pool.';

function fillers(n: number): RawCandidate[] {
  return Array.from({ length: n }, (_, i) => ({
    name: `Filler ${i + 1}`,
    cmc: 2,
    mana_cost: '{2}',
    type_line: 'Artifact',
    score: 70 - i,
    mitigates_gap: null,
  }));
}

function pinFor(pool: RawCandidate[], card: RawCandidate, reason = HOUND_REASON): DeckPin {
  return { name: card.name, reason, card, rank: pool.indexOf(card) + 1, poolSize: pool.length };
}

function remedyGrid(container: HTMLElement): HTMLElement {
  return container.querySelector('.gv1-apo-remedies') as HTMLElement;
}

describe('Apothecary', () => {
  it('renders an empty state when apothecary is null', () => {
    render(<Apothecary apothecary={null} />);
    expect(screen.getByRole('heading', { name: /the apothecary/i })).toBeInTheDocument();
    expect(screen.getByText(/no diagnosis on file/i)).toBeInTheDocument();
  });

  it('filters remedies when a malady chip is toggled', () => {
    render(<Apothecary apothecary={makeApothecary()} />);

    expect(screen.getByText('Sol Ring')).toBeInTheDocument();
    expect(screen.getByText('Rhystic Study')).toBeInTheDocument();
    expect(screen.getByText('Generic Filler')).toBeInTheDocument();

    const cardDrawChip = screen.getByRole('button', { name: /card draw/i, pressed: false });
    fireEvent.click(cardDrawChip);

    expect(screen.getByRole('button', { name: /card draw/i, pressed: true })).toBeInTheDocument();
    expect(screen.getByText('Rhystic Study')).toBeInTheDocument();
    expect(screen.queryByText('Sol Ring')).not.toBeInTheDocument();
    expect(screen.queryByText('Generic Filler')).not.toBeInTheDocument();
    expect(screen.getByText(/filtered: card draw/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /clear filter/i }));
    expect(screen.getByText('Sol Ring')).toBeInTheDocument();
  });

  it('toggles the breakdown panel and surfaces the weakest component', () => {
    render(<Apothecary apothecary={makeApothecary()} />);

    expect(screen.getByText(/interaction density/i)).toBeInTheDocument();

    const toggle = screen.getByRole('button', { name: /show breakdown/i });
    fireEvent.click(toggle);
    expect(screen.getByRole('button', { name: /hide breakdown/i })).toBeInTheDocument();
    expect(screen.getAllByText(/weakest/i).length).toBeGreaterThan(0);
  });

  it('renders the confidence margin next to the score when provided (DEC-310)', () => {
    render(
      <Apothecary
        apothecary={makeApothecary({
          diagnosis: {
            score: 82,
            confidenceMargin: 5,
            methodology: 'deck-metrics-v2',
            generatedAt: '2026-05-29T00:00:00Z',
            mirrorUpdatedAt: '2026-05-29T00:00:00Z',
            components: {
              manabase_health: { score: 80 },
              role_coverage_health: { score: 80 },
              curve_health: { score: 80 },
              interaction_density: { score: 80 },
              gameplan_cohesion: { score: 80 },
              resilience_health: { score: 80 },
            },
          },
        })}
      />,
    );

    expect(screen.getByText(/± 5/)).toBeInTheDocument();
    expect(screen.getByText('82')).toBeInTheDocument();
  });

  it('renders the Best/Typical/Contested triple when winTurn is provided (DEC-311)', () => {
    render(
      <Apothecary
        apothecary={makeApothecary({
          diagnosis: {
            score: 82,
            confidenceMargin: 5,
            methodology: 'deck-metrics-v2',
            generatedAt: '2026-05-29T00:00:00Z',
            mirrorUpdatedAt: '2026-05-29T00:00:00Z',
            components: { manabase_health: { score: 80 } },
            winTurn: {
              best: 6,
              typical: 8,
              contested: 9,
              source: 'lethalProxy',
              bracket_drag: 1,
              thresholds: { best: 15.0, typical: 50.0 },
              window_last_turn: 10,
            },
          },
        })}
      />,
    );

    expect(screen.getByText('WIN TURN')).toBeInTheDocument();
    expect(screen.getByText('BEST')).toBeInTheDocument();
    expect(screen.getByText('TYPICAL')).toBeInTheDocument();
    expect(screen.getByText('CONTESTED')).toBeInTheDocument();
    expect(screen.getByText('T6')).toBeInTheDocument();
    expect(screen.getByText('T8')).toBeInTheDocument();
    expect(screen.getByText('T9')).toBeInTheDocument();
  });

  it('renders em-dash for typical/contested when threshold is not reached (DEC-311)', () => {
    render(
      <Apothecary
        apothecary={makeApothecary({
          diagnosis: {
            score: 70,
            methodology: 'deck-metrics-v2',
            generatedAt: '2026-05-29T00:00:00Z',
            mirrorUpdatedAt: '2026-05-29T00:00:00Z',
            components: { manabase_health: { score: 70 } },
            winTurn: {
              best: 8,
              typical: null,
              contested: null,
              source: 'max',
              bracket_drag: 0,
              thresholds: { best: 15.0, typical: 50.0 },
              window_last_turn: 10,
            },
          },
        })}
      />,
    );

    expect(screen.getByText('WIN TURN')).toBeInTheDocument();
    expect(screen.getByText('T8')).toBeInTheDocument();
    const dashes = screen.getAllByText('—');
    expect(dashes.length).toBeGreaterThanOrEqual(2);
  });

  it('suppresses the WIN TURN block entirely when winTurn is null (DEC-311)', () => {
    render(<Apothecary apothecary={makeApothecary()} />);
    expect(screen.queryByText('WIN TURN')).not.toBeInTheDocument();
  });

  it('renders a single-letter grade with no banding (DEC-310)', () => {
    render(
      <Apothecary
        apothecary={makeApothecary({
          diagnosis: {
            score: 87,
            confidenceMargin: 4,
            methodology: 'deck-metrics-v2',
            generatedAt: '2026-05-29T00:00:00Z',
            mirrorUpdatedAt: '2026-05-29T00:00:00Z',
            components: { manabase_health: { score: 80 } },
          },
        })}
      />,
    );

    // 87 used to be "A+"; under DEC-310 it must collapse to "B".
    expect(screen.queryByText('A+')).not.toBeInTheDocument();
    expect(screen.queryByText('A-')).not.toBeInTheDocument();
    expect(screen.getByText('B')).toBeInTheDocument();
  });

  describe('board picks (DEC-1000)', () => {
    it('shows a pin below the top 30 in the strip, not in the grid', () => {
      const pool = [...fillers(30), HOUND];
      const { container } = render(
        <Apothecary apothecary={makeApothecary({ remedies: pool, pins: [pinFor(pool, HOUND)] })} />,
      );

      const strip = screen.getByRole('region', { name: 'Board picks' });
      expect(within(strip).getByText('board pick')).toBeInTheDocument();
      expect(within(strip).getByText('Flickering Hound')).toBeInTheDocument();
      expect(within(strip).getByText('Creature — Dog')).toBeInTheDocument();
      expect(within(strip).getByText('ETB Value / Flicker')).toBeInTheDocument();
      expect(within(strip).getByText('rank 31 of 31')).toBeInTheDocument();
      expect(within(strip).getByText('score 33.7')).toBeInTheDocument();
      expect(within(strip).getByText(HOUND_REASON)).toBeInTheDocument();

      const grid = remedyGrid(container);
      expect(grid.querySelectorAll('article')).toHaveLength(30);
      expect(within(grid).queryByText('Flickering Hound')).not.toBeInTheDocument();
      expect(grid.querySelector('.gv1-apo-tag-pinned')).toBeNull();
    });

    it('badges a pin inside the top 30 in the grid and keeps it in the strip', () => {
      const pool = [...fillers(2), HOUND, ...fillers(1).map((c) => ({ ...c, name: 'Tail Filler', score: 20 }))];
      const { container } = render(
        <Apothecary apothecary={makeApothecary({ remedies: pool, pins: [pinFor(pool, HOUND)] })} />,
      );

      const grid = remedyGrid(container);
      const entry = grid.querySelector('article[data-card-name="Flickering Hound"]') as HTMLElement;
      expect(entry).toHaveClass('is-pinned');
      expect(within(entry).getByText('pinned')).toHaveClass('gv1-apo-tag', 'gv1-apo-tag-pinned');
      expect(grid.querySelectorAll('.is-pinned')).toHaveLength(1);
      expect(grid.querySelectorAll('.gv1-apo-tag-pinned')).toHaveLength(1);

      const strip = screen.getByRole('region', { name: 'Board picks' });
      expect(within(strip).getByText('Flickering Hound')).toBeInTheDocument();
      expect(within(strip).getByText('rank 3 of 4')).toBeInTheDocument();

      // Same score against the same max: the strip ring and the grid ring agree.
      const dash = (el: HTMLElement) => el.querySelector('.gv1-apo-ring-fill')?.getAttribute('stroke-dashoffset');
      expect(dash(strip)).toBeTruthy();
      expect(dash(strip)).toBe(dash(entry));
    });

    it('renders pins in the order given', () => {
      const second: RawCandidate = { ...HOUND, name: 'Second Pick', score: 12 };
      const pool = [...fillers(3), HOUND, second];
      render(
        <Apothecary
          apothecary={makeApothecary({
            remedies: pool,
            pins: [pinFor(pool, second, 'Later in the pool, first in the file.'), pinFor(pool, HOUND)],
          })}
        />,
      );

      const strip = screen.getByRole('region', { name: 'Board picks' });
      const names = [...strip.querySelectorAll('.gv1-apo-remedy-name')].map((n) => n.textContent);
      expect(names).toEqual(['Second Pick', 'Flickering Hound']);
      expect(within(strip).getAllByText('board pick')).toHaveLength(2);
    });

    it('renders no strip and no badge when there are no pins', () => {
      const { container } = render(<Apothecary apothecary={makeApothecary()} />);
      expect(screen.queryByRole('region', { name: 'Board picks' })).not.toBeInTheDocument();
      expect(screen.queryByText('board pick')).not.toBeInTheDocument();
      expect(container.querySelector('.gv1-apo-pins')).toBeNull();
      expect(container.querySelector('.gv1-apo-tag-pinned')).toBeNull();
      expect(container.querySelector('.is-pinned')).toBeNull();
    });

    it('keeps the strip while a malady filter is active', () => {
      const base = makeApothecary().remedies;
      const pool = [...base, HOUND];
      const { container } = render(
        <Apothecary apothecary={makeApothecary({ remedies: pool, pins: [pinFor(pool, HOUND)] })} />,
      );
      expect(within(remedyGrid(container)).getByText('Flickering Hound')).toBeInTheDocument();

      fireEvent.click(screen.getByRole('button', { name: /card draw/i, pressed: false }));

      const grid = remedyGrid(container);
      expect(within(grid).getByText('Rhystic Study')).toBeInTheDocument();
      expect(within(grid).queryByText('Flickering Hound')).not.toBeInTheDocument();
      const strip = screen.getByRole('region', { name: 'Board picks' });
      expect(within(strip).getByText('Flickering Hound')).toBeInTheDocument();
      expect(within(strip).getByText(HOUND_REASON)).toBeInTheDocument();
    });

    it('keeps the strip above the empty state when the filter matches nothing', () => {
      const pool = [HOUND];
      render(
        <Apothecary
          apothecary={makeApothecary({
            maladies: [{ role: 'tutor', actual: 0, target: 2, score: 0 }],
            remedies: pool,
            pins: [pinFor(pool, HOUND)],
          })}
        />,
      );
      fireEvent.click(screen.getByRole('button', { name: /tutors/i, pressed: false }));

      expect(screen.getByText(/no remedies match/i)).toBeInTheDocument();
      const strip = screen.getByRole('region', { name: 'Board picks' });
      expect(within(strip).getByText('Flickering Hound')).toBeInTheDocument();
    });
  });

  it('labels the remedies order as fit, ownership and play rate, not quality (DEC-1000)', () => {
    render(<Apothecary apothecary={makeApothecary()} />);
    const label =
      'top 30 by archetype fit, cards we own and EDHREC play rate · not a quality order';
    expect(screen.getByText(`${label} · gap-addressers floated`)).toBeInTheDocument();
    expect(screen.queryByText(/top 30 candidates/i)).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /card draw/i, pressed: false }));
    expect(screen.getByText(`${label} · filtered: Card Draw`)).toBeInTheDocument();
  });
});
