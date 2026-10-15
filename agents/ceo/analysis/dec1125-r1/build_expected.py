"""DEC-1125 fix round 1 (route A): build the expected web/src/__tests__/components/Apothecary.test.tsx.

Input: the head's file (git show 854aad6:web/src/__tests__/components/Apothecary.test.tsx,
blob 7cb69550). It moves the reviewer's kill file (reviewer/Apothecary.dec1125-kill.test.tsx,
blob 2d03ca52, the code block of verdict 49e08dfa) into the file, as the verdict asks: with the
file's own makeApothecary and helpers. Each edit asserts its anchor.

  K1 (B1) and K2 (B2) go into `resilience maladies (DEC-1007)`, after the redundancy table.
          The only change to the reviewer's text: `fig(container)` becomes
          `part(chips(container)[0], '.gv1-apo-malady-fig')`, the block's own reading of the
          first chip's figure (the same element).
  K3 (B3) goes into `role labels from the shared map (DEC-1077)`, after the Win-Cons case, as the
          reviewer's nested describe. Its `remedy` helper is dropped: the block already holds the
          same function. Every other line is the reviewer's.

Usage: python3 build_expected.py <head file> <out file>
"""
import sys
from pathlib import Path

src = Path(sys.argv[1]).read_text()


def insert_after(text: str, anchor: str, new: str) -> str:
    assert text.count(anchor) == 1, (anchor[:60], text.count(anchor))
    return text.replace(anchor, anchor + new)


# 1. K1 and K2: after the redundancy table, before the fallback case.
src = insert_after(src, """    ])('the redundancy chip %s', (_, entry, fig) => {
      const { container } = render(
        <Apothecary
          apothecary={makeApothecary({
            maladies: [{ resilience_component: 'redundancy', score_pct: 50, max: 25, ...entry }],
          })}
        />,
      );
      expect(part(chips(container)[0], '.gv1-apo-malady-fig')).toBe(fig);
    });
""", """
    // DEC-1125 B1 — mutant A13: `g.actual != null || g.target != null` in the actual branch.
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
      const { container } = render(<Apothecary apothecary={makeApothecary({ maladies: [entry] })} />);
      expect(part(chips(container)[0], '.gv1-apo-malady-fig')).toBe(text);
    });
""")

# 2. K3: after the Win-Cons case, last in the role labels block.
src = insert_after(src, """      expect(container.querySelector('.gv1-apo-tag-addresses')?.textContent).toBe('addresses · Win-Cons');
      expect(roleTags(container)).toEqual(['Threats']);
    });
""", """
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
""")

Path(sys.argv[2]).write_text(src)
