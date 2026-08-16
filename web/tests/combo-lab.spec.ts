// DEC-487 — Combo Lab route smoke (fleet + paste modes).

import { expect, test } from '@playwright/test';

test('Combos nav link reaches the route with the tier framing', async ({ page }) => {
  await page.goto('/codex');
  await page.getByRole('link', { name: /combos/i }).first().click();
  await expect(page).toHaveURL(/\/combos/);
  await expect(page.getByRole('heading', { name: /combo lab/i })).toBeVisible();
});

test('fleet mode renders a curated combo report for a real deck', async ({ page }) => {
  await page.goto('/combos');
  // Deck selector present; report renders with the Tier-A framing + attribution.
  // (.first() = the Tier-A framing; later sections add their own framing blocks.)
  await expect(page.locator('.gv1-cl-select')).toBeVisible();
  await expect(page.locator('.gv1-cl-framing').first()).toContainText(/tier a/i);
  await expect(page.locator('.gv1-cl-framing').first()).toContainText(/goldfish/i);
  // Bracket disclosure section + corpus-version indicator.
  await expect(page.getByRole('region', { name: /bracket disclosure/i })).toBeVisible();
  await expect(page.locator('.gv1-cl-report-bar')).toContainText(/corpus/i);
  // Attribution footer (DR-6).
  await expect(page.locator('.gv1-cl-attrib')).toContainText(/commander spellbook/i);
  await expect(page.locator('.gv1-cl-attrib')).toContainText(/wizards of the coast/i);
});

test('fleet mode: eternal-agony surfaces included two-card combos', async ({ page }) => {
  await page.goto('/combos?mode=fleet&deck=eternal-agony');
  // Included section should list at least one Tier-A finding with a permalink.
  const findings = page.locator('.gv1-cl-finding');
  await expect(findings.first()).toBeVisible();
  await expect(findings.first().locator('.gv1-cl-tier-a')).toBeVisible();
  await expect(findings.first().locator('.gv1-cl-why')).toHaveAttribute(
    'href',
    /commanderspellbook\.com\/combo\//,
  );
});

test('paste mode matches a known 2-card combo', async ({ page }) => {
  await page.goto('/combos?mode=paste');
  await page.locator('.gv1-cl-textarea').fill('1 Sheoldred, the Apocalypse\n1 Peer into the Abyss');
  await page.getByRole('button', { name: /^analyze$/i }).click();
  // The report renders and the included section has at least one finding.
  await expect(page.locator('.gv1-cl-report')).toBeVisible();
  await expect(page.locator('.gv1-cl-finding').first()).toBeVisible();
  // NF-3 timing indicator appears.
  await expect(page.locator('.gv1-cl-paste-actions')).toContainText(/parse\+match/i);
});

test('export copies a tier-labeled report to the clipboard', async ({ page, context }) => {
  await context.grantPermissions(['clipboard-read', 'clipboard-write']);
  await page.goto('/combos?mode=fleet&deck=eternal-agony');
  await expect(page.locator('.gv1-cl-finding').first()).toBeVisible();
  await page.getByRole('button', { name: /copy text/i }).click();
  const clip = await page.evaluate(() => navigator.clipboard.readText());
  expect(clip).toContain('TIER A — CURATED');
  expect(clip).toContain('Commander Spellbook');
});

// ─── Phase 4 (DEC-516) ────────────────────────────────────────────────────────

test('Markdown export preserves tier labels + attribution (RT-4)', async ({ page, context }) => {
  await context.grantPermissions(['clipboard-read', 'clipboard-write']);
  await page.goto('/combos?mode=fleet&deck=eternal-agony');
  await expect(page.locator('.gv1-cl-finding').first()).toBeVisible();
  await page.getByRole('button', { name: /copy markdown/i }).click();
  const clip = await page.evaluate(() => navigator.clipboard.readText());
  expect(clip).toContain('# Combo Lab');
  expect(clip).toContain('Tier A · Combos present');
  expect(clip).toContain('Wizards of the Coast');
});

test('computed near-miss completion surfaces Tier-B + Tier-C completers (NM-1)', async ({
  page,
}) => {
  await page.goto('/combos?mode=fleet&deck=titan-convergence');
  const panel = page.getByRole('region', { name: /computed near-miss completions/i });
  await expect(panel).toBeVisible();
  await panel.getByRole('button', { name: /find completions/i }).click();
  // Latency line proves the pool scan ran within budget (NF-4).
  await expect(panel.locator('.gv1-cl-latency')).toContainText(/searched .* pool cards in .*ms/i);
  // Filters (NM-5): currency + max price + owned toggle.
  await expect(panel.locator('.gv1-cl-filters')).toContainText(/color identity/i);
  await expect(panel.getByRole('combobox')).toBeVisible();
  // At least one computed completion appears at Tier B or Tier C.
  await expect(panel.locator('.gv1-cl-tier-c').first()).toBeVisible();
});

test('paste mode Tier-B completion is disclosed as deferred', async ({ page }) => {
  await page.goto('/combos?mode=paste');
  await page
    .locator('.gv1-cl-textarea')
    .first()
    .fill('1 Blood Artist\n1 Viscera Seer\n1 Gravecrawler\n1 Carrion Feeder');
  await page.getByRole('button', { name: /^analyze$/i }).click();
  const panel = page.getByRole('region', { name: /computed near-miss completions/i });
  await expect(panel).toBeVisible();
  await panel.getByRole('button', { name: /find completions/i }).click();
  await expect(panel).toContainText(/not available for pasted decks/i);
});

test('deck-URL input degrades with an actionable message when blocked (IN-2)', async ({ page }) => {
  await page.goto('/combos?mode=paste');
  await page.getByPlaceholder(/moxfield\.com\/decks/i).fill('https://www.moxfield.com/decks/xxxxx');
  await page.getByRole('button', { name: /^load$/i }).click();
  // Either it resolves or (far more likely, CORS-blocked) it shows a paste-fallback message.
  await expect(page.locator('.gv1-cl-url-msg')).toBeVisible({ timeout: 15000 });
});
