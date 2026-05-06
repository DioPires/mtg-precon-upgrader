// Port of design_handoff_grimoire/prototype/gv1-data.js (transformDeck) into TS.
//
// Differences vs. the prototype:
//   - Strict types (see ./types.ts).
//   - Role taxonomy aligned to the canonical 15-role set in docs/role-taxonomy.md
//     (raw deck.json uses `primary_role`, e.g. `land`, `card-draw`, `removal-spot`).
//   - No `recs` field — `recommendations.json` was retired in DEC-150 reconciliation.
//   - Pure functions; no window globals.

import type {
  DeckApothecary,
  DeckCardTile,
  DeckCombo,
  DeckCurveEntry,
  DeckEngineSection,
  DeckFuncEntry,
  DeckFull,
  DeckListGroup,
  DeckStub,
  DeckWincon,
  RawCategory,
  RawDeck,
  RawDeckBundle,
  RawDecklistCard,
  RawHighlight,
  RawSynergy,
  RawWinCondition,
  SplitTitle,
} from './types';

const COLOR_TO_GLYPH: Record<string, string> = {
  W: '⚪',
  U: '🔵',
  B: '⚫',
  R: '🔴',
  G: '🟢',
  C: '◇',
};

const ROMAN: Record<string, string> = {
  '1': 'I',
  '2': 'II',
  '3': 'III',
  '4': 'IV',
  '5': 'V',
};

const ROLE_LABEL: Record<string, string> = {
  land: 'Lands',
  ramp: 'Ramp',
  'card-draw': 'Card Draw',
  counterspell: 'Counters',
  'removal-spot': 'Spot Removal',
  'removal-board': 'Board Wipes',
  recursion: 'Recursion',
  protection: 'Protection',
  payoff: 'Payoffs',
  threat: 'Threats',
  wincon: 'Win-Cons',
  engine: 'Engine',
  tutor: 'Tutors',
  utility: 'Utility',
  other: 'Other',
};

const SRC_LABEL: Record<string, string> = {
  edhrec: 'EDHREC',
  youtube: 'YouTube',
  article: 'Article',
  draftsim: 'Draftsim',
  commanderspellbook: 'Spellbook',
  'ai-inferred': 'Analysis',
  scryfall: 'Scryfall',
  reddit: 'Reddit',
  other: 'Source',
};

export function colorsToGlyphs(arr: string[] | undefined): string {
  return (arr || []).map((c) => COLOR_TO_GLYPH[c] || '◇').join('');
}

export function toRoman(n: string | number | undefined): string {
  return ROMAN[String(n)] || String(n ?? '');
}

/**
 * Split a heading like "Infinite Mana into Eldrazi Army" into a [head, tail] pair.
 * The tail is rendered emphasized (`<em>`) by the wincon/combo card; the trailing space
 * on the head is intentional so the tail wraps without manual whitespace fix-ups.
 */
export function splitTitle(t: string | undefined): SplitTitle {
  if (!t) return ['', ''];
  const words = t.split(/\s+/);
  if (words.length <= 1) return [t, ''];
  const mid = Math.ceil(words.length / 2);
  return [words.slice(0, mid).join(' ') + ' ', words.slice(mid).join(' ')];
}

interface DeckCtx {
  decklistByName: Map<string, RawDecklistCard>;
  highlightsByName: Map<string, RawHighlight>;
}

function buildCtx(deck: RawDeck): DeckCtx {
  const decklistByName = new Map<string, RawDecklistCard>();
  (deck.decklist || []).forEach((c) => {
    if (c?.name) decklistByName.set(c.name.toLowerCase(), c);
  });
  const highlightsByName = new Map<string, RawHighlight>();
  (deck.highlights || []).forEach((h) => {
    if (h?.name) highlightsByName.set(h.name.toLowerCase(), h);
  });
  return { decklistByName, highlightsByName };
}

function mvFromRow(row: RawDecklistCard | undefined): string {
  if (!row) return '—';
  if (row.type === 'Land' || row.primary_role === 'land') return 'LAND';
  return '—';
}

