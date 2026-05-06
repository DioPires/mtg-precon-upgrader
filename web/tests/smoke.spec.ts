import { expect, test } from '@playwright/test';

test('home renders the token-themed shell with topbar', async ({ page }) => {
  // `/` redirects to `/codex` post-DEC-167.
  await page.goto('/');
  await expect(page).toHaveURL(/\/codex$/);
  await expect(page.getByRole('banner')).toBeVisible();
  await expect(page.getByRole('navigation', { name: /surfaces/i })).toBeVisible();
  // background uses the ink-blue token; check that the body actually applied it.
  const bg = await page.evaluate(() =>
    getComputedStyle(document.body).backgroundColor,
  );
  // --gv1-bg → --gv1-ink-blue-900 → #0b1220 → rgb(11, 18, 32)
  expect(bg).toBe('rgb(11, 18, 32)');
});

test('unknown deck slugs land on the not-found stub', async ({ page }) => {
  for (const path of ['/deck/x', '/scrying/x', '/m/x']) {
    await page.goto(path);
    await expect(page.locator('h1', { hasText: /not found/i })).toBeVisible();
  }
});

test('Guide and Scrying nav links resolve to a real deck (DEC-168)', async ({ page }) => {
  await page.goto('/codex');

  const guide = page.getByRole('link', { name: /guide/i });
  const scrying = page.getByRole('link', { name: /scrying/i });

  // Topbar resolves the active deck once the index loads; href must never be the '_' sentinel.
  await expect(guide).toHaveAttribute('href', /\/deck\/[^_/][^/]*$/);
  await expect(scrying).toHaveAttribute('href', /\/scrying\/[^_/][^/]*$/);

  await guide.click();
  await expect(page).toHaveURL(/\/deck\/[^_/]+/);
  await expect(page.locator('.gv1-deck-guide')).toBeVisible();
  await expect(page.locator('.gv1-stub-title', { hasText: /not found/i })).toHaveCount(0);

  await page.getByRole('link', { name: /scrying/i }).click();
  await expect(page).toHaveURL(/\/scrying\/[^_/]+/);
  await expect(page.locator('.gv1-deck-guide')).toBeVisible();
  await expect(page.locator('.gv1-stub-title', { hasText: /not found/i })).toHaveCount(0);
});

test('SPA refresh serves index.html on deep routes (DEC-173)', async ({ page }) => {
  const indexResp = await page.request.get('/data/index.json');
  const idx = (await indexResp.json()) as { commanders: { id: string }[] };
  const first = idx.commanders[0]!.id;

  await page.goto(`/deck/${first}`);
  await expect(page.locator('.gv1-deck-guide')).toBeVisible();
  await page.reload();
  await expect(page.locator('.gv1-deck-guide')).toBeVisible();

  for (const path of ['/codex', '/compare', '/shopping', `/scrying/${first}`, `/m/${first}`]) {
    await page.goto(path);
    await page.reload();
    await expect(page.getByRole('banner')).toBeVisible();
    await expect(page.locator('.gv1-stub-title', { hasText: /not found/i })).toHaveCount(0);
  }
});

test('last-viewed deck persists across reload (DEC-168)', async ({ page }) => {
  await page.goto('/codex');
  // Wait for the first index load → Guide link points at first deck.
  await expect(page.getByRole('link', { name: /guide/i })).toHaveAttribute(
    'href',
    /\/deck\/[^_/]+/,
  );

  // Visit the second deck so it becomes the "last viewed" target.
  const indexResp = await page.request.get('/data/index.json');
  const idx = (await indexResp.json()) as { commanders: { id: string }[] };
  const second = idx.commanders[1]?.id ?? idx.commanders[0]!.id;
  await page.goto(`/deck/${second}`);
  await expect(page.locator('.gv1-deck-guide')).toBeVisible();

  await page.reload();
  await page.goto('/codex');
  await expect(page.getByRole('link', { name: /guide/i })).toHaveAttribute(
    'href',
    new RegExp(`/deck/${second}$`),
  );
});
