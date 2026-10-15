// DEC-1131: card lookups and price refreshes go in /cards/collection batches;
// /shopping refreshes prices older than 24 h and shows a line while a stop holds
// the refresh. The fixture's rate check (support/test.ts) holds in every case.
// No figure is written here: every count and date comes from the page and the
// repository's data files.
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { formatPricesDate } from '../src/lib/pricesDate';
import { normalizeName } from '../src/lib/spellbookMatch';
import { expect, test, type BrowserContext, type Page, type Request } from './support/test';

const DATA = resolve(dirname(fileURLToPath(import.meta.url)), '..', '..', 'data');
const read = (file: string) => JSON.parse(readFileSync(resolve(DATA, file), 'utf8'));
const FILE = read('card-metadata.json') as Record<string, { usd: number | null }>;
const USD = new Map(Object.entries(FILE).map(([name, entry]) => [name.toLowerCase(), entry.usd]));
const PRICES_AS_OF = (read('card-metadata.meta.json') as { prices_as_of: string }).prices_as_of;
const HOUR_MS = 3_600_000;
const STOP_KEY = 'grimoire-scryfall-stop';
const COLLECTION = 'https://api.scryfall.com/cards/collection';

/** A page clock at which every price of the file is older than 24 h, also on the day the file was made. */
const pricesAreOld = () => Math.max(Date.now(), Date.parse(PRICES_AS_OF) + 25 * HOUR_MS);

const front = (name: string) => name.split(' // ')[0].trim();
const usdText = (usd: number) => `$${usd.toFixed(2)}`;

/** The identifiers of a batch request. */
function identifiers(request: Request): string[] {
  const body = JSON.parse(request.postData() ?? '{}') as { identifiers?: Array<{ name: string }> };
  return (body.identifiers ?? []).map((id) => id.name);
}

/** The requests of one context to api.scryfall.com, by kind, as the browser sends them. */
function watch(context: BrowserContext) {
  const seen = {
    batches: [] as string[][],
    /** The real time of each batch's send. */
    batchTimes: [] as number[],
    autocomplete: [] as string[],
    other: [] as string[],
    methods: [] as string[],
  };
  context.on('request', (request) => {
    const url = new URL(request.url());
    if (url.hostname !== 'api.scryfall.com') return;
    seen.methods.push(`${request.method()} ${url.pathname}`);
    if (url.pathname === '/cards/collection' && request.method() === 'POST') {
      seen.batches.push(identifiers(request));
      seen.batchTimes.push(Date.now());
    }
    else if (url.pathname === '/cards/autocomplete') seen.autocomplete.push(url.searchParams.get('q') ?? '');
    else seen.other.push(`${request.method()} ${request.url()}`);
  });
  return seen;
}

// Runs in the page before the app: counts the app's fetches to api.scryfall.com,
// takes the first rows of /shopping as the first commit puts them in the page,
// and records each value of the estimate.
function recordShoppingPaint(): void {
  const w = window as unknown as Record<string, unknown>;
  w.__apiFetches = 0;
  w.__estimates = [] as string[];
  const send = window.fetch;
  window.fetch = function (input: RequestInfo | URL, init?: RequestInit) {
    const url = typeof input === 'string' ? input : input instanceof URL ? input.href : input.url;
    if (url.startsWith('https://api.scryfall.com/')) w.__apiFetches = (w.__apiFetches as number) + 1;
    return send.call(this, input, init);
  };
  new MutationObserver(() => {
    const rows = [...document.querySelectorAll('.gv1-shop-row')];
    if (rows.length === 0) return;
    const stat = [...document.querySelectorAll('.gv1-shop-stat')].find((s) => s.textContent?.includes('EST. COST'));
    const estimate = stat?.querySelector('.gv1-serif-xl')?.textContent ?? '';
    const estimates = w.__estimates as string[];
    if (estimates[estimates.length - 1] !== estimate) estimates.push(estimate);
    if (w.__firstRows) return;
    w.__firstRows = {
      apiFetches: w.__apiFetches,
      names: rows.map((r) => r.getAttribute('data-card-name') ?? ''),
      priced: rows.filter((r) => r.querySelector('.gv1-shop-row-price .gv1-rune')).map((r) => r.getAttribute('data-card-name')),
    };
  }).observe(document, { childList: true, subtree: true, characterData: true });
}

