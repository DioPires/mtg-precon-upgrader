// Computed near-miss completion — DEC-516 (DEC-476 Phase 4, NM-1..NM-7).
//
// The mechanistic recommendation engine (NM-7): given a decklist, find pool cards
// that CLOSE the deck's near-misses. Two computed tiers, mirroring the epistemic
// structure (NM-1):
//   • Tier C (speculative) — dangling half-edges in the deck's provides/wants
//     graph (a deck feature whose compatible partner feature nothing in the deck
//     carries), paired with pool cards that carry that partner feature. Adding the
//     card forms the coupling the Tier-C synergy engine would then display, so the
//     completion is consistent with synergyMatch.ts by construction.
//   • Tier B (computed) — a candidate loop that fails closure by a concrete numeric
//     deficit (from the Phase-3 verifier's deficit vectors), paired with pool cards
//     whose contribution closes that resource leak (NM-2 is honoured upstream: the
//     deficit IS the verifier's event-trace-aware output; here we cover it with
//     features known to supply the leaked resource). Tier-B deficits are supplied by
//     the caller: fleet mode reads the precomputed tier-b-loops.json engines; paste
//     mode computes them live via comboVerify.verifyDeck (DEC-516). When the caller
//     passes no engines (index unavailable) Tier-B completion is skipped.
//
// The search runs client-side over the committed full-coverage KB feature index
// (the deployed KB projection): per-hole cost linear in pool size, pure precomputed-
// vector matching, no generative calls and no "add each card and re-analyze" brute
// force (NM-4). Suggestions are filterable by color identity, format legality, price
// (EUR/USD), and — optionally — an owned collection (NM-5 / OQ-1). Near-miss stays a
// REPORT: nothing here edits or hosts a deck (NG5).

import type { FeatureIndex, SynergyConfig } from '../data/synergy';
import type { PriceIndex, Currency, PriceRow } from '../data/prices';
import type { TierBFinding } from '../data/tierB';
import { nameKeys, normalizeName } from './synergyMatch';

// ─── Distance-to-closure (PRD 6.6) ───────────────────────────────────────────────
//
// A metric over near-misses, monotone in (number of missing pieces, deficit
// magnitude), such that "missing 1 generic mana per iteration" ranks CLOSER than
// "missing an entire engine piece" (6.6 worked example). Missing whole pieces
// dominates; a pure numeric deficit (all pieces present, a resource leaks) contributes
// a smaller-than-one term so it always ranks ahead of a missing-piece near-miss.
const DIST_SMOOTH = 4;

export function distanceToClosure(missingPieces: number, deficitMagnitude: number): number {
  const mag = Math.max(0, deficitMagnitude);
  return missingPieces + mag / (mag + DIST_SMOOTH);
}

// ─── Deficit-resource → closer-feature map (Tier-B, NM-3) ─────────────────────────
//
// Maps a verifier deficit resource to the ontology features that close it, ordered
// strongest-closer-first, including ambient modifiers as first-class closers (NM-3).
// Conservative and disclosed (NM-2, provenance-gate spirit): the only concrete numeric
// deficit the Phase-3 verifier emits over the fleet is a per-iteration `mana` leak, and
// only PER-ITERATION amplifiers/reducers can close it — a trigger doubler (amplifies the
// mana trigger every iteration) or a cost reduction (cheaper cost every iteration). A
// one-shot mana rock (`mana_add`) does not change the per-iteration net, so it is NOT a
// closer here; including it would inflate the tier past what the model supports.
const RESOURCE_CLOSERS: Record<string, string[]> = {
  mana: ['trigger_doubler', 'cost_reduction'],
};

// ─── Types ────────────────────────────────────────────────────────────────────────

export interface CompletionFilters {
  /** Deck color identity, e.g. "BG" / "C" / "WUBRG". Completers must fit within it. */
  deckColorIdentity: string;
  currency: Currency;
  /** Max price in the selected currency; null = no cap. Unpriced cards pass. */
  maxPrice: number | null;
  /** OQ-1: restrict to owned cards. Requires `ownedKeys`. */
  ownedOnly: boolean;
  /** Normalized name-keys of the owned collection (OQ-1). */
  ownedKeys?: Set<string> | null;
}

export interface CompletionCard {
  name: string;
  ci: string;
  /** Price in the selected currency, or null when unpriced. */
  price: number | null;
  /** True when the owned collection is present AND contains this card. */
  owned: boolean | null;
}

