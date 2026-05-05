import { describe, expect, it } from 'vitest';
import {
  bottomCountFor,
  colorsFromManaCost,
  computeSwapDelta,
  countLandsInHand,
  deriveType,
  fmtManaCost,
  keptHandSize,
  shuffleArr,
} from '../../lib/scrying';
import type { CardEntry } from '../../data/cardCache';
import type { RawDecklistCard } from '../../data/types';

describe('London mulligan helpers', () => {
  it('bottoms zero on first mulligan (free), N-1 thereafter', () => {
    expect(bottomCountFor(0)).toBe(0);
    expect(bottomCountFor(1)).toBe(0);
    expect(bottomCountFor(2)).toBe(1);
    expect(bottomCountFor(3)).toBe(2);
    expect(bottomCountFor(7)).toBe(6);
    // Negative inputs clamp to zero (defensive).
    expect(bottomCountFor(-1)).toBe(0);
  });

  it('keeps a 7-card hand at 0/1 mulls and shrinks thereafter', () => {
    expect(keptHandSize(0)).toBe(7);
    expect(keptHandSize(1)).toBe(7);
    expect(keptHandSize(2)).toBe(6);
    expect(keptHandSize(3)).toBe(5);
    expect(keptHandSize(7)).toBe(1);
    // London bottoms 7+ — kept size clamps at 0 (no negative hands).
    expect(keptHandSize(8)).toBe(0);
    expect(keptHandSize(20)).toBe(0);
  });
});

describe('shuffleArr', () => {
  it('returns a permutation (same multiset)', () => {
    const input = [1, 2, 3, 4, 5, 6, 7];
    const out = shuffleArr(input);
    expect(out).toHaveLength(7);
    expect(out.slice().sort()).toEqual(input);
  });

  it('does not mutate the input', () => {
    const input = [1, 2, 3];
    const orig = input.slice();
    shuffleArr(input);
    expect(input).toEqual(orig);
  });

  it('is deterministic given a deterministic RNG', () => {
    // Seeded RNG via a closure — same seed sequence gives same output.
    const seedRng = () => {
      let s = 1;
      return () => {
        s = (s * 9301 + 49297) % 233280;
        return s / 233280;
      };
    };
    const a = shuffleArr([1, 2, 3, 4, 5, 6, 7], seedRng());
    const b = shuffleArr([1, 2, 3, 4, 5, 6, 7], seedRng());
    expect(a).toEqual(b);
  });

  it('handles empty + single-element arrays', () => {
    expect(shuffleArr([])).toEqual([]);
    expect(shuffleArr(['only'])).toEqual(['only']);
  });
});

describe('colorsFromManaCost / fmtManaCost', () => {
  it('extracts WUBRG colors from {n}{X} costs', () => {
    expect(colorsFromManaCost('{2}{U}{B}').sort()).toEqual(['B', 'U']);
    expect(colorsFromManaCost('{X}{R}{R}')).toEqual(['R']);
    expect(colorsFromManaCost('')).toEqual([]);
    expect(colorsFromManaCost(null)).toEqual([]);
    expect(colorsFromManaCost(undefined)).toEqual([]);
  });

  it('handles hybrid costs (e.g. {U/B})', () => {
    const out = colorsFromManaCost('{2}{U/B}{R}').sort();
    expect(out).toEqual(['B', 'R', 'U']);
  });

  it('ignores generic-only costs', () => {
    expect(colorsFromManaCost('{4}')).toEqual([]);
  });

  it('formats cost with middle-dot separator', () => {
    expect(fmtManaCost('{2}{U}{B}')).toBe('2 · U · B');
    expect(fmtManaCost('')).toBe('');
  });
});

describe('deriveType', () => {
  it('reads the type line first, then falls back to deck role', () => {
    expect(deriveType('Legendary Creature — Eldrazi', 'Creature')).toBe('Creature');
    expect(deriveType('Land', undefined)).toBe('Land');
    expect(deriveType('Instant', undefined)).toBe('Instant');
    expect(deriveType('', 'Land')).toBe('Land');
    expect(deriveType(undefined, undefined)).toBe('Other');
  });
});

