import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import {
  aggregateBuiltClaims,
  computeBuyOwnSplit,
  getBuiltDecks,
  setBuiltDecks,
  toggleBuiltDeck,
} from '../../data/builtDecks';
import type { DeckFull, DeckListGroup } from '../../data/types';

const STORAGE_KEY = 'grimoire-built-decks';

function makeDeck(over: Partial<DeckFull>): DeckFull {
  return {
    idx: 1,
    slug: 'alpha',
    deckName: 'Alpha',
    commander: 'Alpha Commander',
    commanderMv: '—',
    type: 'Commander · Theme',
    colors: '🔴',
    bracket: 'IV',
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
    health: { score: 70, grade: 'B' },
    assessment: null,
    composition: { totalCards: 100, lands: 36, avgCmc: 2.8 },
    sim: null,
    rawDecklist: [],
    physicalDecklist: [],
    synergies: [],
    gameChangers: 0,
    tokens: [],
    ...over,
  };
}

function group(name: string, names: string[], type = 'Creature'): DeckListGroup {
  return {
    name,
    cards: names.map((n) => ({ n, mv: '—', type, price: '—', gc: false })),
  };
}

interface PlannedQty { quantity: number; tag?: string }
function planned(...entries: Array<[string, number, string?]>): Map<string, PlannedQty> {
  const m = new Map<string, PlannedQty>();
  entries.forEach(([n, q, t]) => m.set(n, { quantity: q, tag: t }));
  return m;
}

describe('localStorage helpers', () => {
  beforeEach(() => localStorage.removeItem(STORAGE_KEY));
  afterEach(() => localStorage.removeItem(STORAGE_KEY));

  it('round-trips a Set through localStorage', () => {
    setBuiltDecks(new Set(['alpha', 'beta']));
    const back = getBuiltDecks();
    expect([...back].sort()).toEqual(['alpha', 'beta']);
  });

  it('returns an empty Set when storage is empty or malformed', () => {
    expect(getBuiltDecks().size).toBe(0);
    localStorage.setItem(STORAGE_KEY, 'not-json');
    expect(getBuiltDecks().size).toBe(0);
    localStorage.setItem(STORAGE_KEY, '{"not":"array"}');
    expect(getBuiltDecks().size).toBe(0);
  });

  it('toggles ids in/out and persists', () => {
    toggleBuiltDeck('alpha');
    expect([...getBuiltDecks()]).toEqual(['alpha']);
    toggleBuiltDeck('beta');
    expect([...getBuiltDecks()].sort()).toEqual(['alpha', 'beta']);
    toggleBuiltDeck('alpha');
    expect([...getBuiltDecks()]).toEqual(['beta']);
  });
});

describe('aggregateBuiltClaims', () => {
  const ALPHA = makeDeck({
    slug: 'alpha',
    deckName: 'Alpha',
    commander: 'Alpha Commander',
    list: [
      group('Commander', ['Alpha Commander']),
      group('Ramp', ['Sol Ring', 'Forest']),
    ],
  });
  const BETA = makeDeck({
    idx: 2,
    slug: 'beta',
    deckName: 'Beta',
    commander: 'Beta Commander',
    list: [
      group('Commander', ['Beta Commander']),
      group('Ramp', ['Sol Ring', 'Island']),
    ],
  });
  const GAMMA = makeDeck({
    idx: 3,
    slug: 'gamma',
    deckName: 'Gamma',
    commander: 'Gamma Commander',
    partner: 'Gamma Partner',
    list: [
      group('Commander', ['Gamma Commander']),
      group('Ramp', ['Sol Ring']),
    ],
  });

  it('counts each built deck once per unique card name', () => {
    const claims = aggregateBuiltClaims(new Set(['alpha', 'beta']), [ALPHA, BETA, GAMMA]);
    expect(claims.get('Sol Ring')).toBe(2);
    expect(claims.get('Alpha Commander')).toBe(1);
    expect(claims.get('Beta Commander')).toBe(1);
  });

  it('excludes basic lands', () => {
    const claims = aggregateBuiltClaims(new Set(['alpha', 'beta']), [ALPHA, BETA]);
    expect(claims.has('Forest')).toBe(false);
    expect(claims.has('Island')).toBe(false);
  });

  it('includes commander and partner', () => {
    const claims = aggregateBuiltClaims(new Set(['gamma']), [ALPHA, BETA, GAMMA]);
    expect(claims.get('Gamma Commander')).toBe(1);
    expect(claims.get('Gamma Partner')).toBe(1);
  });

  it('returns an empty map when no decks are built', () => {
    expect(aggregateBuiltClaims(new Set(), [ALPHA, BETA]).size).toBe(0);
  });

  it('ignores slugs not in the deck list', () => {
    const claims = aggregateBuiltClaims(new Set(['ghost']), [ALPHA, BETA]);
    expect(claims.size).toBe(0);
  });

  it('skips the plural "Commanders" group for partner decks (DEC-211)', () => {
    // normalize.ts emits group name `'Commanders'` when partner is set; the
    // commander + partner are added explicitly, so the group must be skipped
    // to avoid double-counting.
    const PARTNERS = makeDeck({
      slug: 'partners',
      deckName: 'Partner Deck',
      commander: 'Leonardo, the Balance',
      partner: 'Donatello, the Brains',
      list: [
        group('Commanders', ['Leonardo, the Balance', 'Donatello, the Brains']),
        group('Ramp', ['Sol Ring']),
      ],
    });
    const claims = aggregateBuiltClaims(new Set(['partners']), [PARTNERS]);
    // Set-based, so even without the fix it'd be 1; assert presence.
    expect(claims.get('Leonardo, the Balance')).toBe(1);
    expect(claims.get('Donatello, the Brains')).toBe(1);
  });

  it('keys DFC entries by front face so the owned map reconciles (DEC-178)', () => {
    const DFC = makeDeck({
      slug: 'dfc',
      deckName: 'DFC Deck',
      commander: 'DFC Commander',
      list: [
        group('Commander', ['DFC Commander']),
        group('Threats', ['Sephiroth, Fabled SOLDIER // Final Heaven']),
      ],
    });
    const claims = aggregateBuiltClaims(new Set(['dfc']), [DFC]);
    expect(claims.get('Sephiroth, Fabled SOLDIER')).toBe(1);
    expect(claims.has('Sephiroth, Fabled SOLDIER // Final Heaven')).toBe(false);
  });
});