export interface CompletionCoupling {
  deckFeature: string;
  completerFeature: string;
  label: string;
  economy: string;
  magnitude: number;
  signal: number;
}

export interface TierCCompletion {
  card: CompletionCard;
  couplings: CompletionCoupling[];
  economies: string[];
  distance: number;
  band: 'strong' | 'speculative';
}

export interface TierBCompletion {
  card: CompletionCard;
  /** The candidate loop this completes (the engine's cards). */
  loopCards: string[];
  resource: string;
  shortfall: number;
  /** The completer feature that covers the leak, with its human label. */
  closerFeature: string;
  closerLabel: string;
  distance: number;
}

export interface CompletionCounts {
  /** Pool cards that carry ≥1 dangling-target feature, before filters. */
  tierCConsidered: number;
  tierCTotal: number;
  tierC: number;
  tierBTotal: number;
  tierB: number;
  /** Suggestions dropped by each filter (for honest disclosure). */
  droppedByColor: number;
  droppedByPrice: number;
  droppedByOwned: number;
}

export interface CompletionReport {
  deckColorIdentity: string;
  poolSize: number;
  currency: Currency;
  tierC: TierCCompletion[];
  tierB: TierBCompletion[];
  /** True when the caller supplied engine deficits (fleet precompute or the paste
   * verifier); false only when the Tier-B verifier data is unavailable. */
  tierBAvailable: boolean;
  counts: CompletionCounts;
  elapsedMs: number;
}

export interface CompletionOptions {
  filters: CompletionFilters;
  prices: PriceIndex | null;
  /** Engine deficits: fleet reads tier-b-loops.json; paste computes them via
   * comboVerify.verifyDeck (DEC-516). Absent/null ⇒ Tier-B completion skipped. */
  engines?: TierBFinding[] | null;
  /** Result caps (NF-4). */
  tierCCap?: number;
  tierBCap?: number;
  /** Max couplings shown per Tier-C completer. */
  couplingsPerCard?: number;
}

const TIER_C_CAP = 60;
const TIER_B_CAP = 40;
const COUPLINGS_PER_CARD = 6;

// ─── Lean pool projection ─────────────────────────────────────────────────────────

/** Collapsed feature → max magnitude (provides ∪ wants ∪ ambient), matching
 * synergyMatch.toFeatureMap so a completion forms the pair the engine would show. */
function toFeatureMap(card: FeatureIndex['cards'][string]): Map<string, number> {
  const out = new Map<string, number>();
  for (const field of [card.p, card.w, card.a]) {
    if (!field) continue;
    for (const [f, m] of field) {
      const mag = m ?? 1;
      const prev = out.get(f);
      out.set(f, prev === undefined ? mag : Math.max(prev, mag));
    }
  }
  return out;
}

function round4(x: number): number {
  return Math.round(x * 1e4) / 1e4;
}

// ─── Color identity ────────────────────────────────────────────────────────────────

/** Letters of a color-identity string, dropping the colorless marker. */
function ciLetters(ci: string): Set<string> {
  const out = new Set<string>();
  for (const ch of ci.toUpperCase()) {
    if (ch === 'W' || ch === 'U' || ch === 'B' || ch === 'R' || ch === 'G') out.add(ch);
  }
  return out;
}

/** A card fits a deck iff every colored pip in its identity is in the deck's. */
function ciWithin(cardCi: string, deckCi: Set<string>): boolean {
  for (const ch of ciLetters(cardCi)) if (!deckCi.has(ch)) return false;
  return true;
}

/** Derive a deck's color identity from resolved pool cards (paste-mode fallback
 * when the caller has no declared identity). Union of every card's identity. */
export function deriveColorIdentity(names: string[], index: FeatureIndex): string {
  const nameToOid = buildNameToOid(index);
  const deck = new Set<string>();
  for (const raw of names) {
    for (const k of nameKeys(raw)) {
      const oid = nameToOid.get(k);
      if (oid) {
        for (const ch of ciLetters(index.cards[oid]?.ci ?? '')) deck.add(ch);
        break;
      }
    }
  }
  return [...'WUBRG'].filter((c) => deck.has(c)).join('') || 'C';
}

function buildNameToOid(index: FeatureIndex): Map<string, string> {
  const m = new Map<string, string>();
  for (const [oid, row] of Object.entries(index.cards)) {
    for (const k of nameKeys(row.n)) if (!m.has(k)) m.set(k, oid);
  }
  return m;
}

