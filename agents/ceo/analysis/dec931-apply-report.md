# DEC-931 — Apply report (board verdicts on card 682b6545, 2026-09-29)

**Outcome:** eight board-approved swaps applied across six decks, full post-swap hygiene run, no validator, Game Changer, or strategy-ceiling warnings. Line C was applied with the board's cut (It That Betrays), not the proposed one (Blightsteel Colossus). Trigger-2 fired for titan-convergence, stampede-acres and broodfire-hatchery; re-assessment issues are filed (ids in the issue comment).

## Swaps applied

| Deck | Add | Cut | Round |
|---|---|---|---|
| tidal-legion | The Theorist, Jace Beleren | Quick Study | 1 since DEC-468 |
| titan-convergence | Emrakul, the Exigent Doom | It That Betrays (board's cut) | 3 since DEC-394 → Trigger-2 |
| verdant-tide | Verdant Kraken | Ohran Frostfang | 1 since DEC-569 |
| stampede-acres | Rockfall Vale | Jungle Shrine | 3 since DEC-581 → Trigger-2 |
| stampede-acres | Overgrown Farmland | Path of Ancestry | (same round) |
| broodfire-hatchery | Identity Echo | Rishkar's Expertise | 3 since DEC-544 → Trigger-2 |
| broodfire-hatchery | Rootbound Crag (owned) | Utopia Sprawl | (same round) |
| eternal-harvest | Darklight Phoenix | Culling the Weak | 2 since DEC-572 |

## Before / after (same inputs: 100k mana games, 10k goldfish games, metrics weights A)

| Deck | Sim health | Metrics global | Gaps | Notes |
|---|---|---|---|---|
| tidal-legion | 78.2 → 78.7 (A) | 93 → 93 | 0 → 0 | threatDensity T6 85.8 → 87.8; the sim cannot see The Theorist's opponent-draw-step draw, so the draw side is understated |
| titan-convergence | 72.4 → 72.3 (B) | 65 → 65 | 4 → 4 | within noise; the sim does not model the cast-trigger land untap |
| verdant-tide | 71.5 → 71.2 (B) | 89 → 89 | 0 → 0 | drawEngineReliability T6 70.4 → 65.9 (Frostfang was tagged card-draw); Kraken's upkeep tokens are not goldfished |
| stampede-acres | 72.6 → 72.8 (B) | 85 → 85 | 2 → 2 | manaReliability 70.7 → 71.6 from the two slow lands; untapped lands 35 → 37 of 37 |
| broodfire-hatchery | 65.3 → 67.0 (B) | 84 → 85 | 1 → 1 | manaReliability 65.1 → 67.9 (lands 36 → 37, Karsten G 21 → 22); interactionAvailability T6 80.8 → 83.5 |
| eternal-harvest | 72.6 → 73.2 (B) | 88 → 87 | 0 → 0 | threatDeployment 78.2 → 80.8; the −1 global is the ramp-role count dropping by one (Culling the Weak was tagged ramp) |

Manabase audit after the swaps: stampede-acres lands 37, untapped 37, Karsten G 23/14, R 18/13, W 26/18, health 76 → 78. Broodfire-hatchery lands 37, untapped 36 (Jetmir's Garden), Karsten G 22/20, R 17/13, W 17/14, health 77.

## Hygiene run

- `fetch_card_metadata.py` per deck: seven new cards added to `data/card-metadata.json` (Rootbound Crag was already present).
- `compute_tokens.py` per deck: Forest Tentacle (verdant-tide) and Illusion (tidal-legion) tokens added.
- `validate_deck_json.py`: all six decks green. `check_game_changers.py --offline`: fleet recount 0 problems (none of the adds or cuts is a Game Changer). `validate_strategy_ceiling.py`: no warnings on any of the six.
- `refresh_card_pool.py` and `compute_deck_metrics.py --weights A` per deck; `export_simulation_results.py --deck` per deck.
- Mana-sim model edits: stampede-acres now models Rockfall Vale and Overgrown Farmland as slow lands (tapped unless two other lands are on the battlefield) and drops Jungle Shrine and Path of Ancestry; broodfire-hatchery adds Rootbound Crag as an untapped checkland and drops the Utopia Sprawl modeling-gap note (Wild Growth left at DEC-574).
- Prose: tidal-legion draw sentence rewritten for The Theorist; broodfire Free Sacrifice Outlets, Ramp and Fixing, and Key Lands categories updated (37 lands, 36 untapped); verdant-tide Card Advantage / Token Army categories and eternal-harvest Engine Pieces category updated; Culling the Weak highlight removed; new highlights for The Theorist, Emrakul, Verdant Kraken, Identity Echo, Darklight Phoenix; new eternal-harvest synergy "Phoenix free-death loop". Stale-reference sweep: cut cards appear only in `sources` attribution strings.
- Combo Lab artifacts regenerated in order (spellbook → Tier C → Tier B) for all six decks. The per-deck sync advanced the shared corpus (2026-09-28T15:10 → 2026-09-29T15:10, Spellbook API 7.1.1 → 7.1.2, 7,294 → 7,302 cards, 107,338 → 107,731 variants), so the whole fleet was re-emitted with `--offline --force`; no deck's `included[]` changed (titan 12, eternal-harvest 11, broodfire 6, stampede 4, tidal-legion 0, verdant-tide 0), so no Tier B rebuild was needed elsewhere.
- Web cache key bumped to `gv1-deck-data-v132`.

## EDHREC closing diff (DEC-402) — absentees at 40% or more after the swaps

- **tidal-legion**: Attuma 74.8, Merfolk Sovereign 65.8, High Tide 58.5, Merrow Reejerey 58.2, Pongify 56.9, Seafloor Oracle 51.6, Bident of Thassa 50.6, Emperor Mihail II 46.9, Summon: Leviathan 45.6, Opt 44.2, Stonybrook Banneret 43.1, Deeproot Waters 40.8 — all on the DEC-468 reject or defer lists, unchanged. Negate 40.5 — defer: the counter suite is at 13 plus two creature counters and the DEC-467 vision prefers multi-pip counters (Negate has one).
- **titan-convergence**: It That Betrays 79.8 — board's cut, on record. Flayer of Loyalties 76.4, Ulamog the Infinite Gyre 65.6, Endbringer 61.0, Bane of Bala Ged 59.5, Oblivion Sower 57.2, Ultima 52.2 — defer to the Trigger-2 re-assessment (titan slots). Calamity of the Titans 63.5 and Kozilek's Command 47.0 — defer, first in line: they address the removal-board and removal-spot gaps. Null Elemental Blast 54.8 — defer (interaction slot review). Palladium Myr 73.5, Skittering Cicada 72.5, Dreamstone Hedron 59.5, Everflowing Chalice 55.5, Solemn Simulacrum 50.9 — reject class: slower than the deck's fast-mana suite (Mana Vault, Ancient Tomb, Thran Dynamo, Basalt Monolith, Tron). Rogue's Passage 69.7, Tomb of the Spirit Dragon 65.7, Temple of the False God 61.6, Arcane Lighthouse 54.7, Guildless Commons 51.0 — defer to the manabase step of the re-assessment.
- **verdant-tide**: Forest 97.2 is a name mismatch (the deck runs Snow-Covered Forest). Fyndhorn Elves 68.8, Arbor Elf 53.4 — defer: 23-elf core already at the DEC-569 count; next dork slot. Beast Whisperer 60.4 — defer: Glimpse of Nature, Guardian Project, The Great Henge and Leaf-Crowned Visionary cover cast-draw. Fierce Empath 43.3 — defer: tutors Kraken/Craterhoof/Ghalta; Worldly Tutor and Eladamri's top-of-library cast cover it. Emerald Medallion 40.9 — defer.
- **stampede-acres**: Second Harvest 50.2 — deliberate DEC-378 cut. Doubling Season 46.3 — DEC-581 defer. Parallel Lives 42.8 — DEC-685 board cut. Jungle Shrine 42.4 — cut this round. Jetmir's Garden 43.3 — reject, same always-tapped tri class. Farseek 43.7 — defer (Nature's Lore plus four dorks). Heroic Intervention 42.4 — defer (Clever Concealment, Flawless Maneuver, Grand Crescendo). Aura Mutation 42.4 — defer (Artifact Mutation in). Jacked Rabbit 43.6, Peregrin Took 41.1, Finneas 40.7, Farmer Cotton 40.7, Cadira 40.1 — defer: token creatures for the next creature slot; the board's low-MV token floor is the constraint, and none was oracle-verified this round.
- **broodfire-hatchery**: Cultivate 63.5, Rampant Growth 55.6, Kodama's Reach 43.7 — reject class: tapped basics; the deck's ramp is the untapped Nature's Lore class. Jungle Shrine 59.7 — reject (always tapped). Heroic Intervention 40.8 — DEC-574 board cut. Etali Primal Storm 59.1, Zetalpa 51.2, Ghalta and Mavren 49.2, Ghalta Primal Hunger 48.5, Ghalta Stampede Tyrant 46.2, Gishath 42.0 — defer to the Trigger-2 re-assessment (bomb slots). Cinder Glade 54.4 (owned, 3 free), Canopy Vista 49.9, Sunpetal Grove 41.8 — defer: next land adds; Cinder Glade is Forest-typed and fetchable by Nature's Lore, so it is first in line if the count goes to 38. Rhythm of the Wild 51.0, Sundering Growth 45.1, Swiftfoot Boots 41.9, Dinosaur Egg 41.6 — defer.
- **eternal-harvest**: Viscera Seer 67.4, Arcane Signet 57.6, Accursed Marauder 54.5, Grim Haruspex 49.4, Cankerbloom 46.4, Protean Hulk 45.9, Syr Konrad 44.5 — DEC-572 defers; Tainted Wood 54.6, Fleshbag Marauder 42.9, Golgari Rot Farm 41.3 — DEC-572 rejects; Carrion Feeder 46.9 — DEC-929 board cut. Unchanged.

## Purchases (information only; release 2026-10-02)

The Theorist, Jace Beleren; Emrakul, the Exigent Doom; Verdant Kraken; Rockfall Vale; Overgrown Farmland; Identity Echo; Darklight Phoenix. Rootbound Crag comes from the owned pool (3 free copies). ManaBox remains the printing record.
