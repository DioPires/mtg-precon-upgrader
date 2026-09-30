# DEC-937 — goldfish mana double-spend: fleet before/after

Before = fleet simulation.json / metrics.json as committed at `316766b`.
After = re-export on the DEC-937 fix (one mana pool per turn, spent once).
Both runs: 10,000 goldfish games per deck, unchanged seeds, unchanged thresholds.
Machine-readable copy: [`dec937-fleet-before-after.json`](dec937-fleet-before-after.json).

## What changed in the model

`simulate_goldfish_game` rebuilt the turn's mana pool from every active source on
each pass of its cast loop and threw away the `after_spending` remainder. Every
spell in a turn therefore paid with the full untapped board. Reproduced on a
synthetic 40 Forest + 59 `{1}{G}` deck: two lands on turn 2 paid for six
two-drops. The fix builds one pool per turn after the land drop and carries it,
so each cast removes the sources it spent and sources that come online untapped
mid-turn join the pool. The same remaining pool now feeds the commander cast,
the `winConditions` combo gate, the `KEY_COMBOS` assembly gate, and the DEC-405
transform activation.

Nothing else moved: cast priority, `GOLDFISH_LETHAL_DAMAGE_PROXY`,
`meaningful_threshold`, combat scoring, and every per-deck engine are untouched.

## How to read the deltas

The fleet got roughly one turn slower, and the size of the drop is a direct
readout of how much a deck leaned on the bug:

- **lethalProxy** falls everywhere. The steepest early-turn drops are decks that
  chained several cheap bodies per turn (tidal-legion T5 7.4 → 0.0, verdant-tide
  5.9 → 0.0, gathering-shadow T5 24.0 → 5.9). T8 losses are milder (typically
  15–25 points) because by then the real pool is large enough to deploy.
- **comboLethal** falls too, for two compounding reasons: the pieces themselves
  now have to fit one turn's mana, and the gate is checked against what is left
  *after* the main-phase filler casts. zada-hedron-grinder (T8 7.2 → 1.9) and
  anvil-chorus (3.8 → 1.9) are the clearest cases. Decks with no `kind:"combo"`
  win condition sit at 0.0 in both columns and are unaffected.
- **`deckHealthScore.score`** barely moves (≤0.5 in every deck) — its combo term
  reads `comboAssembly`, not the damage curve.
- **`global_health` and `global_health_normalized` are unchanged on all 21
  decks.** `win_turn` shifted on 18 of 21 (eternal-agony, grave-dividends and
  zada-hedron-grinder are identical), but never far enough to move
  `bracket_drag`, which is what feeds `global_health`.

## Follow-ups for the CEO's band re-fit

1. **The bands now sit above the fleet.** 13 of 21 decks cleared 30%
   lethalProxy at T7 before the fix; 4 do after — gathering-shadow (58.0),
   armory-protocol (35.3), tidal-legion (33.9), gandalf-party-guest (31.6). The
   `data/bracket-philosophy.md` "B4 Reality Check" thresholds and the
   `docs/deck-metrics.md` targets were fitted against double-spend curves and
   are deliberately left alone here.
2. **One new strategy-ceiling warning.** `validate_strategy_ceiling.py` exits 0
   with 2 warnings (was 1): grave-dividends was already flagged, and
   hidden-legion is new — its payoff reads LP@T7 23.9% → 13.2%, crossing the
   15% `payoff_floor`. That is the threshold meeting a corrected curve, not a
   deck regression.
3. **The combo gate is now filler-gated.** The goldfish casts proactive filler
   before the end-of-turn combo check, so a deck that taps out on filler cannot
   register a combo that turn even when holding the pieces — a real pilot would
   hold mana instead. Making the combo check pre-empt filler is a cast-priority
   change, explicitly out of scope for DEC-937; flagging it as a candidate
   follow-up for whoever owns the next goldfish sequencing pass.

## lethalProxy — % of games at or past the damage proxy by turn T

