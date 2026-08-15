// Combo Lab report helpers — pure, testable logic shared by the route UI and
// the export paths. DEC-487 (DEC-476 Phase 0).
//
// Epistemic-tier vocabulary (PRD 6.7 / EI-1..EI-5): every finding surfaced here
// is Tier A — Curated (Commander Spellbook, human-verified). Tier B/C are later
// phases; nothing in Phase 0 is labeled beyond Tier A.

import { BRACKET_TAG_LABELS, type SpellbookCombo } from '../data/spellbook';

export interface ComboReport {
  mode: 'fleet' | 'paste';
  deckLabel: string;
  commander: string[];
  corpusVersion: string;
  included: SpellbookCombo[];
  nearMisses: SpellbookCombo[];
  nearMissesTotal: number;
  /** RT-5 partial-analysis accounting. For paste mode only; fleet = full deck. */
  cardsAnalyzed: number;
  cardsTotal: number;
  /** IN-6 unresolvable lines (paste mode). */
  unresolved: string[];
}

/** A combo's element count: cycle-piece cards + required templates (BR-1). */
export function pieceCount(c: SpellbookCombo): number {
  return c.cards.length + c.templates.length;
}

const WIN_MARKERS = [/wins? the game/i, /loses? the game/i, /win the game/i];

/** Does this combo end the game outright (vs. generate value)? RT-1. */
export function isWinCombo(c: SpellbookCombo): boolean {
  return c.produces.some((p) => WIN_MARKERS.some((re) => re.test(p)));
}

/** Two-card infinite combos carry outsized bracket weight (BR-1) — flag them. */
export function isTwoCardInfinite(c: SpellbookCombo): boolean {
  return pieceCount(c) === 2 && c.produces.some((p) => /infinite/i.test(p));
}

export function bracketLabel(tag: string): string {
  return BRACKET_TAG_LABELS[tag] ?? tag ?? '—';
}

export interface BracketDisclosure {
  totalCombos: number;
  twoCardInfinites: number;
  winCombos: number;
  byBracketTag: { tag: string; label: string; count: number }[];
  resultTypes: { label: string; count: number }[];
}

/** BR-1 disclosure summary of the deck's combo profile (Tier-A included only). */
export function buildBracketDisclosure(included: SpellbookCombo[]): BracketDisclosure {
  const tagCounts = new Map<string, number>();
  const resultCounts = new Map<string, number>();
  for (const c of included) {
    tagCounts.set(c.bracketTag, (tagCounts.get(c.bracketTag) ?? 0) + 1);
    for (const p of c.produces) resultCounts.set(p, (resultCounts.get(p) ?? 0) + 1);
  }
  return {
    totalCombos: included.length,
    twoCardInfinites: included.filter(isTwoCardInfinite).length,
    winCombos: included.filter(isWinCombo).length,
    byBracketTag: [...tagCounts.entries()]
      .map(([tag, count]) => ({ tag, label: bracketLabel(tag), count }))
      .sort((a, b) => b.count - a.count),
    resultTypes: [...resultCounts.entries()]
      .map(([label, count]) => ({ label, count }))
      .sort((a, b) => b.count - a.count),
  };
}

function comboCardLine(c: SpellbookCombo): string {
  const cards = c.cards.map((x) => (x.mustBeCommander ? `${x.name} (commander)` : x.name));
  const tmpl = c.templates.map((t) => `[${t.name}]`);
  return [...cards, ...tmpl].join(' + ');
}

/**
 * RT-4 / BR-4 minimal export. Plain text preserving tier labels + attribution +
 * corpus version + the goldfish/coverage caveats. Tier labels must survive every
 * export path (EI-4), so they are written inline, not just in a header.
 */
export function buildPlainTextExport(report: ComboReport): string {
  const lines: string[] = [];
  lines.push('COMBO LAB — combo report');
  lines.push(`Deck: ${report.deckLabel}`);
  if (report.commander.length) lines.push(`Commander: ${report.commander.join(' + ')}`);
  if (report.mode === 'paste' && report.cardsAnalyzed < report.cardsTotal) {
    lines.push(`Analyzed ${report.cardsAnalyzed} of ${report.cardsTotal} cards.`);
  }
  lines.push('');
  lines.push('All findings below are TIER A — CURATED (source: Commander Spellbook,');
  lines.push('human-verified). Analysis assumes a goldfish (no interaction). This is');
  lines.push('not an exhaustiveness claim — only combos in the curated corpus are shown.');
  lines.push(`Corpus version: ${report.corpusVersion}`);
  lines.push('');

  const disc = buildBracketDisclosure(report.included);
  lines.push('— BRACKET / RULE-0 DISCLOSURE —');
  lines.push(
    `${disc.totalCombos} curated combo(s) present · ${disc.twoCardInfinites} two-card infinite(s) · ${disc.winCombos} win-the-game`,
  );
  if (disc.byBracketTag.length) {
    lines.push(
      `Spellbook bracket tags: ${disc.byBracketTag.map((b) => `${b.label} ×${b.count}`).join(', ')}`,
    );
  }
  lines.push('');

  lines.push(`— TIER A · COMBOS PRESENT (${report.included.length}) —`);
  if (!report.included.length) {
    lines.push('No curated combos found (at any tier), within corpus coverage.');
  }
  for (const c of report.included) {
    const flags = [
      isTwoCardInfinite(c) ? '2-card infinite' : '',
      isWinCombo(c) ? 'WIN' : '',
    ].filter(Boolean);
    lines.push(`• [Tier A] ${comboCardLine(c)}${flags.length ? ` (${flags.join(', ')})` : ''}`);
    if (c.produces.length) lines.push(`    Result: ${c.produces.join('; ')}`);
    lines.push(`    Bracket tag (Commander Spellbook): ${bracketLabel(c.bracketTag)}`);
    lines.push(`    ${c.permalink}`);
  }
  lines.push('');

  lines.push(
    `— TIER A · NEAR-MISSES / ONE-TO-TWO CARDS AWAY (${report.nearMisses.length}${report.nearMissesTotal > report.nearMisses.length ? ` of ${report.nearMissesTotal}` : ''}) —`,
  );
  for (const c of report.nearMisses) {
    const need = [
      ...(c.missing?.cards ?? []),
      ...(c.missing?.templates ?? []).map((t) => `a ${t.name}`),
    ];
    lines.push(`• [Tier A near-miss] ${comboCardLine(c)}`);
    lines.push(`    Needs: ${need.join(', ')}`);
    if (c.produces.length) lines.push(`    Would produce: ${c.produces.join('; ')}`);
    lines.push(`    ${c.permalink}`);
  }
  lines.push('');
  lines.push('Combo data © Commander Spellbook (CC-BY-SA). Card data © Scryfall.');
  lines.push('Not affiliated with or endorsed by Wizards of the Coast.');
  return lines.join('\n');
}
