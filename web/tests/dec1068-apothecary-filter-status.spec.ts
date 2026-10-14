// DEC-1068: the Apothecary's filter status line at 390px.
//
// The status line is a polite live region (WCAG 4.1.3). It is empty at load
// and reads the filter's result after each filter action. stampede-acres has
// one role gap, Board Wipes, and no board wipe in its pool, so a press on the
// chip gives the empty-state words. The case runs with the web fonts live and
// with them blocked.

import { expect, test, type Page } from './support/test';

const DECK = 'stampede-acres';
const ROLE = 'removal-board';

type PoolEntry = { deck_role?: string | null; mitigates_gap?: string | null };

// Hold the pool at zero board wipes, as dec1028-apothecary-followups.spec.ts
// does, so the expected text outlives the pool content work on DEC-1016.
async function withoutBoardWipes(page: Page): Promise<void> {
  await page.route(`**/data/commanders/${DECK}/candidates.json`, async (route) => {
    const response = await route.fetch();
    const body = (await response.json()) as { candidates: PoolEntry[] };
    body.candidates = body.candidates.filter((c) => c.deck_role !== ROLE && c.mitigates_gap !== ROLE);
    await route.fulfill({ response, json: body });
  });
}

for (const fonts of ['live', 'blocked'] as const) {
  test.describe(`DEC-1068 @ 390px, fonts ${fonts}`, () => {
    test.use({ viewport: { width: 390, height: 844 }, fonts });

    test('the status line reads the filter result', async ({ page }) => {
      await withoutBoardWipes(page);
      await page.goto(`/deck/${DECK}`);

      const apothecary = page.locator('.gv1-apothecary');
      const status = apothecary.getByRole('status');
      await expect(status).toHaveCount(1);
      await expect(status).toHaveText('');

      await apothecary.getByRole('button', { name: /board wipes/i }).click();
      await expect(status).toHaveText('No remedies match Board Wipes.');

      await apothecary.getByRole('button', { name: 'Clear filter', exact: true }).click();
      await expect(apothecary.locator('.gv1-apo-remedies article.gv1-apo-remedy')).toHaveCount(30);
      await expect(status).toHaveText('Filter cleared: 30 remedies.');
    });
  });
}
