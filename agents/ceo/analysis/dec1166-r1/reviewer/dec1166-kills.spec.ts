// DEC-1166 reviewer's kill cases for PR #64 (web/tests/support/test.ts). A
// case below kills a mutant that the four specs of the implementer's runner
// leave alive. test.fail() expects the rate check's failure, as in the H7 case
// of dec1131-card-batches.spec.ts. The stub answers every request; nothing
// reaches the live API.
import { test } from './support/test';

const COLLECTION = 'https://api.scryfall.com/cards/collection';
const AUTOCOMPLETE = 'https://api.scryfall.com/cards/autocomplete?q=sol';
const GAP_MS = 600;

test.describe('the rate check, real clock: only /cards/named and /cards/collection count', () => {
  // S4: the real clock stamps every /cards/ request. Scryfall allows 10 a second
  // on /cards/autocomplete, and the app spaces them 120 ms apart, so three at
  // once must pass.
  test('three autocompletes at once pass', async ({ page }) => {
    await page.goto('/data/index.json');
    await page.evaluate(
      (url) => Promise.all([0, 1, 2].map(() => fetch(url).then((r) => r.status))),
      AUTOCOMPLETE,
    );
  });
});

test.describe("the rate check, the page's clock: fetch(request, init) sends init's method", () => {
  test.use({ rateClock: 'page' });

  // R1: the page reads the Request's method (GET) in place of init's (POST),
  // so the two batches start 2 requests, not 4, and the check stays silent.
  test("two batches 600 ms apart, as fetch(new Request(url), { method: 'POST' }), fail the test", async ({ page }) => {
    test.fail();
    await page.clock.install();
    await page.goto('/data/index.json');
    await page.clock.pauseAt(Date.now() + 10_000);
    for (let i = 0; i < 2; i += 1) {
      await page.evaluate(
        (url) =>
          void fetch(new Request(url), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ identifiers: [{ name: 'Sol Ring' }] }),
          }).catch(() => undefined),
        COLLECTION,
      );
      if (i === 0) await page.clock.fastForward(GAP_MS);
    }
    await page.waitForTimeout(1_000);
  });
});
