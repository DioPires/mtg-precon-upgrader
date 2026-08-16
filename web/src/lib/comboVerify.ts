// Mirror of scripts/combo_verifier_lib.py + scripts/build_tier_b_candidates.build_deck
// — keep in sync; guarded by comboVerify.test.ts (unit + fleet parity vs the
// committed per-deck tier-b-loops.json outputs).
//
// Paste-mode Tier-B loop verifier (DEC-516, DEC-476 Phase 4). Reproduces the Python
// deterministic closure verifier for a pasted decklist, client-side, over the
// committed tier-b-index.json (the loop-relevant raw KB projection the lean
// feature index drops). Everything here is Tier B — machine-verified UNDER LAÇO'S
// MODEL (EI-2), never a comprehensive-rules proof. Corroborated loops remain Tier A
// (Commander Spellbook); the computed verdict is recorded as corroboration only
// (DB-7). Novel infinite discovery is rare by design (DC-6) and strictly gated.
//
// SOUNDNESS is the invariant, not recall (QE-4). Two mechanisms, both ported:
//   1. Provenance gate (plan 6b): a Tier-B verdict consumes only deterministic /
//      human-reviewed KB items; an llm/community item caps the finding at Tier C.
//   2. Corroboration vs novel split (DB-7 / DC-6): only a NOT-in-corpus loop whose
//      closure is fully derivable from the coarse features (CLOSE_SAFE) may be a
//      novel Tier-B finding; other templates may only corroborate a curated combo.
//
// Paste mode = NO EDHREC crowd prior (decision 4); ranking is display-order only
// (never tier, never in the output), so the default weights are used. The parity
// test compares closure fields, which are crowd-prior-independent.

import { nameKeys } from './synergyMatch';
import type { TBRecord, TierBIndex } from '../data/tierBIndex';
import type { TierBDeficit, TierBFinding, TierBCounts, TierBPrerequisites } from '../data/tierB';

// ─── Provenance gate (mirror combo_kb_lib.TIER_B_PROVENANCES) ─────────────────────

const TIER_B_PROVENANCES = new Set(['deterministic', 'human-reviewed']);

function tierBEligible(prov: string): boolean {
  return TIER_B_PROVENANCES.has(prov);
}

// ─── Closure-model constants (mirror combo_verifier_lib) ──────────────────────────

const MAX_CYCLE_PIECES = 3;
const DEFAULT_LIBRARY_SIZE = 99;

// ─── Mana / cost parsing ──────────────────────────────────────────────────────────

const PIP_RE = /\{([^}]+)\}/g;
const GENERIC_RE = /^\d+$/;
const COLOR_PIPS = new Set(['W', 'U', 'B', 'R', 'G']);
const HYBRID = new Set([
  'W/U', 'W/B', 'U/B', 'U/R', 'B/R', 'B/G', 'R/G', 'R/W', 'G/W', 'G/U',
  '2/W', '2/U', '2/B', '2/R', '2/G',
]);

/** Mana value of a cost string IFF the cost is purely mana; otherwise null. A cost
 * with ANY non-mana component ({T}, {Q}, sacrifice text, {X}, Phyrexian, …) returns
 * null — the verifier must never treat such a cost as "free mana" (QE-4). Mirror of
 * combo_verifier_lib.parse_mana. */
export function parseMana(cost: string | null | undefined): number | null {
  if (!cost) return null;
  const pips = [...cost.matchAll(PIP_RE)].map((m) => m[1]);
  // Any text remaining after removing the mana pips is a non-mana cost component.
  const residue = cost.replace(PIP_RE, '');
  if (residue.replace(/[ ,.:]/g, '').length > 0) return null;
  if (pips.length === 0) return null;
  let total = 0;
  for (const p of pips) {
    const pu = p.toUpperCase();
    if (GENERIC_RE.test(pu)) total += parseInt(pu, 10);
    else if (COLOR_PIPS.has(pu) || pu === 'C') total += 1;
    else if (HYBRID.has(pu)) total += pu.startsWith('2/') ? 2 : 1;
    else return null; // {T}, {Q}, {X}, Phyrexian, energy, snow — not pure mana
  }
  return total;
}

// ─── Feature model over a record (post provenance gate when gated) ────────────────

interface Item {
  feature: string;
  magnitude: number;
  economy: string;
  evidence: string;
  provenance: string;
}