// ─── Price / owned annotation ────────────────────────────────────────────────────

function priceFromRow(row: PriceRow | undefined, currency: Currency): number | null {
  if (!row) return null;
  return currency === 'eur' ? row[0] : row[1];
}

/** Apply the price cap. Unpriced cards PASS (we cannot exclude on unknown price). */
function passesPrice(price: number | null, maxPrice: number | null): boolean {
  if (maxPrice == null || price == null) return true;
  return price <= maxPrice;
}

// ─── Main analysis ──────────────────────────────────────────────────────────────

export function analyzeCompletions(
  deckNames: string[],
  index: FeatureIndex,
  config: SynergyConfig,
  opts: CompletionOptions,
): CompletionReport {
  const t0 = perfNow();
  const { filters } = opts;
  const deckCi = ciLetters(filters.deckColorIdentity);
  const currency = filters.currency;
  const prices = opts.prices;
  const nameToOid = buildNameToOid(index);

  // Resolve the deck: in-deck oracle ids + collapsed feature presence/histogram.
  const deckOids = new Set<string>();
  const deckFeatureCount = new Map<string, number>(); // feature → # deck cards carrying it
  const deckFeatureMag = new Map<string, number>(); // feature → max magnitude in deck
  for (const raw of deckNames) {
    let oid: string | undefined;
    for (const k of nameKeys(raw)) {
      const hit = nameToOid.get(k);
      if (hit) {
        oid = hit;
        break;
      }
    }
    if (!oid || deckOids.has(oid)) continue;
    deckOids.add(oid);
    const feats = toFeatureMap(index.cards[oid]);
    for (const [f, m] of feats) {
      deckFeatureCount.set(f, (deckFeatureCount.get(f) ?? 0) + 1);
      deckFeatureMag.set(f, Math.max(deckFeatureMag.get(f) ?? 0, m));
    }
  }

  const compat = buildCompat(config);
  const noise = buildNoisePairs(config);
  const constants = config.constants;

  // Dangling targets: feature G compatible with some deck feature F, where nothing
  // in the deck carries G and (F,G) is not a noise pair. Each target records its
  // best in-deck partner (highest deck-fit) for scoring + display.
  interface Dangle {
    partnerF: string;
    partnerMag: number;
    deckFit: number; // fraction of deck carrying F, in (0,1]
    signal: number; // magnitude × (idf[F]+idf[G])
  }
  const maxDeckFeatCount = Math.max(1, ...deckFeatureCount.values());
  const dangle = new Map<string, Dangle>();
  for (const [f, fCount] of deckFeatureCount) {
    const partners = compat.get(f);
    if (!partners) continue;
    const idfF = config.idf[f] ?? constants.IDF_FALLBACK;
    for (const g of partners) {
      if (f === g) continue;
      if (deckFeatureCount.has(g)) continue; // already satisfied in-deck
      if (noise.has(pairKey(f, g))) continue;
      const idfG = config.idf[g] ?? constants.IDF_FALLBACK;
      const magnitude = deckFeatureMag.get(f) ?? 1;
      const signal = round4(magnitude * (idfF + idfG));
      const deckFit = fCount / maxDeckFeatCount;
      const prev = dangle.get(g);
      // Keep the strongest partner F for this target G (highest deck-fit, then signal).
      if (!prev || deckFit > prev.deckFit || (deckFit === prev.deckFit && signal > prev.signal)) {
        dangle.set(g, { partnerF: f, partnerMag: magnitude, deckFit, signal });
      }
    }
  }

  // ── Tier-C completion: scan the pool once (NM-4 linear) ──
  let tierCConsidered = 0;
  let droppedByColor = 0;
  let droppedByPrice = 0;
  let droppedByOwned = 0;
  const tierCScored: { c: TierCCompletion; score: number }[] = [];

  for (const [oid, row] of Object.entries(index.cards)) {
    if (deckOids.has(oid)) continue;
    const feats = toFeatureMap(row);
    if (feats.size === 0) continue;
    // Collect the couplings this card would add (its features that are dangling targets).
    let matched: CompletionCoupling[] | null = null;
    for (const [g, mag] of feats) {
      const d = dangle.get(g);
      if (!d) continue;
      (matched ??= []).push({
        deckFeature: d.partnerF,
        completerFeature: g,
        label: `${config.labels[d.partnerF] ?? d.partnerF} ↔ ${config.labels[g] ?? g}`,
        economy: config.economies[g] ?? config.economies[d.partnerF] ?? '',
        magnitude: Math.max(mag, d.partnerMag),
        signal: d.signal,
      });
    }
    if (!matched) continue;
    tierCConsidered += 1;

    // Filters (NM-5). Count each drop reason for honest disclosure.
    if (!ciWithin(row.ci, deckCi)) {
      droppedByColor += 1;
      continue;
    }
    const price = priceFromRow(prices?.[normalizeName(row.n)], currency);
    if (!passesPrice(price, filters.maxPrice)) {
      droppedByPrice += 1;
      continue;
    }
    const owned = ownedFlag(row.n, filters);
    if (filters.ownedOnly && owned === false) {
      droppedByOwned += 1;
      continue;
    }

    matched.sort((a, b) => b.signal - a.signal || cmpStr(a.completerFeature, b.completerFeature));
    const weight = round4(matched.reduce((s, m) => s + m.signal, 0));
    const magSig = 1 - 1 / (1 + Math.max(weight, 0) / constants.EDGE_WEIGHT_SCALE);
    const fit = matched.reduce((s, m) => s + (dangle.get(m.completerFeature)?.deckFit ?? 0), 0) /
      matched.length;
    const denom = constants.W_MAGNITUDE + constants.W_DECK_FIT;
    const composite = round4((constants.W_MAGNITUDE * magSig + constants.W_DECK_FIT * fit) / denom);
    const economies = [...new Set(matched.map((m) => m.economy).filter(Boolean))].sort(cmpStr);
    tierCScored.push({
      score: composite,
      c: {
        card: { name: row.n, ci: row.ci, price, owned },
        couplings: matched.slice(0, opts.couplingsPerCard ?? COUPLINGS_PER_CARD),
        economies,
        distance: distanceToClosure(1, 0),
        band: composite >= constants.STRONG_BAND_CUT ? 'strong' : 'speculative',
      },
    });
  }
  tierCScored.sort(
    (a, b) => b.score - a.score || cmpStr(a.c.card.name, b.c.card.name),
  );
  const tierCTotal = tierCScored.length;
  const tierC = tierCScored.slice(0, opts.tierCCap ?? TIER_C_CAP).map((s) => s.c);

  // ── Tier-B completion: cover the verifier's deficit vectors (fleet precompute
  // or paste-mode comboVerify.verifyDeck) ──
  const engines = opts.engines ?? null;
  const tierBAvailable = engines != null;
  const tierBAll: { b: TierBCompletion; sort: number; pri: number }[] = [];
  if (engines) {
    for (const eng of engines) {
      for (const d of eng.deficit) {
        if (d.shortfall == null || d.shortfall <= 0) continue; // KB-gap abstentions skipped
        const closerFeatures = RESOURCE_CLOSERS[d.resource];
        if (!closerFeatures) continue;
        const loopKeys = new Set<string>();
        for (const cn of eng.cards) for (const k of nameKeys(cn)) loopKeys.add(k);
        const dist = distanceToClosure(0, d.shortfall);
        const seen = new Set<string>();
        for (const [oid, row] of Object.entries(index.cards)) {
          if (deckOids.has(oid)) continue;
          // A closer must SUPPLY the feature (provides or ambient — doublers
          // and cost reducers are ambient/static effects in the KB). A card
          // that merely WANTS the feature does not close the leak, so `w` is
          // excluded. closerFeatures is strongest-first; take the strongest.
          const supplies = new Set(
            [...(row.p ?? []), ...(row.a ?? [])].map(([f]) => f),
          );
          const closer = closerFeatures.find((cf) => supplies.has(cf));
          if (!closer) continue;
          // Filters.
          if (!ciWithin(row.ci, deckCi)) continue;
          const price = priceFromRow(prices?.[normalizeName(row.n)], currency);
          if (!passesPrice(price, filters.maxPrice)) continue;
          const owned = ownedFlag(row.n, filters);
          if (filters.ownedOnly && owned === false) continue;
          const key = normalizeName(row.n);
          if (loopKeys.has(key) || seen.has(key)) continue;
          seen.add(key);
          tierBAll.push({
            sort: dist,
            pri: closerFeatures.indexOf(closer),
            b: {
              card: { name: row.n, ci: row.ci, price, owned },
              loopCards: eng.cards,
              resource: d.resource,
              shortfall: d.shortfall,
              closerFeature: closer,
              closerLabel: config.labels[closer] ?? closer,
              distance: dist,
            },
          });
        }
      }
    }
  }
  // Rank near-misses by distance-to-closure (NM-6), then by completed-finding strength
  // (strongest closer first — a trigger doubler reaches strict gain more reliably than a
  // cost reduction), then by name for stability.
  tierBAll.sort(
    (a, b) => a.sort - b.sort || a.pri - b.pri || cmpStr(a.b.card.name, b.b.card.name),
  );
  const tierBTotal = tierBAll.length;
  const tierB = tierBAll.slice(0, opts.tierBCap ?? TIER_B_CAP).map((s) => s.b);

  return {
    deckColorIdentity: filters.deckColorIdentity,
    poolSize: Object.keys(index.cards).length,
    currency,
    tierC,
    tierB,
    tierBAvailable,
    counts: {
      tierCConsidered,
      tierCTotal,
      tierC: tierC.length,
      tierBTotal,
      tierB: tierB.length,
      droppedByColor,
      droppedByPrice,
      droppedByOwned,
    },
    elapsedMs: round4(perfNow() - t0),
  };
}

