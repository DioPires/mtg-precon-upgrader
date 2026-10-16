// DEC-1170 scratch cases (reviewer of PR #70). Not a file of the pull request.
// R3: the meta case of dec1153-card-data-followups.spec.ts, with `meta` and `file` in an annotation.
// R4: /shopping when /data/card-metadata.json answers 500: the date text of the footer.
// R5: the two-tab case of dec1153-card-data-followups.spec.ts, with the names of each batch in an annotation.
import { expect, test } from './support/test';

test('R3 meta request: the meta and file requests by phase', async ({ page, context }) => {
  const meta: string[] = [];
  const file: string[] = [];
  let phase = 'cold';
  context.on('request', (request) => {
    const path = new URL(request.url()).pathname;
    if (path === '/data/card-metadata.meta.json') meta.push(phase);
    if (path === '/data/card-metadata.json') file.push(phase);
  });
  await page.goto('/deck/creeping-corruption');
  await page.locator('.gv1-card-tile').first().waitFor();
  await page.waitForTimeout(1_000);
  phase = 'reload';
  await page.reload();
  await page.locator('.gv1-card-tile').first().waitFor();
  await page.waitForTimeout(1_000);
  phase = 'spa-nav';
  await page.locator('a[href="/shopping"]').first().click();
  await expect(page).toHaveURL(/\/shopping$/);
  await expect(page.locator('.gv1-shop-foot')).toContainText('Prices are USD from Scryfall');
  await page.waitForTimeout(1_000);
  test.info().annotations.push({ type: 'meta', description: JSON.stringify({ meta, file }) });
});

for (const status of [500, 404]) {
  test(`R4 failed file: /shopping when card-metadata.json answers ${status}`, async ({ page, context }) => {
    const seen: string[] = [];
    context.on('request', (request) => {
      const path = new URL(request.url()).pathname;
      if (path.startsWith('/data/card-metadata')) seen.push(path);
    });
    await context.route('**/data/card-metadata.json', (route) => route.fulfill({ status, body: 'error' }));
    await page.goto('/shopping');
    await page.locator('[role="alert"], .gv1-shop-foot').first().waitFor();
    await page.waitForTimeout(4_000);
    const alert = (await page.locator('[role="alert"]').allInnerTexts()).map((t) => t.replace(/\s+/g, ' ').trim());
    const foot = (await page.locator('.gv1-shop-foot').allInnerTexts()).map((t) => t.replace(/\s+/g, ' ').trim());
    const dateLine = foot.join(' ').match(/Prices are USD from Scryfall[^.]*\.(?:[^.]*\d{4}\.)?/)?.[0] ?? null;
    test.info().annotations.push({ type: 'date', description: JSON.stringify({ status, dateLine, alert, foot: foot.map((t) => t.slice(0, 300)), seen }) });
    await page.screenshot({ path: test.info().outputPath(`shopping-${status}.png`) });
  });
}

test('R5 two tabs: the names of each /cards/collection batch', async ({ context }) => {
  test.setTimeout(90_000);
  const batches: Array<{ at: number; names: string[] }> = [];
  const t0 = Date.now();
  context.on('request', (request) => {
    if (request.url() === 'https://api.scryfall.com/cards/collection' && request.method() === 'POST') {
      const body = JSON.parse(request.postData() ?? '{}') as { identifiers?: Array<{ name: string }> };
      batches.push({ at: Date.now() - t0, names: (body.identifiers ?? []).map((id) => id.name) });
    }
  });
  await context.route('https://api.scryfall.com/cards/collection', async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 1_500));
    await route.fallback();
  });
  const tabs = await Promise.all([context.newPage(), context.newPage()]);
  await Promise.all(tabs.map((tab) => tab.goto('/combos')));
  for (const tab of tabs) {
    await tab.locator('.gv1-lab-art').first().waitFor();
    await expect(tab.locator('.gv1-lab-skeleton')).toHaveCount(0, { timeout: 60_000 });
  }
  await tabs[0].waitForTimeout(2_000);
  const perName = new Map<string, number>();
  batches.flatMap((batch) => batch.names).forEach((name) => perName.set(name, (perName.get(name) ?? 0) + 1));
  test.info().annotations.push({ type: 'names', description: JSON.stringify(batches) });
  expect([...perName].filter(([, count]) => count > 1).map(([name]) => name)).toEqual([]);
});