function expandItems(raw: TBRecord['pr']): Item[] {
  return (raw ?? []).map((it) => ({
    feature: it.f,
    magnitude: it.m ?? 1,
    economy: it.e ?? '',
    evidence: it.v ?? '',
    provenance: it.p,
  }));
}

/** The loop-relevant projection of one KB record, AFTER the provenance gate
 * (gate=true) or ungated (gate=false, for the cap re-run). Mirror of MemberModel. */
export class MemberModel {
  oracleId: string;
  name: string;
  colorIdentity: string[];
  tierBCapped: Set<string>;
  provides: Item[];
  wants: Item[];
  ambient: Item[];
  triggers: { trigger: string; provenance: string }[];
  guards: string[];
  eventsEmitted: string[];
  untapsOther: boolean;
  activated: (string | null)[];

  constructor(oracleId: string, rec: TBRecord, gate: boolean) {
    this.oracleId = oracleId;
    this.name = rec.n;
    this.colorIdentity = rec.ci ?? [];
    this.tierBCapped = new Set(rec.cap ?? []);

    const gateItems = (items: Item[]) =>
      gate ? items.filter((it) => tierBEligible(it.provenance)) : items;
    this.provides = gateItems(expandItems(rec.pr));
    this.wants = gateItems(expandItems(rec.wa));
    this.ambient = gateItems(expandItems(rec.am));

    const rawTriggers = (rec.tr ?? []).map((t) => ({ trigger: t.t, provenance: t.p }));
    this.triggers = gate ? rawTriggers.filter((t) => tierBEligible(t.provenance)) : rawTriggers;

    const rawGuards = rec.gu ?? [];
    this.guards = (gate ? rawGuards.filter((g) => tierBEligible(g.p)) : rawGuards).map(
      (g) => g.g,
    );

    // events_emitted + untaps_other are read gate-blind from the raw entry.
    this.eventsEmitted = rec.ev ?? [];
    this.untapsOther = rec.uo === true;

    const rawActivated = (rec.co?.ac ?? []).map((c) => ({ cost: c.c, provenance: c.p }));
    this.activated = (gate
      ? rawActivated.filter((c) => tierBEligible(c.provenance))
      : rawActivated
    ).map((c) => c.cost);
  }

  private allItems(): Item[] {
    return [...this.provides, ...this.wants, ...this.ambient];
  }

  hasFeature(fid: string): boolean {
    return this.allItems().some((it) => it.feature === fid);
  }

  featureMagnitude(fid: string): number {
    let best = 0;
    for (const it of this.allItems()) {
      if (it.feature === fid) best = Math.max(best, it.magnitude || 1);
    }
    return best;
  }

  featureEconomy(fid: string): string {
    for (const it of this.allItems()) if (it.feature === fid) return it.economy;
    return '';
  }

  manaProduced(): number {
    return this.featureMagnitude('mana_add');
  }

  /** Generic-mana cost of a self-untap activated ability, or null (N1 / QE-4). */
  untapCost(): number | null {
    if (!this.eventsEmitted.includes('untap')) return null;
    if (this.untapsOther) return null; // target-untap, not a self-untapping rock
    const priced = new Set<number>();
    for (const c of this.activated) {
      if (c === null || c.trim() === '{T}') continue;
      const m = parseMana(c);
      if (m !== null) priced.add(m);
    }
    if (priced.size !== 1) return null; // 0 → none; ≥2 → unattributable (N1 abstain)
    return [...priced][0];
  }
}

// ─── Verdict container ────────────────────────────────────────────────────────────

class Verdict {
  closes = false;
  template = '';
  k: number | null = null;
  loopClass = '';
  finiteZoneBound: TierBFinding['finiteZoneBound'] = null;
  resultTypes: string[] = [];
  accumulators: string[] = [];
  deficit: TierBDeficit[] = [];
  trace: string[] = [];
  prerequisites: TierBPrerequisites = { minInitialMana: 0, ordering: [], guards: [], note: '' };
  provenance: TierBFinding['provenance'] = {
    members: [],
    ontologyVersion: '',
    extractorVersion: '',
    corpusVersion: '',
    gate: '',
  };
  tierCapped: string | null = null;
  novelEligible = false;
}

// ─── Closure templates ────────────────────────────────────────────────────────────

