// DEC-1153: two follow-ups of the PR #54 review (DEC-1149) that a page shows.
//
// N4: the loader fetches card-metadata.meta.json only with card-metadata.json,
// and stores the file with its own date. A load from storage sends no request
// for either file.
//
// N5: bucket 1 of the limiter frees its lock only after the card cache has
// stored the answer. A tab whose turn comes while another tab's answer is out
// finds those names in storage, also when the answer takes longer than the
// 1,200 ms between starts. The fixture's rate check (support/test.ts) holds in
// both cases.
import { expect, test } from './support/test';

test('a deck guide sends 1 meta request cold, none after a reload, and none on the way to /shopping', async ({
  page,
  context,
}) => {
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
  await expect(page.locator('.gv1-shop-foot')).toContainText('Prices are USD from Scryfall, as of ');
  await page.waitForTimeout(1_000);

  expect({ meta, file }).toEqual({ meta: ['cold'], file: ['cold'] });
});

test('two tabs open /combos at once and each /cards/collection answer takes 1.5 s: each name goes out once', async ({
  context,
}) => {
  test.setTimeout(90_000);
  const batches: Array<{ at: number; names: string[] }> = [];
  const t0 = Date.now();
  context.on('request', (request) => {
    if (request.url() === 'https://api.scryfall.com/cards/collection' && request.method() === 'POST') {
      const body = JSON.parse(request.postData() ?? '{}') as { identifiers?: Array<{ name: string }> };
      batches.push({ at: Date.now() - t0, names: (body.identifiers ?? []).map((id) => id.name) });
    }
  });
  // This route comes before the stub's: it holds each answer, then the stub answers.
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
  const twice = [...perName].filter(([, count]) => count > 1).map(([name]) => name);
  test.info().annotations.push({
    type: 'batches',
    description: JSON.stringify(batches.map((batch) => ({ at: batch.at, n: batch.names.length }))),
  });
  expect(perName.size).toBeGreaterThan(5);
  expect(twice).toEqual([]);
});
