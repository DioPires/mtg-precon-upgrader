// DEC-1154 fix round 1 (review DEC-1163, B4 and B5): the bounds and the packing of the
// phone rule of the /shopping summary.
// 1. It holds at 480px and stops at 481px, so nothing changes above 480px.
// 2. A line of stats takes as many stats as their narrowest (min-content) widths allow:
//    the first stat of the next line would not fit on it.

import { expect, test, type Page } from './support/test';

async function open(page: Page, width: number) {
  await page.setViewportSize({ width, height: 900 });
  await page.goto('/shopping');
  await page.locator('.gv1-shop-row').first().waitFor();
  await page.evaluate(() => document.fonts.ready.then(() => undefined));
}

// For each line of stats but the last: the line's width at the stats' narrowest widths with
// the next line's first stat added, against the width of the box's content.
async function packing(page: Page) {
  await page.evaluate(() => document.fonts.ready.then(() => undefined));
  return page.locator('.gv1-shop-summary').evaluate((box) => {
    const cs = getComputedStyle(box);
    const content = box.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
    const gap = parseFloat(cs.columnGap);
    const stats = [...box.querySelectorAll<HTMLElement>('.gv1-shop-stat')];
    const tops = stats.map((s) => Math.round(s.getBoundingClientRect().top));
    // The narrowest width of each stat: its min-content width, read with the stat taken out of the flex sizing.
    const narrowest = stats.map((s) => {
      const keep = s.getAttribute('style');
      s.style.flex = 'none';
      s.style.width = 'min-content';
      const w = s.getBoundingClientRect().width;
      if (keep === null) s.removeAttribute('style'); else s.setAttribute('style', keep);
      return w;
    });
    const lines: number[][] = [];
    stats.forEach((_, i) => {
      if (i === 0 || tops[i] > tops[i - 1] + 1) lines.push([i]); else lines[lines.length - 1].push(i);
    });
    return lines.slice(0, -1).map((line, k) => {
      const next = lines[k + 1][0];
      const withNext = [...line, next].reduce((sum, i) => sum + narrowest[i], 0) + gap * line.length;
      return { line: line.map((i) => stats[i].firstElementChild?.textContent), next: stats[next].firstElementChild?.textContent, withNext: Math.round(withNext * 10) / 10, content };
    });
  });
}

for (const fonts of ['live', 'blocked'] as const) {
  test.describe(`DEC-1163 /shopping summary on a phone, web fonts ${fonts}`, () => {
    test.use({ fonts });

    for (const { width, display, figure } of [
      { width: 480, display: 'flex', figure: '27px' },
      { width: 481, display: 'grid', figure: '42px' },
    ]) {
      test(`at ${width}px the summary is a ${display} box with ${figure} figures`, async ({ page }) => {
        await open(page, width);
        const read = await page.locator('.gv1-shop-summary').evaluate((box) => ({
          display: getComputedStyle(box).display,
          figures: [...box.querySelectorAll('.gv1-shop-stat .gv1-serif-xl')].map((el) => getComputedStyle(el).fontSize),
        }));
        expect(read).toEqual({ display, figures: [figure, figure, figure, figure] });
      });
    }

    for (const width of [320, 360, 390, 430, 480]) {
      test(`at ${width}px a line of stats takes every stat that fits at its narrowest width`, async ({ page }) => {
        await open(page, width);
        const first = await packing(page);
        const brewing = page.getByRole('button', { name: 'Include brewing' });
        if ((await brewing.count()) > 0) await brewing.click();
        await page.getByRole('button', { name: 'Select all' }).click();
        await expect(page.getByRole('button', { name: /^Add / })).toHaveCount(0);
        const all = await packing(page);
        console.log(`DEC-1163 packing ${width}px fonts ${fonts}: ${JSON.stringify({ first, all })}`);
        // Half a pixel of room: the browser sums fractional widths.
        const fits = [...first, ...all].filter((l) => l.withNext < l.content - 0.5);
        expect(fits, 'a stat that fits on the line above at its narrowest width').toEqual([]);
      });
    }
  });
}
