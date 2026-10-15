// DEC-1152 (DEC-1149 N3): the rate check counts each POST to /cards/collection
// twice, for the CORS preflight that the browser sends before it, in both
// clocks. Two batches 600 ms apart start 4 requests in 1 s, so the check must
// fail the test: test.fail() expects that failure, as in the H7 case of
// dec1131-card-batches.spec.ts. The last two cases read the error that the
// fixture throws. The stub answers every request; nothing reaches the live API.
import {
  expect,
  peakPerWindow,
  rateCheckFailure,
  startTimes,
  test,
  type Page,
  type TestInfo,
} from './support/test';

const COLLECTION = 'https://api.scryfall.com/cards/collection';
const LOOKUP = 'https://api.scryfall.com/cards/named?fuzzy=Sol%20Ring';
const GAP_MS = 600;

test.describe('the rate check, real clock: a POST counts twice', () => {
  test('two batches 600 ms apart fail the test', async ({ page }) => {
    test.fail();
    await page.goto('/data/index.json');
    for (let i = 0; i < 2; i += 1) {
      await page.evaluate(
        (url) =>
          void fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ identifiers: [{ name: 'Sol Ring' }] }),
          }).catch(() => undefined),
        COLLECTION,
      );
      if (i === 0) await page.waitForTimeout(GAP_MS);
    }
    await page.waitForTimeout(1_000);
  });
});

test.describe("the rate check, the page's clock: a POST counts twice", () => {
  test.use({ rateClock: 'page' });

  // The page reads the method of each form of a fetch call.
  for (const form of ['fetch(url, init)', 'fetch(request)', "fetch(url, init), method 'post'"] as const) {
    test(`two batches 600 ms apart of the page's clock fail the test: ${form}`, async ({ page }) => {
      test.fail();
      await page.clock.install();
      await page.goto('/data/index.json');
      await page.clock.pauseAt(Date.now() + 10_000);
      for (let i = 0; i < 2; i += 1) {
        await page.evaluate(
          ([url, form]) => {
            const init = {
              method: form.endsWith("'post'") ? 'post' : 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ identifiers: [{ name: 'Sol Ring' }] }),
            };
            const sent = form === 'fetch(request)' ? fetch(new Request(url, init)) : fetch(url, init);
            void sent.catch(() => undefined);
          },
          [COLLECTION, form] as const,
        );
        if (i === 0) await page.clock.fastForward(GAP_MS);
      }
      await page.waitForTimeout(1_000);
    });
  }
});

test('the error says that a POST counts twice, and lists each send with its method', () => {
  // The sends keep the order of their stamps; a spec can move the page's clock back.
  const sends = [
    { method: 'POST', time: 5_250 },
    { method: 'GET', time: 5_000 },
    { method: 'POST', time: 5_850 },
  ];
  expect(peakPerWindow(startTimes(sends))).toBe(5);
  expect(rateCheckFailure(sends, 5, 'real')).toBe(
    'One browser context started 5 requests to /cards/named and /cards/collection in 1 s; Scryfall allows 2.\n' +
      '  A POST counts twice: the browser sends a CORS preflight (OPTIONS) before it, and the check cannot see that one.\n' +
      '  Sends (method, ms after the first, real time): POST 250, GET 0, POST 850\n' +
      'Every request to api.scryfall.com goes through src/data/scryfallLimiter.ts (web/README.md, "Scryfall requests").',
  );
  expect(rateCheckFailure(sends, 5, 'page')).toContain("Sends (method, ms after the first, the page's clock): POST 250,");
});

// The fixture throws the rate check's error when it ends, after the test body,
// so a case cannot catch it. This rateClock fixture ends after the stub's
// fixture, which depends on it, and reads the error there. It marks the test as
// expected to fail only when that error is `expected` and nothing else; any
// other end fails the test.
const readRateCheck =
  (expected: string) =>
  // Playwright reads a fixture's dependencies from the pattern; this one has none.
  // eslint-disable-next-line no-empty-pattern
  async ({}, use: (clock: 'page') => Promise<void>, testInfo: TestInfo) => {
    await use('page');
    const errors = testInfo.errors.map((error) => error.message);
    if (errors.length !== 1 || errors[0] !== `Error: ${expected}`) {
      throw new Error(`The test did not end with the rate check's error alone:\n${errors.join('\n') || '(no error)'}`);
    }
    testInfo.fail();
  };

// Two batches GAP_MS apart of the page's clock.
async function sendTwoBatches(page: Page): Promise<void> {
  await page.clock.install();
  await page.goto('/data/index.json');
  await page.clock.pauseAt(Date.now() + 10_000);
  for (let i = 0; i < 2; i += 1) {
    await page.evaluate(
      (url) =>
        void fetch(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ identifiers: [{ name: 'Sol Ring' }] }),
        }).catch(() => undefined),
      COLLECTION,
    );
    if (i === 0) await page.clock.fastForward(GAP_MS);
  }
  await page.waitForTimeout(1_000);
}

test.describe("the rate check's error, as the fixture throws it", () => {
  const sends = [
    { method: 'POST', time: 0 },
    { method: 'POST', time: GAP_MS },
  ];
  test.use({ rateClock: readRateCheck(rateCheckFailure(sends, 4, 'page')) });

  test("names the page's clock", async ({ page }) => {
    await sendTwoBatches(page);
  });

  test('lists the sends of the context with the highest peak, not of the first one', async ({ browser, page }) => {
    // The test's own context stamps first: one GET, a peak of 1.
    await page.goto('/data/index.json');
    await page.evaluate((url) => fetch(url).then((response) => response.status), LOOKUP);
    const other = await browser.newContext();
    await sendTwoBatches(await other.newPage());
    await other.close();
  });
});
