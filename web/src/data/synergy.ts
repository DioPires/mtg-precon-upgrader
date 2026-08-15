// Tier-C synergy data — types + loaders. DEC-491 (DEC-476 Phase 2).
//
// The runtime never derives synergy constants; it consumes committed artifacts
// produced by the Python engine (scripts/combo_synergy_lib.py + the fleet
// build):
//   - shared config   /data/combo-kb/synergy-config.json        (both modes)
//   - feature index    /data/combo-kb/feature-index.json (~3.3 MB, paste mode)
//   - per-deck         /data/commanders/{id}/synergy-candidates.json (fleet)
//
// The feature index deliberately BYPASSES the deckLoader's localStorage envelope
// (localStorage caps ~5 MB per origin; a 3.3 MB write would silently fail and
// could evict deck bundles). It is held in a module-level in-memory cache and
// fetched with a corpus-version ?v= buster — mirrors data/spellbook.ts exactly.

// ─── Feature index (paste mode) ─────────────────────────────────────────────────

/** Compact per-card feature projection. p/w/a = provides/wants/ambient, each a
 * list of [feature, magnitude]. Absent when the card carries no features. */
export interface FeatureIndexCard {
  n: string;
  ci: string;
  p?: [string, number][];
  w?: [string, number][];
  a?: [string, number][];
}

export interface FeatureIndex {
  cards: Record<string, FeatureIndexCard>;
}

export interface FeatureIndexMeta {
  schema: string;
  corpusVersion: string;
  ontologyVersion: string;
  extractorVersion: string;
  cardCount: number;
  featurefulCount: number;
  generatedAt: string;
  note?: string;
}

// ─── Shared synergy config (mirror of data/combo-kb/synergy-config.json) ─────────

export interface SynergyConstants {
  EDGE_MIN_SIGNAL: number;
  EDGE_WEIGHT_SCALE: number;
  DEEP_EDGE_LIMIT: number;
  STRONG_BAND_CUT: number;
  PAIR_CAP: number;
  TRIPLE_CAP: number;
  CYCLE_CAP: number;
  W_MAGNITUDE: number;
  W_DECK_FIT: number;
  W_CROWD_PRIOR: number;
  IDF_FALLBACK: number;
}

export interface SynergyConfig {
  schema: string;
  ontologyVersion?: string;
  /** Symmetric ``pairs_with`` relation: feature id → compatible feature ids. */
  compat: Record<string, string[]>;
  /** Inverse document frequency per feature. */
  idf: Record<string, number>;
  /** Feature id → human label. */
  labels: Record<string, string>;
  /** Feature id → economy tag. */
  economies: Record<string, string>;
  /** Unordered feature pairs excluded from Tier-C display. */
  noisePairs: string[][];
  constants: SynergyConstants;
}

// ─── Rendered candidates (fleet file + paste-engine output) ──────────────────────

export interface SynergyEdge {
  from: string;
  to: string;
  fromFeature: string;
  toFeature: string;
  magnitude: number;
  label: string;
}

export type SynergyBand = 'strong' | 'speculative';

export interface SynergyCandidate {
  cards: string[];
  edges: SynergyEdge[];
  economies: string[];
  band: SynergyBand;
}

export interface SynergyCounts {
  pairs: number;
  pairsTotal: number;
  triples: number;
  triplesTotal: number;
  cycles: number;
  cyclesTotal: number;
  uncovered: number;
}

export interface DeckSynergyCandidates {
  meta: {
    deckId: string;
    source: string;
    corpusVersion: string;
    generatedAt: string;
    matchingModel: string;
    ontologyVersion?: string;
    note?: string;
    /** True in fleet mode (EDHREC crowd prior folded into ranking). */
    crowdPriorApplied: boolean;
    /** True when the deep scan was restricted to the strongest couplings. */
    deepFocused: boolean;
  };
  commander: string[];
  counts: SynergyCounts;
  uncovered: string[];
  pairs: SynergyCandidate[];
  triples: SynergyCandidate[];
  cycles: SynergyCandidate[];
}

// ─── Loaders (mirror data/spellbook.ts) ──────────────────────────────────────────

async function fetchJson<T>(url: string, fetchImpl: typeof fetch): Promise<T | null> {
  const r = await fetchImpl(url);
  if (r.status === 404) return null;
  if (!r.ok) throw new Error(`${url}: HTTP ${r.status}`);
  return (await r.json()) as T;
}

let metaCache: FeatureIndexMeta | null = null;
let metaInflight: Promise<FeatureIndexMeta | null> | null = null;
let indexCache: FeatureIndex | null = null;
let indexInflight: Promise<FeatureIndex | null> | null = null;
let configCache: SynergyConfig | null = null;
let configInflight: Promise<SynergyConfig | null> | null = null;

/** Cheap corpus-version read — a few hundred bytes, no 3.3 MB download. */
export function loadFeatureIndexMeta(
  fetchImpl: typeof fetch = fetch,
): Promise<FeatureIndexMeta | null> {
  if (metaCache) return Promise.resolve(metaCache);
  if (metaInflight) return metaInflight;
  metaInflight = (async () => {
    const meta = await fetchJson<FeatureIndexMeta>(
      '/data/combo-kb/feature-index.meta.json',
      fetchImpl,
    );
    if (meta) metaCache = meta;
    return meta;
  })().finally(() => {
    metaInflight = null;
  });
  return metaInflight;
}

/** Full feature index — in-memory only, corpus-version cache-buster, never localStorage. */
export function loadFeatureIndex(fetchImpl: typeof fetch = fetch): Promise<FeatureIndex | null> {
  if (indexCache) return Promise.resolve(indexCache);
  if (indexInflight) return indexInflight;
  indexInflight = (async () => {
    const meta = await loadFeatureIndexMeta(fetchImpl);
    const v = encodeURIComponent(meta?.corpusVersion ?? 'unknown');
    const index = await fetchJson<FeatureIndex>(
      `/data/combo-kb/feature-index.json?v=${v}`,
      fetchImpl,
    );
    if (index) indexCache = index;
    return index;
  })().finally(() => {
    indexInflight = null;
  });
  return indexInflight;
}

/** Shared synergy config (small; in-memory cache). */
export function loadSynergyConfig(fetchImpl: typeof fetch = fetch): Promise<SynergyConfig | null> {
  if (configCache) return Promise.resolve(configCache);
  if (configInflight) return configInflight;
  configInflight = (async () => {
    const cfg = await fetchJson<SynergyConfig>('/data/combo-kb/synergy-config.json', fetchImpl);
    if (cfg) configCache = cfg;
    return cfg;
  })().finally(() => {
    configInflight = null;
  });
  return configInflight;
}

/** Test-only: drop in-memory caches. */
export function _resetSynergyCaches(): void {
  metaCache = null;
  metaInflight = null;
  indexCache = null;
  indexInflight = null;
  configCache = null;
  configInflight = null;
}
