# Architecture

### Commander Spellbook MCP Server Structure
MCP server at `mcp-servers/commanderspellbook/` mirrors the scryfall MCP pattern:
- Single tool: `commanderspellbook_find_combos(decklist: list[str])`
- Returns `included` combos + `almost_included` with `missing_cards` and `missing_templates` computed by diffing (the API does NOT return missing_cards directly)
- Cache key = SHA256 of sorted decklist (sorting avoids order-sensitivity)
- SQLite caching with 24h TTL and WAL mode
- Retry on 429/5xx, rate limiting, empty decklist guard
- Registered via `.mcp.json` + `.claude/settings.local.json`
- Source: session ee529a54, 2026-03-17

### Commander Spellbook: missing_cards Must Be Computed
The Commander Spellbook API's `almostIncluded` response does NOT include which cards are missing. The `missing_cards` field in our tool response is computed by diffing the combo's required cards against the decklist. Template requirements (card types, generic roles) cannot be matched against card names and are reported as missing in `missing_templates`.
- Source: session ee529a54, 2026-03-17

### Simulation Script Naming: Per-Deck-ID (Migrating from Color-Identity)
New decks use per-deck-ID naming: `scripts/mana_simulation_{deck-id-underscored}.py` (e.g., `mana_simulation_verdant_tide.py`). Legacy decks retain color-identity names:
- `mana_simulation.py` → titan-convergence
- `mana_simulation_rakdos.py` → eternal-agony
- `mana_simulation_grixis.py` → dark-dominion
- `mana_simulation_golgari.py` → eternal-harvest
- `mana_simulation_jeskai.py` → planar-decree
- `mana_simulation_mono_blue.py` → azure-dominion
- `mana_simulation_azorius.py` → genesis-protocol
- `mana_simulation_jund.py` → forge-and-fury
- `mana_simulation_atraxa.py` → compleated-dominion (phyrexian-perfection was removed)
- `mana_simulation_wubrg.py` → mutant-multiplication
- `mana_simulation_the_white_forge.py` → the-white-forge (renamed from gandalf_the_white in DEC-68)
- `mana_simulation_verdant_tide.py` → verdant-tide (per-deck-ID pattern)

All scripts integrate with `export_simulation_results.py`. Interface contract per script: `build_decklist()`, `classify_cards()`, `_run_chunk()`, `merge_stats()`. Use `azure_dominion` script as template for mono-color decks.
- Sources: session c566e4f7, 2026-03-17; session e4eef813, 2026-03-20; session fd90e34c, 2026-04-06

### Card Metadata Must Be Pre-Populated for Simulation
The simulation scripts rely on `card-metadata.json` for CMC, color, and type data. Cards missing from this file cause incorrect avg CMC and land count calculations. When adding new cards to a deck, run `scripts/fetch_card_metadata.py` to regenerate the metadata before running simulations.
- Source: session c566e4f7, 2026-03-17

### Deck Naming Convention
Deck display names should be strategic/evocative, not commander-based:
- ✓ "Azure Dominion" (for Urza, Lord High Artificer)
- ✓ "Genesis Protocol" (for Shorikai, Genesis Engine)
- ✗ "Urza Deck"
The name plus a subtitle convey strategy identity in the gallery view.
- Source: session b4001091, 2026-03-17

### Polymorph/Proteus Staff Deck Constraint
In a Polymorph/Proteus Staff combo deck, creature count must be tightly controlled. Only include creatures you want to hit with Polymorph. Any additional creatures (tutors, utility creatures, recursion) break the line. Use non-creature equivalents: Conjurer's Closet (flicker), Lightning Greaves (protection), Mystical Tutor (instant find), Tezzeret the Seeker (planeswalker tutor).
- Source: session b4001091, 2026-03-17

### Owned Cards Reference File
Player's owned card collection is at `priv_data/owned_formatted.csv`. Check this file when recommending cards to identify high-value adds the player already owns (especially Game Changers). This file is gitignored and not committed to the repository.
- Source: session 594ee133, 2026-03-17