// ─── Helpers ─────────────────────────────────────────────────────────────────────

function ownedFlag(name: string, filters: CompletionFilters): boolean | null {
  if (!filters.ownedKeys) return null;
  for (const k of nameKeys(name)) if (filters.ownedKeys.has(k)) return true;
  return false;
}

function buildCompat(config: SynergyConfig): Map<string, Set<string>> {
  const compat = new Map<string, Set<string>>();
  for (const [k, vs] of Object.entries(config.compat)) compat.set(k, new Set(vs));
  return compat;
}

function buildNoisePairs(config: SynergyConfig): Set<string> {
  const out = new Set<string>();
  for (const pair of config.noisePairs) out.add([...pair].sort(cmpStr).join(' '));
  return out;
}

function pairKey(a: string, b: string): string {
  return a < b ? `${a} ${b}` : `${b} ${a}`;
}

function cmpStr(a: string, b: string): number {
  return a < b ? -1 : a > b ? 1 : 0;
}

function perfNow(): number {
  return typeof performance !== 'undefined' && performance.now ? performance.now() : Date.now();
}

const CSV_HEADER_WORDS = new Set(['name', 'card', 'card name', 'count', 'quantity', 'qty']);

/** Extract the card name from one CSV row. Handles the ManaBox name-first export
 * (`Name,Set,...`), count-first exports (`1,Card,Set`), and quoted names that
 * contain commas (`1,"Borrowing 100,000 Arrows",...`). */
