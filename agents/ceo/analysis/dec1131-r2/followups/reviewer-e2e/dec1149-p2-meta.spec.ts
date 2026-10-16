// DEC-1149 P2 (reviewer scratch): requests to /data/card-metadata.meta.json on one deck guide, cold and after a reload.
import { writeFileSync } from 'node:fs';
import { test } from './support/test';

test('P2: meta file requests on /deck/creeping-corruption', async ({ page, context }) => {
  const meta: string[] = [];
  const file: string[] = [];
  let phase = 'cold';
  context.on('request', (r) => {
    const path = new URL(r.url()).pathname;
    if (path === '/data/card-metadata.meta.json') meta.push(phase);
    if (path === '/data/card-metadata.json') file.push(phase);
  });
  await page.goto('/deck/creeping-corruption');
  await page.locator('.gv1-card-tile').first().waitFor();
  await page.waitForTimeout(2_000);
  phase = 'reload';
  await page.reload();
  await page.locator('.gv1-card-tile').first().waitFor();
  await page.waitForTimeout(2_000);
  phase = 'spa-nav';
  await page.locator('a[href="/shopping"]').first().click().catch(() => undefined);
  await page.waitForTimeout(2_000);
  const out = { meta, file };
  console.log(`P2 reading (${process.env.P2_LABEL}): ${JSON.stringify(out)}`);
  writeFileSync(`/tmp/dec1149/p2-meta-${process.env.P2_LABEL}.json`, JSON.stringify(out));
});
