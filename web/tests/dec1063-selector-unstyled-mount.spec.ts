// DEC-1063: the deck selector reads its track again when the track's own size
// changes, so the right-edge fade follows it, and it centres the active pill
// once the track has its styled layout.
//
// WebKit can mount the selector before the page's stylesheets apply. The
// unstyled track is a block that does not overflow, so the mount effect read
// "at its end" and set `data-at-end`. The styles then applied with no scroll
// and no window resize, and the fade stayed hidden on a rail at its start.
// The centring effect read the same layout: `scrollTo` cannot move a track
// that is not a scroll container, so the active pill stayed where the styles
// put it, off screen for a late deck. On a short viewport the unstyled track
// also ran past the bottom edge, and the effect scrolled the page.
//
// CI runs Chromium, which holds the module script until the stylesheets are
// in. Two routes give the mount effects an unstyled track there. They differ
// in when the styles then apply: `mountUnstyled` after the first observation
// of the selector's size observer, `mountUnstyledInWebKitOrder` before it.

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
// On this route the selector's size observer gets its first observation on
// the unstyled track, and the styles follow as a change of the track's size.
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

// The track's `overflow-x` when the selector began to observe it, and at each
// size observation the browser then made of it.
type Order = { mounted: string[]; observed: string[] };

// As `mountUnstyled`, but the sheet goes sooner. This route gives WebKit's
// order: the styles apply after the selector's mount effects and before its
// size observer's first observation. WebKit delivers no observation while the
// track is unstyled, so there the styles are never a change of size: the
// first observation has to centre the pill and re-read the fade.
//
// The selector's fade effect adds the window's `resize` listener right after
// it reads the track. The init script drops the sheet in a microtask queued
// at that call. A microtask runs before the next rendering update, and the
// first observation comes with that update.
//
// The route passes the selector's observer that first observation and no
// later one. The web fonts swap in a moment afterwards and make the track a
// pixel taller, and a selector that ignored its first observation would do
// all the work at that second one.
//
// Every later load on this page mounts this way too.
async function mountUnstyledInWebKitOrder(page: Page, deck: string): Promise<void> {
  await page.addInitScript(() => {
    const sheet = new CSSStyleSheet();
    sheet.replaceSync('*, *::before, *::after { all: revert !important; }');
    document.adoptedStyleSheets = [sheet];

    const add = window.addEventListener as (this: Window, ...args: unknown[]) => void;
    let dropped = false;
    window.addEventListener = function (this: Window, ...args: unknown[]) {
      if (args[0] === 'resize' && !dropped && document.querySelector('.gv1-selector-track')) {
        dropped = true;
        queueMicrotask(() => {
          document.adoptedStyleSheets = [];
        });
      }
      return add.apply(this, args);
    };

    const order: Order = { mounted: [], observed: [] };
    (window as unknown as { __dec1063Order: Order }).__dec1063Order = order;
    const isTrack = (el: Element) => el.classList.contains('gv1-selector-track');
    const overflowX = (el: Element) => getComputedStyle(el).overflowX;
    const heard = new WeakSet<ResizeObserver>();
    const Native = window.ResizeObserver;
    window.ResizeObserver = class extends Native {
      constructor(callback: ResizeObserverCallback) {
        super((entries, observer) => {
          const track = entries.find((entry) => isTrack(entry.target))?.target;
          if (track) {
            order.observed.push(overflowX(track));
            if (heard.has(observer)) return;
            heard.add(observer);
          }
          callback(entries, observer);
        });
      }
      observe(target: Element, options?: ResizeObserverOptions) {
        if (isTrack(target)) order.mounted.push(overflowX(target));
        super.observe(target, options);
      }
    };
  });
  await page.goto(`/deck/${deck}`);
  await page.locator('.gv1-selector-track .gv1-active').waitFor({ state: 'attached' });
  await expect
    .poll(() => page.evaluate(() => document.adoptedStyleSheets.length), {
      message: 'the route drops its sheet when the selector adds its resize listener',
    })
    .toBe(0);
  await settled(page);
}

