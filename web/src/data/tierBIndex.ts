// Tier-B verifier index — types + loader. DEC-516 (DEC-476 Phase 4).
//
// Paste mode runs the Phase-3 deterministic Tier-B verifier client-side
// (web/src/lib/comboVerify.ts) so a pasted decklist gets the same "verified under
// the model" loop results the fleet precompute (tier-b-loops.json) ships. That
// verifier needs the loop-relevant RAW KB fields the lean feature index drops
// (per-item provenance, events_emitted, activated costs, triggers, guards). This
// module loads the committed derivative produced by scripts/build_tier_b_index.py:
//   - /data/combo-kb/tier-b-index.json  (~4 MB; one record per candidate-member card)
//
// Like the matcher / feature / price indexes it BYPASSES the deckLoader localStorage
// envelope (a multi-MB write risks evicting deck bundles) and is held in a
// module-level in-memory cache, fetched once with a corpus-version ?v= buster. The
// corpus version is shared with the feature index (same KB build), so we reuse its
// meta for the buster rather than shipping a second meta file.

import { loadFeatureIndexMeta } from './synergy';

/** A loop-relevant KB item, ungated (provenance retained so the mirror gates). */
export interface TBItem {
  /** feature id */
  f: string;
  /** provenance: deterministic | human-reviewed | llm | community-tag */
  p: string;
  /** magnitude (default 1 when absent) */
  m?: number;
  /** economy (e.g. "mana", "sacrifice"); absent when empty */
  e?: string;
  /** evidence fragment — present only on mana_add items (color/amplifier tests) */
  v?: string;
}

export interface TBTrigger {
  t: string;
  p: string;
}

export interface TBGuard {
  g: string;
  p: string;
}

export interface TBCost {
  c: string;
  p: string;
}

/** Compact per-card record. All fields optional beyond name + the three item lists;
 * defaults reconstruct the full MemberModel projection in comboVerify.ts. */
export interface TBRecord {
  n: string;
  pr: TBItem[];
  wa: TBItem[];
  am: TBItem[];
  ci?: string[];
  tr?: TBTrigger[];
  gu?: TBGuard[];
  ev?: string[];
  co?: { mc?: string; ac?: TBCost[] };
  /** untaps_other — the N1 self-scope guard, precomputed gate-blind. */
  uo?: boolean;
  /** tier_b_capped — exact provenance-gate cap over the FULL entry. */
  cap?: string[];
}

export interface TierBIndexMeta {
  schema: string;
  ontologyVersion: string;
  extractorVersion: string;
  corpusVersion: string;
  generatedAt: string;
  recordCount: number;
  memberCount: number;
  bystanderCount: number;
  provenanceGate: string;
  note?: string;
}

export interface TierBIndex {
  meta: TierBIndexMeta;
  /** oracle_id → full loop-relevant record. Includes candidate-member seeds AND
   * non-seed combo-universe bystanders (so a curated combo resolves with every
   * piece — a bystander's activated costs + guards feed the prerequisite math). The
   * enumerator gates seeds by feature, so bystanders only ever join a curated group. */
  cards: Record<string, TBRecord>;
  /** name key (normalizeName-folded, //-faces aliased) → oracle_id (first-wins). */
  names: Record<string, string>;
}

async function fetchJson<T>(url: string, fetchImpl: typeof fetch): Promise<T | null> {
  const r = await fetchImpl(url);
  if (r.status === 404) return null;
  if (!r.ok) throw new Error(`${url}: HTTP ${r.status}`);
  return (await r.json()) as T;
}

let indexCache: TierBIndex | null = null;
let indexInflight: Promise<TierBIndex | null> | null = null;

/** Full Tier-B verifier index — in-memory only, corpus-version cache-buster (shared
 * with the feature index), never localStorage. */
export function loadTierBIndex(fetchImpl: typeof fetch = fetch): Promise<TierBIndex | null> {
  if (indexCache) return Promise.resolve(indexCache);
  if (indexInflight) return indexInflight;
  indexInflight = (async () => {
    const meta = await loadFeatureIndexMeta(fetchImpl);
    const v = encodeURIComponent(meta?.corpusVersion ?? 'unknown');
    const index = await fetchJson<TierBIndex>(
      `/data/combo-kb/tier-b-index.json?v=${v}`,
      fetchImpl,
    );
    if (index) indexCache = index;
    return index;
  })().finally(() => {
    indexInflight = null;
  });
  return indexInflight;
}
