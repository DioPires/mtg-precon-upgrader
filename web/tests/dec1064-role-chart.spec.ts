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

import { expect, test, type Page } from '@playwright/test';

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
    return cols.map((col, i) => {
      const count = col.querySelector<HTMLElement>('.gv1-curve-n')!;
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
              return gap < 0 || gap > 6 || Math.abs(off) > 1;
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
    });
  });
}
