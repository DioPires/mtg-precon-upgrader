// DEC-1156: the engine panel's role title on a phone.
//
// At 42px a role title can be wider than the engine panel on a phone, and the
// page then scrolls sideways. With the web fonts at 320px, shield-doctrine's
// "Quartermaster Corps" (tab 4) took the root to 332 / 320 and
// "Counteroffensive" (tab 7) to 376 / 320; in Verdana the default tab of
// hidden-legion took it to 336, tidal-legion to 338 and gandalf-party-guest to
// 338. "Counteroffensive" at 42px is wider than a 320px phone's panel in every
// face, so letting the card count wrap under the title is not enough alone.
//
// Two rules fix it. The panel head wraps at every width up to 990px (before,
// from 769px only), so the card count drops under a title too long to share
// its row. At 768px and below the title is clamp(30px, 10vw, 42px): 32px at
// 320px, 39px at 390px and 42px from 420px up. The size rule reaches the
// engine title only; the other users of `.gv1-serif-xl` keep 42px.

import { expect, test, type Page } from './support/test';

// WIDE_FACES of dec1116-phone-fallback.spec.ts: a face wider than the web fonts.
const WIDE_FACES =
  ":root { --gv1-serif: Verdana, 'DejaVu Sans', sans-serif; --gv1-serif-italic: Verdana, 'DejaVu Sans', sans-serif;" +
  " --gv1-mono: Menlo, 'DejaVu Sans Mono', monospace; }";

