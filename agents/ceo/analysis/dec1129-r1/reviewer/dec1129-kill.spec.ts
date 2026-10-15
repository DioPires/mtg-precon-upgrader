// DEC-1129 kill cases for M3 and M4: the pin's 700px threshold, read on each
// side. 1280×700 is the shortest screen on which the part pins; at 1280×699
// the whole rail stays in the flow.

import { expect, test, type Page } from './support/test';

const PIN = '.gv1-lab-rail-pin';

async function openLab(page: Page): Promise<void> {
  await page.goto('/combos');
  await expect(page.locator('.gv1-lab-attrib')).toBeVisible();
  await expect(page.locator('.gv1-lab-combo').first()).toBeVisible();
  await page.evaluate(() => document.fonts.ready);
}

// Scroll `past` px beyond the part's own place in the page, and read its box.
async function partScrolledPast(page: Page, past: number) {
  return page.evaluate(
    ({ selector, by }) => {
      window.scrollTo(0, 0);
      const pin = document.querySelector(selector)!;
      const target = Math.round(pin.getBoundingClientRect().top + window.scrollY) + by;
      window.scrollTo(0, target);
      const r = pin.getBoundingClientRect();
      return { scrolled: window.scrollY, target, top: r.top, bottom: r.bottom };
    },
    { selector: PIN, by: past },
  );
}

test.describe('DEC-1129 kill case M3: Combo Lab rail @ 1280×700', () => {
  test.use({ viewport: { width: 1280, height: 700 } });

  test('the part pins whole, 20px from the top', async ({ page }) => {
    await openLab(page);
    for (const past of [600, 1500]) {
      const m = await partScrolledPast(page, past);
      expect(m.scrolled, 'the report is long enough to scroll that far').toBe(m.target);
      expect(Math.abs(m.top - 20), `top of the part, ${past}px past its place: read ${m.top}`).toBeLessThan(1);
      expect(m.bottom, 'the pinned part fits the screen whole').toBeLessThanOrEqual(700);
    }
  });
});

test.describe('DEC-1129 kill case M4: Combo Lab rail @ 1280×699', () => {
  test.use({ viewport: { width: 1280, height: 699 } });

  test('the whole rail scrolls with the page', async ({ page }) => {
    await openLab(page);
    const m = await partScrolledPast(page, 600);
    expect(m.scrolled, 'the report is long enough to scroll that far').toBe(m.target);
    expect(Math.abs(m.top + 600), `top of the part, 600px past its place: read ${m.top}`).toBeLessThan(1);
  });
});
