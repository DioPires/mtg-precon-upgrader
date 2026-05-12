# Domain Knowledge

### B Design Token System (Warm Cream / Manuscript Theme)
Full palette for the "B direction" redesign:
- **Backgrounds:** `#FAF7F2` (page bg), `#F5F0E8` (card/panel surface), `#E8E0D4` (subtle border)
- **Accents:** `#D4853A` (amber/copper — primary accent), `#2C7A3E` (green — positive/stat), `#C23028` (red — warning/combo)
- **Text:** `#2C2420` (dark primary), `#5C534A` (secondary), `#8A7F74` (muted)
- **Typography:** Playfair Display (headings), Inter (body), Fira Code (data/numbers)
- **Spacing:** 24px section gaps, 16px card padding, 8px between rows
- Source: session a8e6cc42, 2026-03-20; session 4a7404a5, 2026-03-20

### Typography Migration (A → B Direction)
Direction A used: Cinzel (headings), Source Sans 3 (body).
Direction B uses: Playfair Display (headings), Inter (body), Fira Code for numeric data.
Both Playfair Display + Inter must be loaded via Google Fonts `<link>` in `index.html`.
- Source: session a8e6cc42, 2026-03-20

### Scrying Pool — KPI Donut Chart Colors
Three donut ring charts in Scrying Pool view use:
- Mana efficiency: purple `#7B5EA7`
- Consistency: green `#2C7A3E`
- Speed: amber `#D4853A`
Ring background (track): `#E8E0D4`. Values in Fira Code 28px bold.
- Source: session 4a7404a5, 2026-03-20

### Scrying Pool — Mana Chart Style
Amber `#D4853A` stroke line, area fill at 0.1 opacity, dashed grid lines (`stroke-dasharray: 4 4`, color `#E8E0D4`), dots radius 4px. X-axis grid steps every 3 mana (0, 3, 6, 9, 12).
- Source: session 4a7404a5, 2026-03-20

### Paper Artboard Inventory — "Commander Deck Builder" File
Direction A (dark fantasy): A - Deck Gallery, A - Grimoire Top, A - Grimoire Bottom, A - Battlefield, A - Scrying Pool (5 artboards)
Direction B (warm manuscript): B - Deck Gallery, B - Grimoire Top, B - Grimoire Bottom, B - Scrying Pool, B - Shopping List (5 artboards — nav has 3 tabs: Grimoire, Scrying Pool, Shopping List)
B artboards are positioned to the right of A artboards on the canvas.
- Source: session a8e6cc42, 2026-03-20; session 9a365107, 2026-03-20

### Commander Spellbook API
Free, public JSON API providing pre-indexed combo lines for every Magic commander. Useful for a "Spell Library" or combo-browser feature. CORS-friendly.
- Source: session 1a8c36e7, 2026-03-21

### Smoke Test Script
`scripts/smoke_test.sh` — headless browser test that loads all 11 decks and checks for JS errors and error banner visibility. 12 checks total. Added in commit `6614bf9`.
- Source: session 9a365107, 2026-03-20

### Basic Lands — Shopping List Filter List
`aggregateShoppingCards()` filters out basic lands before building the buy list. Filtered names: Plains, Island, Swamp, Mountain, Forest, Wastes, Snow-Covered Plains, Snow-Covered Island, Snow-Covered Swamp, Snow-Covered Mountain, Snow-Covered Forest. Any card matching these names is dropped regardless of quantity.
- Source: session a2964006, 2026-03-20

### Shopping List — Singleton Deduplication Rule
Commander is a singleton format. When multiple decks are selected, each unique card needed appears exactly once in the shopping list (quantity 1), never additive. If "Sol Ring" appears in 3 selected decks, you still only need to buy 1. `aggregateShoppingCards()` deduplicates on card name — it does NOT sum quantities across decks.
- Source: session a2964006, 2026-03-20

### Commander Spellbook — almostIncluded Data Structure
`commanderspellbook_find_combos` returns two lists. `included` entries have combo data at the top level (cards, description, etc.). `almostIncluded` entries have a **nested** structure: `{combo: {cards: [{name}...], ...}, missing_cards: [...], missing_templates: [...]}`. When processing near-misses, card names come from `entry.combo.cards[].name`, not `entry.cards[].name`.
- Source: session e9eed048, 2026-03-22

