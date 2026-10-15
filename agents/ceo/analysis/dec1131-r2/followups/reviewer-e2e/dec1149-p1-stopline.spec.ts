// DEC-1149 P1 (reviewer scratch): the /shopping stop line at 390 px and 1440 px,
// with the fonts live and blocked. Reads its size after document.fonts.ready, its
// contrast, and Chromium's own accessibility node (CDP), and takes screenshots
// with animations disabled.
import { mkdirSync, writeFileSync } from 'node:fs';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { expect, test } from './support/test';

const DATA = resolve(dirname(fileURLToPath(import.meta.url)), '..', '..', 'data');
const PRICES_AS_OF = (JSON.parse(readFileSync(resolve(DATA, 'card-metadata.meta.json'), 'utf8')) as { prices_as_of: string }).prices_as_of;
const OUT = '/tmp/dec1149/p1';
const STOP_KEY = 'grimoire-scryfall-stop';

for (const fonts of ['live', 'blocked'] as const) {
  for (const width of [390, 1440]) {
    test.describe(`stop line ${width} px, fonts ${fonts}`, () => {
      test.use({ scryfall429From: 1, rateClock: 'page', fonts, viewport: { width, height: 900 } });

      test(`shot ${width} ${fonts}`, async ({ page }) => {
        test.setTimeout(60_000);
        mkdirSync(OUT, { recursive: true });
        await page.clock.install({ time: Math.max(Date.now(), Date.parse(PRICES_AS_OF) + 25 * 3_600_000) });
        await page.goto('/shopping');
        await page.locator('.gv1-shop-row').first().waitFor();
        await page.waitForFunction((key) => localStorage.getItem(key) !== null, STOP_KEY, { timeout: 30_000 });
        const line = page.getByRole('status').filter({ hasText: 'Price refresh paused' });
        await expect(line).toHaveCount(1);
        // Hold the page clock so that the line stays for the reads.
        await page.clock.pauseAt((await page.evaluate(() => Date.now())) + 500);
        await page.evaluate(() => document.fonts.ready.then(() => undefined));
        const read = await line.evaluate((el) => {
          const cs = getComputedStyle(el);
          const rect = el.getBoundingClientRect();
          let bgEl: Element | null = el;
          let bg = 'rgba(0, 0, 0, 0)';
          while (bgEl) {
            const b = getComputedStyle(bgEl).backgroundColor;
            if (b && b !== 'rgba(0, 0, 0, 0)' && b !== 'transparent') { bg = b; break; }
            bgEl = bgEl.parentElement;
          }
          const parse = (c: string) => (c.match(/[\d.]+/g) ?? []).map(Number);
          const lum = ([r, g, b]: number[]) => {
            const f = (v: number) => { const s = v / 255; return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4; };
            return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
          };
          const fg = parse(cs.color);
          const back = parse(bg);
          // The colour is opaque in tokens; blend an alpha colour over the background when there is one.
          const a = fg.length > 3 ? fg[3] : 1;
          const blended = [0, 1, 2].map((i) => fg[i] * a + back[i] * (1 - a));
          const l1 = lum(blended);
          const l2 = lum(back);
          const ratio = (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
          return {
            text: el.textContent,
            width: Math.round(rect.width * 10) / 10,
            height: Math.round(rect.height * 10) / 10,
            lines: Math.round(rect.height / parseFloat(cs.lineHeight || '16')),
            fontFamily: cs.fontFamily,
            fontSize: cs.fontSize,
            lineHeight: cs.lineHeight,
            color: cs.color,
            background: bg,
            contrast: Math.round(ratio * 100) / 100,
            border: cs.border,
            padding: cs.padding,
            margin: cs.margin,
            scrollOverflow: document.documentElement.scrollWidth > window.innerWidth,
            fontsLoaded: [...document.fonts].filter((f) => f.status === 'loaded').map((f) => f.family),
          };
        });
        // Chromium's own accessibility node of the line.
        const cdp = await page.context().newCDPSession(page);
        await cdp.send('DOM.enable');
        await cdp.send('Accessibility.enable');
        const { root } = (await cdp.send('DOM.getDocument', { depth: -1 })) as { root: { nodeId: number } };
        const { nodeId } = (await cdp.send('DOM.querySelector', { nodeId: root.nodeId, selector: '.gv1-shop-paused' })) as { nodeId: number };
        const ax = (await cdp.send('Accessibility.getPartialAXTree', { nodeId, fetchRelatives: false })) as {
          nodes: Array<{ role?: { value: string }; name?: { value: string }; properties?: Array<{ name: string; value: { value: unknown } }> }>;
        };
        const node = ax.nodes[0];
        const axRead = {
          role: node.role?.value,
          name: node.name?.value,
          properties: Object.fromEntries((node.properties ?? []).map((p) => [p.name, p.value.value])),
        };
        await line.screenshot({ path: `${OUT}/line-${width}-${fonts}.png`, animations: 'disabled' });
        await page.locator('.gv1-shop-summary').evaluate((el) => el.scrollIntoView({ block: 'start' }));
        const section = line.locator('xpath=ancestor::section[1]');
        await section.screenshot({ path: `${OUT}/section-${width}-${fonts}.png`, animations: 'disabled' });
        writeFileSync(`${OUT}/read-${width}-${fonts}.json`, JSON.stringify({ read, axRead }, null, 2));
        console.log(`P1 ${width} ${fonts}: ${JSON.stringify({ read, axRead })}`);
        expect(read.scrollOverflow).toBe(false);
      });
    });
  }
}
