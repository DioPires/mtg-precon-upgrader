# DEC-537 — Gathering Shadow single-deck re-assessment (DEC-396 Trigger 2)

Date: 2026-08-17. Owner: CEO. Baseline: DEC-533 remake commit `1135053` (deck then named dark-dominion). Current: HEAD after round 5 (`4a6130d`).

## Verdict

PASS. No swap proposal needed. The deck holds its 4- bar after 5 board-approved rounds. All rubric steps ran clean.

## Card delta since baseline (rounds 3–5)

- Cuts (7): Along the Crooked Way, Book of Mazarbul, Gorbag of Minas Morgul, Grishnákh Brash Instigator, Lightning Greaves, Orcish Medicine, Thought Vessel
- Adds (7): Black Market Connections, Consider, Gandalf Friend of the Shire, My Precious // Allure of Power, Talisman of Creativity, The Grey Havens, Windfall
- Both lists total 99.

## 1. Pool / metrics / sim — before vs after (same 100k mana-sim + 10k goldfish basis)

- `refresh_card_pool`: mirror current (2026-08-17), EDHREC rates fresh (2026-08-15), candidates unchanged (200).
- `compute_deck_metrics`: global 91±5, norm 96, mana 88, roles 95, curve 94, interaction 120, cohesion 33, resilience 100, gaps 0 — **unchanged vs baseline** (baseline global 91, gaps 0).
- Sim (baseline → current):
  - deckHealthScore 75.1 → 74.9 (flat). Components: manaReliability 73.4 → 75.3 (+1.9), interactionDensity 84.5 → 82.7 (−1.8), commanderIndependence 58.9 → 56.4 (−2.5). The dips are the draw-package trade; expected.
  - Speed up: commanderCast T5 65.8% → 70.7%; lethalProxy T5 26.5% → 28.3%, T6 55.0% → 55.7%, T7 78.5% → 78.8%, T8 91.0% → 91.3%.
  - drawEngineReliability count 15 → 17; T5 uptime 85.3% → 88.9% (the round-4 package doing its job).
  - Color screw improved every turn (U weightedAdequacy 78.6 → 81.2; The Grey Havens + Talisman of Creativity).

## 2. Bar check (bracket-philosophy, deck is 4-, uncapped GC tier)

- `validate_strategy_ceiling`: shell 88, payoff 78.8% LP@T7, flags **ok** — clears shell_floor 80 / payoff_floor 15%.
- `check_game_changers --offline`: ts mirror ok (53), fleet recount 0 problems; deck field 6 GCs matches, 4- is uncapped.
- Interaction suite: 5 spot removal + 3 board wipes + 5 counterspells (incl. free Fierce Guardianship, Deadly Rollick); interaction metric 120. Bar ≥ B3+/4- met.

## 3. Stale-reference sweep

- `validate_deck_json`: 244 references validated, pass.
- Prose grep of the full deck.json blob for all 7 cut cards (incl. diacritic variants Gorbag/Grishnakh): **0 hits**.

## 4. EDHREC closing diff (final 99 vs Sauron, the Dark Lord page, 298 rated cards)

Six cards ≥40% inclusion absent from the 99. All six were triaged in the DEC-533 closing diff; dispositions stand, none re-opened:

- Crumbling Necropolis 63.3% — reject (enters tapped; manabase strictly better: T3 color screw ≤ 11.4%, mana 88)
- Blasphemous Act 60.6% — defer (3 wipes already; symmetric wipe kills the amassed Army)
- Arcane Denial 53.0% — reject (counter suite at 5; Swan Song chosen over it head-to-head in DEC-533)
- Lord of the Nazgûl 48.8% — reject (pulls the deck into a wraith-tribal plan)
- Dark Ritual 48.7% — reject (battlecruiser deck, not ritual combo)
- Anger 47.2% — defer (per DEC-533 record)

## Artifacts

- Regenerated `data/commanders/gathering-shadow/simulation.json` (only file changed; metrics + candidates byte-identical).
- Next Trigger-2 baseline for this deck: this assessment (DEC-537).
