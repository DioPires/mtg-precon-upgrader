// DEC-199 visual QA: capture Tokens section on 3 decks, desktop + mobile,
// plus a producer-hover popover. Outputs PNGs alongside this file.
import { chromium } from 'playwright';
import { mkdirSync, writeFileSync } from 'node:fs';

const OUT = new URL('.', import.meta.url).pathname;
const BASE = 'http://127.0.0.1:4173';
const DECKS = ['titan-convergence', 'eternal-harvest', 'the-white-forge'];

mkdirSync(OUT, { recursive: true });

const findings = [];

const browser = await chromium.launch();

async function shoot(label, page, locator) {
  const path = `${OUT}${label}.png`;
  if (locator) {
    await locator.screenshot({ path });
  } else {
    await page.screenshot({ path, fullPage: false });
  }
  return path;
}

for (const deck of DECKS) {
  // Desktop @ 1280x900
  {
    const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
    const page = await ctx.newPage();
    page.on('pageerror', (e) => findings.push({ deck, scope: 'desktop', pageerror: String(e) }));
    page.on('console', (m) => {
      if (m.type() === 'error') findings.push({ deck, scope: 'desktop', console: m.text() });
    });
    await page.goto(`${BASE}/deck/${deck}`, { waitUntil: 'networkidle' });
    // wait for tokens section
    const tokens = page.locator('section.gv1-tokens');
    await tokens.waitFor({ timeout: 10_000 });
    const present = await tokens.count();
    const headerText = (await tokens.locator('.gv1-section-head').innerText().catch(() => '')) || '';
    const cardCount = await tokens.locator('.gv1-token-card').count();
    const imgs = await tokens.locator('.gv1-token-img:not(.gv1-token-img-stub)').count();
    const stubs = await tokens.locator('.gv1-token-img-stub').count();
    const producers = await tokens.locator('.gv1-token-producer').count();
    const dataCardNames = await tokens.locator('.gv1-token-producer[data-card-name]').count();
    findings.push({
      deck, scope: 'desktop',
      tokensSectionPresent: present > 0,
      headerText: headerText.replace(/\s+/g, ' ').trim(),
      cardCount, imgs, stubs, producers, dataCardNames,
    });

    await tokens.scrollIntoViewIfNeeded();
    await page.waitForTimeout(400);
    await shoot(`${deck}-desktop-section`, page, tokens);

    // Hover the first producer to verify GV1CardHoverLayer fires
    const firstProducer = tokens.locator('.gv1-token-producer').first();
    const producerName = await firstProducer.getAttribute('data-card-name');
    const box = await firstProducer.boundingBox();
    if (box) {
      await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
      await page.waitForTimeout(900);
      // hover layer is fixed-position overlay rendered at body root
      const hoverLayerCount = await page.locator('[class*="hover"], [class*="Hover"], .gv1-card-hover-layer, .gv1-card-hover, .gv1-hover-layer').count();
      const hoverImgs = await page.locator('img[src*="cards.scryfall.io"]').count();
      // Take a screenshot of the page with hover active so we can eyeball it
      await shoot(`${deck}-desktop-producer-hover`, page);
      findings.push({
        deck, scope: 'desktop-hover',
        producerName, hoverLayerCount, hoverImgs,
      });
    }
    await ctx.close();
  }

  // Mobile @ 390x844 (iPhone 14)
  {
    const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2 });
    const page = await ctx.newPage();
    page.on('pageerror', (e) => findings.push({ deck, scope: 'mobile', pageerror: String(e) }));
    await page.goto(`${BASE}/deck/${deck}`, { waitUntil: 'networkidle' });
    const tokens = page.locator('section.gv1-tokens');
    await tokens.waitFor({ timeout: 10_000 });
    await tokens.scrollIntoViewIfNeeded();
    await page.waitForTimeout(400);
    await shoot(`${deck}-mobile-section`, page, tokens);

    // Inspect computed grid template at this viewport
    const grid = await tokens.locator('.gv1-tokens-grid').first().evaluate((el) => {
      const cs = getComputedStyle(el);
      return {
        gridTemplateColumns: cs.gridTemplateColumns,
        gap: cs.gap,
      };
    });
    findings.push({ deck, scope: 'mobile', grid });
    await ctx.close();
  }
}

// Edge case: there's no production deck with tokens=[]. We'll mock it via DOM
// by hitting an unrelated route — but since every deck has tokens, we instead
// document this in findings.json and rely on the unit test for the empty case.
findings.push({
  scope: 'empty-state',
  note: 'No production deck has tokens.length === 0; empty hide is covered by web/src/components/organisms/Tokens.test.tsx (unit).',
});

await browser.close();
writeFileSync(`${OUT}findings.json`, JSON.stringify(findings, null, 2));
console.log(JSON.stringify(findings, null, 2));
