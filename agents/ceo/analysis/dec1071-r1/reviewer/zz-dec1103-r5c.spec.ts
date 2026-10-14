// Scratch probe (DEC-1103 review, R5c). Which Moxfield requests does the check name?
// The scratch DNS rules map every Moxfield name that no block rule takes to the
// local logger on 127.0.0.1:14623, so no request can reach a Moxfield host.
import { appendFileSync } from 'node:fs';
import { test, type Page, type Route } from './support/test';

const URL_ = 'https://api2.moxfield.com/v3/decks/all/dec1103-r5c';
const OUT = '/tmp/dec1071-review/r5c/readings.jsonl';

const ROUTES: Record<string, ((route: Route) => Promise<void>) | null> = {
  continue: (route) => route.continue(),
  abort: (route) => route.abort(),
  'abort namenotresolved': (route) => route.abort('namenotresolved'),
  fulfill: (route) => route.fulfill({ status: 403, body: '' }),
  'no route': null,
};

async function send(page: Page, label: string) {
  page.on('requestfailed', (r) => {
    if (r.url() === URL_) appendFileSync(OUT, JSON.stringify({ label, tree: process.env.R5C_TREE, failure: r.failure()?.errorText, timing: r.timing() }) + '\n');
  });
  await page.goto('/data/index.json');
  return page.evaluate((u) => fetch(u).then((r) => `status ${r.status}`, (e) => String(e)), URL_);
}

for (const [label, handler] of Object.entries(ROUTES)) {
  test(`R5c ${label}`, async ({ page }) => {
    if (handler) await page.route('https://api2.moxfield.com/**', handler);
    const result = await send(page, label);
    console.log(`[R5C] ${process.env.R5C_TREE} ${label}: page read "${result}"`);
  });
}
