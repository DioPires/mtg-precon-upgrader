import { describe, expect, it } from 'vitest';
import { bracketBase, bracketOrder, buildDeckStubs, colorsToGlyphs, normalizeBracket, normalizeDeck, splitTitle } from '../../data/normalize';
import type { RawCandidate, RawDeckBundle } from '../../data/types';

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

describe('normalizeBracket', () => {
  it('passes canonical numeric forms through', () => {
    expect(normalizeBracket('3')).toBe('3');
    expect(normalizeBracket('3+')).toBe('3+');
    expect(normalizeBracket('4-')).toBe('4-');
    expect(normalizeBracket(4)).toBe('4');
  });
  it('converts legacy Roman input, with or without modifier', () => {
    expect(normalizeBracket('IV')).toBe('4');
    expect(normalizeBracket('III')).toBe('3');
    expect(normalizeBracket('IV+')).toBe('4+');
    expect(normalizeBracket('V')).toBe('5');
  });
  it('echoes unknown values', () => {
    expect(normalizeBracket('99')).toBe('99');
    expect(normalizeBracket(undefined)).toBe('');
  });
});

describe('bracketBase / bracketOrder', () => {
  it('extracts numeric base regardless of modifier', () => {
    expect(bracketBase('4-')).toBe(4);
    expect(bracketBase('4+')).toBe(4);
    expect(bracketBase('3+')).toBe(3);
    expect(bracketBase('IV')).toBe(4);
    expect(bracketBase(undefined)).toBeNaN();
  });
  it('orders brackets by power: 3 < 3+ < 4- < 4 < 4+', () => {
    const sorted = ['4+', '3', '4-', '3+', '4'].sort((a, b) => bracketOrder(a) - bracketOrder(b));
    expect(sorted).toEqual(['3', '3+', '4-', '4', '4+']);
  });
  it('sorts unknown values last', () => {
    expect(bracketOrder('?')).toBe(Number.POSITIVE_INFINITY);
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
    expect(out.bracket).toBe('4');
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

  it('maps global_health_normalized to scoreNormalized, null when absent (DEC-389/390)', () => {
    const absent = normalizeDeck(makeBundle(), 1);
    expect(absent.apothecary?.diagnosis.scoreNormalized).toBeNull();

    const bundle = makeBundle();
    bundle.metrics = { ...bundle.metrics!, global_health_normalized: 64 };
    const present = normalizeDeck(bundle, 1);
    expect(present.apothecary?.diagnosis.scoreNormalized).toBe(64);
  });

  describe('apothecary pins (DEC-1000)', () => {
    const artifact = (name: string, score: number, pinned?: boolean): RawCandidate => ({
      name,
      cmc: 2,
      mana_cost: '{2}',
      type_line: 'Artifact',
      score,
      ...(pinned ? { pinned } : {}),
    });

    function withPins(pool: RawCandidate[], pins: unknown): RawDeckBundle {
      const bundle = makeBundle();
      bundle.candidates = { deck_id: bundle.id, candidates: pool };
      bundle.deck = { ...bundle.deck, candidate_pins: pins as RawDeckBundle['deck']['candidate_pins'] };
      return bundle;
    }

    it('joins candidate_pins to their pinned pool entries with rank and poolSize', () => {
      const pool = [
        artifact('Dreamstone Hedron', 49.9),
        artifact('Hedron Archive', 41.2, true),
        artifact('Mind Stone', 30),
        artifact('Thought Vessel', 12.5, true),
      ];
      const before = structuredClone(pool);
      const out = normalizeDeck(
        withPins(pool, [
          { name: 'Thought Vessel', reason: 'First in the file, last in the pool.' },
          { name: 'Hedron Archive', reason: 'Second in the file.' },
        ]),
        1,
      );

      expect(out.apothecary?.pins).toEqual([
        { name: 'Thought Vessel', reason: 'First in the file, last in the pool.', card: pool[3], rank: 4, poolSize: 4 },
        { name: 'Hedron Archive', reason: 'Second in the file.', card: pool[1], rank: 2, poolSize: 4 },
      ]);
      expect(out.apothecary?.remedies).toEqual(before);
    });

    it('drops a pin the generator did not seat', () => {
      const pool = [artifact('Dreamstone Hedron', 49.9), artifact('Mind Stone', 30)];
      const out = normalizeDeck(
        withPins(pool, [
          { name: 'Sol Ring', reason: 'Already in the decklist: no pool entry.' },
          { name: 'Mind Stone', reason: 'In the pool on merit, never flagged pinned.' },
        ]),
        1,
      );
      expect(out.apothecary?.pins).toEqual([]);
      expect(out.apothecary?.remedies).toHaveLength(2);
    });

    it('joins a front-face pin name to its Front // Back pool entry', () => {
      const dfc: RawCandidate = {
        name: 'Wedding Announcement // Wedding Festivity',
        cmc: 3,
        mana_cost: '',
        type_line: 'Enchantment // Enchantment',
        score: 56.1,
        pinned: true,
      };
      const out = normalizeDeck(
        withPins([artifact('Dreamstone Hedron', 60), dfc], [{ name: 'Wedding Announcement', reason: 'Pinned by front face.' }]),
        1,
      );
      expect(out.apothecary?.pins).toEqual([
        { name: 'Wedding Announcement', reason: 'Pinned by front face.', card: dfc, rank: 2, poolSize: 2 },
      ]);
    });

    it('returns no pins when the deck has no candidate_pins', () => {
      expect(normalizeDeck(makeBundle(), 1).apothecary?.pins).toEqual([]);
    });

    it('tolerates malformed candidate_pins: nameless, duplicate, reasonless, non-array', () => {
      const pool = [artifact('Hedron Archive', 41.2, true)];
      const out = normalizeDeck(
        withPins(pool, [null, { reason: 'no name' }, { name: ' Hedron Archive ' }, { name: 'Hedron Archive', reason: 'dup' }]),
        1,
      );
      expect(out.apothecary?.pins).toEqual([
        { name: 'Hedron Archive', reason: '', card: pool[0], rank: 1, poolSize: 1 },
      ]);
      expect(normalizeDeck(withPins(pool, 'Hedron Archive'), 1).apothecary?.pins).toEqual([]);
    });
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

  it('names the mana-fixing role "Fixing" in the chart, Function mix and the decklist (DEC-1074)', () => {
    const { deck } = makeBundle();
    const decklist = [...(deck.decklist ?? []), { name: 'Bloom Tender', type: 'Creature', primary_role: 'mana-fixing' }];
    const out = normalizeDeck(makeBundle({ deck: { ...deck, decklist } }), 1);
    expect(out.curve.map((c) => c.cmc)).toContain('Fixing');
    expect(out.func.map((f) => f.l)).toContain('Fixing');
    expect(out.list.map((g) => g.name)).toContain('Fixing (1)');
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
      bracket: '4',
      hasDetail: true,
    });
  });
});