### Typed Land Arrays in Simulation Scripts
Simulation scripts maintain separate arrays for lands with basic land subtypes (e.g., `SWAMP_TYPED_LANDS`, `FOREST_TYPED_LANDS`). These arrays drive enter-tapped checks for conditional duals (Woodland Cemetery, Castle Locthwain, Blooming Marsh, Deathcap Glade, etc.). When adding a land with basic land types (e.g., Underground Mortuary has Swamp + Forest), add it to ALL matching typed arrays — missing this causes incorrect enter-tapped simulation for conditional lands.
- Source: session ccb0e567, 2026-03-18

### Shopping List Tab Architecture
The Shopping List tab (4th tab, `#view=shopping`) supports multi-deck selection with these key design decisions:
- **Dedup strategy**: max-qty-per-card across selected decks (Sol Ring appears once even if in multiple decks)
- **Deck loading**: `Promise.allSettled` (not `Promise.all`) for partial failure resilience
- **Commander access**: Read `deck.commander` / `deck.partner` directly, not `getEffectiveCommander()`
- **Provenance**: Results show which decks need each card when multiple are selected
- Source: session 405ac149, 2026-03-18

### Post-Card-Swap Workflow
When replacing a card in `deck.json`, also update:
1. `mana_simulation_{identity}.py` — check for the card in ALL of these structures:
   - `ROCK_DEFS` (mana rocks), `DORK_DEFS` (mana creatures), `CREATURE_RAMP`, `SORCERY_RAMP`, `UTILITY_ARTIFACTS`
   - `ALWAYS_TAPPED` and **typed land arrays** (`SWAMP_TYPED_LANDS`, `FOREST_TYPED_LANDS`, `R_PRODUCING_LANDS`, `B_PRODUCING_LANDS`, `G_PRODUCING_LANDS`, etc.)
   - `compute_land_mana()` named branches and `_land_play_priority()` scores
   - `_try_cast_ramp()` priority list
   - For removed cards: remove stale entries (dead code — will never be drawn but inflates numbers)
   - For added mana producers: add new entries with correct color/CMC values
2. `card-metadata.json` — regenerate via `scripts/fetch_card_metadata.py`
3. `data/simulation/{deck-id}/simulation.json` — re-export via `export_simulation_results.py`
Skipping any step leaves stale data in simulation outputs. Land and rock changes are most common omissions.
- Sources: session f4a29b04, 2026-03-17; session ccb0e567, 2026-03-18; session a1a821dd, 2026-04-06

### Synergy Source Attribution Schema and Dual Placement
Each synergy/winCondition entry has a `sources` array with objects `{type, name, url, detail}`. Source types:
- `commanderspellbook` — most authoritative; links to `https://commanderspellbook.com/combo/{id}/`
- `manual-verified` — human-reviewed; EDHREC URLs: `https://edhrec.com/combos/{card1}-{card2}`
- `ai-inferred` — deprecated; remove when a CS source exists, replace with `manual-verified` + EDHREC URL otherwise

Combos may appear in both `winConditions` and `synergies` simultaneously — this is intentional and established behavior, not a bug.
- Source: session d5616f91, 2026-03-20; session f0c90f29, 2026-03-20

### Archidekt MCP Server Integration
Archidekt deck IDs tracked in `archidekt_deck_ids.json` (project root), mapping deck slug → Archidekt integer ID. MCP server at `mcp-servers/archidekt/` exposes 3 tools: `archidekt_list_decks` (no auth needed), `archidekt_publish_deck` (auth required), `archidekt_sync_all` (auth required). Write ops require `ARCHIDEKT_AUTH_TOKEN` env var. Cards identified by Scryfall UIDs; commander designated via category with `isPremier: true`.
- Source: session a9954278, 2026-03-20

### Commander Not in Decklist; Partner Decks Have 98 Cards
The `commander` field (string, or array for partner commanders) is NOT included in the `decklist` array — it is separate. Partner commander decks have 98-card decklists (not 99). Simulation scripts and publish tools add the commander back separately when constructing card payloads.
- Source: session d5616f91, 2026-03-20

### Frontend File Structure (Post-Split)
The app was split from a single 327KB monolithic `index.html` into three separate files:
- `index.html` — 37KB (HTML shell only, ~656 lines)
- `styles.css` — 89KB (~4,500 lines of CSS)
- `app.js` — 169KB (~4,700 lines of JS)

