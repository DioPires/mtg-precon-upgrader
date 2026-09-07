# DEC-689 — Gathering Shadow Trigger-2 re-assessment (PASS)

Date: 2026-09-07. Assessor: CEO. Baseline: DEC-533 close (commit `4a6130d`, decklist identical at `5751cff`). Current: `bfae929` (DEC-688).

## Verdict

**PASS — no swaps proposed.** All metrics at or above baseline, zero gaps, validators clean, bar check clean. The swap-round counter resets to 0 at this assessment.

## Rounds covered (3 board-approved rounds since DEC-533)

1. DEC-578 — +Raise the Palisade / −Decree of Pain (commit `e5a56c6`)
2. DEC-687 — +Chrome Mox / −Inherited Envelope, +Dark Ritual / −Mind Stone (commit `393a638`)
3. DEC-688 — +Turbulent Springs / −Goblin-town + sim model update (commit `bfae929`)

## 1. Card pool refresh + top-50 triage

`refresh_card_pool.py` ran clean today: mirror current (2026-09-07), EDHREC rates fresh (fetched 2026-09-07 17:45Z), candidate pool regenerated with **no change** (200 candidates). No new printing entered the pool since the DEC-578 sweep.

All 50 top-50 non-deck candidates fall into standing dispositions:
- **DEC-578 HOB/HOC sweep (156 cards, closed)**: the LOTR-set bulk (Orcish Medicine, Bilbo Retired Burglar, Dunland Crebain, Down Down to Goblin-town, etc.). Board accepted only +Raise the Palisade from that sweep; do-not-reopen flag stands.
- **DEC-533 final rejects**: Glorious Gale, Fiery Inscription, Fall of Cair Andros, Mordor Muster, Surrounded by Orcs, Sauron the Necromancer, Lord of the Nazgûl, Dreadhorde Invasion, Crumbling Necropolis.
- **Deliberate recent cuts**: Inherited Envelope (63.8, cut DEC-687 for Chrome Mox), Gorbag of Minas Morgul (cut DEC-533 R5), Grishnákh (cut R4 for Windfall), Book of Mazarbul / Along the Crooked Way (cut R4 draw package).
- **Generic go-wide fillers scoring 51–55** (Maskwood Nexus, Endless Ranks of HYDRA, Marionette Apprentice, …): defer — zero `gaps[]` to address, none outranks an incumbent.

Include: none.

## 1b. Archetype recipe sweep (tokens-go-wide, status live)

Ran all 15 sub-recipe queries with `id<=ubr` splice, ordered by EDHREC, capped top-50 per sub-recipe, post-filtered vs decklist + candidates top-50 (raw deltas in run scratch; ~170 names). Deck tags amass-orcs / amass-armies have no live recipes — tokens-go-wide absorbs both idioms per its summary. No include. Notable defers, all with Sauron-page inclusion below 25% and none in candidates top-50:
- Lazotep Plating 23.4% — also on DEC-533 rejects list; disposition stands.
- Widespread Brutality 23.0% — deck deliberately caps wipes (symmetric wipes kill the Army); defer.
- Gríma Wormtongue 10.4%, Gleaming Overseer 10.1%, Commence the Endgame 6.5% — outscored by incumbents; defer.
- Doubler/go-wide engines (Bitterblossom, Krenko lines, X-spells): off-idiom — this deck grows one Army via amass rather than making many tokens; reject as a class.

## 2. Before/after vs DEC-533 baseline

| Measure | DEC-533 (`4a6130d`) | HEAD (`bfae929`) | Δ |
|---|---|---|---|
| manabase_health | 88 | 89 | +1 |
| role_coverage | 95 | 95 | 0 |
| curve_health | 94 | 97 | +3 |
| interaction_density | 120 | 120 | 0 |
| gameplan_cohesion | 33 | 33 | 0 |
| resilience_health | 100 | 100 | 0 |
| **global_health** | **91 / norm 96** | **92 / norm 97** | **+1** |
| gaps[] | 0 | 0 | 0 |
| sim deckHealth | 74.8 (B) | 74.5 (B) | −0.3 |
| lethalProxy T6/7/8 | 55.7 / 78.8 / 91.3 | 49.8 / 74.3 / 88.4 | −5.9 / −4.5 / −2.9 |
| commander cast by T6 | 56.4% | 54.7% | −1.7 |
| threat count (sim) | 37 | 36 | −1 |

