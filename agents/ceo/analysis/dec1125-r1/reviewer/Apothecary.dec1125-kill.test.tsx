// DEC-1125 kill cases for PR #45. Each case passes on the merged head and
// fails on the mutant that its comment names. The fix round moves them into
// Apothecary.test.tsx and uses that file's own makeApothecary and helpers.
import { describe, expect, it } from 'vitest';
import { fireEvent, render, screen, within } from '@testing-library/react';
import { Apothecary } from '../../components/organisms/Apothecary';
import type { DeckApothecary, RawCandidate } from '../../data/types';

function makeApothecary(over: Partial<DeckApothecary> = {}): DeckApothecary {
  return {
    diagnosis: {
      score: 72,
      scoreNormalized: null,
      methodology: 'deck-metrics-v1',
      generatedAt: '2026-05-01T00:00:00Z',
      mirrorUpdatedAt: '2026-05-01T00:00:00Z',
      components: {},
    },
    maladies: over.maladies ?? [],
    remedies: over.remedies ?? [],
    pins: [],
  };
}

const fig = (container: HTMLElement) => container.querySelector('.gv1-apo-malady .gv1-apo-malady-fig')?.textContent;

describe('DEC-1125 kill cases', () => {
  // B1 — mutant A13: `g.actual != null || g.target != null` in the actual branch.
  it('reads the percentage for a resilience entry with a target and no count', () => {
    const { container } = render(
      <Apothecary
        apothecary={makeApothecary({
          maladies: [{ resilience_component: 'protection', score_pct: 40, max: 25, target: 4 }],
        })}
      />,
    );
    expect(fig(container)).toBe('40%');
  });

  // B2 — mutants A9 and A10 (redundancy row) and A16 and A17 (actual row):
  // a figure written without fmtFigure.
  it.each([
    [{ resilience_component: 'redundancy', score_pct: 50, max: 25, lines: 2.34, floor: 1, target: 3.67 }, '2.3 / 3.7 lines'],
    [{ resilience_component: 'protection', score_pct: 40, max: 25, actual: 1.26, target: 2.71 }, '1.3 / 2.7'],
  ])('writes a resilience figure with at most one decimal (%#)', (entry, text) => {
    const { container } = render(<Apothecary apothecary={makeApothecary({ maladies: [entry] })} />);
    expect(fig(container)).toBe(text);
  });

  // B3 — the six mutants that drop `|| key` from a ROLE_LABEL use.
  describe('a role key that the shared map does not hold reads raw', () => {
    function remedy(name: string, deck_role: string, mitigates_gap: string | null = null): RawCandidate {
      return { name, cmc: 2, mana_cost: '{2}', type_line: 'Artifact', score: 40, deck_role, mitigates_gap };
    }
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
