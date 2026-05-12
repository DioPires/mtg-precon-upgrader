# Patterns

### Commander Spellbook Near-Miss Analysis Workflow
When researching deck updates, always run `commanderspellbook_find_combos` and evaluate `almost_included` results:
1. Review combos 1-2 cards away (`missing_cards` field)
2. For each near-miss, ask: does adding the missing card fit the deck strategy, bracket target, and budget?
3. If a single card enables a strong combo without hurting consistency, recommend it as an add with `commanderspellbook` source
4. Note whether the missing card also has standalone value (e.g., Walking Ballista is useful outside the combo)
This is the most valuable part of Commander Spellbook integration — finding high-impact adds the deck is "one card away" from.
- Source: session ee529a54, 2026-03-17

### Back to Basics Nonbasic Land Evaluation Framework
When evaluating whether to include Back to Basics with nonbasic lands:
1. **Fetch lands** — always fine (sac immediately, leave play)
2. **Channel/MDFC lands** — fine (channel from hand, never need to untap)
3. **Artifact lands** — fine in Urza (tappable as artifacts; Unwinding Clock negates lockout)
4. **Sagas** — fine (progress via lore counters)
5. **One-shot ETB lands** — fine (value already realized)
6. **Activated-ability lands** (Academy Ruins, Inventors' Fair) — truly hurt, real cost
7. **Mana-only nonbasics** (Ancient Tomb) — hurt after early game
If 75%+ of nonbasics are unaffected, Back to Basics is worth running. Chain of Vapor is sufficient as an emergency self-removal out.
- Source: session b4001091, 2026-03-17

### Asymmetric Wrath Suite for Vehicle/Token Decks
For decks that produce small tokens as crew bodies (Shorikai/similar), build a wrath suite that leaves you with creatures:
- Wraths that kill power X+ (target your own small creature): Fell the Mighty, The Battle of Bywater, Dusk // Dawn, Expel the Interlopers
- Wraths that create tokens post-wipe: White Sun's Twilight (X Mites), Martial Coup (X Soldiers), Sunfall (Incubator token)
- Exile wraths to handle indestructible: Sunfall
Avoid wraths that also destroy Vehicles/artifacts (e.g., Spectacular Pileup kills Shorikai).
- Source: session b4001091, 2026-03-17

### Game Changer Cross-Reference with Owned Collection
Before finalizing a deck build, cross-reference `priv_data/owned_formatted.csv` against the Game Changers list filtered by color identity. This surfaces high-power cards the player already owns that could be included. Evaluate each candidate for color legality, strategic synergy, and whether it adds a distinct role vs. duplicates existing lines.
- Source: session 594ee133, 2026-03-17

### Bracket 4/5 Compliance Audit Checklist
When building or upgrading a B4+ deck, audit against these structural issues (from CZ731):
1. **Tapped lands** — each tapped land costs tempo; eliminate or minimize
2. **Sorcery-speed interaction** — removal and counters should be instant-speed or free
3. **Free spells** — Fierce Guardianship, Deadly Rollick, Deflecting Swat (commander-dependent); Force of Will / Force of Negation (blue); Flusterstorm / Pact of Negation
4. **Slow ramp** — replace Cultivate / Kodama's Reach with fast mana (Chrome Mox, Ancient Tomb) or cheaper ramp (Rampant Growth, Nature's Lore)
5. **Fast mana presence** — Sol Ring minimum; Mana Vault, Mox Diamond, Chrome Mox for B5
Address structural issues first, then layer specific card upgrades (Jeska's Will, Survival of the Fittest, etc.).
- Source: session ccb0e567, 2026-03-18

### Verify Replacement Cards Against Current Decklist
Before proposing a land or card replacement, always verify the proposed addition is NOT already in the deck.json decklist. Multiple failures occurred when proposed replacements (Watery Grave, Morphic Pool, Luxury Suite, Adarkar Wastes, Seachrome Coast, Eiganjo) were already present. Run a search of the deck.json before finalizing swaps.
- Source: session ccb0e567, 2026-03-18

### Superfriends Two-Mode Design Under Humility
Humility-based superfriends decks operate in two distinct modes. Mode A (Humility online): all creatures are blanked (yours and opponents'), planeswalkers are protected from combat, creature-based utility is dead. Mode B (no Humility): creature utility (Grand Abolisher, Voice of Victory, Deepglow Skate) is active, power-threshold board wipes work. Design the 99 so both modes have viable win lines. ~4-6 dead cards per mode out of 99 is acceptable. The burn win-cons (Chandra Legacy of Fire, Guff -3) and stax PWs (T3feri, Narset) work in both modes.
- Source: session e1ddc605, 2026-03-19

### Stax Planeswalkers Are Double-Duty in Superfriends
In a Guff superfriends deck, control planeswalkers like Teferi, Time Raveler and Narset, Parter of Veils are both stax pieces AND planeswalker-count contributors. Chandra, Legacy of Fire and Commodore Guff's -3 deal X damage where X = number of PWs you control. Every stax PW advances two win conditions simultaneously — this efficiency is what makes Jeskai superfriends viable at Bracket 4.
- Source: session e1ddc605, 2026-03-19

### Adding a New Deck: Required Checklist
All steps must be completed when adding a new deck or simulation data will be incorrect:
1. Create `data/commanders/{id}/deck.json` (commander separate from decklist)
2. Add entry to `data/index.json`
3. Run `scripts/fetch_card_metadata.py` to populate card metadata
4. Create `scripts/mana_simulation_{deck-id-underscored}.py` (per-deck-ID naming, e.g. `mana_simulation_verdant_tide.py`); use `azure_dominion` script as template for mono-color decks
5. Add deck import + function call to `scripts/export_simulation_results.py`
6. Run export script to generate `data/commanders/{id}/simulation.json`
7. Generate `data/commanders/{id}/recommendations.json` (run Commander Spellbook combos, normalize `almost_included` → `almostIncluded` key, run `generate_recommendations.py`)
8. Add Archidekt ID to `archidekt_deck_ids.json` if deck is published to Archidekt
Skipping step 3 causes land misclassification → inflated mulligan rate (see debugging.md). Skipping step 7 leaves the Upgrade Paths and Compare tabs with no data.
- Sources: session 0e13b68a, 2026-03-21; session 975406e6, 2026-03-20; session fd90e34c, 2026-04-06

### Commander Spellbook Batch Audit Workflow
When auditing multiple decks against Commander Spellbook:
1. Extract card names: `jq '[.decklist[].name] | unique' deck.json`
2. Call `commanderspellbook_find_combos` per deck (large results auto-save to temp files — use jq to extract `.included[]`)
3. For each included combo: if already tracked with CS source → skip; if tracked with only `ai-inferred` → add CS source; if absent entirely → add new synergy entry with CS source
4. Combos in both `winConditions` and `synergies` are valid — don't deduplicate across arrays
5. Process decks in parallel (subagents per deck) for efficiency
- Source: session d5616f91, 2026-03-20

### Source Attribution Cleanup (ai-inferred Removal)
When cleaning `ai-inferred` source entries from deck.json files:
- Synergy already has a `commanderspellbook` source → remove the `ai-inferred` entry (CS is authoritative)
- Synergy has no other source → replace `ai-inferred` with `manual-verified` + EDHREC URL (`https://edhrec.com/combos/{card1}-{card2}`, lowercase hyphen-separated names)
- Never leave a synergy with zero sources after cleanup
- Source: session f0c90f29, 2026-03-20

### Performance: CSS/JS Extraction from Monolithic HTML
Extracting CSS and JS from a monolithic HTML file into separate files gives three wins:
1. Browser can cache CSS and JS independently (changes to JS don't bust CSS cache)
2. HTML response is 89% smaller (37KB vs 327KB) — faster first paint
3. `defer` on the JS `<script>` tag allows HTML to parse before JS executes

Extraction process: `sed` to isolate content between `<style>` tags (saved to `styles.css`) and `<script>` tags (saved to `app.js`); strip 4-space indentation from being inside the HTML tags; replace inline blocks with `<link rel="stylesheet">` and `<script src defer>`.
- Source: session e8e851c4, 2026-03-20

### Parallel Subagent Deck Analysis
For multi-deck upgrade analysis (e.g., reviewing owned cards across 5 decks), launch one subagent per deck concurrently. Each agent gets: (1) full deck.json with decklist, categories, and strategy, (2) pre-scored candidate cards with relevance scores, (3) owned card inventory reference. Each returns a top-10 ranked list with specific cut candidates and conflict flags. After all agents complete, aggregate results and verify no card appears in conflicting recommendations across decks. This scales to 5 decks in parallel with fast turnaround and deep per-deck analysis.
- Source: session e6b85099, 2026-04-06

### Holistic Deck Swap Evaluation Checklist
Card-for-card swap analysis is insufficient — each swap must be validated holistically across 5 dimensions:
1. **Mana curve shift** — does removing a low-CMC card and adding a higher-CMC card push the curve past the deck's threshold?
2. **Card type distribution** — does the swap break creature/noncreature balance or reduce land count?
3. **Role replacement** — does the new card fully cover the cut card's role (removal, draw, ramp, threat)?
4. **Combo line integrity** — does the cut card appear in any named combo or synergy chain? (e.g., Altar of Dementia in Mikaeus+Ballista loop)
5. **Redundancy saturation** — is the new card duplicating a role already covered by 4+ cards, while the cut provides something scarcer?
Failure in any dimension is grounds to reject the swap. In practice, 60%+ of initially attractive swaps fail holistic review.
- Source: session 244a8cf1, 2026-04-06

### Per-Deck Adoption Pass: Classify All Top-50 Before Proposing
For per-deck adoption passes (DEC-90 / DEC-99 line, any DEC-1XX candidate review), classify the **entire top-50** through the deck's strategy filters before proposing any add. Never pitch the top-N-by-score directly — the candidate score doesn't encode strategy lens (asymmetric vs symmetric, new axis vs redundancy). On 2026-05-03 (DEC-101, eternal-agony), pitching top-3-by-score before holistic review produced three cards the board immediately rejected; the subsequent "review candidates as a whole" correction cost two extra heartbeats.
Process: (1) dump all 50 candidates' oracle text via jq or Scryfall; (2) apply two filters per card: does it fit the strategy asymmetrically, and does it open a new axis or redundantly cover an existing one? (3) build a triage table grouping all 50 into reject / defer / include buckets; (4) propose only the 3-5 strongest includes with explicit rationale; (5) include the full table in the board comment for auditability.
- Source: session fd3ef271, 2026-05-03
