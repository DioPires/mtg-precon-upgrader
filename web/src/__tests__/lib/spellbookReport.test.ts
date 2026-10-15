// DEC-487 — Combo Lab report helpers (bracket disclosure + export).

import { describe, it, expect } from 'vitest';
import {
  buildBracketDisclosure,
  buildPlainTextExport,
  buildMarkdownExport,
  isTwoCardInfinite,
  isWinCombo,
  pieceCount,
  type ComboReport,
} from '../../lib/spellbookReport';
import type { SpellbookCombo } from '../../data/spellbook';
import type { CompletionReport } from '../../lib/nearMissComplete';

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

  const completions: CompletionReport = {
    deckColorIdentity: 'BG',
    poolSize: 31830,
    currency: 'eur',
    tierBAvailable: true,
    tierB: [
      {
        card: { name: 'Panharmonicon', ci: '', price: 5.08, owned: null },
        loopCards: ['Basalt Monolith', 'Rings of Brighthearth'],
        resource: 'mana',
        shortfall: 1,
        closerFeature: 'trigger_doubler',
        closerLabel: 'Trigger doubler (ambient)',
        distance: 0.2,
      },
    ],
    tierC: [
      {
        card: { name: 'Academy Manufactor', ci: '', price: 5.32, owned: null },
        couplings: [
          {
            deckFeature: 'dies_trigger',
            completerFeature: 'trigger_doubler',
            label: 'Death payoff ↔ Trigger doubler (ambient)',
            economy: 'dies',
            magnitude: 1,
            signal: 4,
          },
        ],
        economies: ['dies'],
        distance: 1,
        band: 'strong',
      },
    ],
    counts: {
      tierCConsidered: 100,
      tierCTotal: 3,
      tierC: 1,
      tierBTotal: 2,
      tierB: 1,
      droppedByColor: 10,
      droppedByPrice: 2,
      droppedByOwned: 0,
    },
    elapsedMs: 58,
  };

  it('appends computed completions preserving Tier B/C labels (NM-1 / EI-4)', () => {
    const txt = buildPlainTextExport(report, completions);
    expect(txt).toContain('COMPUTED NEAR-MISS COMPLETIONS');
    expect(txt).toMatch(/\[Tier B · verified under the model\] Panharmonicon/);
    expect(txt).toContain('Closes the mana leak on Basalt Monolith + Rings of Brighthearth');
    expect(txt).toMatch(/\[Tier C · strong\] Academy Manufactor/);
    expect(txt).toContain('€5.08');
    expect(txt).toContain('color identity BG');
    expect(txt).toMatch(/TIER B · COMPUTED COMPLETIONS \(1 of 2\)/);
  });

  it('discloses when the Tier-B verifier index is unavailable', () => {
    const paste = { ...completions, tierBAvailable: false, tierB: [] };
    const txt = buildPlainTextExport({ ...report, mode: 'paste' }, paste);
    expect(txt).toContain('the Tier-B verifier index could not be loaded');
  });
});

describe('buildMarkdownExport (RT-4 shareable rendering)', () => {
  const report: ComboReport = {
    mode: 'fleet',
    deckLabel: 'Eternal Agony',
    commander: ['Valgavoth, Harrower of Souls'],
    corpusVersion: '2026-08-15T13:18:26+00:00',
    included: [combo({ produces: ['Infinite mana'], bracketTag: 'P' })],
    nearMisses: [combo({ id: 'nm', distance: 1, missing: { cards: ['Mindcrank'], templates: [] } })],
    nearMissesTotal: 1,
    cardsAnalyzed: 99,
    cardsTotal: 99,
    unresolved: [],
  };

  it('renders Markdown headings and preserves every tier label + attribution', () => {
    const md = buildMarkdownExport(report);
    expect(md).toMatch(/^# Combo Lab — Eternal Agony/m);
    expect(md).toContain('## Tier A · Combos present');
    expect(md).toMatch(/\*\*\[Tier A\]\*\*/);
    expect(md).toContain('epistemic tier');
    expect(md).toContain('Commander Spellbook');
    expect(md).toContain('Wizards of the Coast');
  });
});

describe('the count of cards analyzed in a paste report (DEC-1142)', () => {
  const paste = (cardsAnalyzed: number, cardsTotal: number): ComboReport => ({
    mode: 'paste',
    deckLabel: 'Pasted decklist',
    commander: [],
    corpusVersion: '2026-08-15T13:18:26+00:00',
    included: [],
    nearMisses: [],
    nearMissesTotal: 0,
    cardsAnalyzed,
    cardsTotal,
    unresolved: [],
  });

  // A paste of one name that the index does not resolve gives 0 of 1. The noun
  // follows the total.
  it('reads `of 1 card` in the plain-text export for a total of 1', () => {
    expect(buildPlainTextExport(paste(0, 1))).toContain('\nAnalyzed 0 of 1 card.\n');
  });

  it('reads `of 2 cards` in the plain-text export for a total of 2', () => {
    expect(buildPlainTextExport(paste(1, 2))).toContain('\nAnalyzed 1 of 2 cards.\n');
  });

  it('reads `of 1 card` in the Markdown export for a total of 1', () => {
    expect(buildMarkdownExport(paste(0, 1))).toContain('\n_Analyzed 0 of 1 card._\n');
  });

  it('reads `of 2 cards` in the Markdown export for a total of 2', () => {
    expect(buildMarkdownExport(paste(1, 2))).toContain('\n_Analyzed 1 of 2 cards._\n');
  });
});
