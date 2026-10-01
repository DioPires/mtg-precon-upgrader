// DEC-526 — graveyard-return loop primitives, acceptance fixture.
//
// Runs the EXACT paste-mode pipeline (matchDecklist + verifyDeck, headless) over the
// reconstructed 80-card Bartolomé del Presidio deck from Commander Challenge video
// 1Yusxsud5BE, against the committed deployed artifacts (spellbook matcher index +
// tier-b-index). Asserts the Tier-B verifier now VERIFIES the death-return reanimator
// cores the ontology v1.1 primitives model — the family the verifier used to abstain
// on entirely (all generic etb/dies/drain features, 0 verified). Coven-gated Redemption
// Choir cores stay guarded/abstained by design.

import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, it, expect } from 'vitest';
import { matchDecklist } from './spellbookMatch';
import { verifyDeck } from './comboVerify';
import type { MatcherIndex } from '../data/spellbook';
import type { TierBIndex } from '../data/tierBIndex';
import type { TierBFinding } from '../data/tierB';

const here = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(here, '..', '..', '..');
const rj = <T>(rel: string): T => JSON.parse(readFileSync(resolve(repoRoot, rel), 'utf-8')) as T;

const matcherIndex = rj<MatcherIndex>('data/spellbook/matcher-index.json');
const tierBIndex = rj<TierBIndex>('data/combo-kb/tier-b-index.json');
const fixture = rj<{ commander: string; decklist: string[] }>(
  'web/src/lib/__fixtures__/bartolome-video.json',
);

// The named loop pieces (video walkthrough). Unconditional reanimators only —
// Redemption Choir is coven-gated (abstains).
const REANIMATORS = new Set([
  'Sun Titan',
  'Angel of Indemnity',
  'Shepherd of the Cosmos',
  'Boonweaver Giant',
  'Brotherhood Outcast',
  "Danitha, Benalia's Hope",
]);
const PARTNERS = new Set([
  'Werefox Bodyguard',
  'Fiend Hunter',
  'Gift of Immortality',
  "Kaya's Ghostform",
  "Minion's Return",
  'Necrogen Communion',
  'Angelic Renewal',
  'Changing Loyalty',
  'Fungal Fortitude',
]);

/** Extract the (reanimator, partner) core key from a graveyard_return finding's
 * 3-card set [reanimator, partner, free-sac]. */
function coreKey(f: TierBFinding): string | null {
  const r = f.cards.find((c) => REANIMATORS.has(c));
  const p = f.cards.find((c) => PARTNERS.has(c));
  return r && p ? `${r} + ${p}` : null;
}

