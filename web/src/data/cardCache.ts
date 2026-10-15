// Shared card cache (DEC-1102, design D of DEC-1072).
//
// An entry comes from one of three places:
//   1. data/card-metadata.json. The loader gives the file to seed() before it
//      gives any page a deck (loader.ts, loadCardMetadata), so get() answers at
//      once for every name of the file and enqueue() sends nothing for it. The
//      pictures are Scryfall's own addresses on cards.scryfall.io, and the price
//      is the file's USD price.
//   2. A /cards/named lookup, for a name that the file lacks. The lookups go one
//      at a time through scryfallLimiter (bucket 1: 600 ms between starts, and the
//      429 stop). A loaded lookup lives 24 h in localStorage under `gv1-card:`.
//   3. A picture from the file that fails to load. The cache looks that card up
//      once, and the answer's addresses replace the file's for 24 h. A second
//      failure inside the 24 h sends nothing.
//
// Public API (singleton):
//   cardCache.get(name)               → CardEntry | null (synchronous lookup)
//   cardCache.subscribe(name, fn)     → () => void       (notified on entry update)
//   cardCache.enqueue(name, options)  → void             (a lookup through the limiter; `first` goes before the queue)
//   cardCache.seed(metadata)          → void             (entries from data/card-metadata.json)
//   cardCache.imageFailed(name)       → void             (a picture of this card did not load)
//
// A lookup that answers 404 or another status fails that card only, and no one
// asks for it again inside ERROR_RETRY_MS. A 429 or a rejected fetch is not the
// card's failure: the limiter stops, and the card stays first in the queue.

import { cardEntryFromFile, cardEntryFromScryfall, type ScryfallCard } from './cardEntry';
import { createScryfallLimiter, lookupUrl, scryfallLimiter, type ScryfallLimiter } from './scryfallLimiter';
import type { RawCardMetadata } from './types';

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
  errorStatus?: number;
  /** Epoch ms when this entry was fetched; used for 24h TTL. */
  fetchedAt?: number;
  /** Epoch ms when a picture of this card from the file failed and the cache looked the card up again. */
  refreshedAt?: number;
}

type Listener = (entry: CardEntry | null) => void;

const TTL_MS = 24 * 60 * 60 * 1000; // 24 hours
const STORAGE_PREFIX = 'gv1-card:';
const ERROR_RETRY_MS = 30 * 1000;

export interface EnqueueOptions {
  /** Look this name up before the names that wait (the hover, the commander art). */
  first?: boolean;
}

/** Visible for testing — production callers should use the exported singleton. */
export interface CardCache {
  get(name: string): CardEntry | null;
  subscribe(name: string, fn: Listener): () => void;
  enqueue(name: string, options?: EnqueueOptions): void;
  seed(metadata: RawCardMetadata): void;
  imageFailed(name: string): void;
  /** Test-only: clear in-memory state. Does not touch localStorage. */
  _reset(): void;
}

interface CacheDeps {
  storage?: Storage | null;
  /** The fetch of the cache's own limiter, when `limiter` is not given. */
  fetchImpl?: typeof fetch;
  now?: () => number;
  limiter?: ScryfallLimiter;
}

interface QueueItem {
  name: string;
  key: string;
  /** A lookup for the pictures of a name of the file, after one of them failed. */
  refresh: boolean;
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
  const now = deps.now ?? (() => Date.now());
  const limiter =
    deps.limiter ?? createScryfallLimiter({ fetchImpl: deps.fetchImpl, storage: deps.storage, now: deps.now });

  const cache = new Map<string, CardEntry>();
  const subs = new Map<string, Set<Listener>>();
  const queue: QueueItem[] = [];
  /** Keys of the names that the file holds. */
  const seeded = new Set<string>();
  let seededFrom: RawCardMetadata | null = null;
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

