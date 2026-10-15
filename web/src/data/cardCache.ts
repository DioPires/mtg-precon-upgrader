// Shared card cache (DEC-1102 and DEC-1131, design D of DEC-1072).
//
// An entry comes from one of two places:
//   1. data/card-metadata.json. The loader gives the file and the date of its
//      prices (`prices_as_of` of card-metadata.meta.json) to seed() before it
//      gives any page a deck (loader.ts, loadCardMetadata), so get() answers at
//      once for every name of the file and enqueue() sends nothing for it. The
//      pictures are Scryfall's own addresses on cards.scryfall.io, and the price
//      is the file's USD price, dated `prices_as_of`.
//   2. A batch, for a name that the file lacks: one POST to /cards/collection
//      with up to 75 names, through scryfallLimiter (bucket 1: 1,200 ms between
//      starts, the 20 s timeout and the 429 stop). A loaded name lives 24 h in
//      localStorage under `gv1-card:`; its price is dated by the answer.
//
// A batch also carries two refreshes for a name of the file. Each changes only
// its own fields, and lives 24 h under `gv1-card:` as an overlay (the changed
// fields and the time of the try). seed() keeps a live overlay.
//   - The price, when the price shown is older than 24 h (refreshPrice(): the
//     /shopping rows and the deck guide tiles that show the cache's price). Only
//     the price and its date change. When the file is newer than the refresh,
//     the file's price wins. A refresh that gets no price (not found, a 400 or
//     422, or `usd` null) keeps the price shown, and nobody asks again for 24 h.
//   - The pictures, after a picture from the file failed to load (imageFailed()).
//     The mark goes to storage before the batch, so a second failure inside 24 h
//     sends nothing, also after a reload.
//
// At its turn a batch takes the waiting names in this order: the names asked
// `first` (the hover, the commander art), the other lookups, then the refreshes.
// A `//` name goes out as its front face, and two names with one front face go
// out once. The answer is matched to the names by normalizeName() on the full
// name and on the front face, never by position, and stored under the name that
// the app asked for.
//
// A name in the answer's `not_found` gets an error entry that lives 24 h in
// storage: nobody asks for it again, also after a reload. An answer with another
// status (a 400 or a 422) fails the batch's lookups for ERROR_RETRY_MS, in
// memory, and holds its refreshes for 24 h; it starts no stop. A 429, a rejected
// fetch or a request with no answer in 20 s is not the cards' failure: the
// limiter stops, and the same batch goes first when the stop ends.
//
// Public API (singleton):
//   cardCache.get(name)                 → CardEntry | null (synchronous lookup)
//   cardCache.subscribe(name, fn)       → () => void       (notified on entry update)
//   cardCache.enqueue(name, options)    → void             (a lookup in the next batch; `first` goes before the others)
//   cardCache.seed(metadata, asOf)      → void             (entries from data/card-metadata.json, prices dated `asOf`)
//   cardCache.imageFailed(name)         → void             (a picture of this card did not load)
//   cardCache.refreshPrice(name)        → void             (refresh the price if it is older than 24 h)
//   cardCache.pricePending(name)        → boolean          (a price refresh of this card waits or is out)

import { cardEntryFromFile, cardEntryFromScryfall, formatUsd, type ScryfallCard, type ScryfallCollection } from './cardEntry';
import { frontFace } from './cardName';
import { collectionRequest, createScryfallLimiter, scryfallLimiter, type ScryfallLimiter } from './scryfallLimiter';
import type { RawCardMetadata } from './types';
import { nameKeys, normalizeName } from '../lib/spellbookMatch';

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
  /** Epoch ms of the price: `prices_as_of` of the file, or the time of the answer that gave it. */
  priceAsOf?: number;
  /** Epoch ms of the last price refresh of a name of the file, whatever its answer. */
  priceCheckedAt?: number;
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
/** Scryfall answers up to 75 identifiers in one /cards/collection request. */
export const BATCH_MAX = 75;
/** The errorStatus of a name that Scryfall does not know (`not_found`). */
const NOT_FOUND = 404;

export interface EnqueueOptions {
  /** Look this name up before the names that wait (the hover, the commander art). */
  first?: boolean;
}