| deck | T5 | T6 | T7 | T8 | median turn |
|---|---|---|---|---|---|
| anvil-chorus | 1.4 → 0.0 | 8.4 → 0.7 | 28.4 → 9.5 | 54.2 → 35.9 | 8 → 9 |
| armory-protocol | 15.1 → 2.2 | 37.3 → 12.2 | 61.8 → 35.3 | 78.8 → 61.5 | 7 → 8 |
| broodfire-hatchery | 1.8 → 0.1 | 12.2 → 2.4 | 34.0 → 16.1 | 58.5 → 43.6 | 8 → 9 |
| creeping-corruption | 2.8 → 0.1 | 17.3 → 5.8 | 41.2 → 27.0 | 64.2 → 53.7 | 8 |
| eternal-agony | 2.4 → 0.1 | 11.2 → 3.7 | 28.9 → 18.9 | 47.5 → 41.1 | 9 |
| eternal-harvest | 3.0 → 0.2 | 13.9 → 5.0 | 35.8 → 21.0 | 58.9 → 46.7 | 8 → 9 |
| exponential-growth | 0.4 → 0.0 | 3.9 → 0.4 | 15.0 → 6.0 | 31.1 → 20.6 | 10 |
| gandalf-party-guest | 7.6 → 0.3 | 27.8 → 7.6 | 53.0 → 31.6 | 73.4 → 61.7 | 7 → 8 |
| gathering-shadow | 24.0 → 5.9 | 49.8 → 27.0 | 74.3 → 58.0 | 88.4 → 80.7 | 7 |
| grave-dividends | 0.1 → 0.0 | 0.8 → 0.0 | 4.0 → 1.1 | 11.5 → 6.8 | None |
| hidden-legion | 0.8 → 0.0 | 7.1 → 1.9 | 23.9 → 13.2 | 47.6 → 36.5 | 9 |
| hoard-and-bleed | 4.9 → 0.2 | 21.1 → 6.2 | 45.8 → 25.9 | 67.6 → 53.5 | 8 |
| shield-doctrine | 0.4 → 0.0 | 4.4 → 0.3 | 15.5 → 4.4 | 32.0 → 18.9 | 10 |
| slivers | 1.8 → 0.0 | 15.4 → 2.9 | 43.7 → 20.2 | 70.0 → 51.4 | 8 |
| stampede-acres | 5.0 → 0.0 | 22.6 → 5.1 | 47.7 → 25.4 | 67.5 → 53.6 | 8 |
| the-white-forge | 0.2 → 0.0 | 1.5 → 0.2 | 7.9 → 2.6 | 23.8 → 15.2 | 10 |
| tidal-legion | 7.4 → 0.0 | 28.9 → 4.4 | 59.4 → 33.9 | 79.2 → 71.0 | 7 → 8 |
| titan-convergence | 4.5 → 0.8 | 14.7 → 5.4 | 32.0 → 18.8 | 52.4 → 40.0 | 8 → 9 |
| verdant-tide | 5.9 → 0.0 | 26.2 → 4.5 | 54.6 → 27.5 | 76.8 → 60.5 | 7 → 8 |
| witherbloom-the-balancer | 0.9 → 0.1 | 6.8 → 2.9 | 21.4 → 14.3 | 41.9 → 34.5 | 9 |
| zada-hedron-grinder | 2.8 → 0.0 | 13.7 → 2.7 | 37.6 → 20.7 | 60.9 → 52.9 | 8 |

## comboLethal — % of games with a combo line assembled and payable by turn T

