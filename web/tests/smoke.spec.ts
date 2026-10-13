import { expect, test } from './support/test';

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
  // /m/x redirects to /deck/x (DEC-183) which then renders the not-found stub.
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

test('Compare shows Vitals + bracket-normalized columns (DEC-390)', async ({ page }) => {
  await page.goto('/compare');
  await expect(page.locator('.gv1-cmp-table')).toBeVisible();

  const vitalsHeader = page.getByRole('columnheader', { name: /vitals/i });
  const normHeader = page.getByRole('columnheader', { name: /norm\./i });
  await expect(vitalsHeader).toBeVisible();
  await expect(normHeader).toBeVisible();

  // Vitals (metrics.global_health) is live data today — at least one row must
  // show a numeric score. Norm. stays em-dash until DEC-389 emits the field;
  // assert the column renders either a number or the placeholder, not blank.
  const rows = page.locator('.gv1-cmp-row');
  await expect(rows.first()).toBeVisible();
  const headerCells = page.locator('thead th');
  const vitalsIdx = await headerCells.evaluateAll((ths) =>
    ths.findIndex((th) => /vitals/i.test(th.textContent ?? '')),
  );
  const normIdx = await headerCells.evaluateAll((ths) =>
    ths.findIndex((th) => /norm\./i.test(th.textContent ?? '')),
  );
  const firstVitals = rows.first().locator('td').nth(vitalsIdx);
  const firstNorm = rows.first().locator('td').nth(normIdx);
  await expect(firstVitals).toHaveText(/\d+|—/);
  await expect(firstNorm).toHaveText(/\d+|—/);

  // Footer explains the two-score semantics.
  await expect(page.locator('.gv1-cmp-foot')).toContainText(/bracket bar/i);
  await expect(page.locator('.gv1-cmp-foot')).toContainText(/apples-to-apples/i);
});

test.describe('mobile responsive routing (DEC-181 + DEC-183)', () => {
  test.use({ viewport: { width: 390, height: 844 } });

  test('Topbar collapses to hamburger and exposes all surfaces', async ({ page }) => {
    await page.goto('/codex');

    // Desktop nav is hidden by CSS; the hamburger should be the visible
    // navigation entry-point.
    const hamburger = page.getByRole('button', { name: /open navigation menu/i });
    await expect(hamburger).toBeVisible();

    await hamburger.click();
    const menu = page.locator('.gv1-topbar-mobile-menu');
    await expect(menu).toBeVisible();
    await expect(menu.getByRole('link', { name: /codex/i })).toBeVisible();
    await expect(menu.getByRole('link', { name: /guide/i })).toBeVisible();
    await expect(menu.getByRole('link', { name: /scrying/i })).toBeVisible();
    await expect(menu.getByRole('link', { name: /shopping/i })).toBeVisible();
    await expect(menu.getByRole('link', { name: /compare/i })).toBeVisible();
  });

  test('/m/:id redirects to /deck/:id on mobile (DEC-183: bezel artboard retired)', async ({ page }) => {
    const idx = await (await page.request.get('/data/index.json')).json();
    const first = idx.commanders[0].id as string;

    await page.goto(`/m/${first}`);
    await expect(page).toHaveURL(new RegExp(`/deck/${first}$`));
    await expect(page.locator('.gv1-deck-guide')).toBeVisible();
  });

  test('/deck/:id renders responsively at phone widths (DEC-183: no /m/ redirect)', async ({ page }) => {
    const idx = await (await page.request.get('/data/index.json')).json();
    const first = idx.commanders[0].id as string;

    await page.goto(`/deck/${first}`);
    await expect(page).toHaveURL(new RegExp(`/deck/${first}$`));
    await expect(page.locator('.gv1-deck-guide')).toBeVisible();
  });

  test('each surface renders something at 390x844 (no broken layout)', async ({ page }) => {
    const idx = await (await page.request.get('/data/index.json')).json();
    const first = idx.commanders[0].id as string;

    await page.goto('/codex');
    await expect(page.locator('.gv1-codex')).toBeVisible();

    await page.goto('/compare');
    await expect(page.locator('.gv1-cmp-table')).toBeVisible();

    await page.goto('/shopping');
    await expect(page.locator('.gv1-shop-rail')).toBeVisible();

    await page.goto(`/deck/${first}`);
    await expect(page.locator('.gv1-deck-guide')).toBeVisible();

    await page.goto(`/scrying/${first}`);
    await expect(page.locator('[data-gv1-screen="scrying"]')).toBeVisible();
  });

  test('Scrying surfaces a desktop-suggested banner under 480px', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    const idx = await (await page.request.get('/data/index.json')).json();
    const first = idx.commanders[0].id as string;
    await page.goto(`/scrying/${first}`);
    await expect(page.locator('.gv1-scry-mobile-banner')).toBeVisible();

    await page.setViewportSize({ width: 1024, height: 800 });
    await page.goto(`/scrying/${first}`);
    await expect(page.locator('.gv1-scry-mobile-banner')).toBeHidden();
  });
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
  // The guide writes the last-viewed deck in an effect, after it first shows.
  // Wait for the write: a reload that lands between the two loses it.
  await expect
    .poll(() => page.evaluate(() => window.localStorage.getItem('grimoire-last-deck')))
    .toBe(second);

  await page.reload();
  await page.goto('/codex');
  await expect(page.getByRole('link', { name: /guide/i })).toHaveAttribute(
    'href',
    new RegExp(`/deck/${second}$`),
  );
});
