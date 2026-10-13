// DEC-1019: `.gv1-root` is `overflow: clip`, so nothing scrolls it, and the
// sticky rails inside it answer to the viewport.
//
// While the root was `overflow: hidden` it was a scroll container. Script
// could move it sideways with no way back (DEC-1008), and every
// `position: sticky` rail inside it was pinned to a box that never scrolls —
// so none of them had ever pinned. `clip` switches them on. Two are too tall
// to pin and stay in the flow; the cases below hold each one to that.

import { expect, test, type Page } from './support/test';

// Scroll `past` px beyond the rail's own position and read where it ends up:
// 0 when it pins, `-past` when it scrolls with the page.
async function railTopScrolledPast(page: Page, selector: string, past: number): Promise<number> {
  return page.locator(selector).evaluate((el, by) => {
    window.scrollTo(0, Math.round(el.getBoundingClientRect().top + window.scrollY) + by);
    return el.getBoundingClientRect().top;
  }, past);
}

// The scroll target is a whole pixel and the rail's position is not.
function expectWithin1px(received: number, expected: number): void {
  expect(Math.abs(received - expected), `expected ${expected}, read ${received}`).toBeLessThan(1);
}

test.describe('DEC-1019 root @ 390px', () => {
  test.use({ viewport: { width: 390, height: 900 } });

  test('script cannot scroll the root sideways', async ({ page }) => {
    await page.goto('/deck/anvil-chorus');
    await page.locator('.gv1-perf-grid').waitFor();
    await page.locator('.gv1-selector-track .gv1-active').waitFor();

    // The guide has fitted the viewport since DEC-1008, which leaves the root
    // nothing to scroll to. Add a block that is too wide, as the guide was.
    const m = await page.evaluate(() => {
      const root = document.querySelector('.gv1-root')!;
      const wide = document.createElement('div');
      wide.style.cssText = 'width: 2000px; height: 1px';
      root.appendChild(wide);

      root.scrollLeft = 100;
      const assigned = root.scrollLeft;
      root.scrollLeft = 0;
      wide.scrollIntoView({ inline: 'end' });
      return {
        rootScrollWidth: root.scrollWidth,
        assigned,
        scrolledIntoView: root.scrollLeft,
        pageScrollX: window.scrollX,
      };
    });

    // `clip` still reports the wide block. The overflow checks in dec181,
    // dec184 and dec1008 read `scrollWidth` and depend on that.
    expect(m.rootScrollWidth).toBeGreaterThan(390);
    expect(m.assigned, 'root.scrollLeft after `root.scrollLeft = 100`').toBe(0);
    expect(m.scrolledIntoView, 'root.scrollLeft after scrollIntoView on the wide block').toBe(0);
    expect(m.pageScrollX, 'the page must not take the scroll instead').toBe(0);
  });
});

// The Shopping deck rail pins only where it takes a quarter of the screen or
// less: tablet portrait. It is 222px tall on a phone.
const SHOPPING = [
  { width: 320, height: 568, pins: false },
  { width: 390, height: 844, pins: false },
  { width: 667, height: 375, pins: false }, // phone, landscape
  { width: 768, height: 1024, pins: true },
];

for (const { width, height, pins } of SHOPPING) {
  test.describe(`DEC-1019 Shopping rail @ ${width}×${height}`, () => {
    test.use({ viewport: { width, height } });

    test(`the deck rail ${pins ? 'pins to the top' : 'scrolls with the page'}`, async ({ page }) => {
      await page.goto('/shopping');
      const rail = page.locator('.gv1-shop-rail');
      await rail.waitFor();
      const railHeight = await rail.evaluate((el) => el.getBoundingClientRect().height);

      const top = await railTopScrolledPast(page, '.gv1-shop-rail', 600);

      if (pins) {
        expectWithin1px(top, 0);
        expect(railHeight / height, 'share of the screen the pinned rail takes').toBeLessThanOrEqual(0.25);
      } else {
        expectWithin1px(top, -600);
      }
    });
  });
}

test.describe('DEC-1019 Shopping rail, keyboard @ 768×1024', () => {
  test.use({ viewport: { width: 768, height: 1024 } });

  // A control that already sits on screen, under the pinned rail, does not
  // scroll when Tab reaches it unless it carries a scroll margin.
  test('focus does not land under the pinned rail', async ({ page }) => {
    await page.goto('/shopping');
    const rail = page.locator('.gv1-shop-rail');
    const sort = page.getByRole('button', { name: 'Type', exact: true });
    await rail.waitFor();
    await sort.waitFor();

    // Put the first control after the rail 40px down the screen, then Tab to
    // it from the rail's last chip.
    await sort.evaluate((el) => {
      window.scrollTo(0, Math.round(el.getBoundingClientRect().top + window.scrollY) - 40);
    });
    expectWithin1px(await rail.evaluate((el) => el.getBoundingClientRect().top), 0);
    await page.locator('.gv1-shop-chip').last().evaluate((el: HTMLElement) => el.focus({ preventScroll: true }));
    await page.keyboard.press('Tab');
    await expect(sort).toBeFocused();

    const railBottom = await rail.evaluate((el) => el.getBoundingClientRect().bottom);
    const sortTop = await sort.evaluate((el) => el.getBoundingClientRect().top);
    expect(sortTop, `top of the focused control (the rail ends at ${railBottom})`).toBeGreaterThanOrEqual(railBottom);
  });
});

test.describe('DEC-1019 Combo Lab rail @ 1280×800', () => {
  test.use({ viewport: { width: 1280, height: 800 } });

  // The control rail is taller than the screen with the fleet's decks in it.
  // Pinned, its lower blocks (Contents, the tier legend, the exports) would
  // sit below the fold for the length of the report.
  test('the control rail scrolls with the page', async ({ page }) => {
    await page.goto('/combos');
    await expect(page.locator('.gv1-lab-attrib')).toBeVisible();
    await expect(page.locator('.gv1-lab-combo').first()).toBeVisible();

    const railHeight = await page.locator('.gv1-lab-rail').evaluate((el) => el.getBoundingClientRect().height);
    expect(railHeight, 'the rail is taller than the screen; if it no longer is, it can pin').toBeGreaterThan(800);

    expectWithin1px(await railTopScrolledPast(page, '.gv1-lab-rail', 600), -600);
  });
});
