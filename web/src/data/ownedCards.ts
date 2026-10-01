// Owned-cards inventory: the user's imported ManaBox/CSV collection.
//
// This is user data, not a derivable cache — it cannot be re-fetched. When the
// browser is out of localStorage room, the re-fetchable caches yield to it, and
// a write that still fails is reported rather than swallowed (DEC-941/DEC-942).
//
// Keys are stored verbatim (front-face, original case) as Shopping writes them;
// cardAtlas.ts lowercases on its own read.

export const OWNED_KEY = 'grimoire-owned-cards';

/**
 * Prefixes of purely derivable caches — the deck-JSON envelope and the Scryfall
 * card cache. Both re-populate from the network, so they are what gets dropped
 * when the owned map does not fit.
 */
const EVICTABLE_PREFIXES = ['gv1-deck-data-', 'gv1-card:'];

/** Drop every derivable cache key. Returns how many were removed. */
export function evictDerivableCaches(storage: Storage): number {
  const doomed: string[] = [];
  for (let i = 0; i < storage.length; i += 1) {
    const key = storage.key(i);
    if (key && EVICTABLE_PREFIXES.some((p) => key.startsWith(p))) doomed.push(key);
  }
  doomed.forEach((k) => storage.removeItem(k));
  return doomed.length;
}

/**
 * Persist the owned map.
 *
 * Returns `false` when the write did not land, so callers never report success
 * over a dropped save. On a quota failure the derivable caches are evicted and
 * the write is retried exactly once.
 */
export function saveOwned(
  map: Map<string, number>,
  storage: Storage = localStorage,
): boolean {
  const payload = JSON.stringify([...map]);
  try {
    storage.setItem(OWNED_KEY, payload);
    return true;
  } catch {
    // Fall through to evict-and-retry.
  }
  try {
    evictDerivableCaches(storage);
    storage.setItem(OWNED_KEY, payload);
    return true;
  } catch {
    return false;
  }
}