// Resolve once the fonts are in (or have failed) and the page has not moved
// for 300ms: the selector's smooth scroll is still running at first paint.
async function settle(page: Page): Promise<void> {
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

async function openDeck(page: Page, deck: string, css?: string): Promise<void> {
  await page.goto(`/deck/${deck}`);
  if (css) await page.addStyleTag({ content: css });
  await page.locator('.gv1-perf-grid').waitFor();
  await settle(page);
}

// The root's widths, the faces that loaded, and the title against the panel's
// content edge (so a failure names what runs past it).
async function readGuide(page: Page) {
  return page.evaluate(() => {
    const root = document.querySelector('.gv1-root')!;
    const panel = document.querySelector('.gv1-engine-panel')!;
    const ps = getComputedStyle(panel);
    const edge = panel.getBoundingClientRect().right - parseFloat(ps.paddingRight) - parseFloat(ps.borderRightWidth);
    const title = document.querySelector('.gv1-engine-panel-head h3')!;
    const range = document.createRange();
    range.selectNodeContents(title);
    const reach = Math.max(
      title.getBoundingClientRect().right,
      ...[...range.getClientRects()].filter((r) => r.width > 0).map((r) => r.right),
    );
    return {
      scrollWidth: root.scrollWidth,
      clientWidth: root.clientWidth,
      loadedFaces: [...document.fonts].filter((f) => f.status === 'loaded').length,
      title: `"${title.textContent}" ${getComputedStyle(title).fontSize} reaches ${reach.toFixed(1)}, the panel's edge ${edge.toFixed(1)}`,
      titlePast: reach > edge + 0.5,
    };
  });
}

// What the engine title and the panel head compute.
async function readHead(page: Page) {
  return page.evaluate(() => {
    const head = document.querySelector('.gv1-engine-panel-head')!;
    const hs = getComputedStyle(head);
    return {
      title: getComputedStyle(head.querySelector('h3')!).fontSize,
      wrap: hs.flexWrap,
      gap: hs.gap,
    };
  });
}

test.describe('DEC-1156 rules: where they act', () => {
  test.use({ cards: 'seeded', fonts: 'blocked' });

  test('the role title is 32px at 320px, 39px at 390px, and 42px from 420px', async ({ page }) => {
    const want: Record<number, string> = {
      280: '30px',
      320: '32px',
      390: '39px',
      420: '42px',
      768: '42px',
      769: '42px',
      990: '42px',
      1440: '42px',
    };
    const got: Record<number, string> = {};
    await openDeck(page, 'shield-doctrine');
    for (const width of Object.keys(want).map(Number)) {
      await page.setViewportSize({ width, height: 900 });
      got[width] = (await readHead(page)).title;
    }
    expect(got, 'The engine title font-size by viewport width').toEqual(want);
  });

  // DEC-1168 B1: case 1's viewports are all 900px high, so 10vmin would read as
  // 10vw there. On a phone on its side the title still follows the width.
  test('on a viewport lower than it is wide, the role title follows the width', async ({ page }) => {
    const want: Record<string, string> = { '740x360': '42px', '390x300': '38px', '320x280': '32px' };
    const got: Record<string, string> = {};
    await page.setViewportSize({ width: 740, height: 360 });
    await page.goto('/deck/shield-doctrine');
    await page.locator('.gv1-perf-grid').waitFor();
    for (const size of Object.keys(want)) {
      const [width, height] = size.split('x').map(Number);
      await page.setViewportSize({ width, height });
      got[size] = await page.evaluate(() => getComputedStyle(document.querySelector('.gv1-engine-panel-head h3')!).fontSize);
    }
    expect(got, 'The engine title font-size by viewport width x height').toEqual(want);
  });

  test('the panel head wraps with an 8px 16px gap up to 990px, and not from 991px', async ({ page }) => {
    const want: Record<number, string> = {
      320: 'wrap 8px 16px',
      768: 'wrap 8px 16px',
      769: 'wrap 8px 16px',
      990: 'wrap 8px 16px',
      991: 'nowrap normal',
    };
    const got: Record<number, string> = {};
    await openDeck(page, 'shield-doctrine');
    for (const width of Object.keys(want).map(Number)) {
      await page.setViewportSize({ width, height: 900 });
      const h = await readHead(page);
      got[width] = `${h.wrap} ${h.gap}`;
    }
    expect(got, 'The engine panel head flex-wrap and gap by viewport width').toEqual(want);
  });

  test('at 320px the other users of .gv1-serif-xl keep 42px', async ({ page }) => {
    await page.setViewportSize({ width: 320, height: 900 });
    await page.goto('/scrying/eternal-agony');
    await page.locator('[data-gv1-screen="scrying"]').waitFor();
    const sizes = await page.evaluate(() =>
      [...document.querySelectorAll('.gv1-serif-xl')].map((el) => `${el.textContent?.trim()}: ${getComputedStyle(el).fontSize}`),
    );
    expect(sizes, 'The .gv1-serif-xl headings of /scrying at 320px').toEqual([
      'Hand Simulator: 42px',
      'Swap Analyzer: 42px',
      'Simulation Baseline: 42px',
    ]);
  });
});

test.describe('DEC-1156 @ 320px: the guides fit', () => {
  test.use({ viewport: { width: 320, height: 900 } });

  test.describe('web fonts', () => {
    test.use({ cards: 'seeded' });

    test('shield-doctrine tabs 4 and 7 fit the viewport', async ({ page }) => {
      test.setTimeout(60_000);
      await openDeck(page, 'shield-doctrine');
      const out: string[] = [];
      for (const tab of [4, 7]) {
        await page.locator('.gv1-engine-tabs [role="tab"]').nth(tab - 1).click();
        await settle(page);
        const g = await readGuide(page);
        expect(g.loadedFaces, `tab ${tab}: no web font loaded, so the web fonts are not under test`).toBeGreaterThan(0);
        if (g.scrollWidth > g.clientWidth || g.titlePast) out.push(`tab ${tab}: root ${g.scrollWidth} / ${g.clientWidth}; ${g.title}`);
      }
      expect(out, 'shield-doctrine tabs wider than a 320px viewport').toEqual([]);
    });
  });

  test.describe('Verdana and Menlo', () => {
    test.use({ cards: 'seeded', fonts: 'blocked' });

    test('the three guides whose title ran past the viewport fit it', async ({ page }) => {
      test.setTimeout(60_000);
      const out: string[] = [];
      for (const deck of ['hidden-legion', 'tidal-legion', 'gandalf-party-guest']) {
        await openDeck(page, deck, WIDE_FACES);
        const g = await readGuide(page);
        expect(g.loadedFaces, `${deck}: a web font loaded, so the wide face is not under test`).toBe(0);
        if (g.scrollWidth > g.clientWidth || g.titlePast) out.push(`${deck}: root ${g.scrollWidth} / ${g.clientWidth}; ${g.title}`);
      }
      expect(out, 'Guides wider than a 320px viewport in a wide face').toEqual([]);
    });
  });
});
