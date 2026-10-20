// Review kill case (DEC-1087) for test.ts:153 (`browser.newContext = newContext`).
// Serial mode keeps both tests in one worker and one browser. The second test
// must not get the stub options of the test before it.
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
