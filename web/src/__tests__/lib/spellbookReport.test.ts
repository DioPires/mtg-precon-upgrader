// DEC-487 — Combo Lab report helpers (bracket disclosure + export).

import { describe, it, expect } from 'vitest';
import {
  buildBracketDisclosure,
  buildPlainTextExport,
  isTwoCardInfinite,
  isWinCombo,
  pieceCount,
  type ComboReport,
} from '../../lib/spellbookReport';
import type { SpellbookCombo } from '../../data/spellbook';

function combo(over: Partial<SpellbookCombo>): SpellbookCombo {
  return {
    id: 'x',
    permalink: 'https://commanderspellbook.com/combo/x/',
    cards: [{ name: 'A', mustBeCommander: false, quantity: 1, zones: [] }],
    templates: [],
    produces: [],
    identity: 'C',
    bracketTag: 'E',
    manaNeeded: '',
    manaValueNeeded: 0,
    prerequisites: { easy: '', notable: '' },
    steps: '',
    notes: '',
    prices: {},
    popularity: 0,
    distance: 0,
    ...over,
  };
}

describe('finding classifiers', () => {
  it('counts cards + templates as pieces', () => {
    expect(pieceCount(combo({ cards: [], templates: [{ name: 'T', query: '' }] }))).toBe(1);
  });

  it('flags win combos and two-card infinites', () => {
    const winTwo = combo({
      cards: [
        { name: 'A', mustBeCommander: false, quantity: 1, zones: [] },
        { name: 'B', mustBeCommander: false, quantity: 1, zones: [] },
      ],
      produces: ['Infinite mana', 'Each opponent loses the game'],
    });
    expect(isWinCombo(winTwo)).toBe(true);
    expect(isTwoCardInfinite(winTwo)).toBe(true);
    expect(isTwoCardInfinite(combo({ produces: ['Infinite mana'] }))).toBe(false); // 1 piece
  });
});

describe('buildBracketDisclosure', () => {
  it('summarizes counts, two-card infinites, wins, and bracket tags', () => {
    const included = [
      combo({
        cards: [
          { name: 'A', mustBeCommander: false, quantity: 1, zones: [] },
          { name: 'B', mustBeCommander: false, quantity: 1, zones: [] },
        ],
        produces: ['Infinite mana'],
        bracketTag: 'S',
      }),
      combo({ produces: ['Target opponent loses the game'], bracketTag: 'E' }),
    ];
    const d = buildBracketDisclosure(included);
    expect(d.totalCombos).toBe(2);
    expect(d.twoCardInfinites).toBe(1);
    expect(d.winCombos).toBe(1);
    expect(d.byBracketTag.map((b) => b.label)).toEqual(expect.arrayContaining(['Spicy', 'Exhibition']));
  });
});

describe('buildPlainTextExport', () => {
  const report: ComboReport = {
    mode: 'fleet',
    deckLabel: 'Eternal Agony',
    commander: ['Valgavoth, Harrower of Souls'],
    corpusVersion: '2026-08-15T13:18:26+00:00',
    included: [combo({ produces: ['Infinite mana'], bracketTag: 'P' })],
    nearMisses: [
      combo({
        id: 'nm',
        distance: 1,
        produces: ['Infinite mill'],
        missing: { cards: ['Mindcrank'], templates: [] },
      }),
    ],
    nearMissesTotal: 5,
    cardsAnalyzed: 99,
    cardsTotal: 99,
    unresolved: [],
  };

  it('preserves tier labels, attribution, corpus version, and caveats (EI-4)', () => {
    const txt = buildPlainTextExport(report);
    expect(txt).toContain('TIER A — CURATED');
    expect(txt).toMatch(/\[Tier A\]/);
    expect(txt).toMatch(/\[Tier A near-miss\]/);
    expect(txt).toContain('Commander Spellbook');
    expect(txt).toContain('goldfish');
    expect(txt).toContain('exhaustiveness'); // EI-3 non-exhaustiveness caveat present
    expect(txt).toContain('2026-08-15');
    expect(txt).toContain('Needs: Mindcrank');
    // Near-miss total surfaced when capped.
    expect(txt).toMatch(/NEAR-MISSES.*of 5/s);
  });
});