function tileFor(name: string, ctx: DeckCtx): DeckCardTile {
  if (!name) return { n: '—', mv: '—', price: '—', type: '—', gc: false };
  const dl = ctx.decklistByName.get(name.toLowerCase());
  const hl = ctx.highlightsByName.get(name.toLowerCase());
  return {
    n: name,
    mv: mvFromRow(dl),
    price: hl?.price || '—',
    type: dl?.type || '—',
    gc: !!hl?.isGameChanger,
    note: hl?.reason,
  };
}

function transformWincons(deck: RawDeck, ctx: DeckCtx): DeckWincon[] {
  return (deck.winConditions || []).map((w: RawWinCondition) => ({
    title: splitTitle(w.title),
    prob: '',
    desc: w.description,
    cards: (w.cards || []).slice(0, 3).map((n) => tileFor(n, ctx)),
  }));
}

function transformEngine(deck: RawDeck, ctx: DeckCtx): DeckEngineSection[] {
  return (deck.categories || [])
    .map((cat: RawCategory): DeckEngineSection => ({
      title: cat.name,
      count: (cat.cards || []).length,
      cards: (cat.cards || []).map((n) => tileFor(n, ctx)),
      isGameChangers: !!cat.isHighlighted,
    }))
    .filter((s) => s.count > 0);
}

function transformCombos(deck: RawDeck, ctx: DeckCtx): DeckCombo[] {
  return (deck.synergies || []).map((s: RawSynergy) => {
    const srcs = s.sources || [];
    const preferred =
      srcs.find((x) => x.type === 'commanderspellbook') ||
      srcs.find((x) => x.type === 'edhrec') ||
      srcs[0];
    const srcLabel = preferred
      ? `${SRC_LABEL[preferred.type] || preferred.type} · ${preferred.name || preferred.detail || ''}`
          .trim()
          .replace(/\s*·\s*$/, '')
      : '';
    return {
      title: splitTitle(s.title),
      desc: s.description,
      cards: (s.cards || []).slice(0, 3).map((n) => tileFor(n, ctx)),
      src: srcLabel,
      tag: `${(s.cards || []).length}-CARD`,
    };
  });
}

function transformApothecary(bundle: RawDeckBundle): DeckApothecary | null {
  const { metrics, candidates } = bundle;
  if (!metrics || !candidates) return null;
  return {
    diagnosis: {
      score: metrics.global_health,
      methodology: metrics.methodology || 'deck-metrics-v1',
      generatedAt: metrics.generated_at,
      mirrorUpdatedAt: candidates.scryfall_mirror_updated_at,
      components: metrics.metrics || {},
    },
    maladies: metrics.gaps || [],
    remedies: candidates.candidates || [],
  };
}

function transformCurveAndFunc(deck: RawDeck): { curve: DeckCurveEntry[]; func: DeckFuncEntry[] } {
  const roleCounts: Record<string, number> = {};
  (deck.decklist || []).forEach((c) => {
    const role = c.primary_role || 'other';
    roleCounts[role] = (roleCounts[role] || 0) + (c.quantity ?? 1);
  });
  const entries = Object.entries(roleCounts).sort((a, b) => b[1] - a[1]);
  const maxRole = Math.max(1, ...entries.map(([, n]) => n));
  const curve: DeckCurveEntry[] = entries.slice(0, 8).map(([role, n]) => ({
    cmc: ROLE_LABEL[role] || role,
    n,
    peak: n === maxRole,
  }));
  const func: DeckFuncEntry[] = entries.map(([role, n]) => ({
    l: ROLE_LABEL[role] || role,
    n,
    pct: Math.round((n / maxRole) * 100),
  }));
  return { curve, func };
}

