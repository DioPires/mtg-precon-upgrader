// Shared Scryfall card cache.
//
// Mirrors gv1-cards.js (legacy prototype) with two additions:
//   1. localStorage persistence with 24h TTL (read on first access; write on every load).
//   2. Strict TypeScript types for the entry shape.
//
// Public API (singleton):
//   cardCache.get(name)             → CardEntry | null  (synchronous lookup)
//   cardCache.subscribe(name, fn)   → () => void        (notified on entry update)
//   cardCache.fetch(name)           → Promise<CardEntry> (deduped)
//   cardCache.enqueue(name)         → void              (throttled ≥80ms between Scryfall calls)
//
// The throttled queue exists because Scryfall's docs request ≥50ms between calls;
// we use 80ms for headroom. Dedupe both at the queue level (skip names already in
// queue or cache) and at the inflight level (concurrent fetch() calls share one promise).

export type CardStatus = 'loading' | 'loaded' | 'error';

export interface CardEntry {
  status: CardStatus;
  name: string;
  mana_cost?: string;
  cmc?: number;
  type_line?: string;
  image_small?: string;
  image_normal?: string;
  image_large?: string;
  art_crop?: string;
  price?: string | null;
  error?: string;
  /** Epoch ms when this entry was fetched; used for 24h TTL. */
  fetchedAt?: number;
}

type Listener = (entry: CardEntry | null) => void;

const TTL_MS = 24 * 60 * 60 * 1000; // 24 hours
const STORAGE_PREFIX = 'gv1-card:';
const THROTTLE_MS = 80;

/** Visible for testing — production callers should use the exported singleton. */
export interface CardCache {
  get(name: string): CardEntry | null;
  subscribe(name: string, fn: Listener): () => void;
  fetch(name: string): Promise<CardEntry>;
  enqueue(name: string): void;
  /** Test-only: clear in-memory state. Does not touch localStorage. */
  _reset(): void;
}

interface CacheDeps {
  storage?: Storage | null;
  fetchImpl?: typeof fetch;
  now?: () => number;
  throttleMs?: number;
}

function defaultStorage(): Storage | null {
  // Resolved lazily because module load may run before jsdom installs window/localStorage,
  // and Node's experimental localStorage (without setItem) shouldn't be captured.
  if (typeof window !== 'undefined' && window.localStorage) return window.localStorage;
  if (typeof globalThis !== 'undefined' && (globalThis as { localStorage?: Storage }).localStorage) {
    const ls = (globalThis as { localStorage?: Storage }).localStorage!;
    if (typeof ls.setItem === 'function' && typeof ls.getItem === 'function') return ls;
  }
  return null;
}

