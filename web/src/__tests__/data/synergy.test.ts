// DEC-552 — feature-index loader cache-buster. The 3.3 MB index is derived from
// the KB entries AND the ontology AND the extractor, so a corpus-only ?v= key
// would serve a stale index against a freshly re-emitted synergy-config.

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { loadFeatureIndex, _resetSynergyCaches } from '../../data/synergy';

const META = {
  schema: 'combo-kb-feature-index',
  corpusVersion: '2026-08-15T09:01:55.591+00:00',
  ontologyVersion: '1.1.0',
  extractorVersion: 'det-1.0.1',
  cardCount: 1,
  featurefulCount: 1,
  generatedAt: 'x',
};
const INDEX = { cards: {} };

function fakeFetch(urls: string[]) {
  return vi.fn(async (url: string) => {
    urls.push(url);
    if (url.startsWith('/data/combo-kb/feature-index.meta.json')) {
      return { ok: true, status: 200, json: async () => META } as Response;
    }
    if (url.startsWith('/data/combo-kb/feature-index.json')) {
      return { ok: true, status: 200, json: async () => INDEX } as Response;
    }
    return { ok: false, status: 404, json: async () => null } as Response;
  }) as unknown as typeof fetch;
}

describe('feature-index loader', () => {
  beforeEach(() => _resetSynergyCaches());

  it('busts the index cache on corpus, ontology AND extractor version', async () => {
    const urls: string[] = [];
    await loadFeatureIndex(fakeFetch(urls));
    const indexUrl = urls.find((u) => u.startsWith('/data/combo-kb/feature-index.json'));
    const expected = encodeURIComponent(
      `${META.corpusVersion}|${META.ontologyVersion}|${META.extractorVersion}`,
    );
    expect(indexUrl).toBe(`/data/combo-kb/feature-index.json?v=${expected}`);
  });

  it('caches in memory — a second call issues no further fetches', async () => {
    const urls: string[] = [];
    const f = fakeFetch(urls);
    await loadFeatureIndex(f);
    const count = urls.length;
    await loadFeatureIndex(f);
    expect(urls.length).toBe(count);
  });
});
