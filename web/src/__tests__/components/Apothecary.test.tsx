import { describe, expect, it } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { Apothecary } from '../../components/organisms/Apothecary';
import type { DeckApothecary } from '../../data/types';

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
  };
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
});
