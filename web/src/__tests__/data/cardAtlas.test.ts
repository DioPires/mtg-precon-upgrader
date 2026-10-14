import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  buildCardAtlasIndex,
  loadOwnedMap,
  localSuggest,
  scryfallSuggest,
} from '../../data/cardAtlas';
import type { DeckFull } from '../../data/types';
import { createScryfallLimiter } from '../../data/scryfallLimiter';

const OWNED_KEY = 'grimoire-owned-cards';

function makeDeck(over: Partial<DeckFull>): DeckFull {
  return {
    idx: 1,
    slug: 'alpha',
    deckName: 'Alpha',
    commander: 'Alpha Commander',
    commanderMv: '—',
    type: 'Commander · Theme',
    colors: '🔴',
    bracket: '4',
    status: 'physical',
    pt: '—',
    winTurn: '—',
    winRate: null,
    flavor: '',
    oracle: [],
    strategy: '',
    wincons: [],
    engine: [],
    combos: [],
    apothecary: null,
    curve: [],
    func: [],
    sources: [],
    list: [],
    health: null,
    assessment: null,
    composition: null,
    sim: null,
    rawDecklist: [],
    physicalDecklist: [],
    synergies: [],
    gameChangers: 0,
    tokens: [],
    ...over,
  };
}

/** One physical + one brewing deck sharing Sol Ring (DEC-568 split fixture). */
function mixedDecks(): DeckFull[] {
  return [
    makeDeck({
      slug: 'physical-deck',
      deckName: 'Physical',
      commander: 'Atraxa, Praetors\' Voice',
      status: 'physical',
      rawDecklist: [{ name: 'Sol Ring', type: 'Artifact', primary_role: 'ramp' }],
    }),
    makeDeck({
      slug: 'brewing-deck',
      deckName: 'Brewing',
      commander: 'Esika, God of the Tree',
      status: 'brewing',
      rawDecklist: [
        { name: 'Sol Ring', type: 'Artifact', primary_role: 'ramp' },
        { name: 'Teferi, Hero of Dominaria', type: 'Planeswalker', primary_role: 'engine' },
      ],
    }),
  ];
}

describe('buildCardAtlasIndex', () => {
  it('indexes commander, partner, and decklist entries with role labels', () => {
    const decks: DeckFull[] = [
      makeDeck({
        slug: 'alpha',
        deckName: 'Alpha',
        commander: 'Alesha, Who Smiles at Death',
        partner: 'Tymna the Weaver',
        rawDecklist: [
          { name: 'Sol Ring', type: 'Artifact', primary_role: 'ramp' },
          { name: 'Cyclonic Rift', type: 'Instant', primary_role: 'removal-board' },
        ],
      }),
      makeDeck({
        slug: 'beta',
        deckName: 'Beta',
        commander: 'Atraxa, Praetors\' Voice',
        rawDecklist: [
          { name: 'Sol Ring', type: 'Artifact', primary_role: 'ramp' },
        ],
      }),
    ];

    const idx = buildCardAtlasIndex(decks);

    expect(idx.byName.get('sol ring')).toHaveLength(2);
    expect(idx.byName.get('sol ring')?.[0].role).toBe('Ramp');
    expect(idx.byName.get('cyclonic rift')?.[0].role).toBe('Board Wipes');

    const alesha = idx.byName.get('alesha, who smiles at death');
    expect(alesha?.[0].role).toBe('Commander');
    expect(alesha?.[0].partner).toBe('Tymna the Weaver');

    const tymna = idx.byName.get('tymna the weaver');
    expect(tymna?.[0].role).toBe('Partner');

    expect(idx.names).toContain('Sol Ring');
    expect(idx.names).toContain('Tymna the Weaver');
  });

  it('keys DFC cards by their front face for cross-deck reconciliation', () => {
    const decks: DeckFull[] = [
      makeDeck({
        slug: 'alpha',
        rawDecklist: [
          { name: 'Brazen Borrower // Petty Theft', type: 'Creature', primary_role: 'utility' },
        ],
      }),
    ];
    const idx = buildCardAtlasIndex(decks);
    expect(idx.byName.has('brazen borrower')).toBe(true);
    expect(idx.byName.get('brazen borrower')?.[0].displayName).toBe(
      'Brazen Borrower // Petty Theft',
    );
  });

  it('preserves quantity for basics with quantity > 1', () => {
    const decks: DeckFull[] = [
      makeDeck({
        rawDecklist: [
          { name: 'Forest', type: 'Basic Land', primary_role: 'land', quantity: 8 },
        ],
      }),
    ];
    const idx = buildCardAtlasIndex(decks);
    expect(idx.byName.get('forest')?.[0].qty).toBe(8);
  });

  it('keeps brewing usages out of the built-deck map (DEC-297/DEC-568)', () => {
    const idx = buildCardAtlasIndex(mixedDecks());

    // Sol Ring is in both decks — the built map only reports the physical one.
    expect(idx.byName.get('sol ring')).toHaveLength(1);
    expect(idx.byName.get('sol ring')?.[0].deckSlug).toBe('physical-deck');

    // Cards only present in the brewing deck never enter the built map.
    expect(idx.byName.has('teferi, hero of dominaria')).toBe(false);
    expect(idx.byName.has('esika, god of the tree')).toBe(false);
  });

  it('indexes brewing usages separately (DEC-568)', () => {
    const idx = buildCardAtlasIndex(mixedDecks());

    // Card only in a brewing deck: brewing-side hit, built-side miss.
    const teferi = idx.brewingByName.get('teferi, hero of dominaria');
    expect(teferi).toHaveLength(1);
    expect(teferi?.[0].deckSlug).toBe('brewing-deck');
    expect(teferi?.[0].role).toBe('Engine');
    expect(teferi?.[0].deckName).toBe('Brewing');

    // Brewing commanders are indexed too.
    expect(idx.brewingByName.get('esika, god of the tree')?.[0].role).toBe('Commander');

    // Card in both: one usage on each side — the counters the header renders.
    expect(idx.byName.get('sol ring')).toHaveLength(1);
    expect(idx.brewingByName.get('sol ring')).toHaveLength(1);
    expect(idx.brewingByName.get('sol ring')?.[0].deckSlug).toBe('brewing-deck');

    // Card in neither.
    expect(idx.byName.has('black lotus')).toBe(false);
    expect(idx.brewingByName.has('black lotus')).toBe(false);
  });

  it('offers brewing-only card names as local suggestions (DEC-568)', () => {
    const idx = buildCardAtlasIndex(mixedDecks());

    // `names` spans both sides so the autocomplete can badge brewing-only hits
    // instead of dropping through to the Scryfall fallback.
    expect(idx.names).toContain('Teferi, Hero of Dominaria');
    expect(idx.names).toContain('Sol Ring');
    // Deduped across the two decks.
    expect(idx.names.filter((n) => n === 'Sol Ring')).toHaveLength(1);
    expect(localSuggest('teferi', idx.names, 10)).toEqual(['Teferi, Hero of Dominaria']);
  });

  it('preserves brewing quantities and DFC front-face keys (DEC-568)', () => {
    const idx = buildCardAtlasIndex([
      makeDeck({
        slug: 'brewing-deck',
        status: 'brewing',
        rawDecklist: [
          { name: 'Forest', type: 'Basic Land', primary_role: 'land', quantity: 9 },
          { name: 'Brazen Borrower // Petty Theft', type: 'Creature', primary_role: 'utility' },
        ],
      }),
    ]);
    expect(idx.brewingByName.get('forest')?.[0].qty).toBe(9);
    expect(idx.brewingByName.get('brazen borrower')?.[0].displayName).toBe(
      'Brazen Borrower // Petty Theft',
    );
  });
});

