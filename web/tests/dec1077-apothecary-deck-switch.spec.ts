// DEC-1077: each deck mounts its own Apothecary at 390px.
//
// The route renders one <Apothecary> for every deck. With no key, React kept
// it mounted across a deck switch, and the next deck opened with the last
// deck's filter pressed and its breakdown open. The case presses both on
// stampede-acres, picks Titan Convergence in the deck selector and reads a
// fresh Apothecary there.

import { expect, test } from './support/test';

test.describe('DEC-1077 @ 390px', () => {
  test.use({ viewport: { width: 390, height: 844 }, cards: 'seeded' });

  test('a deck switch clears the filter and closes the breakdown', async ({ page }) => {
    await page.goto('/deck/stampede-acres');

    const apothecary = page.locator('.gv1-apothecary');
    const breakdown = apothecary.locator('button.gv1-apo-details-btn');
    const boardWipes = apothecary.getByRole('button', { name: /board wipes/i });
    await breakdown.click();
    await expect(breakdown).toHaveAttribute('aria-expanded', 'true');
    await boardWipes.click();
    await expect(boardWipes).toHaveAttribute('aria-pressed', 'true');

    await page.getByRole('tab', { name: /Titan Convergence/ }).click();

    // Read the URL before each expect: a switch that did not happen fails
    // here, not on the next expect.
    const onTitanConvergence = () => expect(page).toHaveURL(/\/deck\/titan-convergence$/);

    await onTitanConvergence();
    await expect(apothecary.locator('[aria-pressed="true"]')).toHaveCount(0);
    await onTitanConvergence();
    await expect(apothecary.getByRole('button', { name: 'Clear filter', exact: true })).toHaveCount(0);
    await onTitanConvergence();
    await expect(apothecary.locator('.gv1-apo-remedies article.gv1-apo-remedy')).toHaveCount(30);
    await onTitanConvergence();
    await expect(apothecary.getByRole('status')).toHaveText('');
    await onTitanConvergence();
    await expect(breakdown).toHaveText('Show breakdown');
    await expect(breakdown).toHaveAttribute('aria-expanded', 'false');
  });
});
