# Grimoire v1 — Handoff

A single-page Commander deck companion. Seven artboards in one canvas, all real:

**Per-deck (3):** Deck Guide · Codex Overview · Mobile Guide
**Cross-deck tools (3):** Compare · Shopping List · Scrying Pool
**Mobile responsive (1):** Mobile Scrying Pool

All seven render from real data for 12 decks, with live Scryfall card art, prices, and hover popovers. There are **no stubs** — every surface is interactive.

---

## TL;DR for the next engineer

1. Open `Grimoire v1.html`. Everything is loaded from there.
2. Pick a deck from the selector in the chrome — **Guide, Mobile, and Scrying Pool** all react in lockstep. Codex / Shopping / Compare are multi-deck by design.
3. Hover any card name (anywhere) → full Scryfall popover with image + price + oracle text.
4. Tokens live in `gv1-tokens.css`. Touch those before touching components.
5. Component contracts live in `components.api.js`. Read that file before writing new ones.
6. **No build step.** Hand-loaded JSX via `@babel/standalone`. Cache-bust by bumping the `?v=N` on the script tag.

---

## What ships

| Surface | Component | Source data | Notes |
|---|---|---|---|
| Deck Guide (hero, commander, win-cons, engine, combos, upgrades, performance, decklist) | `gv1-chrome.jsx` + `gv1-engine.jsx` + `gv1-perf.jsx` + `gv1-mobile.jsx` (§VII) | `deck.json` per deck | Reactive to selected deck |
| Codex Overview | `gv1-codex.jsx` (`GV1Codex`) | All `deck.json` | All 12 decks, sortable, filterable |
| Mobile Guide | `gv1-mobile.jsx` (`GV1Mobile`) | `deck.json` | iPhone-bezel artboard, internal mobile styling |
| **Compare** | `gv1-compare.jsx` (`GV1Compare`) | All `deck.json` | All 12 decks; sortable on every column. Five health components per deck (mana / threats / interaction / combo / commander independence). Color-tinted score chips, grade badges, mana pips. Click a deck name → navigates to its Guide. Sticky header. |
| **Shopping List** | `gv1-shopping.jsx` (`GV1Shopping`) | All `recommendations.json` | Multi-deck chip selection. CSV/TXT owned-cards import (parses `1x Card Name`). `localStorage` persistence (`grimoire-owned-cards`). Need-to-Buy / Already-Own split. Sort by Type or A–Z. Per-card mana cost. Cross-deck "across N decks" attribution. Copy-to-clipboard buy list. |
| **Scrying Pool** (desktop) | `gv1-scrying.jsx` (`GV1Scrying`) | `simulation.json` + `game-changers.json` | Hand simulator (draw/mulligan with Paris+London bottoming, scry, keep, bottom-N selection). Swap analyzer (cut+add picker → simulation delta + GC awareness). KPI rings, mana ramp chart, mulligan/curve histograms. |
| **Scrying Pool** (mobile) | same component | same | Container-query reflow. Hand → 3-up grid; swap → stacked with ↓ arrow; sim panels → single column; histogram → compact bars. Full feature parity, just narrower. |
| Card hover popover | `gv1-cardhover.jsx` (`GV1CardHoverLayer`) | Scryfall | Global `[data-card-name]` listener. Mount once near root. |
| Scryfall art + prices | `gv1-cards.js` (`useCard()` hook) | Scryfall | Throttled (≥80ms), deduped, cached for process lifetime |

### Other notes

- `preview.html` is stale (still pulls flat top-level keys from the data layer rather than a single deck object). Either update it to consume `DECK_FULL[i]` or delete it.
- No build step — hand-loaded JSX via `@babel/standalone`.
- Scryfall calls happen at component mount; no SSR / prefetch / service worker.

---

## File map

