# Grimoire v1 — Scope for "Real Handoff" Build

> **Status (final): SHIPPED.** All four surfaces are live, plus mobile Scrying. See *Final state* at the bottom of this file for what actually got built; the rest of this doc is the original planning doc kept for context.

Inventoried from the original `index.html` + `app.js` (5800 lines) by reading every relevant function. The goal: turn the three stub surfaces into real working features so the receiving engineer ships a coherent product, not a proof-of-concept plus three façades.

Format per surface: **Behavior** (what users do) → **Data** (what we read) → **In scope / Out of scope** (explicit cuts) → **Effort** (rough).

---

## 1. Shopping List — easiest, do first

### Behavior
1. **Multi-deck selection.** Pill rail of all 12 decks; click to toggle. Multi-select with visual selected state (color gradient from commander's color identity).
2. **Aggregation.** Across all selected decks, build a deduped card list. Each unique card counts as quantity 1 (you only need one copy of Sol Ring for the binder, even if it's in 6 decks). Commanders included. Basic lands excluded.
3. **Owned cards import.** User uploads a `.csv` or `.txt` of cards they own. CSV format detected automatically; falls back to one-name-per-line text. Stored in `localStorage` so it persists across sessions. Clear button to reset.
4. **Buy / Own split.** Each card lands in either "Need to Buy" or "Already Own" based on the owned set. Counts shown in summary bar (Need / Own / Total).
5. **Sort modes.** Group by type (Creature → Planeswalker → Artifact → Enchantment → Instant → Sorcery → Land, with commanders pinned at top) OR alphabetical A–Z.
6. **Per-card deck dots.** When >1 deck is selected, each row shows colored dots indicating which decks include the card (so you can see "this card serves 4 of your 5 decks").
7. **Copy buy list.** One-click copy of the "Need to Buy" list to clipboard in `Nx CardName` format (Moxfield/Archidekt-pasteable).
8. **Card hover.** Reuse the existing `GV1CardHoverLayer` — no new code needed.

### Data
- `GV1_REAL_DECKS[].deck.decklist[]` — already loaded.
- `localStorage["grimoire-owned-cards"]` — new, owned by Shopping.

### In scope
- All 8 behaviors above.

### Out of scope
- Price totals (original doesn't aggregate prices either; would need per-card price lookup which Scryfall throttling makes painful for 500+ cards).
- "Owned" CSV format negotiation — accept the same loose format the original does.
- Per-deck export (only the combined buy list).

### Effort: **~4–6 hours**
Most logic is straight ports of `aggregateShoppingCards`, `splitByOwnership`, `parseOwnedCsv`, `renderShoppingDeckChips`. The Grimoire visual scaffold already exists; we're swapping in real handlers.

---

## 2. Compare — second-easiest, do second

### Behavior
1. **All-decks table.** Every deck is a row. No filtering — the whole point is seeing all 12 at once.
2. **Columns.** Color identity pips · Deck name · Commander name · Grade (letter A+…F) · Score (0–100) · Mana Reliability · Threat Deployment · Interaction Density · Combo Consistency · Commander Independence (the 5 health components).
3. **Sortable columns.** Click any column header to sort asc/desc. Clicking the active column flips direction.
4. **Color-coded score cells.** Green ≥75, gold 50–74, red <50. Letter grade colored similarly.
5. **Loading state** while recommendations.json files load.
6. **Empty state** if no decks have health data yet.

### Data
- `GV1_REAL_DECKS[].recs.healthBaseline` — already loaded for all 12 decks. Schema confirmed: `{ score, grade, components: {manaReliability, threatDeployment, interactionDensity, comboConsistency, commanderIndependence}, weakestComponent }`.

### In scope
- All 6 behaviors above.

### Out of scope
- Side-by-side card comparison (that would be a different view; the original doesn't do it either).
- Diffing engine roles between decks (interesting future feature, not v1).
- Filter to "compare these 2/3 decks" (original shows all; we match).

### Effort: **~2–3 hours**
Pure data → table. All five health components are present in every deck's recommendations.json. The Grimoire visual scaffold has the table; we're filling it with real numbers and adding click-to-sort.

---

## 3. Scrying Pool — biggest, do third

This is two sub-features that share a surface.

### 3a. Opening Hand Simulator

#### Behavior
1. **Draw 7.** Shuffle the deck's 99-card list, draw 7. Show as a row of card images.
2. **London mulligans.** Click "Mulligan" → reshuffle, draw 7 again, but you must put N cards on the bottom (N = number of mulligans taken). Free first mulligan in Commander rules.
3. **Bottoming phase.** Click cards to mark them for the bottom; UI shows "Put N cards on bottom" and disables Keep until you've selected enough.
4. **Keep.** Lock in the hand.
5. **Hand assessment.** When kept (or on first draw), show badges:
   - Land count (good/fair/poor based on 2–4 / 1 or 5 / 0 or 6+)
   - Castability (`X/Y castable by T3`)
   - Commander timing (`~T6 commander, X% of sims cast by T6`) — pulled from `simulation.json.commanderTiming.byTurn`
   - Ramp pieces present
   - Land odds (`X% of opening hands have N lands`) — pulled from `simulation.json.openingHand.landDistribution`
6. **Card hover** on each hand card — reuse `GV1CardHoverLayer`.
7. **Reset / New Hand** when kept.

#### Data
- `GV1_REAL_DECKS[].deck.decklist` — for shuffling.
- `GV1_REAL_DECKS[].sim.openingHand.landDistribution` — already present.
- `GV1_REAL_DECKS[].sim.commanderTiming.{cmc, byTurn}` — already present.
- Card metadata (cmc, type_line, oracle_text, colors) — Scryfall cache. Already wired.

### 3b. What-If Swap Analyzer

#### Behavior
1. **Cut slot.** Dropdown grouped by type, lists every card in the current deck.
2. **Add slot.** Search input; results pulled from the recommendation pool (cards that have been pre-fetched into Scryfall cache).
3. **Live delta panel** when both slots are filled, showing:
   - Mana value change (this card's CMC delta)
   - Average mana value change for the whole deck (with before/after)
   - Land count change (if either side is a land)
   - Color balance change (which colored pip counts went up/down)
   - Card type change
   - Game Changer impact ("Removing a Game Changer: 8 → 7") — affects bracket
   - Synergy impact ("Breaks: Sol Ring + Basalt Monolith combo")
4. **Clear buttons** on each slot.

#### Data
- `currentDeck.decklist` — for the cut dropdown.
- `cardMetadataCache` (Scryfall) — for the add search and all delta math.
- `data/game-changers.json` — already in repo at top level.
- `currentDeck.synergies` — combo data; **need to verify field name in our deck.json**.

### In scope
- Hand simulator full London mulligan flow + 5 assessment badges.
- Swap analyzer with all 7 delta categories.

### Out of scope
- Bottoming after mulligans beyond what London rules require (no advanced house-rule modes).
- "Save this hand" / hand history (not in original either).
- Swap recommendations from AI (the original is user-driven; we match).
- Multi-card swap (only 1-for-1).

### Effort: **~10–14 hours**
This is the bulk of the work. Hand sim is ~4 hours (state machine + render + assessment math). Swap analyzer is ~6–8 hours (the delta computations + search UI + per-row rendering of 7 different delta types). Has the most edge cases.

---

## 4. Responsive routing — last, ~3–5 hours

### Behavior
- A media query (`max-width: 768px`) decides whether to mount the desktop layout or the mobile layout.
- **Guide:** mobile uses `GV1Mobile` (already built).
- **Shopping:** mobile gets a real layout — single-column card list, sticky deck-pill rail, summary bar collapses to a chip row.
- **Compare:** mobile gets a real layout — horizontally-scrollable table with sticky deck-name column, OR a card-stack view (one deck per card, swipe to next). Decide during build.
- **Scrying:** desktop-only. On mobile, show a "Best on desktop — this tool needs more screen than your phone has" message with a link to the Guide of the current deck.
- **Codex:** mobile gets responsive grid (already responsive-ish; verify).
- URL state (`?deck=titan-convergence&view=scrying`) survives the routing.

### In scope
- Viewport-based mount of desktop vs mobile layouts for Guide, Shopping, Compare, Codex.
- Real "best on desktop" message for Scrying.

### Out of scope
- Mobile Scrying. Hand sim and swap analyzer need horizontal real estate to be usable; cramming them into 375px is a worse experience than redirecting to desktop.

### Effort: **~3–5 hours**

---

## Total effort estimate
- Shopping: 4–6h (+ ~2h mobile)
- Compare: 2–3h (+ ~1–2h mobile)
- Scrying (hand sim + swap analyzer, desktop only): 10–14h
- Responsive routing + Codex mobile pass: 1h
- Re-verify everything as one product: 1–2h

**Sum: ~21–30 hours of focused work.** Compare to "we've already done ~30+ hours on the Guide" — so this roughly doubles the build, but takes us from "1 working surface + 3 façades" to "4 working surfaces ready for handoff."

## Decisions locked (2026-04-26)
- Constellation Map: **cut from v1.**
- Scrying: **desktop only**, mobile gets "best on desktop" message.
- Shopping + Compare: **real mobile layouts** required.
- Owned-cards: auto-detect CSV vs text (matches original).
- URL state: yes (`?deck=...&view=...`).
- Compare: show all 12 decks, no filter (matches original).
- Swap analyzer: search the local Scryfall cache only, not live API.

---

## Open questions for the user

1. **Owned-cards format** — accept Moxfield/Archidekt CSV exports? Or just a flexible `Nx Cardname` text list? (Original accepts both with auto-detect.) **My recommendation: match original — auto-detect both.**

2. **URL state** — worth doing? (`?deck=...&view=scrying`) Adds shareable links and survives reload. **My recommendation: yes, it's ~30 min and prevents user pain.**

3. **Hand simulator on mobile?** It's playable on mobile in the original, but cramped. **My recommendation: desktop-only for v1; mobile gets "best on desktop" message.**

4. **Compare table — do we need it for all decks at once, or should it be filterable?** Original shows all. **My recommendation: match original. 12 rows is fine.**

5. **Swap analyzer "Add" search pool** — in the original, it searches `cardMetadataCache` which is whatever's been pre-fetched (recommendations + decklist + a few extras). Should we be more aggressive (search all of Scryfall via API)? **My recommendation: match original. Live Scryfall search adds latency and complexity for marginal benefit.**

6. **Game Changers list** — the original references `data/game-changers.json`. Need to confirm this file exists and has the canonical Wizards game-changer list. **Action: verify before scrying work begins.**

7. **One thing not in scope I want to flag:** the original has a **"Constellation Map"** synergy visualization that we haven't ported. It's a graph of card interactions. I'd cut it from v1 — it's gorgeous but expensive to build well, and the Engine + Combos sections in the Guide already cover the same information. **My recommendation: cut it. Flag for v2.**

---

## Build order

1. **Verify game-changers.json exists** (5 min — read the file, confirm shape).
2. **Compare** (smallest, sanity-checks the data layer for all 12 decks).
3. **Shopping** (medium, validates owned-cards pattern + multi-deck state).
4. **Scrying — hand simulator** (validates shuffling + assessment math).
5. **Scrying — swap analyzer** (largest single piece; do last, after we've validated the data layer with the previous three).
6. **Responsive routing** (final wiring).
7. **Full re-verify** (verifier sweep across every surface).

Each step ends with a working, verifier-checked surface. If we discover something is bigger than expected at step N, we stop and reassess instead of half-finishing N+1.

---

## Final state (what actually shipped)

All four planned surfaces shipped, **plus** a mobile Scrying artboard that wasn't in the original plan. Below is the diff between this doc's "in scope" and the actual delivered build.

### ✅ Shipped as scoped

- **Compare** — all 12 decks, sortable on every column, color-tinted score chips, mana pips, grade badges, sticky header, click-to-navigate. Mobile: sticky deck-name column with horizontal scroll. (`gv1-compare.jsx` + `gv1-compare.css`)
- **Shopping List** — multi-deck chip selection, CSV/TXT import with auto-detect, `localStorage` persistence (`grimoire-owned-cards`), Need-to-Buy / Already-Own split, Type / A–Z sort, per-card mana cost + "across N decks" attribution, copy-to-clipboard buy list. Mobile: single-column reflow. (`gv1-shopping.jsx` + `gv1-shopping.css`)
- **Scrying — Hand Simulator** — London mulligan flow with bottom-N selection, 5-badge hand assessment, card hover, reset/new hand. (`gv1-scrying.jsx`)
- **Scrying — Swap Analyzer** — cut/add picker, live delta panel covering CMC, average CMC, lands, color balance, type, **Game Changers** (wired up against the official 51-card list in `data/game-changers.json`), broken/kept synergies. Search pulls from local Scryfall cache as scoped.
- **Game Changers list** — confirmed present at `data/game-changers.json`; baked into `gv1-game-changers.js` as `window.GV1_GAME_CHANGERS_SET` for the swap analyzer.

### ✅ Shipped above scope

- **Mobile Scrying Pool.** The original plan was "desktop only, show 'best on desktop' on mobile" (decision locked 2026-04-26). We reversed that decision once the desktop build was solid: the hand simulator and swap analyzer reflow cleanly to a single-column phone layout, and there's no reason to lock them out. The Scrying root uses `container-type: inline-size` so the same component drives both the 1440px desktop artboard and the 390px mobile artboard via `@container scrying (max-width: 720px)` rules in `gv1-scrying.css`. Full feature parity, just narrower.
- **Cross-surface deck navigation.** Compare's deck-name links call `gv1NavTo('guide')` to jump straight from the table to that deck's Guide, which wasn't in the original "click is just a sort key" plan.

### ⚠️ Cut from v1 (stayed cut)

- **Constellation Map.** Locked cut on 2026-04-26; still cut. The Engine + Combos sections of the Guide cover the same information without the graph-rendering cost.
- **URL state for `?deck=...&view=...`.** Was on the *recommended-yes* list but never wired up — the design canvas is one page with seven artboards, so deep links inside the canvas would need additional work. Worth picking up in v1.1 if shareable links matter.

### ⚠️ Known stale at handoff

- `preview.html` — still pulls flat top-level keys from the data layer rather than `DECK_FULL[i]`. Either update or delete.
- A handful of hard-coded hex values in `gv1-styles.css` (mana-value chip colors, card-art fallback gradient) should be promoted to tokens.

### Architecture decisions made during build

- **Container queries over media queries** for surface-level responsive layouts inside the design canvas. The artboard preview wraps the surface in a 1440px-wide canvas at scale, so viewport-based `@media` doesn't fire correctly for narrower artboards. Container queries fire on the artboard's actual rendered width.
- **No build step.** Hand-loaded JSX via `@babel/standalone`, cache-busted with `?v=N` query strings on script tags. This was the right call for a design-handoff artifact; the receiving team will replace this with their build pipeline.
