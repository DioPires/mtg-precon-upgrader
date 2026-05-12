// Grimoire v1 — real data, derived from /data/index.json + /<deckId>/deck.json, recommendations.json, simulation.json
// All 12 decks render from real JSON. No invented deck contents.
//
// This file assumes the real data has been bundled into window.GV1_REAL_DECKS
// (an array of { id, index, deck, recs, sim }) by the page loader.

window.GV1_DATA = (() => {

// Scryfall image helpers
const scryArt = (name) => `https://api.scryfall.com/cards/named?fuzzy=${encodeURIComponent(name)}&format=image&version=art_crop`;
const scryCard = (name) => `https://api.scryfall.com/cards/named?fuzzy=${encodeURIComponent(name)}&format=image&version=normal`;
const scrySmall = (name) => `https://api.scryfall.com/cards/named?fuzzy=${encodeURIComponent(name)}&format=image&version=small`;

// ---- Helpers ------------------------------------------------------

// Color identity array -> glyph string the existing GV1ManaPips expects
const COLOR_TO_GLYPH = { W: '⚪', U: '🔵', B: '⚫', R: '🔴', G: '🟢', C: '◇' };
const colorsToGlyphs = (arr) => (arr || []).map(c => COLOR_TO_GLYPH[c] || '◇').join('');

// Roman numerals for bracket
const ROMAN = { '1': 'I', '2': 'II', '3': 'III', '4': 'IV', '5': 'V' };
const toRoman = (n) => ROMAN[String(n)] || String(n);

// Split a title like "Infinite Mana into Eldrazi Army" into [first half, emphasized tail]
// so the existing wincon/combo UI renders <span>first</span><em>second</em>.
const splitTitle = (t) => {
  if (!t) return ['', ''];
  const words = t.split(/\s+/);
  if (words.length <= 1) return [t, ''];
  const mid = Math.ceil(words.length / 2);
  return [words.slice(0, mid).join(' ') + ' ', words.slice(mid).join(' ')];
};

// Format a price range from deck.cost or derive from highlights.
const formatCost = (c) => (c || '—').replace(/\$/g, '$');

// Best-effort approximate mana value for display. Most deck.json rows don't include MV,
// so we show '—' unless we can infer from role=lands.
const mvFromRow = (row) => {
  if (!row) return '—';
  if (row.type === 'Land' || row.role === 'lands') return 'LAND';
  return '—';
};

// Build a card tile payload from a raw card NAME + optional metadata.
// Looks up type/role/price/gc from the deck's decklist + highlights tables.
function tileFor(name, ctx) {
  if (!name) return { n: '—', mv: '—', price: '—', type: '—' };
  const dl = ctx.decklistByName[name.toLowerCase()];
  const hl = ctx.highlightsByName[name.toLowerCase()];
  return {
    n: name,
    mv: dl ? mvFromRow(dl) : '—',
    price: hl?.price || '—',
    type: dl?.type || (hl ? '—' : '—'),
    gc: !!hl?.isGameChanger,
    note: hl?.reason || undefined,
  };
}

// Build the per-deck context once so tileFor is fast.
function buildCtx(deck) {
  const decklistByName = {};
  (deck.decklist || []).forEach(c => { decklistByName[c.name.toLowerCase()] = c; });
  const highlightsByName = {};
  (deck.highlights || []).forEach(h => { highlightsByName[h.name.toLowerCase()] = h; });
  return { decklistByName, highlightsByName };
}

// Role labels (from the role slugs used in deck.json)
const ROLE_LABEL = {
  'lands': 'Lands',
  'ramp': 'Ramp',
  'card-draw': 'Card Draw',
  'counter-spells': 'Counters',
  'removal': 'Removal',
  'board-wipes': 'Board Wipes',
  'graveyard-hate': 'GY Hate',
  'reanimation': 'Reanimate',
  'finishers': 'Finishers',
  'protection': 'Protection',
  'value': 'Value',
  'combo-enabler': 'Combo',
  'tutor': 'Tutors',
  'utility': 'Utility',
};

// Order sections in the Engine tab.
const ENGINE_ROLE_ORDER = ['ramp','card-draw','removal','counter-spells','board-wipes','finishers','value','reanimation','protection','combo-enabler'];

// Abbreviate source type -> pill label
const SRC_LABEL = {
  'edhrec': 'EDHREC',
  'youtube': 'YouTube',
  'article': 'Article',
  'commanderspellbook': 'Spellbook',
  'ai-inferred': 'Analysis',
  'scryfall': 'Scryfall',
  'reddit': 'Reddit',
};

// ---- Per-deck transform ------------------------------------------

function transformDeck(record, idx) {
  const { id, index: idxEntry, deck, recs, sim, metrics, candidates } = record;
  if (!deck) return null;

  const ctx = buildCtx(deck);

  // ----- Wincons --------------------------------------------------
  const wincons = (deck.winConditions || []).map((w) => ({
    title: splitTitle(w.title),
    // No per-wincon turn data in real JSON — derive bucket from commander bracket + sim speed if present
    prob: '',
    desc: w.description,
    cards: (w.cards || []).slice(0, 3).map(n => tileFor(n, ctx)),
  }));

  // ----- Engine (categories) --------------------------------------
  // Categories in deck.json are the strategic groupings the author already defined.
  // We use those directly as engine sections.
  const engineSections = (deck.categories || []).map(cat => ({
    title: cat.name,
    count: (cat.cards || []).length,
    cards: (cat.cards || []).map(n => tileFor(n, ctx)),
    isGameChangers: !!cat.isHighlighted,
  })).filter(s => s.count > 0);

  // ----- Combos / synergies --------------------------------------
  const combos = (deck.synergies || []).map(s => {
    // Pick a source label — prefer Commander Spellbook, then EDHREC, then first available
    const srcs = s.sources || [];
    const preferred = srcs.find(x => x.type === 'commanderspellbook')
                   || srcs.find(x => x.type === 'edhrec')
                   || srcs[0];
    const srcLabel = preferred
      ? `${SRC_LABEL[preferred.type] || preferred.type} · ${preferred.name || preferred.detail || ''}`.trim().replace(/\s*·\s*$/, '')
      : '';
    return {
      title: splitTitle(s.title),
      desc: s.description,
      cards: (s.cards || []).slice(0, 3).map(n => tileFor(n, ctx)),
      src: srcLabel,
      tag: `${(s.cards || []).length}-CARD`,
    };
  });

  // ----- Apothecary (from metrics.json + candidates.json) ---------
  // Schema mirrors upstream: Diagnosis (metrics.global_health + per-component scores),
  // Maladies (metrics.gaps[]), Remedies (top-N candidates with mitigates_gap + score).
  // Decks without metrics/candidates render an empty Apothecary.
  const apothecary = (metrics && candidates) ? {
    diagnosis: {
      score: metrics.global_health,
      methodology: metrics.methodology || 'deck-metrics-v1',
      generatedAt: metrics.generated_at,
      mirrorUpdatedAt: candidates.scryfall_mirror_updated_at,
      components: metrics.metrics || {},
    },
    maladies: metrics.gaps || [],
    remedies: candidates.candidates || [],
  } : null;

  // ----- Curve + Function mix (from decklist roles) ---------------
  // The real deck.json rows don't include per-card MV, so we can't draw a mana-value curve
  // from them. We DO have role/type distributions, and sim.deckComposition has avgCmc and counts.
  // Instead of inventing a curve, we show a role-distribution chart labelled accurately.
  const roleCounts = {};
  (deck.decklist || []).forEach(c => { roleCounts[c.role] = (roleCounts[c.role] || 0) + 1; });
  const roleEntries = Object.entries(roleCounts).sort((a,b) => b[1] - a[1]);
  const maxRole = Math.max(1, ...roleEntries.map(([,n]) => n));
  // Reuse the existing 'curve' prop shape (cmc+n) but feed role counts.
  const curve = roleEntries.slice(0, 8).map(([role, n]) => ({
    cmc: ROLE_LABEL[role] || role,
    n,
    peak: n === maxRole,
  }));

  // Function mix = same data, different view (percent of max).
  const func = roleEntries.map(([role, n]) => ({
    l: ROLE_LABEL[role] || role,
    n,
    pct: Math.round((n / maxRole) * 100),
  }));

  // ----- Sources --------------------------------------------------
  const sources = (deck.sources || []).map(s => [
    SRC_LABEL[s.type] || s.type || 'Source',
    s.name || s.detail || '',
  ]);

  // ----- Full decklist grouped by role ---------------------------
  const byRole = {};
  (deck.decklist || []).forEach(c => {
    const role = c.role || 'other';
    (byRole[role] ||= []).push(c);
  });
  const list = [
    { name: 'Commander', cards: [{ n: deck.commander, gc: deck.gameChangers > 0, mv: '—', price: '—', type: 'Commander', note: '' }] },
    ...Object.entries(byRole)
      .sort((a, b) => {
        // Lands last, ramp first after commander, then by size desc
        if (a[0] === 'lands') return 1;
        if (b[0] === 'lands') return -1;
        return b[1].length - a[1].length;
      })
      .map(([role, cards]) => ({
        name: `${ROLE_LABEL[role] || role} (${cards.length})`,
        cards: cards.map(c => ({
          n: c.name,
          mv: c.role === 'lands' ? 'LAND' : '—',
          price: ctx.highlightsByName[c.name.toLowerCase()]?.price || '—',
          type: c.type,
          gc: !!ctx.highlightsByName[c.name.toLowerCase()]?.isGameChanger,
          note: ctx.highlightsByName[c.name.toLowerCase()]?.reason,
        })),
      })),
  ];

  // ----- Top-level scalar stats for the commander spotlight --------
  const pt = '—'; // not in real data without a Scryfall lookup
  const cost = deck.cost || '—';
  const bracket = toRoman(deck.bracket);
  const winTurn = '—'; // sim.goldfish tracks lethalProxy by turn; we could derive a median but let's be honest
  const winRate = sim?.deckHealthScore?.score ? Math.round(sim.deckHealthScore.score) : null;

  // Strategy overview from deck.guideContent (already written by the real analysis)
  const strategy = deck.guideContent?.strategyOverview || '';

  // Synthesize oracle-text-like lines from deck.guideContent if available, else leave empty.
  // We don't have commander oracle text in local JSON; show theme + strategy snippet instead.
  const oracle = [
    `Theme · ${idxEntry.theme}`,
    `Last verified · ${idxEntry.lastUpdatedSet}`,
  ];

  // Derive a short flavor line — pull first sentence of strategy
  const flavor = strategy ? strategy.split(/(?<=[.!?])\s+/)[0] : '';

  return {
    idx,
    slug: id,
    deckName: deck.name,
    commander: deck.commander,
    commanderMv: '—',
    type: `Commander · ${idxEntry.theme}`,
    colors: colorsToGlyphs(idxEntry.colors),
    bracket,
    pt,
    price: cost,
    winTurn,
    winRate,
    flavor,
    oracle,
    strategy,
    wincons,
    engine: engineSections,
    combos,
    apothecary,
    curve,
    func,
    sources,
    list,
    // real metrics
    health: sim?.deckHealthScore || null,
    assessment: sim?.assessment || null,
    composition: sim?.deckComposition || null,
    // raw payloads for Scrying (hand sim + swap analyzer)
    sim: sim || null,
    rawDecklist: deck.decklist || [],
    synergies: (deck.synergies || []).map(s => ({
      title: typeof splitTitle === 'function' && splitTitle(s.title)?.first ? `${splitTitle(s.title).first} ${splitTitle(s.title).rest || ''}`.trim() : (s.title || ''),
      cards: s.cards || [],
      description: s.description || '',
    })),
    gameChangers: deck.gameChangers || 0,
  };
}

// ---- Build the full data set -------------------------------------

const raw = window.GV1_REAL_DECKS || [];
const DECK_FULL = raw.map((r, i) => transformDeck(r, i + 1)).filter(Boolean);

// Selector-facing metadata
const DECKS = DECK_FULL.map((d, i) => ({
  idx: i + 1,
  slug: d.slug,
  name: d.deckName,
  cmd: d.commander,
  colors: d.colors,
  bracket: d.bracket,
  price: d.price,
  hasDetail: true,
}));

const DECK_MAP = {};
DECK_FULL.forEach(d => { DECK_MAP[d.slug] = d; });

// Back-compat aliases (first deck as legacy single-deck export)
const z = DECK_FULL[0] || {};
return {
  DECKS, DECK_MAP, DECK_FULL, DECK_STUBS: [],
  scryArt, scryCard, scrySmall,
  WINCONS: z.wincons || [], ENGINE: z.engine || [], COMBOS: z.combos || [],
  APOTHECARY: z.apothecary || null, CURVE: z.curve || [], FUNC: z.func || [], SOURCES: z.sources || [], LIST: z.list || [],
};
})();
