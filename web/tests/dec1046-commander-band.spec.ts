// DEC-1046: the Commander block from 769 to 1020px keeps the art beside the
// dossier. No deck sets `partner` today, so this case serves one deck with a
// second commander. With two arts and two names the block is at its widest,
// and the first real partner deck should not be the first to draw it.
//
// At 769px the dossier is 345px wide. On one row, the two commander names and
// the deck type need more than that (27px past the content edge with the web
// fonts, 76px with them blocked), so the row wraps.

import { expect, test, type Page } from './support/test';

const DECK = 'witherbloom-the-balancer';
const PARTNER = 'Donatello, the Brains';

async function withPartner(page: Page): Promise<void> {
  await page.route(`**/data/commanders/${DECK}/deck.json`, async (route) => {
    const response = await route.fetch();
    const body = (await response.json()) as Record<string, unknown>;
    body.partner = PARTNER;
    await route.fulfill({ response, json: body });
  });
}

// The fonts are in (or have failed), and nothing has moved for 300ms.
async function settle(page: Page): Promise<void> {
  await page.evaluate(async () => {
    await document.fonts.ready;
    await new Promise<void>((resolve) => {
      const root = document.querySelector('.gv1-root');
      const read = () => `${window.scrollY}|${root?.scrollLeft}|${document.body.scrollHeight}|${document.body.scrollWidth}`;
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

type Block = {
  arts: number;
  stackRight: number;
  stackBottom: number;
  bodyLeft: number;
  nameTop: number;
  past: string[];
};

// The art stack, the dossier and the deck name, and every box or text in the
// block that passes the section's content edge.
async function readBlock(page: Page): Promise<Block> {
  return page.evaluate(() => {
    const section = document.querySelector('.gv1-commander')!;
    const grid = section.querySelector('.gv1-cmd-grid')!;
    const edge = section.getBoundingClientRect().right - parseFloat(getComputedStyle(section).paddingRight);
    const label = (el: Element) => `${el.tagName.toLowerCase()}.${(el.getAttribute('class') ?? '').trim().split(/\s+/).join('.')}`;
    const past: string[] = [];
    for (const el of [grid, ...grid.querySelectorAll('*')]) {
      const r = el.getBoundingClientRect();
      if (r.width > 0 && r.height > 0 && r.right > edge + 0.5) past.push(`${label(el)} box ${(r.right - edge).toFixed(1)}px`);
      for (const n of el.childNodes) {
        if (n.nodeType !== Node.TEXT_NODE || !(n.textContent ?? '').trim()) continue;
        const range = document.createRange();
        range.selectNodeContents(n);
        const right = Math.max(...[...range.getClientRects()].filter((t) => t.width > 0).map((t) => t.right));
        if (right > edge + 0.5) past.push(`${label(el)} text "${(n.textContent ?? '').trim().slice(0, 30)}" ${(right - edge).toFixed(1)}px`);
      }
    }
    const stack = section.querySelector('.gv1-cmd-art-stack')!.getBoundingClientRect();
    return {
      arts: section.querySelectorAll('.gv1-cmd-art').length,
      stackRight: stack.right,
      stackBottom: stack.bottom,
      bodyLeft: section.querySelector('.gv1-cmd-body')!.getBoundingClientRect().left,
      nameTop: section.querySelector('.gv1-cmd-deckname')!.getBoundingClientRect().top,
      past,
    };
  });
}

for (const fonts of ['live', 'blocked'] as const) {
  test.describe(`DEC-1046 @ 769px, web fonts ${fonts}`, () => {
    test.use({ cards: 'seeded', fonts, viewport: { width: 769, height: 900 } });

    test('a deck with a partner: both arts beside the name, and the block inside its content edge', async ({ page }) => {
      await withPartner(page);
      await page.goto(`/deck/${DECK}`);
      await page.locator('.gv1-perf-grid').first().waitFor();
      await settle(page);

      const block = await readBlock(page);
      expect(block.arts, 'commander arts').toBe(2);
      expect(block.stackRight, 'the art stack ends before the dossier starts').toBeLessThan(block.bodyLeft);
      expect(block.nameTop, 'the deck name starts beside the art, not below it').toBeLessThan(block.stackBottom);
      expect(block.past, 'boxes and text past the content edge').toEqual([]);
    });
  });
}
