// DEC-1116: the deck guide on a 320px phone in the fallback faces.
//
// The fallback faces are wider than the web fonts, and `display=swap` draws
// them until the web fonts arrive, and for good when they fail. In Georgia
// five guides ran past a 320px viewport, where the root clips them:
// eternal-agony 373 / 320, grave-dividends 385, broodfire-hatchery 355,
// witherbloom-the-balancer 331 and titan-convergence 325. Three kinds of text
// did it: one word of the Commander's deck name ("Convergence"), the longest
// word of an engine tile ("artifact/enchantment/token)"), and the Commander
// Spellbook URLs in the combo and win-condition texts. The first case blocks
// the web fonts. The second also sets a wider face on the decks where each
// rule acts in it (a tile name such as "Archaeomancer's" on the-white-forge).

import { expect, test, type Page } from './support/test';

// Stand-ins for a face wider than the web fonts, as in
// dec1043-band-rules.spec.ts. Linux has no Verdana or Menlo; DejaVu Sans and
// DejaVu Sans Mono have about the same widths.
const WIDE_FACES =
  ":root { --gv1-serif: Verdana, 'DejaVu Sans', sans-serif; --gv1-serif-italic: Verdana, 'DejaVu Sans', sans-serif;" +
  " --gv1-mono: Menlo, 'DejaVu Sans Mono', monospace; }";

// The texts that the DEC-1116 rules let break inside a word.
const RULED = [
  '.gv1-cmd-deckname',
  '.gv1-engine-cards .gv1-card-tile-name',
  '.gv1-engine-cards .gv1-card-tile-note',
  '.gv1-wincon-desc',
  '.gv1-combo-desc',
].join(', ');

// Resolve once the fonts have failed and the page has not moved for 300ms:
// the selector's smooth scroll is still running at first paint.
async function openSettled(page: Page, deck: string, css?: string): Promise<void> {
  await page.goto(`/deck/${deck}`);
  if (css) await page.addStyleTag({ content: css });
  await page.locator('.gv1-perf-grid').waitFor();
  await page.evaluate(async () => {
    await document.fonts.ready;
    await new Promise<void>((resolve) => {
      const root = document.querySelector('.gv1-root');
      const read = () => `${window.scrollY}|${root?.scrollWidth}|${document.body.scrollHeight}`;
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

type Reading = { scrollWidth: number; clientWidth: number; loadedFaces: number; past: string[] };

// The root's widths, the faces that loaded, and each ruled text that runs past
// its own content edge (so a failure names what to fix).
async function readGuide(page: Page): Promise<Reading> {
  return page.evaluate((ruled) => {
    const root = document.querySelector('.gv1-root')!;
    const past: string[] = [];
    for (const el of document.querySelectorAll(ruled)) {
      const cs = getComputedStyle(el);
      const edge = el.getBoundingClientRect().right - parseFloat(cs.paddingRight) - parseFloat(cs.borderRightWidth);
      const range = document.createRange();
      range.selectNodeContents(el);
      const reach = Math.max(...[...range.getClientRects()].filter((r) => r.width > 0).map((r) => r.right));
      if (reach > edge + 0.5) {
        const cls = (el.getAttribute('class') ?? '').trim().split(/\s+/).join('.');
        const text = (el.textContent ?? '').trim().slice(0, 40);
        past.push(`${cls} "${text}" reaches ${reach.toFixed(1)}, its edge ${edge.toFixed(1)}`);
      }
    }
    return {
      scrollWidth: root.scrollWidth,
      clientWidth: root.clientWidth,
      loadedFaces: [...document.fonts].filter((f) => f.status === 'loaded').length,
      past,
    };
  }, RULED);
}

async function offenders(page: Page, decks: string[], css?: string): Promise<string[]> {
  const out: string[] = [];
  for (const deck of decks) {
    await openSettled(page, deck, css);
    const g = await readGuide(page);
    expect(g.loadedFaces, `${deck}: a web font loaded, so the fallback faces are not under test`).toBe(0);
    if (g.scrollWidth > g.clientWidth || g.past.length > 0) {
      out.push(`${deck}: root ${g.scrollWidth} / ${g.clientWidth}${g.past.map((p) => `; ${p}`).join('')}`);
    }
  }
  return out;
}

test.describe('DEC-1116 @ 320px, web fonts blocked', () => {
  test.use({ cards: 'seeded', fonts: 'blocked', viewport: { width: 320, height: 900 } });

  test('the five guides that ran past the viewport in the fallback faces fit it', async ({ page }) => {
    test.setTimeout(60_000);
    const decks = ['eternal-agony', 'grave-dividends', 'broodfire-hatchery', 'witherbloom-the-balancer', 'titan-convergence'];
    expect(await offenders(page, decks), 'Guides wider than a 320px viewport in the fallback faces').toEqual([]);
  });

  test('with Verdana and Menlo, the guides where each rule acts fit the viewport', async ({ page }) => {
    test.setTimeout(60_000);
    const decks = [
      'titan-convergence', // deck name
      'exponential-growth', // deck name
      'eternal-agony', // tile note
      'the-white-forge', // tile name
      'grave-dividends', // win-condition and combo URLs
      'broodfire-hatchery', // combo URLs
    ];
    expect(await offenders(page, decks, WIDE_FACES), 'Guides wider than a 320px viewport in a wide face').toEqual([]);
  });
});