/** The rows of /shopping: name → the price that the row shows, or null. */
async function rowPrices(page: Page): Promise<Map<string, string | null>> {
  const rows = await page.locator('.gv1-shop-row').evaluateAll((els) =>
    els.map((el) => [el.getAttribute('data-card-name') ?? '', el.querySelector('.gv1-shop-row-price .gv1-rune')?.textContent ?? null] as const),
  );
  return new Map(rows);
}

test.describe('/shopping refreshes the prices older than 24 h', () => {
  test.use({ scryfallUsdBump: 1 });

  test("first paint shows the file's prices with no request; then the batches bring the new prices once; a reload inside 24 h sends nothing", async ({
    page,
    context,
  }) => {
    test.setTimeout(90_000);
    const seen = watch(context);
    await context.addInitScript(recordShoppingPaint);
    await page.clock.install({ time: pricesAreOld() });
    await page.goto('/shopping');
    await page.locator('.gv1-shop-row').first().waitFor();

    // The first rows: the file's prices, and no fetch to api.scryfall.com yet.
    const first = (await page.evaluate(() => (window as unknown as Record<string, unknown>).__firstRows)) as {
      apiFetches: number;
      names: string[];
      priced: string[];
    };
    expect(first.apiFetches).toBe(0);
    expect(first.names.length).toBeGreaterThan(50);
    expect(first.priced).toEqual(first.names.filter((name) => USD.get(name.toLowerCase()) != null));

    // One batch for each 75 front faces of the rows, in their turn.
    const fronts = new Set(first.names.map((name) => normalizeName(front(name))));
    const expectedBatches = Math.ceil(fronts.size / 75);
    expect(expectedBatches).toBeGreaterThanOrEqual(2);
    await expect.poll(() => seen.batches.length, { timeout: 30_000 }).toBe(expectedBatches);
    expect(seen.batches.map((b) => b.length)).toEqual(
      Array.from({ length: expectedBatches }, (_, i) => Math.min(75, fronts.size - 75 * i)),
    );
    expect(new Set(seen.batches.flat().map(normalizeName))).toEqual(fronts);
    // Bucket 1 starts a batch 1,200 ms or more after the last (ruling 5); the page's clock runs at real speed here.
    const gaps = seen.batchTimes.slice(1).map((t, i) => t - seen.batchTimes[i]);
    expect(Math.min(...gaps)).toBeGreaterThanOrEqual(1_100);

    // Each priced row shows the refreshed price: $1.00 more than the file's.
    await expect
      .poll(async () => {
        const prices = await rowPrices(page);
        return first.names.filter((name) => {
          const usd = USD.get(name.toLowerCase());
          return usd != null && prices.get(name) !== usdText(usd + 1);
        });
      })
      .toEqual([]);
    // The estimate changed once: the file's sum, then the refreshed sum.
    const estimates = (await page.evaluate(() => (window as unknown as Record<string, unknown>).__estimates)) as string[];
    expect(estimates).toHaveLength(2);
    // The footer gives the date of the refresh, the oldest date among the priced rows.
    const today = await page.evaluate(() => new Date().toISOString());
    await expect(page.locator('.gv1-shop-foot')).toContainText(`Prices are USD from Scryfall, as of ${formatPricesDate(today)}.`);
    expect(seen.other).toEqual([]);

    // A reload inside 24 h: the refreshed prices come from storage, and nothing goes.
    const sent = seen.batches.length;
    await page.reload();
    await page.locator('.gv1-shop-row').first().waitFor();
    await page.waitForTimeout(3_000);
    expect(seen.batches).toHaveLength(sent);
    const prices = await rowPrices(page);
    const priced = first.names.filter((name) => USD.get(name.toLowerCase()) != null);
    expect(priced.filter((name) => prices.get(name) !== usdText(USD.get(name.toLowerCase())! + 1))).toEqual([]);
  });
});

