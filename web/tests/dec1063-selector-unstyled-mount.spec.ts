// DEC-1063: the deck selector reads its track again when the track's own size
// changes, so the right-edge fade follows it.
//
// WebKit can mount the selector before the page's stylesheets apply. The
// unstyled track is a block that does not overflow, so the mount effect read
// "at its end" and set `data-at-end`. The styles then applied with no scroll
// and no window resize, and the fade stayed hidden on a rail at its start.
//
// CI runs Chromium, which holds the module script until the stylesheets are
// in. `mountUnstyled` gives the mount effects an unstyled track there.

import { expect, test, type Page } from '@playwright/test';

const WIDTHS = [390, 1280];

// Resolve once the web fonts are in and neither the track nor the page has
// moved for 300ms (the selector's scrolls are smooth).
async function settled(page: Page): Promise<void> {
  await page.evaluate(async () => {
    // Two frames first, so that a font the new styles ask for is loading.
    await new Promise<void>((r) => requestAnimationFrame(() => requestAnimationFrame(() => r())));
    await document.fonts.ready;
    await new Promise<void>((resolve) => {
      const track = document.querySelector('.gv1-selector-track')!;
      const read = () => `${track.scrollLeft}|${window.scrollY}`;
      const started = Date.now();
      let last = read();
      let still = 0;
      const tick = () => {
        const now = read();
        still = now === last ? still + 1 : 0;
        last = now;
        if (still < 6 && Date.now() - started < 5000) {
          setTimeout(tick, 50);
          return;
        }
        resolve();
      };
      setTimeout(tick, 50);
    });
  });
}

async function openSettled(page: Page, deck: string): Promise<void> {
  await page.goto(`/deck/${deck}`);
  await page.locator('.gv1-selector-track .gv1-active').waitFor();
  await settled(page);
}

// Load a deck with every author rule reverted, which is what WebKit lays out
// while a stylesheet in <head> is still loading: the track is a block with
// `overflow: visible`, and the body keeps its 8px margin. Once the selector's
// mount effects have run on that layout, drop the sheet: all the styles apply
// at once, with no scroll and no window resize, as they do in WebKit.
//
// Every later load on this page mounts unstyled too.
async function mountUnstyled(page: Page, deck: string): Promise<void> {
  await page.addInitScript(() => {
    const sheet = new CSSStyleSheet();
    sheet.replaceSync('*, *::before, *::after { all: revert !important; }');
    document.adoptedStyleSheets = [sheet];
  });
  await page.goto(`/deck/${deck}`);
  // The fade effect marks a track that does not overflow, and the unstyled
  // track does not: the attribute shows that the mount effects have run.
  await page.locator('.gv1-selector[data-at-end] .gv1-active').waitFor({ state: 'attached' });
  const unstyled = await page.evaluate(() => {
    const track = document.querySelector('.gv1-selector-track')!;
    const cs = getComputedStyle(track);
    return {
      display: cs.display,
      overflowX: cs.overflowX,
      overflow: track.scrollWidth - track.clientWidth,
      bodyMargin: getComputedStyle(document.body).marginLeft,
    };
  });
  expect(unstyled, 'the selector mounted on an unstyled track').toEqual({
    display: 'block',
    overflowX: 'visible',
    overflow: 0,
    bodyMargin: '8px',
  });

  await page.evaluate(() => {
    document.adoptedStyleSheets = [];
  });
  await settled(page);
}

type Rail = { scrollLeft: number; clientWidth: number; scrollWidth: number; atEnd: boolean; fade: string };

const rail = (page: Page): Promise<Rail> =>
  page.evaluate(() => {
    const selector = document.querySelector('.gv1-selector')!;
    const track = selector.querySelector('.gv1-selector-track')!;
    return {
      scrollLeft: track.scrollLeft,
      clientWidth: track.clientWidth,
      scrollWidth: track.scrollWidth,
      atEnd: selector.hasAttribute('data-at-end'),
      fade: getComputedStyle(selector, '::after').opacity,
    };
  });

// Narrow the selector with an inline style: the track shrinks with it, and
// the window does not resize.
const narrowSelector = (page: Page, by: number) =>
  page.evaluate((px) => {
    const selector = document.querySelector<HTMLElement>('.gv1-selector')!;
    selector.style.paddingRight = `${parseFloat(getComputedStyle(selector).paddingRight) + px}px`;
  }, by);

for (const width of WIDTHS) {
  test.describe(`DEC-1063 @ ${width}px`, () => {
    test.use({ viewport: { width, height: 900 } });

    test('the fade returns when the selector narrows around a track at its end', async ({ page }) => {
      // The last pill: the selector scrolls the track to its end.
      await openSettled(page, 'anvil-chorus');
      await expect.poll(async () => (await rail(page)).fade).toBe('0');
      const before = await rail(page);

      await narrowSelector(page, 60);

      // The track is now 60px short of its end: more pills lie to the right.
      await expect.poll(async () => (await rail(page)).fade).toBe('1');
      const after = await rail(page);
      expect(after.clientWidth).toBe(before.clientWidth - 60);
      expect(after.scrollWidth - (after.scrollLeft + after.clientWidth)).toBeGreaterThan(1);
      expect(after.atEnd).toBe(false);
    });

    test('the fade shows on the first deck when the selector mounts before the styles apply', async ({
      page,
    }) => {
      await mountUnstyled(page, 'titan-convergence');

      // The styled track is at its start and overflows.
      await expect.poll(async () => (await rail(page)).fade).toBe('1');
      const r = await rail(page);
      expect(r.scrollLeft).toBe(0);
      expect(r.scrollWidth).toBeGreaterThan(r.clientWidth + 1);
      expect(r.atEnd).toBe(false);
    });
  });
}
