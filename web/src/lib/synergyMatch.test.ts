// DEC-491 — paste-mode Tier-C synergy engine parity + unit tests.
//
// The parity test is the acceptance gate: analyze() must reproduce the
// authoritative Python-engine output in __fixtures__/synergy-parity.json
// (paste mode, deep scan) exactly. If it fails, the TS port has a bug — fix the
// port, never weaken the assertions.

import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, it, expect } from 'vitest';
import { analyze, normalizeName, nameKeys } from './synergyMatch';
import type { FeatureIndex, SynergyConfig } from '../data/synergy';

const here = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(here, '..', '..', '..'); // web/src/lib → repo root
const readJson = <T>(rel: string): T => JSON.parse(readFileSync(resolve(repoRoot, rel), 'utf-8')) as T;

const featureIndex = readJson<FeatureIndex>('data/combo-kb/feature-index.json');
const config = readJson<SynergyConfig>('data/combo-kb/synergy-config.json');

interface ParityFixture {
  names: string[];
  counts: unknown;
  uncovered: string[];
  nodeCount: number;
  edgeCount: number;
  truncated: unknown;
  pairs: unknown[];
  triples: unknown[];
  cycles: unknown[];
}
const fixture = readJson<ParityFixture>('web/src/lib/__fixtures__/synergy-parity.json');

describe('normalizeName', () => {
  it('casefolds, strips accents and punctuation (matches the Python contract)', () => {
    expect(normalizeName("Ashnod's Altar")).toBe('ashnod s altar');
    expect(normalizeName('Jötun Grunt')).toBe('jotun grunt');
    expect(normalizeName('  Sol   Ring ')).toBe('sol ring');
  });
});

describe('nameKeys', () => {
  it('aliases EVERY face of a split/DFC card (not just the front)', () => {
    const keys = nameKeys('Tony Stark // The Invincible Iron Man');
    expect(keys).toContain('tony stark the invincible iron man');
    expect(keys).toContain('tony stark');
    expect(keys).toContain('the invincible iron man');
  });
});

describe('analyze — Python parity (paste mode, deep scan)', () => {
  const result = analyze(fixture.names, featureIndex, config, { deep: true });

  it('reproduces counts exactly', () => {
    expect(result.counts).toEqual(fixture.counts);
  });

  it('reproduces pairs exactly', () => {
    expect(result.pairs).toEqual(fixture.pairs);
  });

  it('reproduces triples exactly', () => {
    expect(result.triples).toEqual(fixture.triples);
  });

  it('reproduces cycles exactly', () => {
    expect(result.cycles).toEqual(fixture.cycles);
  });

  it('reproduces uncovered, node/edge counts, and truncation flags', () => {
    expect(result.uncovered).toEqual(fixture.uncovered);
    expect(result.nodeCount).toBe(fixture.nodeCount);
    expect(result.edgeCount).toBe(fixture.edgeCount);
    expect(result.truncated).toEqual(fixture.truncated);
    expect(result.crowdPriorApplied).toBe(false);
  });
});

describe('analyze — unit behaviors', () => {
  // Synthetic index: two cards whose only overlap is the mana_add ↔ mana_sink
  // noise pair, which is excluded by construction.
  const noiseIndex: FeatureIndex = {
    cards: {
      'oid-source': { n: 'Test Mana Source', ci: '', p: [['mana_add', 1]] },
      'oid-sink': { n: 'Test Mana Sink', ci: '', p: [['mana_sink', 1]] },
    },
  };

  it('excludes the mana_add ↔ mana_sink noise pair (no edge)', () => {
    const r = analyze(['Test Mana Source', 'Test Mana Sink'], noiseIndex, config, { deep: true });
    expect(r.nodeCount).toBe(2);
    expect(r.edgeCount).toBe(0);
    expect(r.pairs).toEqual([]);
  });

  it('surfaces a genuine compatible pair (etb_trigger ↔ recursion)', () => {
    const idx: FeatureIndex = {
      cards: {
        'oid-etb': { n: 'Test ETB', ci: '', p: [['etb_trigger', 1]] },
        'oid-rec': { n: 'Test Recursion', ci: '', p: [['recursion', 1]] },
      },
    };
    const r = analyze(['Test ETB', 'Test Recursion'], idx, config, { deep: false });
    expect(r.edgeCount).toBe(1);
    expect(r.pairs).toHaveLength(1);
    expect(r.pairs[0].cards).toEqual(['Test ETB', 'Test Recursion']);
    expect(r.pairs[0].edges[0].label).toContain('↔');
  });

  it('reports a name with no KB entry as uncovered', () => {
    const r = analyze(['Zzz Nonexistent Card 9000'], featureIndex, config, { deep: false });
    expect(r.uncovered).toContain('Zzz Nonexistent Card 9000');
    expect(r.counts.uncovered).toBe(1);
    expect(r.nodeCount).toBe(0);
  });
});
