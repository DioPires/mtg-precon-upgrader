// The stub's options belong to one test: a test in the same worker after a
// seeded test does not get the seed (tests/support/test.ts, browser.newContext).
import { expect, test } from './support/test';

test.describe.configure({ mode: 'serial' });

const seededKeys = () => Object.keys(localStorage).filter((k) => k.startsWith('gv1-card:')).length;

test.describe('first test', () => {
  test.use({ cards: 'seeded' });
  test('seeded: the cache holds the seed', async ({ page }) => {
    await page.goto('/data/index.json');
    expect(await page.evaluate(seededKeys)).toBeGreaterThan(1500);
  });
});

test.describe('second test', () => {
  test('repo: the cache holds no seed of the test before it', async ({ page }) => {
    await page.goto('/data/index.json');
    expect(await page.evaluate(seededKeys)).toBe(0);
  });
});