describe('localSuggest', () => {
  const names = ['Sol Ring', 'Sol\'kanar the Tainted', 'Solemn Simulacrum', 'Lightning Bolt'];

  it('returns prefix matches before substring matches', () => {
    const out = localSuggest('sol', names, 10);
    expect(out.slice(0, 3)).toEqual(['Sol Ring', "Sol'kanar the Tainted", 'Solemn Simulacrum']);
  });

  it('returns empty for an empty query', () => {
    expect(localSuggest('', names, 10)).toEqual([]);
  });

  it('respects the limit', () => {
    expect(localSuggest('sol', names, 2)).toHaveLength(2);
  });

  it('hoists exact matches to the top', () => {
    const out = localSuggest('sol ring', names, 10);
    expect(out[0]).toBe('Sol Ring');
  });
});

describe('scryfallSuggest', () => {
  const limiterWith = (fetchImpl: typeof fetch) => createScryfallLimiter({ fetchImpl, storage: null, locks: null });

  it('returns the data array on a successful response, from bucket 2 of the limiter', async () => {
    const fakeFetch = vi.fn(async () =>
      new Response(JSON.stringify({ data: ['Counterspell', 'Counterflux'] }), { status: 200 }),
    );
    const out = await scryfallSuggest('count', undefined, limiterWith(fakeFetch as unknown as typeof fetch));
    expect(out).toEqual(['Counterspell', 'Counterflux']);
    expect(fakeFetch).toHaveBeenCalledWith('https://api.scryfall.com/cards/autocomplete?q=count');
  });

  it('returns [] for queries shorter than 2 chars', async () => {
    const fakeFetch = vi.fn() as unknown as typeof fetch;
    expect(await scryfallSuggest('a', undefined, limiterWith(fakeFetch))).toEqual([]);
    expect(fakeFetch).not.toHaveBeenCalled();
  });

  it('returns [] on an error status', async () => {
    const fakeFetch = vi.fn(async () => new Response('{}', { status: 500 })) as unknown as typeof fetch;
    expect(await scryfallSuggest('counter', undefined, limiterWith(fakeFetch))).toEqual([]);
  });

  it('returns [] when the caller aborts', async () => {
    const fakeFetch = vi.fn() as unknown as typeof fetch;
    const ctrl = new AbortController();
    ctrl.abort();
    expect(await scryfallSuggest('counter', ctrl.signal, limiterWith(fakeFetch))).toEqual([]);
    expect(fakeFetch).not.toHaveBeenCalled();
  });
});

describe('loadOwnedMap', () => {
  beforeEach(() => localStorage.removeItem(OWNED_KEY));
  afterEach(() => localStorage.removeItem(OWNED_KEY));

  it('returns empty map when nothing is stored', () => {
    expect(loadOwnedMap().size).toBe(0);
  });

  it('parses stored entries and re-keys to lowercase front-face', () => {
    localStorage.setItem(
      OWNED_KEY,
      JSON.stringify([
        ['Sol Ring', 1],
        ['Brazen Borrower // Petty Theft', 2],
      ]),
    );
    const m = loadOwnedMap();
    expect(m.get('sol ring')).toBe(1);
    expect(m.get('brazen borrower')).toBe(2);
  });

  it('returns empty map when stored value is malformed', () => {
    localStorage.setItem(OWNED_KEY, 'not json');
    expect(loadOwnedMap().size).toBe(0);
  });
});
