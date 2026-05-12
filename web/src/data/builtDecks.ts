// Built-decks reservation logic for the Shopping artboard.
//
// A "built deck" is a deck the user has already physically assembled.
// Cards in a built deck reserve owned copies, reducing what's available to
// shop with. localStorage-backed so selections survive reloads (improvement
// over the legacy app, which lost state on refresh).

import type { DeckFull } from './types';
import { frontFace } from './cardName';

const STORAGE_KEY = 'grimoire-built-decks';

const BASIC_LANDS = new Set([
  'Plains', 'Island', 'Swamp', 'Mountain', 'Forest', 'Wastes',
  'Snow-Covered Plains', 'Snow-Covered Island', 'Snow-Covered Swamp',
  'Snow-Covered Mountain', 'Snow-Covered Forest',
]);

// normalize.ts names the commander group `'Commanders'` (plural) when a
// partner is present and `'Commander'` otherwise. Skip both — the
// commander/partner are claimed explicitly above.
const COMMANDER_GROUPS = new Set(['Commander', 'Commanders']);

export function getBuiltDecks(): Set<string> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return new Set();
    const arr = JSON.parse(raw);
    if (Array.isArray(arr)) return new Set(arr.filter((x): x is string => typeof x === 'string'));
  } catch {
    // ignore parse / quota errors
  }
  return new Set();
}

export function setBuiltDecks(s: Set<string>): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify([...s]));
  } catch {
    // ignore quota
  }
}

export function toggleBuiltDeck(id: string): Set<string> {
  const cur = getBuiltDecks();
  if (cur.has(id)) cur.delete(id);
  else cur.add(id);
  setBuiltDecks(cur);
  return cur;
}

/**
 * Count, per card name, how many built decks claim a copy.
 *
 * Each built deck contributes at most 1 claim per unique card name (a deck
 * with two listed copies of a card still only needs 1 owned slot per copy in
 * its own decklist, but for the cross-deck reservation we treat presence as
 * a single claim — matches legacy `aggregateShoppingCards`).
 *
 * Includes commander + partner. Excludes basic lands.
 */
export function aggregateBuiltClaims(
  builtSlugs: Set<string>,
  allDecks: DeckFull[],
): Map<string, number> {
  const claims = new Map<string, number>();
  builtSlugs.forEach((slug) => {
    const d = allDecks.find((x) => x.slug === slug);
    if (!d) return;
    // Keys are front-face names so DFC / split / adventure cards reconcile
    // against the same key the owned map uses (see data/cardName.ts).
    const keys = new Set<string>();
    if (d.commander && !BASIC_LANDS.has(d.commander)) keys.add(frontFace(d.commander));
    if (d.partner && !BASIC_LANDS.has(d.partner)) keys.add(frontFace(d.partner));
    (d.list || []).forEach((group) => {
      if (COMMANDER_GROUPS.has(group.name)) return;
      (group.cards || []).forEach((c) => {
        if (c.n && !BASIC_LANDS.has(c.n)) keys.add(frontFace(c.n));
      });
    });
    keys.forEach((k) => claims.set(k, (claims.get(k) || 0) + 1));
  });
  return claims;
}

export interface PlannedCard {
  /** Number of copies the planned (selected) decks need. */
  quantity: number;
}

export interface BuyOwnRow<T extends PlannedCard> {
  name: string;
  /** Original planned info merged with the resolved buy/own quantity. */
  info: T;
  /** Resolved quantity for this row (need-to-buy or already-own count). */
  qty: number;
  /** Number of built decks reserving owned copies of this card. */
  reservedBy: number;
}

export interface BuyOwnSplit<T extends PlannedCard> {
  buy: BuyOwnRow<T>[];
  own: BuyOwnRow<T>[];
}

/**
 * Pure reservation math. Direct port of legacy `splitByOwnership`.
 *
 *   availableForShopping = max(0, ownedQty - builtClaims)
 *   needQty              = max(0, planned.quantity - availableForShopping)
 *   ownQty               = min(planned.quantity, availableForShopping)
 *
 * `reservedBy` is non-zero only when reservations actually reduced the
 * effective owned pool for that card — this is what the UI uses to decide
 * whether to render the "Reserved by N built deck(s)" subline.
 */
export function computeBuyOwnSplit<T extends PlannedCard>(
  planned: Map<string, T>,
  owned: Map<string, number>,
  builtClaims: Map<string, number>,
): BuyOwnSplit<T> {
  const buy: BuyOwnRow<T>[] = [];
  const own: BuyOwnRow<T>[] = [];
  planned.forEach((info, name) => {
    const ownedQty = owned.get(name) || 0;
    const builtQty = builtClaims.get(name) || 0;
    const availableForShopping = Math.max(0, ownedQty - builtQty);
    const needQty = Math.max(0, info.quantity - availableForShopping);
    const ownQty = Math.min(info.quantity, availableForShopping);
    const reservedBy = ownedQty > 0 ? Math.min(ownedQty, builtQty) : 0;
    if (needQty > 0) buy.push({ name, info, qty: needQty, reservedBy });
    if (ownQty > 0) own.push({ name, info, qty: ownQty, reservedBy });
  });
  return { buy, own };
}
