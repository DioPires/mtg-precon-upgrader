// DEC-942 regression: a 4,500-row owned-cards import must survive the deck
// cache. Before the fix, loadAll() filled localStorage to ~5.17M chars on
// /shopping, the owned-map write threw QuotaExceededError, saveOwned swallowed
// it, and /atlas showed "not imported" (DEC-941).

import { expect, test } from './support/test';

const OWNED_KEY = 'grimoire-owned-cards';
const ROWS = 4500;

/** ManaBox-shaped export: a Name,Quantity header plus the usual extra columns. */
function manaboxCsv(): string {
  const lines = ['Name,Set code,Collector number,Foil,Quantity,Scryfall ID'];
  // Sol Ring is in every deck, so /atlas can resolve it from the local index.
  lines.push('Sol Ring,LTC,284,normal,3,00000000-0000-0000-0000-000000000000');
  for (let i = lines.length - 1; i <= ROWS; i += 1) {
    lines.push(`Filler Card ${i} of the Very Long Padded Name,MH3,${i},normal,2,`
      + `11111111-2222-3333-4444-${String(i).padStart(12, '0')}`);
  }
  return lines.join('\n');
}

async function storageChars(page: import('./support/test').Page): Promise<number> {
  return page.evaluate(() => {
    let n = 0;
    for (let i = 0; i < localStorage.length; i += 1) {
      const k = localStorage.key(i)!;
      n += k.length + (localStorage.getItem(k)?.length ?? 0);
    }
    return n;
  });
}

test('a 4,500-row owned import persists and reaches /atlas', async ({ page }) => {
  await page.goto('/shopping');
  await page.evaluate(() => localStorage.clear());
  await page.reload();

  // Wait for loadAll() to finish writing the deck cache before importing.
  await expect(page.getByRole('heading', { name: /Need to buy/i })).toBeVisible();
  await expect(page.locator('.gv1-shop-chip').first()).toBeVisible();
  await page.waitForFunction(
    () => Object.keys(localStorage).some((k) => k.startsWith('gv1-deck-data-')),
  );

  const beforeChars = await storageChars(page);
  // The persisted deck cache must leave plenty of room under the ~5.2M quota.
  expect(beforeChars).toBeLessThan(3_500_000);

  await page.setInputFiles('#gv1-shop-owned-file', {
    name: 'owned.csv',
    mimeType: 'text/csv',
    buffer: Buffer.from(manaboxCsv(), 'utf8'),
  });

  // Honest success, not a swallowed failure.
  await expect(page.locator('.gv1-shop-import-ok')).toContainText(/Imported \d+ unique cards/);
  await expect(page.locator('.gv1-shop-import-err')).toHaveCount(0);
  await expect(page.locator('.gv1-shop-owned-bar')).toContainText('saved locally');
  await expect(page.locator('.gv1-shop-owned-bar')).not.toContainText('NOT saved');

  const raw = await page.evaluate((k) => localStorage.getItem(k), OWNED_KEY);
  expect(raw, 'owned map landed in localStorage').toBeTruthy();
  const entries = JSON.parse(raw!) as Array<[string, number]>;
  expect(entries.length).toBeGreaterThan(4_000);
  expect(entries).toContainEqual(['Sol Ring', 3]);

  // /atlas reads the same key and must show the quantity.
  await page.goto('/atlas');
  const search = page.locator('#gv1-atlas-input');
  await search.fill('Sol Ring');
  await expect(page.getByRole('option').first()).toBeVisible();
  await page.getByRole('option').filter({ hasText: /^Sol Ring/ }).first().click();

  const ownedStat = page.locator('.gv1-atlas-result-stat', { hasText: 'OWNED' });
  await expect(ownedStat).toContainText('×3');
  await expect(ownedStat).toContainText('in inventory');
});
