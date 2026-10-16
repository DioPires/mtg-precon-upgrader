// DEC-1149 P3 (reviewer scratch): two tabs of one context open /combos at once.
// Logs the batches and the names that went twice. HOLD_MS holds each
// /cards/collection answer that long before the stub answers it.
import { appendFileSync } from 'node:fs';
import { expect, test } from './support/test';

const HOLD_MS = Number(process.env.P3_HOLD_MS ?? 0);

test(`P3: two tabs on /combos, answers held ${HOLD_MS} ms`, async ({ context }, testInfo) => {
  test.setTimeout(120_000);
  const batches: Array<{ at: number; names: string[] }> = [];
  const t0 = Date.now();
  context.on('request', (r) => {
    if (r.url() === 'https://api.scryfall.com/cards/collection' && r.method() === 'POST') {
      const body = JSON.parse(r.postData() ?? '{}') as { identifiers?: Array<{ name: string }> };
      batches.push({ at: Date.now() - t0, names: (body.identifiers ?? []).map((id) => id.name) });
    }
  });
  if (HOLD_MS > 0) {
    await context.route('https://api.scryfall.com/cards/collection', async (route) => {
      await new Promise((r) => setTimeout(r, HOLD_MS));
      await route.fallback();
    });
  }
  const tabs = await Promise.all([context.newPage(), context.newPage()]);
  await Promise.all(tabs.map((tab) => tab.goto('/combos')));
  for (const tab of tabs) {
    await tab.locator('.gv1-lab-art').first().waitFor();
    await expect(tab.locator('.gv1-lab-skeleton')).toHaveCount(0, { timeout: 60_000 });
  }
  await tabs[0].waitForTimeout(2_000);
  const count = new Map<string, number>();
  batches.flatMap((b) => b.names).forEach((n) => count.set(n, (count.get(n) ?? 0) + 1));
  const twice = [...count].filter(([, c]) => c > 1).map(([n]) => n);
  const line = { hold: HOLD_MS, repeat: testInfo.repeatEachIndex, batches: batches.map((b) => ({ at: b.at, n: b.names.length })), twice: twice.length, twiceNames: twice };
  appendFileSync(`/tmp/dec1149/p3-hold-${HOLD_MS}.jsonl`, JSON.stringify(line) + '\n');
  console.log(`P3 ${JSON.stringify(line)}`);
});
