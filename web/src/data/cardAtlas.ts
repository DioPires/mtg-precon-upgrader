// Reverse index for the Card Atlas surface.
//
// Given a card name, return every built deck the card appears in plus the role
// the card plays inside that deck. Match scope (per DEC-197): commander +
// partner commander + 99-card decklist. Keys are front-face names so DFC /
// split / adventure cards reconcile against `priv_data` owned-card entries
// (see web/src/data/cardName.ts).

import type { DeckFull } from './types';
import { frontFace } from './cardName';

const ROLE_LABEL: Record<string, string> = {
  land: 'Lands',
  ramp: 'Ramp',
  'card-draw': 'Card Draw',
  counterspell: 'Counters',
  'removal-spot': 'Spot Removal',
  'removal-board': 'Board Wipes',
  recursion: 'Recursion',
  protection: 'Protection',
  payoff: 'Payoffs',
  threat: 'Threats',
  wincon: 'Win-Cons',
  engine: 'Engine',
  tutor: 'Tutors',
  utility: 'Utility',
  other: 'Other',
};

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
  /** front-face lowercase name -> usages */
  byName: Map<string, CardUsage[]>;
  /** Sorted unique display names (front-face) seen across all decks. */
  names: string[];
}

/**
 * Build the reverse index from normalized decks. O(N decks * 99 cards).
 * Use `useMemo` in callers — this is cheap (<5ms for ~12 decks) but worth
 * caching across re-renders.
 */
export function buildCardAtlasIndex(decks: DeckFull[]): CardAtlasIndex {
  const byName = new Map<string, CardUsage[]>();
  const displayByKey = new Map<string, string>();

  const push = (rawName: string, usage: CardUsage) => {
    if (!rawName) return;
    const front = frontFace(rawName);
    const key = front.toLowerCase();
    const arr = byName.get(key);
    if (arr) arr.push(usage);
    else byName.set(key, [usage]);
    if (!displayByKey.has(key)) displayByKey.set(key, front);
  };

  // Brewing decks are not physical and must not contribute to card-usage analysis.
  const physical = decks.filter((d) => d.status !== 'brewing');
  physical.forEach((d) => {
    if (d.commander) {
      push(d.commander, {
        deckSlug: d.slug,
        deckName: d.deckName,
        commander: d.commander,
        partner: d.partner,
        colors: d.colors,
        bracket: d.bracket,
        role: 'Commander',
        qty: 1,
        displayName: d.commander,
      });
    }
    if (d.partner) {
      push(d.partner, {
        deckSlug: d.slug,
        deckName: d.deckName,
        commander: d.commander,
        partner: d.partner,
        colors: d.colors,
        bracket: d.bracket,
        role: 'Partner',
        qty: 1,
        displayName: d.partner,
      });
    }
    (d.rawDecklist || []).forEach((c) => {
      const role = c.primary_role || 'other';
      push(c.name, {
        deckSlug: d.slug,
        deckName: d.deckName,
        commander: d.commander,
        partner: d.partner,
        colors: d.colors,
        bracket: d.bracket,
        role: ROLE_LABEL[role] || role,
        qty: c.quantity ?? 1,
        displayName: c.name,
      });
    });
  });

  const names = [...displayByKey.values()].sort((a, b) => a.localeCompare(b));
  return { byName, names };
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
 */
export async function scryfallSuggest(
  query: string,
  fetchImpl: typeof fetch = fetch,
  signal?: AbortSignal,
): Promise<string[]> {
  const q = query.trim();
  if (q.length < 2) return [];
  const url = `https://api.scryfall.com/cards/autocomplete?q=${encodeURIComponent(q)}`;
  try {
    const r = await fetchImpl(url, { signal });
    if (!r.ok) return [];
    const data = (await r.json()) as { data?: string[] };
    return data.data || [];
  } catch {
    return [];
  }
}

/**
 * Owned-cards reader. Mirrors Shopping.tsx so the user's existing import is
 * reused — no separate ownership UI in the Atlas surface. Keys are front-face.
 */
const OWNED_KEY = 'grimoire-owned-cards';

export function loadOwnedMap(): Map<string, number> {
  try {
    if (typeof window === 'undefined') return new Map();
    const raw = window.localStorage.getItem(OWNED_KEY);
    if (!raw) return new Map();
    const out = new Map<string, number>();
    (JSON.parse(raw) as Array<[string, number]>).forEach(([n, q]) => {
      const key = frontFace(n).toLowerCase();
      out.set(key, (out.get(key) || 0) + q);
    });
    return out;
  } catch {
    return new Map();
  }
}
