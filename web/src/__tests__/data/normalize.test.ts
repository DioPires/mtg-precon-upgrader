import { describe, expect, it } from 'vitest';
import { buildDeckStubs, colorsToGlyphs, normalizeDeck, splitTitle, toRoman } from '../../data/normalize';
import type { RawDeckBundle } from '../../data/types';

function makeBundle(over: Partial<RawDeckBundle> = {}): RawDeckBundle {
  return {
    id: 'titan-convergence',
    index: {
      id: 'titan-convergence',
      name: 'Titan Convergence',
      commander: 'Zhulodok, Void Gorger',
      colors: ['C'],
      theme: 'Eldrazi Cascade',
      bracket: '4',
      lastUpdatedSet: 'Tarkir: Dragonstorm',
    },
    deck: {
      id: 'titan-convergence',
      type: 'commander',
      name: 'Titan Convergence',
      commander: 'Zhulodok, Void Gorger',
      bracket: '4',
      gameChangers: 3,
      lastUpdatedSet: 'Tarkir: Dragonstorm',
      sources: [
        { type: 'edhrec', name: 'EDHREC' },
        { type: 'ai-inferred', name: 'Claude analysis' },
      ],
      guideContent: { strategyOverview: 'Cascade. Win. Repeat.' },
      categories: [
        { name: 'Game Changers', isHighlighted: true, cards: ['Mana Vault', 'Ancient Tomb'] },
        { name: 'Eldrazi Titans', cards: ['Ulamog, the Ceaseless Hunger'] },
        { name: 'Empty', cards: [] },
      ],
      decklist: [
        { name: 'Sol Ring', type: 'Artifact', primary_role: 'ramp' },
        { name: 'Ancient Tomb', type: 'Land', primary_role: 'land' },
        { name: 'Mana Vault', type: 'Artifact', primary_role: 'ramp' },
        { name: 'Ulamog, the Ceaseless Hunger', type: 'Creature', primary_role: 'wincon' },
      ],
      highlights: [
        { name: 'Mana Vault', isGameChanger: true, price: '$80', reason: 'Premium ramp' },
        { name: 'Ancient Tomb', isGameChanger: true, price: '$120' },
      ],
      synergies: [
        {
          title: 'Cascade Stacking',
          description: 'Echoes amps cascades.',
          cards: ['Echoes of Eternity', 'Maelstrom Wanderer'],
          sources: [{ type: 'commanderspellbook', name: 'Combo' }],
        },
      ],
      winConditions: [
        {
          title: 'Infinite Mana into Eldrazi Army',
          description: 'Basalt + Forsaken loop into Eye of Ugin tutors.',
          cards: ['Basalt Monolith', 'Forsaken Monument', 'Eye of Ugin', 'Should Not Appear'],
        },
      ],
    },
    sim: {
      deckHealthScore: { score: 63.5, grade: 'C' },
      deckComposition: { totalCards: 99, lands: 35, avgCmc: 5.5 },
      assessment: { manaAdequacy: 'light', mulliganVerdict: 'excellent', commanderTiming: 'on curve' },
    },
    metrics: {
      deck_id: 'titan-convergence',
      commander: 'Zhulodok, Void Gorger',
      bracket: '4',
      global_health: 72,
      confidence_margin: 7,
      metrics: { manabase_health: { score: 80 }, role_coverage_health: { score: 60 } },
      gaps: [{ role: 'card-draw', actual: 4, target: 10, score: 40 }],
      methodology: 'deck-metrics-v1',
    },
    candidates: {
      deck_id: 'titan-convergence',
      candidates: [
        {
          name: 'Dreamstone Hedron',
          cmc: 6,
          mana_cost: '{6}',
          type_line: 'Artifact',
          score: 49.9,
          deck_role: 'ramp',
        },
      ],
    },
    ...over,
  };
}

describe('splitTitle', () => {
  it('returns ["", ""] for empty input', () => {
    expect(splitTitle(undefined)).toEqual(['', '']);
    expect(splitTitle('')).toEqual(['', '']);
  });
  it('returns single-word input as head only', () => {
    expect(splitTitle('Inevitability')).toEqual(['Inevitability', '']);
  });
  it('splits multi-word at midpoint and adds trailing space to head', () => {
    const [head, tail] = splitTitle('Infinite Mana into Eldrazi Army');
    expect(head).toBe('Infinite Mana into ');
    expect(tail).toBe('Eldrazi Army');
  });
});

