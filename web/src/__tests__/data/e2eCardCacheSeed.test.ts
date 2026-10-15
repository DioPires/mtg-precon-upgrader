// DEC-1073, DEC-1102 — the e2e stub's card entries against the app's own.
//
// The app seeds its card cache from data/card-metadata.json (cardEntryFromFile).
// The stub's cardCacheSeed() uses the same function, and its /cards/named
// answers take the pictures and prices from the same file. These cases hold the
// three together for every name: the app's seed, the stub's seed, and the entry
// that the app makes from the stub's lookup answer.

import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { createCardCache } from '../../data/cardCache';
import { cardEntryFromScryfall, type ScryfallCard } from '../../data/cardEntry';
import type { RawCardMetadata } from '../../data/types';
import { answerFor, cardCacheSeed } from '../../../tests/support/scryfall';
import { lookupUrl } from '../../data/scryfallLimiter';

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

  it("holds, for every key, the entry that the app makes from the stub's lookup answer", () => {
    const seed = cardCacheSeed();
    const fromLookup: Record<string, object> = {};
    for (const key of Object.keys(seed)) {
      const answer = answerFor(new URL(lookupUrl(key)));
      if (!answer || answer.status !== 200) throw new Error(`the stub has no card for ${key}`);
      const entry = cardEntryFromScryfall(JSON.parse(answer.body) as ScryfallCard, 0);
      delete entry.fetchedAt;
      fromLookup[key] = entry;
    }
    expect(Object.keys(seed).length).toBeGreaterThan(1500);
    expect(fromLookup).toStrictEqual(seed);
  });

  it('holds no joined mana cost', () => {
    const joined = Object.entries(cardCacheSeed()).filter(([, e]) =>
      (e as { mana_cost: string }).mana_cost.includes(' // '),
    );
    expect(joined.map(([key]) => key)).toEqual([]);
  });
});
