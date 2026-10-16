// DEC-1046: the Commander block from 769 to 1020px keeps the art beside the
// dossier. No deck sets `partner` today, so this case serves one deck with a
// second commander. With two arts and two names the block is at its widest,
// and the first real partner deck should not be the first to draw it.
//
// At 769px the dossier is 345px wide. On one row, the two commander names and
// the deck type need more than that (27px past the content edge with the web
// fonts, 76px with them blocked), so the row wraps. It wraps at every width:
// without the wrap the row also passed the content edge at 390px (14px with the
// web fonts, 63px with them blocked) and at 1021px with the fonts blocked (28px).

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
  rootScroll: number;
  rootClient: number;
};

// The art stack, the dossier and the deck name, every box or text in the block
// that passes the section's content edge, and the root's widths.
async function readBlock(page: Page): Promise<Block> {
  return page.evaluate(() => {
    const section = document.querySelector('.gv1-commander')!;
    const root = document.querySelector('.gv1-root')!;
    const edge = section.getBoundingClientRect().right - parseFloat(getComputedStyle(section).paddingRight);
    const label = (el: Element) => `${el.tagName.toLowerCase()}.${(el.getAttribute('class') ?? '').trim().split(/\s+/).join('.')}`;
    const past: string[] = [];
    for (const el of [section, ...section.querySelectorAll('*')]) {
      const r = el.getBoundingClientRect();
      if (el !== section && r.width > 0 && r.height > 0 && r.right > edge + 0.5) past.push(`${label(el)} box ${(r.right - edge).toFixed(1)}px`);
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
      rootScroll: root.scrollWidth,
      rootClient: root.clientWidth,
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

// The partner row wraps outside the band too (the base rules).
const OUTSIDE_THE_BAND = [
  { width: 390, fonts: 'live', root: false },
  { width: 390, fonts: 'blocked', root: true },
  { width: 1021, fonts: 'blocked', root: false },
] as const;

for (const { width, fonts, root } of OUTSIDE_THE_BAND) {
  test.describe(`DEC-1046 @ ${width}px, web fonts ${fonts}`, () => {
    test.use({ cards: 'seeded', fonts, viewport: { width, height: 900 } });

    test(`a deck with a partner: the block inside its content edge${root ? ', and the root inside the viewport' : ''}`, async ({ page }) => {
      await withPartner(page);
      await page.goto(`/deck/${DECK}`);
      await page.locator('.gv1-perf-grid').first().waitFor();
      await settle(page);

      const block = await readBlock(page);
      expect(block.arts, 'commander arts').toBe(2);
      expect(block.past, 'boxes and text past the content edge').toEqual([]);
      if (root) expect(block.rootScroll, '.gv1-root scrollWidth against its clientWidth').toBe(block.rootClient);
    });
  });
}

// Between 768 and 769px (browser zoom) a band rule from 769px and the 768px
// block both miss, and the Commander got the desktop tracks. The harness sets
// whole-pixel viewports only, and an iframe 768.5px wide gives its page a 769px
// viewport. So this case reads the built stylesheet: the band rule has no lower
// bound.
test('DEC-1046: the band rule of the deck name has no lower bound', async ({ page }) => {
  await page.goto(`/deck/${DECK}`);
  await page.locator('.gv1-cmd-deckname').waitFor();

  const media = await page.evaluate(() => {
    const found: string[] = [];
    const walk = (rules: CSSRuleList, within: string) => {
      for (const rule of rules) {
        if (rule instanceof CSSMediaRule) walk(rule.cssRules, rule.media.mediaText);
        else if (rule instanceof CSSStyleRule && rule.selectorText === '.gv1-cmd-deckname' && rule.style.fontSize.includes('clamp(')) found.push(within);
      }
    };
    for (const sheet of document.styleSheets) {
      // The web fonts' sheet comes from another origin, and its rules cannot be read.
      let rules: CSSRuleList;
      try {
        rules = sheet.cssRules;
      } catch {
        continue;
      }
      walk(rules, '(no media rule)');
    }
    return found;
  });
  expect(media, 'the media rules that scale the deck name').toEqual(['(max-width: 1020px)']);
});