/** Visible for testing — production callers should use the exported singleton. */
export interface CardCache {
  get(name: string): CardEntry | null;
  subscribe(name: string, fn: Listener): () => void;
  enqueue(name: string, options?: EnqueueOptions): void;
  seed(metadata: RawCardMetadata, pricesAsOf?: string | null): void;
  imageFailed(name: string): void;
  refreshPrice(name: string): void;
  pricePending(name: string): boolean;
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

/** One name that waits for a batch, with what the batch must bring for it. */
interface Wanted {
  key: string;
  name: string;
  first: boolean;
  /** The whole entry, for a name that the file lacks. */
  lookup: boolean;
  /** New picture addresses, after a picture from the file failed. */
  pictures: boolean;
  /** A new price, for a price older than 24 h. */
  price: boolean;
}

/** What a refresh changed for a name of the file, as storage holds it under `gv1-card:`. */
interface Overlay {
  /** The time of the last write. */
  fetchedAt: number;
  refreshedAt?: number;
  image_small?: string;
  image_normal?: string;
  image_large?: string;
  art_crop?: string;
  priceCheckedAt?: number;
  price?: string;
  priceAsOf?: number;
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

/** The price part of an overlay, without its pictures. */
function pricePart(overlay: Overlay | undefined): Partial<Overlay> {
  if (overlay?.priceCheckedAt === undefined) return {};
  const part: Partial<Overlay> = { priceCheckedAt: overlay.priceCheckedAt };
  if (overlay.price !== undefined && overlay.priceAsOf !== undefined) {
    part.price = overlay.price;
    part.priceAsOf = overlay.priceAsOf;
  }
  return part;
}

/** The picture part of an overlay, without its price. */
function picturePart(overlay: Overlay | undefined): Partial<Overlay> {
  if (overlay?.refreshedAt === undefined) return {};
  const { refreshedAt, image_small, image_normal, image_large, art_crop } = overlay;
  return image_normal || image_small || image_large || art_crop
    ? { refreshedAt, image_small, image_normal, image_large, art_crop }
    : { refreshedAt };
}

/** The identifier that a batch sends for a name: its front face. */
function identifierOf(name: string): string {
  return frontFace(name).trim();
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
  /** The names that wait for a batch, in order, and by key. */
  const queue: Wanted[] = [];
  const queued = new Map<string, Wanted>();
  /** The names of the batch that is out (one at a time), by key. */
  const out = new Map<string, Wanted>();
  /** The file's entry of each name of the file, before any overlay. */
  const fileEntries = new Map<string, CardEntry>();
  const overlays = new Map<string, Overlay>();
  let seededFrom: RawCardMetadata | null = null;
  let seededAsOf: number | undefined;
  let pumping = false;

  function storageKey(key: string): string {
    return STORAGE_PREFIX + key;
  }

  function isLive(at: number | undefined): at is number {
    return at !== undefined && now() - at <= TTL_MS;
  }

  // ── Storage ──────────────────────────────────────────────────────────────

  /** A loaded lookup, or a name that Scryfall does not know, younger than 24 h. */
  function readPersisted(key: string): CardEntry | null {
    const storage = resolveStorage();
    if (!storage) return null;
    try {
      const raw = storage.getItem(storageKey(key));
      if (!raw) return null;
      const parsed = JSON.parse(raw) as CardEntry;
      const kept = parsed.status === 'loaded' || (parsed.status === 'error' && parsed.errorStatus === NOT_FOUND);
      if (!kept) return null;
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
    const kept = entry.status === 'loaded' || (entry.status === 'error' && entry.errorStatus === NOT_FOUND);
    if (!kept) return;
    try {
      storage.setItem(storageKey(key), JSON.stringify(entry));
    } catch {
      // Quota exceeded or disabled — silently drop. Memory cache still works.
    }
  }

  function readOverlay(key: string): Overlay | null {
    const storage = resolveStorage();
    if (!storage) return null;
    try {
      const raw = storage.getItem(storageKey(key));
      return raw ? (JSON.parse(raw) as Overlay) : null;
    } catch {
      return null;
    }
  }

  function writeOverlay(key: string, overlay: Overlay): void {
    overlays.set(key, overlay);
    try {
      resolveStorage()?.setItem(storageKey(key), JSON.stringify(overlay));
    } catch {
      // Quota exceeded or disabled: the overlay lives in memory.
    }
  }

  /** An overlay whose picture part or price part is younger than 24 h. */
  function overlayIsLive(overlay: Overlay | null): overlay is Overlay {
    return !!overlay && (isLive(overlay.refreshedAt) || isLive(overlay.priceCheckedAt));
  }

  // ── Entries ──────────────────────────────────────────────────────────────

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

  /** The entry of a name of the file: the file's entry with the live parts of its overlay. */
  function compose(file: CardEntry, overlay: Overlay | null): CardEntry {
    const entry: CardEntry = { ...file };
    if (!overlay) return entry;
    if (isLive(overlay.refreshedAt)) {
      entry.refreshedAt = overlay.refreshedAt;
      entry.fetchedAt = overlay.fetchedAt;
      if (overlay.image_normal || overlay.image_small || overlay.image_large || overlay.art_crop) {
        entry.image_small = overlay.image_small ?? '';
        entry.image_normal = overlay.image_normal ?? '';
        entry.image_large = overlay.image_large ?? '';
        entry.art_crop = overlay.art_crop ?? '';
      }
    }
    if (isLive(overlay.priceCheckedAt)) {
      entry.priceCheckedAt = overlay.priceCheckedAt;
      // The file's price wins when the file is newer than the refresh.
      const fileIsNewer = file.priceAsOf !== undefined && overlay.priceAsOf !== undefined && file.priceAsOf >= overlay.priceAsOf;
      if (overlay.price !== undefined && overlay.priceAsOf !== undefined && !fileIsNewer) {
        entry.price = overlay.price;
        entry.priceAsOf = overlay.priceAsOf;
      }
    }
    return entry;
  }

  function recompose(key: string): void {
    const file = fileEntries.get(key);
    if (file) put(key, compose(file, overlays.get(key) ?? null), false);
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

  function seed(metadata: RawCardMetadata, pricesAsOf?: string | null): void {
    const parsed = pricesAsOf ? Date.parse(pricesAsOf) : NaN;
    const asOf = Number.isFinite(parsed) ? parsed : undefined;
    if (metadata === seededFrom && asOf === seededAsOf) return;
    seededFrom = metadata;
    seededAsOf = asOf;
    const storage = resolveStorage();
    const stored = storage ? persistedKeys(storage) : new Set<string>();
    for (const [name, meta] of Object.entries(metadata)) {
      const key = name.toLowerCase();
      const file = cardEntryFromFile(name, meta);
      if (asOf !== undefined) file.priceAsOf = asOf;
      fileEntries.set(key, file);
      if (stored.has(key)) {
        // Storage holds each card once: a lookup made before the file held the
        // name goes, and only a live overlay stays.
        const overlay = readOverlay(key);
        if (overlayIsLive(overlay)) overlays.set(key, overlay);
        else {
          overlays.delete(key);
          try { storage!.removeItem(storageKey(key)); } catch { /* nothing to free */ }
        }
      }
      put(key, compose(file, overlays.get(key) ?? null), false);
    }
  }

  // ── The queue ────────────────────────────────────────────────────────────

  function want(key: string, name: string, part: 'lookup' | 'pictures' | 'price', first = false): void {
    let wanted = queued.get(key);
    if (!wanted) {
      wanted = { key, name, first: false, lookup: false, pictures: false, price: false };
      queued.set(key, wanted);
      queue.push(wanted);
    }
    wanted[part] = true;
    if (first) {
      wanted.first = true;
      queue.splice(queue.indexOf(wanted), 1);
      queue.unshift(wanted);
    }
    pump();
  }

  function errorIsHeld(entry: CardEntry): boolean {
    if (!entry.fetchedAt) return false;
    const hold = entry.errorStatus === NOT_FOUND ? TTL_MS : ERROR_RETRY_MS;
    return now() - entry.fetchedAt < hold;
  }

  function enqueue(name: string, options: EnqueueOptions = {}): void {
    if (!name) return;
    const key = name.toLowerCase();
    const existing = cache.get(key) ?? readPersisted(key);
    if (existing && existing !== cache.get(key)) cache.set(key, existing);
    if (existing && existing.status !== 'error') return;
    if (existing && errorIsHeld(existing)) return;
    const wanted = queued.get(key);
    if (wanted?.lookup && !options.first) return;
    want(key, name, 'lookup', options.first);
  }

  function imageFailed(name: string): void {
    if (!name) return;
    const key = name.toLowerCase();
    // Only a picture from the file has another address to find.
    const file = fileEntries.get(key);
    if (!file) return;
    const entry = cache.get(key);
    if (entry?.status !== 'loaded') return;
    if (isLive(entry.refreshedAt)) return;
    // Mark the card before the batch goes, so that a reload inside 24 h does not ask again.
    const t = now();
    writeOverlay(key, { ...pricePart(overlays.get(key)), fetchedAt: t, refreshedAt: t });
    recompose(key);
    want(key, name, 'pictures');
  }

  function priceIsOld(entry: CardEntry): boolean {
    return entry.priceAsOf === undefined || now() - entry.priceAsOf > TTL_MS;
  }

  function refreshPrice(name: string): void {
    if (!name) return;
    const key = name.toLowerCase();
    // A name outside the file has the price of its own lookup, younger than 24 h.
    if (!fileEntries.has(key)) return;
    const entry = cache.get(key);
    if (entry?.status !== 'loaded' || !priceIsOld(entry)) return;
    if (isLive(entry.priceCheckedAt)) return;
    if (pricePending(name)) return;
    want(key, name, 'price');
  }

  function pricePending(name: string): boolean {
    if (!name) return false;
    const key = name.toLowerCase();
    return !!(queued.get(key)?.price || out.get(key)?.price);
  }

  /** Drops the parts of a waiting name that another tab or the seed has done. True while a part remains. */
  function stillWanted(wanted: Wanted): boolean {
    if (wanted.lookup) {
      const existing = cache.get(wanted.key) ?? readPersisted(wanted.key);
      if (existing && existing !== cache.get(wanted.key)) put(wanted.key, existing, false);
      if (existing?.status === 'loaded' || (existing?.status === 'error' && errorIsHeld(existing))) {
        wanted.lookup = false;
        wanted.first = false;
      }
    }
    if (wanted.price && fileEntries.has(wanted.key)) {
      // Another tab may have refreshed the price while this one waited.
      const stored = readOverlay(wanted.key);
      if (stored && isLive(stored.priceCheckedAt) && !isLive(overlays.get(wanted.key)?.priceCheckedAt)) {
        overlays.set(wanted.key, stored);
        recompose(wanted.key);
      }
      if (isLive(overlays.get(wanted.key)?.priceCheckedAt)) wanted.price = false;
    }
    return wanted.lookup || wanted.pictures || wanted.price;
  }

  /** At the turn of bucket 1: the next batch, in order, with up to BATCH_MAX identifiers. */
  function takeBatch(): { batch: Wanted[]; identifiers: string[] } {
    const rank = (w: Wanted) => (w.first ? 0 : w.lookup ? 1 : 2);
    const ordered = [...queue].sort((a, b) => rank(a) - rank(b));
    const batch: Wanted[] = [];
    const identifiers = new Map<string, string>();
    for (const wanted of ordered) {
      if (!stillWanted(wanted)) {
        queue.splice(queue.indexOf(wanted), 1);
        queued.delete(wanted.key);
        continue;
      }
      const identifier = identifierOf(wanted.name);
      const id = normalizeName(identifier);
      if (!identifiers.has(id)) {
        if (identifiers.size >= BATCH_MAX) continue;
        identifiers.set(id, identifier);
      }
      batch.push(wanted);
    }
    for (const wanted of batch) {
      queue.splice(queue.indexOf(wanted), 1);
      queued.delete(wanted.key);
      out.set(wanted.key, wanted);
      if (wanted.lookup) put(wanted.key, { status: 'loading', name: wanted.name }, false);
    }
    return { batch, identifiers: [...identifiers.values()] };
  }

  /** The card of the answer for a name: by the full name, else by the front face. */
  function cardFor(cards: Map<string, ScryfallCard>, name: string): ScryfallCard | null {
    for (const key of nameKeys(name)) {
      const card = cards.get(key);
      if (card) return card;
    }
    return null;
  }

  function settleLookup(wanted: Wanted, card: ScryfallCard | null, answered: boolean, status: number, t: number): void {
    const { key, name } = wanted;
    // The seed arrived while the batch was out: the file's entry stays.
    if (fileEntries.has(key) && cache.get(key)?.status === 'loaded') return;
    if (card) {
      put(key, { ...cardEntryFromScryfall(card, t), priceAsOf: t }, true);
    } else if (answered) {
      put(key, { status: 'error', name, error: 'not_found', errorStatus: NOT_FOUND, fetchedAt: t }, true);
    } else {
      put(key, { status: 'error', name, error: `scryfall ${status}`, errorStatus: status, fetchedAt: t }, false);
    }
  }

  function settlePrice(wanted: Wanted, card: ScryfallCard | null, t: number): void {
    const overlay: Overlay = { ...picturePart(overlays.get(wanted.key)), fetchedAt: t, priceCheckedAt: t };
    const price = formatUsd(card?.prices?.usd);
    // No price keeps the price shown: the file's, as the old refresh is past 24 h.
    if (price) {
      overlay.price = price;
      overlay.priceAsOf = t;
    }
    writeOverlay(wanted.key, overlay);
    recompose(wanted.key);
  }

  function settlePictures(wanted: Wanted, card: ScryfallCard | null, t: number): void {
    // A failed refresh leaves the file's pictures; the mark holds the next try off for 24 h.
    if (!card) return;
    const looked = cardEntryFromScryfall(card, t);
    const overlay: Overlay = {
      ...pricePart(overlays.get(wanted.key)),
      refreshedAt: overlays.get(wanted.key)?.refreshedAt ?? t,
      fetchedAt: t,
      image_small: looked.image_small,
      image_normal: looked.image_normal,
      image_large: looked.image_large,
      art_crop: looked.art_crop,
    };
    writeOverlay(wanted.key, overlay);
    recompose(wanted.key);
  }

  async function settle(batch: Wanted[], response: Response): Promise<void> {
    let answer: ScryfallCollection | null = null;
    let status = response.status;
    if (response.ok) {
      try {
        answer = (await response.json()) as ScryfallCollection;
      } catch {
        status = 0;
      }
    }
    const t = now();
    const cards = new Map<string, ScryfallCard>();
    for (const card of answer?.data ?? []) {
      if (!card?.name) continue;
      for (const key of nameKeys(card.name)) if (!cards.has(key)) cards.set(key, card);
    }
    for (const wanted of batch) {
      out.delete(wanted.key);
      const card = answer ? cardFor(cards, wanted.name) : null;
      if (wanted.lookup) settleLookup(wanted, card, answer !== null, status, t);
      if (wanted.price) settlePrice(wanted, card, t);
      if (wanted.pictures) settlePictures(wanted, card, t);
    }
  }

  /** A batch that could not go (no fetch, or an address that the limiter refuses): its lookups fail. */
  function abandon(batch: Wanted[], err: unknown): void {
    const t = now();
    const message = err instanceof Error ? err.message : String(err);
    for (const wanted of batch) {
      out.delete(wanted.key);
      if (wanted.lookup) put(wanted.key, { status: 'error', name: wanted.name, error: message, fetchedAt: t }, false);
    }
  }

  function pump(): void {
    if (pumping) return;
    pumping = true;
    (async () => {
      try {
        while (queue.length > 0) {
          const taken: { batch: Wanted[] } = { batch: [] };
          try {
            const sent = await limiter.next('lookup', () => {
              const { batch, identifiers } = takeBatch();
              taken.batch = batch;
              return batch.length > 0 ? collectionRequest(identifiers) : null;
            });
            if (sent) await settle(taken.batch, sent.response);
          } catch (err) {
            abandon(taken.batch, err);
          }
        }
      } finally {
        pumping = false;
      }
    })();
  }

  function _reset(): void {
    cache.clear();
    subs.clear();
    queue.length = 0;
    queued.clear();
    out.clear();
    fileEntries.clear();
    overlays.clear();
    seededFrom = null;
    seededAsOf = undefined;
    pumping = false;
    limiter._reset?.();
  }

  return { get, subscribe, enqueue, seed, imageFailed, refreshPrice, pricePending, _reset };
}

export const cardCache: CardCache = createCardCache({ limiter: scryfallLimiter });