function transformList(deck: RawDeck, ctx: DeckCtx): DeckListGroup[] {
  const byRole = new Map<string, RawDecklistCard[]>();
  (deck.decklist || []).forEach((c) => {
    const role = c.primary_role || 'other';
    const arr = byRole.get(role) ?? [];
    arr.push(c);
    byRole.set(role, arr);
  });
  const commanderTile: DeckCardTile = {
    n: deck.commander,
    gc: (deck.gameChangers || 0) > 0,
    mv: '—',
    price: '—',
    type: 'Commander',
  };
  const groups: DeckListGroup[] = [{ name: 'Commander', cards: [commanderTile] }];
  const qtySum = (cs: RawDecklistCard[]) => cs.reduce((n, c) => n + (c.quantity ?? 1), 0);
  const sortedRoles = [...byRole.entries()].sort((a, b) => {
    if (a[0] === 'land') return 1;
    if (b[0] === 'land') return -1;
    return qtySum(b[1]) - qtySum(a[1]);
  });
  for (const [role, cards] of sortedRoles) {
    groups.push({
      name: `${ROLE_LABEL[role] || role} (${qtySum(cards)})`,
      cards: cards.map((c) => {
        const hl = ctx.highlightsByName.get(c.name.toLowerCase());
        const qty = c.quantity ?? 1;
        return {
          n: c.name,
          mv: c.primary_role === 'land' ? 'LAND' : '—',
          price: hl?.price || '—',
          type: c.type,
          gc: !!hl?.isGameChanger,
          note: hl?.reason,
          ...(qty > 1 ? { qty } : {}),
        };
      }),
    });
  }
  return groups;
}

/** Normalize one raw deck bundle into the UI-facing DeckFull shape. */
export function normalizeDeck(bundle: RawDeckBundle, idx: number): DeckFull {
  const { id, index: idxEntry, deck, sim } = bundle;
  const ctx = buildCtx(deck);
  const { curve, func } = transformCurveAndFunc(deck);

  const sources: Array<readonly [string, string]> = (deck.sources || []).map((s) =>
    [SRC_LABEL[s.type] || s.type || 'Source', s.name || s.detail || ''] as const,
  );

  const winRate = sim?.deckHealthScore?.score
    ? Math.round(sim.deckHealthScore.score)
    : null;
  const strategy = deck.guideContent?.strategyOverview || '';
  const flavor = strategy ? strategy.split(/(?<=[.!?])\s+/)[0] : '';

  return {
    idx,
    slug: id,
    deckName: deck.name,
    commander: deck.commander,
    partner: deck.partner || undefined,
    commanderMv: '—',
    type: `Commander · ${idxEntry.theme}`,
    colors: colorsToGlyphs(idxEntry.colors),
    bracket: toRoman(deck.bracket),
    pt: '—',
    price: deck.cost || '—',
    winTurn: '—',
    winRate,
    flavor,
    oracle: [
      `Theme · ${idxEntry.theme}`,
      `Last verified · ${idxEntry.lastUpdatedSet ?? '—'}`,
    ],
    strategy,
    wincons: transformWincons(deck, ctx),
    engine: transformEngine(deck, ctx),
    combos: transformCombos(deck, ctx),
    apothecary: transformApothecary(bundle),
    curve,
    func,
    sources,
    list: transformList(deck, ctx),
    health: sim?.deckHealthScore || null,
    assessment: sim?.assessment || null,
    composition: sim?.deckComposition || null,
    sim: sim || null,
    rawDecklist: deck.decklist || [],
    synergies: (deck.synergies || []).map((s) => ({
      title: s.title || '',
      cards: s.cards || [],
      description: s.description || '',
    })),
    gameChangers: deck.gameChangers || 0,
  };
}

/** Normalize an array of raw bundles. Filters out bundles missing a `deck`. */
export function normalizeDecks(bundles: RawDeckBundle[]): DeckFull[] {
  return bundles
    .filter((b): b is RawDeckBundle => !!b && !!b.deck)
    .map((b, i) => normalizeDeck(b, i + 1));
}

/** Build the lightweight selector list from normalized decks. */
export function buildDeckStubs(decks: DeckFull[]): DeckStub[] {
  return decks.map((d) => ({
    idx: d.idx,
    slug: d.slug,
    name: d.deckName,
    cmd: d.commander,
    colors: d.colors,
    bracket: d.bracket,
    price: d.price,
    hasDetail: true,
  }));
}