function csvCardName(line: string): string {
  // A leading quoted field.
  if (line.startsWith('"')) {
    const m = line.match(/^"([^"]+)"/);
    if (m) return m[1].trim();
  }
  const first = line.split(',')[0].trim();
  // Count-first format: the first field is a bare quantity — take the second field.
  if (/^\d+$/.test(first)) {
    const rest = line.slice(line.indexOf(',') + 1);
    const q = rest.match(/^"([^"]+)"/);
    return (q ? q[1] : rest.split(',')[0]).trim();
  }
  return first;
}

/** Parse a pasted collection into normalized name-keys (OQ-1). Accepts decklist
 * lines (quantities, set/collector suffixes) and CSV exports (ManaBox / deckbox).
 * Returns null when the text has no usable names. */
export function parseOwnedCollection(text: string): Set<string> | null {
  const keys = new Set<string>();
  for (const rawLine of text.split(/\r?\n/)) {
    let line = rawLine.trim();
    if (!line || line.startsWith('#') || line.startsWith('//')) continue;
    if (line.includes(',')) {
      line = csvCardName(line);
      if (CSV_HEADER_WORDS.has(line.toLowerCase())) continue;
    }
    line = line.replace(/^(\d+)\s*[xX]?\s+/, '');
    line = line.replace(/\s+\([0-9A-Za-z]{2,6}\)(\s+[0-9A-Za-z-]+)?\s*(\*[^*]+\*)?\s*$/, '').trim();
    if (!line || !/[a-zA-Z]/.test(line)) continue;
    for (const k of nameKeys(line)) keys.add(k);
  }
  return keys.size > 0 ? keys : null;
}
