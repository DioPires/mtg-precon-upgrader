// DEC-516 (DEC-476 Phase 4) — paste-mode Tier-B verifier mirror.
//
// Fleet parity: for every fleet deck, run the TS mirror over the deck's decklist +
// commander + curated combos and assert the resulting Tier-B findings match the
// committed per-deck tier-b-loops.json the Python verifier produced (the deployed
// artifacts). This pins byte-parity of the closure verdicts — the CEO's Phase-4
// requirement. Plus targeted unit tests over real KB cards for every template path.

import { readFileSync, existsSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, it, expect } from 'vitest';
import { parseMana, verifyDeck } from './comboVerify';
import type { TierBIndex } from '../data/tierBIndex';
import type { TierBFinding } from '../data/tierB';

const here = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(here, '..', '..', '..');
const rj = <T>(rel: string): T => JSON.parse(readFileSync(resolve(repoRoot, rel), 'utf-8')) as T;

const index = rj<TierBIndex>('data/combo-kb/tier-b-index.json');

interface FleetDeck {
  decklist?: { name: string }[];
  commander?: string;
}
interface Included {
  included?: { cards?: ({ name?: string } | string)[] }[];
}
interface DeckTierB {
  verifiedCorroborated: TierBFinding[];
  verifiedNovel: TierBFinding[];
  engines: TierBFinding[];
  capped: TierBFinding[];
}

const fleetIds: string[] = rj<{ commanders: { id: string }[] }>('data/index.json').commanders.map(
  (c) => c.id,
);

/** A finding keyed by its sorted card list (parity is compared as a set, since the
 * committed order carries the fleet crowd-prior ranking the paste path omits). */
function byKey(findings: TierBFinding[]): Map<string, TierBFinding> {
  const m = new Map<string, TierBFinding>();
  for (const f of findings) m.set(f.cards.join(' | '), f);
  return m;
}

/** Closure-relevant fields — everything except crowd-prior-dependent ordering. */
function closureFields(f: TierBFinding) {
  return {
    cards: f.cards,
    closes: f.closes,
    template: f.template,
    loopClass: f.loopClass,
    k: f.k,
    band: f.band,
    resultTypes: f.resultTypes,
    finiteZoneBound: f.finiteZoneBound,
    trace: f.trace,
    deficit: f.deficit,
    prerequisites: f.prerequisites,
    provenance: f.provenance,
    tierCapped: f.tierCapped,
    corroboration: f.corroboration,
  };
}

describe('parseMana', () => {
  it('prices pure-mana costs', () => {
    expect(parseMana('{3}')).toBe(3);
    expect(parseMana('{1}{B}')).toBe(2);
    expect(parseMana('{C}{C}')).toBe(2);
    expect(parseMana('{2/W}{W}')).toBe(3);
  });
  it('abstains (null) on any non-mana component', () => {
    expect(parseMana('{T}')).toBeNull();
    expect(parseMana('{G}{T}')).toBeNull();
    expect(parseMana('{X}')).toBeNull();
    expect(parseMana('{2}, Sacrifice a creature')).toBeNull();
    expect(parseMana('')).toBeNull();
    expect(parseMana(null)).toBeNull();
  });
});

describe('verifyDeck — titan-convergence known loops', () => {
  const deck = rj<FleetDeck>('data/commanders/titan-convergence/deck.json');
  const combos = rj<Included>('data/commanders/titan-convergence/spellbook-combos.json');
  const names = [...(deck.decklist ?? []).map((c) => c.name), deck.commander ?? ''];
  const curatedCardSets = (combos.included ?? []).map((c) =>
    (c.cards ?? []).map((x) => (typeof x === 'string' ? x : x.name ?? '')),
  );
  const res = verifyDeck(names, index, {
    curatedCardSets,
    commanderNames: deck.commander ? [deck.commander] : [],
  });

  it('corroborates the Basalt Monolith + Forsaken Monument infinite-mana loop', () => {
    const f = res.corroborated.find((x) => x.cards.includes('Forsaken Monument'));
    expect(f).toBeTruthy();
    expect(f!.closes).toBe(true);
    expect(f!.template).toBe('untap_mana');
    expect(f!.k).toBe(0);
    expect(f!.resultTypes).toEqual(['infinite_mana:mana']);
    expect(f!.corroboration).toBe(true);
    expect(f!.prerequisites.guards).toEqual(['control_requirement', 'summoning_sick']);
  });

  it('reports Basalt Monolith + Rings of Brighthearth as a non-closing engine (deficit 1)', () => {
    const f = res.engines.find(
      (x) => x.cards.includes('Rings of Brighthearth') && x.cards.includes('Basalt Monolith'),
    );
    expect(f).toBeTruthy();
    expect(f!.closes).toBe(false);
    expect(f!.deficit).toEqual([
      expect.objectContaining({ resource: 'mana', shortfall: 1 }),
    ]);
  });

  it('never reports a novel Tier-B loop for titan (all closing loops are curated)', () => {
    expect(res.novel).toHaveLength(0);
  });
});

describe('verifyDeck — fleet parity vs committed tier-b-loops.json', () => {
  for (const id of fleetIds) {
    const tblPath = `data/commanders/${id}/tier-b-loops.json`;
    if (!existsSync(resolve(repoRoot, tblPath))) continue;
    it(`${id} matches the Python verifier's findings`, () => {
      const deck = rj<FleetDeck>(`data/commanders/${id}/deck.json`);
      const combosPath = `data/commanders/${id}/spellbook-combos.json`;
      const combos = existsSync(resolve(repoRoot, combosPath))
        ? rj<Included>(combosPath)
        : { included: [] };
      const expected = rj<DeckTierB>(tblPath);
      const names = [...(deck.decklist ?? []).map((c) => c.name), deck.commander ?? ''];
      const curatedCardSets = (combos.included ?? []).map((c) =>
        (c.cards ?? []).map((x) => (typeof x === 'string' ? x : x.name ?? '')),
      );
      const res = verifyDeck(names, index, {
        curatedCardSets,
        commanderNames: deck.commander ? [deck.commander] : [],
      });

      for (const bucket of ['verifiedCorroborated', 'verifiedNovel', 'engines', 'capped'] as const) {
        const got =
          bucket === 'verifiedCorroborated'
            ? res.corroborated
            : bucket === 'verifiedNovel'
              ? res.novel
              : bucket === 'engines'
                ? res.engines
                : res.capped;
        const exp = expected[bucket];
        const gotKeys = byKey(got);
        const expKeys = byKey(exp);
        // Same finding set (keyed by cards) …
        expect([...gotKeys.keys()].sort()).toEqual([...expKeys.keys()].sort());
        // … and every finding's closure fields match byte-for-byte.
        for (const [key, ef] of expKeys) {
          expect(closureFields(gotKeys.get(key)!)).toEqual(closureFields(ef));
        }
      }
    });
  }
});