The lethalProxy dip is the composite of the three approved rounds plus the DEC-688 sim-model change, which models Turbulent Springs conservatively (tapped until it is at least the 4th land drop, dropping the turn-3 unlock case) where Goblin-town was a flat always-tapped land. Health components are flat (interaction 82.7→82.7, combo 50.0→50.0, commanderIndependence 56.4→56.3). Strategy ceiling still passes with wide margin (payoff 74.3% LP@T7 vs 15% floor). Each round's impact was board-visible at approval time; no corrective action needed.

## 3. Bar check

Bracket 4−, shell 89, payoff 74.3% LP@T7 — `validate_strategy_ceiling.py` reports ok, no warnings. Fleet bar (≥ B3+/4−) met. GC recount (`check_game_changers.py --offline`): ts mirror ok (53 cards), fleet recount 0 problems; deck at 7 GCs, uncapped at 4−.

## 4. Stale-reference sweep

Swept all prose (guideContent, category descriptions, win-condition text, synergies, adds) for the four cards cut since baseline — Decree of Pain, Goblin-town, Inherited Envelope, Mind Stone: **0 mentions**. `validate_deck_json.py`: 241 refs validated, clean. DEC-688's post-swap hygiene held.

## 5. Deck Review Checklist items

**EDHREC closing diff** (298 rated cards, fetched today). Misses ≥40%, all with standing dispositions from the DEC-533/DEC-537 closing diffs — none reopened:
- Crumbling Necropolis 63.0% — reject (enters tapped; manabase strictly better, mana 89, Karsten all green).
- Blasphemous Act 60.6% — defer (symmetric wipe kills the amassed Army; wipes deliberately capped).
- Arcane Denial 53.3% — reject (counter suite at 5; Swan Song chosen head-to-head in DEC-533).
- Lord of the Nazgûl 49.1% — reject (pulls into wraith tribal).
- Anger 47.3% — defer (per DEC-533 record).
- Note: Dark Ritual (48.7% reject in DEC-537) is now IN the deck — board-approved placement in DEC-687 supersedes.
- New near-threshold: Grishnákh 39.4% (deliberate R4 cut, stands), Living Death 39.2% — defer with note: symmetric mass reanimation; Ring-tempt discards do fill our yard, but it rebuys every opponent's yard too, and the deck's plan is board-independent amass, not reanimator.

**Manabase audit**: lands 39.0 (target 39.4), untapped 38, Karsten B 27/16, R 21/20, U 21/18 — all pass. Only unconditional tapped land is Bojuka Bog (kept: the deck's only land-slot graveyard hate). Free upgrades exist (Reflecting Pool, City of Brass) but with Karsten green across all three colors there is no deficit to fix — defer.

**Hoser coverage** (top hate classes: graveyard hate vs Ring-tempt/recursion package; board wipes vs the Army): per-permanent-type answers unchanged since the DEC-533 round-6 review — artifact-carried hate (Grafdigger's Cage class) answered by Flame of Anor (only hard artifact kill); enchantment-carried (Rest in Peace class) answered by Feed the Swarm (oracle re-verified today: "Destroy target creature or enchantment an opponent controls"). Board reviewed exactly this thinness in DEC-533 round 6 and chose keep-flame; disposition stands.

**Commander dependency**: sim commanderIndependence 56.3. Sauron carries the amass-on-opponent-cast and Ring-tempt engines; with him neutralized the deck still executes through its 36 sim-counted threats and 14-piece draw package. Under a Darksteel Mutation-class lock (commander stays on battlefield, CR 903.3d — no zone change, no CZ return): covering outs are Feed the Swarm (destroys the opposing aura), Raise the Palisade (oracle re-verified: "Choose a creature type. Return all creatures that aren't of the chosen type to their owners' hands" — name a type the locked Sauron doesn't have, he bounces to hand and recasts through the command zone option), plus 5 counterspells to stop the lock on the stack. Pass.

## Disposition

PASS, no proposal needed, round counter reset to 0. Next Trigger-2 fires after 3 new board-approved rounds.