### Deck Health Score — Five Components (Deterministic, post-DEC-90)
`data/commanders/{id}/metrics.json` → five deterministic scores, each 0–100:
- `manabase_health` — mana base consistency
- `role_coverage_health` — role slots filled vs B3/B4/B5 targets
- `curve_health` — CMC distribution + avg-cmc closeness + topcurve penalty
- `interaction_density` — removal/counter density
- `gameplan_cohesion` — archetype fit of card roles

`global_health` is the weighted aggregate. `grade` (A–F) derived by `gradeForGlobalHealth()`: >=90 A, 80–89 B, 70–79 C, 60–69 D, <60 F. Old simulation-based keys (`manaReliability`, `threatDeployment`, `comboConsistency`, `commanderIndependence`) are deleted.
- Source: session 5c05070c, 2026-05-04; session 3fef9cb0, 2026-05-04

### DFC Cards in the Deck Pool
10 double-faced cards (DFCs) exist in the 11-deck card pool. 7 are true DFCs needing back-face images (`modal_dfc` or `transform` layout): these use Scryfall's `?face=back` URL parameter for back face. 3 are split/room cards that show both halves on one face — no back image needed. The `layout` field in `card-metadata.json` distinguishes them. The card preview panel shows a ↻ flip button for `modal_dfc` and `transform` cards.
- Source: session 90f9b134, 2026-03-22

### Gandalf the White — Commander Profile
Mono-white, 5 CMC. Abilities: Flash; grants flash to all legendary and artifact spells; doubles all ETB and LTB triggered abilities from legendary permanents and artifacts. Strategy archetype: Hybrid Value-Stax (legendary ETB value + instant-speed hatebears). Bracket 4. 6 Game Changers: Ancient Tomb, Chrome Mox, Enlightened Tutor, Smothering Tithe, Teferi's Protection, The One Ring. Simulation: 68.1 health score (B grade), commander on curve at T5.
- Source: session 4d43917b, 2026-03-27

### Gandalf the White — Card Evaluation Rulings (B4 Mono-White Artifact ETB)
**Include:** Mana Tithe (white's Force Spike; 1-mana counter, plays well holding mana at instant speed in B4); Continue? ({1}{W} instant returning up to 4 creatures that died this turn — ETBs trigger doubled with Gandalf); Clever Concealment (board protection via convoke, nearly free with Myr tokens); Minas Tirith (legendary land with conditional card draw, enters untapped with a legendary creature).
**Skip:** Dawn's Truce (fog — dead card most turns); Parting Gust (bounce own permanent for 3 mana, inefficient vs Ephemerate at 1); Debt of Loyalty (requires opponent's creature to die; regenerate keyword rare on modern threats); Resurrection Orb (equip {4} too slow; Nim Deathmantle is superior — auto-triggers on any creature death).
- Source: session 4d43917b, 2026-03-27

