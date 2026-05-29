# Deck Metrics (DEC-90 P7.1)

Deterministic, formula-driven metrics for every deck. Each metric is a 0–100 score with explicit inputs — no opinion, no LLM calls. Outputs land in `data/commanders/{id}/metrics.json` (computed by P7.5, DEC-119).

Why deterministic: metrics drive **gaps[]** (P7.6, DEC-120) which then drive **candidate enrichment** (P7.7, DEC-121). Anything subjective belongs in human review notes, not in the score.

Roles below refer to the closed set in [`role-taxonomy.md`](role-taxonomy.md).

## The 6 metrics

The original five (`manabase_health`, `role_coverage_health`, `curve_health`, `interaction_density`, `gameplan_cohesion`) are unchanged. DEC-308 adds `resilience_health` as the sixth and reweights `global_health`. Methodology bumped to `deck-metrics-v2`.

## Bracket mapping

Decks may declare `bracket: "3+"` or `bracket: "4+"`. The `+` suffix is a display flourish ("slightly above") — target-table lookups collapse it to the base bracket. The canonical mapping is:

| Declared | Effective bracket for target lookups |
|---|---|
| `"3"`, `"3+"` | 3 |
| `"4"`, `"4+"` | 4 |
| `"5"`, `"5+"` | 5 |
| `"1"`, `"2"` (not modeled) | clamped to 3 |

Every `metrics.json` carries the resolved `bracket_effective` alongside the declared `bracket` so the math is reproducible.


### 1. `manabase_health` (0–100)

Inputs: `decklist` lands (incl. MDFCs at 0.5 weight), `commander_color_identity`, oracle text patterns for tap/untap/fetch.

Sub-scores:

| Component | Weight | Formula |
|---|---|---|
| Karsten color compliance | 40 | For each color C in identity, target sources S(C) per Karsten table (see below). Score = mean over C of `min(actual_sources(C) / S(C), 1.0)` × 40 |
| Untapped land ratio | 30 | `(untapped_lands / total_lands) × 30`. Lands tapped only conditionally (e.g. shocks, painlands) count as untapped. |
| Fetch density | 15 | `min(fetches / 6, 1.0) × 15`. Counts true fetches (Polluted Delta), Fabled Passage, and pseudo-fetches (Evolving Wilds). |
| Land count fit | 15 | Bell curve around target = `35 + (avg_cmc × 1.5)`. Full credit ±1, half credit ±2, zero ≥3 off. |

