## DEC-935 — sim model recommendation, v2 (self-reviewed against the code)

**Recommendation (revised): change the goldfish in two phases. Phase 1 now: an Atla hatch engine plus a team-haste rule, keyed to this deck, built in the existing commander-engine pattern. Phase 2 later, only if the board wants it after seeing Phase 1's curve: extra combats and power multipliers, which need a metadata extension first. Do not build a combat simulator.**

This version fixes four things in v1: it phases the work instead of bundling four models; it corrects one overstated claim; it drops Lightning Greaves from the haste set; and it names the acceptance criteria the child issue would carry. Every code claim below was re-read in `scripts/export_simulation_results.py` this heartbeat.

### 1. Facts (verified)

| Claim | Where | Status |
|---|---|---|
| Creatures enter only by cast from hand; no hatch path exists | `simulate_goldfish_game`; the deck's sim module says the hatch loops are "measured by the shared goldfish", which has no such model | confirmed |
| Combat per creature = min(8, mana value), +1 for one evasion keyword, from the turn after entry | `build_goldfish_profile` lines 1322–1326; `combatReadyTurn = turn + 1` line 2020 | confirmed |
| Lethal proxy = 40 cumulative damage | `GOLDFISH_LETHAL_DAMAGE_PROXY = 40`; `metrics_from_board` | confirmed |
| No haste, no double strike, no doublers, no extra combats in the shared model | only the DEC-405 deploy engine handles a haste back face and double-strike Equipment, for its own commander | confirmed |
| Four commander engines exist as config block + code path, keyed by deck id | `COMMANDER_CASCADE`, `COMMANDER_COPY_ENGINE`, `COMMANDER_TOKEN_ENGINE`, `COMMANDER_DEPLOY_ENGINE` | confirmed |
| A free put-onto-the-battlefield path already exists and is reusable | DEC-405: "Free put-onto-battlefield, not a cast: it re-credits resolution effects but never triggers cast-gated models" via `resolve_cast_effects`; DEC-385 cascade digs the library the same way | confirmed |
| Mana-gated activations already exist | DEC-405 transform: "affordability-checked against the turn pool exactly like every other cast" | confirmed |
| Card metadata carries no power or toughness | `data/card-metadata.json` fields: cmc, colors, layout, mana_cost, oracle_text, type_line | confirmed — this is why Phase 2 needs a metadata extension |
| The goldfish is seeded | `random.seed(seed)` per chunk | confirmed — a control deck can be re-exported and must come out byte-identical |
| Precedent engine size | DEC-404 109 lines, DEC-385 166, DEC-393 170, DEC-405 189 (exporter diff) | confirmed |
| `win_turn` and the strategy-ceiling check read `lethalProxy` for combat decks | `compute_deck_metrics.py` DEC-311 branching; `validate_strategy_ceiling.py` | confirmed |

Correction to v1: I wrote that the deck's "brewing until the sim confirms the turn-6 kill rate" gate "cannot be met by any combat deck". That is too strong — a fast enough combat deck can reach 50% lethal proxy at turn 6 on the cast-only model (armory-protocol reads 37% there). The accurate statement: the gate cannot be met by *this deck's plan* as modeled, because the plan's damage comes from hatched creatures the model never puts on the battlefield.

### 2. Phase 1 — Atla hatch engine + team haste (this deck only)

