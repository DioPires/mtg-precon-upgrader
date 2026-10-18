// DEC-1201 scratch: the guard case for R6, as a separate file for the run.
// The proposed text for dec1177-empty-sigils.spec.ts is the test below; that
// spec already has `beforeGlyph`.
import { expect, test, type Page } from './support/test';

async function beforeGlyph(page: Page, text: string): Promise<string> {
  return page
    .locator('.gv1-empty')
    .filter({ hasText: text })
    .evaluate((el) => getComputedStyle(el, '::before').content);
}

// A box with no `.gv1-rune` span keeps the ◇ of `.gv1-empty::before`, its only mark (DEC-1199).
// No deck in the repository has an empty `winConditions`, so the route empties it.
test('the deck page with no win conditions keeps the ◇ of its empty state (DEC-1199)', async ({ page }) => {
  await page.route('**/commanders/eternal-agony/deck.json', async (route) => {
    const response = await route.fetch();
    await route.fulfill({ response, json: { ...(await response.json()), winConditions: [] } });
  });
  await page.goto('/deck/eternal-agony');
  const message = "No documented win conditions in this deck's dossier yet.";
  const empty = page.locator('.gv1-empty').filter({ hasText: message });
  await expect(empty).toHaveCount(1);
  await expect(empty.locator('.gv1-rune')).toHaveCount(0);
  expect(await beforeGlyph(page, message)).toMatch(/^"◇"/);
});
