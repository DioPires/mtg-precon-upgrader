import { expect, test } from './support/test';

// DEC-185 — The Manifest sorts each subsection by mana value ascending,
// alphabetical tiebreak. Verifies the cmc map populated via cardCache (Scryfall).
test('Manifest subsections render in cmc-ascending order', async ({ page }) => {
  await page.goto('/deck/titan-convergence');
  // Wait for the Manifest section to render.
  await expect(page.locator('.gv1-decklist')).toBeVisible();

  // Allow time for Scryfall fetches to hydrate cmc on cards.
  // cardCache throttles ≥80ms between calls; 99 cards ≈ 8s worst case.
  // Many cards will be cached by other surfaces, but give a generous wait.
  await page.waitForTimeout(10_000);

  const groups = page.locator('.gv1-dl-group');
  const groupCount = await groups.count();
  expect(groupCount).toBeGreaterThan(2);

  // For each non-Commander group, read card names in render order, then read
  // cmc by inspecting the cardCache via window.localStorage.
  const groupData = await page.evaluate(() => {
    const groups = Array.from(document.querySelectorAll('.gv1-dl-group'));
    return groups.map((g) => ({
      header: g.querySelector('.gv1-dl-group-head .gv1-serif-sm')?.textContent || '',
      cards: Array.from(g.querySelectorAll('.gv1-dl-row')).map(
        (row) => row.getAttribute('data-card-name') || '',
      ),
    }));
  });

  // Pull cmc from localStorage (cardCache writes loaded entries there).
  const cmcByName = await page.evaluate(() => {
    const map: Record<string, number | undefined> = {};
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i)!;
      if (!key.startsWith('gv1-card:')) continue;
      try {
        const entry = JSON.parse(localStorage.getItem(key)!);
        if (entry?.status === 'loaded' && typeof entry.cmc === 'number') {
          map[entry.name] = entry.cmc;
        }
      } catch { /* ignore */ }
    }
    return map;
  });

  // For each non-Commander group with ≥ 2 cards that have known cmc, assert
  // cmc-then-name ordering across consecutive pairs.
  for (const grp of groupData) {
    if (grp.header.toLowerCase().startsWith('commander')) continue;
    if (grp.cards.length < 2) continue;
    for (let i = 0; i < grp.cards.length - 1; i++) {
      const a = grp.cards[i];
      const b = grp.cards[i + 1];
      const ca = cmcByName[a];
      const cb = cmcByName[b];
      // Skip pairs where either side hasn't been hydrated yet.
      if (ca == null || cb == null) continue;
      if (ca !== cb) {
        expect(ca, `[${grp.header}] ${a} (${ca}) before ${b} (${cb})`).toBeLessThanOrEqual(cb);
      } else {
        expect(
          a.localeCompare(b),
          `[${grp.header}] ${a} before ${b} (alpha tiebreak at cmc=${ca})`,
        ).toBeLessThanOrEqual(0);
      }
    }
  }
});
