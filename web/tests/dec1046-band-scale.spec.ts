// DEC-1046 kill cases (review DEC-1145): the sizes of the Commander band rule.
// From 769 to 1020px the art track is 5/16 of the viewport, 40px from the
// dossier, and the deck name is 12vw - 32px, at most 88px. At 1021px the
// desktop rule is back: the 420px art, 64px from the dossier, and the 88px name.
// The spec of DEC-1046 reads only 769px with a partner, so a change of a slope,
// a cap, the gap or the upper bound passed it and the whole suite.

import { expect, test, type Page } from './support/test';

const DECK = 'witherbloom-the-balancer';

// The fonts are in (or have failed), and nothing has moved for 300ms.
async function settle(page: Page): Promise<void> {
  await page.evaluate(async () => {
    await document.fonts.ready;
    await new Promise<void>((resolve) => {
      const root = document.querySelector('.gv1-root');
      const read = () => `${window.innerWidth}|${root?.scrollWidth}|${document.body.scrollHeight}|${document.body.scrollWidth}`;
      const started = Date.now();
      let last = read();
      let still = 0;
      const tick = () => {
        const now = read();
        still = now === last ? still + 1 : 0;
        last = now;
        if (still >= 6 || Date.now() - started > 5000) resolve();
        else setTimeout(tick, 50);
      };
      setTimeout(tick, 50);
    });
  });
}

// The art, the gap to the dossier, the name's size, the words of the name that
// break across lines, and every box or text in the block past the content edge.
async function readBlock(page: Page) {
  return page.evaluate(() => {
    const section = document.querySelector('.gv1-commander')!;
    const edge = section.getBoundingClientRect().right - parseFloat(getComputedStyle(section).paddingRight);
    const art = section.querySelector('.gv1-cmd-art')!.getBoundingClientRect();
    const body = section.querySelector('.gv1-cmd-body')!.getBoundingClientRect();
    const name = section.querySelector('.gv1-cmd-deckname')!;
    const broken: string[] = [];
    for (const n of name.childNodes) {
      if (n.nodeType !== Node.TEXT_NODE) continue;
      const text = n.textContent ?? '';
      const re = /\S+/g;
      for (let m = re.exec(text); m; m = re.exec(text)) {
        const range = document.createRange();
        range.setStart(n, m.index);
        range.setEnd(n, m.index + m[0].length);
        const tops = new Set([...range.getClientRects()].filter((r) => r.width > 0).map((r) => Math.round(r.top)));
        if (tops.size > 1) broken.push(m[0]);
      }
    }
    const past: string[] = [];
    for (const el of section.querySelectorAll('*')) {
      const r = el.getBoundingClientRect();
      if (r.width > 0 && r.height > 0 && r.right > edge + 0.5) past.push(`${el.className} ${(r.right - edge).toFixed(1)}px`);
    }
    return {
      artWidth: art.width,
      gap: body.left - art.right,
      nameSize: parseFloat(getComputedStyle(name).fontSize),
      broken,
      past,
    };
  });
}

const clamp = (low: number, value: number, high: number) => Math.min(high, Math.max(low, value));

// A face wider than the web fonts, as in dec1043-band-rules.spec.ts. Linux has
// no Verdana or Menlo; DejaVu Sans and DejaVu Sans Mono have about the same widths.
const WIDE_FACE =
  ":root { --gv1-serif: Verdana, 'DejaVu Sans', sans-serif; --gv1-serif-italic: Verdana, 'DejaVu Sans', sans-serif;" +
  " --gv1-mono: Menlo, 'DejaVu Sans Mono', monospace; }";

for (const fonts of ['live', 'blocked'] as const) {
  test.describe(`DEC-1046 band sizes, web fonts ${fonts}`, () => {
    test.use({ cards: 'seeded', fonts, viewport: { width: 769, height: 900 } });

    test('769 to 1020px: the art is 5/16 of the viewport and 40px from the dossier, the name is 12vw - 32px up to 88px; 1021px is the desktop', async ({ page }) => {
      await page.goto(`/deck/${DECK}`);
      await page.locator('.gv1-perf-grid').first().waitFor();
      for (const width of [769, 900, 1000, 1020, 1021]) {
        await page.setViewportSize({ width, height: 900 });
        await settle(page);
        const block = await readBlock(page);
        const band = width <= 1020;
        expect(block.artWidth, `${width}px: the art's width`).toBeCloseTo(band ? clamp(240, width * 0.3125, 320) : 420, 1);
        expect(block.gap, `${width}px: the gap between the art and the dossier`).toBeCloseTo(band ? 40 : 64, 1);
        expect(block.nameSize, `${width}px: the deck name's size`).toBeCloseTo(band ? clamp(56, width * 0.12 - 32, 88) : 88, 1);
        // The fallback face differs by system (Georgia on macOS, another serif on
        // the Linux runner), so the words of the name are read with the web fonts only.
        if (band && fonts === 'live') expect(block.broken, `${width}px: words of the deck name that break inside`).toEqual([]);
        expect(block.past, `${width}px: boxes past the content edge`).toEqual([]);
      }
    });
  });
}

// In this face one word of three deck names is wider than the dossier. The
// dossier keeps its track (minmax(0, 1fr)) and the word breaks, a known limit
// of the face (DEC-1043). A track that takes width from its content would run
// the name past the content edge (titan-convergence: 31.6px at 769px).
test.describe('DEC-1046 band, a face wider than the web fonts', () => {
  test.use({ cards: 'seeded', fonts: 'blocked', viewport: { width: 769, height: 900 } });

  test('769 to 1020px: the dossier keeps its track, and no box passes the content edge', async ({ page }) => {
    for (const deck of ['titan-convergence', 'gandalf-party-guest', DECK]) {
      await page.setViewportSize({ width: 769, height: 900 });
      await page.goto(`/deck/${deck}`);
      await page.addStyleTag({ content: WIDE_FACE });
      await page.locator('.gv1-perf-grid').first().waitFor();
      for (const width of [769, 900, 1020]) {
        await page.setViewportSize({ width, height: 900 });
        await settle(page);
        const block = await readBlock(page);
        expect(block.past, `${deck} at ${width}px: boxes past the content edge`).toEqual([]);
      }
    }
  });
});
