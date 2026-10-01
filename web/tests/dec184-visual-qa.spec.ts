// DEC-184: visual + a11y QA pass for the 5 production surfaces at phone widths.
// Captures full-page screenshots at 360/375/390/430/430-landscape/768/1024 and
// runs an interactive-control tap-target audit per the parent issue's pass criteria.
//
// Outputs:
//   web/qa-screenshots/dec-184/{surface}-{width}.png
//   web/qa-screenshots/dec-184/findings.json   (tap-target violations + overflow notes)

import { test, type Page } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const OUT_DIR = path.resolve(__dirname, '../qa-screenshots/dec-184');
const FINDINGS_PATH = path.join(OUT_DIR, 'findings.json');
const MIN_TAP = 44;

type Viewport = { label: string; width: number; height: number };

const VIEWPORTS: Viewport[] = [
  { label: '360', width: 360, height: 900 },
  { label: '375', width: 375, height: 900 },
  { label: '390', width: 390, height: 900 },
  { label: '430', width: 430, height: 900 },
  { label: '430-landscape', width: 932, height: 430 },
  { label: '768', width: 768, height: 1024 },
  { label: '1024', width: 1024, height: 768 },
];

type TapAuditTarget = { selector: string; label: string; surface: string };

const TAP_TARGETS: TapAuditTarget[] = [
  { surface: 'codex', selector: '.gv1-codex a, .gv1-codex button', label: 'codex card link/button' },
  { surface: 'deck', selector: '.gv1-engine-tabs button[role="tab"]', label: 'Engine tab' },
  { surface: 'deck', selector: '.gv1-apoth-card-row button, .gv1-apoth-row .gv1-btn-icon, .gv1-apoth-card button', label: 'Apothecary details button' },
  { surface: 'deck', selector: '.gv1-decklist-toolbar button, .gv1-decklist-toolbar input, .gv1-decklist-toolbar select', label: 'Decklist toolbar control' },
  { surface: 'topbar', selector: '.gv1-topbar-mobile-btn', label: 'Topbar hamburger' },
  { surface: 'shopping', selector: '.gv1-shop-rail button, .gv1-shop-chip, .gv1-shop-rail a', label: 'Shopping chip/button' },
];

type TapViolation = {
  surface: string;
  width: number;
  selector: string;
  label: string;
  text: string;
  width_px: number;
  height_px: number;
};

type Finding = {
  type: 'tap-target' | 'page-overflow';
  surface: string;
  width: number;
  detail: string;
};

const findings: Finding[] = [];

async function getFirstDeckId(page: Page): Promise<string> {
  const r = await page.request.get('/data/index.json');
  const idx = (await r.json()) as { commanders: { id: string }[] };
  return idx.commanders[0].id;
}

async function checkOverflow(page: Page, surface: string, width: number): Promise<void> {
  const overflows = await page.evaluate(() => {
    const win = window.innerWidth;
    const doc = document.documentElement.scrollWidth;
    return doc > win + 1;
  });
  if (overflows) {
    findings.push({ type: 'page-overflow', surface, width, detail: `documentElement.scrollWidth > window.innerWidth at ${width}px` });
  }
}

async function auditTapTargets(page: Page, surface: string, width: number): Promise<void> {
  const relevant = TAP_TARGETS.filter((t) => t.surface === surface || t.surface === 'topbar');
  for (const target of relevant) {
    const violations: TapViolation[] = await page.evaluate(({ selector, surface, label, MIN_TAP, width }) => {
      const els = Array.from(document.querySelectorAll<HTMLElement>(selector));
      const out: TapViolation[] = [];
      for (const el of els) {
        const r = el.getBoundingClientRect();
        if (r.width === 0 || r.height === 0) continue;
        const style = getComputedStyle(el);
        if (style.visibility === 'hidden' || style.display === 'none') continue;
        if (r.width < MIN_TAP || r.height < MIN_TAP) {
          out.push({
            surface,
            width,
            selector,
            label,
            text: (el.textContent || el.getAttribute('aria-label') || '').trim().slice(0, 40),
            width_px: Math.round(r.width * 100) / 100,
            height_px: Math.round(r.height * 100) / 100,
          });
        }
      }
      return out;
    }, { selector: target.selector, surface: target.surface, label: target.label, MIN_TAP, width });

    for (const v of violations) {
      findings.push({
        type: 'tap-target',
        surface: v.surface,
        width: v.width,
        detail: `${v.label} "${v.text}" is ${v.width_px}×${v.height_px} (min 44×44)  selector=${v.selector}`,
      });
    }
  }
}

