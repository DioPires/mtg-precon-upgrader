// DEC-1028: the Apothecary's filtered empty state and `Clear filter ×` at 390px.
//
// jsdom has no layout, so the unit cases can only count child nodes and read
// `document.activeElement`. These cases measure the boxes in a browser.
// `.gv1-empty` is a grid: each child node takes a row, so a sentence split
// across three nodes stacked on three lines. `Clear filter ×` wraps to a line
// of its own at this width, where no chip stretches it to 44px.

import { expect, test, type Page } from './support/test';

const DECK = 'stampede-acres';
const ROLE = 'removal-board';

type PoolEntry = { deck_role?: string | null; mitigates_gap?: string | null };

// Hold the pool at zero board wipes. The empty state then outlives the pool
// content work on DEC-1016, which gives this deck a board wipe to offer.
async function withoutBoardWipes(page: Page): Promise<void> {
  await page.route(`**/data/commanders/${DECK}/candidates.json`, async (route) => {
    const response = await route.fetch();
    const body = (await response.json()) as { candidates: PoolEntry[] };
    body.candidates = body.candidates.filter((c) => c.deck_role !== ROLE && c.mitigates_gap !== ROLE);
    await route.fulfill({ response, json: body });
  });
}

test.describe('DEC-1028 @ 390px', () => {
  test.use({ viewport: { width: 390, height: 844 } });

  test.beforeEach(async ({ page }) => {
    await withoutBoardWipes(page);
    await page.goto(`/deck/${DECK}`);
    await page.locator('.gv1-apothecary').getByRole('button', { name: /board wipes/i }).click();
  });

  test('the filtered empty state reads on one line', async ({ page }) => {
    const empty = page.locator('.gv1-apothecary .gv1-empty');
    await expect(empty).toHaveText('No remedies match Board Wipes.');

    const sentence = await empty.evaluate((el) => {
      const child = el.firstElementChild!;
      return {
        nodes: el.childNodes.length,
        height: child.getBoundingClientRect().height,
        fontSize: parseFloat(getComputedStyle(child).fontSize),
      };
    });
    expect(sentence.nodes).toBe(1);
    // A second line would double the height; one line stays under two font sizes.
    expect(sentence.height).toBeLessThan(sentence.fontSize * 2);
  });

  test('the clear button is as tall as the chips', async ({ page }) => {
    const chip = await page.locator('.gv1-apothecary button.gv1-apo-malady.is-active').boundingBox();
    const clear = await page.locator('.gv1-apo-malady-clear').boundingBox();

    expect(chip!.height).toBeGreaterThanOrEqual(44);
    expect(clear!.height).toBeGreaterThanOrEqual(44);
  });

  test('Enter on the clear button moves focus to the chip it cleared', async ({ page }) => {
    const clear = page.locator('.gv1-apo-malady-clear');
    await clear.focus();
    await page.keyboard.press('Enter');

    await expect(clear).toHaveCount(0);
    const chip = page.locator('.gv1-apothecary').getByRole('button', { name: /board wipes/i });
    await expect(chip).toBeFocused();
    await expect(chip).toHaveAttribute('aria-pressed', 'false');
  });
});