**Karsten color sources** (from Frank Karsten's CFB study, 99-card singleton, 90% on-curve):

| CMC of cheapest spell of color C | Required sources of C |
|---|---|
| 1 (CC) | 20 |
| 1 (C) | 14 |
| 2 (CC) | 18 |
| 2 (C) | 13 |
| 3 (CCC) | 20 |
| 3 (CC) | 16 |
| 3 (C) | 12 |
| 4+ (C) | 10 |

Computed per color from the deck's actual mana costs. If multiple thresholds apply (e.g. both a 1-CC and 3-CCC card exist), use the strictest.

### 2. `role_coverage_health` (0–100)

Inputs: `decklist[].primary_role` + `decklist[].secondary_role` + `commanderRoles`, `bracket`, `commander_color_identity`.

Per-role target counts by bracket:

| Role | B3 | B4 | B5 |
|---|---|---|---|
| `ramp` | 10 | 10 | 12 |
| `card-draw` | 8 | 10 | 12 |
| `removal-spot` | 6 | 8 | 8 |
| `removal-board` | 2 | 3 | 3 |
| `protection` | 2 | 4 | 5 |
| `tutor` | 2 | 4 | 6 |
| `wincon` | 2 | 3 | 3 |
| `counterspell` * | 4 | 6 | 8 |

\* `counterspell` only contributes when blue ∈ `commander_color_identity`. For non-blue decks, the counterspell row is skipped (not zero — its weight is redistributed across the remaining rows).

Score:

```
per_role_score(R) = min(actual_count(R) / target(R), 1.2) × 100
                    # cap at 1.2 so massive overshoot doesn't mask gaps elsewhere
role_coverage_health = mean(per_role_score across applicable rows)
```

`actual_count` includes both `primary_role == R` and `secondary_role == R` (secondary at 0.5 weight) plus commander roles.

**`wincon` target adjustment by deck-level `wincon_style`** (overrides the bracket row above):

| `wincon_style` | wincon target | Engine substitution |
|---|---|---|
| `combo` | 1 | no |
| `value-incremental` | 1 | yes — `engine` cards count toward the wincon shortfall (capped at target so engine-stuffed decks don't double-credit) |
| `discrete-threats` | 2 | no |
| (unset) | bracket row above | no |

Rationale: a tuned combo deck closes off one assembled line; a value-incremental deck's engine *is* its closer (Meren chains, Zur fetches), so engines substitute for the missing wincon-tagged card; a discrete-threats deck must threaten on at least two independent axes to keep pressure under removal.

**`gaps[]`**: any role with `per_role_score < 70` is appended to `metrics.json`'s `gaps[]` array as `{role, actual, target, score}` (plus `wincon_style` on a wincon gap). Stored only in `metrics.json` (not `deck.json`) since it's derived state. The math behind every gap is reproducible from the inputs in `metrics.json` plus this doc.

### 3. `curve_health` (0–100)

Inputs: non-land cards' `cmc`. **Lands are excluded** (commander deck curves are conventionally drawn for spells only). MDFCs contribute 0.5 weight at their spell-side CMC.

Compute target curve based on archetype + bracket:

| Archetype family | Target avg CMC |
|---|---|
| `ramp-big-mana`, `eldrazi-colorless` | 4.2 |
| `tokens-go-wide`, `aristocrats` | 2.8 |
| `voltron`, `infect-poison` | 2.5 |
| `graveyard-reanimator`, `spellslinger` | 3.0 |
| (default / mixed) | 3.2 |

Score:

```
delta = abs(actual_avg_cmc - target_avg_cmc)
curve_health = max(0, 100 - delta × 25)
```

Plus a topcurve penalty: if `count(cmc >= 6) > 8`, subtract `(count - 8) × 5`.

### 4. `interaction_density` (0–100)

Inputs: counts of `removal-spot`, `removal-board`, `counterspell`, `protection` across the deck.

```
weighted = removal_spot × 1.0
         + removal_board × 2.0
         + counterspell × 1.5
         + protection × 1.0
         + (commander_interaction_bonus if commander has removal/counter/protection role)
target_by_bracket = {B3: 10, B4: 14, B5: 18}
interaction_density = min(weighted / target, 1.2) × 100  # same 1.2 cap as role_coverage
```

`counterspell` weight is preserved even in non-blue decks (since the count will be 0 anyway). The metric does not double-penalize.

### 5. `gameplan_cohesion` (0–100)

Inputs: non-land card count, `primary_role` distribution, `archetypes`, `wincon_style`.

Base: `% of non-land cards with primary_role ∈ {payoff, engine, wincon, threat}`.

Archetype-conditional extension — the cohesion set is widened when the archetype's gameplan structurally relies on a role:

| Archetype | Roles added to cohesion set |
|---|---|
| `graveyard-reanimator`, `aristocrats` | `recursion` |
| `tutor-heavy` (≥6 tutors), any combo-wincon deck | `tutor` |
| `tokens-go-wide`, `+1+1-counters` | `utility` (anthems / counter doublers tagged as utility still count) |
| `lands-matter`, `landfall` | `ramp` (extra lands and land-fetchers ARE the gameplan) |

Wincon penalty:
- `combo` wincon in **B3** deck: −15
- ≥2 `combo` wincons in **B4** deck: −10
- No `wincon` at all: clamp result to ≤50 (a deck with no closer is incoherent regardless)

### 6. `resilience_health` (0–100) — DEC-308

Inputs: `decklist[].primary_role` / `secondary_role` for `recursion` and `protection`; deck-root `wincon_style`; `winConditions[]` line count; cards tagged `recursion` or `engine` (for the rebuild-from-yard component); resolved `bracket_effective`.

Why: a single board wipe should not be a guaranteed loss. CRISPI and similar power-scoring frameworks treat recovery capacity as a first-class signal, and the original five metrics don't measure it at all. This metric does.

Components:

| Component | Weight | Formula |
|---|---|---|
| `recursion` | 30 | `min(recursion_count / recursion_target(wincon_style, bracket), 1.2) × 30`. `recursion_count` = primary + 0.5 × secondary on the `recursion` role, plus commander. |
| `redundancy` | 25 | `min((wincon_lines − floor(wincon_style)) / 2, 1.0) × 25`. Counts *extra* `winConditions[]` lines beyond the per-style floor — one redundant assembly is full credit. |
| `protection` | 25 | `min(protection_count / protection_target(bracket), 1.0) × 25`. Whole-deck protection count (primary + 0.5 × secondary + commander); not piece-overlap. |
| `gy_second_hand` | 20 | `min(gy_role_card_count / 6, 1.0) × 20`. `gy_role_card_count` = cards whose primary OR secondary role is in `{recursion, engine}`. Tag-only — no oracle-text re-derivation (see anti-double-counting below). |

`resilience_health = recursion + redundancy + protection + gy_second_hand` (rounded).

**Targets, branched on `wincon_style`:**

| `wincon_style` | recursion target (B3 / B4 / B5) | wincon line floor |
|---|---|---|
| `combo` | 1 / 2 / 2 | 1 |
| `value-incremental` | 3 / 4 / 5 | 1 |
| `discrete-threats` | 2 / 3 / 3 | 2 |
| `combat`, `drain`, `drain-x` | 2 / 3 / 4 | 1 |
| `mixed`, (unset) | 2 / 3 / 4 | 1 |

`mixed` is the deck-level value for multi-kind decks with no dominant plan (see [`role-taxonomy.md`](role-taxonomy.md#wincon_style)). It deliberately inherits the unset-row targets and the `max(comboLethal, lethalProxy)` win-turn curve so the metric stays honest when the deck closes on more than one axis.

Protection target (bracket-only): B3 = 2, B4 = 4, B5 = 5.

Rationale: a tuned `combo` deck closing on T6 doesn't need five recursion slots; punishing it for that double-counts the closed-doors archetype against itself. A `value-incremental` deck *does* need a deep recursion bench because it has to outlast multiple wipes. `discrete-threats` decks must threaten on at least two independent axes by definition, so their wincon floor is 2 — beyond which redundancy still scales.

**Anti-double-counting:** `gy_second_hand` is constrained to cards already tagged `recursion` or `engine`. Oracle-text re-derivation is explicitly forbidden — every Animate Dead, every Reanimate would otherwise count three times (recursion role → recursion component, "from your graveyard" text → re-counted, and again as the engine half). The intent of this component is "the deck rebuilds its hand from the yard", which is the engine half of the recursion universe (Deep Analysis, Snapcaster, Bone Shards on engine creatures, …). Set overlap between the `recursion` and `gy_second_hand` populations is by design and is bounded by the hard `min(count/6, 1) × 20` cap.

**`gaps[]` surfacing:** any component whose percentage-of-max is `< 70` is appended to `metrics.json`'s `gaps[]` as `{resilience_component, score_pct, max, ...}` (with component-specific fields — actual/target for recursion/protection/gy, lines/floor for redundancy, and `wincon_style` on recursion/redundancy entries). This rides the same `gaps[]` feed that role-coverage already uses, so candidate enrichment (P7.7) can prioritize cards that close a resilience gap just like it prioritizes role gaps.

### Confidence band: `confidence_margin` (±2…±15) — DEC-310

`global_health` is presented to the reader as **`{score} ± {margin}`**. The margin is a data-completeness uncertainty channel, not a quality channel — it widens when the underlying tags or sibling files are missing/stale, and narrows when the deck is fully tagged and the sibling files are current. Letter grade renders as a single letter (A/B/C/D/F); the margin number is the only uncertainty signal.

Inputs:

| Trigger | Effect |
|---|---|
| (baseline) | `default = 5` |
| Non-land card with unset `primary_role` | `+1` per card, capped at `+15` |
| Commander deck without `wincon_style` | `+6` |
| Empty `archetypes` array | `+6` |
| `simulation.json` missing | `+10` |
| `candidates.json` missing **or** `generated_at` older than 90 days | `+6` |
| `resilience_health` components with non-zero signal `< 4` (data-completeness on the recovery axis) | `+3` |
| **Bonus floor**: all of `{archetypes set, wincon_style set, role_coverage_health.score ≥ 100, simulation present, candidates within 30 days}` | clamp to `±2` |

Final:

```
margin = clamp(default + penalties − bonuses, 2, 15)
```

The cap was lowered from `±25` to `±15` deliberately — a band that spans three full letter grades is presentationally useless (an "82 ± 22" deck could be anywhere between F and A and the reader learns nothing).

Implementation detail: `candidates.json` carries an internal `generated_at` timestamp (written by `scripts/generate_candidate_pool.py`); the margin reads that and falls back to file mtime only if the field is missing.

### Win-turn triple: `win_turn` (DEC-311)

`win_turn` is **derivation, not modelling** — it is a presentation layer over the existing per-turn lethality curves in `simulation.json.goldfish.byTurn["{T}"]`. Three numbers (`best`, `typical`, `contested`) summarise *when* the deck closes; the underlying curves are unchanged and still consulted by DEC-309's strategy-ceiling check.

**Payoff curve** is picked by deck-level `wincon_style`. If the deck's card-level `wincon_style` tags also mix `combo` with any non-combo kind (`combat`, `drain`, `drain-x`, `discrete-threats`, `tokens`, `mill`, `alt`), the deck is treated as *multi-kind* and falls through to `max`. This matches the heuristic used in [`scripts/validate_strategy_ceiling.py`](../scripts/validate_strategy_ceiling.py) so the two metrics agree on what counts as mixed.

| Deck-level `wincon_style` | Multi-kind? | `payoff_curve(T)` |
|---|---|---|
| `combo` | no | `byTurn["{T}"].comboLethal` |
| `combat`, `drain`, `drain-x`, `discrete-threats` | no | `byTurn["{T}"].lethalProxy` |
| `value-incremental` *or* unset *or* any multi-kind | — | `max(comboLethal, lethalProxy)` |

**Thresholds:**

| Name | Definition |
|---|---|
| `best` | lowest `T` where `payoff_curve(T) ≥ 15%` |
| `typical` | lowest `T` where `payoff_curve(T) ≥ 50%` |
| `contested` | `typical + interaction_drag(bracket)`, drag = `{B3: 0, B4: 1, B5: 2}` |

The **`best` floor is locked to DEC-309's [`PAYOFF_FLOOR`](../scripts/validate_strategy_ceiling.py)** (`15.0`) — both consumers MUST read the same number, so the strategy-ceiling check and the Vitals readout never disagree on what "the payoff is real" means. If DEC-309 retunes its floor, retune the `WIN_TURN_BEST_THRESHOLD` constant in `scripts/compute_deck_metrics.py` to match in the same PR.

**Suppression rules** — surface honest absences, never fabricate:

- `simulation.json` missing → omit the entire `win_turn` block (`null`).
- The selected payoff curve is flat at `0.0` across every simulated turn → omit the entire block. Surfacing three em-dashes is noise.
- `typical` not reached inside the simulated window (`T1`…`window_last_turn`) → render `typical = null`. **Also suppress `contested`** — without an anchor, the offset is meaningless.
- `best` is allowed to stand on its own when `typical` is `null`; this is the honest reading for combat decks whose 50% lethality lands past the simulated window.

**Output shape** (top-level field on `metrics.json`):

```json
"win_turn": {
  "best": 6,
  "typical": 7,
  "contested": 7,
  "source": "lethalProxy",
  "bracket_drag": 0,
  "thresholds": { "best": 15.0, "typical": 50.0 },
  "window_last_turn": 10
}
```

`source` records which curve was consumed (`comboLethal` | `lethalProxy` | `max`); `bracket_drag` and `thresholds` are echoed back so the math is reproducible from the file alone.

The Vitals card on the Apothecary surface renders this triple as `Best / Typical / Contested` alongside `global_health`. When the whole block is suppressed (sim missing or curve flat), the Vitals slot renders no win-turn row at all.

### Global blend: `global_health` (0–100)

```
global_health = 0.25 × manabase_health
              + 0.25 × role_coverage_health
              + 0.15 × curve_health
              + 0.15 × interaction_density
              + 0.10 × gameplan_cohesion
              + 0.10 × resilience_health
```

Mana and roles still co-dominate at 50% combined — they remain the most actionable failure modes. Cohesion and resilience share equal floor weight at 10% each: directional signals, not verdicts. See the [DEC-308 calibration subsection](#calibration-snapshot-2026-05-29-all-15-decks-resilience_health-added) below for the A/B/C comparison and the rationale for picking option A.

## Output schema (`data/commanders/{id}/metrics.json`)

```json
{
  "deck_id": "dark-dominion",
  "methodology": "deck-metrics-v2",
  "generated_at": "2026-05-29T12:00:00Z",
  "bracket": "4+",
  "bracket_effective": 4,
  "weight_option": "A",
  "weights": { "manabase": 0.25, "role": 0.25, "curve": 0.15, "interaction": 0.15, "cohesion": 0.10, "resilience": 0.10 },
  "metrics": {
    "manabase_health":      { "score": 82, "components": { "karsten": 40.0, "untapped": 29.2, "fetch": 5.0, "land_count": 7.5 } },
    "role_coverage_health": { "score": 86, "by_role": { "ramp": 100, "card-draw": 70, "removal-spot": 90, "removal-board": 66, "protection": 50, "tutor": 100, "wincon": 100, "counterspell": 83 } },
    "curve_health":         { "score": 95, "actual_avg_cmc": 2.58, "target_avg_cmc": 2.8 },
    "interaction_density":  { "score": 118, "weighted": 16.5, "target": 14 },
    "gameplan_cohesion":    { "score": 24, "in_set_pct": 0.24, "archetype_extensions": ["recursion"] },
    "resilience_health":    {
      "score": 88,
      "components": {
        "recursion":      { "score": 30.0, "actual": 4.5, "target": 2, "max": 30 },
        "redundancy":     { "score": 25.0, "lines": 9, "floor": 1, "max": 25 },
        "protection":     { "score": 13.8, "actual": 2.0, "target": 4, "max": 25 },
        "gy_second_hand": { "score": 20.0, "actual": 13.0, "target": 6, "max": 20 }
      },
      "inputs": { "wincon_style": "value-incremental", "bracket_effective": 4 }
    }
  },
  "global_health": 85,
  "confidence_margin": 5,
  "win_turn": { "best": 6, "typical": 7, "contested": 8, "source": "max", "bracket_drag": 1, "thresholds": { "best": 15.0, "typical": 50.0 }, "window_last_turn": 10 },
  "gaps": [
    { "role": "protection", "actual": 2, "target": 4, "score": 50 },
    { "resilience_component": "protection", "score_pct": 55, "max": 25, "actual": 2.0, "target": 4 }
  ]
}
```

`gaps[]` is the **single feed** into the candidate-enrichment step (P7.7) — that step prioritizes candidate cards whose `primary_role` matches a gap.

## A–F grade table (DEC-90 P8.1)

The Vitals card on each deck page renders `global_health` as a letter grade. Provisional thresholds:

| Grade | `global_health` range |
|---|---|
| A | 90–100 |
| B | 80–89 |
| C | 70–79 |
| D | 60–69 |
| F | <60 |

### Calibration snapshot (2026-05-04, all 9 built decks)

| Deck | global | mana | role | curve | int | cohesion | grade |
|---|---:|---:|---:|---:|---:|---:|---|
| creeping-corruption | 86 | 83 | 81 | 92 | 120 | 47 | B |
| genesis-protocol | 84 | 80 | 97 | 82 | 120 | 11 | B |
| the-white-forge | 84 | 69 | 103 | 87 | 120 | 14 | B |
| mutant-multiplication | 82 | 84 | 66 | 90 | 118 | 57 | B |
| dark-dominion | 78 | 74 | 72 | 96 | 114 | 29 | C |
| eternal-agony | 76 | 75 | 65 | 98 | 94 | 55 | C |
| verdant-tide | 76 | 69 | 88 | 79 | 80 | 47 | C |
| eternal-harvest | 73 | 71 | 60 | 98 | 93 | 46 | C |
| titan-convergence | 58 | 69 | 62 | 0 | 93 | 44 | F |

The spread is sane: tuned B4 builds cluster B (80–89), competent-but-incomplete builds land C (70–79), and a single outlier (titan-convergence, hit by curve=0 from avg CMC 5.58 + topcurve penalty) earns the F. No deck currently scores A — re-tune thresholds once a deck legitimately reaches 90+ on the global blend; if A becomes unreachable in practice, lower the bar to 88+ rather than handing out A grades to merit-B decks.

The Vitals card sources this score and grade from `metrics.json` only.

### Calibration snapshot (2026-05-29, all 15 decks, `resilience_health` added)

Component scores (`mana`, `role`, `curve`, `int`, `cohesion`, `resilience`) are weight-option-independent. The three columns project `global_health` under DEC-308's three candidate weight tuples; the chosen option is **A** (committed as `DEFAULT_WEIGHT_OPTION` in `compute_deck_metrics.py`).

| Deck | mana | role | curve | int | cohesion | resilience | A (25/25/15/15/10/10) | B (28/28/14/14/8/8) | C (30/25/15/12/8/10) | A grade | margin |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|---:|
| silverquill-the-disputant | 85 | 100 | 93 | 120 | 54 | 106 | 94 | 94 | 94 | A | ±11 |
| witherbloom-the-balancer | 71 | 109 | 100 | 120 | 50 | 94 | 92 | 93 | 91 | A | ±2 |
| aziza-mage-tower-captain | 75 | 99 | 94 | 120 | 40 | 106 | 90 | 90 | 90 | A | ±5 |
| creeping-corruption | 82 | 94 | 92 | 120 | 47 | 70 | 88 | 88 | 87 | B | ±8 |
| the-white-forge | 69 | 103 | 87 | 120 | 19 | 106 | 87 | 87 | 86 | B | ±2 |
| zada-hedron-grinder | 69 | 104 | 88 | 102 | 38 | 106 | 86 | 87 | 86 | B | ±2 |
| dark-dominion | 82 | 86 | 95 | 118 | 24 | 88 | 85 | 86 | 85 | B | ±5 |
| hidden-legion | 64 | 100 | 95 | 120 | 32 | 85 | 85 | 85 | 84 | B | ±2 |
| eternal-agony | 75 | 86 | 100 | 120 | 45 | 66 | 84 | 85 | 84 | B | ±5 |
| superfriends-esika | 62 | 107 | 82 | 120 | 33 | 80 | 84 | 85 | 83 | B | ±2 |
| pyre-and-panic | 70 | 85 | 98 | 120 | 47 | 68 | 83 | 83 | 82 | B | ±8 |
| eternal-harvest | 69 | 79 | 100 | 104 | 50 | 81 | 81 | 80 | 80 | B | ±8 |
| mutant-multiplication | 86 | 72 | 97 | 89 | 52 | 64 | 79 | 80 | 80 | C | ±8 |
| verdant-tide | 71 | 91 | 80 | 80 | 44 | 70 | 76 | 77 | 76 | C | ±8 |
| titan-convergence | 69 | 75 | 0 | 93 | 44 | 71 | 61 | 63 | 61 | D | ±5 |

**DEC-310 margin distribution** (15 decks): no margin exceeds ±15 (acceptance), max is ±11 on silverquill (its `wincon_style` is currently unset, which the metric correctly flags as a data gap). Five decks reach the ±2 floor — every one of them has full archetype + wincon tagging, ≥100 role-coverage score, a present `simulation.json`, and a `candidates.json` regenerated within the last 30 days. The remaining ten decks land at ±5 or ±8, dominated by `wincon_style` not yet tagged on older builds and one or two slightly stale `candidates.json` files (>90 days). This is the metric working as intended: it points review effort at decks whose underlying tagging is the bottleneck, not their gameplay quality.

**Why option A was chosen** against the invariants from DEC-308:

1. *No previously-B deck regresses to F*: confirmed for all three options.
2. *Top-rank preservation across the prior-snapshot decks*: among the eight decks that existed in the [2026-05-04 snapshot](#calibration-snapshot-2026-05-04-all-9-built-decks), `creeping-corruption` and `the-white-forge` remain the top two under A. `mutant-multiplication` drops from prior-B to C (79 under A; 80 under B and C) — this is the metric working as intended: its resilience component (`64/100`) reflects an actual recovery gap, not a tuning artefact, and B/C only just barely save it. All three options agree on the direction; A is the cleanest reading.
3. *titan-convergence remains the outlier*: lifts from F (58) to D (61 under A, 63 under B, 61 under C). The lift is driven by a legitimate `resilience_health = 71` — titan does have meaningful recursion + protection density. The deck remains the lowest-scoring build by a 15-point margin, so it stays the outlier in spirit even though it crosses the F/D boundary in letter. Option A and C share the smallest lift (+3). Picking A preserves spend-pattern intuition (mana + roles equally weighted at the top).
4. The A↔B↔C spread is at most 2 points for any single deck — the choice is genuinely cosmetic at the margin, so the simplest defensible tuple wins.

Three new entrants score A under all three options (silverquill, witherbloom, aziza) because their recursion + protection density is structurally strong for their bracket — they're the first decks in the project to legitimately clear the A bar. This validates DEC-308's premise: resilience was the missing axis that distinguished a "tuned" B4 build from an "A-grade" one.

## Why these formulas

Each formula is auditable and reversible. If a metric reads poorly on a known-good deck, the failing component is visible in the JSON output, and the formula can be tuned in this doc (with version note) — not by editing per-deck overrides.

The cap at 1.2× target across role coverage and interaction is the main anti-Goodhart guard: piling 25 ramp cards doesn't paper over a missing wincon.
