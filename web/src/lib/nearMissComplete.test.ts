// DEC-516 (DEC-476 Phase 4) — computed near-miss completion engine tests.
//
// Runs the real full-coverage KB feature index + synergy config + committed price
// index (the deployed artifacts), so the assertions guard the engine end to end:
// linear pool scan (NM-4), the distance-to-closure metric (6.6), the NM-5 filters,
// and Tier-B deficit cover over a precomputed deficit vector.

import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, it, expect } from 'vitest';
import {
  analyzeCompletions,
  distanceToClosure,
  deriveColorIdentity,
  parseOwnedCollection,
} from './nearMissComplete';
import type { FeatureIndex, SynergyConfig } from '../data/synergy';
import type { PriceIndex } from '../data/prices';
import type { TierBFinding } from '../data/tierB';

const here = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(here, '..', '..', '..');
const rj = <T>(rel: string): T => JSON.parse(readFileSync(resolve(repoRoot, rel), 'utf-8')) as T;

const featureIndex = rj<FeatureIndex>('data/combo-kb/feature-index.json');
const config = rj<SynergyConfig>('data/combo-kb/synergy-config.json');
const prices = rj<PriceIndex>('data/spellbook/price-index.json');

const ARISTOCRATS = [
  'Blood Artist',
  'Zulaport Cutthroat',
  'Viscera Seer',
  "Ashnod's Altar",
  'Meren of Clan Nel Toth',
  'Grave Pact',
  'Dictate of Erebos',
  'Pitiless Plunderer',
  'Reassembling Skeleton',
  'Gravecrawler',
  'Carrion Feeder',
];

const MANA_ENGINE: TierBFinding = {
  cards: ['Basalt Monolith', 'Rings of Brighthearth'],
  closes: false,
  template: '',
  loopClass: 'engine',
  k: null,
  band: 'engine',
  resultTypes: [],
  finiteZoneBound: null,
  trace: [],
  deficit: [{ resource: 'mana', shortfall: 1, note: 'needs a mana amplifier or cheaper untap' }],
  prerequisites: { minInitialMana: 0, ordering: [], guards: [], note: '' },
  provenance: { members: [], ontologyVersion: '', extractorVersion: '', corpusVersion: '', gate: '' },
  tierCapped: null,
  corroboration: false,
};

const baseFilters = (deckColorIdentity: string) => ({
  deckColorIdentity,
  currency: 'eur' as const,
  maxPrice: null,
  ownedOnly: false,
});

describe('distanceToClosure (PRD 6.6)', () => {
  it('is monotone in deficit magnitude at equal piece count', () => {
    expect(distanceToClosure(0, 1)).toBeLessThan(distanceToClosure(0, 3));
    expect(distanceToClosure(0, 3)).toBeLessThan(distanceToClosure(0, 10));
  });

  it('is monotone in missing pieces', () => {
    expect(distanceToClosure(1, 0)).toBeLessThan(distanceToClosure(2, 0));
    expect(distanceToClosure(0, 100)).toBeLessThan(distanceToClosure(1, 0));
  });

  it('ranks "missing 1 generic mana" closer than "missing a whole piece" (6.6 example)', () => {
    // A pure numeric deficit (all pieces present) beats a missing-card near-miss.
    expect(distanceToClosure(0, 1)).toBeLessThan(distanceToClosure(1, 0));
  });
});

describe('deriveColorIdentity', () => {
  it('unions card identities into a WUBRG-ordered string', () => {
    expect(deriveColorIdentity(ARISTOCRATS, featureIndex)).toBe('BG');
  });
  it('returns C for an all-colorless list', () => {
    expect(deriveColorIdentity(['Sol Ring', 'Basalt Monolith'], featureIndex)).toBe('C');
  });
});

