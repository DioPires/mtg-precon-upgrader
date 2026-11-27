// The phone rule of the /shopping summary (DEC-1154). The reviewer of PR #65 wrote these
// cases (DEC-1163); dec1154-shop-summary.spec.ts reads each stat's edge against the box.
// 1. It holds at 480px and stops at 481px, so nothing changes above 480px.
// 2. A line of stats takes as many stats as their narrowest (min-content) widths allow:
//    the first stat of the next line would not fit on it.

import { expect, test, type Page } from './support/test';

// The index has had no brewing deck since 2026-11-27, so the case marks its
// last deck brewing, as dec1021-selector-pill.spec.ts does: the app reads a
// deck's status from its deck.json. "Include brewing" then shows, and the
// case clicks it (includeBrewing). Returns the marked deck's name.
async function markLastDeckBrewing(page: Page): Promise<string> {
  const r = await page.request.get('/data/index.json');
  const last = ((await r.json()) as { commanders: { id: string; name: string }[] }).commanders.at(-1)!;
  await page.route(`**/data/commanders/${last.id}/deck.json`, async (route) => {
    const response = await route.fetch();
    await route.fulfill({ response, json: { ...(await response.json()), status: 'brewing' } });
  });
  return last.name;
}

// The toggle shows the marked deck in the picker: no chip for it before the
// click, an unselected one after it. "Select all" then selects it.
async function includeBrewing(page: Page, name: string): Promise<void> {
  const picker = page.getByRole('group', { name: 'Deck selection' });
  const brewing = page.getByRole('button', { name: 'Include brewing' });
  await expect(brewing, 'the "Include brewing" toggle').toBeVisible();
  await expect(picker.getByRole('button', { name: new RegExp(`^(Add|Remove) ${name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}$`) }), `${name} before the toggle`).toHaveCount(0);
  await brewing.click();
  await expect(picker.getByRole('button', { name: `Add ${name}`, pressed: false }), `${name} after the toggle`).toHaveCount(1);
}

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
    const boxes = stats.map((s) => s.getBoundingClientRect());
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
      // A stat starts a line when its top is at or below the bottom of the stat before it. The stats
      // of a line share their bottom edge (align-items: end), so a taller stat starts higher.
      if (i === 0 || boxes[i].top >= boxes[i - 1].bottom - 0.5) lines.push([i]); else lines[lines.length - 1].push(i);
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
      { width: 480, display: 'flex', figure: '28px' },
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
        const marked = await markLastDeckBrewing(page);
        await open(page, width);
        const first = await packing(page);
        await includeBrewing(page, marked);
        await page.getByRole('button', { name: 'Select all' }).click();
        await expect(
          page.getByRole('group', { name: 'Deck selection' }).getByRole('button', { name: `Remove ${marked}`, pressed: true }),
          `${marked} after "Select all"`,
        ).toHaveCount(1);
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
