# Architecture

### Frontend — Vite + React + TypeScript (post-DEC-149 cutover 2026-05-05)
Production frontend is now `web/` — Vite + React 18 + TypeScript. Vanilla JS app archived to `legacy/` for one release. `vercel.json` builds `cd web && npm run build`, copies `data/` into `dist/data/`, serves `web/dist/` as host root. `localStorage` keys preserved across cutover: `grimoire-prefs`, `grimoire-owned-cards`.
- Source: session 01f7504e, 2026-03-20; session a8e6cc42, 2026-03-20; session a8413c84, 2026-05-05

### Tab-Based SPA Views
Three tabs: **Grimoire** (deck guide), **Scrying Pool** (simulation analytics), **Shopping List** (upgrade buy list). Battlefield/playtest tab was removed in full (DEC-11, commit removes ~700 JS lines, ~710 CSS lines, ~80 HTML lines).
- Source: session 4a7404a5, 2026-03-20

### Deck Data Structure
Flat JSON per deck. Key fields: `commander` (string), `cards[]` (array with `name`, `category`, `type` per card). No tier nesting — previous tier-based structure was flattened. `getEffectiveCommander()` is a legacy helper that should simply return `currentDeck.commander`.
- Source: session 9a365107, 2026-03-20

### Simulation Engine
Exists in `app.js`. Produces mana curve data and sim metrics (average mana available by turn, win-condition assessment). Results displayed in Scrying Pool view. Simulation runs against the current deck's mana base.
- Source: session 4a7404a5, 2026-03-20

### Deck Count
9 decks render in the Grimoire React app (those with `deck.json`). 3 additional directories exist with only `candidates.json` + `metrics.json`. Only `titan-convergence` ships the full dataset (`deck.json` + `simulation.json`). `creeping-corruption` was missing from the DEC-149 design snapshot — add before shipping that route. The earlier claim of "12 production decks" was stale; DEC-150 (2026-05-05) reconciled to 9.
- Source: session 01f7504e, 2026-03-20; session 4d43917b, 2026-03-27; session a8413c84, 2026-05-05

### Shopping List — State & API Surface
Global state: `shoppingSelectedDecks` (Set of deck IDs), `ownedCards` (Map<name, qty>), `shoppingSortMode` ('type' | 'az'). Key functions: `parseOwnedFile(text)` (parses `1x Card Name` format), `aggregateShoppingCards()` (async, deduplicates across decks, skips basic lands), `splitByOwnership(cardMap)`, `renderShoppingList()`, `generateShoppingExportText(format)`. Owned cards persist in localStorage. Input format: `1x Card Name` CSV/TXT (sample file at `priv_data/owned_formatted.csv`). Shopping view is self-contained — hides selector section, has its own deck chip selector.
- Source: session f6684008, 2026-03-20

### Per-Deck CSS Theming Variables
`--deck-accent`, `--deck-glow`, and `--deck-bg-tint` CSS custom properties drive per-deck color theming. `body.colors-BR`, `body.colors-UBR`, `body.colors-C` etc. override these variables. Page background radial-gradient uses `--deck-bg-tint`; `h1` gets `text-shadow: 0 0 40px var(--deck-glow)`. Color identity pips use `.pip-W/U/B/R/G/C` CSS classes (defined in gallery section). Selected shopping deck chips use color gradients derived from commander identity colors (e.g., BR → red→black gradient).
- Source: session 2d0f5dd3, 2026-03-20; session a074338b, 2026-03-20

### Grimoire Tab — Animation Inventory
Key `@keyframes`: `commanderEntrance` (scale 0.92→1.02→1 + blur 6px→0, 0.5s on deck load), `cascadeIn` (7 staggered opacity+translateY, 0.08–0.44s delays), `bracketFill` (5 bracket segments scaleX 0→1, 0.06s stagger), `starPulse` (Game Changer star, 2s loop), `synergyPulse` (box-shadow pulse). Commander art background: `#commander-bg` fixed-position with `blur(40px) brightness(1.4) saturate(0.3) opacity(0.15)`, fades in over 0.8s. Ambient art: `#ambient-art` second layer cycling card art every 15s with `transition: opacity 2s ease`. 3D card tilt: `transform-style: preserve-3d`, `--tilt-max-angle: 15deg`, glare overlay tracks mouse position.
- Source: session 2d0f5dd3, 2026-03-20