test.describe('/shopping while a stop holds the refresh', () => {
  test.use({ scryfall429From: 1, rateClock: 'page' });

  test('the stop line gives the date of the prices and the time of the next try; 0 requests in 30 s, then 1, and the line goes', async ({
    page,
    context,
  }) => {
    test.setTimeout(90_000);
    const seen = watch(context);
    // The spec holds the request that goes after the stop, so that the page
    // can be read while it is out; then the stub answers it.
    let release: () => void = () => undefined;
    const held = new Promise<void>((resolve) => {
      release = resolve;
    });
    let routed = 0;
    await page.route(COLLECTION, async (route) => {
      if (route.request().method() === 'POST' && ++routed === 2) await held;
      await route.fallback();
    });
    await page.clock.install({ time: pricesAreOld() });
    await page.goto('/shopping');
    await page.locator('.gv1-shop-row').first().waitFor();

    // Batch 1 meets the 429 with no CORS header: the fetch rejects and the stop starts.
    await page.waitForFunction((key) => localStorage.getItem(key) !== null, STOP_KEY, { timeout: 30_000 });
    const { until, ms } = await page.evaluate((key) => {
      const stop = JSON.parse(localStorage.getItem(key)!) as { until: number; ms: number };
      return stop;
    }, STOP_KEY);
    expect(ms).toBe(30_000);
    expect(seen.batches).toHaveLength(1);

    const line = page.getByRole('status').filter({ hasText: 'Price refresh paused' });
    const nextTry = (at: number) =>
      page.evaluate((t) => new Date(t).toLocaleTimeString('en-GB', { hour12: false }), at);
    await expect(line).toHaveText(
      `Price refresh paused. Prices shown are from ${formatPricesDate(PRICES_AS_OF)}. Next try at ${await nextTry(until)}.`,
    );

    // Hold the page's time, then move it to 1 ms before the end of the stop.
    const pausedAt = (await page.evaluate(() => Date.now())) + 1_000;
    expect(pausedAt).toBeLessThan(until - 1);
    await page.clock.pauseAt(pausedAt);
    await page.clock.fastForward(until - pausedAt - 1);
    await page.waitForTimeout(2_000);
    expect(seen.batches).toHaveLength(1);
    await expect(line).toHaveCount(1);

    // The stop ends: one request goes, the same batch. The line goes while it is out.
    await page.clock.fastForward(2);
    await expect.poll(() => seen.batches.length, { timeout: 10_000 }).toBe(2);
    expect(seen.batches[1]).toEqual(seen.batches[0]);
    await expect(line).toHaveCount(0);
    await page.waitForTimeout(1_000);
    expect(seen.batches).toHaveLength(2);

    // The stub answers it with a 429 too: the stop doubles, and the line comes back.
    release();
    await expect
      .poll(() => page.evaluate((key) => (JSON.parse(localStorage.getItem(key) ?? '{}') as { ms?: number }).ms, STOP_KEY))
      .toBe(60_000);
    const doubled = await page.evaluate((key) => (JSON.parse(localStorage.getItem(key)!) as { until: number }).until, STOP_KEY);
    await expect(line).toContainText(`Next try at ${await nextTry(doubled)}.`);
  });
});