// Show that a load made by `mountUnstyledInWebKitOrder` ran in that order,
// from what the selector's own observer was given. Without the first check
// the load could have mounted styled; without the second it could have run
// in `mountUnstyled`'s order.
async function expectWebKitOrder(page: Page): Promise<void> {
  const order = await page.evaluate(
    () => (window as unknown as { __dec1063Order: Order }).__dec1063Order,
  );
  expect(order.mounted, "the track's overflow-x when the selector began to observe it").toEqual([
    'visible',
  ]);
  expect(order.observed[0], "the track's overflow-x at the first observation").toBe('auto');
}

// Count the selector's `scrollTo` calls on the track, on every later load.
const countTrackScrolls = (page: Page) =>
  page.addInitScript(() => {
    const counts = window as unknown as { __dec1063TrackScrolls: number };
    counts.__dec1063TrackScrolls = 0;
    const scrollTo = Element.prototype.scrollTo as (this: Element, ...args: unknown[]) => void;
    Element.prototype.scrollTo = function (this: Element, ...args: unknown[]) {
      if (this.classList.contains('gv1-selector-track')) counts.__dec1063TrackScrolls += 1;
      return scrollTo.apply(this, args);
    };
  });

const trackScrolls = (page: Page) =>
  page.evaluate(() => (window as unknown as { __dec1063TrackScrolls: number }).__dec1063TrackScrolls);

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

// Where the active pill sits: its corner from the selector's corner.
type Pill = { x: number; y: number; scrollY: number };

const activePill = (page: Page): Promise<Pill> =>
  page.evaluate(() => {
    const selector = document.querySelector('.gv1-selector')!;
    const s = selector.getBoundingClientRect();
    const p = selector.querySelector('.gv1-selector-track .gv1-active')!.getBoundingClientRect();
    return { x: p.left - s.left, y: p.top - s.top, scrollY: window.scrollY };
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

    // hidden-legion's pill centres away from both ends; anvil-chorus is the
    // last pill, and the track stops at its end.
    for (const deck of ['hidden-legion', 'anvil-chorus']) {
      test(`the active pill of ${deck} reaches its place when the selector mounts before the styles apply`, async ({
        page,
      }) => {
        await countTrackScrolls(page);
        await openSettled(page, deck);
        const styled = await activePill(page);
        expect(await trackScrolls(page)).toBe(1);

        await mountUnstyled(page, deck);

        await expect
          .poll(async () => Math.abs((await activePill(page)).x - styled.x), {
            message: `the pill's x from the selector's corner, against ${styled.x} on a styled mount`,
          })
          .toBeLessThanOrEqual(1);
        const late = await activePill(page);
        expect(Math.abs(late.y - styled.y)).toBeLessThanOrEqual(1);
        expect(late.scrollY).toBe(styled.scrollY);
        // One scroll for the deck, as on a styled mount.
        expect(await trackScrolls(page)).toBe(1);
      });
    }

    test('a styled mount scrolls the track once for each deck change', async ({ page }) => {
      await countTrackScrolls(page);
      await openSettled(page, 'hidden-legion');
      expect(await trackScrolls(page)).toBe(1);

      // A client-side route change: the selector stays mounted.
      await page.evaluate(() => {
        history.pushState({}, '', '/deck/anvil-chorus');
        dispatchEvent(new PopStateEvent('popstate'));
      });
      await page.locator('.gv1-selector-track .gv1-active', { hasText: 'Anvil Chorus' }).waitFor();
      await settled(page);
      expect(await trackScrolls(page)).toBe(2);
    });

    for (const mount of ['a styled', 'an unstyled'] as const) {
      test(`after ${mount} mount, a rail the user has scrolled stays put when the track changes size`, async ({
        page,
      }) => {
        await openSettled(page, 'hidden-legion');
        let centred = await rail(page);
        // The pill centres with room to scroll 300px further.
        expect(centred.scrollLeft).toBeGreaterThan(0);
        expect(centred.scrollLeft + 300).toBeLessThan(centred.scrollWidth - centred.clientWidth);

        if (mount === 'an unstyled') {
          const styled = centred.scrollLeft;
          await mountUnstyled(page, 'hidden-legion');
          await expect
            .poll(async () => Math.abs((await rail(page)).scrollLeft - styled))
            .toBeLessThanOrEqual(1);
          centred = await rail(page);
        }

        const box = (await page.locator('.gv1-selector-track').boundingBox())!;
        await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
        await page.mouse.wheel(300, 0);
        await expect
          .poll(async () => (await rail(page)).scrollLeft)
          .toBeGreaterThan(centred.scrollLeft + 200);
        await settled(page);
        const wheeled = await rail(page);

        await narrowSelector(page, 60);
        await expect.poll(async () => (await rail(page)).clientWidth).toBe(centred.clientWidth - 60);
        // Time for a scroll back to the centre to run, if one started.
        await page.waitForTimeout(300);
        await settled(page);

        expect((await rail(page)).scrollLeft).toBe(wheeled.scrollLeft);
      });
    }
  });
}

