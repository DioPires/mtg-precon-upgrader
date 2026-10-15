// DEC-1102: deck cards come from data/card-metadata.json, and one limiter holds
// every request to api.scryfall.com. The fixture's rate check (support/test.ts)
// holds in every case here too.
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { formatPricesDate } from '../src/lib/pricesDate';
import { expect, test, type BrowserContext, type Locator, type Page } from './support/test';

const DATA = resolve(dirname(fileURLToPath(import.meta.url)), '..', '..', 'data');
const FILE = JSON.parse(readFileSync(resolve(DATA, 'card-metadata.json'), 'utf8')) as Record<
  string,
  { usd: number | null; mana_cost: string }
>;
const USD = new Map(Object.entries(FILE).map(([name, entry]) => [name.toLowerCase(), entry.usd]));
const PRICES_AS_OF = (
  JSON.parse(readFileSync(resolve(DATA, 'card-metadata.meta.json'), 'utf8')) as { prices_as_of: string }
).prices_as_of;

/** The requests of one context that matter here, by kind. */
function watch(context: BrowserContext) {
  const seen = { api: [] as string[], lookups: [] as string[], imageHost: [] as string[], localImages: [] as string[] };
  context.on('request', (request) => {
    const url = new URL(request.url());
    if (url.hostname === 'api.scryfall.com') {
      seen.api.push(request.url());
      if (/^\/cards\/(named|collection)$/.test(url.pathname)) seen.lookups.push(request.url());
    } else if (url.hostname === 'cards.scryfall.io') {
      seen.imageHost.push(request.url());
    } else if (url.pathname.startsWith('/data/images/cards/')) {
      seen.localImages.push(request.url());
    }
  });
  return seen;
}

async function scrollToEnd(page: Page) {
  const height = await page.evaluate(() => document.documentElement.scrollHeight);
  for (let y = 0; y <= height; y += 600) {
    await page.evaluate((top) => window.scrollTo(0, top), y);
    await page.waitForTimeout(100);
  }
}

/**
 * Opens the hover frame of one name. Any scroll closes the frame, so the
 * pointer comes only after the scroll has ended. hover() would scroll again, so
 * the pointer moves to the box itself. It leaves first: a pointer that does not
 * move fires no mouseover.
 */
async function hoverName(page: Page, name: Locator) {
  await page.mouse.move(0, 0);
  await name.scrollIntoViewIfNeeded();
  await page.waitForTimeout(250);
  const box = (await name.boundingBox())!;
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2, { steps: 5 });
  await expect(page.locator('.gv1-cardhover')).toBeVisible();
}

test('a scroll to the end of a deck guide sends nothing to api.scryfall.com or /data/images/cards/', async ({
  page,
  context,
}) => {
  const seen = watch(context);
  await page.goto('/deck/creeping-corruption');
  await page.locator('.gv1-card-tile').first().waitFor();
  await scrollToEnd(page);
  await page.waitForLoadState('networkidle');

  // Every tile has its picture address from the file at once.
  const tiles = await page.locator('.gv1-card-tile').count();
  expect(tiles).toBeGreaterThan(30);
  await expect(page.locator('.gv1-card-tile img.gv1-card-tile-img')).toHaveCount(tiles);
  expect(seen.imageHost.length).toBeGreaterThan(0);
  expect(seen.api).toEqual([]);
  expect(seen.localImages).toEqual([]);
});

test('/shopping shows its priced count at first paint, with no request to api.scryfall.com', async ({
  page,
  context,
}) => {
  const seen = watch(context);
  await page.goto('/shopping');
  // The rows and the summary in one task: the first paint that holds rows.
  const first = await page
    .waitForFunction(() => {
      const rows = [...document.querySelectorAll('.gv1-shop-row')];
      if (rows.length === 0) return null;
      const cost = [...document.querySelectorAll('.gv1-shop-stat')].find((s) => s.textContent?.includes('EST. COST'));
      return {
        names: rows.map((r) => r.getAttribute('data-card-name') ?? ''),
        priced: rows.filter((r) => r.querySelector('.gv1-shop-row-price .gv1-rune')).map((r) => r.getAttribute('data-card-name')),
        summary: cost?.lastElementChild?.textContent ?? '',
      };
    })
    .then((handle) => handle.jsonValue());

  const expected = first!.names.filter((name) => USD.get(name.toLowerCase()) != null);
  expect(first!.names.length).toBeGreaterThan(50);
  expect(first!.priced).toEqual(expected);
  expect(first!.summary).toBe(
    expected.length < first!.names.length ? `${expected.length}/${first!.names.length} priced` : 'all priced',
  );
  await expect(page.locator('.gv1-shop-foot')).toContainText(
    `Prices are USD from Scryfall, as of ${formatPricesDate(PRICES_AS_OF)}.`,
  );

  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(1_000);
  expect(seen.api).toEqual([]);
});