describe('toRoman', () => {
  it('maps 1-5 to roman', () => {
    expect(toRoman('1')).toBe('I');
    expect(toRoman(4)).toBe('IV');
    expect(toRoman('5')).toBe('V');
  });
  it('echoes unknown values', () => {
    expect(toRoman('99')).toBe('99');
    expect(toRoman(undefined)).toBe('');
  });
});

describe('colorsToGlyphs', () => {
  it('maps mtg colors to glyph chars', () => {
    expect(colorsToGlyphs(['B', 'R'])).toBe('⚫🔴');
    expect(colorsToGlyphs(['C'])).toBe('◇');
    expect(colorsToGlyphs(undefined)).toBe('');
  });
  it('falls back to colorless glyph for unknown letters', () => {
    expect(colorsToGlyphs(['X'])).toBe('◇');
  });
});

describe('normalizeDeck', () => {
  it('produces the expected DeckFull shape with correct top-level fields', () => {
    const out = normalizeDeck(makeBundle(), 1);
    expect(out.idx).toBe(1);
    expect(out.slug).toBe('titan-convergence');
    expect(out.deckName).toBe('Titan Convergence');
    expect(out.commander).toBe('Zhulodok, Void Gorger');
    expect(out.bracket).toBe('IV');
    expect(out.colors).toBe('◇');
    expect(out.winRate).toBe(64);
    expect(out.flavor).toBe('Cascade.');
  });

  it('defaults status to "physical" and respects "brewing" override (DEC-297)', () => {
    expect(normalizeDeck(makeBundle(), 1).status).toBe('physical');

    const brewing = makeBundle();
    brewing.deck.status = 'brewing';
    expect(normalizeDeck(brewing, 1).status).toBe('brewing');
  });

  it('propagates status onto DeckStub entries (DEC-297)', () => {
    const phys = normalizeDeck(makeBundle(), 1);
    const brewBundle = makeBundle();
    brewBundle.deck.status = 'brewing';
    brewBundle.id = 'brew';
    brewBundle.deck.id = 'brew';
    brewBundle.index.id = 'brew';
    const brew = normalizeDeck(brewBundle, 2);
    const stubs = buildDeckStubs([phys, brew]);
    expect(stubs.map((s) => s.status)).toEqual(['physical', 'brewing']);
  });

  it('builds engine sections from non-empty categories only', () => {
    const out = normalizeDeck(makeBundle(), 1);
    expect(out.engine.map((e) => e.title)).toEqual(['Game Changers', 'Eldrazi Titans']);
    expect(out.engine[0].isGameChangers).toBe(true);
    expect(out.engine[1].isGameChangers).toBe(false);
  });

  it('falls back to guideContent.deckCategories when top-level categories is absent (DEC-351)', () => {
    const bundle = makeBundle();
    delete bundle.deck.categories;
    bundle.deck.guideContent = {
      strategyOverview: 'Counters.',
      deckCategories: [
        { name: 'Counter Doublers', cards: ['Mana Vault'] },
        { name: 'Empty', cards: [] },
      ],
    };
    const out = normalizeDeck(bundle, 1);
    expect(out.engine.map((e) => e.title)).toEqual(['Counter Doublers']);
  });

  it('truncates wincon card lists to 3', () => {
    const out = normalizeDeck(makeBundle(), 1);
    expect(out.wincons).toHaveLength(1);
    expect(out.wincons[0].cards).toHaveLength(3);
    expect(out.wincons[0].cards.map((c) => c.n)).toEqual([
      'Basalt Monolith',
      'Forsaken Monument',
      'Eye of Ugin',
    ]);
  });

  it('marks a card as gc=true when in highlights', () => {
    const out = normalizeDeck(makeBundle(), 1);
    const tile = out.engine[0].cards.find((c) => c.n === 'Mana Vault');
    expect(tile?.gc).toBe(true);
    expect(tile?.price).toBe('$80');
  });

  it('renders combos with a Spellbook source label preferred', () => {
    const out = normalizeDeck(makeBundle(), 1);
    expect(out.combos).toHaveLength(1);
    expect(out.combos[0].src).toBe('Spellbook · Combo');
    expect(out.combos[0].tag).toBe('2-CARD');
  });

  it('builds an apothecary block when metrics + candidates are present', () => {
    const out = normalizeDeck(makeBundle(), 1);
    expect(out.apothecary).not.toBeNull();
    expect(out.apothecary?.diagnosis.score).toBe(72);
    expect(out.apothecary?.diagnosis.confidenceMargin).toBe(7);
    expect(out.apothecary?.maladies).toHaveLength(1);
    expect(out.apothecary?.remedies[0].name).toBe('Dreamstone Hedron');
  });

  it('returns apothecary=null when metrics or candidates missing', () => {
    const noMetrics = normalizeDeck(makeBundle({ metrics: null }), 1);
    expect(noMetrics.apothecary).toBeNull();
    const noCandidates = normalizeDeck(makeBundle({ candidates: null }), 1);
    expect(noCandidates.apothecary).toBeNull();
  });

  it('builds a curve from primary_role distribution with peak flagged', () => {
    const out = normalizeDeck(makeBundle(), 1);
    const peak = out.curve.find((c) => c.peak);
    expect(peak).toBeDefined();
    expect(peak?.cmc).toBe('Ramp');
    expect(peak?.n).toBe(2);
  });

  it('groups decklist by role with Commander first and Lands last', () => {
    const out = normalizeDeck(makeBundle(), 1);
    expect(out.list[0].name).toBe('Commander');
    expect(out.list[out.list.length - 1].name.startsWith('Lands')).toBe(true);
  });

  it('marks land tiles with mv "LAND"', () => {
    const out = normalizeDeck(makeBundle(), 1);
    const lands = out.list.find((g) => g.name.startsWith('Lands'));
    expect(lands?.cards[0].mv).toBe('LAND');
  });

  it('hydrates mana costs and cmc from generated card metadata before live Scryfall loads', () => {
    const out = normalizeDeck(makeBundle({
      cardMetadata: {
        'Sol Ring': { mana_cost: '{1}', cmc: 1, type_line: 'Artifact' },
        'Mana Vault': { mana_cost: '{1}', cmc: 1, type_line: 'Artifact' },
        'Zhulodok, Void Gorger': { mana_cost: '{5}{C}', cmc: 6, type_line: 'Legendary Creature — Eldrazi' },
      },
    }), 1);

    const ramp = out.list.find((g) => g.name.startsWith('Ramp'));
    const solRing = ramp?.cards.find((c) => c.n === 'Sol Ring');
    expect(solRing?.mv).toBe('{1}');
    expect(solRing?.cmc).toBe(1);
    expect(out.list[0].cards[0].mv).toBe('{5}{C}');
  });

  it('flattens rawDecklist into physicalDecklist by quantity (DEC-176)', () => {
    const bundle = makeBundle();
    bundle.deck.decklist = [
      { name: 'Sol Ring', type: 'Artifact', primary_role: 'ramp' },
      { name: 'Plains', type: 'Land', primary_role: 'land', quantity: 7 },
      { name: 'Island', type: 'Land', primary_role: 'land', quantity: 6 },
      { name: 'Forest', type: 'Land', primary_role: 'land' },
    ];
    const out = normalizeDeck(bundle, 1);

    // rawDecklist preserves authoring shape (one entry per unique card).
    expect(out.rawDecklist).toHaveLength(4);

    // physicalDecklist expands to one entry per copy: 1 + 7 + 6 + 1 = 15.
    expect(out.physicalDecklist).toHaveLength(15);
    const plainsCount = out.physicalDecklist.filter((c) => c.name === 'Plains').length;
    expect(plainsCount).toBe(7);
    const islandCount = out.physicalDecklist.filter((c) => c.name === 'Island').length;
    expect(islandCount).toBe(6);

    // quantity is stripped from emitted physical entries — each entry is one copy.
    expect(out.physicalDecklist.every((c) => c.quantity === undefined)).toBe(true);
  });

  it('expands quantity into list group counts and curve roleCounts (DEC-174)', () => {
    const bundle = makeBundle();
    bundle.deck.decklist = [
      { name: 'Sol Ring', type: 'Artifact', primary_role: 'ramp' },
      { name: 'Plains', type: 'Land', primary_role: 'land', quantity: 7 },
      { name: 'Island', type: 'Land', primary_role: 'land', quantity: 6 },
      { name: 'Forest', type: 'Land', primary_role: 'land' },
    ];
    const out = normalizeDeck(bundle, 1);

    const lands = out.list.find((g) => g.name.startsWith('Lands'));
    expect(lands).toBeDefined();
    // 7 Plains + 6 Islands + 1 Forest = 14 lands
    expect(lands!.name).toBe('Lands (14)');

    const plainsTile = lands!.cards.find((c) => c.n === 'Plains');
    expect(plainsTile?.qty).toBe(7);
    const forestTile = lands!.cards.find((c) => c.n === 'Forest');
    // qty omitted when 1
    expect(forestTile?.qty).toBeUndefined();

    // Curve role distribution counts physical copies, not entries.
    const landCurve = out.curve.find((c) => c.cmc === 'Lands');
    expect(landCurve?.n).toBe(14);
  });
});

