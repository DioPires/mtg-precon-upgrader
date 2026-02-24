# Major Overhaul: Convert to Commander-Only App (No Tiers/Upgrades)

## Context

The app currently supports 3 precon upgrade guides + 1 commander deck, each with multiple tiers. The user wants to simplify to 3 standalone commander decks with **no tier, upgrade, or precon concept**:

1. **Titan Convergence** (from Eldrazi Unbound `full` tier) — Zhulodok, Void Gorger
2. **Eternal Agony** (from Endless Punishment `full` tier) — The Lord of Pain
3. **Dark Dominion** (from Sauron `full` tier) — Sauron, the Dark Lord

Remove: Necron Dynasties, all other tiers, all precon/upgrade machinery, bracket targets from AGENTS.md.

---

## New Data Structure (Flat — No `upgrades` Wrapper)

```json
{
  "id": "titan-convergence",
  "type": "commander",
  "name": "Titan Convergence",
  "subtitle": "Cascading Inevitability",
  "commander": "Zhulodok, Void Gorger",
  "cost": "$200-350",
  "bracket": "4",
  "gameChangers": 2,
  "sources": [...],
  "guideContent": { "strategyOverview": "..." },
  "addCategories": [...],
  "adds": [...],
  "synergies": [...],
  "decklist": [{ "name": "Card", "type": "Creature" }, ...]
}
```

All tier-level fields (`cost`, `bracket`, `gameChangers`, `addCategories`, `adds`, `synergies`, `decklist`, `sources`) move to deck root. No `upgrades` key, no `baseDeck`, no `cuts`, no `currentBracket`, no `targetBracket`.

Note: `guideContent.deckCategories` is dead code in the frontend (defined in `renderDeckThemeGroups()` at line 6275 but never called). Skip it for new decks. The `addCategories` at root level is what the UI actually renders as "Deck Themes".

---

## Step 1: Compute Decklists for Titan Convergence & Eternal Agony

Neither precon tier has a `decklist` array. Must compute `baseDeck - cuts + adds`.

**Titan Convergence** (Eldrazi Unbound):
- `baseDeck`: 86 entries (incl. Wastes x15 = 100 total cards incl. commander candidates)
- Minus `upgrades.full.cuts` (47 tier-specific cuts, incl. Wastes qty 5 reduction = 51 cards removed). Note: the `full` tier has its own `cuts` array that OVERRIDES the shared deck-level cuts (code: `upgrade.cuts || currentPrecon.cuts`)
- Plus `upgrades.full.adds` (51 adds)
- Commander = Zhulodok, Void Gorger (tier-level `commander` field) — excluded from decklist
- Math: 100 - 1 (Zhulodok) - 51 (cuts) + 51 (adds) = 99. Verified.

**Eternal Agony** (Endless Punishment):
- `baseDeck`: 86 entries (incl. Swamp x8, Mountain x8 = 100 total cards incl. commander)
- Minus `upgrades.full.cuts` (46 entries, 46 removals)
- Plus `upgrades.full.adds` (46 adds)
- Commander = The Lord of Pain (deck-level) — excluded from decklist
- Math: 100 - 1 (The Lord of Pain) - 46 (cuts) + 46 (adds) = 99. Verified.

Approach: Write a Node.js script to compute decklists, output JSON arrays, verify counts.

## Step 2: Create/Update Commander Deck Files

### Create `data/commanders/titan-convergence/deck.json`
- Flatten Eldrazi Unbound `upgrades.full` fields to root
- `guideContent.strategyOverview`: Use tier `description` field ("Bracket 4 Zhulodok build with infinite mana combos...") as base, strip "48 swaps turn the precon into" language. Do NOT use deck-level strategyOverview ("This upgrade transforms Eldrazi Unbound from a casual Bracket 1-2 precon...") — that's precon-focused.
- `addCategories` from existing tier (`upgrades.full.addCategories`)
- Computed `decklist` from Step 1
- Drop: `baseDeck`, `cuts`, `cutCategories`, `currentBracket`, `targetBracket`, `upgrades` wrapper

### Create `data/commanders/eternal-agony/deck.json`
- Flatten Endless Punishment `upgrades.full` fields to root
- Rewrite `guideContent.strategyOverview` (currently references "upgrade" and precon context)
- `addCategories` from `upgrades.full.addCategories`
- `cutCategories` from `upgrades.full.cutCategories` → rename to `deckCategories` (dead code, but keep for data consistency)
- Computed `decklist`

