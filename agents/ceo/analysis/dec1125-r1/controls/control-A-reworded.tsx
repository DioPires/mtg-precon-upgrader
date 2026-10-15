import { afterEach, beforeEach, describe, expect, it, vi, type MockInstance } from 'vitest';
import { fireEvent, render, screen, within } from '@testing-library/react';
import { Apothecary } from '../../components/organisms/Apothecary';
import type { DeckApothecary, DeckPin, RawCandidate, RawMetricsGap } from '../../data/types';

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

function gridNames(container: HTMLElement): (string | null)[] {
  return [...container.querySelectorAll('.gv1-apo-remedies .gv1-apo-remedy-name')].map((n) => n.textContent);
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
      expect(within(entry).getByText('board pick')).toHaveClass('gv1-apo-tag', 'gv1-apo-tag-pinned');
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

      // DEC-1068 — the status line speaks the same words; this reads the visible empty state.
      expect(screen.getByText(/no remedies match/i, { selector: '.gv1-empty span' })).toBeInTheDocument();
      const strip = screen.getByRole('region', { name: 'Board picks' });
      expect(within(strip).getByText('Flickering Hound')).toBeInTheDocument();
    });
  });

  describe('resilience maladies (DEC-1007)', () => {
    // The anvil-chorus gaps[] as committed 2026-10-12: one role gap, two resilience gaps.
    const TUTOR: RawMetricsGap = { role: 'tutor', actual: 1, target: 4, score: 25 };
    const RECURSION: RawMetricsGap = {
      resilience_component: 'recursion',
      score_pct: 33,
      max: 30,
      actual: 1,
      target: 3,
      wincon_style: 'combat',
    };
    const REDUNDANCY: RawMetricsGap = {
      resilience_component: 'redundancy',
      score_pct: 50,
      max: 25,
      lines: 2,
      floor: 1,
      target: 3,
      wincon_style: 'combat',
    };

    const chips = (container: HTMLElement) => [...container.querySelectorAll<HTMLElement>('.gv1-apo-malady')];
    const part = (chip: HTMLElement, cls: string) => chip.querySelector(cls)?.textContent ?? null;

    // React reports a missing or duplicate key through console.error.
    let errors: MockInstance;
    beforeEach(() => {
      errors = vi.spyOn(console, 'error').mockImplementation(() => {});
    });
    afterEach(() => {
      errors.mockRestore();
    });

    it('labels a resilience gap beside a role gap and logs no key warning', () => {
      const { container } = render(
        <Apothecary apothecary={makeApothecary({ maladies: [TUTOR, RECURSION, REDUNDANCY] })} />,
      );

      const [tutor, recursion, redundancy] = chips(container);
      expect(chips(container)).toHaveLength(3);
      expect(part(tutor, '.gv1-apo-malady-label')).toBe('Tutors');
      expect(part(tutor, '.gv1-apo-malady-fig')).toBe('1 / 4');
      expect(part(recursion, '.gv1-apo-malady-kind')).toBe('resilience');
      expect(part(recursion, '.gv1-apo-malady-label')).toBe('Recursion');
      expect(part(recursion, '.gv1-apo-malady-fig')).toBe('1 / 3');
      expect(part(redundancy, '.gv1-apo-malady-label')).toBe('Redundancy');
      expect(part(redundancy, '.gv1-apo-malady-fig')).toBe('2 / 3 lines');
      // DEC-1077 — the count first, the rest dim, as on a role chip.
      expect(part(redundancy, '.gv1-apo-malady-fig .gv1-dim')).toBe(' / 3 lines');

      // score_pct on the role chips' thresholds: 33 is bad, 50 is warn.
      expect(recursion).toHaveClass('gv1-apo-tier-bad');
      expect(redundancy).toHaveClass('gv1-apo-tier-warn');
      expect(errors).not.toHaveBeenCalled();
    });

    it('renders a resilience gap as a static chip that leaves the remedy grid alone', () => {
      const { container } = render(
        <Apothecary apothecary={makeApothecary({ maladies: [TUTOR, RECURSION] })} />,
      );
      const before = gridNames(container);
      const recursion = chips(container)[1];

      expect(recursion.tagName).not.toBe('BUTTON');
      expect(recursion).not.toHaveAttribute('aria-pressed');
      expect(screen.queryByRole('button', { name: /recursion/i })).not.toBeInTheDocument();
      expect(screen.getAllByRole('button', { pressed: false })).toHaveLength(1);

      fireEvent.click(recursion);

      expect(gridNames(container)).toEqual(before);
      expect(screen.queryByRole('button', { name: /clear filter/i })).not.toBeInTheDocument();
      expect(screen.getByText(/gap-addressers floated/)).toBeInTheDocument();
    });

    it('keeps the role filter working next to a resilience chip', () => {
      const { container } = render(
        <Apothecary
          apothecary={makeApothecary({
            maladies: [{ role: 'card-draw', actual: 4, target: 10, score: 40 }, RECURSION],
          })}
        />,
      );
      fireEvent.click(screen.getByRole('button', { name: /card draw/i, pressed: false }));
      expect(gridNames(container)).toEqual(['Rhystic Study']);
      expect(chips(container)).toHaveLength(2);
    });

    it('keys a role gap and a resilience gap of the same name apart', () => {
      // grave-dividends carries `protection` in both shapes.
      const { container } = render(
        <Apothecary
          apothecary={makeApothecary({
            maladies: [
              { role: 'protection', actual: 2.5, target: 4, score: 62 },
              { resilience_component: 'protection', score_pct: 62, max: 25, actual: 2.5, target: 4 },
            ],
          })}
        />,
      );

      const [role, resilience] = chips(container);
      expect(chips(container)).toHaveLength(2);
      expect(role.tagName).toBe('BUTTON');
      expect(part(role, '.gv1-apo-malady-kind')).toBeNull();
      expect(part(resilience, '.gv1-apo-malady-kind')).toBe('resilience');
      expect(part(resilience, '.gv1-apo-malady-label')).toBe('Protection');
      expect(part(resilience, '.gv1-apo-malady-fig')).toBe('2.5 / 4');
      expect(errors).not.toHaveBeenCalled();
    });

    // DEC-1077 — redundancy reads `lines / target lines`; `target` comes from the
    // script (floor + 2 today), and an entry from before PR #21 has none.
    it.each([
      ['reads the lines over the target', { lines: 3, floor: 2, target: 4 }, '3 / 4 lines'],
      ['reads the target from the entry, not floor + 2', { lines: 2, floor: 1, target: 4 }, '2 / 4 lines'],
      ['keeps lines and floor for an entry with no target', { lines: 2, floor: 1 }, '2 lines · floor 1'],
      ['says lines for a count of one', { lines: 1, floor: 1, target: 3 }, '1 / 3 lines'],
      ['takes its branch also when the entry carries actual', { actual: 2, target: 3, lines: 2, floor: 1 }, '2 / 3 lines'],
    ])('the redundancy chip %s', (_, entry, fig) => {
      const { container } = render(
        <Apothecary
          apothecary={makeApothecary({
            maladies: [{ resilience_component: 'redundancy', score_pct: 50, max: 25, ...entry }],
          })}
        />,
      );
      expect(part(chips(container)[0], '.gv1-apo-malady-fig')).toBe(fig);
    });

    // B1 of the DEC-1125 review: an entry that carries a target and no count
    // reads its percentage (mutant A13).

    it('reads the percentage for a resilience entry with a target and no count', () => {
      const { container } = render(
        <Apothecary
          apothecary={makeApothecary({
            maladies: [{ resilience_component: 'protection', score_pct: 40, max: 25, target: 4 }],
          })}
        />,
      );
      expect(part(chips(container)[0], '.gv1-apo-malady-fig')).toBe('40%');
    });

    // DEC-1125 B2 — mutants A9 and A10 (redundancy row) and A16 and A17 (actual row):
    // a figure written without fmtFigure.
    it.each([
      [{ resilience_component: 'redundancy', score_pct: 50, max: 25, lines: 2.34, floor: 1, target: 3.67 }, '2.3 / 3.7 lines'],
      [{ resilience_component: 'protection', score_pct: 40, max: 25, actual: 1.26, target: 2.71 }, '1.3 / 2.7'],
    ])('writes a resilience figure with at most one decimal (%#)', (entry, text) => {
      const { container } = render(
        <Apothecary apothecary={makeApothecary({ maladies: [entry] })} />,
      );
      expect(part(chips(container)[0], '.gv1-apo-malady-fig')).toBe(text);
    });

    it('falls back to the percentage and the raw name for a component it has no counts or label for', () => {
      const { container } = render(
        <Apothecary
          apothecary={makeApothecary({
            maladies: [
              { resilience_component: 'gy_second_hand', score_pct: 50, max: 20, actual: 3, target: 6 },
              { resilience_component: 'mana_denial', score_pct: 10, max: 15 },
            ],
          })}
        />,
      );

      const [gy, unknown] = chips(container);
      expect(part(gy, '.gv1-apo-malady-label')).toBe('Graveyard second hand');
      expect(part(gy, '.gv1-apo-malady-fig')).toBe('3 / 6');
      expect(part(unknown, '.gv1-apo-malady-label')).toBe('mana_denial');
      expect(part(unknown, '.gv1-apo-malady-fig')).toBe('10%');
      expect(unknown).toHaveClass('gv1-apo-tier-crit');
    });

    it('offers the filter hint only when a chip can filter', () => {
      const { unmount } = render(<Apothecary apothecary={makeApothecary({ maladies: [TUTOR, RECURSION] })} />);
      expect(screen.getByText('click to filter remedies')).toBeInTheDocument();
      unmount();

      // broodfire-hatchery: a recursion gap and nothing else.
      render(<Apothecary apothecary={makeApothecary({ maladies: [RECURSION] })} />);
      expect(screen.getByText('MALADIES')).toBeInTheDocument();
      expect(screen.queryByText('click to filter remedies')).not.toBeInTheDocument();
    });
  });

  describe('role filter over the full pool (DEC-1015)', () => {
    const TUTOR_GAP: RawMetricsGap = { role: 'tutor', actual: 1, target: 4, score: 25 };
    // anvil-chorus as committed 2026-10-12: the one tutor in a pool of 201 sits at rank 195.
    const OSWALD: RawCandidate = {
      name: 'Oswald Fiddlebender',
      cmc: 2,
      mana_cost: '{1}{W}',
      type_line: 'Legendary Creature — Gnome Artificer',
      score: 48.3,
      deck_role: 'tutor',
      mitigates_gap: 'tutor',
    };

    it('shows a role hit ranked below the top 30 when its chip is clicked', () => {
      const pool = [...fillers(40), OSWALD];
      const { container } = render(
        <Apothecary apothecary={makeApothecary({ maladies: [TUTOR_GAP], remedies: pool })} />,
      );
      expect(gridNames(container)).not.toContain('Oswald Fiddlebender');

      fireEvent.click(screen.getByRole('button', { name: /tutors/i, pressed: false }));

      expect(gridNames(container)).toEqual(['Oswald Fiddlebender']);
      expect(screen.queryByText(/no remedies match/i)).not.toBeInTheDocument();
      expect(screen.getByText(/· filtered: Tutors$/)).toBeInTheDocument();
    });

    it('matches on deck_role as well as mitigates_gap below the top 30', () => {
      const byRole: RawCandidate = { ...OSWALD, name: 'Role Only Tutor', score: 20, mitigates_gap: null };
      const pool = [...fillers(40), byRole, OSWALD];
      const { container } = render(
        <Apothecary apothecary={makeApothecary({ maladies: [TUTOR_GAP], remedies: pool })} />,
      );
      fireEvent.click(screen.getByRole('button', { name: /tutors/i, pressed: false }));

      // The gap-addresser floats above the role-only match, as in the unfiltered grid.
      expect(gridNames(container)).toEqual(['Oswald Fiddlebender', 'Role Only Tutor']);
    });

    it('cuts a filtered pool of more than 30 to its first 30', () => {
      const hits: RawCandidate[] = Array.from({ length: 35 }, (_, i) => ({
        name: `Tutor ${i + 1}`,
        cmc: 2,
        mana_cost: '{1}{B}',
        type_line: 'Sorcery',
        score: 50 - i,
        deck_role: 'tutor',
        // DEC-1028 — one gap-addresser below the cut: a sort before the cut would float `Tutor 33` in.
        mitigates_gap: i === 32 ? 'tutor' : null,
      }));
      const pool = [...fillers(10), ...hits];
      const { container } = render(
        <Apothecary apothecary={makeApothecary({ maladies: [TUTOR_GAP], remedies: pool })} />,
      );
      fireEvent.click(screen.getByRole('button', { name: /tutors/i, pressed: false }));

      expect(gridNames(container)).toEqual(hits.slice(0, 30).map((c) => c.name));
    });

    it('shows the empty state and the clear button when no card in the pool has the role', () => {
      // stampede-acres: a board-wipe gap and no board wipe among its 200 candidates.
      const { container } = render(
        <Apothecary
          apothecary={makeApothecary({
            maladies: [{ role: 'removal-board', actual: 2, target: 3, score: 67 }],
            remedies: fillers(40),
          })}
        />,
      );
      fireEvent.click(screen.getByRole('button', { name: /board wipes/i, pressed: false }));

      expect(container.querySelector('.gv1-empty')?.textContent).toBe('No remedies match Board Wipes.');
      // DEC-1028 — `.gv1-empty` is a grid: one child node keeps the sentence on one line.
      expect(container.querySelector('.gv1-empty')?.childNodes).toHaveLength(1);
      expect(remedyGrid(container)).toBeNull();

      fireEvent.click(screen.getByRole('button', { name: /clear filter/i }));
      expect(container.querySelector('.gv1-empty')).toBeNull();
      expect(gridNames(container)).toHaveLength(30);
    });

    it('moves focus to the chip it cleared when the clear button is used (DEC-1028)', () => {
      // Two role chips, the second one active: focus must land on that chip, not on the first.
      render(<Apothecary apothecary={makeApothecary()} />);
      fireEvent.click(screen.getByRole('button', { name: /card draw/i, pressed: false }));
      const chip = screen.getByRole('button', { name: /card draw/i, pressed: true });

      const clear = screen.getByRole('button', { name: /clear filter/i });
      // DEC-1052 — the `×` is hidden from the accessibility tree. A string name matches the whole name.
      expect(screen.getByRole('button', { name: 'Clear filter' })).toBe(clear);
      expect(clear).toHaveTextContent('Clear filter ×');
      clear.focus();
      fireEvent.click(clear);

      expect(screen.queryByRole('button', { name: /clear filter/i })).not.toBeInTheDocument();
      expect(document.activeElement).toBe(chip);
      expect(chip).toHaveAttribute('aria-pressed', 'false');
    });

    it('leaves the unfiltered grid at the top 30, gap-addressers first', () => {
      // Gap-addressers at ranks 5, 20 and 33: the cut drops rank 33 before the sort floats it.
      const gapAt: Record<number, string> = { 5: 'tutor', 20: 'tutor', 33: 'tutor' };
      const pool = fillers(35).map((c, i) => (gapAt[i + 1] ? { ...c, mitigates_gap: gapAt[i + 1] } : c));
      const { container } = render(
        <Apothecary apothecary={makeApothecary({ maladies: [TUTOR_GAP], remedies: pool })} />,
      );

      const rest = Array.from({ length: 30 }, (_, i) => i + 1).filter((n) => n !== 5 && n !== 20);
      expect(gridNames(container)).toEqual(['Filler 5', 'Filler 20', ...rest.map((n) => `Filler ${n}`)]);
      expect(gridNames(container)).toHaveLength(30);
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

  describe('filter status line (DEC-1068)', () => {
    const BOARD_WIPE_GAP: RawMetricsGap = { role: 'removal-board', actual: 2, target: 3, score: 67 };

    function statusLine(container: HTMLElement): HTMLElement {
      return within(container.querySelector('.gv1-apothecary') as HTMLElement).getByRole('status');
    }

    function gridCount(container: HTMLElement): number {
      return container.querySelectorAll('.gv1-apo-remedies article.gv1-apo-remedy').length;
    }

    it('is mounted and empty at load', () => {
      const { container } = render(<Apothecary apothecary={makeApothecary()} />);
      const status = statusLine(container);
      expect(status).toHaveAttribute('aria-live', 'polite');
      expect(status).toHaveClass('gv1-sr-only');
      expect(status.textContent).toBe('');
    });

    it('names the role and counts the grid after a chip press, not the board picks', () => {
      const pool = [...makeApothecary().remedies, HOUND];
      const { container } = render(
        <Apothecary apothecary={makeApothecary({ remedies: pool, pins: [pinFor(pool, HOUND)] })} />,
      );
      const status = statusLine(container);

      fireEvent.click(screen.getByRole('button', { name: /ramp/i, pressed: false }));
      expect(gridCount(container)).toBe(2);
      expect(container.querySelectorAll('.gv1-apo-pin')).toHaveLength(1);
      expect(status.textContent).toBe('Filtered by Ramp: 2 remedies.');

      fireEvent.click(screen.getByRole('button', { name: /card draw/i, pressed: false }));
      expect(gridCount(container)).toBe(1);
      expect(status.textContent).toBe('Filtered by Card Draw: 1 remedy.');
    });

    it('speaks the empty-state words when the filter matches nothing', () => {
      const { container } = render(
        <Apothecary apothecary={makeApothecary({ maladies: [BOARD_WIPE_GAP], remedies: fillers(40) })} />,
      );
      fireEvent.click(screen.getByRole('button', { name: /board wipes/i, pressed: false }));

      expect(statusLine(container).textContent).toBe('No remedies match Board Wipes.');
      expect(statusLine(container).textContent).toBe(container.querySelector('.gv1-empty')?.textContent);
    });

    it('says the filter is cleared and counts the whole grid after Clear filter', () => {
      const { container } = render(
        <Apothecary apothecary={makeApothecary({ maladies: [BOARD_WIPE_GAP], remedies: fillers(40) })} />,
      );
      fireEvent.click(screen.getByRole('button', { name: /board wipes/i, pressed: false }));
      fireEvent.click(screen.getByRole('button', { name: /clear filter/i }));

      expect(gridCount(container)).toBe(30);
      expect(statusLine(container).textContent).toBe('Filter cleared: 30 remedies.');
    });

    it('gives the same text for a second press on the active chip as for Clear filter', () => {
      const { container } = render(<Apothecary apothecary={makeApothecary()} />);
      const status = statusLine(container);

      fireEvent.click(screen.getByRole('button', { name: /ramp/i, pressed: false }));
      fireEvent.click(screen.getByRole('button', { name: /clear filter/i }));
      const byClear = status.textContent;

      fireEvent.click(screen.getByRole('button', { name: /ramp/i, pressed: false }));
      expect(status.textContent).toBe('Filtered by Ramp: 2 remedies.');
      fireEvent.click(screen.getByRole('button', { name: /ramp/i, pressed: true }));

      expect(byClear).toBe('Filter cleared: 3 remedies.');
      expect(status.textContent).toBe(byClear);
    });

    it('goes empty, not stale, when another deck renders into the same Apothecary', () => {
      const { container, rerender } = render(<Apothecary apothecary={makeApothecary()} />);
      fireEvent.click(screen.getByRole('button', { name: /ramp/i, pressed: false }));
      expect(statusLine(container).textContent).toBe('Filtered by Ramp: 2 remedies.');

      // The next deck has a ramp gap too, so the filter stays set on its grid.
      const nextDeck = makeApothecary({ remedies: fillers(5).map((c) => ({ ...c, deck_role: 'ramp' })) });
      rerender(<Apothecary apothecary={nextDeck} />);
      expect(gridCount(container)).toBe(5);
      expect(statusLine(container).textContent).toBe('');
    });

    describe('a filter carried from another deck, and a count of zero (DEC-1097)', () => {
      const RAMP_GAP: RawMetricsGap = { role: 'ramp', actual: 6, target: 10, score: 60 };

      function card(i: number, role?: string): RawCandidate {
        return { name: `Card ${i}`, cmc: 2, mana_cost: '{2}', type_line: 'Artifact', score: 40 - i, deck_role: role, mitigates_gap: null };
      }

      function deck(remedies: RawCandidate[]): DeckApothecary {
        return {
          diagnosis: {
            score: 72,
            scoreNormalized: null,
            methodology: 'deck-metrics-v1',
            generatedAt: '2026-05-01T00:00:00Z',
            mirrorUpdatedAt: '2026-05-01T00:00:00Z',
            components: { manabase_health: { score: 80 } },
          },
          maladies: [RAMP_GAP],
          remedies,
          pins: [],
        } as DeckApothecary;
      }

      // Kills S1 (clearFilter calls setFilterRole(null)) and M2 (filterBy(null) skips setFilteredDeck).
      it('speaks the cleared result when Clear filter follows a filter carried from another deck', () => {
        const { container, rerender } = render(<Apothecary apothecary={deck([card(1, 'ramp'), card(2)])} />);
        fireEvent.click(screen.getByRole('button', { name: /ramp/i, pressed: false }));
        expect(statusLine(container).textContent).toBe('Filtered by Ramp: 1 remedy.');

        rerender(<Apothecary apothecary={deck([card(1, 'ramp'), card(2, 'ramp'), card(3)])} />);
        expect(screen.getByRole('button', { name: /ramp/i, pressed: true })).toBeInTheDocument();
        expect(statusLine(container).textContent).toBe('');

        fireEvent.click(screen.getByRole('button', { name: /clear filter/i }));
        expect(statusLine(container).textContent).toBe('Filter cleared: 3 remedies.');
      });

      // Kills M2 (filterBy(null) skips setFilteredDeck): the second-press path of the active chip.
      it('speaks the cleared result when a press on the active chip follows a filter carried from another deck', () => {
        const { container, rerender } = render(<Apothecary apothecary={deck([card(1, 'ramp'), card(2)])} />);
        fireEvent.click(screen.getByRole('button', { name: /ramp/i, pressed: false }));

        rerender(<Apothecary apothecary={deck([card(1, 'ramp'), card(2, 'ramp'), card(3)])} />);
        expect(statusLine(container).textContent).toBe('');

        fireEvent.click(screen.getByRole('button', { name: /ramp/i, pressed: true }));
        expect(statusLine(container).textContent).toBe('Filter cleared: 3 remedies.');
      });

      // Kills S3 (the plural reads `pool.length > 1`): a count of zero after Clear filter.
      it('reads "0 remedies" after Clear filter on a deck with no remedies', () => {
        const { container } = render(<Apothecary apothecary={deck([])} />);
        fireEvent.click(screen.getByRole('button', { name: /ramp/i, pressed: false }));
        expect(statusLine(container).textContent).toBe('No remedies match Ramp.');

        fireEvent.click(screen.getByRole('button', { name: /clear filter/i }));
        expect(statusLine(container).textContent).toBe('Filter cleared: 0 remedies.');
      });
    });
  });

  describe('role labels from the shared map (DEC-1077)', () => {
    function remedy(name: string, deck_role: string, mitigates_gap: string | null = null): RawCandidate {
      return { name, cmc: 2, mana_cost: '{2}', type_line: 'Artifact', score: 40, deck_role, mitigates_gap };
    }

    function roleTags(container: HTMLElement): (string | null)[] {
      return [...container.querySelectorAll('.gv1-apo-remedies .gv1-apo-tag-role')].map((t) => t.textContent);
    }

    it('tags a land remedy "Lands", not the raw key', () => {
      const { container } = render(
        <Apothecary apothecary={makeApothecary({ remedies: [remedy('Command Tower', 'land')] })} />,
      );
      expect(roleTags(container)).toEqual(['Lands']);
    });

    it('tags a utility remedy "Utility", not the raw key', () => {
      const { container } = render(
        <Apothecary apothecary={makeApothecary({ remedies: [remedy('Mind Stone', 'utility')] })} />,
      );
      expect(roleTags(container)).toEqual(['Utility']);
    });

    it('reads "Win-Cons" on the wincon chip, in the status line and in the tags after a press', () => {
      const { container } = render(
        <Apothecary
          apothecary={makeApothecary({
            maladies: [{ role: 'wincon', actual: 1, target: 3, score: 33 }],
            remedies: [remedy('Craterhoof Behemoth', 'threat', 'wincon'), remedy('Filler', 'ramp')],
          })}
        />,
      );
      const chip = screen.getByRole('button', { name: /win-cons/i, pressed: false });
      expect(chip.querySelector('.gv1-apo-malady-label')?.textContent).toBe('Win-Cons');

      fireEvent.click(chip);
      const status = within(container.querySelector('.gv1-apothecary') as HTMLElement).getByRole('status');
      expect(status.textContent).toBe('Filtered by Win-Cons: 1 remedy.');
      expect(screen.getByText(/ · filtered: Win-Cons$/)).toBeInTheDocument();
      expect(container.querySelector('.gv1-apo-tag-addresses')?.textContent).toBe('addresses · Win-Cons');
      expect(roleTags(container)).toEqual(['Threats']);
    });

    // DEC-1125 B3 — the six mutants that drop `|| key` from a ROLE_LABEL use.
    describe('a role key that the shared map does not hold reads raw', () => {
      const LIFEGAIN = { role: 'lifegain', actual: 1, target: 3, score: 33 };

      it('on the chip, in the status line, in "filtered:" and in both tags', () => {
        const { container } = render(
          <Apothecary
            apothecary={makeApothecary({
              maladies: [LIFEGAIN],
              remedies: [remedy('Soul Warden', 'storm', 'lifegain'), remedy('Filler', 'ramp')],
            })}
          />,
        );
        const chip = screen.getByRole('button', { name: /lifegain/, pressed: false });
        expect(chip.querySelector('.gv1-apo-malady-label')?.textContent).toBe('lifegain');

        fireEvent.click(chip);
        const status = within(container.querySelector('.gv1-apothecary') as HTMLElement).getByRole('status');
        expect(status.textContent).toBe('Filtered by lifegain: 1 remedy.');
        expect(screen.getByText(/ · filtered: lifegain$/)).toBeInTheDocument();
        expect(container.querySelector('.gv1-apo-tag-addresses')?.textContent).toBe('addresses · lifegain');
        expect(container.querySelector('.gv1-apo-remedies .gv1-apo-tag-role')?.textContent).toBe('storm');
      });

      it('in the empty state', () => {
        const { container } = render(
          <Apothecary apothecary={makeApothecary({ maladies: [LIFEGAIN], remedies: [remedy('Filler', 'ramp')] })} />,
        );
        fireEvent.click(screen.getByRole('button', { name: /lifegain/, pressed: false }));
        expect(container.querySelector('.gv1-empty')?.textContent).toBe('No remedies match lifegain.');
      });
    });
  });
});
