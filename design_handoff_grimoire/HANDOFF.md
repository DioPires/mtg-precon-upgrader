# Grimoire v1 — Claude Code Handoff

A redesign of an MTG Commander deck companion. This bundle hands off **seven working surfaces** to a developer for production implementation.

---

## What's in the box

```
design_handoff_grimoire/
├── HANDOFF.md              ← you are here (read this first)
├── prototype/              ← the design references — see prototype/README.md
│   ├── Grimoire v1.html    ← entry point; open in a browser to see it
│   ├── README.md           ← detailed architecture, file map, components, tokens
│   ├── SCOPE.md            ← locked design decisions + behavior specs per surface
│   ├── components.api.js   ← public component inventory + JSDoc prop contracts
│   └── gv1-*.{jsx,css,js}  ← the implementation
└── source-data/            ← canonical data the prototype derives from
    ├── game-changers.json  ← official MTG Commander Game Changers (51 cards)
    └── commanders/         ← per-deck source JSON (deck.json, recommendations.json,
                              simulation.json, metrics.json, candidates.json)
```

---

## What this is — and isn't

**The files in `prototype/` are design references, not production code.** They are HTML+JSX+CSS prototypes that demonstrate the intended look, layout, behavior, and interactions in pixel detail. Every surface is interactive and renders from real data — there are no stubs.