describe('computeBuyOwnSplit', () => {
  it('returns no buy / no own when nothing is planned', () => {
    const split = computeBuyOwnSplit(planned(), new Map(), new Map());
    expect(split.buy).toEqual([]);
    expect(split.own).toEqual([]);
  });

  it('routes a planned card to buy when nothing is owned', () => {
    const split = computeBuyOwnSplit(planned(['Sol Ring', 1]), new Map(), new Map());
    expect(split.buy).toHaveLength(1);
    expect(split.buy[0]).toMatchObject({ name: 'Sol Ring', qty: 1, reservedBy: 0 });
    expect(split.own).toHaveLength(0);
  });

  it('routes the card to own when the owner has a copy', () => {
    const split = computeBuyOwnSplit(
      planned(['Sol Ring', 1]),
      new Map([['Sol Ring', 1]]),
      new Map(),
    );
    expect(split.buy).toHaveLength(0);
    expect(split.own[0]).toMatchObject({ name: 'Sol Ring', qty: 1, reservedBy: 0 });
  });

  it('reserves owned copies for built decks before computing buy', () => {
    // 3 built decks claim Sol Ring; owner has 3 copies; 1 selected planned deck needs 1.
    // available = max(0, 3-3) = 0 -> need = max(0, 1-0) = 1 to buy.
    const split = computeBuyOwnSplit(
      planned(['Sol Ring', 1]),
      new Map([['Sol Ring', 3]]),
      new Map([['Sol Ring', 3]]),
    );
    expect(split.buy[0]).toMatchObject({ name: 'Sol Ring', qty: 1, reservedBy: 3 });
    expect(split.own).toHaveLength(0);
  });

  it('lets surplus owned copies satisfy the planned deck', () => {
    // 3 built decks claim Sol Ring; owner has 5 copies; 1 selected planned deck needs 1.
    // available = max(0, 5-3) = 2 -> need = max(0, 1-2) = 0.
    const split = computeBuyOwnSplit(
      planned(['Sol Ring', 1]),
      new Map([['Sol Ring', 5]]),
      new Map([['Sol Ring', 3]]),
    );
    expect(split.buy).toHaveLength(0);
    expect(split.own[0]).toMatchObject({ name: 'Sol Ring', qty: 1, reservedBy: 3 });
  });

  it('partial-claim case: owned exceeds planned but built decks reduce headroom', () => {
    // owner has 2; 1 built deck claims; planned wants 2.
    // available = max(0, 2-1) = 1 -> need = max(0, 2-1) = 1 to buy; own = min(2, 1) = 1.
    const split = computeBuyOwnSplit(
      planned(['Sol Ring', 2]),
      new Map([['Sol Ring', 2]]),
      new Map([['Sol Ring', 1]]),
    );
    expect(split.buy[0]).toMatchObject({ name: 'Sol Ring', qty: 1, reservedBy: 1 });
    expect(split.own[0]).toMatchObject({ name: 'Sol Ring', qty: 1, reservedBy: 1 });
  });

  it('reservedBy stays 0 when the owner has no copies (nothing to reserve)', () => {
    const split = computeBuyOwnSplit(
      planned(['Sol Ring', 1]),
      new Map(),
      new Map([['Sol Ring', 3]]),
    );
    expect(split.buy[0]).toMatchObject({ name: 'Sol Ring', qty: 1, reservedBy: 0 });
  });

  it('preserves the planned info on each row', () => {
    const split = computeBuyOwnSplit(planned(['Sol Ring', 1, 'rocks']), new Map(), new Map());
    expect(split.buy[0].info).toMatchObject({ quantity: 1, tag: 'rocks' });
  });
});
