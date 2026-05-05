import { expect, test } from '@playwright/test';

test('home renders the token-themed shell with topbar', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('banner')).toBeVisible();
  await expect(page.getByRole('navigation', { name: /surfaces/i })).toBeVisible();
  await expect(page.getByRole('heading', { name: /the grimoire/i })).toBeVisible();
  // background uses the ink-blue token; check that the body actually applied it.
  const bg = await page.evaluate(() =>
    getComputedStyle(document.body).backgroundColor,
  );
  // --gv1-bg → --gv1-ink-blue-900 → #0b1220 → rgb(11, 18, 32)
  expect(bg).toBe('rgb(11, 18, 32)');
});

test('each artboard route has a heading', async ({ page }) => {
  for (const path of ['/codex', '/compare', '/shopping', '/deck/x', '/scrying/x', '/mobile/x']) {
    await page.goto(path);
    await expect(page.locator('h1')).toBeVisible();
  }
});
