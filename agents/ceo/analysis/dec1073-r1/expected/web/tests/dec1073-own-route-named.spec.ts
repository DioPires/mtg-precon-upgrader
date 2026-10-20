// Review kill case (DEC-1087) for test.ts:141 (the check listens for `response`).
// The spec's own route answers with a body that the page never reads; the page
// reads only the status, and the test ends. The stub's check must name the
// request, so this test is expected to fail (test.fail): it passes on the head.
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
