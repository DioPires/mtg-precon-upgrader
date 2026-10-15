// The two ways a card entry comes about (DEC-1102, DEC-1131): from an entry of
// data/card-metadata.json, and from a card of a /cards/collection answer. The e2e
// stub builds its seed with cardEntryFromFile too (tests/support/scryfall.ts).

import type { CardEntry } from './cardCache';
import type { RawCardMetadataEntry } from './types';

/** Scryfall's image host. A picture's address is `<host>/<size>/<image>` for each size. */
export const CARD_IMAGE_HOST = 'https://cards.scryfall.io';

export type CardImageSize = 'small' | 'normal' | 'large' | 'art_crop';

export function cardImageUrl(size: CardImageSize, image: string): string {
  return `${CARD_IMAGE_HOST}/${size}/${image}`;
}

/** A USD price as the app shows it: `$1.42`, or null when there is none. */
export function formatUsd(usd: number | string | null | undefined): string | null {
  if (usd === null || usd === undefined || usd === '') return null;
  const amount = typeof usd === 'number' ? usd : parseFloat(usd);
  return Number.isFinite(amount) ? `$${amount.toFixed(2)}` : null;
}

/**
 * The entry for one name of data/card-metadata.json. A card with two halves
 * holds a joined cost there, such as `{1}{R} // {2}{R}`; the app shows the
 * front half's cost, as a lookup gives it.
 */
export function cardEntryFromFile(name: string, meta: RawCardMetadataEntry): CardEntry {
  const image = meta.image ?? '';
  const url = (size: CardImageSize) => (image ? cardImageUrl(size, image) : '');
  return {
    status: 'loaded',
    name,
    mana_cost: (meta.mana_cost ?? '').split(' // ')[0],
    cmc: meta.cmc,
    type_line: meta.type_line ?? '',
    image_small: url('small'),
    image_normal: url('normal'),
    image_large: url('large'),
    art_crop: url('art_crop'),
    price: formatUsd(meta.usd),
  };
}

interface ScryfallImageUris {
  small?: string;
  normal?: string;
  large?: string;
  art_crop?: string;
}

interface ScryfallFace {
  mana_cost?: string;
  type_line?: string;
  image_uris?: ScryfallImageUris;
}

/** The part of a card object that the app reads. */
export interface ScryfallCard extends ScryfallFace {
  name: string;
  cmc?: number;
  card_faces?: ScryfallFace[];
  prices?: { usd?: string | null };
}

/** The answer to a POST to /cards/collection. `data` holds the cards found, `not_found` the identifiers that matched none. */
export interface ScryfallCollection {
  object?: 'list';
  data?: ScryfallCard[];
  not_found?: Array<{ name?: string }>;
}

/**
 * The entry for a card of a /cards/collection answer. A card with faces shows
 * its first face's cost. A transform or modal_dfc card has `image_uris` only in
 * `card_faces`, so the pictures come from the first face then.
 */
export function cardEntryFromScryfall(data: ScryfallCard, fetchedAt: number): CardEntry {
  const face = data.card_faces?.[0] ?? data;
  const images = data.image_uris ?? face.image_uris ?? {};
  return {
    status: 'loaded',
    name: data.name,
    mana_cost: face.mana_cost || data.mana_cost || '',
    cmc: data.cmc,
    type_line: data.type_line || face.type_line || '',
    image_small: images.small || '',
    image_normal: images.normal || '',
    image_large: images.large || '',
    art_crop: images.art_crop || '',
    price: formatUsd(data.prices?.usd),
    fetchedAt,
  };
}
