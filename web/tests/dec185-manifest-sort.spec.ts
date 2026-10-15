import { expect, test } from './support/test';

// DEC-185 — The Manifest sorts each subsection by mana value ascending,
// alphabetical tiebreak. The cmc map comes from cardCache, which holds every
// deck card from data/card-metadata.json at first paint (DEC-1102).
test('Manifest subsections render in cmc-ascending order', async ({ page }) => {
  await page.goto('/deck/titan-convergence');
  // Wait for the Manifest section to render.
  await expect(page.locator('.gv1-decklist')).toBeVisible();

  const groups = page.locator('.gv1-dl-group');
  const groupCount = await groups.count();
  expect(groupCount).toBeGreaterThan(2);

  // For each non-Commander group, read card names in render order.
  const groupData = await page.evaluate(() => {
    const groups = Array.from(document.querySelectorAll('.gv1-dl-group'));
    return groups.map((g) => ({
      header: g.querySelector('.gv1-dl-group-head .gv1-serif-sm')?.textContent || '',
      cards: Array.from(g.querySelectorAll('.gv1-dl-row')).map(
        (row) => row.getAttribute('data-card-name') || '',
      ),
    }));
  });

  // The cmc of each card, from the file that the app's card cache holds.
  const cmcByName = await page.evaluate(async () => {
    const file = (await (await fetch('/data/card-metadata.json')).json()) as Record<string, { cmc?: number }>;
    const map: Record<string, number | undefined> = {};
    for (const [name, entry] of Object.entries(file)) map[name] = entry.cmc;
    return map;
  });

  // For each non-Commander group with ≥ 2 cards that have known cmc, assert
  // cmc-then-name ordering across consecutive pairs.
  let pairs = 0;
  for (const grp of groupData) {
    if (grp.header.toLowerCase().startsWith('commander')) continue;
    if (grp.cards.length < 2) continue;
    for (let i = 0; i < grp.cards.length - 1; i++) {
      const a = grp.cards[i];
      const b = grp.cards[i + 1];
      const ca = cmcByName[a];
      const cb = cmcByName[b];
      // Skip pairs where either side is not in the file.
      if (ca == null || cb == null) continue;
      pairs += 1;
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
  // Every card of the deck is in the file, so the check is not empty.
  expect(pairs).toBeGreaterThan(50);
});
