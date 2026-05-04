# Deck Metrics (DEC-90 P7.1)

Deterministic, formula-driven metrics for every deck. Each metric is a 0–100 score with explicit inputs — no opinion, no LLM calls. Outputs land in `data/commanders/{id}/metrics.json` (computed by P7.5, DEC-119).

Why deterministic: metrics drive **gaps[]** (P7.6, DEC-120) which then drive **candidate enrichment** (P7.7, DEC-121). Anything subjective belongs in human review notes, not in the score.

Roles below refer to the closed set in [`role-taxonomy.md`](role-taxonomy.md).

## The 5 metrics

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

### Global blend: `global_health` (0–100)

```
global_health = 0.30 × manabase_health
              + 0.30 × role_coverage_health
              + 0.15 × curve_health
              + 0.15 × interaction_density
              + 0.10 × gameplan_cohesion
```

Mana and roles dominate because they're the most actionable failure modes. Cohesion is intentionally low-weight — it's a directional signal, not a verdict.

## Output schema (`data/commanders/{id}/metrics.json`)

```json
{
  "deck_id": "dark-dominion",
  "generated_at": "2026-05-04T12:00:00Z",
  "bracket": "4",
  "metrics": {
    "manabase_health": { "score": 78, "components": { "karsten": 30.4, "untapped": 24.0, "fetch": 7.5, "land_count": 15.0 } },
    "role_coverage_health": { "score": 82, "by_role": { "ramp": 100, "card-draw": 70, "removal-spot": 90, "removal-board": 66, "protection": 50, "tutor": 100, "wincon": 100, "counterspell": 83 } },
    "curve_health": { "score": 88, "actual_avg_cmc": 2.9, "target_avg_cmc": 2.8 },
    "interaction_density": { "score": 91, "weighted": 12.5, "target": 14 },
    "gameplan_cohesion": { "score": 74, "in_set_pct": 0.76, "archetype_extensions": ["recursion"] }
  },
  "global_health": 81,
  "gaps": [
    { "role": "protection", "actual": 2, "target": 4, "score": 50 },
    { "role": "removal-board", "actual": 2, "target": 3, "score": 66 }
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

The Vitals card sources this score and grade from `metrics.json` only — no `recommendations.json` fallback.

## Why these formulas

Each formula is auditable and reversible. If a metric reads poorly on a known-good deck, the failing component is visible in the JSON output, and the formula can be tuned in this doc (with version note) — not by editing per-deck overrides.

The cap at 1.2× target across role coverage and interaction is the main anti-Goodhart guard: piling 25 ramp cards doesn't paper over a missing wincon.
