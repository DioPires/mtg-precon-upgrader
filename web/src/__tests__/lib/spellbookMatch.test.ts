// DEC-487 — paste-mode matching against the Spellbook matcher index.

import { describe, it, expect } from 'vitest';
import {
  normalizeName,
  nameKeys,
  parseDecklist,
  matchDecklist,
} from '../../lib/spellbookMatch';
import type { MatcherIndex } from '../../data/spellbook';

describe('normalizeName', () => {
  it('casefolds, strips accents and punctuation (matches the Python contract)', () => {
    expect(normalizeName("Ashnod's Altar")).toBe('ashnod s altar');
    // Combining diacritics decompose under NFKD and are stripped.
    expect(normalizeName('Jötun Grunt')).toBe('jotun grunt');
    expect(normalizeName('  Sol   Ring ')).toBe('sol ring');
    // Æ has no NFKD decomposition, so it is stripped identically on both sides
    // (real card names already use the "Ae" spelling, e.g. "Aether Vial").
    expect(normalizeName('Æther Vial')).toBe('ther vial');
  });
});

describe('nameKeys', () => {
  it('adds a front-face key for split/DFC cards', () => {
    const keys = nameKeys('Hagra Mauling // Hagra Broodpit');
    expect(keys).toContain('hagra mauling hagra broodpit');
    expect(keys).toContain('hagra mauling');
  });
});

describe('parseDecklist', () => {
  it('strips quantities, set/collector suffixes, and section headers', () => {
    const { cardNames } = parseDecklist(
      ['Deck', '1 Sol Ring (C21) 263', '3x Forest', 'Ashnod’s Altar', '', '# a comment'].join('\n'),
    );
    expect(cardNames).toEqual(['Sol Ring', 'Forest', 'Ashnod’s Altar']);
  });

  it('routes commander-tagged lines to commanderNames', () => {
    const { cardNames, commanderNames } = parseDecklist(
      ['1 Meren of Clan Nel Toth *CMDR*', '1 Sol Ring'].join('\n'),
    );
    expect(commanderNames).toEqual(['Meren of Clan Nel Toth']);
    expect(cardNames).toEqual(['Sol Ring']);
  });

  it('collects unresolvable (letterless) lines for IN-6, proceeding on the rest', () => {
    const { cardNames, unresolved } = parseDecklist(['1 Sol Ring', '123', '- - -'].join('\n'));
    expect(cardNames).toEqual(['Sol Ring']);
    // Letterless content lines cannot be a card name → surfaced as unresolved.
    expect(unresolved).toEqual(['123', '- - -']);
  });
});

// Synthetic index: variant 1 is a 2-card combo (cards 10+11), variant 2 needs a
// commander (card 12) + a normal card (13), variant 3 has a template (100).
const INDEX: MatcherIndex = {
  meta: {
    source: 'commanderspellbook',
    sourceUrl: 'x',
    corpusVersion: '2026-08-15T00:00:00+00:00',
    spellbookApiVersion: '6',
    generatedAt: 'x',
    variantCount: 3,
    cardCount: 4,
    matchingModel: 'phase0-card-set-containment',
    bracketTagLegend: { E: 'Exhibition' },
  },
  cards: {
    '10': { n: 'Sol Ring', o: 'a' },
    '11': { n: 'Tidespout Tyrant', o: 'b' },
    '12': { n: 'Meren of Clan Nel Toth', o: 'c' },
    '13': { n: 'Viscera Seer', o: 'd' },
  },
  templates: { '100': { n: 'Sacrifice Outlet', q: 'o:sacrifice' } },
  features: { '1': 'Infinite mana', '2': 'Infinite ETB' },
  variants: [
    { id: 'v1', u: [10, 11], c: [], r: [], p: [1], i: 'U', b: 'S', m: 0, pop: 500 },
    { id: 'v2', u: [12, 13], c: [12], r: [], p: [2], i: 'BG', b: 'E', m: 0, pop: 300 },
    { id: 'v3', u: [10, 13], c: [], r: [100], p: [2], i: 'B', b: 'E', m: 0, pop: 200 },
  ],
};

describe('matchDecklist', () => {
  it('marks a fully-present 2-card combo as included', () => {
    const r = matchDecklist({ cardNames: ['Sol Ring', 'Tidespout Tyrant'], commanderNames: [] }, INDEX);
    expect(r.included.map((c) => c.id)).toEqual(['v1']);
    expect(r.included[0].distance).toBe(0);
  });

  it('reports a 1-away near-miss with the missing card named', () => {
    const r = matchDecklist({ cardNames: ['Sol Ring'], commanderNames: [] }, INDEX);
    const v1 = r.nearMisses.find((c) => c.id === 'v1');
    expect(v1?.distance).toBe(1);
    expect(v1?.missing?.cards).toEqual(['Tidespout Tyrant']);
  });

  it('honors mustBeCommander: card in the 99 does not satisfy a commander slot', () => {
    // Meren in the deck (not commander) + Viscera Seer → v2 must NOT be included.
    const inList = matchDecklist(
      { cardNames: ['Meren of Clan Nel Toth', 'Viscera Seer'], commanderNames: [] },
      INDEX,
    );
    expect(inList.included.map((c) => c.id)).not.toContain('v2');

    // Meren designated as commander → v2 included.
    const asCmdr = matchDecklist(
      { cardNames: ['Viscera Seer'], commanderNames: ['Meren of Clan Nel Toth'] },
      INDEX,
    );
    expect(asCmdr.included.map((c) => c.id)).toContain('v2');
  });

  it('treats a template requirement as an unmet near-miss element', () => {
    // Have both cards of v3 but not the template → 1-away near-miss needing the template.
    const r = matchDecklist({ cardNames: ['Sol Ring', 'Viscera Seer'], commanderNames: [] }, INDEX);
    const v3 = r.nearMisses.find((c) => c.id === 'v3');
    expect(v3?.distance).toBe(1);
    expect(v3?.missing?.templates.map((t) => t.name)).toEqual(['Sacrifice Outlet']);
    // v3 is never "included" because the template stays unmet in Phase 0.
    expect(r.included.map((c) => c.id)).not.toContain('v3');
  });

  it('drops noise: no overlap is not a near-miss', () => {
    const r = matchDecklist({ cardNames: ['Island'], commanderNames: [] }, INDEX);
    expect(r.included).toHaveLength(0);
    expect(r.nearMisses).toHaveLength(0);
  });
});