```
Grimoire v1.html        ← entry; loads everything in order
design-canvas.jsx       ← seven-artboard pan/zoom shell (starter component)

# Tokens & states
gv1-tokens.css          ← color, type, space, motion tokens — single source of truth
gv1-states.css          ← hover/focus/loading/empty interaction primitives
gv1-styles.css          ← shared component styles (uses tokens + states)

# Surface-specific styles
gv1-shopping.css        ← Shopping List
gv1-compare.css         ← Compare
gv1-scrying.css         ← Scrying Pool (uses container queries for mobile)

# Data
gv1-real-decks.js       ← inlined raw deck.json/recommendations.json/simulation.json bundles
gv1-data.js             ← normalizes raw bundles → window.GV1_DATA.{DECKS, DECK_MAP, DECK_FULL}
gv1-cards.js            ← Scryfall fetch cache + useCard() hook (throttled, batched)
gv1-game-changers.js    ← official MTG Commander Game Changers list (51 cards) for swap analyzer

# Components — per-deck guide
gv1-chrome.jsx          ← topbar, hero, deck selector, commander spotlight
gv1-engine.jsx          ← § II Win Conditions + § III The Engine (also exports CardTile + ManaCost)
gv1-perf.jsx            ← § IV Combos + § V Upgrade Path + § VI Performance dashboard
gv1-mobile.jsx          ← mobile artboard (GV1Mobile + GV1Decklist § VII)

# Components — cross-deck tools
gv1-codex.jsx           ← cross-deck overview artboard
gv1-compare.jsx         ← Compare artboard
gv1-shopping.jsx        ← Shopping List artboard
gv1-scrying.jsx         ← Scrying Pool artboard (desktop + mobile responsive via container queries)

# Components — global
gv1-cardhover.jsx       ← global [data-card-name] → Scryfall popover layer

# Reference
components.api.js       ← public component inventory + JSDoc contracts (read this!)
SCOPE.md                ← locked design decisions + glossary
preview.html            ← isolated harness for a single artboard (currently stale — update or delete)
```

Loading order in `Grimoire v1.html` matters — tokens before states before component CSS; data before cards before components; chrome before artboards. Don't shuffle.

> **Naming caveat:** `gv1-engine.jsx` is named for The Engine *section* (§ III of the deck guide), not an "upgrade engine." Upgrade swaps live in `gv1-perf.jsx`.

---

## Architecture

### Data flow

```
deck.json            ─┐
recommendations.json ─┼─→ gv1-real-decks.js ─→ gv1-data.js ─→ window.GV1_DATA.DECK_FULL[]
simulation.json      ─┘                           ↑
                                              normalization
                                              (handles missing fields,
                                               synthesizes derived counts)
game-changers.json     ─────────────────────→ gv1-game-changers.js ─→ window.GV1_GAME_CHANGERS_SET
```

`DECK_FULL` is the only shape components consume. If a new deck is added, regenerate `gv1-real-decks.js` from the source JSON files and `gv1-data.js` will pick it up — no component changes needed. Same for `gv1-game-changers.js` if WotC updates the GC list.

### Reactive selection

A single `useState` lives in the top-level `App` in `Grimoire v1.html`. The Guide artboard writes to it via `GV1DeckSelector.onSelect`; **Guide, Mobile, both Scrying artboards (desktop + mobile)** all read from it. Codex / Shopping / Compare are multi-deck by design (cross-deck overviews) and don't subscribe — though Compare's deck-name links call `gv1NavTo('guide')` to jump there.

If you add a new artboard that needs to react, pass `activeIdx` (and `setActiveIdx` if it needs to write) down from `App` — no pub/sub needed at this scale.

### Card art

`useCard(name)` (defined in `gv1-cards.js`, re-exported in `components.api.js`) subscribes a component to a shared in-memory Scryfall cache. First subscriber for a name enqueues a fetch (≥80ms apart, deduped). Cache is process-lifetime; refresh = re-fetch.

Loading and empty/error states are handled by primitives in `gv1-states.css` (`.gv1-skeleton`, `.gv1-loading-inline`, `.gv1-hoverable`) — components don't reimplement skeletons.

### Container queries (Scrying mobile)

The Scrying Pool's mobile reflow uses `@container scrying (max-width: 720px)` rather than `@media`, so it triggers based on the **artboard's** rendered width, not the viewport's. This lets the 390px Mobile Scrying artboard sit inside the 1440px-wide canvas and still get the mobile layout. The container is declared on `[data-gv1-screen="scrying"], [data-gv1-screen="mobile-scrying"]` at the top of `gv1-scrying.css`.

If you add another mobile-responsive surface, follow the same pattern: declare `container-type: inline-size` on the artboard root, then use `@container` rules. Real-browser viewport-based responsive (`@media`) still works for users actually visiting the bundled site at phone widths.

---

## Design system

### Tokens (`gv1-tokens.css`)

Layered as **primitives → semantic → component**. Components should reference *semantic* tokens; only semantic tokens may reference primitives.

**Color primitives**
- `--gv1-ink-blue-{600..900}` — background scale
- `--gv1-parchment-{100..600}` — text scale (light on dark)
- `--gv1-rune-{100..900}` — green accent (active, positive)
- `--gv1-gold-{300,500,700}` — italic accent (use sparingly)
- `--gv1-mana-{w,u,b,r,g,c}` + matching `*-stroke` — color-identity pips
- `--gv1-status-{warn,error}` — informational only