### Tyvar, Jubilant Brawler — Card Profile (Meren/Graveyard Decks)
{1}{B}{G} Planeswalker, 3 CMC (Duskmourn). Static: creatures may activate abilities as though they had haste. +1: Untap target creature. -2: Mill 3, return MV ≤ 2 creature from GY to battlefield. Strong in Meren-style graveyard decks — the -2 hits 8+ targets (Blood Artist, Zulaport Cutthroat, Spore Frog, Sakura-Tribe Elder, Carrion Feeder, Stitcher's Supplier, Walking Ballista). The haste static lets Fauna Shaman, mana dorks, and tap-to-activate creatures use abilities immediately on entry.
- Source: session 60396211, 2026-04-07; session 8b5634a5, 2026-04-07

### Tyvar, the Pummeler — Card Profile (Elf Tribal)
{1}{G}{G} Legendary Creature — Elf Warrior 3/3 (Duskmourn). Finisher for Elf tribal commander decks with exponential pump mechanic. Replaced Tireless Tracker in the Verdant Tide deck — non-synergistic card draw without tribal or graveyard relevance is a weak slot.
- Source: session d7bac209, 2026-04-07

### Shriekmaw — Removal Evaluation in Black Decks
Evoke creature that destroys "target nonartifact, nonblack creature" — combined restriction misses a large portion of the Commander meta (black commanders, artifact creatures, indestructible threats). In graveyard/sacrifice decks, Plaguecrafter is superior as recurrable removal: forces sacrifice (no targeting restriction), bypasses hexproof/indestructible, hits planeswalkers and black creatures. Shriekmaw is typically the weakest removal slot to cut when evaluating swap targets.
- Source: session 8e81d541, 2026-04-07; session 8b5634a5, 2026-04-07

### Insidious Roots — Value in Sac/Graveyard Decks
Generates Plant creature tokens that serve as mana dorks and sac fodder — they grow over time as creatures die. In graveyard/sacrifice strategies (e.g., Meren of Clan Nel Toth), this is meaningful ongoing value, not just ramp. Don't cut it lightly when evaluating swap targets.
- Source: session 8e81d541, 2026-04-07

### The-White-Forge — Deck Profile
Commander: Gandalf the White (mono-white, 5 CMC). Archetypes: `["artifacts-matter", "etb-flicker"]`. Strategy: artifact ETB value engine — Gandalf doubles ETB/LTB triggers for legendary permanents and artifacts; grants flash to all legendary/artifact spells. Key synergy pieces: KCI, Mystic Forge, The One Ring, Smothering Tithe, Sun Titan. Bracket 4.
- Source: session 556a72ac, 2026-05-04

### Academy Manufactor — Card Profile
{1}{G} Artifact Creature. Whenever you create a Food, Clue, or Treasure token, create a token of each of the other two types instead. In artifact-engine decks (ETB doublers, Smothering Tithe, KCI), triples token output. An ETB trigger — Gandalf doubles it. Strong include in the-white-forge; only one copy is available in the physical collection (held in Mutant Multiplication).
- Source: session 556a72ac, 2026-05-04

### Inspiring Statuary — Card Profile
{3} Artifact. Nonartifact spells have improvise (tap artifacts you control to pay generic mana). In artifact-heavy decks with Gandalf flash, this lets the artifact swarm pay for nonartifact protection/tutor spells at instant speed. Strong combo accelerator alongside KCI / Mystic Forge. Replaces Endless Atlas in the-white-forge.
- Source: session 556a72ac, 2026-05-04

### Candidate Pool Scoring Noise — etb-flicker Tag
The `etb-flicker` archetype tag matches budget mono-white ETB creatures (Cat Collector, Mouse Trapper, Prideful Parent, etc.) that have no artifact-engine fit for Gandalf-style decks. Causes ~84% reject rate in top-50 triage. Fix: tighten etb-flicker pattern weight or add sub-tag "etb-flicker/artifact-only" so non-artifact ETB stragglers stop flooding the candidate pool.
- Source: session 556a72ac, 2026-05-04

### Candidate Pool Scoring Noise — Gap-Aware Boost Too Weak
P7.7 gap-aware boost (`score += gap_bonus`) is too weak to lift tutor candidates into the top 50 even when a deck has a 60+ tutor gap. Steelshaper's Gift and similar tutors fail to surface despite the explicit gap. Reported to DEC-99/DEC-134 for formula tuning.
- Source: session 556a72ac, 2026-05-04

### London Mulligan Math (Scrying Pool)
London mulligan rule: the first mulligan is free (draw 7 again); each subsequent mull bottoms (starting hand size - 1) cards. `bottomCountFor(N) = N - 1` where N = number of mulligans taken. When `bottomCountFor(8) = 7`, the player mulls to zero — terminal state: empty hand, display "Mulliganed to zero. Try a new hand." Implemented in `web/src/lib/scrying.ts`.
- Source: session a4d0d123, 2026-05-05

### DFC / Split / Adventure Cards — Canonical ` // ` Separator
deck.json stores multi-face and split cards in Scryfall's canonical `Front // Back` form (e.g., `Sea Gate Restoration // Sea Gate, Reborn`, `Dusk // Dawn`, `Brazen Borrower // Petty Theft`). Owned-card CSVs list only the front face name. All card-name keyed comparisons (Shopping, reservation math, cardMap lookups) must normalize via `frontFace()` to avoid missed matches. Covers DFCs (modal/transform), split/aftermath, and adventure cards — all use the same ` // ` separator on Scryfall.
- Source: session 4a3f24f8, 2026-05-06
