// Commander Spellbook combo data — types + loaders.
//
// DEC-487 (DEC-476 Phase 0). The runtime never calls Commander Spellbook. This
// module reads the committed derivatives produced by
// scripts/sync_spellbook_combos.py:
//   - per-deck   /data/commanders/{id}/spellbook-combos.json  (fleet mode)
//   - matcher    /data/spellbook/matcher-index.json           (paste mode)
//
// The matcher index (~13 MB) deliberately BYPASSES the deckLoader's localStorage
// envelope: localStorage caps at ~5 MB per origin, the write would silently fail
// and could evict the deck bundles. It is held in a module-level in-memory cache
// and fetched with a corpus-version ?v= buster so the browser HTTP cache serves
// it unchanged between corpus updates but refetches when the weekly sync lands.

// ─── Spellbook's per-combo bracket tag (attributed, never Laço's own judgment) ──
// Authoritative labels from the Spellbook backend OpenAPI BracketTagEnum.
export const BRACKET_TAG_LABELS: Record<string, string> = {
  E: 'Exhibition',
  C: 'Core',
  P: 'Powerful',
  O: 'Oddball',
  S: 'Spicy',
  R: 'Ruthless',
  B: 'Banned',
};

export interface SpellbookComboCard {
  name: string;
  mustBeCommander: boolean;
  quantity: number;
  zones: string[];
}

export interface SpellbookComboTemplate {
  name: string;
  query: string;
  quantity?: number;
}

export interface SpellbookPrices {
  tcgplayer?: string;
  cardkingdom?: string;
  cardmarket?: string;
}

/** One curated combo, self-contained (embedded in per-deck files + emitted by paste-mode matching). */
export interface SpellbookCombo {
  id: string;
  permalink: string;
  cards: SpellbookComboCard[];
  templates: SpellbookComboTemplate[];
  produces: string[];
  identity: string;
  bracketTag: string;
  manaNeeded: string;
  manaValueNeeded: number;
  prerequisites: { easy: string; notable: string };
  steps: string;
  notes: string;
  prices: SpellbookPrices;
  popularity: number;
  /** 0 for included; 1-2 for near-misses (count of unmet elements). */
  distance: number;
  /** Present only on near-misses. */
  missing?: { cards: string[]; templates: SpellbookComboTemplate[] };
}

export interface SpellbookDeckCombos {
  meta: {
    deckId: string;
    source: string;
    corpusVersion: string;
    generatedAt: string;
    matchingModel: string;
    nearMissCap?: number;
    nearMissPopularityFloor?: number;
    templateCaveat?: string;
  };
  commander: string[];
  counts: { included: number; nearMisses: number; nearMissesTotal: number };
  included: SpellbookCombo[];
  nearMisses: SpellbookCombo[];
}

// ─── Matcher index (paste mode) ────────────────────────────────────────────────

export interface MatcherMeta {
  source: string;
  sourceUrl: string;
  corpusVersion: string;
  spellbookApiVersion: string;
  generatedAt: string;
  variantCount: number;
  cardCount: number;
  matchingModel: string;
  bracketTagLegend: Record<string, string>;
}

/** Compact matcher row: u=use card ids, c=must-be-commander card ids, r=template
 * ids, p=produced feature ids, i=color identity, b=bracket tag, m=mana value,
 * pop=Spellbook popularity. Ids resolve against the index dictionaries. */
export interface MatcherVariant {
  id: string;
  u: number[];
  c: number[];
  r: number[];
  p: number[];
  i: string;
  b: string;
  m: number;
  pop: number;
}

export interface MatcherIndex {
  meta: MatcherMeta;
  cards: Record<string, { n: string; o: string }>;
  templates: Record<string, { n: string; q: string }>;
  features: Record<string, string>;
  variants: MatcherVariant[];
}

async function fetchJson<T>(url: string, fetchImpl: typeof fetch): Promise<T | null> {
  const r = await fetchImpl(url);
  if (r.status === 404) return null;
  if (!r.ok) throw new Error(`${url}: HTTP ${r.status}`);
  return (await r.json()) as T;
}

let metaCache: MatcherMeta | null = null;
let metaInflight: Promise<MatcherMeta | null> | null = null;
let indexCache: MatcherIndex | null = null;
let indexInflight: Promise<MatcherIndex | null> | null = null;

/** Cheap corpus-version read (DR-7) — a few hundred bytes, no 13 MB download. */
export function loadMatcherMeta(fetchImpl: typeof fetch = fetch): Promise<MatcherMeta | null> {
  if (metaCache) return Promise.resolve(metaCache);
  if (metaInflight) return metaInflight;
  metaInflight = (async () => {
    const meta = await fetchJson<MatcherMeta>('/data/spellbook/matcher-index.meta.json', fetchImpl);
    if (meta) metaCache = meta;
    return meta;
  })().finally(() => {
    metaInflight = null;
  });
  return metaInflight;
}

/** Full matcher index — in-memory only, corpus-version cache-buster, never localStorage. */
export function loadMatcherIndex(fetchImpl: typeof fetch = fetch): Promise<MatcherIndex | null> {
  if (indexCache) return Promise.resolve(indexCache);
  if (indexInflight) return indexInflight;
  indexInflight = (async () => {
    const meta = await loadMatcherMeta(fetchImpl);
    const v = encodeURIComponent(meta?.corpusVersion ?? 'unknown');
    const index = await fetchJson<MatcherIndex>(`/data/spellbook/matcher-index.json?v=${v}`, fetchImpl);
    if (index) indexCache = index;
    return index;
  })().finally(() => {
    indexInflight = null;
  });
  return indexInflight;
}

/** Test-only: drop in-memory caches. */
export function _resetSpellbookCaches(): void {
  metaCache = null;
  metaInflight = null;
  indexCache = null;
  indexInflight = null;
}
