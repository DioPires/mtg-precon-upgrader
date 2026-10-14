// DEC-534 — Combo Lab redesign smoke (control rail + report column).
// Covers: fleet report render, paste-mode full pipeline, unresolved-lines
// warning, copy text/markdown exports, completions, Tier-B region in paste
// mode, deck-URL loader message.

import { expect, test } from './support/test';

test('Combos nav link reaches the route with the lab shell', async ({ page }) => {
  await page.goto('/codex');
  await page.getByRole('link', { name: /combos/i }).first().click();
  await expect(page).toHaveURL(/\/combos/);
  await expect(page.getByRole('heading', { name: /combo lab/i })).toBeVisible();
  // Control rail with the mode toggle + tier legend.
  await expect(page.getByRole('complementary', { name: /combo lab controls/i })).toBeVisible();
  await expect(page.getByRole('button', { name: /fleet deck/i })).toHaveAttribute(
    'aria-pressed',
    'true',
  );
});

test('fleet mode renders the disclosure band first with the five stats', async ({ page }) => {
  await page.goto('/combos');
  // The Disclosure opens the report: five stat cells + goldfish caveat + corpus stamp.
  const summary = page.getByRole('region', { name: /bracket and rule-0 disclosure/i });
  await expect(summary).toBeVisible();
  await expect(summary.locator('.gv1-lab-stat')).toHaveCount(5);
  await expect(summary.locator('.gv1-lab-summary-foot')).toContainText(/goldfish/i);
  await expect(summary.locator('.gv1-lab-summary-foot')).toContainText(/corpus/i);
  // Tier-A framing box keeps the epistemic copy.
  await expect(page.locator('.gv1-lab-framing').first()).toContainText(/human-verified/i);
  await expect(page.locator('.gv1-lab-tier-a').first()).toBeVisible();
  // Attribution footer.
  await expect(page.locator('.gv1-lab-attrib')).toContainText(/commander spellbook/i);
  await expect(page.locator('.gv1-lab-attrib')).toContainText(/wizards of the coast/i);
});

test('fleet mode surfaces curated combos and the deck picker writes ?deck=', async ({ page }) => {
  await page.goto('/combos?mode=fleet&deck=eternal-agony');
  // Included section lists Tier-A finding cards with a Spellbook permalink.
  const combo = page.locator('.gv1-lab-combo').first();
  await expect(combo).toBeVisible();
  await expect(combo.locator('.gv1-lab-tier-a')).toBeVisible();
  await expect(combo.locator('.gv1-lab-link')).toHaveAttribute(
    'href',
    /commanderspellbook\.com\/combo\//,
  );
  // Deck picker is a listbox; picking a row writes that deck's id to the URL
  // (id read from the DOM — no hardcoded catalog order).
  const picker = page.getByRole('listbox', { name: /fleet decks/i });
  await expect(picker).toBeVisible();
  const firstOption = picker.getByRole('option').first();
  const deckId = await firstOption.getAttribute('data-deck-id');
  expect(deckId).toBeTruthy();
  await firstOption.click();
  await expect(page).toHaveURL(new RegExp(`deck=${deckId}`));
  await expect(firstOption).toHaveAttribute('aria-selected', 'true');
});

test('paste mode runs the full pipeline and warns about unresolved lines', async ({ page }) => {
  await page.goto('/combos?mode=paste');
  await page
    .locator('.gv1-lab-textarea')
    .fill('1 Sheoldred, the Apocalypse\n1 Peer into the Abyss\n12345');
  await page.getByRole('button', { name: /analyze/i }).click();
  // Disclosure band renders with the paste-specific "cards analyzed" stat.
  const summary = page.getByRole('region', { name: /bracket and rule-0 disclosure/i });
  await expect(summary).toBeVisible();
  await expect(summary.locator('.gv1-lab-stats')).toContainText(/cards analyzed/i);
  // The known 2-card combo matches as a Tier-A finding card.
  await expect(page.locator('.gv1-lab-combo').first()).toBeVisible();
  // IN-6 — the unresolvable line is disclosed, not silently dropped.
  const warn = page.locator('.gv1-lab-warn').first();
  await expect(warn).toContainText(/could not be read/i);
  await expect(warn).toContainText('12345');
  // NF-3 timing note in the rail.
  await expect(page.locator('.gv1-lab-note', { hasText: /parse\+match/i })).toBeVisible();
});

