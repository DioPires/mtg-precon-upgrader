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
//
// DEC-1074: each bar is 24px wide above 560px, so equal counts also draw equal
// areas; the count's line is 14px high in every face, so the case runs with
// the web fonts and without them; and the Performance blocks stack until the
// chart can hold slivers' eight labels.

import { expect, test, type Page } from './support/test';

const DECK = 'titan-convergence';
const WIDTHS = [390, 1280];
// Each case runs as the file sets the fonts, and again with them blocked.
const BLOCKED = [false, true];

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
  // DEC-1074. The column is the bar's wrap: the column element itself has
  // `display: contents` and no box.
  colLeft: number;
  colRight: number;
  barWidth: number;
};

// The selector's smooth scroll is still running when the guide first paints,
// and the fallback faces set the labels at another width. Resolve once the
// web fonts are in and the page has not moved for 300ms.
async function openSettled(page: Page, deck = DECK): Promise<void> {
  await page.goto(`/deck/${deck}`);
  await page.locator('.gv1-curve').waitFor();
  await settle(page);
}

async function settle(page: Page): Promise<void> {
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
      const w = col.querySelector<HTMLElement>('.gv1-curve-bar-wrap')!.getBoundingClientRect();
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
        colLeft: w.left,
        colRight: w.right,
        barWidth: b.width,
      };
    });
  });
}

const px = (n: number) => `${Math.round(n * 100) / 100}px`;

for (const { width, blocked } of BLOCKED.flatMap((blocked) => WIDTHS.map((width) => ({ width, blocked })))) {
  test.describe(`DEC-1064 @ ${width}px${blocked ? ', web fonts blocked' : ''}`, () => {
    test.use({ viewport: { width, height: 900 }, ...(blocked ? { fonts: 'blocked' as const } : {}) });

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
            .filter((c) => c.labelLeft < c.colLeft - 0.5 || c.labelRight > c.colRight + 0.5)
            .map((c) => `${name(c)}: label ${px(c.labelRight - c.labelLeft)}, column ${px(c.colRight - c.colLeft)}`),
          'labels wider than their column',
        )
        .toEqual([]);

      // --- Review additions (DEC-1070) ---
      const wide = width > 560;

      // A1. The bar row is 130px above 560px and 120px from 560px down, and
      // the peak bar fills it.
      expect.soft(px(peak.barHeight), 'height of the peak bar').toBe(wide ? '130px' : '120px');

      // A3. The chart keeps 22px of padding above the bar row, and the peak's
      // count stands inside the chart's box. The room above the count is the
      // padding less the 4px gap and the count's line. The line is 14px high
      // in every face (DEC-1074), so the room is 4px with the web fonts and
      // without them. Left normal, the line is 14px in JetBrains Mono and 13px
      // in the fallback face.
      expect.soft(px(peak.barTop - peak.chartTop), 'padding above the peak bar').toBe('22px');
      expect.soft(peak.countTop - peak.chartTop, 'room above the count of the peak bar').toBeGreaterThanOrEqual(0);
      expect.soft(px(peak.countTop - peak.chartTop), 'room above the count of the peak bar').toBe('4px');

      // A4. Columns are 8px apart above 560px and 4px apart from 560px down.
      // The gap is read between the columns: above 560px a bar is narrower
      // than its column, and the space between two bars differs for each pair
      // (DEC-1074).
      expect
        .soft(
          cols
            .slice(1)
            .map((c, i) => ({ c, gap: c.colLeft - cols[i].colRight }))
            .filter(({ gap }) => Math.abs(gap - (wide ? 8 : 4)) > 0.5)
            .map(({ c, gap }) => `${name(c)}: ${px(gap)} after the column before it`),
          'columns at the wrong distance from their neighbour',
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

      // A8 (DEC-1074). Above 560px each bar is 24px wide, so equal counts draw
      // equal areas whatever the width of their column. From 560px down the
      // columns are equal and each bar fills its own. Each bar is centred in
      // its column.
      expect
        .soft(
          cols
            .filter((c) => Math.abs(c.barWidth - (wide ? 24 : c.colRight - c.colLeft)) > 0.5)
            .map((c) => `${name(c)}: bar ${px(c.barWidth)}, column ${px(c.colRight - c.colLeft)}`),
          'bars of the wrong width',
        )
        .toEqual([]);
      expect
        .soft(
          cols
            .filter((c) => Math.abs((c.barLeft + c.barRight) / 2 - (c.colLeft + c.colRight) / 2) > 0.5)
            .map((c) => `${name(c)}: bar ${px((c.barLeft + c.barRight) / 2 - (c.colLeft + c.colRight) / 2)} off the centre of its column`),
          'bars off the centre of their column',
        )
        .toEqual([]);

      // A9 (DEC-1095). Each bar is painted: the peak in the rune colour with
      // its glow, every other bar in the dim rune colour without one.
      const paint = await page.evaluate(() => {
        const token = (name: string) => {
          const probe = document.createElement('div');
          probe.style.backgroundColor = `var(${name})`;
          document.body.append(probe);
          const colour = getComputedStyle(probe).backgroundColor;
          probe.remove();
          return colour;
        };
        return {
          rune: token('--gv1-rune'),
          dim: token('--gv1-rune-dim'),
          bars: [...document.querySelectorAll('.gv1-curve-bar')].map((bar) => {
            const style = getComputedStyle(bar);
            return { colour: style.backgroundColor, glow: style.boxShadow !== 'none' };
          }),
        };
      });
      expect.soft(paint.dim, 'the dim rune colour').not.toBe(paint.rune);
      expect
        .soft(
          cols
            .map((c, i) => ({ c, ...paint.bars[i], isPeak: c.count === peak.count }))
            .filter(({ colour, glow, isPeak }) => colour !== (isPeak ? paint.rune : paint.dim) || glow !== isPeak)
            .map(({ c, colour, glow }) => `${name(c)}: ${colour}${glow ? ' with a glow' : ''}`),
          'bars in the wrong colour',
        )
        .toEqual([]);
    });
  });
}

