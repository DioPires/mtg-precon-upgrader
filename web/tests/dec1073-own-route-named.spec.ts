// A request that a spec's own route answers fails its test (DEC-1073 item 3).
// The page reads only the status, and the test ends at once. The stub's check
// listens for `response`, so it still names the request: test.fail() expects that.
import { expect, test } from './support/test';

test('an own route answer whose body the page never reads is named', async ({ page }) => {
  test.fail();
  await page.goto('/');
  await page.route('https://api.scryfall.com/**', (route) =>
    route.fulfill({
      status: 429,
      headers: { 'access-control-allow-origin': '*' },
      body: 'x'.repeat(8 * 1024 * 1024),
    }),
  );
  const status = await page.evaluate(() =>
    fetch('https://api.scryfall.com/cards/named?fuzzy=Sol%20Ring').then((r) => r.status),
  );
  expect(status).toBe(429);
});
