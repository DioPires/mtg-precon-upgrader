// Shared card-type bucketing used by Shopping and Decklist.
// Prefers Scryfall type_line via cardCache; falls back to deck.json type field.

import { cardCache } from '../data/cardCache';

export const TYPE_ORDER = [
  'Commander', 'Creature', 'Planeswalker', 'Artifact',
  'Enchantment', 'Instant', 'Sorcery', 'Battle', 'Land', 'Other',
] as const;

export type TypeBucket = (typeof TYPE_ORDER)[number];

export function typeBucket(name: string, fallback: string | undefined): TypeBucket {
  const cached = cardCache.get(name);
  return classifyTypeLine(cached?.type_line || fallback || '');
}

/** Pure classifier — exposed for tests that don't want to seed cardCache. */
export function classifyTypeLine(typeLine: string): TypeBucket {
  // Categorize MDFCs by their FRONT (non-land) face: an `Instant // Land` card
  // (Hagra Mauling, Valakut Awakening) belongs in the Instant section, not
  // Lands; a `Land // …` card (Pathways, Westvale Abbey) stays a Land. The
  // front face is the one Scryfall prints first. (DEC-347 board policy.)
  const front = typeLine.split('//')[0];
  const tl = front.toLowerCase();
  if (tl.includes('creature')) return 'Creature';
  if (tl.includes('planeswalker')) return 'Planeswalker';
  if (tl.includes('land')) return 'Land';
  if (tl.includes('artifact')) return 'Artifact';
  if (tl.includes('enchantment')) return 'Enchantment';
  if (tl.includes('instant')) return 'Instant';
  if (tl.includes('sorcery')) return 'Sorcery';
  if (tl.includes('battle')) return 'Battle';
  return 'Other';
}