The `<script src="app.js" defer>` attribute is critical — `defer` prevents render-blocking. Images already use `loading="lazy"` natively. Playtest/analytics JS was NOT split out because it has deep dependencies on shared state (`currentDeck`, `deckIndex`, etc.) and splitting would require a module system.
- Source: session e8e851c4, 2026-03-20

### Gallery Data Source and lastUpdatedSet Field
The gallery view reads from `deckIndex.commanders` (loaded from `data/index.json`), not from individual deck files. Any field needed for gallery display must be in BOTH `deck.json` AND `data/index.json`.

`lastUpdatedSet` was added to all 11 deck files and to `index.json` to show the most recent MTG set that contributed cards to the deck. Displayed as a small badge on gallery cards.
- Source: session de02e670, 2026-03-20

### deck.json Field: highlights[] (Formerly adds[])
The field for highlighted/recommended card additions is `highlights[]`, not `adds[]`. AGENTS.md still refers to `adds` but the actual data files use `highlights`. All 11 decks confirmed: 304 `highlights[]` entries and 152 `synergies[]` entries, each with valid `sources` arrays.
- Source: session e4eef813, 2026-03-20

### Light Theme: Warm Cream/Parchment
The app's visual theme was migrated from dark navy to warm cream/parchment. Key CSS custom property values:
```css
--bg-deep: #FAF7F2;
--bg-primary: #FAF7F2;
--bg-elevated: #F5F0E8;
--border-subtle: #E8E0D4;
--text-primary: #2C2420;
--text-secondary: #5C534A;
--accent-purple: #D4853A;   /* kept as "accent-purple" to minimize diff; actually amber */
--accent-red: #C23028;
--accent-green: #2C7A3E;
```
**Playtest view (battlefield) is intentionally kept dark** — it's a play mat and dark is correct. Only gallery, grimoire, scrying pool, and shopping list use the light theme. Commander background filter for light theme: `blur(40px) brightness(1.4) saturate(0.3) opacity(0.15)`.
- Source: session 8cc28aff, 2026-03-20

### Constellation Map SVG
The synergy constellation map uses a hardcoded coordinate space: `W = 800, H = 500`. The SVG has `viewBox="0 0 800 500"` with `width="100%"` — it scales responsively. Labels are 9px font size (very small at mobile widths). On mobile, the SVG container height is reduced via media query. Touch support must be added alongside hover events since `mouseenter`/`mouseleave` don't fire on touch devices.
- Source: session e8e851c4, 2026-03-20

### Shopping List: .shopping-controls CSS Wrapper
Deck selectors and the owned cards bar are grouped inside a `.shopping-controls` wrapper with `gap: 16px` (14px on mobile). The parent `.shopping-view` keeps its `32px` gap for separation between the controls group and content sections below. This two-level gap hierarchy gives visual breathing room between control elements (tight, 16px) and content sections (loose, 32px).
- Source: DEC-36 session, 2026-03-21

### Pencil Design: Shopping List Has Two Frames
The Pencil design file maintains two distinct frames for the Shopping List: a "Full Page" frame (shows the complete page view including the owned cards import widget) and a "component" frame (the reusable component view). Both frames must be kept in sync when UI changes are made — the owned cards import widget was historically missing from the component frame, causing design/implementation drift.
- Source: DEC-36 session, 2026-03-21

### Opening Hand Simulator: Implementation Details
Lives as a section inside `#analytics-view` (Scrying Pool tab), not a standalone view. Uses Fisher-Yates shuffle, draws 7 cards, implements London mulligan (put N cards on bottom before redraw). Hand quality assessment compares hand characteristics against `simulation.json` baselines: land count, commander castability timing, ramp count, color distribution probability. State is reset when the selected deck changes (`currentDeck` swap). Global (top-level) functions are used for onclick handlers since inline `onclick="fn()"` attributes can't reference closure-scoped functions.
- Source: session 9c9da508, 2026-03-21

### What-If Swap Analyzer: Implementation Details
Lives as a section inside `#analytics-view` (Scrying Pool tab). Cut slot is a `<select>` dropdown populated from the current decklist, grouped by card type. Add slot is a text search against `cardMetadataCache` (the pre-loaded local metadata for all 633 cards across all decks). Delta display shows: mana value change, avg CMC impact on deck, land count change, color identity balance shift, and card type change. Synergy impact detects when a cut card appears in the deck's `synergies[]` pairs. Bracket impact flags if the cut/add crosses a Game Changer boundary using runtime-loaded `data/game-changers.json`.
- Source: session 5931830a, 2026-03-22