### Card Hover Preview — Scoped to Grimoire/Decklist; Floating Tooltip for Shopping
The delegated sidebar preview event listener only targets `#add-groups` and `#decklist-content`. Shopping list has a **separate** floating tooltip: a position-aware popup with Scryfall card image appears near the cursor on card row hover, flipping left/right if near viewport edge. Mobile shopping card taps use the existing full-screen modal instead of the tooltip.
- Source: session 2d0f5dd3, 2026-03-20; session a074338b, 2026-03-20

### Scryfall Rate Limiting System
All Scryfall image fetches go through a centralized throttle queue at 100ms/request (10 req/s). Bulk-rendered images (deck gallery, decklist gallery, guide cards) use `data-scryfall-src` attribute + IntersectionObserver for lazy loading — images only fetch when they scroll into view. URL construction is centralized via `scryfallImageUrl()` helper replacing 12+ scattered constructions. Image URLs persist in localStorage (`grimoire-image-urls`, 2000-entry max) so repeat visits skip API calls. `showMobilePreview()` uses the same cache.
- Source: session a074338b, 2026-03-20

### Sticky Navigation
`.sticky-nav` wrapper with `position: sticky; top: 0` wraps the view-toggle tabs. An IntersectionObserver on `<header>` toggles `.stuck` class when the header scrolls out of view. Stuck state shows a compact collapsed title with frosted glass background. Respects `prefers-reduced-motion`.
- Source: session a074338b, 2026-03-20

### Pencil Design File — grimoire-ui.pen
Design source lives in `designs/grimoire-ui.pen` (managed by Pencil editor app — not a regular filesystem file accessible via read/write tools). PNG exports are committed at `designs/exports/{deck-gallery,grimoire-guide,scrying-pool,shopping-list}.png`. File contains 4 artboards (Deck Gallery, Grimoire Guide, Scrying Pool, Shopping List) + 2 reusable components (Deck Card, Card Row) + 17 design variables matching the app's CSS custom properties. Full-page compositions include the shared navigation shell with the correct active tab state per view.
- Source: session d3c6539f, 2026-03-20; session 12b821bf, 2026-03-20

### Pencil — Empty State Frames (grimoire-ui.pen)
Three empty state frames added to `grimoire-ui.pen`: **Scrying Pool** ("Select a Deck" + bar chart icon in accent circle), **Shopping List** ("No Decks Selected" + clipboard icon in accent circle), **Card Preview** (dashed card-shaped placeholder + image icon + "Hover over a card name" hint). Consistent pattern: 64px circle with `--deck-accent` fill containing a Heroicons icon, 24px Playfair Display title, 14px Inter subtitle below. PNG exports committed at `designs/exports/`.
- Source: session ae955a70, 2026-03-20

### `body.colors-*` Color Identity Class Format
Color identity classes applied as `body.colors-{LETTERS}` where letters are MTG color abbreviations in WUBRG order (e.g., `body.colors-BG`, `body.colors-WUG`, `body.colors-WUBRG`). Only 3 identities have explicit CSS theme overrides (C, BR, UBR); others fall back to default `--deck-accent` values. `body.commander-deck` is also added whenever any deck is selected — used to gate deck-context-specific UI like the sticky nav accent bar.
- Source: session d128f414, 2026-03-20

### Per-Deck Color Theming — React App
In the React app (`web/`), per-deck color theming is applied by setting `body.className = "colors-{IDENTITY}"` when a deck route loads. This was a post-cutover regression found in DEC-164: `body.className` was empty on every deck/scrying/mobile route. Theming requires the className to be set explicitly on mount, not via CSS cascade from a route container.

