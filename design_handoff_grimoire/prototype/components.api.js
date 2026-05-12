// Grimoire v1 — Component public API
// ─────────────────────────────────────────────────────────────────
// This file is the SINGLE SOURCE OF TRUTH for what's a public
// component, what props it takes, and where the implementation lives.
//
// At runtime it does nothing — components are still attached to
// window by their implementation files. This file's only job is
// to give engineers a typed, documented inventory.
//
// On migration to a real build (Vite/Next), use this file as the
// barrel index: each `export const Foo = window.Foo` becomes a
// `export { Foo } from './Foo'` and the JSDoc moves to its own file.
//
// Reading order:
//   1. Tokens         → gv1-tokens.css
//   2. Hooks          → §A
//   3. Atoms          → §B
//   4. Molecules      → §C
//   5. Organisms      → §D
//   6. Layout shells  → §E
// ─────────────────────────────────────────────────────────────────

/* ============================================================== */
/* §A. HOOKS                                                       */
/* ============================================================== */

/**
 * useCard — subscribe to the shared Scryfall cache for a card name.
 * Lazy-enqueues a fetch on first use (throttled ≥80ms between calls).
 *
 * @param  {string} name Card name (e.g. "Sol Ring")
 * @return {?CardEntry}  null while not in cache; loading/loaded/error entry once known.
 *
 * @typedef {Object} CardEntry
 * @prop {'loading'|'loaded'|'error'} status
 * @prop {string} name
 * @prop {string} [mana_cost]   e.g. "{2}{R}{R}"
 * @prop {number} [cmc]
 * @prop {string} [type_line]
 * @prop {string} [image_small]  ~146×204 — tile thumbnails
 * @prop {string} [image_normal] ~488×680 — popover frame
 * @prop {string} [art_crop]     ~626×457 — commander hero
 * @prop {?string} [price]        formatted "$0.42" or null
 */
// Implementation: gv1-engine.jsx
export const useCard = window.useCard;

/* ============================================================== */
/* §B. ATOMS                                                       */
/* ============================================================== */

/**
 * ManaCost — render a mana cost string ("{2}{R}{R}") as styled pips.
 * Treats "LAND" / "—" / empty as a special land pip.
 *
 * @param {{ mv?: string }} props
 */
// Implementation: gv1-engine.jsx
export const ManaCost = window.ManaCost;

/**
 * GV1ManaPips — color-identity pips (W U B R G C) from emoji input.
 * Used in deck selector + commander row + codex cards.
 *
 * @param {{ colors?: string }} props colors string e.g. "🔵⚫🔴" or "⚪🔵⚫🔴🟢"
 */
// Implementation: gv1-chrome.jsx
export const GV1ManaPips = window.GV1ManaPips;

/* ============================================================== */
/* §C. MOLECULES                                                   */
/* ============================================================== */

/**
 * CardTile — the workhorse card display (sm | md | lg).
 * Shows live Scryfall art when cached, falls back to deterministic
 * SVG sigil. Always renders mana cost + name + type + price.
 * Adds [data-card-name] so the hover popover can attach.
 *
 * @param {Object} props
 * @param {Object} props.card
 * @param {string} props.card.n      Card name (REQUIRED)
 * @param {string} [props.card.mv]    Mana value, e.g. "{2}{R}" or "—"/"LAND"
 * @param {string} [props.card.type]  Type line; falls back to live Scryfall type
 * @param {string} [props.card.note]  Editor's note shown below type
 * @param {string} [props.card.price] e.g. "$0.42"; falls back to live price
 * @param {boolean} [props.card.gc]   Game-changer flag — adds star + gold border
 * @param {'sm'|'md'|'lg'} [props.size='md']
 */
// Implementation: gv1-engine.jsx
export const CardTile = window.CardTile;

/**
 * GV1CommanderArt — large commander hero with Scryfall art_crop.
 * Handles loading / error / fallback states internally.
 * Rerenders cleanly on slug change.
 *
 * @param {{ name: string, slug: string }} props
 */
// Implementation: gv1-chrome.jsx
export const GV1CommanderArt = window.GV1CommanderArt;

/* ============================================================== */
/* §D. ORGANISMS — page sections                                   */
/* ============================================================== */

/**
 * GV1Topbar — the terminal-style top chrome bar.
 * Static; reads deck count from window.GV1_DATA.
 */
export const GV1Topbar = window.GV1Topbar;

/**
 * GV1Hero — landing-page hero (title, sigil, codex meta strip).
 * Currently unused by the guide flow; available for an index page.
 */
export const GV1Hero = window.GV1Hero;

/**
 * GV1DeckSelector — horizontal pill rail for picking a deck.
 *
 * @param {Object} props
 * @param {Array<{idx:number,slug:string,name:string,cmd:string,colors:string,bracket:string,price:string,hasDetail:boolean}>} props.decks
 * @param {number}   props.activeIdx   Currently-selected deck idx
 * @param {Function} props.onSelect    (idx:number) => void — fires when user picks a non-stub deck
 */
