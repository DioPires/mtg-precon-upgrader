// DEC-501 (DEC-476 Phase 3) — Tier-B report/export unit tests.
//
// Pins the epistemic-integrity behaviour on the shipping surface: tier labels and
// the model-conditional qualifier must survive the plain-text export (EI-2 / EI-4:
// tier inflation in any export is release-blocking), corroborated loops export as
// Tier A (DB-7), novel loops as "verified under the model", and the (k, bound)
// classification renders correctly.

import { describe, it, expect } from 'vitest';
import { buildPlainTextExport, loopClassLabel, type ComboReport } from '../../lib/spellbookReport';
import type { TierBFinding } from '../../data/tierB';

function finding(over: Partial<TierBFinding>): TierBFinding {
  return {
    cards: ['Basalt Monolith', 'Forsaken Monument'],
    closes: true,
    template: 'untap_mana',
    loopClass: 'infinite',
    k: 0,
    band: 'verified',
    resultTypes: ['infinite_mana:colorless'],
    finiteZoneBound: null,
    trace: ['tap → add 3', 'net +1 mana'],
    deficit: [],
    prerequisites: { minInitialMana: 0, ordering: [], guards: ['summoning_sick'], note: 'n' },
    provenance: {
      members: [], ontologyVersion: '1.0.1', extractorVersion: 'det-1.0.1',
      corpusVersion: 'x', gate: 'deterministic|human-reviewed only',
    },
    tierCapped: null,
    corroboration: false,
    ...over,
  };
}

const baseReport = (over: Partial<ComboReport>): ComboReport => ({
  mode: 'fleet',
  deckLabel: 'Test Deck',
  commander: ['Test Commander'],
  corpusVersion: '2026-08-15',
  included: [],
  nearMisses: [],
  nearMissesTotal: 0,
  cardsAnalyzed: 99,
  cardsTotal: 99,
  unresolved: [],
  ...over,
});

describe('loopClassLabel', () => {
  it('labels an infinite loop k=0', () => {
    expect(loopClassLabel(finding({ loopClass: 'infinite', k: 0 }))).toContain('infinite loop (k=0)');
  });
  it('labels a per-turn value engine k>0', () => {
    expect(loopClassLabel(finding({ loopClass: 'engine', k: 1 }))).toContain('value engine (k=1)');
  });
  it('reports the finite-zone bound as an attribute, not a third class', () => {
    const l = loopClassLabel(
      finding({ loopClass: 'infinite', k: 0, finiteZoneBound: { zone: 'library', bound: 49 } }),
    );
    expect(l).toContain('infinite loop (k=0)');
    expect(l).toContain('bounded by library');
  });
});

describe('buildPlainTextExport — Tier-B (EI-2 / EI-4)', () => {
  it('exports a novel loop as verified UNDER THE MODEL, with the qualifier', () => {
    const txt = buildPlainTextExport(
      baseReport({
        tierB: {
          counts: {
            verifiedCorroborated: 0, verifiedNovel: 1, engines: 0, capped: 0,
            candidatesConsidered: 1, curatedPresent: 0, kbGapAbstentions: 0,
          },
          corroborated: [],
          novel: [finding({ corroboration: false })],
          engines: [],
          capped: [],
          crowdPriorApplied: true,
        },
      }),
    );
    expect(txt).toContain('TIER B');
    expect(txt.toLowerCase()).toContain('verified under laço');
    expect(txt).toContain('[Tier B · verified under the model] Basalt Monolith + Forsaken Monument');
    // EI-3: never an exhaustiveness claim.
    expect(txt).not.toMatch(/contains no combos/i);
  });

  it('exports a corroborated loop as Tier A (DB-7), never inflated to a novel claim', () => {
    const txt = buildPlainTextExport(
      baseReport({
        tierB: {
          counts: {
            verifiedCorroborated: 1, verifiedNovel: 0, engines: 0, capped: 0,
            candidatesConsidered: 1, curatedPresent: 1, kbGapAbstentions: 0,
          },
          corroborated: [finding({ corroboration: true })],
          novel: [],
          engines: [],
          capped: [],
          crowdPriorApplied: true,
        },
      }),
    );
    expect(txt).toContain('[Tier A · computed-corroborated]');
    expect(txt).not.toContain('[Tier B · verified under the model] Basalt Monolith');
  });

  it('discloses provenance-gate caps without labelling them verified (plan 6b)', () => {
    const txt = buildPlainTextExport(
      baseReport({
        tierB: {
          counts: {
            verifiedCorroborated: 0, verifiedNovel: 0, engines: 0, capped: 2,
            candidatesConsidered: 2, curatedPresent: 0, kbGapAbstentions: 0,
          },
          corroborated: [], novel: [], engines: [],
          capped: [finding({ closes: false, tierCapped: 'gate' }), finding({ closes: false })],
          crowdPriorApplied: true,
        },
      }),
    );
    expect(txt).toContain('held at Tier C');
  });
});
