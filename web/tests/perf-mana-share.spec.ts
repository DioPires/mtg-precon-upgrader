// The MANA tile and the Performance header (owner-approved 2026-11-25).
//
// The mana label is decided on shares of the mana-simulation games, with two
// in-between states within a point of 50% (near strong, near adequate), and
// the share that decided it shows under it. titan-convergence's turn-4 share
// of games with 6 or more mana (its average mana value, 5.5, rounded up) sits
// in that band on every seed measured: near adequate.
//
// The header names both game counts: the goldfish's and the mana
// simulation's. Like the note it replaced, it is hidden at 768px and below.

import { expect, test } from './support/test';

test.describe('Performance: the MANA tile and the game counts', () => {
  test.use({ cards: 'seeded', viewport: { width: 1440, height: 900 } });

  // The line pins the committed simulation.json (50.2% at the committed seed):
  // a re-export that moves the share moves this line.
  test("titan-convergence's MANA tile shows its label and the share that decided it", async ({ page }) => {
    await page.goto('/deck/titan-convergence');
    const tile = page.locator('.gv1-perf .gv1-kpi').filter({ hasText: /^MANA/ });
    const line = '50.2% of games have 6 or more mana on turn 4';
    await expect(tile.locator(':scope > *')).toHaveText(['MANA', 'near adequate', line, /^mulligan · /]);
    await expect(tile.getByText(line, { exact: true })).toBeVisible();
  });

  test('the header names both game counts, hidden at 768px and shown at 769px', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 900 });
    await page.goto('/deck/titan-convergence');
    const note = page.locator('.gv1-perf .gv1-section-head > .gv1-mono-xs');
    await expect(page.locator('.gv1-perf-grid')).toBeVisible();
    await expect(note).toBeHidden();
    await page.setViewportSize({ width: 769, height: 900 });
    await expect(note).toBeVisible();
    await expect(note).toHaveText('· 10,000 goldfish games · 100,000 mana-sim games');
  });

});

// One count a line. At these widths the note has room for parts of both
// counts on one line ("games · 100,000"): at 860px in the web fonts, at
// 1,000px in the fallback faces. Only a line break between the counts keeps
// the second below the first.
for (const fonts of ['live', 'blocked'] as const) {
  test.describe(`Performance: one game count a line, ${fonts === 'live' ? 'web fonts' : 'fallback faces'}`, () => {
    test.use({ cards: 'seeded', fonts, viewport: { width: 860, height: 900 } });

    test('at 860 and 1,000px the second count starts below the first', async ({ page }) => {
      await page.goto('/deck/titan-convergence');
      const counts = page.locator('.gv1-perf .gv1-section-head > .gv1-mono-xs .gv1-perf-count');
      await expect(counts).toHaveCount(2);
      await page.evaluate(() => document.fonts.ready);
      for (const width of [860, 1000]) {
        await page.setViewportSize({ width, height: 900 });
        const first = await counts.nth(0).boundingBox();
        const second = await counts.nth(1).boundingBox();
        if (!first || !second) throw new Error(`${width}px: a count has no box`);
        expect(
          second.y,
          `${width}px: first count ${first.y} to ${first.y + first.height}, second from ${second.y}`,
        ).toBeGreaterThanOrEqual(first.y + first.height - 0.5);
      }
    });
  });
}