**Implementation (DEC-164 fix):** `web/src/hooks/useDeckColorTheme.ts` — `useEffect` that reads the deck's color identity, applies `body.colors-{sorted-letters}`, and cleans up on unmount/change. CSS overrides live in `web/src/styles/deck-theme.css` using `--gv1-deck-{accent,accent-dim,glow,bg-tint}` tokens for all 9 commander color combos; defaults added to `tokens.css` so non-deck routes still resolve. Hook wired into `DeckGuide`, `Scrying`, and `Mobile`.
- Source: session a5bf6822, 2026-05-05; session 83355f89, 2026-05-05

### Sticky Nav — Deck Color Accent Bar
A 2px gradient accent bar beneath the sticky nav is implemented as a `::after` pseudo-element on `.sticky-nav.stuck`. Uses `background: linear-gradient(90deg, transparent, var(--deck-accent), transparent)`. Only visible when `body.commander-deck` is present (deck selected) AND nav is in the stuck state. No JS required — pure CSS conditional.
- Source: session d128f414, 2026-03-20

### Shopping List — Layout Specs
Content max-width: **1100px** (not 900px — corrected during DEC-35). Vertical padding: 48px; horizontal: 0 (items fill width). Import bar is **full-width** (not capped at 1100px). Separator between import bar and stats section was removed — no visual divider between those two areas.
- Source: session a96c09ca, 2026-03-20

### Shopping List — Card Row Rendering Details
Shopping card images use Scryfall `art_crop` type (artwork only, not full card face), sized 48×64px with `object-fit: cover` and lazy loading via `data-scryfall-src`. CMC is stored as a float in `cardMetadataCache` and `card-metadata.json` (e.g., `3.0`) — display as integer. CMC rendered in Fira Code font. Deck attribution dots per card row are colored circles derived from `deckIndex.commanders[].colors`; multi-color decks use CSS `linear-gradient` as the `background` value (valid shorthand), single-color use solid fill. `aggregateShoppingCards()` tracks a `decks: Set<deckId>` per card and passes it through `splitByOwnership()` → `renderShoppingCardRow()`.
- Source: session d128f414, 2026-03-20; session 1c444592, 2026-03-20

### Tab-Based SPA Views — Compare Tab Added
Four tabs as of 2026-03-22: Grimoire, Scrying Pool, Shopping List, **Compare**. Compare view (DEC-58) is a sortable cross-deck health comparison table showing all 11 decks side-by-side without requiring a deck selection. `switchView('compare')` renders it; no deck-dependency gate. As of DEC-141, the Compare table reads from `metrics.json` (global_health + 5 deterministic components + `gradeForGlobalHealth()`) rather than the old `recommendations.json` healthBaseline.
- Source: session b885fd99, 2026-03-22; session 3fef9cb0, 2026-05-04

### Deck Data Field Renames (app.js diverges from AGENTS.md)
`app.js` and rendered UI use renamed fields vs. the schema in AGENTS.md: `addCategories` → `categories`; `adds` → `highlights`. The `highlights` array shape: `{name, reason, isGameChanger, sources[]}`. AGENTS.md still documents old names — treat `app.js` as authoritative.
- Source: session ba163d69, 2026-03-22

### metrics.json — Sole Health Data Source (post-DEC-141)
`data/commanders/{id}/metrics.json` is the sole source of truth for deck health. The old `recommendations.json` pipeline (`generate_recommendations.py` → `recommendations.json`) was fully deleted (DEC-141). Five deterministic scores (each 0–100): `manabase_health`, `role_coverage_health`, `curve_health`, `interaction_density`, `gameplan_cohesion`; plus `global_health` (weighted aggregate), `gaps[]` (roles below target), and `generated_at`. Compare view and all UI health displays read from `metrics.json` only. `curve_health` also includes a `cmc_distribution` subkey (added DEC-139) used by the curve bar chart. `recommendations.json` does NOT exist anywhere in the repo — HANDOFF.md referenced it erroneously.
- Source: session 556a72ac, 2026-05-04; session 3fef9cb0, 2026-05-04; session a8413c84, 2026-05-05

### Collapsible Guide Sections
Guide sections implemented with HTML `<details>`+`<summary>` elements + `data-section` attributes. State persisted per-section in localStorage under `grimoire-sections`. Initialized by `initCollapsibleSections()` called from app init. All sections default to collapsed except Strategy Overview. New `<section class="guide-section">` elements automatically pick up `cascade-in` animation from `selectDeck()`.
- Source: session bc11bcf3, 2026-03-22