test('/combos at load sends one batch, and each art settles: the picture of a file name, the glyph of a name Scryfall lacks', async ({
  page,
  context,
}) => {
  test.setTimeout(60_000);
  const seen = watch(context);
  await page.clock.install();
  await page.goto('/combos');
  await page.locator('.gv1-lab-art').first().waitFor();
  await expect(page.locator('.gv1-lab-skeleton')).toHaveCount(0, { timeout: 30_000 });
  await page.waitForTimeout(2_000);

  const arts = await page.locator('.gv1-lab-art').evaluateAll((els) =>
    els.map((el) => ({
      name: el.getAttribute('data-card-name') ?? '',
      src: el.querySelector('img')?.getAttribute('src') ?? null,
      glyph: !!el.querySelector('.gv1-lab-art-fallback'),
    })),
  );
  const outside = [...new Set(arts.map((a) => a.name).filter((name) => !USD.has(name.toLowerCase())))];
  expect(outside.length).toBeGreaterThan(1);
  expect(seen.batches).toHaveLength(1);
  expect(new Set(seen.batches[0].map(normalizeName))).toEqual(new Set(outside.map((name) => normalizeName(front(name)))));
  for (const art of arts) {
    if (USD.has(art.name.toLowerCase())) expect(art.src, art.name).toMatch(/^https:\/\/cards\.scryfall\.io\/small\//);
    // The stub knows only the file's names: Scryfall's not_found shows the glyph.
    else expect(art.glyph, art.name).toBe(true);
  }
  expect(seen.other).toEqual([]);

  // A name in not_found gets no other request for 24 h, also after a reload a minute later.
  await page.clock.fastForward(60_000);
  await page.reload();
  await page.locator('.gv1-lab-art').first().waitFor();
  await expect(page.locator('.gv1-lab-skeleton')).toHaveCount(0, { timeout: 30_000 });
  await page.waitForTimeout(2_000);
  expect(seen.batches).toHaveLength(1);
});

test.describe('a batch with no answer', () => {
  test.use({ rateClock: 'page' });

  test('is aborted after 20 s; the stop starts, and after it the same batch goes (N3)', async ({ page, context }) => {
    test.setTimeout(60_000);
    const seen = watch(context);
    let release: () => void = () => undefined;
    const never = new Promise<void>((resolve) => {
      release = resolve;
    });
    let posts = 0;
    await page.route(COLLECTION, async (route) => {
      if (route.request().method() === 'POST' && ++posts === 1) {
        await never;
        return route.fallback().catch(() => undefined);
      }
      return route.fallback();
    });
    await page.clock.install();
    await page.goto('/combos');
    await expect.poll(() => seen.batches.length).toBe(1);
    const pausedAt = (await page.evaluate(() => Date.now())) + 1_000;
    await page.clock.pauseAt(pausedAt);
    expect(await page.evaluate((key) => localStorage.getItem(key), STOP_KEY)).toBeNull();

    // 20 s with no answer: the app aborts the request, and that counts as a failure.
    await page.clock.fastForward(20_000);
    await expect
      .poll(() => page.evaluate((key) => (JSON.parse(localStorage.getItem(key) ?? '{}') as { ms?: number }).ms, STOP_KEY))
      .toBe(30_000);
    expect(seen.batches).toHaveLength(1);

    // After the stop the same batch goes, and the stub answers it.
    await page.clock.fastForward(30_000);
    await expect.poll(() => seen.batches.length).toBe(2);
    expect(seen.batches[1]).toEqual(seen.batches[0]);
    await expect(page.locator('.gv1-lab-skeleton')).toHaveCount(0, { timeout: 10_000 });
    await expect
      .poll(() => page.evaluate((key) => localStorage.getItem(key), STOP_KEY))
      .toBeNull();
    release();
  });
});

test.describe('an old stop record', () => {
  test.use({ scryfall429From: 1 });

  test('a record that ended 400 s ago counts as none: the next failure stops for 30 s (N4)', async ({ page }) => {
    await page.goto('/data/index.json');
    await page.evaluate((key) => {
      localStorage.setItem(key, JSON.stringify({ until: Date.now() - 400_000, ms: 300_000, n: 7 }));
    }, STOP_KEY);
    await page.goto('/combos');
    await page.waitForFunction(
      (key) => (JSON.parse(localStorage.getItem(key) ?? '{}') as { n?: number }).n !== 7,
      STOP_KEY,
      { timeout: 20_000 },
    );
    const stop = await page.evaluate((key) => JSON.parse(localStorage.getItem(key)!) as { ms: number }, STOP_KEY);
    expect(stop.ms).toBe(30_000);
  });
});

test.describe('a stop that lives in memory', () => {
  test.use({ scryfall429From: 1, rateClock: 'page' });

  test('when storage refuses the stop and the clock goes back 10 h, the next batch goes about one stop later (delta N1)', async ({
    page,
    context,
  }) => {
    test.setTimeout(60_000);
    const seen = watch(context);
    const failed: string[] = [];
    context.on('requestfailed', (request) => {
      if (request.url() === COLLECTION && request.method() === 'POST') failed.push(request.failure()?.errorText ?? '');
    });
    await context.addInitScript((key) => {
      const setItem = Storage.prototype.setItem;
      Storage.prototype.setItem = function (k: string, v: string) {
        if (k === key) throw new DOMException('full', 'QuotaExceededError');
        return setItem.call(this, k, v);
      };
    }, STOP_KEY);
    await page.clock.install();
    await page.goto('/combos');
    // The batch meets the 429; the stop lives in memory.
    await expect.poll(() => failed.length).toBe(1);
    const now = await page.evaluate(() => Date.now());
    await page.clock.pauseAt(now + 1_000);
    await page.clock.setSystemTime(now + 1_000 - 10 * HOUR_MS);
    await page.clock.fastForward(29_000);
    expect(seen.batches).toHaveLength(1);
    // The stop reads now + its length after the jump: a batch goes inside two lengths, not 10 h later.
    // runFor() fires the timers that come due on the way, as the limiter's waits do.
    await page.clock.runFor(35_000);
    await expect.poll(() => seen.batches.length, { timeout: 10_000 }).toBe(2);
  });
});

test('a card-metadata.json that fails is not kept: the next load asks for it again (N6)', async ({ page }) => {
  test.setTimeout(60_000);
  let fail = true;
  let asked = 0;
  await page.route('**/data/card-metadata.json', (route) => {
    asked += 1;
    return fail ? route.fulfill({ status: 404, body: 'not found' }) : route.fallback();
  });
  await page.goto('/deck/creeping-corruption');
  await page.locator('.gv1-card-tile').first().waitFor();
  expect(asked).toBe(1);
  const kept = () =>
    page.evaluate(() => Object.keys(localStorage).filter((key) => key.endsWith(':card-metadata')));
  expect(await kept()).toEqual([]);

  fail = false;
  await page.reload();
  await page.locator('.gv1-card-tile').first().waitFor();
  expect(asked).toBe(2);
  await expect.poll(kept).toHaveLength(1);
});

test('a deck guide: only the tiles with no highlight price ask for a refresh, and a reload inside 24 h sends nothing', async ({
  page,
  context,
}) => {
  test.setTimeout(60_000);
  // A deck whose highlights give a price to some tiles and not to others.
  const id = 'eternal-harvest';
  const highlights = (read(`commanders/${id}/deck.json`) as { highlights?: Array<{ name: string; price?: string }> }).highlights ?? [];
  const highlightPriced = new Set(highlights.filter((h) => h.price && h.price !== '—').map((h) => h.name.toLowerCase()));
  const seen = watch(context);
  await page.clock.install({ time: pricesAreOld() });
  await page.goto(`/deck/${id}`);
  await page.locator('.gv1-card-tile').first().waitFor();
  await page.waitForTimeout(3_000);

  const tiles = [...new Set(await page.locator('.gv1-card-tile').evaluateAll((els) => els.map((el) => el.getAttribute('data-card-name') ?? '')))];
  const priced = tiles.filter((name) => highlightPriced.has(name.toLowerCase()));
  const unpriced = tiles.filter((name) => !highlightPriced.has(name.toLowerCase()) && USD.has(name.toLowerCase()));
  expect(priced.length).toBeGreaterThan(0);
  expect(unpriced.length).toBeGreaterThan(0);
  const asked = new Set(seen.batches.flat().map(normalizeName));
  expect(priced.filter((name) => asked.has(normalizeName(front(name))))).toEqual([]);
  expect(unpriced.filter((name) => !asked.has(normalizeName(front(name))))).toEqual([]);

  const sent = seen.batches.length;
  await page.reload();
  await page.locator('.gv1-card-tile').first().waitFor();
  await page.waitForTimeout(3_000);
  expect(seen.batches).toHaveLength(sent);
});

test('the Atlas sends no autocomplete while a stop holds, and keeps its own suggestions (N5)', async ({ page, context }) => {
  const seen = watch(context);
  await page.clock.install();
  await page.goto('/atlas');
  const input = page.locator('#gv1-atlas-input');
  await input.waitFor();
  await page.evaluate((key) => {
    localStorage.setItem(key, JSON.stringify({ until: Date.now() + 60_000, ms: 60_000, n: 1 }));
  }, STOP_KEY);
  await input.fill('sol r');
  await expect(page.locator('#gv1-atlas-suggestions')).toContainText('Sol Ring');
  await page.waitForTimeout(1_500);
  expect(seen.autocomplete).toEqual([]);
  // Nothing waits for the end of the stop either: the request was never queued.
  await page.clock.fastForward(61_000);
  await page.waitForTimeout(1_000);
  expect(seen.autocomplete).toEqual([]);

  // When the stop has gone, the same input asks Scryfall.
  await page.evaluate((key) => localStorage.removeItem(key), STOP_KEY);
  await input.fill('sol ri');
  await expect.poll(() => seen.autocomplete).toEqual(['sol ri']);
});

// The rate check counts a POST in both clocks (H7 and N2 of the PR #38 review).
test.describe("the rate check, the page's clock, with batches (H7)", () => {
  test.use({ rateClock: 'page' });

  test("three batches in one second of the page's clock fail the test", async ({ page }) => {
    test.fail();
    await page.clock.install();
    await page.goto('/data/index.json');
    await page.clock.pauseAt(Date.now() + 10_000);
    for (let i = 0; i < 3; i += 1) {
      await page.evaluate(
        (url) =>
          void fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ identifiers: [{ name: 'Sol Ring' }] }),
          }).catch(() => undefined),
        COLLECTION,
      );
      await page.clock.fastForward(400);
    }
    await page.waitForTimeout(1_000);
  });
});