test('paste mode runs the Tier-B verifier and surfaces a known loop (DEC-516)', async ({
  page,
}) => {
  await page.goto('/combos?mode=paste');
  // A known 2-card infinite-mana loop: the client-side verifier should surface it
  // (corroborated if matched as a curated combo, novel if only enumerated).
  await page.locator('.gv1-lab-textarea').fill('1 Basalt Monolith\n1 Forsaken Monument');
  await page.getByRole('button', { name: /analyze/i }).click();
  const tierB = page.getByRole('region', { name: /verified loops/i });
  await expect(tierB).toBeVisible();
  await expect(tierB).toContainText(/Basalt Monolith/);
  await expect(tierB).toContainText(/Forsaken Monument/);
  // Completions also run for paste mode inside the new layout.
  const panel = page.getByRole('region', { name: /complete a near-miss/i });
  await expect(panel).toBeVisible();
  await expect(panel.locator('.gv1-lab-note', { hasText: /pool cards/i })).toBeVisible({
    timeout: 30000,
  });
});

test('export copies a tier-labeled plain-text report to the clipboard', async ({
  page,
  context,
}) => {
  await context.grantPermissions(['clipboard-read', 'clipboard-write']);
  await page.goto('/combos?mode=fleet&deck=eternal-agony');
  await expect(page.locator('.gv1-lab-combo').first()).toBeVisible();
  await page.getByRole('button', { name: /copy text/i }).click();
  await expect(page.getByRole('button', { name: /copied/i })).toBeVisible();
  const clip = await page.evaluate(() => navigator.clipboard.readText());
  expect(clip).toContain('TIER A — CURATED');
  expect(clip).toContain('Commander Spellbook');
});

test('Markdown export preserves tier labels + attribution (RT-4)', async ({ page, context }) => {
  await context.grantPermissions(['clipboard-read', 'clipboard-write']);
  await page.goto('/combos?mode=fleet&deck=eternal-agony');
  await expect(page.locator('.gv1-lab-combo').first()).toBeVisible();
  await page.getByRole('button', { name: /copy markdown/i }).click();
  const clip = await page.evaluate(() => navigator.clipboard.readText());
  expect(clip).toContain('# Combo Lab');
  expect(clip).toContain('Tier A · Combos present');
  expect(clip).toContain('Wizards of the Coast');
});

test('completions auto-run with price + owned filters (NM-1/NM-5)', async ({ page }) => {
  await page.goto('/combos?mode=fleet&deck=titan-convergence');
  const panel = page.getByRole('region', { name: /complete a near-miss/i });
  await expect(panel).toBeVisible();
  // The pool scan runs on its own and reports its latency + filter accounting (NF-4).
  await expect(
    panel.locator('.gv1-lab-note', { hasText: /searched .* pool cards in/i }),
  ).toBeVisible({ timeout: 30000 });
  await expect(panel.locator('.gv1-lab-note', { hasText: /color identity/i })).toBeVisible();
  // Filters: max price input, currency select, owned-only chip (disabled — no
  // collection imported in this fresh browser context).
  await expect(panel.getByPlaceholder('any')).toBeVisible();
  await expect(panel.getByRole('combobox')).toBeVisible();
  const ownedChip = panel.getByRole('button', { name: /owned only/i });
  await expect(ownedChip).toBeDisabled();
  await expect(panel).toContainText(/import in § IX Shopping/i);
  // At least one completion row renders with the 58px thumb anatomy.
  await expect(panel.locator('.gv1-lab-comp').first()).toBeVisible();
});

test('deck-URL input degrades with an actionable message when blocked (IN-2)', async ({ page }) => {
  // Moxfield's deck API refuses a headless browser. Give that refusal here, so
  // the case sends nothing to the host (DEC-1071). The stub stops and names a
  // Moxfield request that no route of the spec answers.
  await page.route('https://api2.moxfield.com/**', (route) => route.fulfill({ status: 403, body: '' }));
  await page.goto('/combos?mode=paste');
  await page.getByPlaceholder(/moxfield\.com\/decks/i).fill('https://www.moxfield.com/decks/xxxxx');
  await page.getByRole('button', { name: /^load$/i }).click();
  // Either it resolves or (far more likely, CORS-blocked) it shows a paste-fallback message.
  await expect(page.locator('.gv1-lab-url-msg')).toBeVisible({ timeout: 15000 });
  await expect(page.locator('.gv1-lab-url-msg')).toContainText('moxfield returned HTTP 403');
});
