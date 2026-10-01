// DEC-942 verification: evict-and-retry path in a real browser: pad localStorage to the
// quota with deck-cache + card-cache keys, then import 4,500 owned rows.
// Run it from web/ (that is where @playwright/test lives):
//   cd web && npm run dev -- --port 5199 &
//   cd web && cp ../agents/frontend-eng/analysis/dec942-evict-verify.mjs . \
//     && node dec942-evict-verify.mjs; rm dec942-evict-verify.mjs
import { chromium } from '@playwright/test';
const BASE = 'http://localhost:5199';
const b = await chromium.launch();
const p = await b.newPage();
const errors = []; p.on('pageerror', (e) => errors.push(String(e)));
const chars = () => p.evaluate(() => { let c = 0; for (let i = 0; i < localStorage.length; i++) c += localStorage.key(i).length + localStorage.getItem(localStorage.key(i)).length; return c; });

await p.goto(BASE + '/shopping');
await p.evaluate(() => localStorage.clear());
await p.reload();
await p.waitForSelector('#gv1-shop-owned-file', { state: 'attached', timeout: 60000 });
await p.waitForLoadState('networkidle');
await p.waitForTimeout(2000);

// Pad with evictable cache keys until the quota is reached.
const pad = await p.evaluate(() => {
  const blob = 'x'.repeat(100_000);
  let n = 0;
  try { for (; n < 200; n++) localStorage.setItem('gv1-card:pad' + n, blob); } catch { /* full */ }
  let probe = 'ok';
  try { localStorage.setItem('dec942-probe', 'y'.repeat(150_000)); localStorage.removeItem('dec942-probe'); }
  catch (e) { probe = e.name; }
  return { padKeys: n, probe };
});
console.log('padded:', JSON.stringify(pad), 'chars:', await chars());

const rows = ['Name,Quantity'];
for (let i = 0; i < 4500; i++) rows.push(`Synthetic Card Number ${i},1`);
await p.setInputFiles('#gv1-shop-owned-file', { name: 'owned.csv', mimeType: 'text/csv', buffer: Buffer.from(rows.join('\n')) });
await p.waitForTimeout(1000);
console.log('owned bar:', await p.evaluate(() => document.querySelector('.gv1-shop-owned-bar')?.textContent));
console.log('import msg:', await p.evaluate(() => document.querySelector('.gv1-shop-import-msg')?.textContent));
console.log('owned stored chars:', await p.evaluate(() => (localStorage.getItem('grimoire-owned-cards') || '').length));
console.log('pad keys left:', await p.evaluate(() => Object.keys(localStorage).filter((k) => k.startsWith('gv1-card:pad')).length));
await p.goto(BASE + '/atlas');
await p.waitForLoadState('networkidle');
console.log('on /atlas owned chars:', await p.evaluate(() => (localStorage.getItem('grimoire-owned-cards') || '').length));
console.log('page errors:', errors);
await b.close();
