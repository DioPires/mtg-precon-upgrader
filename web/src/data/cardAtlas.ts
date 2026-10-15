// Reverse index for the Card Atlas surface.
//
// Given a card name, return every built deck the card appears in plus the role
// the card plays inside that deck. Brewing decks are indexed separately
// (DEC-568) so they can be surfaced without polluting built-deck usage.
// Match scope (per DEC-197): commander +
// partner commander + 99-card decklist. Keys are front-face names so DFC /
// split / adventure cards reconcile against `priv_data` owned-card entries
// (see web/src/data/cardName.ts).

import type { DeckFull } from './types';
import { frontFace } from './cardName';
import { readOwnedEntries } from './ownedCards';
import { ROLE_LABEL } from './roleLabels';
import { autocompleteUrl, scryfallLimiter, type ScryfallLimiter } from './scryfallLimiter';

export interface CardUsage {
  deckSlug: string;
  deckName: string;
  commander: string;
  partner?: string;
  colors: string;
  bracket: string;
  /** "Commander" / "Partner" / role label (e.g. "Card Draw"). */
  role: string;
  /** Quantity in the deck (1 for non-basics; basics may exceed 1). */
  qty: number;
  /** Display name as authored in deck.json (preserves `Front // Back`). */
  displayName: string;
}

export interface CardAtlasIndex {
  /** front-face lowercase name -> usages in built (physical) decks */
  byName: Map<string, CardUsage[]>;
  /**
   * front-face lowercase name -> usages in brewing decks (DEC-568). Kept in a
   * separate map so built-deck results — the ones that drive card-usage
   * analysis — never mix with virtual builds.
   */
  brewingByName: Map<string, CardUsage[]>;
  /** Sorted unique display names (front-face) seen across built + brewing decks. */
  names: string[];
}

/**
 * Build the reverse index from normalized decks. O(N decks * 99 cards).
 * Use `useMemo` in callers — this is cheap (<5ms for ~12 decks) but worth
 * caching across re-renders.
 */
export function buildCardAtlasIndex(decks: DeckFull[]): CardAtlasIndex {
  const byName = new Map<string, CardUsage[]>();
  const brewingByName = new Map<string, CardUsage[]>();
  const displayByKey = new Map<string, string>();

  const push = (
    target: Map<string, CardUsage[]>,
    rawName: string,
    usage: CardUsage,
  ) => {
    if (!rawName) return;
    const front = frontFace(rawName);
    const key = front.toLowerCase();
    const arr = target.get(key);
    if (arr) arr.push(usage);
    else target.set(key, [usage]);
    if (!displayByKey.has(key)) displayByKey.set(key, front);
  };

  decks.forEach((d) => {
    // Brewing decks are not physical: they are indexed, but never into the
    // built-deck map that card-usage analysis reads.
    const target = d.status === 'brewing' ? brewingByName : byName;
    const identity = {
      deckSlug: d.slug,
      deckName: d.deckName,
      commander: d.commander,
      partner: d.partner,
      colors: d.colors,
      bracket: d.bracket,
    };
    if (d.commander) {
      push(target, d.commander, {
        ...identity,
        role: 'Commander',
        qty: 1,
        displayName: d.commander,
      });
    }
    if (d.partner) {
      push(target, d.partner, {
        ...identity,
        role: 'Partner',
        qty: 1,
        displayName: d.partner,
      });
    }
    (d.rawDecklist || []).forEach((c) => {
      const role = c.primary_role || 'other';
      push(target, c.name, {
        ...identity,
        role: ROLE_LABEL[role] || role,
        qty: c.quantity ?? 1,
        displayName: c.name,
      });
    });
  });

  const names = [...displayByKey.values()].sort((a, b) => a.localeCompare(b));
  return { byName, brewingByName, names };
}

/**
 * Local-first autocomplete: return up to `limit` deck-card names matching the
 * query (case-insensitive prefix match preferred, then substring).
 */
export function localSuggest(
  query: string,
  names: string[],
  limit = 10,
): string[] {
  const q = query.trim().toLowerCase();
  if (!q) return [];
  const prefix: string[] = [];
  const contains: string[] = [];
  for (const n of names) {
    const lc = n.toLowerCase();
    if (lc === q) {
      prefix.unshift(n);
      continue;
    }
    if (lc.startsWith(q)) prefix.push(n);
    else if (lc.includes(q)) contains.push(n);
    if (prefix.length >= limit) break;
  }
  return [...prefix, ...contains].slice(0, limit);
}

/**
 * Scryfall autocomplete fallback. ~250ms typical latency. Caller should
 * debounce calls and deduplicate against local suggestions before showing.
 * The request goes through bucket 2 of the limiter (DEC-1102). While a stop
 * holds, it sends nothing and gives [] at once, and the Atlas keeps its local
 * suggestions (DEC-1131 N5).
 */
export async function scryfallSuggest(
  query: string,
  signal?: AbortSignal,
  limiter: ScryfallLimiter = scryfallLimiter,
): Promise<string[]> {
  const q = query.trim();
  if (q.length < 2) return [];
  if (limiter.stoppedUntil() !== null) return [];
  try {
    const r = await limiter.fetch(autocompleteUrl(q), { signal });
    if (!r.ok) return [];
    const data = (await r.json()) as { data?: string[] };
    return data.data || [];
  } catch {
    return [];
  }
}

/**
 * Owned-cards reader. Reads Shopping's store through `readOwnedEntries`, so the
 * user's existing import is reused — no separate ownership UI in the Atlas
 * surface. Keys are lowercase front-face.
 */
export function loadOwnedMap(): Map<string, number> {
  try {
    if (typeof window === 'undefined') return new Map();
    const out = new Map<string, number>();
    readOwnedEntries(window.localStorage).forEach(([n, q]) => {
      const key = frontFace(n).toLowerCase();
      out.set(key, (out.get(key) || 0) + q);
    });
    return out;
  } catch {
    return new Map();
  }
}
