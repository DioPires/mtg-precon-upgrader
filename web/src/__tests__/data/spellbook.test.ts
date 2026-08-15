// DEC-487 — matcher-index loader: in-memory cache, corpus-version cache-buster,
// and the deliberate localStorage bypass (the 13 MB index must never touch the
// 5 MB localStorage quota).

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { loadMatcherIndex, loadMatcherMeta, _resetSpellbookCaches } from '../../data/spellbook';

const META = {
  source: 'commanderspellbook',
  sourceUrl: 'x',
  corpusVersion: '2026-08-15T13:18:26.081346+00:00',
  spellbookApiVersion: '6',
  generatedAt: 'x',
  variantCount: 1,
  cardCount: 0,
  matchingModel: 'phase0-card-set-containment',
  bracketTagLegend: {},
};
const INDEX = { meta: META, cards: {}, templates: {}, features: {}, variants: [] };

function fakeFetch(urls: string[]) {
  return vi.fn(async (url: string) => {
    urls.push(url);
    if (url.startsWith('/data/spellbook/matcher-index.meta.json')) {
      return { ok: true, status: 200, json: async () => META } as Response;
    }
    if (url.startsWith('/data/spellbook/matcher-index.json')) {
      return { ok: true, status: 200, json: async () => INDEX } as Response;
    }
    return { ok: false, status: 404, json: async () => null } as Response;
  }) as unknown as typeof fetch;
}

describe('spellbook matcher loader', () => {
  beforeEach(() => _resetSpellbookCaches());

  it('fetches the meta sidecar, then the index with a ?v= corpus buster', async () => {
    const urls: string[] = [];
    const index = await loadMatcherIndex(fakeFetch(urls));
    expect(index?.meta.corpusVersion).toBe(META.corpusVersion);
    const indexUrl = urls.find((u) => u.startsWith('/data/spellbook/matcher-index.json'));
    expect(indexUrl).toContain(`?v=${encodeURIComponent(META.corpusVersion)}`);
  });

  it('caches in memory — a second call issues no further fetches', async () => {
    const urls: string[] = [];
    const f = fakeFetch(urls);
    await loadMatcherIndex(f);
    const count = urls.length;
    await loadMatcherIndex(f);
    expect(urls.length).toBe(count);
  });

  it('never writes the index to localStorage', async () => {
    const setItem = vi.spyOn(Storage.prototype, 'setItem');
    await loadMatcherIndex(fakeFetch([]));
    // No localStorage key should carry the multi-MB index payload.
    const wroteIndex = setItem.mock.calls.some(([, v]) => typeof v === 'string' && v.includes('"variants"'));
    expect(wroteIndex).toBe(false);
    setItem.mockRestore();
  });

  it('loadMatcherMeta reads only the small sidecar', async () => {
    const urls: string[] = [];
    const meta = await loadMatcherMeta(fakeFetch(urls));
    expect(meta?.corpusVersion).toBe(META.corpusVersion);
    expect(urls).toEqual(['/data/spellbook/matcher-index.meta.json']);
  });
});
