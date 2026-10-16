// DEC-1146: after browser Back or Forward, focus goes to the deck selector's
// active pill when the change left it astray, and a pick of the open deck
// adds no history entry.
//
// Each deck mounts its own Apothecary (DEC-1077). A Back from a deck whose
// Board Wipes chip had focus removed the chip: focus fell to `body`, and
// Chromium kept its sequential focus starting point where the chip was. The
// first Tab then landed in the new deck's Apothecary, thousands of pixels
// down the page. A Back after a click switch left focus on a pill that was
// no longer active.

import { expect, test, type Page } from './support/test';

const WIDTHS = [390, 1280];

type FocusRead = { name: string; before: number; after: number };

// Record window.scrollY just before and just after each focus call that the
// page makes from now on. The routes change in the same document, so the
// recorder stays in place across Back.
async function recordFocus(page: Page): Promise<void> {
  await page.evaluate(() => {
    const w = window as unknown as { focusReads: FocusRead[] };
    w.focusReads = [];
    const focus = HTMLElement.prototype.focus;
    HTMLElement.prototype.focus = function (this: HTMLElement, options?: FocusOptions) {
      const before = window.scrollY;
      focus.call(this, options);
      w.focusReads.push({
        name: this.querySelector('.gv1-sel-pill-name')?.textContent ?? this.tagName,
        before,
        after: window.scrollY,
      });
    };
  });
}

const focusReads = (page: Page) =>
  page.evaluate(() => (window as unknown as { focusReads: FocusRead[] }).focusReads);

for (const width of WIDTHS) {
  test.describe(`DEC-1146 @ ${width}px`, () => {
    test.use({ viewport: { width, height: 844 }, cards: 'seeded' });

    test('Back after a chip press focuses the active pill, and the next Tab stays out of the Apothecary', async ({
      page,
    }) => {
      await page.goto('/deck/stampede-acres');
      await page.getByRole('tab', { name: /Titan Convergence/ }).click();
      await expect(page).toHaveURL(/\/deck\/titan-convergence$/);
      const chip = page.locator('.gv1-apothecary').getByRole('button', { name: /board wipes/i });
      await chip.click();
      await expect(chip).toBeFocused();

      await recordFocus(page);
      await page.goBack();
      await expect(page).toHaveURL(/\/deck\/stampede-acres$/);
      const pill = page.getByRole('tab', { name: /Field of Blades/ });
      await expect(pill).toBeFocused();
      await expect(pill).toHaveAttribute('aria-selected', 'true');
      await expect(pill).toHaveAttribute('tabindex', '0');
      const reads = await focusReads(page);
      expect(reads).toHaveLength(1);
      expect(reads[0].name).toBe('Field of Blades');
      expect(reads[0].after).toBe(reads[0].before);

      await page.keyboard.press('Tab');
      const next = await page.evaluate(() => {
        const el = document.activeElement;
        return { body: el === document.body, inApothecary: !!el?.closest('.gv1-apothecary') };
      });
      expect(next.body).toBe(false);
      expect(next.inApothecary).toBe(false);
    });

    test('Back after a click switch focuses the active pill', async ({ page }) => {
      await page.goto('/deck/stampede-acres');
      await page.getByRole('tab', { name: /Titan Convergence/ }).click();
      await expect(page).toHaveURL(/\/deck\/titan-convergence$/);

      await page.goBack();
      await expect(page).toHaveURL(/\/deck\/stampede-acres$/);
      const pill = page.getByRole('tab', { name: /Field of Blades/ });
      await expect(pill).toBeFocused();
      await expect(pill).toHaveAttribute('aria-selected', 'true');
    });
  });
}

// Titan Convergence is the first scribed deck: `Home` on it picks the open
// deck, and so does a click on its pill.
test.describe('DEC-1146: a pick of the open deck adds no history entry', () => {
  test.use({ cards: 'seeded' });

  for (const route of ['deck', 'scrying']) {
    test(`/${route}: Home and a click on the active pill keep history.length`, async ({ page }) => {
      await page.goto(`/${route}/titan-convergence`);
      const pill = page.getByRole('tab', { name: /Titan Convergence/ });
      await expect(pill).toHaveAttribute('aria-selected', 'true');
      const length = () => page.evaluate(() => history.length);
      const start = await length();

      await pill.focus();
      await page.keyboard.press('Home');
      await expect(pill).toBeFocused();
      await expect(page).toHaveURL(new RegExp(`/${route}/titan-convergence$`));
      expect(await length()).toBe(start);

      await pill.click();
      await expect(page).toHaveURL(new RegExp(`/${route}/titan-convergence$`));
      expect(await length()).toBe(start);
    });
  }
});