export function createCardCache(deps: CacheDeps = {}): CardCache {
  const explicitStorage = deps.storage;
  const resolveStorage = (): Storage | null =>
    explicitStorage === undefined ? defaultStorage() : explicitStorage;
  // Lazily resolve fetch each call so test spies on globalThis.fetch are honored.
  const explicitFetch = deps.fetchImpl;
  const resolveFetch = (): typeof fetch | undefined =>
    explicitFetch ?? (typeof fetch !== 'undefined' ? fetch : undefined);
  const now = deps.now ?? (() => Date.now());
  const throttleMs = deps.throttleMs ?? THROTTLE_MS;

  const cache = new Map<string, CardEntry>();
  const subs = new Map<string, Set<Listener>>();
  const inflight = new Map<string, Promise<CardEntry>>();
  const queue: string[] = [];
  let pumping = false;

  function storageKey(key: string): string {
    return STORAGE_PREFIX + key;
  }

  function readPersisted(key: string): CardEntry | null {
    const storage = resolveStorage();
    if (!storage) return null;
    try {
      const raw = storage.getItem(storageKey(key));
      if (!raw) return null;
      const parsed = JSON.parse(raw) as CardEntry;
      if (parsed.status !== 'loaded') return null;
      if (!parsed.fetchedAt || now() - parsed.fetchedAt > TTL_MS) {
        storage.removeItem(storageKey(key));
        return null;
      }
      return parsed;
    } catch {
      return null;
    }
  }

  function writePersisted(key: string, entry: CardEntry): void {
    const storage = resolveStorage();
    if (!storage) return;
    if (entry.status !== 'loaded') return;
    try {
      storage.setItem(storageKey(key), JSON.stringify(entry));
    } catch {
      // Quota exceeded or disabled — silently drop. Memory cache still works.
    }
  }

  function notify(key: string): void {
    const set = subs.get(key);
    if (!set) return;
    const entry = cache.get(key) ?? null;
    set.forEach((fn) => {
      try { fn(entry); } catch { /* swallow listener errors */ }
    });
  }

  function get(name: string): CardEntry | null {
    if (!name) return null;
    const key = name.toLowerCase();
    const mem = cache.get(key);
    if (mem) return mem;
    const persisted = readPersisted(key);
    if (persisted) {
      cache.set(key, persisted);
      return persisted;
    }
    return null;
  }

  function subscribe(name: string, fn: Listener): () => void {
    if (!name) return () => {};
    const key = name.toLowerCase();
    let set = subs.get(key);
    if (!set) { set = new Set(); subs.set(key, set); }
    set.add(fn);
    return () => { set!.delete(fn); };
  }

  async function fetchOne(name: string): Promise<CardEntry> {
    const key = name.toLowerCase();
    const existing = cache.get(key) ?? readPersisted(key);
    if (existing && existing.status === 'loaded') {
      cache.set(key, existing);
      return existing;
    }
    const inFlight = inflight.get(key);
    if (inFlight) return inFlight;

    const loading: CardEntry = { status: 'loading', name };
    cache.set(key, loading);
    notify(key);

    const fetchImpl = resolveFetch();
    if (!fetchImpl) {
      const errEntry: CardEntry = { status: 'error', name, error: 'fetch unavailable' };
      cache.set(key, errEntry);
      notify(key);
      return errEntry;
    }

    const url = `https://api.scryfall.com/cards/named?fuzzy=${encodeURIComponent(name)}`;
    const promise = (async (): Promise<CardEntry> => {
      try {
        const r = await fetchImpl(url);
        if (!r.ok) throw new Error('scryfall ' + r.status);
        const data = await r.json();
        const face = (data.card_faces && data.card_faces[0]) || data;
        const imgs = data.image_uris || face.image_uris || {};
        const entry: CardEntry = {
          status: 'loaded',
          name: data.name,
          mana_cost: face.mana_cost || data.mana_cost || '',
          cmc: data.cmc,
          type_line: data.type_line || face.type_line || '',
          image_small: imgs.small || '',
          image_normal: imgs.normal || '',
          image_large: imgs.large || '',
          art_crop: imgs.art_crop || '',
          price: data.prices?.usd ? `$${parseFloat(data.prices.usd).toFixed(2)}` : null,
          fetchedAt: now(),
        };
        cache.set(key, entry);
        writePersisted(key, entry);
        notify(key);
        return entry;
      } catch (err) {
        const entry: CardEntry = {
          status: 'error',
          name,
          error: err instanceof Error ? err.message : String(err),
        };
        cache.set(key, entry);
        notify(key);
        return entry;
      } finally {
        inflight.delete(key);
      }
    })();
    inflight.set(key, promise);
    return promise;
  }

  function pump(): void {
    if (pumping) return;
    pumping = true;
    (async () => {
      while (queue.length) {
        const name = queue.shift()!;
        await fetchOne(name);
        if (queue.length) await new Promise((r) => setTimeout(r, throttleMs));
      }
      pumping = false;
    })();
  }

  function enqueue(name: string): void {
    if (!name) return;
    const key = name.toLowerCase();
    const existing = cache.get(key) ?? readPersisted(key);
    if (existing && existing.status !== 'error') {
      if (existing !== cache.get(key)) cache.set(key, existing);
      return;
    }
    if (queue.includes(name)) return;
    queue.push(name);
    pump();
  }

  function _reset(): void {
    cache.clear();
    subs.clear();
    inflight.clear();
    queue.length = 0;
    pumping = false;
  }

  return { get, subscribe, fetch: fetchOne, enqueue, _reset };
}

export const cardCache: CardCache = createCardCache();
