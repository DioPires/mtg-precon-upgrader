// Tier-B verified-loop data — types + (fleet) shape. DEC-501 (DEC-476 Phase 3).
//
// The runtime consumes the committed per-deck artifact
// data/commanders/{id}/tier-b-loops.json, produced by the deterministic verifier
// (scripts/combo_verifier_lib.py + scripts/build_tier_b_candidates.py). It is a
// standalone per-deck file like metrics.json / synergy-candidates.json, wired into
// the deck bundle by loader.ts as `tierBLoops`.
//
// Everything here is Tier B — machine-verified UNDER LAÇO'S MODEL (EI-2), never a
// comprehensive-rules proof. Corroborated loops remain Tier A (Commander
// Spellbook); the computed verdict is recorded as corroboration only (DB-7).

/** A per-iteration deficit condition on a loop that does not close (6.6 / DB-4). */
export interface TierBDeficit {
  resource: string;
  /** Numeric per-iteration shortfall, or null for a KB-gap abstention (QE-2). */
  shortfall: number | null;
  note: string;
}

export interface TierBPrerequisites {
  /** PR-3: minimal initial mana stock under the optimal action ordering. */
  minInitialMana: number;
  ordering: string[];
  /** Guard set: zone / timing / control / summoning-sickness / command-zone. */
  guards: string[];
  note: string;
}

export interface TierBProvenance {
  members: { name: string; oracleId: string }[];
  ontologyVersion: string | string[];
  extractorVersion: string | string[];
  corpusVersion: string | string[];
  gate: string;
}

/** A single Tier-B loop verdict rendered for the UI. */
export interface TierBFinding {
  cards: string[];
  closes: boolean;
  template: string;
  loopClass: string; // 'infinite' | 'engine' | ''
  k: number | null;
  band: string; // 'verified' | 'engine' | 'candidate'
  resultTypes: string[];
  finiteZoneBound: { zone: string; perIteration?: number; bound?: number; note?: string } | null;
  trace: string[];
  deficit: TierBDeficit[];
  prerequisites: TierBPrerequisites;
  provenance: TierBProvenance;
  /** Non-null => the provenance gate demoted a would-be Tier-B loop to Tier C. */
  tierCapped: string | null;
  /** True when this loop is also in the curated corpus (Tier A corroboration). */
  corroboration: boolean;
}

export interface TierBCounts {
  verifiedCorroborated: number;
  verifiedNovel: number;
  engines: number;
  capped: number;
  candidatesConsidered: number;
  curatedPresent: number;
  kbGapAbstentions: number;
}

export interface DeckTierBLoops {
  meta: {
    deckId: string;
    source: string;
    corpusVersion: string;
    ontologyVersion?: string;
    extractorVersion?: string;
    generatedAt: string;
    matchingModel: string;
    closureModel: string;
    provenanceGate: string;
    crowdPriorApplied: boolean;
    enumBudgetHit: boolean;
    note: string;
  };
  commander: string[];
  counts: TierBCounts;
  /** Curated loops the verifier also closes — presented at Tier A, corroborated. */
  verifiedCorroborated: TierBFinding[];
  /** Novel verified loops (NOT in the curated corpus). Rare by design (DC-6). */
  verifiedNovel: TierBFinding[];
  /** Value engines / near-misses with a concrete deficit vector (NM-1 Tier B). */
  engines: TierBFinding[];
  /** Would-be Tier-B loops demoted to Tier C by the provenance gate (plan 6b). */
  capped: TierBFinding[];
}
