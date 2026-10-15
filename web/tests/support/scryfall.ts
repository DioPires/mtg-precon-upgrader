// Scryfall answers for the e2e suite, built from repository data (DEC-1045).
//
// One committed file holds everything a page asks Scryfall for:
//   data/card-metadata.json   card name → mana cost, mana value, type line,
//                             picture path, USD and EUR price (DEC-1075)
// The app reads the same file (DEC-1102), so a lookup gives the picture
// addresses and the price that the app's own seed holds. The same card gets the
// same answer on every run and every machine. A name that card-metadata.json
// lacks gets a 404, as Scryfall gives.

import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { cardEntryFromFile, cardImageUrl } from '../../src/data/cardEntry';
import { normalizeName } from '../../src/lib/spellbookMatch';

const DATA_DIR = resolve(dirname(fileURLToPath(import.meta.url)), '..', '..', '..', 'data');

interface CardMeta {
  cmc: number;
  colors: string[];
  mana_cost: string;
  oracle_text: string;
  power: string | null;
  toughness: string | null;
  type_line: string;
  layout?: string;
  image: string;
  usd: number | null;
  eur: number | null;
}

interface Repo {
  meta: Record<string, CardMeta>;
  /** Folded full name, and each folded face of a `//` name → name in card-metadata.json. */
  byKey: Map<string, string>;
  /** Front face of a `//` name → that `//` name. */
  byFront: Map<string, string>;
}

let repo: Repo | undefined;

function faces(name: string): string[] {
  return name.includes('//') ? name.split('//').map((face) => face.trim()) : [];
}

function loadRepo(): Repo {
  if (repo) return repo;
  const read = (file: string) => JSON.parse(readFileSync(resolve(DATA_DIR, file), 'utf8'));
  const meta = read('card-metadata.json') as Record<string, CardMeta>;
  const byKey = new Map<string, string>();
  const names = Object.keys(meta).sort();
  for (const name of names) byKey.set(normalizeName(name), name);
  // A face never takes the key of a card that has that full name.
  for (const name of names) {
    for (const face of faces(name)) {
      const key = normalizeName(face);
      if (!byKey.has(key)) byKey.set(key, name);
    }
  }
  const byFront = new Map(names.filter((name) => name.includes('//')).map((name) => [faces(name)[0], name]));
  repo = { meta, byKey, byFront };
  return repo;
}

// Scryfall's sizes for each image version. An image box that takes its height
// from the picture keeps the proportions it has with real card art.
const IMAGE_SIZES: Record<string, [width: number, height: number]> = {
  small: [146, 204],
  normal: [488, 680],
  large: [672, 936],
  png: [745, 1040],
  art_crop: [626, 457],
  border_crop: [480, 680],
};

/** The one picture the stub serves for every card: a flat rectangle of the size asked for. */
function placeholderImage(version: string | null): string {
  const [w, h] = IMAGE_SIZES[version ?? ''] ?? IMAGE_SIZES.large;
  return (
    `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}">` +
    `<rect width="${w}" height="${h}" fill="#2b2a33"/></svg>`
  );
}

/** Scryfall's addresses for the card's picture, from the path in card-metadata.json, as the app builds them. */
function imageUris(card: CardMeta) {
  return {
    small: cardImageUrl('small', card.image),
    normal: cardImageUrl('normal', card.image),
    large: cardImageUrl('large', card.image),
    art_crop: cardImageUrl('art_crop', card.image),
  };
}

const money = (amount: number | null) => (amount == null ? null : amount.toFixed(2));

/**
 * Scryfall's `card_faces` for a one-sided card with two halves (adventure, split,
 * room, prepare): card-metadata.json holds both mana costs and both type lines,
 * joined by ` // `, under the `//` name and again under the front name alone.
 * The whole card keeps the joined values and the pictures, as Scryfall sends
 * them. A two-sided card (transform, modal_dfc) gets no faces: card-metadata.json
 * holds only the cost of its front, which is the cost that the app shows.
 */
function cardFaces(name: string, card: CardMeta) {
  const costs = card.mana_cost.split(' // ');
  const types = card.type_line.split(' // ');
  const names = faces(loadRepo().byFront.get(name) ?? name);
  if (costs.length !== 2 || types.length !== 2 || names.length !== 2) return undefined;
  return names.map((face, i) => ({
    object: 'card_face',
    name: face,
    mana_cost: costs[i],
    type_line: types[i],
  }));
}

