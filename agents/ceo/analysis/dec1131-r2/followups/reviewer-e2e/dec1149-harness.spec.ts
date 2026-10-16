// DEC-1149 items 6b, 6d and 6e (reviewer scratch).
import { expect, test } from './support/test';

const COLLECTION = 'https://api.scryfall.com/cards/collection';
const post = (names: string[]) => ({
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ identifiers: names.map((name) => ({ name })) }),
});

// 6b: the H7 and N2 cases of dec1131-card-batches.spec.ts without test.fail(), to read the rate check's message.
test.describe("6b: three batches in one second of the page's clock (H7, no test.fail)", () => {
  test.use({ rateClock: 'page' });
  test('H7 copy', async ({ page }) => {
    await page.clock.install();
    await page.goto('/data/index.json');
    await page.clock.pauseAt(Date.now() + 10_000);
    for (let i = 0; i < 3; i += 1) {
      await page.evaluate((url) => void fetch(url, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ identifiers: [{ name: 'Sol Ring' }] }),
      }).catch(() => undefined), COLLECTION);
      await page.clock.fastForward(400);
    }
    await page.waitForTimeout(1_000);
  });
});

test('6c: N2 copy, real clock, a held answer (no test.fail)', async ({ page }) => {
  test.setTimeout(30_000);
  let n = 0;
  await page.route(COLLECTION, async (route) => {
    const wait = 1_200 * n;
    n += 1;
    await new Promise((r) => setTimeout(r, wait));
    await route.fallback();
  });
  await page.goto('/data/index.json');
  await page.evaluate((url) => Promise.all([0, 1, 2].map(() => fetch(url, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ identifiers: [{ name: 'Sol Ring' }] }),
  }).then((r) => r.status))), COLLECTION);
});

test('6d: the preflight of one batch POST, as CDP, the route and the request event see it', async ({ page, context }) => {
  const cdpEvents: string[] = [];
  const requestEvents: string[] = [];
  const routed: string[] = [];
  const cdp = await context.newCDPSession(page);
  await cdp.send('Network.enable');
  cdp.on('Network.requestWillBeSent', (e: { request: { method: string; url: string }; type?: string }) => {
    if (e.request.url.includes('api.scryfall.com')) cdpEvents.push(`requestWillBeSent ${e.request.method} ${e.request.url} type=${e.type}`);
  });
  cdp.on('Network.requestWillBeSentExtraInfo', (e: { headers: Record<string, string> }) => {
    const h = e.headers ?? {};
    if (String(h[':authority'] ?? h['Host'] ?? h['host'] ?? '').includes('scryfall')) cdpEvents.push(`extraInfo ${h[':method'] ?? ''} ${h[':path'] ?? ''}`);
  });
  cdp.on('Network.responseReceived', (e: { response: { url: string; status: number }; type?: string }) => {
    if (e.response.url.includes('api.scryfall.com')) cdpEvents.push(`responseReceived ${e.response.status} type=${e.type}`);
  });
  context.on('request', (r) => {
    if (r.url().includes('api.scryfall.com')) requestEvents.push(r.method());
  });
  await page.route('https://api.scryfall.com/**', async (route) => {
    routed.push(route.request().method());
    await route.fallback();
  });
  await page.goto('/data/index.json');
  const status = await page.evaluate((url) => fetch(url, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ identifiers: [{ name: 'Sol Ring' }] }),
  }).then((r) => r.status), COLLECTION);
  await page.waitForTimeout(500);
  console.log(`6d reading: status ${status}; CDP ${JSON.stringify(cdpEvents)}; request events ${JSON.stringify(requestEvents)}; route ${JSON.stringify(routed)}`);
  expect(status).toBe(200);
});

test('6e: 76 identifiers to the stub', async ({ page }) => {
  await page.goto('/data/index.json');
  const names = Array.from({ length: 76 }, (_, i) => (i === 0 ? 'Sol Ring' : `Name ${i}`));
  const answer = await page.evaluate(([url, init]) => fetch(url as string, init as RequestInit).then(async (r) => ({
    status: r.status, contentType: r.headers.get('content-type'), body: await r.text(),
  })), [COLLECTION, post(names)] as const);
  console.log(`6e reading: ${JSON.stringify(answer)}`);
  expect(answer.status).toBe(422);
});