| deck | T5 | T6 | T7 | T8 | median turn |
|---|---|---|---|---|---|
| anvil-chorus | 1.5 → 0.1 | 2.2 → 0.3 | 3.0 → 0.9 | 3.8 → 1.9 | None |
| armory-protocol | 7.0 → 2.5 | 10.6 → 4.9 | 14.2 → 8.2 | 18.5 → 12.6 | None |
| broodfire-hatchery | 3.7 → 1.5 | 5.1 → 2.9 | 6.6 → 4.5 | 8.3 → 6.5 | None |
| creeping-corruption | 0.0 → 0.0 | 0.0 → 0.0 | 0.0 → 0.0 | 0.0 → 0.0 | None |
| eternal-agony | 6.9 → 3.0 | 10.1 → 5.9 | 13.9 → 9.4 | 17.9 → 13.8 | None |
| eternal-harvest | 16.1 → 6.3 | 23.3 → 11.6 | 29.9 → 18.2 | 35.9 → 25.4 | None |
| exponential-growth | 0.0 → 0.0 | 0.0 → 0.0 | 0.0 → 0.0 | 0.0 → 0.0 | None |
| gandalf-party-guest | 14.1 → 4.4 | 20.4 → 10.0 | 27.2 → 17.3 | 33.7 → 25.3 | None |
| gathering-shadow | 0.0 → 0.0 | 0.0 → 0.0 | 0.0 → 0.0 | 0.0 → 0.0 | None |
| grave-dividends | 2.4 → 1.8 | 4.5 → 3.7 | 7.7 → 6.7 | 11.8 → 10.8 | None |
| hidden-legion | 0.0 → 0.0 | 0.0 → 0.0 | 0.0 → 0.0 | 0.0 → 0.0 | None |
| hoard-and-bleed | 3.6 → 0.8 | 5.3 → 2.1 | 7.3 → 4.0 | 9.5 → 6.4 | None |
| shield-doctrine | 11.3 → 5.2 | 14.2 → 9.2 | 17.7 → 13.4 | 21.4 → 17.8 | None |
| slivers | 0.0 → 0.0 | 0.0 → 0.0 | 0.0 → 0.0 | 0.0 → 0.0 | None |
| stampede-acres | 6.9 → 2.9 | 9.0 → 5.4 | 11.2 → 8.5 | 13.9 → 11.7 | None |
| the-white-forge | 21.0 → 9.4 | 27.3 → 15.5 | 33.7 → 23.3 | 39.9 → 31.8 | 10 → None |
| tidal-legion | 0.0 → 0.0 | 0.0 → 0.0 | 0.0 → 0.0 | 0.0 → 0.0 | None |
| titan-convergence | 9.8 → 3.8 | 13.6 → 7.0 | 18.1 → 11.3 | 22.7 → 16.4 | None |
| verdant-tide | 0.0 → 0.0 | 0.0 → 0.0 | 0.0 → 0.0 | 0.0 → 0.0 | None |
| witherbloom-the-balancer | 0.0 → 0.0 | 0.0 → 0.0 | 0.0 → 0.0 | 0.0 → 0.0 | None |
| zada-hedron-grinder | 1.3 → 0.0 | 2.7 → 0.1 | 4.7 → 0.8 | 7.2 → 1.9 | None |

## deckHealthScore, metrics win_turn, global_health

| deck | health score | grade | win_turn best | typical | contested | global_health | normalized | gaps |
|---|---|---|---|---|---|---|---|---|
| anvil-chorus | 73.6 → 73.5 | B | 7 → 8 | 8 → 9 | 9 → 10 | 85 | 90 | 3 |
| armory-protocol | 77.9 | A | 5 → 7 | 7 → 8 | 8 → 9 | 79 | 85 | 2 |
| broodfire-hatchery | 65.1 → 65.0 | B | 7 | 8 → 9 | 9 → 10 | 79 | 84 | 2 |
| creeping-corruption | 68.4 → 68.3 | B | 6 → 7 | 8 | 8 | 92 | 92 | 0 |
| eternal-agony | 66.8 → 66.6 | B | 7 | 9 | 10 | 88 | 92 | 1 |
| eternal-harvest | 73.2 → 73.0 | B | 5 → 7 | 8 → 9 | 9 → 10 | 87 | 91 | 0 |
| exponential-growth | 81.6 → 81.5 | A | 7 → 8 | 9 → 10 | 10 → 11 | 76 | 81 | 4 |
| gandalf-party-guest | 76.4 → 75.9 | A | 6 → 7 | None | None | 88 | 93 | 0 |
| gathering-shadow | 74.5 → 74.4 | B | 5 → 6 | 7 | 8 | 92 | 97 | 0 |
| grave-dividends | 67.9 → 68.0 | B | 9 | None | None | 89 | 94 | 5 |
| hidden-legion | 67.5 | B | 7 → 8 | 9 | 9 | 93 | 93 | 1 |
| hoard-and-bleed | 70.8 | B | 6 → 7 | 8 | 9 | 97 | 101 | 0 |
| shield-doctrine | 82.0 | A | 6 → 8 | 10 | 11 | 87 | 92 | 0 |
| slivers | 71.1 | B | 6 → 7 | 8 | 8 | 89 | 89 | 1 |
| stampede-acres | 72.9 | B | 6 → 7 | 8 | 9 | 86 | 94 | 2 |
| the-white-forge | 76.1 → 76.0 | A | 4 → 6 | 10 | 11 | 88 | 92 | 0 |
| tidal-legion | 78.7 | A | 6 → 7 | 7 → 8 | 7 → 8 | 93 | 93 | 0 |
| titan-convergence | 72.3 → 72.2 | B | 7 | 8 → 9 | 9 → 10 | 65 | 73 | 4 |
| verdant-tide | 71.2 | B | 6 → 7 | 7 → 8 | 7 → 8 | 89 | 89 | 0 |
| witherbloom-the-balancer | 67.2 → 67.3 | B | 7 → 8 | 9 | 9 | 94 | 94 | 0 |
| zada-hedron-grinder | 65.8 → 65.7 | B | 7 | 8 | 8 | 84 | 85 | 2 |