/** The card object for `/cards/named`, or null when card-metadata.json has no such name. */
function cardObject(query: string) {
  const { meta, byKey } = loadRepo();
  const name = byKey.get(normalizeName(query));
  if (!name) return null;
  const card = meta[name];
  const card_faces = cardFaces(name, card);
  return {
    object: 'card',
    name,
    layout: card.layout ?? 'normal',
    mana_cost: card.mana_cost,
    cmc: card.cmc,
    type_line: card.type_line,
    oracle_text: card.oracle_text,
    colors: card.colors,
    ...(card.power == null ? {} : { power: card.power, toughness: card.toughness }),
    ...(card_faces ? { card_faces } : {}),
    image_uris: imageUris(card),
    prices: { usd: money(card.usd), eur: money(card.eur) },
  };
}

function autocomplete(query: string): string[] {
  const q = normalizeName(query);
  if (q.length < 2) return [];
  const names = [...new Set(loadRepo().byKey.values())].sort();
  const starts = names.filter((name) => normalizeName(name).startsWith(q));
  const contains = names.filter((name) => !starts.includes(name) && normalizeName(name).includes(q));
  return [...starts, ...contains].slice(0, 20);
}

export type AnswerKind = 'card' | 'card-image' | 'autocomplete' | 'image';

export interface Answer {
  kind: AnswerKind;
  status: number;
  contentType: string;
  body: string;
  /** The card name asked for, when the answer is a 404. */
  notFound?: string;
}

const json = (kind: AnswerKind, status: number, body: unknown): Answer => ({
  kind,
  status,
  contentType: 'application/json; charset=utf-8',
  body: JSON.stringify(body),
});

const image = (kind: AnswerKind, version: string | null): Answer => ({
  kind,
  status: 200,
  contentType: 'image/svg+xml',
  body: placeholderImage(version),
});

/**
 * The answer for one request to a Scryfall host. Null means the stub does not
 * know the request; the caller treats that as a failure of the test.
 */
export function answerFor(url: URL): Answer | null {
  if (url.hostname === 'cards.scryfall.io') return image('image', url.pathname.split('/')[1]);
  if (url.hostname !== 'api.scryfall.com') return null;

  if (url.pathname === '/cards/autocomplete') {
    const data = autocomplete(url.searchParams.get('q') ?? '');
    return json('autocomplete', 200, { object: 'catalog', total_values: data.length, data });
  }

  if (url.pathname === '/cards/named') {
    const query = url.searchParams.get('fuzzy') ?? url.searchParams.get('exact') ?? '';
    const wantsImage = url.searchParams.get('format') === 'image';
    const kind = wantsImage ? 'card-image' : 'card';
    const card = cardObject(query);
    if (!card) {
      return {
        ...json(kind, 404, {
          object: 'error',
          code: 'not_found',
          status: 404,
          details: `No cards found matching “${query}”`,
        }),
        notFound: query,
      };
    }
    // Scryfall redirects an image lookup to cards.scryfall.io; the stub answers with the picture.
    return wantsImage ? image(kind, url.searchParams.get('version')) : json(kind, 200, card);
  }

  return null;
}

/**
 * The entries of `cards: 'seeded'`: key (the lower-case name the app asks for)
 * → entry, without `fetchedAt`. Every name of card-metadata.json gets the
 * entry that the app's own seed makes (cardEntryFromFile). Each face of a `//`
 * name that the file does not hold as a name gets the entry of its whole card,
 * under the whole card's name, as a lookup of that face gives it.
 */
export function cardCacheSeed(): Record<string, object> {
  const { meta, byKey } = loadRepo();
  const seed: Record<string, object> = {};
  for (const name of Object.keys(meta)) seed[name.toLowerCase()] = cardEntryFromFile(name, meta[name]);
  for (const name of Object.keys(meta)) {
    for (const face of faces(name)) {
      const whole = byKey.get(normalizeName(face))!;
      seed[face.toLowerCase()] ??= cardEntryFromFile(whole, meta[whole]);
    }
  }
  return seed;
}

/** card-metadata.json with no price, for `cards: 'none'`: the layout with no prices. */
export function cardMetadataWithoutPrices(): string {
  const { meta } = loadRepo();
  const bare: Record<string, CardMeta> = {};
  for (const [name, card] of Object.entries(meta)) bare[name] = { ...card, usd: null, eur: null };
  return JSON.stringify(bare);
}
