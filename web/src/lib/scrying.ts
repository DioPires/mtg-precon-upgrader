// Pure functions for the Scrying Pool: shuffle, London-mulligan math, swap delta.
// No React, no DOM, no card cache — these are testable in isolation.

import type { CardEntry } from '../data/cardCache';
import type { RawDecklistCard } from '../data/types';

// ─── London mulligan helpers ─────────────────────────────────────────
// First mulligan is free; subsequent mulligans require putting (mulliganCount - 1)
// cards on bottom. Matches the legacy hand simulator behavior.

export function bottomCountFor(mulligans: number): number {
  return Math.max(0, mulligans - 1);
}

export function keptHandSize(mulligans: number): number {
  return Math.max(0, 7 - bottomCountFor(mulligans));
}

// ─── Shuffle (Fisher–Yates) ──────────────────────────────────────────
// Accepts an injected RNG so tests can pin the order without monkey-patching Math.random.

export type RngFn = () => number;

export function shuffleArr<T>(arr: readonly T[], rng: RngFn = Math.random): T[] {
  const a = arr.slice();
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

// ─── Color/type helpers ──────────────────────────────────────────────

export function colorsFromManaCost(manaCost: string | undefined | null): string[] {
  if (!manaCost) return [];
  const out = new Set<string>();
  manaCost.replace(/\{([^}]+)\}/g, (_, sym: string) => {
    sym.split('/').forEach((s) => {
      const u = s.toUpperCase();
      if (['W', 'U', 'B', 'R', 'G'].includes(u)) out.add(u);
    });
    return '';
  });
  return [...out];
}

export function fmtManaCost(manaCost: string | undefined | null): string {
  if (!manaCost) return '';
  const parts: string[] = [];
  manaCost.replace(/\{([^}]+)\}/g, (_, sym: string) => {
    parts.push(sym.toUpperCase());
    return '';
  });
  return parts.join(' · ');
}

export type DerivedType =
  | 'Land'
  | 'Creature'
  | 'Planeswalker'
  | 'Artifact'
  | 'Enchantment'
  | 'Instant'
  | 'Sorcery'
  | 'Other';

export function deriveType(typeLine: string | undefined, fallback: string | undefined): DerivedType {
  const tl = (typeLine || fallback || '').toLowerCase();
  if (tl.includes('land')) return 'Land';
  if (tl.includes('creature')) return 'Creature';
  if (tl.includes('planeswalker')) return 'Planeswalker';
  if (tl.includes('artifact')) return 'Artifact';
  if (tl.includes('enchantment')) return 'Enchantment';
  if (tl.includes('instant')) return 'Instant';
  if (tl.includes('sorcery')) return 'Sorcery';
  return (fallback as DerivedType) || 'Other';
}

// ─── Swap delta computation ──────────────────────────────────────────
// Captures all 7 categories the brief calls out:
//   1. CMC change (single card)
//   2. Avg CMC of non-land deck
//   3. Land count
//   4. Color pip balance
//   5. Type change
//   6. Game Changers count
//   7. Synergies broken / synergies enabled

export interface SwapDelta {
  cutCmc: number | null;
  addCmc: number | null;
  cmcChange: number | null;

  colorDelta: Record<string, number>;

  cutType: DerivedType;
  addType: DerivedType;
  typeChanged: boolean;

  avgCmcBefore: number;
  avgCmcAfter: number;
  avgCmcChange: number | null;

  landsBefore: number;
  landsAfter: number;

  synergiesBroken: SynergyLike[];
  synergiesKept: SynergyLike[];

  gcKind: 'adding' | 'removing' | 'swap' | null;
  gcDetail: string | null;
  gameChangers: number;

  cutManaCost: string;
  addManaCost: string;
}

export interface SynergyLike {
  title: string;
  cards: string[];
  description: string;
}

export interface SwapInput {
  cutCard: { name: string; type?: string };
  addCard: { name: string; type?: string };
  cutMeta: Partial<CardEntry> | null;
  addMeta: Partial<CardEntry> | null;
  decklist: RawDecklistCard[];
  /** Cache lookup for decklist-wide aggregates; usually `cardCache.get`. */
  metaFor: (name: string) => Partial<CardEntry> | null;
  synergies: SynergyLike[];
  /** Predicate; usually `isGameChanger`. */
  isGameChanger: (name: string) => boolean;
  /** Current GC count from the deck (for `gcDetail` strings). */
  gameChangers: number;
}

