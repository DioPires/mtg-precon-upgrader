// DEC-1171 (DEC-1024 item 13, DEC-1026 N10): the topbar's first breakpoint.
// At 1380px and below the right meta hides. When both ends show, they wrap to
// two lines below 1326px on macOS (DEC-1019, which set 1330px) and below 1373px
// on CI's Linux runner with JetBrains Mono (DEC-1171, which set 1380px). The old
// breakpoint, 1240px, let them wrap from 1241px up, and no case caught it.
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

    test('from 1241 to 1380px no end of the bar takes two lines', async ({ page }) => {
      await page.setViewportSize({ width: 1241, height: 900 });
      await page.goto('/codex');
      await page.locator('.gv1-topbar').waitFor();
      const readings: Record<number, Awaited<ReturnType<typeof readEnds>>> = {};
      for (const width of [1241, 1280, 1325, 1372, 1380]) {
        await page.setViewportSize({ width, height: 900 });
        readings[width] = await readEnds(page);
      }
      console.log(`DEC-1171 topbar fonts ${fonts}: ${JSON.stringify(readings)}`);
      for (const [width, read] of Object.entries(readings)) {
        expect([read.left.lines, read.right.lines].every((n) => n <= 1), `at ${width}px: ${JSON.stringify(read)}`).toBe(true);
      }
    });

    test('at 1381px the right meta shows and each end takes one line', async ({ page }) => {
      await page.setViewportSize({ width: 1381, height: 900 });
      await page.goto('/codex');
      await page.locator('.gv1-topbar').waitFor();
      const read = await readEnds(page);
      // When an end takes two lines here, name the narrowest width up to 1600px
      // at which both take one: with the web fonts CI's Linux runner wrapped
      // them up to 1372px, and macOS up to 1325px (DEC-1171).
      let fits: number | null = 1381;
      if (read.left.lines > 1 || read.right.lines > 1) {
        fits = null;
        for (let width = 1382; width <= 1600 && fits === null; width++) {
          await page.setViewportSize({ width, height: 900 });
          const at = await readEnds(page);
          if (at.left.lines <= 1 && at.right.lines <= 1) fits = width;
        }
      }
      const where = `both ends take one line from ${fits ?? 'beyond 1600'}px`;
      console.log(`DEC-1171 topbar 1381px fonts ${fonts}: ${JSON.stringify(read)}; ${where}`);
      expect(read.right.shown, 'the right meta shows').toBe(true);
      expect({ left: read.left.lines, right: read.right.lines }, `${JSON.stringify(read)}; ${where}`).toEqual({ left: 1, right: 1 });
    });
  });
}