**Hatch engine** (`COMMANDER_HATCH_ENGINE["broodfire-hatchery"]`, on by default):
- Gate: Atla on the battlefield and at least one outlet on the battlefield. Outlet set: Ashnod's Altar, Phyrexian Altar, Goblin Bombardment (free, unlimited); Skullclamp ({1} per Egg); High Market (one per turn). Natural Order and Greater Good are not outlets here (one-shot; discard cost).
- Activations per turn: after the turn's casts, spend leftover mana in pairs on Egg activations, at most one per Atla untap. Untaps: 1 on your turn; +3 per turn cycle while Seedborn Muse is on the battlefield (opponents' untap steps also untap the lands, so those three cost nothing from the turn pool); +1 per Thornbite Staff death while an altar is out, capped. Cap Eggs at 4 per turn cycle before doublers.
- Egg doublers: Mondrak, Glory Dominus and Elspeth, Storm Slayer each double the Egg count (×4 with both, CR 616).
- Hatch resolution: for each Egg killed, scan the library from the top, put the first creature card onto the battlefield through the existing free-put path (credits impact, combat and draw like a free cast; never re-triggers cast-gated models), bottom the cards passed. Annie Joins Up and Roaming Throne (Shaman) each add one hatch per Egg. Raph & Mikey add one hatch per combat while combat-ready. Cap total hatches at 8 per turn so the model never runs the Thornbite loop to exhaustion — that infinite is already scored by `comboLethal` through the existing slot spec.
- Anything the model does not see stays a floor: hatching on opponents' end steps, Palani's Hatcher's beginning-of-combat sacrifice, Zopandrel's and Mondrak's paid outlets, Identity-Echo-style effects.

**Team-haste rule** (`COMMANDER_HASTE_SOURCES["broodfire-hatchery"]`, generic mechanism, this deck the only one opted in):
- While any of Rhythm of the Wild, Samut, Hazoret's Champion or Rising of the Day is on the battlefield, or Palani's Hatcher and Maskwood Nexus both are, creatures that enter (cast or hatched) get `combatReadyTurn = entry turn`. Rhythm's riot is "nontoken", and the goldfish's creatures are all cards, so no exception is needed. Lightning Greaves is out of the set (one creature, sorcery-speed equip; v1 listed it wrongly). Xenagos's haste half waits for Phase 2 with its doubling half.

**Acceptance criteria for the child issue**
1. Unit tests: no hatch without Atla; no hatch without an outlet; Egg count with and without Seedborn and each doubler; hatch bottoms non-creatures and puts exactly one creature per hatch; caps hold; haste rule sets the ready turn only while a source is on the battlefield.
2. Re-export broodfire; re-export one control deck without the engine (stampede-acres) and confirm its `simulation.json` is byte-identical — the RNG is seeded, so any change there means the shared path was touched.
3. `compute_deck_metrics.py --deck broodfire-hatchery` and `validate_strategy_ceiling.py` run clean and pick the new curve up without code changes.
4. The exporter's methodology text for the deck names the engine, its caps and its floors, as the other four engines do.

Size: about the DEC-405 engine (roughly 200–300 lines with tests). Tier 2, one engineer, reviewed by me against the list above.

### 3. Phase 2 — extra combats and power multipliers (decision deferred)

Not in the child issue. Reasons: (i) the goldfish has no printed power, so Tifa's power-7 gate, Xenagos's "+X where X is its power" and the doublers would run on the mana-value proxy unless `fetch_card_metadata.py` first adds front-face power and toughness (one-time churn across about 1,500 cached cards); (ii) the multiplier rules (first-combat clauses, Celebrant's exert, Annie doubling Aurelia and Tifa, Zopandrel compounding per combat) carry more modelling assumptions than Phase 1 and are the part most likely to be argued about; (iii) Phase 1 alone may already move the curve enough to answer the board's question. When the board wants Phase 2, it starts with the metadata extension, keeps the combat proxy for all existing decks unchanged (comparability), and applies the multipliers only to decks that opt in — shield-doctrine, armory-protocol, slivers, zada and four double-strike carriers would be candidates, each followed by a re-run of the DEC-559 calibration extract.

### 4. What stays as in v1

No hand-tuned bonus or threshold change; no opponents or blockers; no change to the metrics layer; the 40-damage proxy stays. I will not predict the Phase 1 curve; if it still reads below the turn-6 bar, that is a fact about the deck.

### 5. Decision asked of the board

Approve opening the Phase 1 engineering child issue (hatch engine + team-haste rule for this deck, acceptance criteria above). Reject means the goldfish stays a mana-and-curve measure for this deck and I record in the deck's sources that its brewing gate is not sim-based.