export function computeSwapDelta(input: SwapInput): SwapDelta {
  const { cutCard, addCard, cutMeta, addMeta, decklist, metaFor, synergies, isGameChanger, gameChangers } = input;
  const cutCmc = cutMeta?.cmc ?? null;
  const addCmc = addMeta?.cmc ?? null;
  const cmcChange = cutCmc != null && addCmc != null ? addCmc - cutCmc : null;

  const cutColors = colorsFromManaCost(cutMeta?.mana_cost);
  const addColors = colorsFromManaCost(addMeta?.mana_cost);
  const colorDelta: Record<string, number> = {};
  cutColors.forEach((c) => (colorDelta[c] = (colorDelta[c] || 0) - 1));
  addColors.forEach((c) => (colorDelta[c] = (colorDelta[c] || 0) + 1));
  Object.keys(colorDelta).forEach((k) => {
    if (colorDelta[k] === 0) delete colorDelta[k];
  });

  const cutType = deriveType(cutMeta?.type_line, cutCard.type);
  const addType = deriveType(addMeta?.type_line, addCard.type);

  let totalCmc = 0;
  let nonLandCount = 0;
  let landCount = 0;
  decklist.forEach((c) => {
    const m = metaFor(c.name);
    const tl = (m?.type_line || c.type || '').toLowerCase();
    const cmc = m?.cmc ?? null;
    if (tl.includes('land')) {
      landCount++;
    } else if (cmc != null) {
      totalCmc += cmc;
      nonLandCount++;
    }
  });
  const oldAvg = nonLandCount > 0 ? totalCmc / nonLandCount : 0;
  const cutIsLand = cutType === 'Land';
  const addIsLand = addType === 'Land';
  let newTotal = totalCmc;
  let newCount = nonLandCount;
  if (!cutIsLand && cutCmc != null) {
    newTotal -= cutCmc;
    newCount -= 1;
  }
  if (!addIsLand && addCmc != null) {
    newTotal += addCmc;
    newCount += 1;
  }
  const newAvg = newCount > 0 ? newTotal / newCount : 0;
  const avgCmcChange = nonLandCount > 0 || newCount > 0 ? newAvg - oldAvg : null;

  const landsBefore = landCount;
  const landsAfter = landCount + (addIsLand ? 1 : 0) - (cutIsLand ? 1 : 0);

  const cutLower = cutCard.name.toLowerCase();
  const addLower = addCard.name.toLowerCase();
  const synergiesBroken = synergies.filter((s) =>
    (s.cards || []).some((c) => c.toLowerCase() === cutLower),
  );
  const synergiesKept = synergies.filter((s) =>
    (s.cards || []).some((c) => c.toLowerCase() === addLower),
  );

  const cutIsGC = isGameChanger(cutCard.name);
  const addIsGC = isGameChanger(addCard.name);
  let gcKind: SwapDelta['gcKind'] = null;
  let gcDetail: string | null = null;
  if (cutIsGC && addIsGC) {
    gcKind = 'swap';
    gcDetail = 'GC for GC — count unchanged';
  } else if (addIsGC) {
    gcKind = 'adding';
    gcDetail = `+1 GC · ${gameChangers} → ${gameChangers + 1}`;
  } else if (cutIsGC) {
    gcKind = 'removing';
    gcDetail = `−1 GC · ${gameChangers} → ${gameChangers - 1}`;
  }

  return {
    cutCmc,
    addCmc,
    cmcChange,
    colorDelta,
    cutType,
    addType,
    typeChanged: cutType !== addType,
    avgCmcBefore: oldAvg,
    avgCmcAfter: newAvg,
    avgCmcChange,
    landsBefore,
    landsAfter,
    synergiesBroken,
    synergiesKept,
    gcKind,
    gcDetail,
    gameChangers,
    cutManaCost: cutMeta?.mana_cost || '',
    addManaCost: addMeta?.mana_cost || '',
  };
}

// ─── Hand assessment (lands count) ───────────────────────────────────
// Used by the histogram to highlight which column the current hand falls in,
// even when not all card metas have loaded.

export function countLandsInHand(
  hand: { name: string; type?: string }[],
  metaFor: (name: string) => Partial<CardEntry> | null,
): number {
  let lands = 0;
  for (const c of hand) {
    const m = metaFor(c.name);
    const tl = (m?.type_line || c.type || '').toLowerCase();
    if (tl.includes('land')) lands++;
  }
  return lands;
}