describe('DEC-526 — Bartolomé del Presidio video fixture (paste-mode Tier-B)', () => {
  const cardNames = fixture.decklist;
  const commanderNames = [fixture.commander];

  // Step 1 — matchDecklist (Tier A curated combos), exactly as paste mode does.
  const match = matchDecklist({ cardNames, commanderNames }, matcherIndex);
  const curatedCardSets = match.included.map((c) => c.cards.map((cc) => cc.name));

  // Step 2 — verifyDeck (Tier B) with the curated sets for corroboration marking.
  const result = verifyDeck([...cardNames, ...commanderNames], tierBIndex, {
    commanderNames,
    curatedCardSets,
  });

  const gyVerified = [...result.corroborated, ...result.novel].filter(
    (f) => f.template === 'graveyard_return' && f.closes,
  );
  const gyEngines = result.engines.filter((f) => f.template === 'graveyard_return');
  const verifiedCores = new Set(gyVerified.map(coreKey).filter((k): k is string => k !== null));

  it('reports the pipeline result for the evidence trail', () => {
    console.log(
      `[DEC-526 fixture] curated(matchDecklist)=${match.included.length} ` +
        `Tier-B: corroborated=${result.counts.verifiedCorroborated} ` +
        `novel=${result.counts.verifiedNovel} engines=${result.counts.engines} ` +
        `capped=${result.counts.capped}\n` +
        `  graveyard_return verified findings=${gyVerified.length} ` +
        `distinct (reanimator+partner) cores=${verifiedCores.size}\n` +
        `  cores: ${[...verifiedCores].sort().join('; ')}\n` +
        `  graveyard_return engines (guarded/abstain)=${gyEngines.length} ` +
        `e.g. ${gyEngines.slice(0, 3).map((f) => f.cards.join('+')).join(' | ')}`,
    );
    expect(result.available).toBe(true);
  });

  it('every graveyard_return verified finding is a sound k=0 infinite death-trigger loop', () => {
    expect(gyVerified.length).toBeGreaterThan(0);
    for (const f of gyVerified) {
      expect(f.closes).toBe(true);
      expect(f.k).toBe(0);
      expect(f.loopClass).toBe('infinite');
      expect(f.resultTypes).toEqual(['infinite_death_triggers']);
      expect(f.cards.length).toBe(3); // reanimator + partner + free sac
    }
  });

  it('verifies at least 12 of the missing death-return cores (acceptance target ≥12/18)', () => {
    expect(verifiedCores.size).toBeGreaterThanOrEqual(12);
  });

  it('verifies the specifically-named cores', () => {
    // Werefox Bodyguard ×2 (with the two unconditional bound≥3 reanimators; the
    // Redemption Choir line is coven-gated → engine, asserted below).
    expect(verifiedCores.has('Sun Titan + Werefox Bodyguard')).toBe(true);
    expect(verifiedCores.has('Angel of Indemnity + Werefox Bodyguard')).toBe(true);
    // Shepherd of the Cosmos + Angelic Renewal (mv 2 ≤ bound 2).
    expect(verifiedCores.has('Shepherd of the Cosmos + Angelic Renewal')).toBe(true);
    // Angel of Indemnity (bound 4) closes with every one of the 9 partners.
    const angelPartners = [...verifiedCores].filter((c) => c.startsWith('Angel of Indemnity + '));
    expect(angelPartners.length).toBeGreaterThanOrEqual(7);
    // Boonweaver / Brotherhood Outcast / Danitha aura lines.
    for (const fetcher of ['Boonweaver Giant', 'Brotherhood Outcast', "Danitha, Benalia's Hope"]) {
      expect([...verifiedCores].some((c) => c.startsWith(`${fetcher} + `))).toBe(true);
    }
  });

  it('abstains on the coven-gated Redemption Choir cores (never verified)', () => {
    // No Redemption Choir core is ever a verified loop (coven guard → the template
    // returns a guarded engine with a null-shortfall deficit, which the deck driver
    // routes to kbGapAbstentions — the existing QE-2 hidden-diagnostic path — so it is
    // never surfaced as a false near-miss either).
    expect(gyVerified.some((f) => f.cards.includes('Redemption Choir'))).toBe(false);
    expect(gyEngines.some((f) => f.cards.includes('Redemption Choir'))).toBe(false);
    // Redemption Choir's 9 partner triples (bound 3, unconditional aside from coven)
    // are enumerated and abstained, so the deck records the abstentions.
    expect(result.counts.kbGapAbstentions).toBeGreaterThanOrEqual(9);
  });

  it('never verifies an aura-restricted fetcher with a non-Aura or a creature partner', () => {
    // Brotherhood Outcast / Boonweaver / Danitha fetch Auras only: never Angelic Renewal
    // (plain Enchantment) and never the exile creatures (Werefox / Fiend Hunter).
    for (const f of gyVerified) {
      const fetcher = f.cards.find((c) =>
        ['Boonweaver Giant', 'Brotherhood Outcast', "Danitha, Benalia's Hope"].includes(c),
      );
      if (!fetcher) continue;
      expect(f.cards).not.toContain('Angelic Renewal');
      expect(f.cards).not.toContain('Werefox Bodyguard');
      expect(f.cards).not.toContain('Fiend Hunter');
    }
  });
});