### Grimoire Tab — Section Order
DOM order: Strategy Overview (div, not section) → Deck Engine → Win Conditions → Key Synergies → Combos → Deck Statistics → Tokens → The Apothecary → Full Deck List. Conditional sections (Win Conditions, Combos, Tokens, The Apothecary) use `style="display:none;"` initially; render functions set `display: ''` when data exists. "The Apothecary" (renamed from "Upgrade Paths" in DEC-140) has three sub-sections: **Diagnosis** (Vitals card + 3 SVG charts), **Maladies** (gaps[] chips), **Remedies** (top-30 candidates list).
- Source: session e9eed048, 2026-03-22; session bc11bcf3, 2026-03-22; session 113e4466, 2026-05-04

### Local Image Pre-fetching — Scripts and Vercel
`scripts/fetch_card_images.py` downloads `normal` and `art_crop` variants for all ~624 cards + back faces for 7 DFC cards. Images stored in `images/` directory. `vercel.json` build step runs the script so images ship to Vercel's edge CDN. Retry: exponential backoff, 5 attempts, delays 1s→2s→4s→8s→16s on 429/5xx/network errors. `fetch_card_metadata.py` includes `layout` field for DFC detection.
- Source: session 90f9b134, 2026-03-22

### Simulation Scripts — Per-Deck Python Pattern
Each deck has its own script at `scripts/mana_simulation_{deck-id-underscored}.py`. Interface contract: `build_decklist(deck_data)`, `classify_cards(decklist, metadata)`, `_run_chunk(args)`, `merge_stats(chunks)`. Mono-color stats keys follow `{color_key}_by_turn` / `zero_{color_key}_by_turn` pattern (e.g., `w_by_turn` for white). Use `azure_dominion` script as template for mono-color decks. Standard run: 100k Monte Carlo. All decks exported via `export_simulation_results.py`.
- Source: session 4d43917b, 2026-03-27

### card-metadata.json — Pre-Simulation Requirement
Before creating a simulation script for a new deck, verify all deck cards exist in `data/card-metadata.json`. Batch-fetch missing cards via Scryfall `scryfall_collection` MCP tool. Missing entries cause cards to be misclassified (e.g., lands counted as spells). 44 Gandalf cards were absent on first run.
- Source: session 4d43917b, 2026-03-27

### The Apothecary — Vitals Card (DEC-137)
Reads `data/commanders/{id}/metrics.json` → derives A–F grade from `global_health` using `gradeForGlobalHealth()`. Grade thresholds: 90+ A / 80–89 B / 70–79 C / 60–69 D / <60 F. Calibration against all 9 built decks (2026-05-04): 4 B, 4 C, 1 F (titan-convergence — curve=0 drags overall). The grade is rendered with 5 component bars (manabase, role coverage, curve, interaction, cohesion) inside `.upgrade-health-baseline` CSS shell.
- Source: session 5c05070c, 2026-05-04

### The Apothecary — Diagnosis Charts (DEC-139)
Three vanilla-SVG charts (no library dependency) rendered inside the Diagnosis sub-section:
1. **Curve chart** — deck-accent colored bars per CMC bucket + dashed `target_avg_cmc` line; CMC>=6 bars turn red when `topcurve_penalty > 0`. Reads `curve_health.cmc_distribution`.
2. **Color sources chart** — per-color bars vs Karsten requirement; green stroke when met, red when short.
3. **Role coverage chart** — horizontal bars per role with B3/B4/B5 target markers; amber/red gap highlighting by score tier.
Charts respect deck color theme via `body.colors-{X}`. Native `<title>` tooltips on every bar.
- Source: session 5c05070c, 2026-05-04

