import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render } from '@testing-library/react';
import { Performance } from '../../components/organisms/Performance';
import type { DeckCurveEntry, RawAssessment } from '../../data/types';

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

function renderHead(assessment: RawAssessment | null, goldfishGames?: number, manaSimGames?: number) {
  const { container } = render(
    <Performance
      curve={[]}
      func={[]}
      sources={[]}
      health={null}
      composition={null}
      assessment={assessment}
      goldfishGames={goldfishGames}
      manaSimGames={manaSimGames}
    />,
  );
  return container;
}

// The heading note, or null when the heading has none.
const note = (container: HTMLElement) => container.querySelector('.gv1-section-head > .gv1-mono-xs');

// The heading note, which the case needs.
function requireNote(container: HTMLElement): Element {
  const found = note(container);
  if (!found) throw new Error('no heading note');
  return found;
}

// The MANA tile's lines, top to bottom.
function manaTile(container: HTMLElement): string[] {
  const tile = [...container.querySelectorAll('.gv1-kpi')].find((k) => k.firstElementChild?.textContent === 'MANA');
  if (!tile) throw new Error('no MANA tile');
  return [...tile.children].map((c) => c.textContent ?? '');
}

// A file's assessment with `share` as its manaAdequacyShare, whatever its shape:
// the app reads simulation.json as parsed, with no check of its types.
const withShare = (share: unknown): RawAssessment =>
  Object.assign(JSON.parse('{"manaAdequacy": "near adequate", "mulliganVerdict": "excellent"}'), { manaAdequacyShare: share });

describe('Performance header', () => {
  // The counts are written as approved ("10,000") whatever the browser's
  // locale. For each case a number formatted with no locale named comes out
  // German ("10.000"), so the cases fail on a count formatted in the
  // process's own locale, whichever locale the suite runs under.
  beforeEach(() => {
    const format = Number.prototype.toLocaleString;
    vi.spyOn(Number.prototype, 'toLocaleString').mockImplementation(function (
      this: number,
      locales?: Intl.LocalesArgument,
      options?: Intl.NumberFormatOptions,
    ) {
      return format.call(this, locales ?? 'de-DE', options);
    });
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('names two game counts, each from its own simulation', () => {
    const counts = [...requireNote(renderHead(null, 2500, 40000)).querySelectorAll('.gv1-perf-count')].map((c) => c.textContent);
    // A no-break space after each separator keeps it beside its number.
    expect(counts).toEqual(['·\u00a02,500 goldfish games', '·\u00a040,000 mana-sim games']);
  });

  it('reads as the approved text', () => {
    expect(note(renderHead(null, 10000, 100000))).toHaveTextContent(/^· 10,000 goldfish games · 100,000 mana-sim games$/);
  });

  it('shows no count a file does not give', () => {
    expect(note(renderHead(null, undefined, 40000))).toHaveTextContent(/^· 40,000 mana-sim games$/);
    expect(note(renderHead(null, 2500, undefined))).toHaveTextContent(/^· 2,500 goldfish games$/);
    expect(note(renderHead(null))).toBeNull();
  });

  it('shows a count only when it is a whole number of 1 or more', () => {
    // A string, NaN, a negative count, zero and a fraction are each left out.
    for (const bad of [JSON.parse('"10000"'), Number.NaN, -5, 0, 2.5]) {
      expect(note(renderHead(null, bad, 40000)), String(bad)).toHaveTextContent(/^· 40,000 mana-sim games$/);
      expect(note(renderHead(null, 2500, bad)), String(bad)).toHaveTextContent(/^· 2,500 goldfish games$/);
    }
  });
});

describe('Performance MANA tile', () => {
  it('shows under the label the share that decided it, to one decimal', () => {
    expect(manaTile(renderHead(withShare({ turn: 5, manaTarget: 6, share: 50 })))).toEqual([
      'MANA',
      'near adequate',
      '50.0% of games have 6 or more mana on turn 5',
      'mulligan · excellent',
    ]);
    expect(manaTile(renderHead(withShare({ turn: 4, manaTarget: 7, share: 37.4 })))[2]).toBe(
      '37.4% of games have 7 or more mana on turn 4',
    );
    // A target of 0 is a whole number of 0 or more.
    expect(manaTile(renderHead(withShare({ turn: 4, manaTarget: 0, share: 100 })))[2]).toBe(
      '100.0% of games have 0 or more mana on turn 4',
    );
  });

  it('keeps the tile to the label and the mulligan line when a file has no share', () => {
    const container = renderHead({ manaAdequacy: 'light', mulliganVerdict: 'acceptable', commanderTiming: 'on curve' });
    expect(manaTile(container)).toEqual(['MANA', 'light', 'mulligan · acceptable']);
  });

  it('shows the share line only for turn 4 or 5, a target of 0 or more whole mana and a share from 0 to 100', () => {
    const bad: Record<string, unknown> = {
      'missing share': { turn: 4, manaTarget: 6 },
      'missing turn': { manaTarget: 6, share: 50.2 },
      'missing target': { turn: 4, share: 50.2 },
      'string share': { turn: 4, manaTarget: 6, share: '50.2' },
      'NaN share': { turn: 4, manaTarget: 6, share: Number.NaN },
      'negative share': { turn: 4, manaTarget: 6, share: -0.1 },
      'share over 100': { turn: 4, manaTarget: 6, share: 100.1 },
      'turn 6': { turn: 6, manaTarget: 6, share: 50.2 },
      'string turn': { turn: '4', manaTarget: 6, share: 50.2 },
      'fractional target': { turn: 4, manaTarget: 5.5, share: 50.2 },
      'negative target': { turn: 4, manaTarget: -1, share: 50.2 },
      'a number': 50.2,
    };
    for (const [label, share] of Object.entries(bad)) {
      expect(manaTile(renderHead(withShare(share))), label).toEqual(['MANA', 'near adequate', 'mulligan · excellent']);
    }
  });
});

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
