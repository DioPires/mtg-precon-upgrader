// DEC-1149 item 8 (reviewer scratch): a cold context visits all 21 deck guides, /shopping and /combos.
import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { test, type BrowserContext, type Page } from './support/test';

const DATA = resolve(dirname(fileURLToPath(import.meta.url)), '..', '..', 'data');
const IDS = (JSON.parse(readFileSync(resolve(DATA, 'index.json'), 'utf8')) as { commanders: Array<{ id: string }> }).commanders.map((c) => c.id);

async function settle(page: Page, context: BrowserContext, quietMs = 3000) {
  let last = Date.now();
  let open = 0;
  const onReq = (r: { url(): string }) => { if (/scryfall/.test(r.url())) { open += 1; last = Date.now(); } };
  const onDone = (r: { url(): string }) => { if (/scryfall/.test(r.url())) { open -= 1; last = Date.now(); } };
  context.on('request', onReq);
  context.on('requestfinished', onDone);
  context.on('requestfailed', onDone);
  const start = Date.now();
  while (Date.now() - start < 120_000) {
    await page.waitForTimeout(250);
    if (open <= 0 && Date.now() - last >= quietMs) break;
  }
  context.off('request', onReq);
  context.off('requestfinished', onDone);
  context.off('requestfailed', onDone);
}

test('item 8: storage after all 21 deck guides, /shopping and /combos', async ({ page, context }) => {
  test.setTimeout(600_000);
  const read = () => page.evaluate(() => {
    let chars = 0; let cardKeys = 0; let cardChars = 0;
    const byFamily: Record<string, number> = {};
    for (let i = 0; i < localStorage.length; i += 1) {
      const key = localStorage.key(i)!;
      const size = key.length + (localStorage.getItem(key) ?? '').length;
      chars += size;
      const family = key.startsWith('gv1-card:') ? 'gv1-card:' : key.replace(/:.*/, ':');
      byFamily[family] = (byFamily[family] ?? 0) + size;
      if (key.startsWith('gv1-card:')) { cardKeys += 1; cardChars += size; }
    }
    return { keys: localStorage.length, chars, cardKeys, cardChars, byFamily };
  });
  let batches = 0;
  context.on('request', (r) => { if (r.url() === 'https://api.scryfall.com/cards/collection') batches += 1; });
  const steps: Array<Record<string, unknown>> = [];
  for (const id of IDS) {
    await page.goto(`/deck/${id}`);
    await page.locator('.gv1-card-tile').first().waitFor();
    await settle(page, context);
    steps.push({ page: id, batches, ...(await read()) });
  }
  for (const path of ['/shopping', '/combos']) {
    await page.goto(path);
    await page.waitForTimeout(1_000);
    await settle(page, context);
    steps.push({ page: path, batches, ...(await read()) });
  }
  // Chromium's quota for localStorage of one origin: fill a probe key until it throws.
  const quota = await page.evaluate(() => {
    const used = (() => { let c = 0; for (let i = 0; i < localStorage.length; i += 1) { const k = localStorage.key(i)!; c += k.length + (localStorage.getItem(k) ?? '').length; } return c; })();
    let lo = 0; let hi = 20_000_000;
    while (hi - lo > 1_000) {
      const mid = Math.floor((lo + hi) / 2);
      try { localStorage.setItem('dec1149-probe', 'x'.repeat(mid)); lo = mid; } catch { hi = mid; }
      localStorage.removeItem('dec1149-probe');
    }
    return { used, freeForOneValue: lo, total: used + lo + 'dec1149-probe'.length };
  });
  writeFileSync('/tmp/dec1149/item8-storage-all.json', JSON.stringify({ steps, quota }, null, 2));
  console.log(`item 8 last: ${JSON.stringify(steps[steps.length - 1])}; quota ${JSON.stringify(quota)}`);
});