**Your task is to recreate these designs in your target codebase**, using its established framework, component library, design system primitives, and build pipeline. If no codebase exists yet, pick the framework appropriate for the project (likely React + Vite or Next.js, given the prototype's shape) and implement the designs there.

**Do not lift the prototype's loading strategy.** It hand-loads JSX through `@babel/standalone` with cache-busting `?v=N` query strings — that's correct for a design-handoff artifact, wrong for production. You'll want a real bundler (Vite, Next, Remix, etc.) and proper data fetching.

---

## Fidelity

**High-fidelity.** Every color, font, weight, spacing value, border radius, animation duration, and easing curve is final. The receiving developer should reproduce the prototype pixel-for-pixel using their codebase's conventions. All design tokens are factored into `prototype/gv1-tokens.css` — port them as-is into your token system (CSS variables, Tailwind config, Style Dictionary, whatever you use).

---

## What ships (seven surfaces)

| # | Surface | Per-deck or cross-deck? | Source files |
|---|---|---|---|
| 1 | Deck Guide (hero · commander · win-cons · engine · combos · § V Apothecary · performance · decklist) | Per-deck | `gv1-chrome.jsx` + `gv1-engine.jsx` + `gv1-perf.jsx` |
| 2 | Codex Overview (all 12 decks, sortable/filterable) | Cross-deck | `gv1-codex.jsx` |
| 3 | Mobile Guide (iPhone-bezel artboard) | Per-deck | `gv1-mobile.jsx` |
| 4 | Compare (all 12 decks, sortable on every column) | Cross-deck | `gv1-compare.jsx` |
| 5 | Shopping List (multi-deck aggregation, owned-cards CSV import, copy buy-list) | Cross-deck | `gv1-shopping.jsx` |
| 6 | Scrying Pool — desktop (hand simulator + swap analyzer + KPIs) | Per-deck | `gv1-scrying.jsx` |
| 7 | Scrying Pool — mobile (full feature parity via container queries) | Per-deck | `gv1-scrying.jsx` (same component) |

Plus a global card-hover popover (`gv1-cardhover.jsx`) that intercepts any `[data-card-name]` mouseover and shows the full Scryfall card frame.

**For complete behavior specs of each surface, read `prototype/SCOPE.md`.** It documents every interaction, data flow, edge case, and explicit cut.

---

## How to read this handoff

1. **Open `prototype/Grimoire v1.html`** in a browser. Pan/zoom the canvas; click into each artboard. Try the deck selector — Guide, Mobile, and Scrying all react in lockstep. Hover any card name anywhere → Scryfall popover.
2. **Read `prototype/README.md`.** It's the developer-facing tour: file map, architecture, data flow, design tokens, component inventory, accessibility notes.
3. **Read `prototype/SCOPE.md`.** Locked behavior specs per surface, with explicit "in scope / out of scope" cuts. This is what you're committing to ship.
4. **Read `prototype/components.api.js`.** Public component inventory with JSDoc prop contracts.
5. **Inspect `source-data/`** for the canonical data shape. The prototype inlines this into `gv1-real-decks.js` for ease of loading; production should fetch the JSON files (or whatever your data layer is) and normalize through the same shape `gv1-data.js` exposes.

---

## Architecture cheat-sheet (full version in `prototype/README.md`)

**Data flow:**
```
deck.json              ─┐
recommendations.json   ─┤
simulation.json        ─┼─→ normalization → DECK_FULL[]   (component-facing shape)
metrics.json           ─┤
candidates.json        ─┘
```

The only shape components consume is `DECK_FULL[]`. If a field is missing on a deck, the normalization layer (`gv1-data.js`) handles the fallback — components assume `DECK_FULL` is well-formed.

**Reactive selection:** a single `useState` at the top of `App` in `Grimoire v1.html`. Guide, Mobile, and both Scrying artboards read from it. Codex / Shopping / Compare are multi-deck by design (they don't subscribe). Compare's deck-name links navigate to that deck's Guide.

**Card art + prices:** `useCard(name)` (in `gv1-cards.js`) is a hook that subscribes to a shared in-memory Scryfall cache. First subscriber for a name enqueues a fetch (≥80ms apart, deduped). Loading and empty states use primitives in `gv1-states.css` — components don't reimplement skeletons.

**Mobile responsive:** Scrying uses `@container` queries (declared on `[data-gv1-screen="scrying"]`) rather than `@media`, so the same component reflows correctly inside the design canvas's narrow artboard *and* on real phones. If you keep the canvas presentation, follow the same pattern for new surfaces.

---

## Design tokens (port these into your token system)

Layered as **primitives → semantic → component**. Components reference *semantic* tokens; only semantic tokens reference primitives.

- **Color primitives:** `--gv1-ink-blue-{600..900}`, `--gv1-parchment-{100..600}`, `--gv1-rune-{100..900}` (green accent), `--gv1-gold-{300,500,700}`, `--gv1-mana-{w,u,b,r,g,c}` + matching `*-stroke`, `--gv1-status-{warn,error}`.
- **Color semantic:** `--gv1-bg`, `--gv1-bg-2`, `--gv1-bg-3`, `--gv1-bg-elevated`, `--gv1-ink`, `--gv1-ink-bright`, `--gv1-ink-dim`, `--gv1-ink-dimmer`, `--gv1-rune`, `--gv1-rune-dim`, `--gv1-rune-bright`, `--gv1-gold`, `--gv1-line`, `--gv1-line-strong`, `--gv1-line-rune`, `--gv1-focus-ring`, `--gv1-focus-bg`, `--gv1-selection-bg`, `--gv1-selection-fg`, `--gv1-grid`.
- **Typography:** `IM Fell English` (display serif) + `IM Fell DW Pica` (alt serif) + `JetBrains Mono`. Loaded via Google Fonts. There is no numeric font-size scale in tokens — sizes are set per-component via utility classes (`.gv1-serif-xl`, `.gv1-mono-xs`, etc.) in `gv1-styles.css`. **Promoting these to a numeric scale is a recommended early refactor.**
- **Space, radius, motion, z-index:** `--gv1-radius-{1,2,3,...}`, `--gv1-duration-{quick,base,slow}`, `--gv1-ease-{out,in,in-out}`, `--gv1-transition-{quick,base}`, `--gv1-z-{base,content,sticky,overlay,popover,toast,modal}`.

A handful of hard-coded hex values still live in `gv1-styles.css` (mana-value chip colors at `.gv1-mv-c`, the card-art fallback gradient) — promote them to tokens during your port.

Full source of truth: `prototype/gv1-tokens.css`.

---

## Components (port these to your component library)

See `prototype/components.api.js` for full prop contracts. Atoms never fetch; molecules use hooks; organisms own layout.

**Hook:** `useCard(name)` → Scryfall cache subscription
**Atoms:** `ManaCost`, `GV1ManaPips`
**Molecules:** `CardTile`, `GV1CommanderArt`
**Organisms (deck-guide sections):** `GV1Topbar`, `GV1Hero`, `GV1DeckSelector`, `GV1Commander`, `GV1WinCons` (§ II), `GV1Engine` (§ III), `GV1Combos` (§ IV), `GV1Apothecary` (§ V), `GV1Performance` (§ VI), `GV1Decklist` (§ VII)
**Artboard roots:** `GV1Codex`, `GV1Mobile`, `GV1Compare`, `GV1Shopping`, `GV1Scrying`
**Layout / global:** `GV1CardHoverLayer` (mount once near root)

> Patterns visible in the design but not yet factored into standalone components: `Sigil`, `MonoLabel`, `RuneRule`, `PriceChip`, `StatBlock`, `SwapRow`. Factoring these is the natural next refactor after the initial port.

---

## Accessibility (already wired; preserve through the port)

- All interactive elements keyboard-reachable; focus rings come from `--gv1-focus-ring`.
- Landmarks (`<header>`, `<main>`, `<nav>`, `<section>`) on every artboard root.
- Engine tabs implement the WAI-ARIA tablist pattern (arrow keys, Home/End, `aria-selected`, roving tabindex).
- Card art has `alt` from card name; decorative sigils are `aria-hidden`.
- Color is never the sole channel — every state pairs color with iconography or text.
- `prefers-reduced-motion` disables non-essential animations.

---

## Known issues at handoff (read before you start)

These are flagged in `prototype/SCOPE.md` § "Known stale at handoff" — picked up here for visibility:

1. **`prototype/preview.html` is stale.** It still pulls flat top-level keys from the data layer rather than `DECK_FULL[i]`. Either update or delete during your port.
2. **Hard-coded hex values in `gv1-styles.css`** — mana-value chip colors at `.gv1-mv-c`, card-art fallback gradient. Promote to tokens.
3. **No URL state.** The design canvas is one page with seven artboards; deep links inside the canvas (`?deck=...&view=...`) were planned-but-cut for v1. Worth picking up if shareable links matter.
4. **No font-size scale.** Sizes set per-component via utility classes. Promote to numeric scale during your port.
5. **Scryfall calls happen at component mount.** No SSR / prefetch / service worker. Your production fetch strategy is up to you.

---

## Suggested implementation order

1. **Token port.** Get `gv1-tokens.css` into your design-token pipeline first. Everything else cascades from this.
2. **Atoms + molecules.** `ManaCost`, `GV1ManaPips`, `CardTile`, `GV1CommanderArt`, plus the `useCard` hook (or your equivalent data binding). These are reused everywhere.
3. **Card hover popover.** Mount once near root.
4. **Deck Guide.** The most complex surface; gets you the deck-selector reactive pattern.
5. **Codex.** Cheap to build once Guide is real; validates the multi-deck data layer.
6. **Compare** → **Shopping** → **Scrying.** In that order — each is more state-heavy than the last. Scrying has the most edge cases; do it after the others.
7. **Mobile reflows.** Container queries for in-canvas; media queries fine for production at real phone widths.

---

That's the handoff. The prototype's `README.md` and `SCOPE.md` are the spec — read them in full before writing code.
