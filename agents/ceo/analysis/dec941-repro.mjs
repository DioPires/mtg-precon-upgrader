// DEC-941 repro: owned-cards import lost after a clean localStorage.
import { chromium } from '@playwright/test';

const BASE = 'http://localhost:5199';
const browser = await chromium.launch();
const page = await browser.newPage();
const errors = [];
page.on('pageerror', (e) => errors.push(String(e)));

const usage = () => page.evaluate(() => {
  let chars = 0; const byPrefix = {};
  for (let i = 0; i < localStorage.length; i++) {
    const k = localStorage.key(i); const v = localStorage.getItem(k) || '';
    chars += k.length + v.length;
    const p = k.split(':')[0]; byPrefix[p] = (byPrefix[p] || 0) + k.length + v.length;
  }
  return { keys: localStorage.length, chars, byPrefix };
});

await page.goto(BASE + '/shopping');
await page.evaluate(() => localStorage.clear());
await page.reload();
await page.waitForSelector('#gv1-shop-owned-file', { state: 'attached', timeout: 60000 });
await page.waitForLoadState('networkidle');
await page.waitForTimeout(2000);
console.log('after clean reload on /shopping:', JSON.stringify(await usage()));

const probe = await page.evaluate(() => {
  try { localStorage.setItem('dec941-probe', 'x'.repeat(50_000)); localStorage.removeItem('dec941-probe'); return 'ok'; }
  catch (e) { return e.name + ': ' + e.message; }
});
console.log('50k-char write probe:', probe);

// Synthetic ManaBox-like CSV, ~4500 rows like priv_data/Owned.csv.
const rows = ['Name,Quantity'];
for (let i = 0; i < 4500; i++) rows.push(`Synthetic Card Number ${i},1`);
await page.setInputFiles('#gv1-shop-owned-file', {
  name: 'owned.csv', mimeType: 'text/csv', buffer: Buffer.from(rows.join('\n')),
});
await page.waitForTimeout(1000);
const msg = await page.evaluate(() => document.querySelector('.gv1-shop-owned-bar')?.textContent);
console.log('owned bar text:', msg);
const stored = await page.evaluate(() => (localStorage.getItem('grimoire-owned-cards') || '').length);
console.log('grimoire-owned-cards stored chars:', stored);

await page.goto(BASE + '/atlas');
await page.waitForLoadState('networkidle');
const storedAtlas = await page.evaluate(() => (localStorage.getItem('grimoire-owned-cards') || '').length);
console.log('on /atlas, grimoire-owned-cards stored chars:', storedAtlas);
console.log('page errors:', errors);
await browser.close();

// Workaround check: evict deck caches in-session, re-import, navigate, hard reload.
{
  const b = await chromium.launch(); const p = await b.newPage();
  await p.goto(BASE + '/shopping');
  await p.evaluate(() => localStorage.clear()); await p.reload();
  await p.waitForSelector('#gv1-shop-owned-file', { state: 'attached' });
  await p.waitForLoadState('networkidle'); await p.waitForTimeout(2000);
  await p.evaluate(() => Object.keys(localStorage).filter((k) => k.startsWith('gv1-deck-data-')).forEach((k) => localStorage.removeItem(k)));
  const rows = ['Name,Quantity']; for (let i = 0; i < 4500; i++) rows.push(`Synthetic Card Number ${i},1`);
  await p.setInputFiles('#gv1-shop-owned-file', { name: 'owned.csv', mimeType: 'text/csv', buffer: Buffer.from(rows.join('\n')) });
  await p.waitForTimeout(1000);
  const len = () => p.evaluate(() => (localStorage.getItem('grimoire-owned-cards') || '').length);
  console.log('WORKAROUND after import:', await len());
  await p.click('a[href="/atlas"]').catch(() => p.goto(BASE + '/atlas'));
  await p.waitForLoadState('networkidle');
  console.log('WORKAROUND on /atlas:', await len(), 'url', p.url());
  await p.reload(); await p.waitForLoadState('networkidle'); await p.waitForTimeout(2000);
  console.log('WORKAROUND after hard reload:', await len(), JSON.stringify(await p.evaluate(() => { let c = 0; for (let i = 0; i < localStorage.length; i++) c += localStorage.getItem(localStorage.key(i)).length; return { keys: localStorage.length, chars: c }; })));
  await b.close();
}
