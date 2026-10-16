// DEC-1171 (DEC-1024 item 13, DEC-1026 N10): the topbar's first breakpoint.
// At 1330px and below the right meta hides (DEC-1019): from 1326px down the two
// ends of the bar wrap to two lines when both show. The old breakpoint, 1240px,
// let them wrap from 1241 to 1325px, and no case caught it.
//
// An end is a flex row that does not wrap, so it takes two lines only when the
// text of one of its spans wraps. Each text node counts its own lines from the
// rects of its fragments, grouped by vertical overlap: a rect that starts at or
// below the bottom of the line above starts a new line. The end takes as many
// lines as its text node with the most. The count reads no element box (a span
// that wraps is one flex item, as tall as both lines) and groups no rects of
// two spans: the row centres a one-line span across the two lines of the other.

import { expect, test, type Page } from './support/test';

async function readEnds(page: Page) {
  await page.evaluate(() => document.fonts.ready.then(() => undefined));
  return page.evaluate(() => {
    const r = (n: number) => Math.round(n * 10) / 10;
    const read = (selector: string) => {
      const el = document.querySelector(selector)!;
      if (getComputedStyle(el).display === 'none') return { shown: false, lines: 0, height: 0 };
      let lines = 0;
      const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
      for (let node = walker.nextNode(); node; node = walker.nextNode()) {
        if (!(node.textContent ?? '').trim()) continue;
        const range = document.createRange();
        range.selectNodeContents(node);
        const rects = [...range.getClientRects()].filter((t) => t.width > 0 && t.height > 0);
        rects.sort((a, b) => a.top - b.top);
        let own = 0;
        let bottom = -Infinity;
        for (const t of rects) {
          if (t.top >= bottom - 0.5) {
            own += 1;
            bottom = t.bottom;
          } else {
            bottom = Math.max(bottom, t.bottom);
          }
        }
        lines = Math.max(lines, own);
      }
      return { shown: true, lines, height: r(el.getBoundingClientRect().height) };
    };
    return {
      bar: r(document.querySelector('.gv1-topbar')!.getBoundingClientRect().height),
      left: read('.gv1-topbar-left'),
      right: read('.gv1-topbar-right'),
    };
  });
}

for (const fonts of ['live', 'blocked'] as const) {
  test.describe(`DEC-1171 topbar breakpoint, web fonts ${fonts}`, () => {
    test.use({ fonts });

    test('from 1241 to 1325px no end of the bar takes two lines', async ({ page }) => {
      await page.setViewportSize({ width: 1241, height: 900 });
      await page.goto('/codex');
      await page.locator('.gv1-topbar').waitFor();
      const readings: Record<number, Awaited<ReturnType<typeof readEnds>>> = {};
      for (const width of [1241, 1280, 1325]) {
        await page.setViewportSize({ width, height: 900 });
        readings[width] = await readEnds(page);
      }
      console.log(`DEC-1171 topbar fonts ${fonts}: ${JSON.stringify(readings)}`);
      for (const [width, read] of Object.entries(readings)) {
        expect([read.left.lines, read.right.lines].every((n) => n <= 1), `at ${width}px: ${JSON.stringify(read)}`).toBe(true);
      }
    });

    test('at 1331px the right meta shows and each end takes one line', async ({ page }) => {
      await page.setViewportSize({ width: 1331, height: 900 });
      await page.goto('/codex');
      await page.locator('.gv1-topbar').waitFor();
      const read = await readEnds(page);
      console.log(`DEC-1171 topbar 1331px fonts ${fonts}: ${JSON.stringify(read)}`);
      expect(read.right.shown, 'the right meta shows').toBe(true);
      expect({ left: read.left.lines, right: read.right.lines }, JSON.stringify(read)).toEqual({ left: 1, right: 1 });
    });
  });
}