**Color semantic**
- `--gv1-bg`, `--gv1-bg-2`, `--gv1-bg-3`, `--gv1-bg-elevated`
- `--gv1-ink`, `--gv1-ink-bright`, `--gv1-ink-dim`, `--gv1-ink-dimmer`
- `--gv1-rune`, `--gv1-rune-dim`, `--gv1-rune-bright`, `--gv1-gold`
- `--gv1-line`, `--gv1-line-strong`, `--gv1-line-rune`
- `--gv1-focus-ring`, `--gv1-focus-bg`, `--gv1-selection-bg`, `--gv1-selection-fg`
- `--gv1-grid` (background grid wash)

**Type** — `IM Fell English` (display serif) + `IM Fell DW Pica` (alt serif) + `JetBrains Mono`. Loaded via Google Fonts in the HTML head. There is no `--gv1-fs-*` size scale; sizes are set per-component using utility classes (`.gv1-serif-xl`, `.gv1-mono-xs`, etc.) defined in `gv1-styles.css`. Migrating these to a numeric scale would be a real win.

**Space, radius, motion, z-index**
- `--gv1-radius-{1,2,3,...}`
- `--gv1-duration-{quick,base,slow}`, `--gv1-ease-{out,in,in-out}`, `--gv1-transition-{quick,base}`
- `--gv1-z-{base,content,sticky,overlay,popover,toast,modal}`

Change a token, the whole UI re-keys. A few hard-coded hex values still live in `gv1-styles.css` (notably the mana-value chip colors at `.gv1-mv-c` and the card-art fallback gradient) — they should be promoted to tokens.

### Components

See `components.api.js` for the full inventory and JSDoc prop contracts. The actual public surface:

**Hooks**
- `useCard(name)` → Scryfall cache subscription

**Atoms**
- `ManaCost`, `GV1ManaPips`

**Molecules**
- `CardTile`, `GV1CommanderArt`

**Organisms (deck-guide sections)**
- `GV1Topbar`, `GV1Hero`, `GV1DeckSelector`, `GV1Commander`
- `GV1WinCons` (§ II), `GV1Engine` (§ III), `GV1Combos` (§ IV)
- `GV1Upgrades` (§ V), `GV1Performance` (§ VI), `GV1Decklist` (§ VII)

**Artboard roots**
- `GV1Codex` + `GV1CodexCard` — cross-deck overview
- `GV1Mobile` — full mobile bezel view
- `GV1Compare` — § X cross-deck Compare
- `GV1Shopping` — § IX cross-deck Shopping List
- `GV1Scrying` — § VIII per-deck Scrying Pool (used for both desktop + mobile artboards)

**Layout / global**
- `GV1CardHoverLayer` — mount once near root; intercepts `[data-card-name]` mouseover globally

Atoms never fetch. Molecules use hooks. Organisms own layout. If a component is doing two of those jobs, split it.

> Patterns like `Sigil`, `MonoLabel`, `RuneRule`, `PriceChip`, `StatBlock`, `SwapRow` are *visible in the design* but not yet factored into standalone components. Doing so is the natural next refactor.

---

## Accessibility

- Every interactive element is keyboard reachable. Focus rings come from `--gv1-focus-ring` in tokens; rule lives in `gv1-tokens.css` under `.gv1-root :focus-visible`.
- `<header>`, `<main>`, `<nav>`, `<section>` landmarks on every artboard root.
- The Engine tabs implement the WAI-ARIA tablist pattern (arrow keys, Home/End, `aria-selected`, roving tabindex).
- Card art has `alt` from the card name; decorative sigils have `aria-hidden="true"`.
- Color is never the sole channel — every state pairs color with iconography or text.
- `prefers-reduced-motion` disables non-essential animations in `gv1-states.css`.

---

## Working on it

- **Add a new card view?** Use `<CardTile name=... />`. It handles fetching, loading, hover popover, price, and mana cost.
- **Add a new artboard?** Drop a `<DCArtboard>` into the `App()` in `Grimoire v1.html`, give it a unique id, mount your root component. If it needs to react to deck selection, accept `activeIdx` as a prop and resolve via `deckByIdx(activeIdx)`.
- **Add a new token?** `gv1-tokens.css`, then reference via `var(--gv1-…)`. Never inline.
- **Hit a missing field on a deck?** Add the fallback in `gv1-data.js` normalization — not in the component. Components assume `DECK_FULL` is well-formed.
- **Need a mobile-responsive variant of an existing tool?** Add a second `<DCArtboard>` at the target width. Wrap `[data-gv1-screen="..."]` with `container-type: inline-size` and use `@container` queries for the reflow rules.

That's the whole thing. Read `components.api.js` and `SCOPE.md` next.