### The Apothecary — Maladies Panel (DEC-138)
`#maladies-panel` renders between Vitals card and Remedies list inside `#upgrade-paths-content`. Hidden when `gaps[]` is empty. One `.malady-chip` per gap with: pretty role label (via `ROLE_LABELS` map, e.g. `card-draw` -> `Card Draw`), actual/target counts, score-tier dot (red <50 / gold 50-74 / green >=75). Click toggles `maladiesFilterRole` and re-renders Remedies filtered to matching `primary_role`. Active chip uses deck accent fill; "Clear filter" affordance appears in panel header. Stale-filter guard resets if active role leaves `gaps[]`.
- Source: session 6acc8e32, 2026-05-04

### The Apothecary — Remedies (DEC-140)
Remedies list reads top-30 from `data/commanders/{id}/candidates.json` (not `recommendations.json`). Gap-addressers (candidates whose `gap_addressed` field matches a `gaps[]` entry) float to the top with a purple left-border and `Addresses: {role}` badge. Click on a Maladies chip filters to matching `primary_role`. Footer shows `metrics.generated_at` + Scryfall mirror age. Configurable N (default 30).
- Source: session 113e4466, 2026-05-04

### Mobile Route — Canonical Form `/m/:id`
In the React app (`web/src/App.tsx`), the mobile artboard route is registered as `/m/:id`. `/mobile/:id` redirects to `/m/:id` via React `<Navigate>`. The design spec, DEC-163 QA coverage, and all internal links use `/m/:id`. Using `/mobile/:id` as the canonical form causes 404s against the spec.
- Source: session 54838c53, 2026-05-05

### Scrying Pool — Pure Logic Layer
`web/src/lib/scrying.ts` contains pure functions for shuffle / London-mulligan math / 7-category swap delta computation. RNG is injectable (default `Math.random`) for deterministic vitest coverage. `web/src/data/gameChangers.ts` is the 51-card TypeScript module ported from `gv1-game-changers.js`. Cross-deck add-search pool, decklist aggregates, and histogram "current hand" highlight all read from `cardCache` singleton — matches legacy prototype behavior.
- Source: session a4d0d123, 2026-05-05

### React Organisms — Shopping and Mobile (DEC-155, P4)
`web/src/components/organisms/Shopping.tsx` — multi-deck chip selector rail, CSV/TXT auto-detect owned-cards import (`grimoire-owned-cards` localStorage key), Need-to-Buy / Already-Own split view, type+A–Z sort modes, copy-buy-list, deck-dot attribution per card row, estimated cost summary.
`web/src/components/organisms/Mobile.tsx` — iPhone-bezel per-deck artboard with tab list, first win-con, mana curve visualization. Both organisms follow the `--gv1-*` token scheme and the existing vitest suite structure.
- Source: session 87a86c06, 2026-05-06

### Default Route Redirect — `/` → `/codex`
`web/src/App.tsx` routes `/` to `<Navigate to='/codex' replace />`. `Home.tsx` stub deleted. `DeckGuide` and `Scrying` write `localStorage['grimoire-last-deck']` on mount so the Topbar nav links track last context.
- Source: session a22484a5, 2026-05-06; session 22e2d585, 2026-05-06

### Topbar — Active Deck ID Resolution Priority
`web/src/components/Topbar.tsx` resolves the deck id for Guide/Scrying nav links via: (1) current URL `:deckId` param when on a deck-scoped route, (2) `localStorage['grimoire-last-deck']`, (3) first commander in `data/index.json`. Links never land on the `/deck/_` stub.
- Source: session 22e2d585, 2026-05-06

### Shopping — Built Decks Reservation Feature (DEC-171)
`web/src/data/builtDecks.ts` — `getBuiltDecks(): Set<string>`, `setBuiltDecks(s)`, `toggleBuiltDeck(id)` — localStorage-backed under key `grimoire-built-decks` (stores string[] of deck ids). `useBuiltDecks()` hook in `web/src/hooks/useBuiltDecks.ts`. Shopping organism renders a "Built Decks" chip rail (mutually exclusive with "Select Decks" rail) with All/None toggle. Reservation math: `availableForShopping = max(0, ownedQty - builtClaims)`, `needQty = max(0, planned.quantity - availableForShopping)`. Per-card "Reserved by N built deck(s)" note renders when applicable. `partner?` field added to `RawDeck` / `DeckFull`.
- Source: session 304bd914, 2026-05-06

