// DEC-942: the localStorage envelope must carry deck + sim + metrics only.
// The four large per-deck artifacts (candidates, spellbook-combos,
// synergy-candidates, tier-b-loops) are 11.7M chars fleet-wide against a ~5.2M
// browser quota — caching them starved the user's owned-cards map (DEC-941).

import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createDeckLoader } from '../../data/loader';

const INDEX = { commanders: [{ id: 'alpha', name: 'Alpha', theme: 'T', colors: ['G'] }] };

function payloadFor(url: string): unknown {
  if (url.endsWith('/index.json')) return INDEX;
  if (url.endsWith('/card-metadata.json')) return { 'Sol Ring': { mana_cost: '{1}' } };
  if (url.endsWith('/deck.json')) return { id: 'alpha', name: 'Alpha', decklist: [] };
  if (url.endsWith('/simulation.json')) return { deck_id: 'alpha' };
  if (url.endsWith('/metrics.json')) return { deck_id: 'alpha' };
  if (url.endsWith('/candidates.json')) return { candidates: ['BIG'] };
  if (url.endsWith('/spellbook-combos.json')) return { included: ['BIG'] };
  if (url.endsWith('/synergy-candidates.json')) return { groups: ['BIG'] };
  if (url.endsWith('/tier-b-loops.json')) return { engines: ['BIG'] };
  throw new Error('unexpected url ' + url);
}

function memStorage(): Storage {
  const map = new Map<string, string>();
  return {
    get length() {
      return map.size;
    },
    key: (i: number) => [...map.keys()][i] ?? null,
    getItem: (k: string) => map.get(k) ?? null,
    setItem: (k: string, v: string) => void map.set(k, v),
    removeItem: (k: string) => void map.delete(k),
    clear: () => map.clear(),
  } as unknown as Storage;
}

let fetchImpl: ReturnType<typeof vi.fn>;
let storage: Storage;

beforeEach(() => {
  storage = memStorage();
  fetchImpl = vi.fn(async (url: string) => ({
    ok: true,
    status: 200,
    json: async () => payloadFor(url),
  }));
});

function loader() {
  return createDeckLoader({ fetchImpl: fetchImpl as unknown as typeof fetch, storage });
}

function deckEnvelope(): Record<string, unknown> {
  const key = [...Array(storage.length).keys()]
    .map((i) => storage.key(i)!)
    .find((k) => k.includes('deck:alpha'));
  expect(key, 'deck envelope was written').toBeTruthy();
  return JSON.parse(storage.getItem(key!)!).payload;
}

describe('deck loader persisted envelope (DEC-942)', () => {
  it('returns a complete bundle but persists only deck + sim + metrics', async () => {
    const bundle = await loader().loadDeck('alpha');

    // Callers still see every artifact.
    expect(bundle?.candidates).toEqual({ candidates: ['BIG'] });
    expect(bundle?.spellbookCombos).toEqual({ included: ['BIG'] });
    expect(bundle?.synergyCandidates).toEqual({ groups: ['BIG'] });
    expect(bundle?.tierBLoops).toEqual({ engines: ['BIG'] });
    expect(bundle?.cardMetadata).toBeTruthy();

    // Storage does not.
    const persisted = deckEnvelope();
    expect(Object.keys(persisted).sort()).toEqual(['deck', 'id', 'index', 'metrics', 'sim']);
    expect(JSON.stringify(persisted)).not.toContain('BIG');
  });

  it('re-fetches the stripped artifacts when a bundle hydrates from storage', async () => {
    await loader().loadDeck('alpha');
    fetchImpl.mockClear();

    // Fresh loader, same storage — simulates a returning user.
    const bundle = await loader().loadDeck('alpha');
    expect(bundle?.tierBLoops).toEqual({ engines: ['BIG'] });
    expect(bundle?.synergyCandidates).toEqual({ groups: ['BIG'] });

    const fetched = fetchImpl.mock.calls.map((c) => String(c[0]));
    expect(fetched.some((u) => u.endsWith('/candidates.json'))).toBe(true);
    expect(fetched.some((u) => u.endsWith('/spellbook-combos.json'))).toBe(true);
    // deck/sim/metrics came from the cache.
    expect(fetched.some((u) => u.endsWith('/deck.json'))).toBe(false);
    expect(fetched.some((u) => u.endsWith('/simulation.json'))).toBe(false);
    expect(fetched.some((u) => u.endsWith('/metrics.json'))).toBe(false);
  });

  it('reclaims envelopes from an earlier STORAGE_PREFIX on first write', async () => {
    // A prefix bump alone orphans the old keys; the fat v143 envelope would
    // otherwise sit there forever and re-create the DEC-941 quota wall.
    storage.setItem('gv1-deck-data-v143:deck:alpha', 'STALE'.repeat(100));
    storage.setItem('gv1-deck-data-v1:card-metadata', 'STALE');
    storage.setItem('gv1-card:sol ring', 'KEEP');
    storage.setItem('grimoire-owned-cards', 'KEEP');

    await loader().loadDeck('alpha');

    expect(storage.getItem('gv1-deck-data-v143:deck:alpha')).toBeNull();
    expect(storage.getItem('gv1-deck-data-v1:card-metadata')).toBeNull();
    // Only this loader's own family is swept.
    expect(storage.getItem('gv1-card:sol ring')).toBe('KEEP');
    expect(storage.getItem('grimoire-owned-cards')).toBe('KEEP');
    expect(deckEnvelope().deck).toBeTruthy();
  });

  it('survives a storage that refuses writes', async () => {
    storage = {
      ...memStorage(),
      setItem: () => {
        throw new DOMException('quota', 'QuotaExceededError');
      },
    } as unknown as Storage;
    const bundle = await loader().loadDeck('alpha');
    expect(bundle?.deck).toBeTruthy();
    expect(bundle?.candidates).toEqual({ candidates: ['BIG'] });
  });
});

// DEC-1102: every deck bundle waits for card-metadata.json, and the loader seeds
// the card cache with it before the bundle resolves. A page takes its card
// names from a bundle, so it cannot ask the cache for a name of the file first.
describe('deck loader seeds the card cache (DEC-1102)', () => {
  it('seeds before the first bundle resolves, from the network and from storage', async () => {
    for (const round of ['network', 'storage']) {
      let resolved = false;
      const seeds: Array<{ metadata: unknown; beforeBundle: boolean }> = [];
      const seed = (metadata: unknown) => seeds.push({ metadata, beforeBundle: !resolved });
      const deckLoader = createDeckLoader({
        fetchImpl: fetchImpl as unknown as typeof fetch,
        storage,
        cardCache: { seed },
      });
      const bundle = await deckLoader.loadDeck('alpha').then((b) => {
        resolved = true;
        return b;
      });
      expect(seeds, round).toEqual([{ metadata: { 'Sol Ring': { mana_cost: '{1}' } }, beforeBundle: true }]);
      expect(bundle?.cardMetadata).toBe(seeds[0].metadata);
      await deckLoader.loadAll();
      expect(seeds, `${round}: one seed per loader`).toHaveLength(1);
    }
    // The second round read the persisted copy, not the network.
    const metadataFetches = fetchImpl.mock.calls.filter(([url]) => String(url).endsWith('/card-metadata.json'));
    expect(metadataFetches).toHaveLength(1);
  });

  it('writes its envelopes under v156', async () => {
    await loader().loadDeck('alpha');
    const keys = [...Array(storage.length).keys()].map((i) => storage.key(i)!);
    expect(keys.filter((k) => k.startsWith('gv1-deck-data-')).every((k) => k.startsWith('gv1-deck-data-v156:'))).toBe(true);
  });
});