async function shotFull(page: Page, file: string): Promise<void> {
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(150);
  await page.screenshot({ path: path.join(OUT_DIR, file), fullPage: true });
}

async function shotViewport(page: Page, file: string): Promise<void> {
  await page.waitForTimeout(150);
  await page.screenshot({ path: path.join(OUT_DIR, file), fullPage: false });
}

test.describe.configure({ mode: 'serial' });

for (const vp of VIEWPORTS) {
  test.describe(`DEC-184 ${vp.label}px`, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    test(`capture + audit @ ${vp.label}px`, async ({ page }) => {
      const deck = await getFirstDeckId(page);
      const w = vp.width;
      const lbl = vp.label;

      await page.goto('/codex');
      await page.locator('.gv1-codex').waitFor();
      await page.waitForLoadState('networkidle');
      await checkOverflow(page, 'codex', w);
      await auditTapTargets(page, 'codex', w);
      await shotFull(page, `codex-${lbl}.png`);

      await page.goto(`/deck/${deck}`);
      await page.locator('.gv1-deck-guide').waitFor();
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(400); // commander art settle
      await checkOverflow(page, 'deck', w);
      await auditTapTargets(page, 'deck', w);
      await shotFull(page, `deck-${lbl}.png`);

      // Topbar hamburger audit (mobile widths only)
      if (w <= 768) {
        await auditTapTargets(page, 'topbar', w);
        const btn = page.locator('.gv1-topbar-mobile-btn');
        if (await btn.count()) {
          await btn.click();
          await page.waitForTimeout(120);
          await shotViewport(page, `topbar-open-${lbl}.png`);
          await page.keyboard.press('Escape');
          await page.waitForTimeout(120);
        }
      }

      await page.goto('/compare');
      await page.locator('.gv1-cmp-table').waitFor();
      await page.waitForLoadState('networkidle');
      await checkOverflow(page, 'compare', w);
      await shotFull(page, `compare-${lbl}.png`);

      await page.goto('/shopping');
      await page.locator('.gv1-shop-rail').waitFor();
      await page.waitForLoadState('networkidle');
      await checkOverflow(page, 'shopping', w);
      await auditTapTargets(page, 'shopping', w);
      await shotFull(page, `shopping-${lbl}.png`);

      await page.goto(`/scrying/${deck}`);
      await page.locator('[data-gv1-screen="scrying"]').waitFor();
      await page.waitForLoadState('networkidle');
      await checkOverflow(page, 'scrying', w);
      await shotFull(page, `scrying-${lbl}.png`);
    });
  });
}

test.afterAll(async () => {
  if (!fs.existsSync(OUT_DIR)) fs.mkdirSync(OUT_DIR, { recursive: true });
  // de-dupe identical findings
  const key = (f: Finding) => `${f.type}|${f.surface}|${f.width}|${f.detail}`;
  const seen = new Set<string>();
  const unique = findings.filter((f) => {
    const k = key(f);
    if (seen.has(k)) return false;
    seen.add(k);
    return true;
  });
  fs.writeFileSync(FINDINGS_PATH, JSON.stringify(unique, null, 2));
  console.log(`[DEC-184] ${unique.length} findings written to ${FINDINGS_PATH}`);
});