describe('Decklist count helper', () => {
  it('cardCount sums qty (defaulting missing to 1) — DEC-174', async () => {
    const { cardCount } = await import('../../components/organisms/Decklist');
    expect(
      cardCount([
        { n: 'Plains', mv: 'LAND', type: 'Land', price: '—', gc: false, qty: 7 },
        { n: 'Sol Ring', mv: '{1}', type: 'Artifact', price: '$2', gc: false },
      ]),
    ).toBe(8);
    expect(cardCount([])).toBe(0);
  });

  it('keeps health/composition/assessment from sim', () => {
    const out = normalizeDeck(makeBundle(), 1);
    expect(out.health?.grade).toBe('C');
    expect(out.composition?.lands).toBe(35);
    expect(out.assessment?.mulliganVerdict).toBe('excellent');
  });

  it('handles missing sim/metrics/candidates without throwing', () => {
    const out = normalizeDeck(makeBundle({ sim: null, metrics: null, candidates: null }), 1);
    expect(out.health).toBeNull();
    expect(out.winRate).toBeNull();
    expect(out.apothecary).toBeNull();
  });

  it('surfaces partner commander on DeckFull and pins both in the Commanders list group (DEC-190)', () => {
    const bundle = makeBundle();
    bundle.deck.commander = 'Leonardo, the Balance';
    bundle.deck.partner = 'Donatello, the Brains';
    const out = normalizeDeck(bundle, 1);
    expect(out.commander).toBe('Leonardo, the Balance');
    expect(out.partner).toBe('Donatello, the Brains');
    const cmdGroup = out.list[0];
    expect(cmdGroup.name).toBe('Commanders');
    expect(cmdGroup.cards.map((c) => c.n)).toEqual([
      'Leonardo, the Balance',
      'Donatello, the Brains',
    ]);
  });

  it('keeps singular Commander group when partner missing', () => {
    const out = normalizeDeck(makeBundle(), 1);
    expect(out.partner).toBeUndefined();
    expect(out.list[0].name).toBe('Commander');
    expect(out.list[0].cards).toHaveLength(1);
  });

  it('passes deck.tokens through and skips entries missing a name (DEC-199)', () => {
    const bundle = makeBundle();
    bundle.deck.tokens = [
      {
        name: 'Eldrazi Scion',
        type_line: 'Token Creature — Eldrazi Scion',
        power: '1',
        toughness: '1',
        produced_by: ['Warping Wail'],
      },
      // malformed entries: missing/blank name → dropped
      { name: '', produced_by: [] } as never,
      { produced_by: ['X'] } as never,
    ];
    const out = normalizeDeck(bundle, 1);
    expect(out.tokens).toHaveLength(1);
    expect(out.tokens[0].name).toBe('Eldrazi Scion');
    expect(out.tokens[0].produced_by).toEqual(['Warping Wail']);
  });

  it('defaults tokens to [] when deck.tokens is missing or invalid', () => {
    const bundle = makeBundle();
    delete bundle.deck.tokens;
    expect(normalizeDeck(bundle, 1).tokens).toEqual([]);
    bundle.deck.tokens = 'nope' as never;
    expect(normalizeDeck(bundle, 1).tokens).toEqual([]);
  });
});

describe('buildDeckStubs', () => {
  it('emits selector entries with hasDetail=true', () => {
    const decks = [normalizeDeck(makeBundle(), 1)];
    const stubs = buildDeckStubs(decks);
    expect(stubs).toHaveLength(1);
    expect(stubs[0]).toMatchObject({
      idx: 1,
      slug: 'titan-convergence',
      name: 'Titan Convergence',
      cmd: 'Zhulodok, Void Gorger',
      bracket: 'IV',
      hasDetail: true,
    });
  });
});
