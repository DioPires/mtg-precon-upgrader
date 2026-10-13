// DEC-1064: the role chart shows each role's count above its bar, and every
// bar stands on one baseline.
//
// The counts were absolutely positioned with no positioned ancestor inside
// the chart, so all eight sat at the top of the page under the topbar and
// were never seen. Above 560px the chart was a flex row of columns, and a
// column whose label wrapped to two lines had a shorter bar area: two roles
// with the same count drew bars of different heights, and the two-line
// columns ended 14px above the rest.
//
// titan-convergence has both pairs that showed it: Spot Removal and
// Protection at 4 cards, Board Wipes and Recursion at 2.

import { expect, test, type Page } from './support/test';

const DECK = 'titan-convergence';
const WIDTHS = [390, 1280];

type Column = {
  label: string;
  count: number;
  /** What `elementFromPoint` returns at the centre of the count. */
  hit: string;
  hitIsCount: boolean;
  countBottom: number;
  countCentre: number;
  barTop: number;
  barBottom: number;
  barLeft: number;
  barRight: number;
  barHeight: number;
  labelLeft: number;
  labelRight: number;
  // Review additions (DEC-1070).
  countTop: number;
  chartTop: number;
  chartBottom: number;
  labelTop: number;
  labelBottom: number;
  /** The label's text, as drawn: the union of its line boxes. */
  textLeft: number;
  textRight: number;
  labelLines: number;
};

// The selector's smooth scroll is still running when the guide first paints,
// and the fallback faces set the labels at another width. Resolve once the
// web fonts are in and the page has not moved for 300ms.
async function openSettled(page: Page): Promise<void> {
  await page.goto(`/deck/${DECK}`);
  await page.locator('.gv1-curve').waitFor();
  await page.evaluate(async () => {
    await document.fonts.ready;
    await new Promise<void>((resolve) => {
      const started = Date.now();
      let last = window.scrollY;
      let still = 0;
      const tick = () => {
        still = window.scrollY === last ? still + 1 : 0;
        last = window.scrollY;
        if (still < 6 && Date.now() - started < 5000) {
          setTimeout(tick, 50);
          return;
        }
        resolve();
      };
      setTimeout(tick, 50);
    });
  });
}

// Bring each count to the middle of the viewport before the hit test:
// `elementFromPoint` answers null for a point outside the viewport. The boxes
// are then read in one pass, at one scroll position.
async function readChart(page: Page): Promise<Column[]> {
  return page.evaluate(() => {
    const cols = [...document.querySelectorAll<HTMLElement>('.gv1-curve-col')];
    const hits = cols.map((col) => {
      const count = col.querySelector<HTMLElement>('.gv1-curve-n')!;
      count.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'instant' });
      const c = count.getBoundingClientRect();
      const hit = document.elementFromPoint(c.left + c.width / 2, c.top + c.height / 2);
      return {
        hit: hit ? `${hit.tagName.toLowerCase()}.${hit.classList[0] ?? ''}` : 'nothing',
        hitIsCount: hit === count,
      };
    });
    const chart = document.querySelector<HTMLElement>('.gv1-curve')!.getBoundingClientRect();
    return cols.map((col, i) => {
      const count = col.querySelector<HTMLElement>('.gv1-curve-n')!;
      const range = document.createRange();
      range.selectNodeContents(col.querySelector('.gv1-curve-l')!);
      const lines = [...range.getClientRects()];
      const c = count.getBoundingClientRect();
      const b = col.querySelector<HTMLElement>('.gv1-curve-bar')!.getBoundingClientRect();
      const l = col.querySelector<HTMLElement>('.gv1-curve-l')!.getBoundingClientRect();
      return {
        label: col.querySelector('.gv1-curve-l')!.textContent ?? '',
        count: Number(count.textContent),
        ...hits[i],
        countBottom: c.bottom,
        countCentre: c.left + c.width / 2,
        barTop: b.top,
        barBottom: b.bottom,
        barLeft: b.left,
        barRight: b.right,
        barHeight: b.height,
        labelLeft: l.left,
        labelRight: l.right,
        countTop: c.top,
        chartTop: chart.top,
        chartBottom: chart.bottom,
        labelTop: l.top,
        labelBottom: l.bottom,
        textLeft: Math.min(...lines.map((r) => r.left)),
        textRight: Math.max(...lines.map((r) => r.right)),
        labelLines: new Set(lines.map((r) => Math.round(r.top))).size,
      };
    });
  });
}

const px = (n: number) => `${Math.round(n * 100) / 100}px`;