const AMPLIFIER_TRIGGER_RE =
  /tap[^.]*\bfor\b[^.]*\{|would produce[^.]*mana|produces?[^.]*mana[^.]*additional|add(?:s)? an additional/i;

function isManaAmplifier(m: MemberModel): boolean {
  if (m.manaProduced() <= 0) return false;
  for (const t of m.triggers) if (AMPLIFIER_TRIGGER_RE.test(t.trigger || '')) return true;
  for (const it of [...m.provides, ...m.ambient]) {
    if (it.feature === 'mana_add' && AMPLIFIER_TRIGGER_RE.test(it.evidence || '')) return true;
  }
  return false;
}

/** Colorless when every modelled mana source's evidence names {C}; else 'mana'. */
function colorTag(members: MemberModel[]): string {
  const manaItems: Item[] = [];
  for (const m of members) for (const it of m.provides) if (it.feature === 'mana_add') manaItems.push(it);
  if (manaItems.length > 0 && manaItems.every((it) => (it.evidence || '').includes('{C}'))) {
    return 'colorless';
  }
  return 'mana';
}

function etbResultType(fid: string): string {
  return (
    {
      drain: 'infinite_etb_drain',
      token_create: 'infinite_tokens',
      draw: 'infinite_draw',
      counter_add: 'infinite_counters',
      damage: 'infinite_damage',
    } as Record<string, string>
  )[fid] ?? 'infinite_etb_triggers';
}

/** T1 — self-untapping mana rock + a mana amplifier => infinite mana (k=0). */
function templateUntapMana(members: MemberModel[]): Verdict | null {
  const rocks = members.filter((m) => m.manaProduced() > 0 && m.untapCost() !== null);
  if (rocks.length === 0) return null;
  const v = new Verdict();
  v.template = 'untap_mana';
  const rock = rocks.reduce((a, b) => (b.manaProduced() > a.manaProduced() ? b : a));
  const p = rock.manaProduced();
  const u = rock.untapCost() ?? 0;
  let amp = 0;
  for (const m of members) if (m !== rock && isManaAmplifier(m)) amp += m.manaProduced();
  const net = p + amp - u;
  v.trace = [`${rock.name}: {T} → add ${p} mana`];
  for (const m of members) {
    if (m !== rock && m.manaProduced() > 0) v.trace.push(`${m.name}: +${m.manaProduced()} mana amplifier`);
  }
  v.trace.push(`${rock.name}: pay ${u} → untap ${rock.name}`);
  v.trace.push(`net ${signed(net)} mana per cycle`);
  if (net > 0) {
    v.closes = true;
    v.k = 0;
    v.loopClass = 'infinite';
    v.accumulators = ['mana'];
    v.resultTypes = [`infinite_mana:${colorTag(members)}`];
  } else {
    v.closes = false;
    v.deficit = [
      {
        resource: 'mana',
        shortfall: 1 - net,
        note:
          `loop nets ${signed(net)} mana per iteration; needs a mana amplifier ` +
          `or cheaper untap to reach strict gain`,
      },
    ];
  }
  return v;
}

/** T2/T3 — blink a creature with an ETB payoff (k=0 infinite ETB / mana). */
function templateBlinkValue(members: MemberModel[]): Verdict | null {
  const blinkers = members.filter((m) => m.hasFeature('blink'));
  const etbs = members.filter((m) => m.hasFeature('etb_trigger'));
  if (blinkers.length === 0 || etbs.length === 0) return null;
  const v = new Verdict();
  v.template = 'blink_value';
  const blink = blinkers[0];
  let blinkCost: number | null = null;
  for (const c of blink.activated) {
    const m = parseMana(c);
    if (m !== null) blinkCost = blinkCost === null ? m : Math.min(blinkCost, m);
  }
  // ETB that untaps lands for mana (infinite-mana case).
  for (const e of etbs) {
    if (e.hasFeature('untap_permanent')) {
      const lands = e.featureMagnitude('untap_permanent');
      if (blinkCost !== null && lands > blinkCost) {
        v.closes = true;
        v.template = 'blink_untap_mana';
        v.k = 0;
        v.loopClass = 'infinite';
        v.accumulators = ['mana'];
        v.resultTypes = [`infinite_mana:${colorTag(members)}`];
        v.trace = [
          `${blink.name}: pay ${blinkCost} → blink ${e.name}`,
          `${e.name}: ETB → untap ${lands} land(s)`,
          `net ${signed(lands - blinkCost)} mana per cycle`,
        ];
        return v;
      }
    }
  }
  // Value-payoff case: ETB emits a value economy; blink must be free/neutral.
  let payoff: [MemberModel, string] | null = null;
  for (const e of etbs) {
    for (const fid of ['drain', 'token_create', 'draw', 'counter_add', 'damage']) {
      if (e.hasFeature(fid)) {
        payoff = [e, fid];
        break;
      }
    }
    if (payoff) break;
  }
  if (payoff === null) return null;
  const [e, fid] = payoff;
  const eco = e.featureEconomy(fid);
  v.trace = [
    `${blink.name}: ${blinkCost ? `pay ${blinkCost} → ` : ''}blink ${e.name}`,
    `${e.name}: ETB → ${eco || fid}`,
  ];
  if (blinkCost === 0) {
    v.closes = true;
    v.k = 0;
    v.loopClass = 'infinite';
    v.accumulators = [eco || fid];
    v.resultTypes = [etbResultType(fid)];
    v.trace.push('blink is free → infinite ETB triggers');
  } else if (blinkCost === null) {
    v.closes = false;
    v.loopClass = 'engine';
    v.k = 1;
    v.resultTypes = [etbResultType(fid)];
    v.deficit = [
      {
        resource: 'mana',
        shortfall: null,
        note:
          'blink activation cost is not modelled in the KB; cannot prove ' +
          'closure — surfaced as a Tier-C candidate, not verified',
      },
    ];
  } else {
    v.closes = false;
    v.loopClass = 'engine';
    v.k = 1;
    v.resultTypes = [etbResultType(fid)];
    v.deficit = [
      {
        resource: 'mana',
        shortfall: null,
        note:
          'blink activation cost cannot be soundly attributed from the KB; ' +
          'structure surfaced as a value engine, not a verified loop',
      },
    ];
  }
  return v;
}

/** T4 — aristocrats: sac outlet + recurring fodder + death payoff (never closes). */
function templateSacRecursion(members: MemberModel[]): Verdict | null {
  const outlets = members.filter((m) => m.hasFeature('sac_outlet'));
  const fodder = members.filter((m) => m.hasFeature('sac_fodder'));
  if (outlets.length === 0 || fodder.length === 0) return null;
  const v = new Verdict();
  v.template = 'sac_recursion';
  v.closes = false;
  v.loopClass = 'engine';
  v.k = 1;
  v.resultTypes = ['death_trigger_engine'];
  const payoff = members.filter((m) => m.hasFeature('dies_trigger') || m.hasFeature('drain'));
  v.trace = [
    `${outlets[0].name}: sacrifice ${fodder[0].name}`,
    `${fodder[0].name}: recurs (return cost not modelled in the KB)`,
  ];
  if (payoff.length > 0) {
    const eco = payoff.some((m) => m.hasFeature('drain')) ? 'drain' : 'dies';
    v.trace.push(`${payoff[0].name}: death trigger → ${eco}`);
  }
  v.deficit = [
    {
      resource: 'recurrence',
      shortfall: null,
      note:
        'aristocrats value-engine structure; the fodder\'s return cost and the ' +
        'sac outlet\'s cost are not soundly priceable from the KB, so closure ' +
        'is not verified (QE-2 diagnostic)',
    },
  ];
  return v;
}

const TEMPLATES = [templateUntapMana, templateBlinkValue, templateSacRecursion];
const CLOSE_SAFE = new Set(['untap_mana', 'blink_untap_mana']);
const NOVEL_SAFE = CLOSE_SAFE;

function runTemplates(members: MemberModel[]): Verdict | null {
  for (const tmpl of TEMPLATES) {
    const v = tmpl(members);
    if (v !== null) return v;
  }
  return null;
}

/** +d / -d / +0 (Python f"{net:+d}"). */
function signed(n: number): string {
  return n >= 0 ? `+${n}` : `${n}`;
}

// ─── Prerequisites (PR-3) ─────────────────────────────────────────────────────────

/** Lexicographic-by-input-index permutations, matching Python itertools.permutations
 * so best_order (the first ordering achieving the minimal need) is byte-identical. */
function* permutations<T>(arr: T[]): Generator<T[]> {
  if (arr.length <= 1) {
    yield arr.slice();
    return;
  }
  for (let i = 0; i < arr.length; i += 1) {
    const rest = arr.slice(0, i).concat(arr.slice(i + 1));
    for (const p of permutations(rest)) yield [arr[i], ...p];
  }
}

function computePrerequisites(
  members: MemberModel[],
  commanderOids: Set<string>,
): TierBPrerequisites {
  const actions: [number, string][] = [];
  for (const m of members) {
    const p = m.manaProduced();
    if (p) actions.push([p, `${m.name}: add ${p}`]);
    const uc = m.untapCost();
    if (uc) actions.push([-uc, `${m.name}: untap (pay ${uc})`]);
    for (const c of m.activated) {
      const mc = parseMana(c);
      if (mc && mc > 0 && (c ?? '').trim() !== '{T}') {
        if (uc !== null && mc === uc) continue; // avoid double-counting the untap
        actions.push([-mc, `${m.name}: activate (pay ${mc})`]);
      }
    }
  }

  let minStock = 0;
  let bestOrder: string[] = [];
  if (actions.length > 0) {
    let best: number | null = null;
    const universe = actions.slice(0, 6);
    for (const perm of permutations(universe)) {
      let bal = 0;
      let worst = 0;
      for (const [delta] of perm) {
        bal += delta;
        worst = Math.min(worst, bal);
      }
      const need = -worst;
      if (best === null || need < best) {
        best = need;
        bestOrder = perm.map(([, lbl]) => lbl);
      }
    }
    // `|| 0` collapses JS negative zero (‑worst when worst===0) to +0, so the
    // serialized minInitialMana matches Python's int 0 byte-for-byte.
    minStock = (best ?? 0) || 0;
  }

  const guards: string[] = [];
  const seen = new Set<string>();
  for (const m of members) {
    for (const g of m.guards) {
      if (g && !seen.has(g)) {
        seen.add(g);
        guards.push(g);
      }
    }
  }
  if (members.some((m) => commanderOids.has(m.oracleId)) && !seen.has('command_zone')) {
    seen.add('command_zone');
    guards.push('command_zone');
  }
  return {
    minInitialMana: minStock,
    ordering: bestOrder,
    guards: guards.slice().sort(),
    note:
      "Correct under Laço's model; may be incomplete in comprehensive-rules edge cases (PR-5).",
  };
}

// ─── Provenance chain (DB-6) ──────────────────────────────────────────────────────

interface Versions {
  ontologyVersion: string;
  extractorVersion: string;
  corpusVersion: string;
}

function provenanceChain(members: MemberModel[], versions: Versions): TierBFinding['provenance'] {
  // KB versions are uniform across the corpus (asserted at index build), so the
  // dedupe Python performs collapses to the single meta version.
  return {
    members: members.map((m) => ({ name: m.name, oracleId: m.oracleId })),
    ontologyVersion: versions.ontologyVersion,
    extractorVersion: versions.extractorVersion,
    corpusVersion: versions.corpusVersion,
    gate: 'deterministic|human-reviewed only (combo_kb_lib.TIER_B_PROVENANCES)',
  };
}

function deriveFiniteBound(members: MemberModel[]): TierBFinding['finiteZoneBound'] {
  for (const m of members) {
    if (m.hasFeature('self_mill')) {
      const per = m.featureMagnitude('self_mill') || 1;
      return {
        zone: 'library',
        perIteration: per,
        bound: Math.floor(DEFAULT_LIBRARY_SIZE / per),
        note: `self-mills ~${per}/iteration; bounded by a ~${DEFAULT_LIBRARY_SIZE}-card library`,
      };
    }
  }
  return null;
}

// ─── Top-level verification (mirror verify_candidate) ─────────────────────────────

interface Member {
  oracleId: string;
  rec: TBRecord;
}

function verifyCandidate(
  entries: Member[],
  inCurated: boolean,
  commanderOids: Set<string>,
  versions: Versions,
): Verdict | null {
  if (entries.length === 0 || entries.length > MAX_CYCLE_PIECES + 8) return null;
  // Sort members by oracle_id (N4 / DB-5) so presentation is order-stable.
  const sorted = [...entries].sort((a, b) => (a.oracleId < b.oracleId ? -1 : a.oracleId > b.oracleId ? 1 : 0));
  const members = sorted.map((e) => new MemberModel(e.oracleId, e.rec, true));

  let verdict = runTemplates(members);

  // Provenance-gate capping (plan 6b). If the gated analysis does not verify but the
  // same structure WOULD close using dropped llm/community items, cap at Tier C.
  const cappedFields = [...new Set(members.flatMap((m) => [...m.tierBCapped]))].sort();
  if (cappedFields.length > 0 && (verdict === null || !verdict.closes)) {
    const ungated = sorted.map((e) => new MemberModel(e.oracleId, e.rec, false));
    const uv = runTemplates(ungated);
    if (uv !== null && uv.closes) {
      uv.closes = false;
      uv.tierCapped =
        'capped at Tier C: loop-relevant field(s) ' +
        cappedFields.join(', ') +
        ' came from LLM/community classification, not deterministic or ' +
        'human-reviewed extraction (plan decision 6b provenance gate); ' +
        'would verify once a human reviews the entry (KB-7)';
      verdict = uv;
    }
  }

  if (verdict === null) return null;

  // SOUNDNESS BACKSTOP (QE-4). Only CLOSE_SAFE templates may assert a closed loop;
  // downgrade any other "closes" to a k>0 value engine.
  if (verdict.closes && !CLOSE_SAFE.has(verdict.template)) {
    verdict.closes = false;
    verdict.loopClass = 'engine';
    if (verdict.k === null || verdict.k === 0) verdict.k = 1;
    if (verdict.deficit.length === 0) {
      verdict.deficit = [
        {
          resource: 'recurrence',
          shortfall: null,
          note:
            'structure present but closure is not soundly derivable from ' +
            'the coarse KB features; surfaced as a value engine, not a ' +
            'verified loop',
        },
      ];
    }
  }

  verdict.prerequisites = computePrerequisites(members, commanderOids);
  verdict.provenance = provenanceChain(members, versions);

  if ((verdict.loopClass === 'infinite' || verdict.loopClass === 'engine') && verdict.finiteZoneBound === null) {
    verdict.finiteZoneBound = deriveFiniteBound(members);
  }

  verdict.novelEligible =
    verdict.closes &&
    !inCurated &&
    verdict.tierCapped === null &&
    verdict.loopClass === 'infinite' &&
    verdict.accumulators.length > 0 &&
    verdict.deficit.length === 0 &&
    NOVEL_SAFE.has(verdict.template);
  return verdict;
}

// ─── Candidate enumeration (mirror enumerate_verification_candidates) ─────────────

const ENUM_BUDGET = 4000;

function enumerateVerificationCandidates(deck: Member[], budget = ENUM_BUDGET): Member[][] {
  const ent = [...deck].sort((a, b) => (a.oracleId < b.oracleId ? -1 : a.oracleId > b.oracleId ? 1 : 0));
  const models = ent.map((e) => ({ e, m: new MemberModel(e.oracleId, e.rec, true) }));
  const gated = (pred: (m: MemberModel) => boolean) => models.filter(({ m }) => pred(m)).map(({ e }) => e);

  const untappers = gated((m) => m.manaProduced() > 0 && m.untapCost() !== null);
  const amplifiers = gated((m) => isManaAmplifier(m));
  const blinkers = gated((m) => m.hasFeature('blink'));
  const etbs = gated((m) => m.hasFeature('etb_trigger'));
  const outlets = gated((m) => m.hasFeature('sac_outlet'));
  const fodders = gated((m) => m.hasFeature('sac_fodder'));
  const payoffs = gated((m) => m.hasFeature('dies_trigger') || m.hasFeature('drain'));

  const seen = new Set<string>();
  const out: Member[][] = [];
  const key = (group: Member[]) =>
    [...new Set(group.map((g) => g.oracleId))].sort().join('|');
  const add = (group: Member[]): boolean => {
    const k = key(group);
    if (k.length < 1 || seen.has(k)) return true;
    seen.add(k);
    out.push(group);
    return out.length < budget;
  };

  // untap-mana: rock × amplifier pairs; rock singleton when no amplifier present.
  for (const r of untappers) {
    const amps = amplifiers.filter((a) => a !== r);
    if (amps.length === 0) add([r]);
    for (const a of amps) if (!add([r, a])) return out;
  }
  // blink + ETB (+ payoff / untapper as third)
  for (const b of blinkers) {
    for (const e of etbs) {
      if (e === b) continue;
      if (!add([b, e])) return out;
      for (const p of [...payoffs, ...untappers]) {
        if (p === b || p === e) continue;
        if (!add([b, e, p])) return out;
      }
    }
  }
  // sac outlet + fodder (+ death payoff)
  for (const o of outlets) {
    for (const f of fodders) {
      if (f === o) continue;
      if (!add([o, f])) return out;
      for (const p of payoffs) {
        if (p === o || p === f) continue;
        if (!add([o, f, p])) return out;
      }
    }
  }
  return out;
}

// ─── Deck driver (mirror build_tier_b_candidates.build_deck, paste mode) ──────────

export interface TierBVerifyResult {
  counts: TierBCounts;
  corroborated: TierBFinding[];
  novel: TierBFinding[];
  engines: TierBFinding[];
  capped: TierBFinding[];
  /** DC-5 enumeration budget hit (disclosed, never silent). */
  enumBudgetHit: boolean;
  /** True once the verifier ran (index loaded); false ⇒ index unavailable. */
  available: boolean;
}

const EMPTY_RESULT: TierBVerifyResult = {
  counts: {
    verifiedCorroborated: 0,
    verifiedNovel: 0,
    engines: 0,
    capped: 0,
    candidatesConsidered: 0,
    curatedPresent: 0,
    kbGapAbstentions: 0,
  },
  corroborated: [],
  novel: [],
  engines: [],
  capped: [],
  enumBudgetHit: false,
  available: false,
};

function render(v: Verdict, inCurated: boolean): TierBFinding {
  const band = v.closes ? 'verified' : v.loopClass === 'engine' ? 'engine' : 'candidate';
  return {
    cards: v.provenance.members.map((m) => m.name).slice().sort(),
    closes: v.closes,
    template: v.template,
    loopClass: v.loopClass,
    k: v.k,
    band,
    resultTypes: v.resultTypes,
    finiteZoneBound: v.finiteZoneBound,
    trace: v.trace,
    deficit: v.deficit,
    prerequisites: v.prerequisites,
    provenance: v.provenance,
    tierCapped: v.tierCapped,
    corroboration: inCurated,
  };
}

function cmpCards(a: string[], b: string[]): number {
  const n = Math.min(a.length, b.length);
  for (let i = 0; i < n; i += 1) {
    if (a[i] < b[i]) return -1;
    if (a[i] > b[i]) return 1;
  }
  return a.length - b.length;
}

export interface VerifyDeckOptions {
  /** Card-name sets of curated combos present in the deck (Tier-A included[]),
   * used to mark corroboration (DB-7). */
  curatedCardSets?: string[][];
  /** Commander name(s) for the IN-4 command-zone guard. */
  commanderNames?: string[];
}

/** Verify a pasted decklist for Tier-B loops. Mirror of build_deck (paste mode: no
 * EDHREC crowd prior, no ranking scalar shipped). Resolves names against the
 * committed tier-b-index; enumerates + curated groups; verifies; suppresses
 * non-minimal supersets; buckets by presentation tier. */
export function verifyDeck(
  names: string[],
  index: TierBIndex | null,
  opts: VerifyDeckOptions = {},
): TierBVerifyResult {
  if (!index) return { ...EMPTY_RESULT };
  const versions: Versions = {
    ontologyVersion: index.meta.ontologyVersion,
    extractorVersion: index.meta.extractorVersion,
    corpusVersion: index.meta.corpusVersion,
  };
  const resolveOid = (raw: string): string | undefined => {
    for (const k of nameKeys(raw)) {
      const hit = index.names[k];
      if (hit !== undefined) return hit;
    }
    return undefined;
  };
  // Resolve decklist → records (deduped by oracle_id). Every index record is a full
  // loop-relevant projection (seeds + bystanders); the enumerator gates seeds by
  // feature, so a bystander never forms a fresh group but does resolve inside a
  // curated group — matching build_deck's KB-wide by_oid.
  const byOid = new Map<string, Member>();
  for (const raw of names) {
    const oid = resolveOid(raw);
    if (oid === undefined || byOid.has(oid) || !index.cards[oid]) continue;
    byOid.set(oid, { oracleId: oid, rec: index.cards[oid] });
  }
  const deckEntries = [...byOid.values()];

  // Commander oids (IN-4 command-zone guard).
  const commanderOids = new Set<string>();
  for (const cname of opts.commanderNames ?? []) {
    for (const face of String(cname).split('//')) {
      const oid = resolveOid(face.trim());
      if (oid !== undefined) commanderOids.add(oid);
    }
  }

  // Curated keys: a curated combo present in the deck whose members ALL resolve to
  // member records (an unresolved member can't be verified — skip, conservative).
  const curated = new Set<string>();
  for (const cardSet of opts.curatedCardSets ?? []) {
    const oids: string[] = [];
    let ok = true;
    for (const card of cardSet) {
      const oid = resolveOid(card);
      if (oid === undefined || !byOid.has(oid)) {
        ok = false;
        break;
      }
      oids.push(oid);
    }
    if (ok && oids.length >= 2 && oids.length <= MAX_CYCLE_PIECES + 8) {
      curated.add([...new Set(oids)].sort().join('|'));
    }
  }

  // Candidate groups: curated member sets first, then feature-gated enumeration.
  const groups: Member[][] = [];
  const seen = new Set<string>();
  for (const ck of curated) {
    const grp = ck.split('|').map((o) => byOid.get(o)).filter((x): x is Member => x !== undefined);
    if (grp.length === ck.split('|').length) {
      groups.push(grp);
      seen.add(ck);
    }
  }
  const enumGroups = enumerateVerificationCandidates(deckEntries);
  const enumBudgetHit = enumGroups.length >= ENUM_BUDGET;
  for (const grp of enumGroups) {
    const k = [...new Set(grp.map((g) => g.oracleId))].sort().join('|');
    if (!seen.has(k)) {
      seen.add(k);
      groups.push(grp);
    }
  }

  interface Rec {
    v: Verdict;
    finding: TierBFinding;
    key: string;
    keySet: Set<string>;
  }
  const verdicts: Rec[] = [];
  let kbGapAbstentions = 0;
  for (const grp of groups) {
    const keySet = new Set(grp.map((g) => g.oracleId));
    const key = [...keySet].sort().join('|');
    const v = verifyCandidate(grp, curated.has(key), commanderOids, versions);
    if (v === null) continue;
    verdicts.push({ v, finding: render(v, curated.has(key)), key, keySet });
  }

  // Superset suppression: drop a closing loop that strictly contains a smaller one.
  const closingKeys = verdicts
    .filter((r) => r.v.closes)
    .map((r) => r.keySet)
    .sort((a, b) => a.size - b.size);
  const minimal: Set<string>[] = [];
  const isStrictSubset = (a: Set<string>, b: Set<string>) =>
    a.size < b.size && [...a].every((x) => b.has(x));
  for (const k of closingKeys) {
    if (!minimal.some((m) => isStrictSubset(m, k))) minimal.push(k);
  }
  const minimalSet = new Set(minimal.map((s) => [...s].sort().join('|')));

  const buckets: Record<'verifiedCorroborated' | 'verifiedNovel' | 'engines' | 'capped', TierBFinding[]> = {
    verifiedCorroborated: [],
    verifiedNovel: [],
    engines: [],
    capped: [],
  };
  for (const r of verdicts) {
    if (r.v.tierCapped) {
      buckets.capped.push(r.finding);
    } else if (r.v.closes) {
      if (!minimalSet.has(r.key)) continue; // non-minimal superset
      if (curated.has(r.key)) buckets.verifiedCorroborated.push(r.finding);
      else if (r.v.novelEligible) buckets.verifiedNovel.push(r.finding);
      else buckets.engines.push(r.finding);
    } else {
      const concrete = r.v.deficit.some((d) => d.shortfall !== null);
      if (concrete || (r.v.loopClass === 'engine' && r.v.closes)) buckets.engines.push(r.finding);
      else kbGapAbstentions += 1;
    }
  }

  // Order by cards only (paste mode ships no rank scalar; ordering is display-only).
  for (const b of Object.values(buckets)) b.sort((a, c) => cmpCards(a.cards, c.cards));

  return {
    counts: {
      verifiedCorroborated: buckets.verifiedCorroborated.length,
      verifiedNovel: buckets.verifiedNovel.length,
      engines: buckets.engines.length,
      capped: buckets.capped.length,
      candidatesConsidered: groups.length,
      curatedPresent: curated.size,
      kbGapAbstentions,
    },
    corroborated: buckets.verifiedCorroborated,
    novel: buckets.verifiedNovel,
    engines: buckets.engines,
    capped: buckets.capped,
    enumBudgetHit,
    available: true,
  };
}
