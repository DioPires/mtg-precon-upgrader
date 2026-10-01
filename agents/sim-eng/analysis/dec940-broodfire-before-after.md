# DEC-940 — broodfire-hatchery before/after (goldfish combat modifiers)

**Baseline**: `2ce215f` (DEC-937 mana fix + DEC-938 hatch engine + DEC-939 ceiling-check fix).
**After**: this change — `COMBAT_MODIFIERS["broodfire-hatchery"]` on the shared goldfish.
Both columns are the same 10,000-game seeded goldfish; only the combat-phase code
and the printed-P/T metadata differ. Re-export: `scripts/export_simulation_results.py
--deck broodfire-hatchery`, then `compute_deck_metrics.py --deck broodfire-hatchery`.

## simulation.json — goldfish speed curves (% of games, cumulative)

| metric | T5 | T6 | T7 | T8 | T9 | median |
|---|---|---|---|---|---|---|
| `lethalProxy` before | 3.2 | 12.6 | 32.9 | 59.2 | 77.8 | T8 |
| `lethalProxy` after | **5.9** | **20.9** | **44.5** | **66.9** | **81.8** | T8 |
| `comboLethal` before | 1.2 | 2.4 | 3.8 | 5.7 | 7.9 | — |
| `comboLethal` after | 1.2 | 2.4 | **3.7** | **5.5** | **7.5** | — |

`lethalProxy` is the metric the modifiers were built to fix: +8.3 pts at T6, +11.6 at
T7, +7.7 at T8. The median lethal turn stays T8, so the deck does not move band on
the DEC-937/DEC-935 re-fitted table (T8 is the fleet-body row).

`comboLethal` drops 0.1–0.4 pts. Cause, stated plainly: Aggravated Assault pays
{3}{R}{R} out of the same end-of-turn pool the combo gate reads, so in the small
number of games where both were live the extra combat takes mana the combo check
wanted. This is the known cast-priority limitation the issue puts out of scope (the
goldfish has no "combo beats value" priority), and the DEC-405 deploy engine and
DEC-938 hatch engine already spend from the pool ahead of the same gate. Not a
behaviour change in the combo systems themselves.

## simulation.json — consumers of the goldfish

| field | before | after |
|---|---|---|
| `reliabilityMetrics.comboAssembly.bestByTurn` T6 / T7 / T8 | 10.7 / 13.8 / 16.9 | 10.6 / 13.5 / 16.7 |
| `reliabilityMetrics.comboAssembly.medianAssemblyTurn` | null | null |
| `reliabilityMetrics.commanderDependency.score` | 77.5 | 77.5 |
| `deckHealthScore.components.comboConsistency` | 51.2 | 51.2 |
| `deckHealthScore.components.commanderIndependence` | 22.5 | 22.5 |
| `deckHealthScore.score` / `grade` | 65.0 / B | 65.1 / B |

`comboAssembly` moves with `comboLethal` and for the same reason (same pool, same
gate). `comboConsistency` and `commanderIndependence` are unchanged to the reported
decimal, so `deckHealthScore` only moves +0.1 — the health score is not driven by the
damage curve.

## metrics.json

| field | before | after |
|---|---|---|
| `win_turn.best` | 7 | **6** |
| `win_turn.typical` | 8 | 8 |
| `win_turn.contested` | 9 | 9 |
| `win_turn.source` | lethalProxy | lethalProxy |
| `global_health` | 79 ±8 | 79 ±8 |
| `gaps[]` count | 2 | 2 |

`win_turn.best` is the first turn `lethalProxy` crosses 15%: T7 (12.6 → 32.9) before,
T6 (20.9) after. `typical` (50% crossing) stays T8. `global_health` is computed from
`deck.json` alone and is unaffected.

## Strategy-ceiling check

`validate_strategy_ceiling.py --deck broodfire-hatchery`: `shell 77, payoff 66.9%
LP@T8, ok` — no warning, no threshold or label change. (Before: 59.2% LP@T8, also
`ok`.)

## Control — base combat proxy unchanged

`compute_goldfish_section` for **stampede-acres** (an unconfigured deck) is byte-equal
before and after, both for the `goldfish` section and the combo-assembly turns. The
metadata change alone was also verified inert: the same comparison across just the
`card-metadata.json` edit is identical. Unit-level control: `combat_phase_damage`
returns the plain sum of ready attackers both with `modifiers=None` and with the
broodfire config but none of the modifier permanents on the battlefield
(`CombatPhaseDamageTests.test_unconfigured_deck_gets_the_plain_sum`), and the
goldfish-loop control runs the identical hand on an unconfigured deck id for one
unmodified combat (`CombatModifierGoldfishTests.test_unconfigured_deck_runs_one_unmodified_combat`).

Only broodfire-hatchery is configured; no other deck's `simulation.json` was
re-exported or needed to be.
