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
  DeckToken,
  DeckWincon,
  RawCardMetadata,
  RawCardMetadataEntry,
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
  metadataByName: Map<string, RawCardMetadataEntry>;
}

function buildCtx(deck: RawDeck, cardMetadata?: RawCardMetadata): DeckCtx {
  const decklistByName = new Map<string, RawDecklistCard>();
  (deck.decklist || []).forEach((c) => {
    if (c?.name) decklistByName.set(c.name.toLowerCase(), c);
  });
  const highlightsByName = new Map<string, RawHighlight>();
  (deck.highlights || []).forEach((h) => {
    if (h?.name) highlightsByName.set(h.name.toLowerCase(), h);
  });
  const metadataByName = new Map<string, RawCardMetadataEntry>();
  Object.entries(cardMetadata || {}).forEach(([name, meta]) => {
    metadataByName.set(name.toLowerCase(), meta);
  });
  return { decklistByName, highlightsByName, metadataByName };
}

/**
 * Flatten a decklist to one entry per physical copy. Basics like
 * `{name:'Plains',quantity:7}` become 7 entries so the shuffle pool reflects
 * actual deck composition. Strips `quantity` from emitted entries.
 */
function expandToCopies(decklist: RawDecklistCard[]): RawDecklistCard[] {
  const out: RawDecklistCard[] = [];
  for (const c of decklist) {
    const qty = Math.max(1, c.quantity ?? 1);
    const { quantity: _q, ...rest } = c;
    for (let i = 0; i < qty; i++) out.push({ ...rest });
  }
  return out;
}

function metaForName(name: string, ctx: DeckCtx): RawCardMetadataEntry | undefined {
  return ctx.metadataByName.get(name.toLowerCase());
}

function isLandTypeLine(typeLine: string | undefined): boolean {
  return /^(Basic |Legendary |Snow )*Land\b/.test(typeLine || '');
}

function mvFromRow(row: RawDecklistCard | undefined, meta?: RawCardMetadataEntry): string {
  if (!row) {
    if (isLandTypeLine(meta?.type_line)) return 'LAND';
    return meta?.mana_cost || '—';
  }
  if (row.type === 'Land' || row.primary_role === 'land' || isLandTypeLine(meta?.type_line)) return 'LAND';
  if (meta?.mana_cost) return meta.mana_cost;
  return '—';
}

function tileFor(name: string, ctx: DeckCtx): DeckCardTile {
  if (!name) return { n: '—', mv: '—', price: '—', type: '—', gc: false };
  const dl = ctx.decklistByName.get(name.toLowerCase());
  const hl = ctx.highlightsByName.get(name.toLowerCase());
  const meta = metaForName(name, ctx);
  const tile: DeckCardTile = {
    n: name,
    mv: mvFromRow(dl, meta),
    price: hl?.price || '—',
    type: dl?.type || meta?.type_line || '—',
    gc: !!hl?.isGameChanger,
    note: hl?.reason,
  };
  if (typeof meta?.cmc === 'number') tile.cmc = meta.cmc;
  return tile;
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

function transformTokens(deck: RawDeck): DeckToken[] {
  const raw = Array.isArray(deck.tokens) ? deck.tokens : [];
  return raw
    .filter((t): t is DeckToken => !!t && typeof (t as DeckToken).name === 'string' && (t as DeckToken).name.length > 0)
    .map((t) => ({ ...t, produced_by: Array.isArray(t.produced_by) ? t.produced_by : [] }));
}

function transformList(deck: RawDeck, ctx: DeckCtx): DeckListGroup[] {
  const byRole = new Map<string, RawDecklistCard[]>();
  (deck.decklist || []).forEach((c) => {
    const role = c.primary_role || 'other';
    const arr = byRole.get(role) ?? [];
    arr.push(c);
    byRole.set(role, arr);
  });
  const commanderMeta = metaForName(deck.commander, ctx);
  const commanderTile: DeckCardTile = {
    n: deck.commander,
    gc: (deck.gameChangers || 0) > 0,
    mv: commanderMeta?.mana_cost || '—',
    price: '—',
    type: commanderMeta?.type_line || 'Commander',
  };
  if (typeof commanderMeta?.cmc === 'number') commanderTile.cmc = commanderMeta.cmc;
  const commanderTiles: DeckCardTile[] = [commanderTile];
  if (deck.partner) {
    const partnerMeta = metaForName(deck.partner, ctx);
    const partnerTile: DeckCardTile = {
      n: deck.partner,
      gc: false,
      mv: partnerMeta?.mana_cost || '—',
      price: '—',
      type: partnerMeta?.type_line || 'Commander',
    };
    if (typeof partnerMeta?.cmc === 'number') partnerTile.cmc = partnerMeta.cmc;
    commanderTiles.push(partnerTile);
  }
  const groupName = deck.partner ? 'Commanders' : 'Commander';
  const groups: DeckListGroup[] = [{ name: groupName, cards: commanderTiles }];
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
        const meta = metaForName(c.name, ctx);
        const qty = c.quantity ?? 1;
        const tile: DeckCardTile = {
          n: c.name,
          mv: mvFromRow(c, meta),
          price: hl?.price || '—',
          type: c.type || meta?.type_line || '—',
          gc: !!hl?.isGameChanger,
          note: hl?.reason,
          ...(qty > 1 ? { qty } : {}),
        };
        if (typeof meta?.cmc === 'number') tile.cmc = meta.cmc;
        return tile;
      }),
    });
  }
  return groups;
}

/** Normalize one raw deck bundle into the UI-facing DeckFull shape. */
export function normalizeDeck(bundle: RawDeckBundle, idx: number): DeckFull {
  const { id, index: idxEntry, deck, sim } = bundle;
  const ctx = buildCtx(deck, bundle.cardMetadata);
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
    status: deck.status === 'brewing' ? 'brewing' : 'physical',
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
    physicalDecklist: expandToCopies(deck.decklist || []),
    synergies: (deck.synergies || []).map((s) => ({
      title: s.title || '',
      cards: s.cards || [],
      description: s.description || '',
    })),
    gameChangers: deck.gameChangers || 0,
    tokens: transformTokens(deck),
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
    partner: d.partner,
    colors: d.colors,
    bracket: d.bracket,
    price: d.price,
    hasDetail: true,
    status: d.status,
  }));
}
