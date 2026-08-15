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
  await expect(page.locator('.gv1-cl-select')).toBeVisible();
  await expect(page.locator('.gv1-cl-framing')).toContainText(/tier a/i);
  await expect(page.locator('.gv1-cl-framing')).toContainText(/goldfish/i);
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
  await page.getByRole('button', { name: /copy report/i }).click();
  const clip = await page.evaluate(() => navigator.clipboard.readText());
  expect(clip).toContain('TIER A — CURATED');
  expect(clip).toContain('Commander Spellbook');
});