  function put(key: string, entry: CardEntry, persist: boolean): void {
    cache.set(key, entry);
    if (persist) writePersisted(key, entry);
    notify(key);
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

  /** The `gv1-card:` keys in storage, without the prefix. */
  function persistedKeys(storage: Storage): Set<string> {
    const keys = new Set<string>();
    try {
      for (let i = 0; i < storage.length; i += 1) {
        const key = storage.key(i);
        if (key?.startsWith(STORAGE_PREFIX)) keys.add(key.slice(STORAGE_PREFIX.length));
      }
    } catch {
      // Storage unavailable: nothing to drop.
    }
    return keys;
  }

  function seed(metadata: RawCardMetadata): void {
    if (metadata === seededFrom) return;
    seededFrom = metadata;
    const storage = resolveStorage();
    const stored = storage ? persistedKeys(storage) : new Set<string>();
    for (const [name, meta] of Object.entries(metadata)) {
      const key = name.toLowerCase();
      let entry = cardEntryFromFile(name, meta);
      if (stored.has(key)) {
        // Storage holds each card once: the file's entry replaces a lookup's.
        // A lookup made after one of the file's pictures failed keeps its
        // addresses for 24 h.
        const refreshed = readPersisted(key);
        if (refreshed?.refreshedAt !== undefined && now() - refreshed.refreshedAt <= TTL_MS) {
          entry = {
            ...entry,
            image_small: refreshed.image_small,
            image_normal: refreshed.image_normal,
            image_large: refreshed.image_large,
            art_crop: refreshed.art_crop,
            fetchedAt: refreshed.fetchedAt,
            refreshedAt: refreshed.refreshedAt,
          };
        } else {
          try { storage!.removeItem(storageKey(key)); } catch { /* nothing to free */ }
        }
      }
      seeded.add(key);
      put(key, entry, false);
    }
  }

  /** The next name that still needs a lookup, marked as loading. */
  function takeNext(): QueueItem | null {
    while (queue.length > 0) {
      const item = queue.shift()!;
      if (item.refresh) return item;
      const existing = cache.get(item.key) ?? readPersisted(item.key);
      if (existing?.status === 'loaded') {
        // The file's seed, or another tab, got there first.
        if (existing !== cache.get(item.key)) put(item.key, existing, false);
        continue;
      }
      put(item.key, { status: 'loading', name: item.name }, false);
      return item;
    }
    return null;
  }

  function fail(item: QueueItem, error: string, errorStatus?: number): void {
    // A failed refresh leaves the file's entry; its refreshedAt holds the next try off for 24 h.
    if (item.refresh) return;
    put(item.key, { status: 'error', name: item.name, error, errorStatus, fetchedAt: now() }, false);
  }

  async function settle(item: QueueItem, response: Response): Promise<void> {
    if (!response.ok) {
      fail(item, `scryfall ${response.status}`, response.status);
      return;
    }
    let looked: CardEntry;
    try {
      looked = cardEntryFromScryfall((await response.json()) as ScryfallCard, now());
    } catch (err) {
      fail(item, err instanceof Error ? err.message : String(err));
      return;
    }
    const current = cache.get(item.key);
    if (item.refresh) {
      if (current?.status !== 'loaded') return;
      put(item.key, {
        ...current,
        image_small: looked.image_small,
        image_normal: looked.image_normal,
        image_large: looked.image_large,
        art_crop: looked.art_crop,
        fetchedAt: looked.fetchedAt,
      }, true);
      return;
    }
    // The seed arrived while the lookup was out: the file's entry stays.
    if (seeded.has(item.key) && current?.status === 'loaded') return;
    put(item.key, looked, true);
  }

  function pump(): void {
    if (pumping) return;
    pumping = true;
    (async () => {
      try {
        while (queue.length > 0) {
          const picked: { item: QueueItem | null } = { item: null };
          try {
            const sent = await limiter.next('lookup', () => {
              picked.item = takeNext();
              return picked.item ? lookupUrl(picked.item.name) : null;
            });
            if (picked.item && sent) await settle(picked.item, sent.response);
          } catch (err) {
            if (picked.item) fail(picked.item, err instanceof Error ? err.message : String(err));
          }
        }
      } finally {
        pumping = false;
      }
    })();
  }

  function enqueue(name: string, options: EnqueueOptions = {}): void {
    if (!name) return;
    const key = name.toLowerCase();
    const existing = cache.get(key) ?? readPersisted(key);
    if (existing && existing.status !== 'error') {
      if (existing !== cache.get(key)) cache.set(key, existing);
      return;
    }
    if (existing?.status === 'error' && existing.fetchedAt && now() - existing.fetchedAt < ERROR_RETRY_MS) {
      return;
    }
    const at = queue.findIndex((queued) => queued.key === key && !queued.refresh);
    if (at >= 0) {
      if (!options.first) return;
      queue.splice(at, 1);
    }
    const item: QueueItem = { name, key, refresh: false };
    if (options.first) queue.unshift(item);
    else queue.push(item);
    pump();
  }

  function imageFailed(name: string): void {
    if (!name) return;
    const key = name.toLowerCase();
    // Only a picture from the file has another address to find.
    if (!seeded.has(key)) return;
    const entry = cache.get(key);
    if (entry?.status !== 'loaded') return;
    if (entry.refreshedAt !== undefined && now() - entry.refreshedAt <= TTL_MS) return;
    // Mark the card before the lookup goes, so that a reload inside 24 h does not ask again.
    const t = now();
    const marked: CardEntry = { ...entry, refreshedAt: t, fetchedAt: t };
    cache.set(key, marked);
    writePersisted(key, marked);
    queue.push({ name, key, refresh: true });
    pump();
  }

  function _reset(): void {
    cache.clear();
    subs.clear();
    queue.length = 0;
    seeded.clear();
    seededFrom = null;
    pumping = false;
    limiter._reset?.();
  }

  return { get, subscribe, enqueue, seed, imageFailed, _reset };
}

export const cardCache: CardCache = createCardCache({ limiter: scryfallLimiter });