describe('countLandsInHand', () => {
  it('counts lands using cached metadata, falling back to deck role', () => {
    const cache: Record<string, Partial<CardEntry>> = {
      'Sol Ring': { type_line: 'Artifact' },
      'Ancient Tomb': { type_line: 'Land' },
    };
    const metaFor = (n: string): Partial<CardEntry> | null => cache[n] ?? null;
    const hand: { name: string; type?: string }[] = [
      { name: 'Sol Ring', type: 'Artifact' },
      { name: 'Ancient Tomb', type: 'Land' },
      { name: 'Wastes', type: 'Land' }, // no cache entry → falls back to row.type
      { name: 'Lightning Bolt', type: 'Instant' },
    ];
    expect(countLandsInHand(hand, metaFor)).toBe(2);
  });
});

describe('computeSwapDelta', () => {
  // 7-card mini-deck the deltas reference.
  const decklist: RawDecklistCard[] = [
    { name: 'Sol Ring', type: 'Artifact' },
    { name: 'Ancient Tomb', type: 'Land' },
    { name: 'Wastes', type: 'Land' },
    { name: 'Lightning Bolt', type: 'Instant' },
    { name: 'Counterspell', type: 'Instant' },
    { name: 'Shock', type: 'Instant' },
    { name: 'Mana Vault', type: 'Artifact' },
  ];
  const cache: Record<string, Partial<CardEntry>> = {
    'Sol Ring': { cmc: 1, mana_cost: '{1}', type_line: 'Artifact' },
    'Ancient Tomb': { cmc: 0, mana_cost: '', type_line: 'Land' },
    Wastes: { cmc: 0, mana_cost: '', type_line: 'Land' },
    'Lightning Bolt': { cmc: 1, mana_cost: '{R}', type_line: 'Instant' },
    Counterspell: { cmc: 2, mana_cost: '{U}{U}', type_line: 'Instant' },
    Shock: { cmc: 1, mana_cost: '{R}', type_line: 'Instant' },
    'Mana Vault': { cmc: 1, mana_cost: '{1}', type_line: 'Artifact' },
    'Demonic Tutor': { cmc: 2, mana_cost: '{1}{B}', type_line: 'Sorcery' },
    Forest: { cmc: 0, mana_cost: '', type_line: 'Basic Land — Forest' },
  };
  const metaFor = (n: string): Partial<CardEntry> | null => cache[n] ?? null;
  const synergies = [
    { title: 'Burn package', description: '', cards: ['Lightning Bolt', 'Shock'] },
    { title: 'Black tutors', description: '', cards: ['Demonic Tutor', 'Vampiric Tutor'] },
  ];
  const isGC = (n: string) => n === 'Demonic Tutor' || n === 'Mana Vault';

  it('reports CMC change, type change, and color delta when swapping cut→add', () => {
    const d = computeSwapDelta({
      cutCard: { name: 'Lightning Bolt', type: 'Instant' },
      addCard: { name: 'Demonic Tutor', type: 'Sorcery' },
      cutMeta: cache['Lightning Bolt'],
      addMeta: cache['Demonic Tutor'],
      decklist,
      metaFor,
      synergies,
      isGameChanger: isGC,
      gameChangers: 1, // pretend deck already has Mana Vault
    });
    expect(d.cmcChange).toBe(1);
    expect(d.typeChanged).toBe(true);
    expect(d.cutType).toBe('Instant');
    expect(d.addType).toBe('Sorcery');
    expect(d.colorDelta).toEqual({ R: -1, B: 1 });
    // Lands unchanged (neither side is a land).
    expect(d.landsBefore).toBe(d.landsAfter);
  });

  it('flags broken synergy when cutting a synergy-participant', () => {
    const d = computeSwapDelta({
      cutCard: { name: 'Lightning Bolt', type: 'Instant' },
      addCard: { name: 'Demonic Tutor', type: 'Sorcery' },
      cutMeta: cache['Lightning Bolt'],
      addMeta: cache['Demonic Tutor'],
      decklist,
      metaFor,
      synergies,
      isGameChanger: isGC,
      gameChangers: 1,
    });
    expect(d.synergiesBroken.map((s) => s.title)).toEqual(['Burn package']);
    expect(d.synergiesKept.map((s) => s.title)).toEqual(['Black tutors']);
  });

  it('detects GC adding when cut is non-GC and add is GC', () => {
    const d = computeSwapDelta({
      cutCard: { name: 'Lightning Bolt', type: 'Instant' },
      addCard: { name: 'Demonic Tutor', type: 'Sorcery' },
      cutMeta: cache['Lightning Bolt'],
      addMeta: cache['Demonic Tutor'],
      decklist,
      metaFor,
      synergies,
      isGameChanger: isGC,
      gameChangers: 1,
    });
    expect(d.gcKind).toBe('adding');
    expect(d.gcDetail).toBe('+1 GC · 1 → 2');
  });

  it('detects GC removing when cut is GC and add is non-GC', () => {
    const d = computeSwapDelta({
      cutCard: { name: 'Mana Vault', type: 'Artifact' },
      addCard: { name: 'Sol Ring', type: 'Artifact' },
      cutMeta: cache['Mana Vault'],
      addMeta: cache['Sol Ring'],
      decklist,
      metaFor,
      synergies,
      isGameChanger: isGC,
      gameChangers: 1,
    });
    expect(d.gcKind).toBe('removing');
    expect(d.gcDetail).toBe('−1 GC · 1 → 0');
  });

  it('detects GC swap (GC for GC, count unchanged)', () => {
    const d = computeSwapDelta({
      cutCard: { name: 'Mana Vault', type: 'Artifact' },
      addCard: { name: 'Demonic Tutor', type: 'Sorcery' },
      cutMeta: cache['Mana Vault'],
      addMeta: cache['Demonic Tutor'],
      decklist,
      metaFor,
      synergies,
      isGameChanger: isGC,
      gameChangers: 1,
    });
    expect(d.gcKind).toBe('swap');
    expect(d.gcDetail).toBe('GC for GC — count unchanged');
  });

  it('updates land count when adding a land and cutting a non-land', () => {
    const d = computeSwapDelta({
      cutCard: { name: 'Lightning Bolt', type: 'Instant' },
      addCard: { name: 'Forest', type: 'Land' },
      cutMeta: cache['Lightning Bolt'],
      addMeta: cache['Forest'],
      decklist,
      metaFor,
      synergies: [],
      isGameChanger: () => false,
      gameChangers: 0,
    });
    expect(d.landsBefore).toBe(2);
    expect(d.landsAfter).toBe(3);
  });

  it('changes the avg CMC when swapping spells', () => {
    // Decklist non-lands: SR(1), Bolt(1), Counter(2), Shock(1), Vault(1) → 6/5 = 1.2
    // Cut Counterspell (2) → 4/4 = 1.0; add Demonic Tutor (2) → 6/5 = 1.2; net 0
    const sameAvg = computeSwapDelta({
      cutCard: { name: 'Counterspell', type: 'Instant' },
      addCard: { name: 'Demonic Tutor', type: 'Sorcery' },
      cutMeta: cache['Counterspell'],
      addMeta: cache['Demonic Tutor'],
      decklist,
      metaFor,
      synergies: [],
      isGameChanger: () => false,
      gameChangers: 0,
    });
    expect(sameAvg.avgCmcBefore).toBeCloseTo(1.2, 5);
    expect(sameAvg.avgCmcAfter).toBeCloseTo(1.2, 5);
    expect(sameAvg.avgCmcChange).toBeCloseTo(0, 5);

    // Cut Bolt (1) → 5/4 = 1.25; add Demonic Tutor (2) → 7/5 = 1.4; net +0.2
    const upAvg = computeSwapDelta({
      cutCard: { name: 'Lightning Bolt', type: 'Instant' },
      addCard: { name: 'Demonic Tutor', type: 'Sorcery' },
      cutMeta: cache['Lightning Bolt'],
      addMeta: cache['Demonic Tutor'],
      decklist,
      metaFor,
      synergies: [],
      isGameChanger: () => false,
      gameChangers: 0,
    });
    expect(upAvg.avgCmcChange).toBeGreaterThan(0);
  });

  it('does not crash when metadata is missing — falls back to deck row.type for lands', () => {
    const d = computeSwapDelta({
      cutCard: { name: 'UnknownLand', type: 'Land' },
      addCard: { name: 'UnknownSpell', type: 'Instant' },
      cutMeta: null,
      addMeta: null,
      decklist,
      metaFor,
      synergies: [],
      isGameChanger: () => false,
      gameChangers: 0,
    });
    // Type-derived land status still respected.
    expect(d.cutType).toBe('Land');
    expect(d.addType).toBe('Instant');
    expect(d.cmcChange).toBeNull();
  });
});