### Rewrite `data/commanders/sauron-the-dark-lord/deck.json`
- Flatten `upgrades.full` (Dark Dominion) to root
- Delete `upgrades.midrange` and `upgrades.budget`
- Remove `upgrades` wrapper entirely
- Remove `alternateCommander` field
- Scrub `guideContent.strategyOverview` — remove "Three tiers are available: Dark Dominion...Shadow Aristocrats...Mordor Rising" text
- Remove `guideContent.deckCategories[3]` ("Sacrifice & Drain") entirely — those cards (Mirkwood Bats, Zulaport Cutthroat, Blood Artist, Goblin Bombardment, Ashnod's Altar, Pitiless Plunderer) are NOT in the Dark Dominion decklist; they belong to the removed Shadow Aristocrats tier

## Step 3: Update `data/index.json`

```json
{
  "commanders": [
    { "id": "titan-convergence", "name": "Titan Convergence", "commander": "Zhulodok, Void Gorger", "colors": ["C"], "theme": "Eldrazi Cascade" },
    { "id": "eternal-agony", "name": "Eternal Agony", "commander": "The Lord of Pain", "colors": ["B", "R"], "theme": "Group Slug" },
    { "id": "sauron-the-dark-lord", "name": "Dark Dominion", "commander": "Sauron, the Dark Lord", "colors": ["U", "B", "R"], "theme": "Amass / Orc Tribal" }
  ]
}
```

No `precons` key.

## Step 4: Refactor Frontend (`index.html`)

### 4a: Remove `currentUpgrade` and tier machinery (~35 references)

**Core pattern**: Every `currentPrecon.upgrades[currentUpgrade]` → `currentPrecon`

Delete:
- `let currentUpgrade = 'full'` (line 4778)
- `generateTabs()` function (line 5812-5851) and its call (line 5970)
- `handleTabClick()` function (line 5853-5869)
- Tier tab HTML: `.tier-tabs` container (line 4132)
- Tier tab CSS: `.tier-tabs` rules (line 720, 1400-1412)
- Tier sources CSS/HTML (lines 1255-1318, 4172-4177) — keep if sources are still rendered, just remove "tier" naming

Replace `const upgrade = currentPrecon.upgrades[currentUpgrade]` with `currentPrecon` at ~15 locations:
- `renderDeckStats()` (5341), `renderDeckList()` (6027), `renderGuide()` (6176), `renderContent()` (6155), `generateDecklistExport()` (6676), `renderShoppingList()` (6808), `renderSynergies()`-related (6953), `getEffectiveCommander()` (7927), `buildPlaytestDeck()` (7934), `initPlaytest()` (8000), `renderBracketVisualization()` (4905), share/export functions (7248, 7265, 7290, 7438, 7450)

### 4b: Simplify `getEffectiveCommander()`
From: `return upgrade?.commander || currentPrecon.commander`
To: `return currentPrecon.commander`

### 4c: Remove bracket visualization "current → target" logic
- `renderBracketVisualization()` — use `currentPrecon.bracket` directly. No `currentBracket` or `targetBracket` lookup. Just display the deck's bracket.

### 4d: Flatten selector (no optgroups)
- `populatePreconSelector()` — remove "Precon Upgrades" and "Commander Decks" optgroups. Iterate `preconIndex.commanders` directly as flat `<option>` elements.
- `loadPreconData()` (line 5896-5904) — always use `commanders/` folder. Simplify: remove `isCmd` check, hardcode `commanders`.

### 4e: Remove Rankings view entirely
The "Creator Rankings" tab (line 4048-4053) shows precon rankings from `creator-rankings.json` — no longer relevant.
- Remove rankings tab button HTML (line 4048-4053)
- Remove rankings view HTML section (line 4490+)
- Remove rankings CSS (lines 2849-3228)
- Remove `loadRankingsData()`, `renderRankings()`, `loadAndRenderRankings()` JS functions
- Remove rankings handling from `switchView()` (line 7822-7827)
- Remove rankings URL hash check in `initializeApp()` (line 8634-8638)
- Remove `rankingsData`, `rankingsLoaded` variables (line 4839)

### 4f: Clean up URL hash and preferences
- Remove `tier=` from URL hash building (lines 6659, 7438, 7836)
- Remove `lastTier` from saved preferences (line 7164)
- Remove tier from hash parsing and restoration (lines 8650, 8667, 8681)
- Remove `&tier=${...}` from playtest URL (line 7836)

### 4g: Remove precon-specific rendering (dead code cleanup)
- Remove `else` branches in `renderGuide()`, `renderDeckList()`, `renderDeckStats()`, `generateDecklistExport()` that handle baseDeck+cuts
- Remove `applyBaseDeckCuts()` function (line 4867-4876)
- Remove `buildCutMap()` function (line 4860-4864)
- Remove `renderCutGroups()` function (line 6251-6273) — only used in precon path
- Remove `renderDeckThemeGroups()` function (line 6275-6295) — dead code, never called
- Remove `isCommanderDeck()` function — always true now. Replace all `if (isCmd)` conditionals with just the `isCmd=true` branch.
- Update "Precon Upgrades" empty state text (line 4590)

### 4j: Update user-facing text
- `<title>` (line 6): "MTG Precon Upgrade Guides" → "MTG Commander Deck Guides" (or similar)
- `<h1>` (line 4033): same
- Shopping list header (line 4209): merge `shopping-list-precon`/`shopping-list-tier` into single span showing deck name. Update JS (line 7294-7295) to populate one element.
- Shopping list footer (line 4230): "Generated from MTG Precon Upgrade Guide" → update
- Loading text (line 4585): "Loading precon data..." → "Loading deck data..."
- Note: internal JS variable names (`preconIndex`, `loadedPrecons`, `currentPrecon`, `preconSelect`) left unchanged — internal naming, no UX impact.

### 4h: Simplify `selectPrecon()` function
- Remove `generateTabs()` call
- `currentUpgrade` references → remove entirely

### 4i: Update playtest state check
- `updatePlaytestTabState()` (line 8606): `if (currentPrecon && currentUpgrade)` → `if (currentPrecon)`

## Step 5: Delete Removed Data

```
rm -rf data/precons/
rm data/creator-rankings.json
```

## Step 6: Delete Docs and Stale Directories

```
rm -rf docs/
rm -rf analysis-01/
```

`docs/` only contains subdirectories for the 3 precons + research — nothing to preserve.
`analysis-01/` contains old codebase review/implementation plans from Feb 10 — stale, references precon structure throughout.

## Step 7: Update AGENTS.md

Rewrite data structure and rules sections:
- Delete "Precon Data Structure" section
- Delete "Precon Upgrades" subsection under "Upgrade Guide Rules"
- Delete "Tier Philosophy" section
- Delete bracket target rules, GC limits per bracket, tier count requirements
- Rewrite "Commander Deck Data Structure" with new flat structure (no `upgrades` wrapper, no tiers)
- Rewrite "Shared Rules" — remove tier-related rules
- Remove `data/precons/{id}/deck.json` from Key Files
- Rewrite "Add a New Commander Deck" task for flat structure
- Delete "Add a New Precon Guide" task
- Update "Source Attribution Schema" — remove `upgrades.{tier}` references
- Keep "Research Upgrades" task (still useful for deck research workflow)

## Step 8: Update CLAUDE.md and README.md

**CLAUDE.md**: Minimal — just references AGENTS.md. Remove any stale bracket/tier text if present.

**README.md**: Major rewrite needed. Currently references precons, tiers, upgrades, bracket targets, midrange/full upgrade paths. Rewrite to describe 3 commander decks, flat structure, no tiers. Update directory structure, featured decks list, and bracket section.

## Step 9: Update `scripts/fetch_card_metadata.py`

Line 25-26 references `DATA_DIR.glob("precons/*/deck.json")`. Remove precons glob, keep only `commanders/*/deck.json`.

Also update `collect_card_names()` (lines 21-56) to read the new flat structure:
- Remove `baseDeck` iteration (lines 37-39)
- Remove top-level `cuts` iteration (lines 41-43)
- Remove `upgrades` tier iteration (lines 45-55)
- Add: iterate `deck.get("adds", [])` and `deck.get("decklist", [])` at root level
- Note: synergies have `cards` arrays (not `name` fields), but synergy cards are always a subset of adds/decklist — no need to collect separately

## Step 10: Update simulation scripts

All 3 simulation scripts need updates for the new flat data structure:

### `mana_simulation.py` (Titan Convergence)
- **`DECK_FILE`** (line 18): `"precons" / "eldrazi-unbound"` → `"commanders" / "titan-convergence"`
- **`build_decklist()`** (lines 90-125): currently computes `baseDeck - cuts + adds` via `deck_data["upgrades"]["full"]`. Simplify to iterate `deck_data["decklist"]` directly (flat array of `{name, type}` objects with optional `qty`)
- Update docstring (lines 91-93) to remove baseDeck/cuts reference

### `mana_simulation_rakdos.py` (Eternal Agony)
- **`DECK_FILE`** (line 21): `"precons" / "endless-punishment"` → `"commanders" / "eternal-agony"`
- **`build_decklist()`** (lines 104-133): same pattern — simplify to iterate `deck_data["decklist"]`
- Update docstring

### `mana_simulation_grixis.py` (Dark Dominion)
- **`DECK_FILE`** (line 21): path unchanged (`commanders/sauron-the-dark-lord`)
- **`build_decklist()`** (lines 283-291): currently reads `deck_data["upgrades"]["full"]["decklist"]`. Change to `deck_data["decklist"]`
- Update docstring

## Execution Order

1. Step 1 (compute decklists) — depends on existing precon data still being present
2. Steps 2-3 (create new deck files, update index) — can run after Step 1
3. Step 4 (frontend refactor) — independent of data, can run in parallel with Step 2-3
4. Steps 5-6 (delete old data/docs) — must run AFTER Steps 2-3
5. Steps 7-10 (docs/scripts/simulations) — independent, can run last

## Verification

1. `python3 -m http.server` in project root
2. Dropdown: 3 decks in flat list — Titan Convergence, Eternal Agony, Dark Dominion
3. No "Creator Rankings" tab visible
4. No tier tabs visible on any deck
5. Each deck:
   - Commander name correct (Zhulodok / The Lord of Pain / Sauron)
   - "Deck Themes" section renders with addCategories
   - Cuts section hidden (CSS `body.commander-deck .guide-section.cuts`)
   - Full decklist renders with count = 100 (99 + commander)
   - Synergies render
   - Mana curve / deck stats render
   - Sources accordion works
6. Playtest mode works for each deck
7. Shopping list prints correctly
8. Share URL works (no `tier=` param, format: `#precon=titan-convergence`)
9. Export (MTGO/Arena) works
10. No console errors
11. URL `#precon=sauron-the-dark-lord` still loads correctly (ID preserved)
12. Run each simulation script to verify it loads the new flat data correctly:
    - `python3 scripts/mana_simulation.py` (Titan Convergence — 99 cards)
    - `python3 scripts/mana_simulation_rakdos.py` (Eternal Agony — 99 cards)
    - `python3 scripts/mana_simulation_grixis.py` (Dark Dominion — 99 cards)
13. Run `python3 scripts/fetch_card_metadata.py` to verify it collects card names from new flat structure

## Files Summary

| File | Action |
|------|--------|
| `data/index.json` | Rewrite — flat commanders list |
| `data/commanders/titan-convergence/deck.json` | **Create** — flat commander deck |
| `data/commanders/eternal-agony/deck.json` | **Create** — flat commander deck |
| `data/commanders/sauron-the-dark-lord/deck.json` | **Rewrite** — flatten, remove tiers |
| `index.html` | **Major edit** — remove tier/upgrade/rankings machinery, flat selector, clean dead code |
| `AGENTS.md` | **Rewrite** — remove precon/tier/bracket rules, new flat data structure |
| `CLAUDE.md` | Minor edit if needed |
| `README.md` | **Rewrite** — remove precon/tier/upgrade references, describe commander decks |
| `scripts/fetch_card_metadata.py` | Edit — remove precon glob, update to flat structure |
| `scripts/mana_simulation.py` | Edit — update path to `titan-convergence`, simplify `build_decklist()` |
| `scripts/mana_simulation_rakdos.py` | Edit — update path to `eternal-agony`, simplify `build_decklist()` |
| `scripts/mana_simulation_grixis.py` | Edit — simplify `build_decklist()` (remove `upgrades` wrapper) |
| `data/precons/` | **Delete** entire directory tree |
| `data/creator-rankings.json` | **Delete** |
| `docs/` | **Delete** entire directory (only contains precon subdirs + research) |
| `analysis-01/` | **Delete** — stale analysis files |
