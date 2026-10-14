// DEC-1073 — the e2e stub's card cache seed against the app's own mapping.
//
// A spec with `test.use({ cards: 'seeded' })` starts with cardCacheSeed() in
// localStorage (tests/support/test.ts), so the app never maps those cards itself.
// cardCacheSeed() repeats the mapping of fetchOne() by hand. This case runs the
// app's fetchOne() on the stub's answer for every key and compares the two, so a
// change to either side that the other does not follow fails here.

import { describe, it, expect } from 'vitest';
import { createCardCache } from '../../data/cardCache';
import { answerFor, cardCacheSeed } from '../../../tests/support/scryfall';

describe('e2e stub: cardCacheSeed()', () => {
  it("holds, for every key, the entry that the app's fetchOne makes from the stub's answer", async () => {
    const stubFetch = async (input: RequestInfo | URL) => {
      const answer = answerFor(new URL(String(input)));
      if (!answer) throw new Error(`the stub has no answer for ${String(input)}`);
      return new Response(answer.body, { status: answer.status });
    };
    const cache = createCardCache({ storage: null, fetchImpl: stubFetch as typeof fetch });

    const seed = cardCacheSeed();
    const fromApp: Record<string, object> = {};
    for (const key of Object.keys(seed)) {
      const entry = await cache.fetch(key);
      delete entry.fetchedAt;
      fromApp[key] = entry;
    }

    expect(Object.keys(seed).length).toBeGreaterThan(1500);
    expect(fromApp).toStrictEqual(seed);
  });

  it('holds no joined mana cost: the stub sends card_faces for every // card', () => {
    const joined = Object.entries(cardCacheSeed()).filter(([, e]) =>
      (e as { mana_cost: string }).mana_cost.includes(' // '),
    );
    expect(joined.map(([key]) => key)).toEqual([]);
  });
});