for (const width of WIDTHS) {
  test.describe(`DEC-1064 @ ${width}px`, () => {
    test.use({ viewport: { width, height: 900 } });

    test('the role chart shows each count above its bar, and equal counts draw equal bars on one baseline', async ({ page }) => {
      await openSettled(page);
      const cols = await readChart(page);
      expect(cols).toHaveLength(8);

      const name = (c: Column) => `${c.label} ${c.count}`;
      const peak = cols.reduce((a, b) => (b.count > a.count ? b : a));

      // The count is the element under its own centre, not the topbar.
      expect
        .soft(
          cols.filter((c) => !c.hitIsCount).map((c) => `${name(c)}: ${c.hit}`),
          'counts hidden under another element',
        )
        .toEqual([]);

      // It sits just above its bar (a 4px gap), centred on it.
      expect
        .soft(
          cols
            .filter((c) => {
              const gap = c.barTop - c.countBottom;
              const off = c.countCentre - (c.barLeft + c.barRight) / 2;
              return Math.abs(gap - 4) > 0.5 || Math.abs(off) > 1;
            })
            .map((c) => `${name(c)}: ${px(c.barTop - c.countBottom)} above the bar`),
          'counts away from the top of their bar',
        )
        .toEqual([]);

      // Each bar is its count's share of the peak bar, so equal counts draw
      // equal bars.
      expect
        .soft(
          cols
            .filter((c) => Math.abs(c.barHeight - (peak.barHeight * c.count) / peak.count) > 0.5)
            .map((c) => `${name(c)}: ${px(c.barHeight)}, expected ${px((peak.barHeight * c.count) / peak.count)}`),
          'bars out of proportion to their counts',
        )
        .toEqual([]);

      expect
        .soft(
          cols.filter((c) => Math.abs(c.barBottom - peak.barBottom) > 0.5).map((c) => `${name(c)}: ${px(c.barBottom - peak.barBottom)}`),
          'bars off the baseline of the peak bar',
        )
        .toEqual([]);

      // A label wider than its column would run into the next one.
      expect
        .soft(
          cols
            .filter((c) => c.labelLeft < c.barLeft - 0.5 || c.labelRight > c.barRight + 0.5)
            .map((c) => `${name(c)}: label ${px(c.labelRight - c.labelLeft)}, column ${px(c.barRight - c.barLeft)}`),
          'labels wider than their column',
        )
        .toEqual([]);

      // --- Review additions (DEC-1070) ---
      const wide = width > 560;

      // A1. The bar row is 130px above 560px and 120px from 560px down, and
      // the peak bar fills it.
      expect.soft(px(peak.barHeight), 'height of the peak bar').toBe(wide ? '130px' : '120px');

      // A3. The chart keeps 22px of padding above the bar row, and the peak's
      // count stands inside the chart's box. The room above the count is not
      // read as one value: it is the padding less the 4px gap and the count's
      // line, and no rule sets that line's height (14px in JetBrains Mono,
      // 13px in the fallback face).
      expect.soft(px(peak.barTop - peak.chartTop), 'padding above the peak bar').toBe('22px');
      expect.soft(peak.countTop - peak.chartTop, 'room above the count of the peak bar').toBeGreaterThanOrEqual(0);

      // A4. Columns are 8px apart above 560px and 4px apart from 560px down.
      expect
        .soft(
          cols
            .slice(1)
            .map((c, i) => ({ c, gap: c.barLeft - cols[i].barRight }))
            .filter(({ gap }) => Math.abs(gap - (wide ? 8 : 4)) > 0.5)
            .map(({ c, gap }) => `${name(c)}: ${px(gap)} after the bar before it`),
          'bars at the wrong distance from their neighbour',
        )
        .toEqual([]);

      // A5. Each label starts 8px under the bars above 560px (a 6px row gap and
      // a 2px margin) and 6px under them from 560px down.
      expect
        .soft(
          cols
            .filter((c) => Math.abs(c.labelTop - c.barBottom - (wide ? 8 : 6)) > 0.5)
            .map((c) => `${name(c)}: label ${px(c.labelTop - c.barBottom)} under its bar`),
          'labels at the wrong distance from their bar',
        )
        .toEqual([]);

      // A6. A label on one line is centred under its bar.
      expect
        .soft(
          cols
            .filter((c) => c.labelLines === 1)
            .filter((c) => Math.abs((c.textLeft + c.textRight) / 2 - (c.barLeft + c.barRight) / 2) > 0.5)
            .map((c) => `${name(c)}: text ${px((c.textLeft + c.textRight) / 2 - (c.barLeft + c.barRight) / 2)} off the centre of its bar`),
          'one-line labels off the centre of their bar',
        )
        .toEqual([]);

      // A7. The chart's box holds its labels.
      expect
        .soft(
          cols.filter((c) => c.labelBottom > c.chartBottom + 0.5).map((c) => `${name(c)}: ${px(c.labelBottom - c.chartBottom)} below the chart`),
          'labels below the bottom of the chart',
        )
        .toEqual([]);
    });
  });
}
