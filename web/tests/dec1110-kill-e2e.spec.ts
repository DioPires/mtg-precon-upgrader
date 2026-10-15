// DEC-1110 reviewer's e2e kill case. It passes on 58ca0b3 and fails on the mutant in its title.
// The spec's own route cancels the small pictures with route.abort('aborted'), which the stub's
// check does not name (web/README.md). The stub answers every lookup.
import { expect, test } from './support/test';

test('A1: on /combos, a small picture from the file that fails sends one lookup for that card', async ({ page, context }) => {
  test.setTimeout(90_000);
  const lookups: string[] = [];
  context.on('request', (req) => {
    const u = new URL(req.url());
    if (u.hostname === 'api.scryfall.com' && u.pathname === '/cards/named') lookups.push(u.searchParams.get('fuzzy') ?? '');
  });
  await context.route('https://cards.scryfall.io/small/**', (route) => route.abort('aborted'));
  await page.goto('/combos');
  await page.locator('.gv1-lab-art').first().waitFor();
  // The pictures load lazily: scroll through the page so that each one starts.
  const height = await page.evaluate(() => document.documentElement.scrollHeight);
  for (let y = 0; y <= height; y += 400) {
    await page.evaluate((top) => window.scrollTo(0, top), y);
    await page.waitForTimeout(150);
  }
  const arts = await page.locator('.gv1-lab-art').evaluateAll((els) =>
    els.map((el) => `${el.getAttribute('data-card-name')}:${el.querySelector('img') ? 'img' : 'none'}`),
  );
  console.log(`A1 arts: ${arts.join(', ')}`);
  // Four cards of the first deck's combos are in card-metadata.json (the hand-back names them).
  const seeded = ['Academy Manufactor', 'Panharmonicon', 'Roaming Throne', 'Ancient Stone Idol'];
  await expect
    .poll(() => seeded.filter((name) => lookups.includes(name)), { timeout: 60_000 })
    .toEqual(seeded);
  await page.waitForTimeout(2_000);
  for (const name of seeded) expect(lookups.filter((n) => n === name)).toHaveLength(1);
});