// DEC-1074 (DEC-1070 N7). Side by side at 1101px the chart was 416.5px wide.
// slivers' eight labels need 422.1px on macOS and 442.9px on Linux, where
// Chromium rounds each glyph's advance to 7px, so "Recursion" ran past the
// chart. The Performance blocks now stack up to 1190px, and at 1191px the
// chart is 461.5px wide.
const STACKED_UP_TO = 1190;

test.describe('DEC-1074 Performance blocks', () => {
  test(`stack up to ${STACKED_UP_TO}px, and side by side every deck's chart holds its columns`, async ({ page }) => {
    const tracks = () => page.locator('.gv1-perf-grid').evaluate((grid) => getComputedStyle(grid).gridTemplateColumns.split(' ').length);

    await page.setViewportSize({ width: STACKED_UP_TO, height: 900 });
    await openSettled(page, 'slivers');
    expect.soft(await tracks(), `blocks across at ${STACKED_UP_TO}px`).toBe(1);

    // DEC-1095 guard (a): every deck at the first width with the blocks side by side.
    await page.setViewportSize({ width: STACKED_UP_TO + 1, height: 900 });
    const decks: string[] = await page.evaluate(async () =>
      ((await (await fetch('/data/index.json')).json()) as { commanders: Array<{ id: string }> }).commanders.map((c) => c.id),
    );
    const faults: string[] = [];
    for (const deck of decks) {
      await openSettled(page, deck);
      expect.soft(await tracks(), `${deck}: blocks across at ${STACKED_UP_TO + 1}px`).toBe(2);
      const fit = await page.locator('.gv1-curve').evaluate((chart) => {
        const box = chart.getBoundingClientRect();
        const faults = [...chart.querySelectorAll('.gv1-curve-col')].flatMap((col) => {
          const label = col.querySelector('.gv1-curve-l')!;
          const w = col.querySelector('.gv1-curve-bar-wrap')!.getBoundingClientRect();
          const range = document.createRange();
          range.selectNodeContents(label);
          const text = [...range.getClientRects()];
          const name = label.textContent ?? '';
          return [
            ...(w.right > box.right + 0.5 ? [`${name}: column ${Math.round((w.right - box.right) * 100) / 100}px past the chart`] : []),
            ...(text.some((r) => r.left < w.left - 0.5 || r.right > w.right + 0.5) ? [`${name}: text wider than its column`] : []),
          ];
        });
        return { scrollWidth: chart.scrollWidth, clientWidth: chart.clientWidth, faults };
      });
      faults.push(...fit.faults.map((f) => `${deck}: ${f}`));
      if (fit.scrollWidth > fit.clientWidth) faults.push(`${deck}: scrollWidth ${fit.scrollWidth} > clientWidth ${fit.clientWidth}`);
    }
    expect(decks.length).toBeGreaterThan(0);
    expect.soft(faults, 'columns past the chart, labels past their column').toEqual([]);
  });
});
