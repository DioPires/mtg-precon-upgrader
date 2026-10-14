import { describe, expect, it } from 'vitest';
import { render } from '@testing-library/react';
import { Performance } from '../../components/organisms/Performance';
import type { DeckCurveEntry } from '../../data/types';

// titan-convergence's eight chart columns.
const CURVE: DeckCurveEntry[] = [
  { cmc: 'Lands', n: 38, peak: true },
  { cmc: 'Ramp', n: 20, peak: false },
  { cmc: 'Engine', n: 14, peak: false },
  { cmc: 'Win-Cons', n: 10, peak: false },
  { cmc: 'Spot Removal', n: 4, peak: false },
  { cmc: 'Protection', n: 4, peak: false },
  { cmc: 'Board Wipes', n: 2, peak: false },
  { cmc: 'Recursion', n: 2, peak: false },
];

function renderChart(curve: DeckCurveEntry[]) {
  const { container } = render(
    <Performance curve={curve} func={[]} sources={[]} health={null} composition={null} assessment={null} />,
  );
  return [...container.querySelectorAll<HTMLElement>('.gv1-curve-col')];
}

describe('Performance role chart', () => {
  it('renders each role with its count and its label', () => {
    const cols = renderChart(CURVE);

    expect(cols).toHaveLength(CURVE.length);
    cols.forEach((col, i) => {
      expect(col.querySelector('.gv1-curve-n')).toHaveTextContent(new RegExp(`^${CURVE[i].n}$`));
      expect(col.querySelector('.gv1-curve-l')).toHaveTextContent(CURVE[i].cmc);
    });
  });

  // The count is positioned from the top of its own bar (DEC-1064). Outside
  // the bar it has no positioned ancestor in the chart and lands at the top
  // of the page, under the topbar. It is set in the 11px mono type of the
  // labels (DEC-1074): the spec reads its line's height, not its face.
  it('puts each count inside its bar', () => {
    for (const col of renderChart(CURVE)) {
      const bar = col.querySelector('.gv1-curve-bar')!;
      const count = col.querySelector<HTMLElement>('.gv1-curve-n');
      expect(bar).toContainElement(count);
      expect(count).toHaveClass('gv1-mono-xs');
    }
  });

  it('sizes each bar by its share of the largest count and marks the peak', () => {
    const cols = renderChart(CURVE);
    const bar = (i: number) => cols[i].querySelector<HTMLElement>('.gv1-curve-bar')!;

    expect(bar(0).style.height).toBe('100%');
    expect(parseFloat(bar(1).style.height)).toBeCloseTo((20 / 38) * 100, 5);
    expect(bar(4).style.height).toBe(bar(5).style.height);
    expect(cols.map((c) => c.classList.contains('gv1-peak'))).toEqual(CURVE.map((c) => c.peak));
  });

  it('keeps a role with no cards: a 0 count on a bar of no height', () => {
    const cols = renderChart([...CURVE.slice(0, 7), { cmc: 'Tutors', n: 0, peak: false }]);
    const empty = cols[7];

    expect(empty.querySelector('.gv1-curve-n')).toHaveTextContent(/^0$/);
    expect(empty.querySelector<HTMLElement>('.gv1-curve-bar')!.style.height).toBe('0%');
  });
});