## deckHealthScore components

| deck | manaReliability | threatDeployment | interactionDensity | comboConsistency | commanderIndependence |
|---|---|---|---|---|---|
| anvil-chorus | 78.4 → 78.0 | 99.6 | 78.3 | 50.0 | 46.8 |
| armory-protocol | 72.2 → 72.4 | 100.0 | 70.0 | 50.0 | 98.3 |
| broodfire-hatchery | 68.5 → 68.6 | 97.0 | 70.0 | 51.6 → 51.2 | 22.5 |
| creeping-corruption | 70.9 → 70.8 | 73.4 | 75.8 | 51.4 → 51.0 | 63.7 |
| eternal-agony | 71.0 → 71.2 | 61.4 | 70.0 | 55.8 → 54.3 | 72.1 |
| eternal-harvest | 73.8 → 73.6 | 80.8 | 73.1 | 52.8 → 52.0 | 82.2 |
| exponential-growth | 69.4 → 69.2 | 99.1 | 97.0 | 50.0 | 93.6 |
| gandalf-party-guest | 77.1 → 76.9 | 98.2 | 86.2 | 57.9 → 55.3 | 51.2 |
| gathering-shadow | 74.1 → 73.9 | 98.7 | 82.7 | 50.0 | 56.3 |
| grave-dividends | 75.6 → 75.9 | 53.9 | 84.5 | 52.2 → 52.0 | 64.9 |
| hidden-legion | 65.2 | 82.2 | 70.0 | 50.0 | 66.8 |
| hoard-and-bleed | 72.2 → 72.1 | 81.0 | 73.1 | 50.3 → 50.1 | 72.1 |
| shield-doctrine | 74.2 → 74.4 | 100.0 | 86.2 | 51.6 → 51.2 | 98.2 |
| slivers | 64.5 → 64.6 | 96.8 | 62.9 | 50.0 | 81.9 |
| stampede-acres | 71.9 → 71.8 | 99.5 | 73.1 | 50.9 → 50.7 | 61.6 |
| the-white-forge | 67.6 → 67.5 | 98.5 | 91.5 | 51.9 → 51.5 | 66.9 |
| tidal-legion | 81.1 → 80.9 | 82.2 | 93.3 | 50.0 | 78.6 |
| titan-convergence | 85.2 → 85.1 | 53.1 | 75.8 | 51.0 → 50.7 | 88.7 |
| verdant-tide | 82.8 → 82.9 | 89.0 | 44.2 | 50.0 | 81.3 |
| witherbloom-the-balancer | 82.8 → 83.1 | 72.0 | 58.9 | 55.1 → 54.8 | 53.0 → 53.2 |
| zada-hedron-grinder | 62.8 | 83.2 | 49.5 | 50.7 → 50.4 | 85.3 |
