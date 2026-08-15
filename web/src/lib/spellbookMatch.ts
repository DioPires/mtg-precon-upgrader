// Paste-mode combo matching against the Spellbook matcher index.
//
// DEC-487 (DEC-476 Phase 0). This mirrors — exactly — the deterministic matching
// model precomputed for fleet decks by scripts/sync_spellbook_combos.py so both
// surfaces agree. Keep normalizeName + the near-miss gate in sync with that
// script. Cost is linear in variants and runs fully client-side; no runtime
// upstream call, so an upstream outage can never break the page (NF-9).

import type { MatcherIndex, MatcherVariant, SpellbookCombo } from '../data/spellbook';

// Near-miss gate — identical to the Python constants.
export const NEAR_MISS_POPULARITY_FLOOR = 1;
export const NEAR_MISS_LIMIT = 120;

const PUNCT_RE = /[^a-z0-9 ]+/g;
const WS_RE = /\s+/g;

/** Casefold + strip accents/punctuation so oracle names compare stably.
 * Mirrors normalize_name() in scripts/sync_spellbook_combos.py. */
export function normalizeName(name: string): string {
  if (!name) return '';
  // Strip combining diacritical marks (U+0300–U+036F) after NFKD decomposition.
  const ascii = name.normalize('NFKD').replace(/[\u0300-\u036f]/g, '');
  return ascii.toLowerCase().replace(PUNCT_RE, ' ').replace(WS_RE, ' ').trim();
}

/** Normalized full name plus front-face key for split/DFC/adventure cards. */
export function nameKeys(name: string): string[] {
  const keys = new Set<string>();
  const full = normalizeName(name);
  if (full) keys.add(full);
  if (name.includes('//')) {
    const front = normalizeName(name.split('//', 1)[0]);
    if (front) keys.add(front);
  }
  return [...keys];
}

export interface ParsedDeck {
  cardNames: string[];
  commanderNames: string[];
  /** IN-6 — non-blank, non-comment lines a card name could not be extracted from. */
  unresolved: string[];
}

/** Parse a pasted decklist. Tolerant of "3 Card", "3x Card", set/collector
 * suffixes, "SB:" sideboard markers, and commander tags (CMDR / [Commander]).
 * Lines that survive as content but yield no name are collected in `unresolved`
 * so the caller can surface them and proceed on the remainder (IN-6). IN-1. */
export function parseDecklist(text: string): ParsedDeck {
  const cardNames: string[] = [];
  const commanderNames: string[] = [];
  const unresolved: string[] = [];
  for (const rawLine of text.split(/\r?\n/)) {
    const original = rawLine.trim();
    let line = original;
    if (!line || line.startsWith('#') || line.startsWith('//')) continue;
    // Section headers like "Commander", "Deck", "Sideboard".
    if (/^(commander|deck|maybeboard|sideboard|companion)\s*:?\s*$/i.test(line)) continue;
    if (/^sb:/i.test(line)) continue;

    let isCommander = false;
    // Trailing/leading commander markers used by Moxfield/Archidekt exports.
    const cmdrTag = /\*?cmdr\*?|\[commander\]|\(commander\)/i;
    if (cmdrTag.test(line)) {
      isCommander = true;
      line = line.replace(cmdrTag, '').trim();
    }

    // Strip leading quantity ("3", "3x").
    line = line.replace(/^(\d+)\s*[xX]?\s+/, '');
    // Strip trailing set/collector suffixes: "(NEO) 123", "(NEO)", "123 *F*".
    line = line.replace(/\s+\([0-9A-Za-z]{2,6}\)(\s+[0-9A-Za-z-]+)?\s*(\*[^*]+\*)?\s*$/, '').trim();
    line = line.replace(/\s+<[^>]*>\s*$/, '').trim();
    // A content line that reduced to nothing (or has no letters) is unresolvable.
    if (!line || !/[a-zA-Z]/.test(line)) {
      unresolved.push(original);
      continue;
    }

    if (isCommander) commanderNames.push(line);
    else cardNames.push(line);
  }
  return { cardNames, commanderNames, unresolved };
}

function resolveCombo(
  index: MatcherIndex,
  v: MatcherVariant,
  distance: number,
  missing?: { cards: string[]; templates: { name: string; query: string }[] },
): SpellbookCombo {
  const cmdrIds = new Set(v.c);
  return {
    id: v.id,
    permalink: `https://commanderspellbook.com/combo/${v.id}/`,
    cards: v.u.map((id) => ({
      name: index.cards[String(id)]?.n ?? `#${id}`,
      mustBeCommander: cmdrIds.has(id),
      quantity: 1,
      zones: [],
    })),
    templates: v.r.map((id) => ({
      name: index.templates[String(id)]?.n ?? 'a required card',
      query: index.templates[String(id)]?.q ?? '',
    })),
    produces: v.p.map((id) => index.features[String(id)]).filter(Boolean),
    identity: v.i,
    bracketTag: v.b,
    manaNeeded: '',
    manaValueNeeded: v.m,
    prerequisites: { easy: '', notable: '' },
    steps: '',
    notes: '',
    prices: {},
    popularity: v.pop,
    distance,
    ...(missing ? { missing } : {}),
  };
}

export interface MatchResult {
  included: SpellbookCombo[];
  nearMisses: SpellbookCombo[];
  nearMissesTotal: number;
}

/** Classify every matcher-index variant against a parsed deck. Same rules and
 * ranking as the per-deck precompute; near-misses ranked by popularity and
 * capped at NEAR_MISS_LIMIT with the true total returned. */
export function matchDecklist(
  deck: Pick<ParsedDeck, 'cardNames' | 'commanderNames'>,
  index: MatcherIndex,
): MatchResult {
  const allKeys = new Set<string>();
  const commanderKeys = new Set<string>();
  for (const n of deck.cardNames) for (const k of nameKeys(n)) allKeys.add(k);
  for (const n of deck.commanderNames) for (const k of nameKeys(n)) commanderKeys.add(k);
  for (const k of commanderKeys) allKeys.add(k); // commanders castable from CZ

  const included: SpellbookCombo[] = [];
  const near: SpellbookCombo[] = [];

  for (const v of index.variants) {
    const missingCards: string[] = [];
    let present = 0;
    for (const id of v.u) {
      const name = index.cards[String(id)]?.n ?? '';
      const keys = nameKeys(name);
      const target = v.c.includes(id) ? commanderKeys : allKeys;
      const satisfied = keys.some((k) => target.has(k));
      if (satisfied) present += 1;
      else missingCards.push(name);
    }
    const unmet = missingCards.length + v.r.length;

    if (unmet === 0) {
      included.push(resolveCombo(index, v, 0));
      continue;
    }
    if (unmet < 1 || unmet > 2) continue;
    if (present < 1 || present < unmet) continue;
    if (v.pop < NEAR_MISS_POPULARITY_FLOOR) continue;

    const templates = v.r.map((id) => ({
      name: index.templates[String(id)]?.n ?? 'a required card',
      query: index.templates[String(id)]?.q ?? '',
    }));
    near.push(resolveCombo(index, v, unmet, { cards: missingCards, templates }));
  }

  included.sort((a, b) => b.popularity - a.popularity || (a.id < b.id ? -1 : 1));
  near.sort(
    (a, b) => a.distance - b.distance || b.popularity - a.popularity || (a.id < b.id ? -1 : 1),
  );
  return { included, nearMisses: near.slice(0, NEAR_MISS_LIMIT), nearMissesTotal: near.length };
}