test("/shopping shows the front half's cost of a two-part card from the file", async ({ page, context }) => {
  const seen = watch(context);
  const joined = new Map(
    Object.entries(FILE)
      .filter(([, entry]) => entry.mana_cost.includes(' // '))
      .map(([name, entry]) => [name.toLowerCase(), entry.mana_cost]),
  );
  await page.goto('/shopping');
  await page.locator('.gv1-shop-row').first().waitFor();
  // Tidal Legion holds Harmonized Trio, whose two costs the file joins with ` // `.
  await page.getByRole('button', { name: 'Add Tidal Legion' }).click();
  const rows = await page.locator('.gv1-shop-row').evaluateAll((els) =>
    els.map((el) => ({
      name: el.getAttribute('data-card-name') ?? '',
      cost: el.querySelector('.gv1-shop-mana')?.getAttribute('aria-label') ?? null,
    })),
  );
  const twoPart = rows.filter((row) => joined.has(row.name.toLowerCase()));
  expect(twoPart.length).toBeGreaterThan(0);
  for (const row of twoPart) {
    const front = joined.get(row.name.toLowerCase())!.split(' // ')[0];
    expect(row.cost, row.name).toBe(`mana cost ${front}`);
  }
  expect(seen.api).toEqual([]);
});

test('a hover over ten commanders on /codex sends nothing, and the frame comes from the file', async ({
  page,
  context,
}) => {
  const seen = watch(context);
  await page.goto('/codex');
  const names = page.locator('[data-card-name]');
  await names.first().waitFor();
  // The deck selector scrolls its active pill into view after load: let it end first.
  await page.waitForTimeout(1_500);
  const hovered: string[] = [];
  for (let i = 0; hovered.length < 10; i += 1) {
    const name = (await names.nth(i).getAttribute('data-card-name'))!;
    if (hovered.includes(name)) continue;
    hovered.push(name);
    await hoverName(page, names.nth(i));
    await expect(page.locator('.gv1-cardhover img')).toHaveAttribute('src', /^https:\/\/cards\.scryfall\.io\/large\/front\//);
  }
  expect(hovered.every((name) => USD.has(name.toLowerCase()))).toBe(true);
  await page.waitForLoadState('networkidle');
  expect(seen.api).toEqual([]);
});

test('a hover over names outside the file looks them up through the limiter, with no format=image address', async ({
  page,
  context,
}) => {
  const seen = watch(context);
  await page.goto('/deck/creeping-corruption');
  const names = page.locator('.gv1-apo-pin[data-card-name], article[data-card-name]');
  await names.first().waitFor();
  const outside: number[] = [];
  const count = await names.count();
  for (let i = 0; i < count && outside.length < 10; i += 1) {
    const name = (await names.nth(i).getAttribute('data-card-name'))!;
    if (!USD.has(name.toLowerCase())) outside.push(i);
  }
  expect(outside.length).toBeGreaterThan(0);
  // The deck selector scrolls its active pill into view after load, and any
  // scroll closes the frame: let it end first.
  await page.waitForTimeout(1_500);
  for (const i of outside) {
    await hoverName(page, names.nth(i));
    await page.waitForTimeout(300);
  }
  await page.mouse.move(0, 0);
  await page.waitForTimeout(8_000);
  expect(seen.api.filter((url) => url.includes('format=image'))).toEqual([]);
  expect(seen.localImages).toEqual([]);
  expect(seen.lookups.length).toBeGreaterThan(0);
  expect(seen.lookups.length).toBeLessThanOrEqual(outside.length);
});

test.describe('the 429 stop', () => {
  test.use({ scryfall429From: 3, rateClock: 'page' });

  test('/combos sends nothing for 30 s after a rejected lookup, then one; a reload inside the stop sends nothing', async ({
    page,
    context,
  }) => {
    const seen = watch(context);
    await page.clock.install();
    await page.goto('/combos');
    // Lookup 3 meets the 429 with no CORS header: the app's fetch rejects and the stop starts.
    const stopKey = 'grimoire-scryfall-stop';
    await page.waitForFunction((key) => localStorage.getItem(key) !== null, stopKey, { timeout: 30_000 });
    const { until, ms, now } = await page.evaluate((key) => {
      const stop = JSON.parse(localStorage.getItem(key)!) as { until: number; ms: number };
      return { ...stop, now: Date.now() };
    }, stopKey);
    expect(ms).toBe(30_000);
    expect(seen.lookups).toHaveLength(3);

    // Hold the page's time, then move it to 1 ms before the end of the stop.
    await page.clock.pauseAt(now + 1);
    await page.clock.fastForward(until - (now + 1) - 1);
    await page.waitForTimeout(2_000);
    expect(seen.lookups).toHaveLength(3);

    // The stop ends: one request goes. It meets the 429 too, and the stop doubles.
    await page.clock.fastForward(2);
    await expect.poll(() => seen.lookups.length, { timeout: 10_000 }).toBe(4);
    await page.waitForTimeout(2_000);
    expect(seen.lookups).toHaveLength(4);
    // The card that met the first 429 went again.
    expect(seen.lookups[3]).toBe(seen.lookups[2]);
    const doubled = await page.evaluate((key) => JSON.parse(localStorage.getItem(key)!) as { ms: number }, stopKey);
    expect(doubled.ms).toBe(60_000);

    // A reload inside the stop reads it from storage and sends nothing.
    await page.reload();
    await page.locator('.gv1-lab-art').first().waitFor();
    await page.waitForTimeout(3_000);
    expect(seen.lookups).toHaveLength(4);
  });
});

test('two tabs of one context open /combos at once: they share bucket 1, and the rate check holds', async ({
  context,
}) => {
  test.setTimeout(90_000);
  const seen = watch(context);
  const tabs = await Promise.all([context.newPage(), context.newPage()]);
  await Promise.all(tabs.map((tab) => tab.goto('/combos')));
  for (const tab of tabs) {
    await tab.locator('.gv1-lab-art').first().waitFor();
    await expect(tab.locator('.gv1-lab-skeleton')).toHaveCount(0, { timeout: 60_000 });
  }
  // Each tab asks for each name at most once. A loaded answer lands in storage
  // before the other tab's turn, so that tab does not ask; a 404 (the stub has
  // most /combos names outside card-metadata.json) is not stored, so it does.
  const perName = new Map<string, number>();
  seen.lookups.forEach((url) => perName.set(url, (perName.get(url) ?? 0) + 1));
  expect(perName.size).toBeGreaterThan(5);
  expect(Math.max(...perName.values())).toBeLessThanOrEqual(2);
  // Both tabs together sent more than one tab alone may send in the time: the
  // fixture's rate check, 2 in any 1 s for the context, is what held them.
  expect(seen.lookups.length).toBeGreaterThan(perName.size);
});

test.describe('the seed and storage', () => {
  test.use({ cards: 'seeded' });

  test("a deck page drops the gv1-card: entry of every name of the file, so storage holds each card once", async ({
    page,
  }) => {
    const cardKeys = () =>
      page.evaluate(() => Object.keys(localStorage).filter((key) => key.startsWith('gv1-card:')).map((key) => key.slice(9)));
    await page.goto('/data/index.json');
    const before = await cardKeys();
    expect(before.filter((key) => USD.has(key)).length).toBe(USD.size);

    await page.goto('/deck/creeping-corruption');
    await page.locator('.gv1-card-tile').first().waitFor();
    // The stub's seed runs again at each navigation; the app's seed follows it.
    await expect.poll(async () => (await cardKeys()).filter((key) => USD.has(key)).length).toBe(0);
    // Only the faces that the file does not hold as names stay.
    const after = await cardKeys();
    expect(after.length).toBeGreaterThan(0);
    expect(after.length).toBeLessThan(100);
  });
});