### `DeckFull.physicalDecklist` — Expanded by Quantity
`normalize.ts` populates `DeckFull.physicalDecklist` = rawDecklist flattened by quantity (e.g., `{name:'Plains', quantity:7}` becomes 7 entries). `HandSimulator` in `Scrying.tsx` uses `physicalDecklist` for shuffling; `SwapAnalyzer` still uses `rawDecklist` (cuts are per-name). Pool-size display strings use `physicalDecklist.length`. Fixes a sim bias where basics with `quantity>1` were drawn at most once.
- Source: session 08d58789, 2026-05-06

### Shared Card Type Bucket Utility
`web/src/lib/cardType.ts` exports `typeBucket(type: string): string` and `TYPE_ORDER: string[]`. Bucket order: Creature → Planeswalker → Artifact → Enchantment → Instant → Sorcery → Land. Used by Shopping (existing) and Decklist group-by-type toggle (DEC-175). Refactored from Shopping into a shared module to avoid duplication.
- Source: session 70e4830f, 2026-05-06

### Hover Popover — 396px Width, `computeHoverPosition` (DEC-169, DEC-179)
`.gv1-cardhover` width bumped from 264→396px (+50%). `web/src/components/global/GV1CardHoverLayer.tsx` exports pure `computeHoverPosition({ rect, vw, vh })` with constants `POPOVER_W=396`, `POPOVER_H=580`, `HOVER_GAP=12`. Side selection: fitsRight → right; fitsLeft → left; else pick the side with more room. Both x and y are clamped to viewport bounds so the popover never clips at any edge.
- Source: session b6324d57, 2026-05-06; session 80247899, 2026-05-06

### `CardEntry.image_large` in Card Cache (DEC-169)
`CardEntry` (cardCache.ts) has optional `image_large` field populated from Scryfall `imgs.large`. `GV1CardHoverLayer` prefers `image_large` over `image_normal`; falls back to Scryfall `?version=large` URL. Added to keep hover popover sharp at 396px display size.
- Source: session b6324d57, 2026-05-06

### CardTile — Uses `image_normal`, Not `image_small` (DEC-170)
`web/src/components/molecules/CardTile.tsx` uses `live.image_normal` (488×680) with `live.image_small` fallback. Changed from `image_small` (~146×204) which caused upscale blur at tile size. Other consumers (gallery mini-tiles) may still use `image_small` intentionally for performance — do not change those sites.
- Source: session f57045a0, 2026-05-06

### `frontFace()` — DFC / Split Card Name Normalizer (DEC-178)
`web/src/data/cardName.ts` exports `frontFace(name: string): string` — strips ` // Back Face` suffix. Handles all card types using Scryfall's ` // ` separator: DFC, split/aftermath, adventure. Shopping keys `cardMap`, `ownedMap`, and `aggregateBuiltClaims` by `frontFace(name)` while preserving full `Front // Back` as `displayName` for the UI. Scryfall fetches use the full display name.
- Source: session 4a3f24f8, 2026-05-06

### Decklist Manifest — Group-By Toggle + Copy Full List (DEC-175)
`Decklist.tsx` added two features: (1) **Group-by toggle** — By Role (default) vs By Type; persists in URL `?manifest=type|role`. (2) **Copy full list** — serializes to `Nx CardName` format, commander as `1x {name}` at top, basics include their quantities. Uses transient copy-state UX (matching Shopping's "Copied"/"Failed" badge) with `aria-live` status. Exported `cardCount(cs: DeckCard[])` helper used by header totals and per-group badges.
- Source: session 70e4830f, 2026-05-06

### Vercel SPA Rewrite Rule (DEC-173)
`vercel.json` includes `"rewrites": [{ "source": "/((?!data/|assets/|.*\\..*).*)", "destination": "/index.html" }]`. Negative lookahead excludes `/data/...` (JSON fetches), `/assets/...` (Vite hashed assets), and dotted paths (favicon, robots.txt). Without this rule, hard-refreshing any React Router route returns Vercel's static 404 instead of the SPA.
- Source: session 8070f731, 2026-05-06
