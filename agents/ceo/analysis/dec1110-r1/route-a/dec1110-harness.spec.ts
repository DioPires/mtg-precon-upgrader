// DEC-1110 reviewer's kill cases for the e2e harness (web/tests/support/test.ts).
// The page sends bucket 1 requests itself, around the app's limiter, so the
// fixture's rate check must fail the test. test.fail() expects that failure:
// on the head these cases pass, and on a mutant that blinds the check they fail.
// The stub answers every request; nothing reaches the live API.
import { expect, test } from './support/test';

const LOOKUP = 'https://api.scryfall.com/cards/named?fuzzy=Sol%20Ring';

test.describe('the rate check, real clock', () => {
  test('three lookups at once fail the test', async ({ page }) => {
    test.fail();
    await page.goto('/data/index.json');
    await page.evaluate((url) => Promise.all([0, 1, 2].map(() => fetch(url).then((r) => r.status))), LOOKUP);
  });

  test('two lookups at once pass', async ({ page }) => {
    await page.goto('/data/index.json');
    await page.evaluate((url) => Promise.all([0, 1].map(() => fetch(url).then((r) => r.status))), LOOKUP);
  });
});

test.describe("the rate check, the page's clock", () => {
  test.use({ rateClock: 'page' });

  test("three lookups in one second of the page's clock fail the test", async ({ page }) => {
    test.fail();
    await page.clock.install();
    await page.goto('/data/index.json');
    await page.clock.pauseAt(Date.now() + 10_000);
    for (let i = 0; i < 3; i += 1) {
      await page.evaluate((url) => void fetch(url).catch(() => undefined), LOOKUP);
      await page.clock.fastForward(400);
    }
    await page.waitForTimeout(1_000);
  });

  test("three lookups 500 ms apart of the page's clock pass: the window is half-open", async ({ page }) => {
    await page.clock.install();
    await page.goto('/data/index.json');
    await page.clock.pauseAt(Date.now() + 10_000);
    for (let i = 0; i < 3; i += 1) {
      await page.evaluate((url) => void fetch(url).catch(() => undefined), LOOKUP);
      // Real time passes between the sends; the page's clock moves 500 ms only.
      await page.waitForTimeout(400);
      if (i < 2) await page.clock.fastForward(500);
    }
    await page.waitForTimeout(1_000);
  });
});

test.describe("cards: 'none'", () => {
  test.use({ cards: 'none' });

  test('/shopping shows its rows with no price', async ({ page }) => {
    await page.goto('/shopping');
    await page.locator('.gv1-shop-row').first().waitFor();
    await page.waitForLoadState('networkidle');
    const rows = await page.locator('.gv1-shop-row').count();
    expect(rows).toBeGreaterThan(50);
    await expect(page.locator('.gv1-shop-row .gv1-shop-row-price .gv1-rune')).toHaveCount(0);
  });
});
