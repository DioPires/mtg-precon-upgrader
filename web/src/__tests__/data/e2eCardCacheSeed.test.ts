// DEC-1073, DEC-1102, DEC-1131 — the e2e stub's card entries against the app's own.
//
// The app seeds its card cache from data/card-metadata.json (cardEntryFromFile).
// The stub's cardCacheSeed() uses the same function, and its /cards/collection
// answers take the pictures and prices from the same file. These cases hold the
// three together for every name: the app's seed, the stub's seed, and the entry
// that the app makes from the stub's batch answer.

import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { createCardCache } from '../../data/cardCache';
import { cardEntryFromFile, cardEntryFromScryfall, type ScryfallCollection } from '../../data/cardEntry';
import type { RawCardMetadata } from '../../data/types';
import { answerFor, cardCacheSeed } from '../../../tests/support/scryfall';
import { collectionRequest, COLLECTION_URL } from '../../data/scryfallLimiter';

/** The stub's answer to one batch of `names`. */
function batch(names: string[], usdBump = 0) {
  const answer = answerFor(new URL(COLLECTION_URL), { method: 'POST', body: collectionRequest(names).body }, { usdBump });
  if (!answer) throw new Error('the stub has no answer for /cards/collection');
  return { status: answer.status, body: JSON.parse(answer.body) as ScryfallCollection & { object: string } };
}

const FILE = JSON.parse(
  readFileSync(resolve(__dirname, '../../../../data/card-metadata.json'), 'utf8'),
) as RawCardMetadata;

describe('e2e stub: cardCacheSeed()', () => {
  it("holds, for every name of card-metadata.json, the entry of the app's own seed", () => {
    const cache = createCardCache({ storage: null });
    cache.seed(FILE);
    const seed = cardCacheSeed();
    const names = Object.keys(FILE);
    expect(names.length).toBeGreaterThan(1500);
    for (const name of names) {
      expect(seed[name.toLowerCase()], name).toStrictEqual(cache.get(name));
    }
  });

  it("gives, for every name of the file, the card whose entry is the app's own seed of that card", () => {
    // A batch sends a `//` name as its front face; the stub answers with the whole card.
    const names = Object.keys(FILE);
    const asked = names.map((name) => name.split(' // ')[0]);
    const answered: string[] = [];
    for (let i = 0; i < asked.length; i += 75) {
      const { status, body } = batch(asked.slice(i, i + 75));
      expect(status).toBe(200);
      expect(body.not_found).toEqual([]);
      for (const card of body.data!) {
        const entry = cardEntryFromScryfall(card, 0);
        delete entry.fetchedAt;
        expect(entry, card.name).toStrictEqual(cardEntryFromFile(card.name, FILE[card.name]));
        answered.push(card.name);
      }
    }
    expect(answered).toHaveLength(names.length);
    // A front face that the file also holds as a name gets the whole `//` card.
    expect(answered.filter((name) => name.includes(' // ')).length).toBe(2 * names.filter((n) => n.includes(' // ')).length);
  });

  it('holds no joined mana cost', () => {
    const joined = Object.entries(cardCacheSeed()).filter(([, e]) =>
      (e as { mana_cost: string }).mana_cost.includes(' // '),
    );
    expect(joined.map(([key]) => key)).toEqual([]);
  });
});

describe('e2e stub: POST /cards/collection', () => {
  const dfc = Object.entries(FILE).find(([name, meta]) => name.includes(' // ') && meta.layout === 'transform')!;
  const mdfc = Object.entries(FILE).find(([name, meta]) => name.includes(' // ') && meta.layout === 'modal_dfc')!;
  const halves = Object.entries(FILE).find(([name, meta]) => name.includes(' // ') && !meta.layout)!;

  it('keeps the order asked, matches a front face without regard to case and accents, and sends a full `//` name to not_found', () => {
    const front = halves[0].split(' // ')[0];
    const { status, body } = batch(['Sol Ring', front.toUpperCase(), halves[0], 'Nonesuch Card', 'sol ring']);
    expect(status).toBe(200);
    expect(body.object).toBe('list');
    expect(body.data!.map((card) => card.name)).toEqual(['Sol Ring', halves[0], 'Sol Ring']);
    expect(body.not_found).toEqual([{ name: halves[0] }, { name: 'Nonesuch Card' }]);
  });

  it('gives every `//` card its faces, and a transform or modal_dfc card its pictures only there', () => {
    const { body } = batch([dfc[0], mdfc[0], halves[0]].map((name) => name.split(' // ')[0]));
    const [transform, modal, adventure] = body.data!;
    for (const card of [transform, modal]) {
      expect(card.image_uris).toBeUndefined();
      expect(card.card_faces).toHaveLength(2);
      expect(card.card_faces![0].image_uris?.normal).toBe(`https://cards.scryfall.io/normal/${FILE[card.name].image}`);
    }
    expect(adventure.card_faces).toHaveLength(2);
    expect(adventure.image_uris?.normal).toBe(`https://cards.scryfall.io/normal/${halves[1].image}`);
  });

  it('answers more than 75 names with a 422', () => {
    const { status, body } = batch(Array.from({ length: 76 }, () => 'Sol Ring'));
    expect(status).toBe(422);
    expect(body.object).toBe('error');
  });

  it('adds the bump to each usd, and leaves a null usd null', () => {
    const noPrice = Object.keys(FILE).find((name) => FILE[name].usd == null && !name.includes(' // '))!;
    const { body } = batch(['Sol Ring', noPrice], 1);
    expect(body.data![0].prices?.usd).toBe((FILE['Sol Ring'].usd! + 1).toFixed(2));
    expect(body.data![1].prices?.usd).toBeNull();
  });
});