test.describe('the rate check, real clock, with a held answer (N2)', () => {
  test('three batches sent at once fail the test, also when the spec releases them 1.2 s apart', async ({ page }) => {
    test.fail();
    test.setTimeout(30_000);
    let n = 0;
    await page.route(COLLECTION, async (route) => {
      const wait = 1_200 * n;
      n += 1;
      await new Promise((r) => setTimeout(r, wait));
      await route.fallback();
    });
    await page.goto('/data/index.json');
    await page.evaluate((url) =>
      Promise.all(
        [0, 1, 2].map(() =>
          fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ identifiers: [{ name: 'Sol Ring' }] }),
          }).then((r) => r.status),
        ),
      ),
    COLLECTION);
  });
});

// A reading for the hand-back: does a route or the `request` event see Chromium's CORS preflight?
test("reading: the preflight of a batch, as Playwright's route and request event see it", async ({ page, context }, testInfo) => {
  const events: string[] = [];
  const routed: string[] = [];
  context.on('request', (request) => {
    if (new URL(request.url()).hostname === 'api.scryfall.com') events.push(request.method());
  });
  await page.route('https://api.scryfall.com/**', async (route) => {
    routed.push(route.request().method());
    await route.fallback();
  });
  await page.goto('/data/index.json');
  const status = await page.evaluate(
    (url) =>
      fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ identifiers: [{ name: 'Sol Ring' }] }),
      }).then((r) => r.status),
    COLLECTION,
  );
  expect(status).toBe(200);
  await testInfo.attach('preflight', { contentType: 'application/json', body: JSON.stringify({ events, routed }) });
  console.log(`preflight reading: request events ${JSON.stringify(events)}, route ${JSON.stringify(routed)}`);
  expect(events).toContain('POST');
  expect(routed).toContain('POST');
});