export const GV1DeckSelector = window.GV1DeckSelector;

/**
 * GV1Commander — full commander spotlight section.
 * Combines art + dossier + stats + strategy.
 *
 * @param {{ deck: import('./types').FullDeck }} props
 */
export const GV1Commander = window.GV1Commander;

/**
 * GV1WinCons — § II Win Conditions grid.
 *
 * @param {{ wincons: Array<WinCon> }} props
 *   WinCon: { title:[string,string], desc:string, prob?:string, cards:Card[] }
 *   Empty array renders an empty state.
 */
export const GV1WinCons = window.GV1WinCons;

/**
 * GV1Engine — § III The Engine (tabbed role panels).
 *
 * @param {{ engine: Array<EngineRole> }} props
 *   EngineRole: { title:string, count:number, cards:Card[], isGameChangers?:boolean }
 *   First role auto-selected; clicking a tab swaps the panel.
 */
export const GV1Engine = window.GV1Engine;

/**
 * GV1Combos — § IV Combos & Interactions.
 *
 * @param {{ combos: Array<Combo> }} props
 *   Combo: { tag:string, title:[string,string], desc:string, cards:Card[], src:string }
 */
export const GV1Combos = window.GV1Combos;

/**
 * GV1Upgrades — § V Upgrade Path table.
 *
 * @param {{ upg: Array<UpgradeSwap> }} props
 *   UpgradeSwap: { out:Card, inCard:Card, note:string }
 */
export const GV1Upgrades = window.GV1Upgrades;

/**
 * GV1Performance — § VI Scrying Pool / Performance dashboard.
 *
 * @param {Object} props
 * @param {Array<{cmc:string,n:number,peak?:boolean}>} props.curve
 * @param {Array<{l:string,n:number,pct:number}>}     props.func
 * @param {Array<[string,string]>}                     props.sources
 * @param {?{score:number,grade:string}}               props.health
 * @param {?{avgCmc:number,totalCards:number,lands:number}} props.composition
 * @param {?{manaAdequacy:string,mulliganVerdict:string,commanderTiming:string}} props.assessment
 */
export const GV1Performance = window.GV1Performance;

/**
 * GV1Decklist — § VII The Manifest (card list grouped by role).
 *
 * @param {{ list: Array<{name:string, cards:Card[]}> }} props
 */
export const GV1Decklist = window.GV1Decklist;

/**
 * GV1Mobile — full iPhone-bezel mobile view of a deck.
 *
 * @param {{ deck: import('./types').FullDeck }} props
 */
export const GV1Mobile = window.GV1Mobile;

/**
 * GV1Codex — cross-deck overview dashboard. Contains its own
 * filter + sort state; expects the FULL deck list.
 *
 * @param {{ decks: Array<import('./types').FullDeck> }} props
 */
export const GV1Codex = window.GV1Codex;

/**
 * GV1CodexCard — single-deck card used inside the codex grid.
 *
 * @param {{ deck: import('./types').FullDeck, rank: number }} props
 */
export const GV1CodexCard = window.GV1CodexCard;

/* ============================================================== */
/* §E. LAYOUT / GLOBAL                                             */
/* ============================================================== */

/**
 * GV1CardHoverLayer — mount ONCE near the React root. Listens
 * globally for mouseover on [data-card-name] and renders a
 * Scryfall popover. No props.
 */
export const GV1CardHoverLayer = window.GV1CardHoverLayer;

/* ============================================================== */
/* §F. DATA LAYER                                                  */
/* ============================================================== */

/**
 * window.GV1_DATA — built at load by gv1-data.js.
 *   .DECKS      : selector-pill summaries
 *   .DECK_MAP   : { [slug]: FullDeck }
 *   .DECK_FULL  : array of FullDeck in shelf order
 *
 * window.GV1Cards — Scryfall cache:
 *   .get(name) → entry|null
 *   .fetch(name) → Promise<entry>
 *   .subscribe(name, fn) → unsubscribe
 *   .enqueue(name) — queue for throttled fetch
 *
 * @typedef {Object} FullDeck
 * @prop {number} idx
 * @prop {string} slug
 * @prop {string} commander
 * @prop {string} deckName
 * @prop {string} colors      e.g. "🔵⚫🔴"
 * @prop {string} bracket     e.g. "IV"
 * @prop {string} price       e.g. "$420"
 * @prop {string} type        e.g. "Eldrazi · Cascade"
 * @prop {string} flavor
 * @prop {string[]} oracle
 * @prop {string} strategy
 * @prop {Array<WinCon>}    wincons
 * @prop {Array<EngineRole>} engine
 * @prop {Array<Combo>}     combos
 * @prop {Array<UpgradeSwap>} upg
 * @prop {Array<Curve>}     curve
 * @prop {Array<FuncRow>}   func
 * @prop {Array<[string,string]>} sources
 * @prop {?Health}          health
 * @prop {?Composition}     composition
 * @prop {?Assessment}      assessment
 * @prop {Array<Group>}     list
 */