describe('analyzeCompletions — Tier C half-edge cover', () => {
  const report = analyzeCompletions(ARISTOCRATS, featureIndex, config, {
    filters: baseFilters('BG'),
    prices,
  });

  it('scans the full pool within the interactive budget (NF-4)', () => {
    expect(report.poolSize).toBeGreaterThan(30000);
    expect(report.elapsedMs).toBeLessThan(1000);
  });

  it('surfaces ranked Tier-C completions with explanatory couplings (DC-3/NM-7)', () => {
    expect(report.tierC.length).toBeGreaterThan(0);
    for (const c of report.tierC) {
      expect(c.couplings.length).toBeGreaterThan(0);
      for (const e of c.couplings) expect(e.label).toContain('↔');
    }
  });

  it('never recommends a card already in the deck', () => {
    const inDeck = new Set(ARISTOCRATS.map((n) => n.toLowerCase()));
    for (const c of report.tierC) expect(inDeck.has(c.card.name.toLowerCase())).toBe(false);
  });

  it('only recommends cards within the deck color identity (NM-5 color)', () => {
    for (const c of report.tierC) {
      for (const ch of c.card.ci) if ('WUBRG'.includes(ch)) expect('BG').toContain(ch);
    }
    expect(report.counts.droppedByColor).toBeGreaterThan(0);
  });

  it('respects the price cap and reports the drop count (NM-5 price)', () => {
    const capped = analyzeCompletions(ARISTOCRATS, featureIndex, config, {
      filters: { ...baseFilters('BG'), maxPrice: 2 },
      prices,
    });
    for (const c of capped.tierC) {
      if (c.card.price != null) expect(c.card.price).toBeLessThanOrEqual(2);
    }
    expect(capped.counts.droppedByPrice).toBeGreaterThan(0);
  });
});

describe('analyzeCompletions — Tier B deficit cover', () => {
  it('is unavailable (deferred) when no engines are supplied — paste mode', () => {
    const r = analyzeCompletions(ARISTOCRATS, featureIndex, config, {
      filters: baseFilters('BG'),
      prices,
    });
    expect(r.tierBAvailable).toBe(false);
    expect(r.tierB).toHaveLength(0);
  });

  it('covers a mana leak with per-iteration amplifiers/reducers only (NM-2/NM-3)', () => {
    const r = analyzeCompletions(ARISTOCRATS, featureIndex, config, {
      filters: baseFilters('BG'),
      prices,
      engines: [MANA_ENGINE],
    });
    expect(r.tierBAvailable).toBe(true);
    expect(r.tierB.length).toBeGreaterThan(0);
    for (const b of r.tierB) {
      expect(b.resource).toBe('mana');
      expect(['trigger_doubler', 'cost_reduction']).toContain(b.closerFeature);
      // A pure numeric deficit ranks closer than a whole missing piece (6.6).
      expect(b.distance).toBeLessThan(1);
      expect(b.loopCards).toEqual(MANA_ENGINE.cards);
    }
  });

  it('skips KB-gap abstentions (shortfall = null)', () => {
    const abstain: TierBFinding = {
      ...MANA_ENGINE,
      deficit: [{ resource: 'recurrence', shortfall: null, note: 'kb gap' }],
    };
    const r = analyzeCompletions(ARISTOCRATS, featureIndex, config, {
      filters: baseFilters('BG'),
      prices,
      engines: [abstain],
    });
    expect(r.tierB).toHaveLength(0);
  });
});

describe('parseOwnedCollection (OQ-1)', () => {
  it('parses plain and quantity-prefixed lines', () => {
    const owned = parseOwnedCollection('1 Sol Ring\n3x Blood Artist\nGrave Pact');
    expect(owned).not.toBeNull();
    expect(owned!.has('sol ring')).toBe(true);
    expect(owned!.has('blood artist')).toBe(true);
    expect(owned!.has('grave pact')).toBe(true);
  });

  it('parses CSV export rows (Owned.csv shape)', () => {
    const owned = parseOwnedCollection('Count,Name,Edition\n1,"Ashnod\'s Altar",FEM\n2,Sol Ring,C21');
    expect(owned!.has('ashnod s altar')).toBe(true);
    expect(owned!.has('sol ring')).toBe(true);
    // Header row should not produce a spurious "name" key mapping to a real card.
    expect(owned!.has('count')).toBe(false);
  });

  it('returns null for empty input', () => {
    expect(parseOwnedCollection('\n\n# comment\n')).toBeNull();
  });

  it('drives the ownedOnly filter', () => {
    const ownedKeys = parseOwnedCollection('Blood Artist\nGrave Pact\nMidnight Reaper')!;
    const r = analyzeCompletions(ARISTOCRATS, featureIndex, config, {
      filters: { ...baseFilters('BG'), ownedOnly: true, ownedKeys },
      prices,
    });
    // Everything surfaced must be owned; drops counted.
    for (const c of r.tierC) expect(c.card.owned).toBe(true);
  });
});
