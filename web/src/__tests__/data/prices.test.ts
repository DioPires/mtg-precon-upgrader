// DEC-516 (DEC-476 Phase 4) — price-index loader: in-memory cache, freshness
// cache-buster, and the deliberate localStorage bypass (the ~1 MB index must never
// touch the 5 MB quota). Mirrors the matcher/feature-index loader contracts.

import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  loadPriceIndex,
  loadPriceIndexMeta,
  priceOf,
  _resetPriceCaches,
} from '../../data/prices';

const META = {
  schema: 'combo-lab-price-index',
  source: 'scryfall-bulk-oracle-cards',
  sourceUrl: 'https://data.scryfall.io/oracle-cards/x.jsonl.gz',
  scryfall_updated_at: '2026-08-15T21:01:56.082+00:00',
  generatedAt: '2026-08-16T07:42:07+00:00',
  currencies: ['eur', 'usd'] as const,
  keyCount: 2,
  pricedEur: 2,
  pricedUsd: 2,
};
const INDEX = {
  'sol ring': [1.49, 1.56] as [number, number],
  'ashnod s altar': [14.41, null] as [number, null],
};

function fakeFetch(urls: string[]) {
  return vi.fn(async (url: string) => {
    urls.push(url);
    if (url.startsWith('/data/spellbook/price-index.meta.json')) {
      return { ok: true, status: 200, json: async () => META } as Response;
    }
    if (url.startsWith('/data/spellbook/price-index.json')) {
      return { ok: true, status: 200, json: async () => INDEX } as Response;
    }
    return { ok: false, status: 404, json: async () => null } as Response;
  }) as unknown as typeof fetch;
}

describe('price-index loader', () => {
  beforeEach(() => _resetPriceCaches());

  it('fetches meta then the index with a freshness ?v= buster', async () => {
    const urls: string[] = [];
    const index = await loadPriceIndex(fakeFetch(urls));
    expect(index?.['sol ring']).toEqual([1.49, 1.56]);
    const indexUrl = urls.find((u) => u.startsWith('/data/spellbook/price-index.json'));
    expect(indexUrl).toContain(`?v=${encodeURIComponent(META.scryfall_updated_at)}`);
  });

  it('caches in memory — a second call issues no further fetches', async () => {
    const urls: string[] = [];
    const f = fakeFetch(urls);
    await loadPriceIndex(f);
    const before = urls.length;
    await loadPriceIndex(f);
    expect(urls.length).toBe(before);
  });

  it('returns null when the artifact is absent (404)', async () => {
    const notFound = vi.fn(async () => ({ ok: false, status: 404, json: async () => null }) as Response);
    const meta = await loadPriceIndexMeta(notFound as unknown as typeof fetch);
    expect(meta).toBeNull();
  });

  it('priceOf reads the selected currency and tolerates gaps', () => {
    expect(priceOf(INDEX, 'sol ring', 'eur')).toBe(1.49);
    expect(priceOf(INDEX, 'sol ring', 'usd')).toBe(1.56);
    expect(priceOf(INDEX, 'ashnod s altar', 'usd')).toBeNull();
    expect(priceOf(INDEX, 'nonexistent', 'eur')).toBeNull();
    expect(priceOf(null, 'sol ring', 'eur')).toBeNull();
  });
});
