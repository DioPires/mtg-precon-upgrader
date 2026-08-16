// Card-price index — types + loader. DEC-516 (DEC-476 Phase 4).
//
// NM-5 requires near-miss completion suggestions to be filterable by price with
// currency selection including EUR (Cardmarket) and USD; DR-5 sets the data
// requirement. The runtime never calls a price API — it reads the committed
// derivative produced by scripts/build_price_index.py:
//   - /data/spellbook/price-index.json        (~1 MB, name-key → [eur, usd])
//   - /data/spellbook/price-index.meta.json    (provenance / freshness, DR-7)
//
// Like the matcher + feature indexes, the price index BYPASSES the deckLoader's
// localStorage envelope (a ~1 MB write risks evicting deck bundles) and is held in
// a module-level in-memory cache, fetched with a corpus-version ?v= buster.

export type Currency = 'eur' | 'usd';

/** Compact price row: [eur, usd] non-foil, either null when unpriced. */
export type PriceRow = [number | null, number | null];

/** Name-key (normalizeName-folded, //-faces aliased) → price row. */
export type PriceIndex = Record<string, PriceRow>;

export interface PriceIndexMeta {
  schema: string;
  source: string;
  sourceUrl: string;
  scryfall_updated_at: string;
  generatedAt: string;
  currencies: Currency[];
  keyCount: number;
  pricedEur: number;
  pricedUsd: number;
  note?: string;
}

async function fetchJson<T>(url: string, fetchImpl: typeof fetch): Promise<T | null> {
  const r = await fetchImpl(url);
  if (r.status === 404) return null;
  if (!r.ok) throw new Error(`${url}: HTTP ${r.status}`);
  return (await r.json()) as T;
}

let metaCache: PriceIndexMeta | null = null;
let metaInflight: Promise<PriceIndexMeta | null> | null = null;
let indexCache: PriceIndex | null = null;
let indexInflight: Promise<PriceIndex | null> | null = null;

/** Cheap freshness read (DR-7) — a few hundred bytes, no 1 MB download. */
export function loadPriceIndexMeta(
  fetchImpl: typeof fetch = fetch,
): Promise<PriceIndexMeta | null> {
  if (metaCache) return Promise.resolve(metaCache);
  if (metaInflight) return metaInflight;
  metaInflight = (async () => {
    const meta = await fetchJson<PriceIndexMeta>('/data/spellbook/price-index.meta.json', fetchImpl);
    if (meta) metaCache = meta;
    return meta;
  })().finally(() => {
    metaInflight = null;
  });
  return metaInflight;
}

/** Full price index — in-memory only, freshness cache-buster, never localStorage. */
export function loadPriceIndex(fetchImpl: typeof fetch = fetch): Promise<PriceIndex | null> {
  if (indexCache) return Promise.resolve(indexCache);
  if (indexInflight) return indexInflight;
  indexInflight = (async () => {
    const meta = await loadPriceIndexMeta(fetchImpl);
    const v = encodeURIComponent(meta?.scryfall_updated_at ?? 'unknown');
    const index = await fetchJson<PriceIndex>(`/data/spellbook/price-index.json?v=${v}`, fetchImpl);
    if (index) indexCache = index;
    return index;
  })().finally(() => {
    indexInflight = null;
  });
  return indexInflight;
}

/** Look up one currency's price for a normalized name-key, or null. */
export function priceOf(
  index: PriceIndex | null,
  nameKey: string,
  currency: Currency,
): number | null {
  const row = index?.[nameKey];
  if (!row) return null;
  return currency === 'eur' ? row[0] : row[1];
}

/** Test-only: drop in-memory caches. */
export function _resetPriceCaches(): void {
  metaCache = null;
  metaInflight = null;
  indexCache = null;
  indexInflight = null;
}