// WebKit's order of the styles and the first size observation, which the
// cases above do not run. One width: the order does not depend on it.
test.describe('DEC-1063 @ 390px, the styles apply before the first observation', () => {
  test.use({ viewport: { width: 390, height: 900 } });

  test('the fade shows on the first deck', async ({ page }) => {
    await mountUnstyledInWebKitOrder(page, 'titan-convergence');

    // The styled track is at its start and overflows.
    await expect.poll(async () => (await rail(page)).fade).toBe('1');
    const r = await rail(page);
    expect(r.scrollLeft).toBe(0);
    expect(r.scrollWidth).toBeGreaterThan(r.clientWidth + 1);
    expect(r.atEnd).toBe(false);
    await expectWebKitOrder(page);
  });

  test('the active pill of anvil-chorus reaches its place', async ({ page }) => {
    await countTrackScrolls(page);
    await openSettled(page, 'anvil-chorus');
    const styled = await activePill(page);
    expect(await trackScrolls(page)).toBe(1);

    await mountUnstyledInWebKitOrder(page, 'anvil-chorus');

    await expect
      .poll(async () => Math.abs((await activePill(page)).x - styled.x), {
        message: `the pill's x from the selector's corner, against ${styled.x} on a styled mount`,
      })
      .toBeLessThanOrEqual(1);
    const late = await activePill(page);
    expect(Math.abs(late.y - styled.y)).toBeLessThanOrEqual(1);
    expect(late.scrollY).toBe(styled.scrollY);
    // One scroll for the deck, as on a styled mount.
    expect(await trackScrolls(page)).toBe(1);
    await expectWebKitOrder(page);
  });
});

// At 390px the unstyled track is 600px tall or more (y 121 to 722 in WebKit).
// On a viewport that ends above its bottom edge the mount effect scrolled the
// page to bring it into view, and the page stayed there.
test.describe('DEC-1063 @ 390x664px', () => {
  test.use({ viewport: { width: 390, height: 664 } });

  test('a selector that mounts before the styles apply does not scroll the page', async ({ page }) => {
    // The first pill: the track has nowhere to scroll, so only the page can move.
    await openSettled(page, 'titan-convergence');
    const styled = await activePill(page);

    await mountUnstyled(page, 'titan-convergence');

    const late = await activePill(page);
    expect(late.scrollY).toBe(styled.scrollY);
    expect(Math.abs(late.x - styled.x)).toBeLessThanOrEqual(1);
    expect(Math.abs(late.y - styled.y)).toBeLessThanOrEqual(1);
  });
});
