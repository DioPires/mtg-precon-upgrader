import { describe, it, expect, vi, beforeEach } from 'vitest';
import { createCardCache, type CardEntry } from '../../data/cardCache';

class MemoryStorage implements Storage {
  private store: Map<string, string> = new Map();
  get length(): number { return this.store.size; }
  clear(): void { this.store.clear(); }
  getItem(k: string): string | null { return this.store.get(k) ?? null; }
  setItem(k: string, v: string): void { this.store.set(k, v); }
  removeItem(k: string): void { this.store.delete(k); }
  key(i: number): string | null { return Array.from(this.store.keys())[i] ?? null; }
}

function scryfallResponse(name: string, overrides: Partial<Record<string, unknown>> = {}) {
  return {
    ok: true,
    json: async () => ({
      name,
      mana_cost: '{1}',
      cmc: 1,
      type_line: 'Artifact',
      image_uris: { small: `s-${name}`, normal: `n-${name}`, large: `l-${name}`, art_crop: `a-${name}` },
      prices: { usd: '0.42' },
      ...overrides,
    }),
  };
}

describe('cardCache', () => {
  let storage: MemoryStorage;
  beforeEach(() => { storage = new MemoryStorage(); });

  it('fetches a card and notifies subscribers with the loaded entry', async () => {
    const fetchImpl = vi.fn().mockResolvedValue(scryfallResponse('Sol Ring'));
    const cache = createCardCache({ storage, fetchImpl: fetchImpl as never, throttleMs: 0 });
    const listener = vi.fn();
    cache.subscribe('Sol Ring', listener);
    const entry = await cache.fetch('Sol Ring');
    expect(entry.status).toBe('loaded');
    expect(entry.name).toBe('Sol Ring');
    expect(entry.image_small).toBe('s-Sol Ring');
    expect(entry.image_normal).toBe('n-Sol Ring');
    expect(entry.image_large).toBe('l-Sol Ring');
    expect(entry.price).toBe('$0.42');
    // Listener should fire at least twice: loading → loaded.
    expect(listener).toHaveBeenCalled();
    const last = listener.mock.calls.at(-1)?.[0] as CardEntry;
    expect(last.status).toBe('loaded');
  });

  it('dedupes concurrent fetches into a single network call', async () => {
    const fetchImpl = vi.fn().mockResolvedValue(scryfallResponse('Sol Ring'));
    const cache = createCardCache({ storage, fetchImpl: fetchImpl as never, throttleMs: 0 });
    const [a, b, c] = await Promise.all([
      cache.fetch('Sol Ring'),
      cache.fetch('Sol Ring'),
      cache.fetch('Sol Ring'),
    ]);
    expect(fetchImpl).toHaveBeenCalledTimes(1);
    expect(a.status).toBe('loaded');
    expect(b).toBe(a);
    expect(c).toBe(a);
  });

  it('persists loaded entries to localStorage and rehydrates on get()', () => {
    const fetchImpl = vi.fn();
    const seed: CardEntry = {
      status: 'loaded',
      name: 'Sol Ring',
      image_small: 'cached-small',
      fetchedAt: Date.now(),
    };
    storage.setItem('gv1-card:sol ring', JSON.stringify(seed));
    const cache = createCardCache({ storage, fetchImpl: fetchImpl as never, throttleMs: 0 });
    const got = cache.get('Sol Ring');
    expect(got?.status).toBe('loaded');
    expect(got?.image_small).toBe('cached-small');
    expect(fetchImpl).not.toHaveBeenCalled();
  });

  it('discards persisted entries older than 24h', () => {
    const stale: CardEntry = {
      status: 'loaded',
      name: 'Sol Ring',
      fetchedAt: 0, // long ago
    };
    storage.setItem('gv1-card:sol ring', JSON.stringify(stale));
    const now = () => 25 * 60 * 60 * 1000;
    const cache = createCardCache({ storage, now, fetchImpl: undefined, throttleMs: 0 });
    expect(cache.get('Sol Ring')).toBeNull();
    expect(storage.getItem('gv1-card:sol ring')).toBeNull();
  });

  it('writes loaded entries through to localStorage on fetch', async () => {
    const fetchImpl = vi.fn().mockResolvedValue(scryfallResponse('Sol Ring'));
    const cache = createCardCache({ storage, fetchImpl: fetchImpl as never, throttleMs: 0 });
    await cache.fetch('Sol Ring');
    const persisted = storage.getItem('gv1-card:sol ring');
    expect(persisted).not.toBeNull();
    const parsed = JSON.parse(persisted!) as CardEntry;
    expect(parsed.status).toBe('loaded');
    expect(parsed.fetchedAt).toBeTypeOf('number');
  });

  it('records errors without persisting them', async () => {
    const fetchImpl = vi.fn().mockResolvedValue({ ok: false, status: 404, json: async () => ({}) });
    const cache = createCardCache({ storage, fetchImpl: fetchImpl as never, throttleMs: 0 });
    const entry = await cache.fetch('Nonesuch');
    expect(entry.status).toBe('error');
    expect(storage.getItem('gv1-card:nonesuch')).toBeNull();
  });

  it('retries transient Scryfall failures before surfacing an error', async () => {
    vi.useFakeTimers();
    const fetchImpl = vi.fn()
      .mockResolvedValueOnce({ ok: false, status: 429, headers: { get: () => null }, json: async () => ({}) })
      .mockResolvedValueOnce(scryfallResponse('Sol Ring'));
    const cache = createCardCache({ storage, fetchImpl: fetchImpl as never, throttleMs: 0 });

    const promise = cache.fetch('Sol Ring');
    await vi.advanceTimersByTimeAsync(0);
    expect(fetchImpl).toHaveBeenCalledTimes(1);
    await vi.advanceTimersByTimeAsync(750);
    const entry = await promise;

    expect(fetchImpl).toHaveBeenCalledTimes(2);
    expect(entry.status).toBe('loaded');
    vi.useRealTimers();
  });

  it('enqueue throttles successive fetches by the configured interval', async () => {
    vi.useFakeTimers();
    const fetchImpl = vi.fn().mockResolvedValue(scryfallResponse('Sol Ring'));
    const cache = createCardCache({ storage, fetchImpl: fetchImpl as never, throttleMs: 80 });
    cache.enqueue('Sol Ring');
    cache.enqueue('Mana Crypt');
    cache.enqueue('Mana Vault');
    // Run microtasks; first fetch resolves immediately.
    await vi.advanceTimersByTimeAsync(0);
    expect(fetchImpl).toHaveBeenCalledTimes(1);
    // Less than 80ms — second fetch should still be waiting.
    await vi.advanceTimersByTimeAsync(40);
    expect(fetchImpl).toHaveBeenCalledTimes(1);
    // Cross the throttle boundary; second fetch fires.
    await vi.advanceTimersByTimeAsync(80);
    expect(fetchImpl).toHaveBeenCalledTimes(2);
    await vi.advanceTimersByTimeAsync(80);
    expect(fetchImpl).toHaveBeenCalledTimes(3);
    vi.useRealTimers();
  });

  it('enqueue is idempotent for names already in the queue or cache', async () => {
    const fetchImpl = vi.fn().mockResolvedValue(scryfallResponse('Sol Ring'));
    const cache = createCardCache({ storage, fetchImpl: fetchImpl as never, throttleMs: 0 });
    cache.enqueue('Sol Ring');
    cache.enqueue('Sol Ring');
    cache.enqueue('Sol Ring');
    // Drain the queue.
    await new Promise((r) => setTimeout(r, 10));
    expect(fetchImpl).toHaveBeenCalledTimes(1);
  });

  it('survives malformed localStorage payloads gracefully', () => {
    storage.setItem('gv1-card:sol ring', '{not json');
    const cache = createCardCache({ storage, fetchImpl: undefined, throttleMs: 0 });
    expect(cache.get('Sol Ring')).toBeNull();
  });
});