### game-changers.json: Runtime-Loaded, Not Preloaded
`data/game-changers.json` is NOT loaded at app startup. It is fetched at runtime when the What-If Swap Analyzer initializes (on first deck selection with the analyzer visible). Cache it after the first load to avoid repeated fetches. This differs from `card-metadata.json` which is loaded eagerly at startup.
- Source: session 5931830a, 2026-03-22

### Data Tools Strategy: Three-Tier Architecture
The Scrying Pool analytics section follows a tiered roadmap (all client-side, curated decks only, no backend):
- **Tier 1** (shipped): Enhanced deck dashboard — type distribution, mana curve, color pip analysis, land quality rating, commander timing from simulation data
- **Tier 2A** (shipped): Opening Hand Simulator — London mulligan, hand assessment vs simulation baselines
- **Tier 2B** (shipped): What-If Swap Analyzer — cut/add delta display, bracket impact, synergy detection
- **Tier 3A** (planned): Goldfish simulator — Monte Carlo avg turn to cast commander, avg turn to hit N mana
- **Tier 3B** (planned): Recommendation engine — card suggestions from pre-computed synergy data
- **Tier 3C** (planned): Combo assembly probability from simulation data
No backend: all data is pre-computed at build/run time from the existing `simulation.json` files.
- Source: session b27105d7, 2026-03-21

### Agent Instruction Files
Paperclip agent instruction files are stored under `agents/` in the project root:
- `agents/sim-eng/AGENTS.md` — Simulation Engineer (Codex/gpt-5.4): Python Monte Carlo sims, mana reliability metrics, Deck Health Score
- `agents/interactive-eng/AGENTS.md` — Interactive Tools Engineer (Claude): Opening Hand Sim, What-If Analyzer, browser-facing interactive features
- `agents/founding-eng/AGENTS.md` — Founding Engineer (Claude): General app.js engineering, UI features, bug fixes
- `agents/ceo/AGENTS.md` — CEO agent instruction file
- `agents/design-eng/AGENTS.md` — Design Engineer instruction file
These files are committed to main and used as `instructionsFilePath` in each agent's Paperclip adapter config.
- Sources: session 0f8d4b67, 2026-03-22; session 8b46df52, 2026-03-23

### Deck Count and Catalog
As of 2026-04-07, 12 decks are in the data directory. `data/index.json` order: titan-convergence, eternal-agony, dark-dominion, mutant-multiplication, eternal-harvest, the-white-forge, azure-dominion, genesis-protocol, compleated-dominion, forge-and-fury, verdant-tide, planar-decree. Changes in DEC-68: phyrexian-perfection removed entirely; gandalf-the-white renamed to the-white-forge; deck order resequenced. `verdant-tide` (Eladamri, Korvecdal — mono-green Elfball/Token Army, Bracket 4, lastUpdatedSet: Tarkir: Dragonstorm) added as deck 13, then catalog dropped to 12 with phyrexian-perfection removal.
- Sources: session 4d43917b, 2026-03-27; session fd90e34c, 2026-04-06; session c4b05b83, 2026-04-07

### Upgrade Paths View: Card Hover System
Upgrade paths card hover system supports three layers with explicit priority (highest first):
1. **Rationale card** — `<span class="upgrade-rationale-card" data-card-name="...">` wrapping card names from `comboDetails.cardsInDeck`, generated by `linkifyRationaleCards(text, cardsInDeck)`
2. **Swap-cut card** — `.upgrade-swap-cut` span carries `data-card-name` attribute set on render
3. **Upgrade card** — `.upgrade-card` element is the base `data-card-name` layer

Priority enforced via `e.target.closest()` chain in a unified mouseover/click handler. `lastHoveredUpgradeCard` variable deduplicates `showCardPreview` calls — prevents flicker when the cursor moves within the same `.upgrade-card` boundary without leaving it. Applied to both desktop mouseover and mobile click handlers.
- Source: session 8b46df52, 2026-03-23
