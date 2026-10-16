// DEC-1154 Part A (DEC-1149 N7): no stat of the /shopping summary passes the
// right edge of its box on a phone, with the web fonts and with the fallback
// faces. At 390px with the web fonts blocked, the third stat ("TOTAL UNIQUE")
// ran past the box.
//
// Each case reads two selections: the page's own (the first deck) and every
// deck with the brewing decks, whose counts and cost are the longest that the
// summary shows. After document.fonts.ready it reads the right edge of each
// stat and of its text against the right edge of the box's content. It also
// reads what the 480px rule says: the stats of a line share all of it, the
// action row has a line of its own as wide as the box or wider, and each of
// its buttons shows its label on one line. At 320px the row's buttons need
// 133.5px and the box holds 126px, so "A–Z" ends 7.5px past the box's content
// edge, inside its padding, as it does on the 3-column grid.

import { expect, test, type Page } from './support/test';

// The widths of DEC-1154, and 480px, the widest that the rule holds. At 480px
// the action row's buttons need less than the box, so the row shows that it
// takes the box's width.
const WIDTHS = [320, 360, 390, 430, 480];

type Reading = {
  left: number;
  edge: number;
  stats: Array<{ label: string; value: string; reach: number; right: number; bottom: number }>;
  actions: { left: number; right: number; top: number };
  buttons: Array<{ label: string; lines: number }>;
};

async function readSummary(page: Page): Promise<Reading> {
  await page.evaluate(() => document.fonts.ready.then(() => undefined));
  return page.locator('.gv1-shop-summary').evaluate((box) => {
    const r = (n: number) => Math.round(n * 10) / 10;
    // The rects of the text in `el`, one or more for each line it takes.
    const textRects = (el: Element) => {
      const range = document.createRange();
      range.selectNodeContents(el);
      return [...range.getClientRects()].filter((rect) => rect.width > 0);
    };
    const cs = getComputedStyle(box);
    const rect = box.getBoundingClientRect();
    const stats = [...box.querySelectorAll<HTMLElement>('.gv1-shop-stat')].map((stat) => {
      const own = stat.getBoundingClientRect();
      const [label, value] = [...stat.children].map((el) => (el.textContent ?? '').trim());
      // The stat's own box or its text, whichever reaches further.
      const reach = Math.max(own.right, ...textRects(stat).map((t) => t.right));
      return { label, value, reach: r(reach), right: r(own.right), bottom: r(own.bottom) };
    });
    const actions = box.querySelector('.gv1-shop-summary-actions')!.getBoundingClientRect();
    const buttons = [...box.querySelectorAll('.gv1-shop-summary-actions button')].map((button) => ({
      label: (button.textContent ?? '').trim(),
      lines: new Set(textRects(button).map((t) => Math.round(t.top))).size,
    }));
    return {
      left: r(rect.left + parseFloat(cs.paddingLeft) + parseFloat(cs.borderLeftWidth)),
      edge: r(rect.right - parseFloat(cs.paddingRight) - parseFloat(cs.borderRightWidth)),
      stats,
      actions: { left: r(actions.left), right: r(actions.right), top: r(actions.top) },
      buttons,
    };
  });
}

// What the reading shows against the rule; an empty list when it holds.
function faults(name: string, s: Reading): string[] {
  const out: string[] = [];
  for (const stat of s.stats) {
    if (stat.reach > s.edge + 0.5) out.push(`${name}: ${stat.label} "${stat.value}" reaches ${stat.reach}, the box's edge ${s.edge}`);
  }
  // The stats of a line end on one bottom edge (align-items: end).
  const lines = new Map<number, number>();
  for (const stat of s.stats) lines.set(Math.round(stat.bottom), Math.max(lines.get(Math.round(stat.bottom)) ?? 0, stat.right));
  for (const [bottom, right] of lines) {
    if (right < s.edge - 0.5) out.push(`${name}: the line of stats at ${bottom} ends at ${right}, the box's edge ${s.edge}`);
  }
  const statsEnd = Math.max(...s.stats.map((stat) => stat.bottom));
  const { left, right, top } = s.actions;
  if (Math.abs(left - s.left) > 0.5 || right < s.edge - 0.5 || top < statsEnd) {
    out.push(`${name}: the action row spans ${left} to ${right} from ${top}; the box ${s.left} to ${s.edge}, the stats end at ${statsEnd}`);
  }
  for (const button of s.buttons) {
    if (button.lines !== 1) out.push(`${name}: the button "${button.label}" takes ${button.lines} lines`);
  }
  return out;
}

for (const fonts of ['live', 'blocked'] as const) {
  test.describe(`DEC-1154 /shopping summary, web fonts ${fonts}`, () => {
    test.use({ fonts });

    for (const width of WIDTHS) {
      test(`at ${width}px no stat passes the right edge of the box`, async ({ page }, testInfo) => {
        test.setTimeout(60_000);
        await page.setViewportSize({ width, height: 900 });
        await page.goto('/shopping');
        await page.locator('.gv1-shop-row').first().waitFor();
        const summary = page.locator('.gv1-shop-summary');

        const first = await readSummary(page);
        const faces = await page.evaluate(() => [...document.fonts].filter((f) => f.status === 'loaded').length);
        if (fonts === 'live') expect(faces, 'no web font loaded, so the web fonts are not under test').toBeGreaterThan(0);
        else expect(faces, 'a web font loaded, so the fallback faces are not under test').toBe(0);
        await summary.screenshot({ path: testInfo.outputPath(`summary-${width}-${fonts}-first.png`), animations: 'disabled' });

        // Every deck, with the brewing decks: the longest counts and cost.
        const brewing = page.getByRole('button', { name: 'Include brewing' });
        if ((await brewing.count()) > 0) await brewing.click();
        await page.getByRole('button', { name: 'Select all' }).click();
        await expect(page.getByRole('button', { name: /^Add / })).toHaveCount(0);
        const all = await readSummary(page);
        await summary.screenshot({ path: testInfo.outputPath(`summary-${width}-${fonts}-all.png`), animations: 'disabled' });

        console.log(`DEC-1154 ${width}px fonts ${fonts}: ${JSON.stringify({ faces, first, all })}`);
        expect([...faults('first deck', first), ...faults('every deck', all)], 'The summary against the 480px rule').toEqual([]);
      });
    }
  });
}
