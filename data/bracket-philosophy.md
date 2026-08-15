# Bracket 4/5 Deckbuilding Philosophy

Source: [Command Zone Episode 731](https://www.youtube.com/watch?v=jzeTz9clIC8) (2026-03-17) — Rachel Weekes + Joe Johnson

## Mana Base

- Zero tapped lands turns 1-3. Fetches, shocks, pain lands, fast lands, utility lands only.
- Acceptable tapped lands: Triomes IF fetchable in-deck (they're searchable ramp targets), Bojuka Bog (free graveyard hate from a land slot).
- Cut at B4+: Vivid lands, Thriving lands, bounce lands, Path of Ancestry, Evolving Wilds, tap duals, cycling duals (Canyon Slough etc.), Seaside Citadel-style trilands.
- Filter lands ({1},{T}: Add {C}{C}) are effectively dead on T1 — avoid in B5.

## Fast Mana

**Bracket 4 minimum:**
- Sol Ring (universal)
- Chrome Mox (any deck with colored spells to exile — produces colored mana)
- Ancient Tomb (any deck)
- Green: all 1-mana dorks (Birds of Paradise, Llanowar Elves, Elvish Mystic, Elves of Deep Shadow, etc.)

**Bracket 5 adds:**
- Mana Vault (any deck — strong in colorless/mono, weaker in 3+ color without untap effects)
- Mox Diamond, Lotus Petal, Jeweled Amulet (if budget allows)
- Jeska's Will (red decks — early Jeska's Will is devastating)
- Dark Ritual (black decks)

**Note:** Mana Vault ({C}{C}{C}) is weaker in 3+ color decks without untap effects. Evaluate per-deck.

## Free Spells (Mandatory by Color)

**Bracket 4:**
- Blue: Force of Will, Fierce Guardianship
- Black: Deadly Rollick
- Red: Deflecting Swat

**Bracket 5 adds:**
- Blue: Force of Negation, Pact of Negation
- Black: Snuff Out (4 life, free instant removal)
- Blue: Misdirection (redirect spell)

## Interaction

- Instant speed only for targeted removal. Sorcery-speed spot removal is unplayable at B4+ speed.
- Sorcery-speed board wipes are acceptable. Toxic Deluge is the premier B4+ wipe. Blasphemous Act is a "bracket 3 card" — too slow, often one-sided when boards are large.
- Cultivate / Kodama's Reach are B3 cards — at B4+ use creature ramp (dorks), 2-mana land tutors (Nature's Lore, Three Visits, Rampant Growth), or artifact rocks.

## Card Quality

- Every card must impact the turn it enters. Do not play expensive permanents and pass (e.g., Doubling Season on an empty board = "5 mana, lose").
- Permanent-based > instants/sorceries where possible. Bodies synergize with sacrifice engines, Gaea's Cradle, token doublers, etc.
- Creature tutors feel less threatening than spell tutors — opponents are less likely to counter them.
- Redundancy over unique effects. Multiple cards doing the same job ensures consistency.
- Plan A/B/C resilience: every card should have a role so you never draw dead.

## Threat Assessment

- Know when something is another player's problem. Leave Rest in Peace up if opponents need graveyard more than you.
- "You must bolt the bird" — early removal to disrupt combo setups is mandatory at B4+.
- Blue players get focused down fast at B4. Hard to go one-for-one with counterspells vs 3 opponents.

## Game Pacing (B4)

- Average 45 min to 1.5 hours, 5-7 turns.
- ~50% combo wins, ~50% creature/non-creature damage.
- Turns 1-2: fast mana, dorks, early value.
- Turns 3-4: board established, 7-8 permanents.
- Attempt to kill by turn 6. Stumbling is very hard to recover from.

---

## B4 Reality Check (Operational)

Added from DEC-205 (2026-05-12). The CZ731 principles above tell you HOW to build a B4 deck. This section tells you WHETHER a candidate deck actually qualifies — a quantitative test using the `comboLethal` / `lethalProxy` curves in `data/commanders/{id}/simulation.json`.

### Kill-turn thresholds

Read the proxy curve from the deck's `simulation.json` → `goldfish.byTurn[T].comboLethal` (combo decks) or `lethalProxy` (combat decks):

| Reading | Classification |
|---|---|
| comboLethal/lethalProxy **≥ 50% at T6** | **True B4** — reliable T5-T7 win window |
| < 50% T6, **≥ 50% at T7** | **Soft B4** — CAN win in the window, doesn't always |
| < 50% at T7 | **B3-B4 borderline** — the combo plan exists but isn't reliable; deck plays as a value pile |
| **≥ 60% at T4-T5** | Approaching B5 / cEDH territory |

These cutoffs apply to the proxy as a *floor* (real-game readiness is higher — see caveats below).

### comboLethal proxy schema (cross-link)

The proxy lives in `scripts/export_simulation_results.py`. Its v2 model substitutes for missing combo pieces via: (1) bargain free-cast tutor (Beseech-style), (2) type-matched regular tutor, (3) reanimation for permanent pieces. Decks must tag the right fields to be read correctly:

- `winConditions[].kind: "combo"` + `winConditions[].pieces: [card names]` — without these, comboLethal stays 0.
- `decklist[].tutor_targets: ["instant", "sorcery"]` — restrict tutors that can't fetch creatures/planeswalkers (e.g., Mystical Tutor, Spellseeker). Default `["any"]`.
- `decklist[].tutor_mv_cap: N` — restrict tutors that have an MV cap (e.g., Spellseeker MV ≤ 2). Default `null`.
- `decklist[].tutor_free_cast_via_bargain: true` — Beseech the Mirror and similar bargain-tutor cards.
- `decklist[].primary_role: "recursion"` (or `secondary_role`) — for reanimation spells (Reanimate, Animate Dead, etc.).

Forgetting these tags will under-count comboLethal and make a real B4 deck look weaker than it is.

### Tainted Pact gotcha

If you add **Tainted Pact** as a Consultation-style finisher, the deck must be singleton-name everywhere — including basics. Convention: 1 of each basic + non-basic duals. Pact's "exile two cards with the same name" stop condition fires on duplicate basics and leaves your library mostly intact, breaking the Thoracle/Jace/Lab Maniac win. The same constraint applies to Doomsday-style pile cards. Demonic Consultation does NOT have this constraint.

### Budget tiers (from DEC-205 path negotiation)

When pushing a deck toward B4 reliability, these are the rungs in approximate cost:

- **Tier X — Ultra-budget (~$5):** Laboratory Maniac + cantrips (Brainstorm, Ponder, Preordain, Opt). Adds a 3rd wincon-permanent + deck-thinning dig. Estimated comboLethal T6 gain: +5-10%.
- **Tier Y — Mid (~$30-40):** Tier X + ONE premium universal tutor (Demonic Tutor or Vampiric Tutor). Estimated T6 gain: +10-15%.
- **Tier Z — Premium (~$80-180):** Tier X + BOTH Demonic AND Vampiric Tutor + Tainted Pact + Lab Maniac. Estimated T6 gain: +18-22% — typically clears the 50% B4 bar.
- **Tier W — cEDH-tier ($500+):** Tier Z + Mana Crypt, Mox Diamond, Imperial Seal, Force of Negation, Pact of Negation, Lotus Petal, Jeweled Amulet. Pushes to B5 (cEDH).

Higher tiers don't replace lower ones — they stack.

### Tier R — redundancy web (DEC-474 / DEC-482)

Added 2026-08-15 from the DEC-474 video review (board vote, interaction `5151f0e1`; amended framing per defect D2). Tier R is a budget path to B4 payoff that sits beside the ladder above, not on it. It replaces the **premium** tutors of Tiers Y/Z (Demonic/Vampiric, $30–180) with per-slot redundancy plus budget tutors. It reduces premium-tutor dependence; it does not eliminate tutoring — the $27 source deck still runs Demonic Bargain, Final Parting, and a transmute creature.

The pattern has three parts:

1. **Command-zone assembly anchor.** The commander is a combo piece, so one slot of the combo is always available.
2. **≥5–7 interchangeable pieces per combo slot.** Each remaining slot accepts any of several cheap cards, so the deck draws into the combo instead of paying premium-tutor prices for consistency.
3. **Graveyard as second hand.** Self-mill fills the yard, and graveyard-castable recursion pieces replace tutor spend.

**Caveats (record these on any build that uses this pattern):**

- The sole performance evidence is the creator's n=10 unopposed goldfish (±~31pp CI at p=0.5). The direction is credible; the point estimate is not.
- Graveyard hate is the known failure mode.
- Any build on this pattern must get a real KEY_COMBOS-tagged 100k-sim readout before any bracket claim.
- Rules-layer verification is on record (DEC-474 second soundness pass): all 7 death-return pieces close infinite same-turn loops with Sun Titan + Bartolome del Presidio, and the payoffs verified are 4 each-opponent drains plus 1 mill converter.

### Caveats

The comboLethal proxy is a FLOOR. Real-game readiness is higher because the proxy doesn't model:

- Literal graveyard tracking (reanim assumes piece could be in GY without verifying)
- Multi-turn assembly ("tutor T3, hold piece, combo T5")
- Stack-trigger ordering (Thoracle ETB on stack + Consultation response is abstracted)
- Token-state combo enablers beyond the commander-in-play approximation
- Opponent interaction / counter-magic against your combo turn

A deck at 50% comboLethal at T6 in the proxy will typically win the actual game in the T5-T7 window in a 4-player pod where you're not the priority target. Conversely, a deck under 40% at T6 does NOT have a reliable T5-T6 plan, even accounting for these caveats.

### Case study

DEC-205 Dark Dominion retune (commits [`4094952`](https://github.com/DioPires/mtg-precon-upgrader/commit/4094952) through [`a62d993`](https://github.com/DioPires/mtg-precon-upgrader/commit/a62d993)) — slow value-pile B5 (T8+ goldfish lethal, comboLethal not tracked) → tutored combo B4+ (comboLethal T6 48.2%, T7 53.3%, median combo-ready turn T7). DeckHealthScore C(65) → B(67.5), manabase_health 74 → 82, global_health 78 → 85. Total spend: $56. Six combo lines tagged (3 wincon-permanents × 2 finishers).

### Shell-vs-payoff ceiling (DEC-309)

Added 2026-05-29 from DEC-309. A B4 deck has to match its **shell** (manabase + interaction) to its **payoff** (what the proxy says it can actually win with). ScryCheck downgrades brackets when these don't match: Sol Ring + Demonic Tutor + 7-mana coin-flip wincon is not actually B4, no matter what the `bracket` field says.

The check lives in `scripts/validate_strategy_ceiling.py` and runs as part of `scripts/smoke_test.sh`. It is **non-blocking** — warnings to stdout, exit 0 either way.

**Inputs:**

- `shell = min(manabase_health, interaction_density)` — the weaker of the two. Fast mana with no countermagic is still a slow shell to defend a combo turn on.
- `payoff`: branched on the deck-root `wincon_style`:
  - `combo` → `comboLethal@T6`
  - `combat`, `drain`, `drain-x`, `discrete-threats` → `lethalProxy@T7`
  - `value-incremental` → `max(comboLethal@T6, lethalProxy@T7)` — a value pile can win either way.
  - Multi-kind (card-level mix of `combo` + any non-combo style, or missing root style) → `max(comboLethal@T6, lethalProxy@T7)` — silverquill-style decks where the payoff is genuinely diversified.

**Detection rules (final thresholds):**

- **shell-exceeds-payoff** (downgrade signal): `shell ≥ 80` AND `payoff < 15%`.
  → "B4 shell, sub-B4 payoff. Either reduce shell investment or upgrade wincon."
- **payoff-exceeds-shell** (consistency risk): `comboLethal@T5 ≥ 50%` AND `shell < 60`.
  → "Fast wincon, weak shell — combo line exists but won't survive a contested table."

**Calibration snapshot (2026-05-29):**

Computed across all 15 production decks. Columns: manaH = manabase_health, intD = interaction_density, shell = min(manaH, intD), CL@T5/T6 = comboLethal at turn 5/6, LP@T7 = lethalProxy at turn 7, payoff per the branching rules above.

| deck | bracket | root `wincon_style` | manaH | intD | shell | CL@T5 | CL@T6 | LP@T7 | payoff | flag |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| aziza-mage-tower-captain | 3 | combat (multi) | 75 | 120 | 75 | 18.4 | 23.6 | 18.9 | 23.6 | ok |
| creeping-corruption | 3 | value-incremental | 82 | 120 | 82 | 0.0 | 0.0 | 46.8 | 46.8 | ok |
| dark-dominion | 4+ | value-incremental | 82 | 118 | 82 | 46.2 | 57.4 | 19.0 | 57.4 | ok |
| eternal-agony | 4 | value-incremental | 75 | 120 | 75 | 5.4 | 8.2 | 42.0 | 42.0 | ok |
| eternal-harvest | 4 | value-incremental | 69 | 104 | 69 | 0.0 | 0.0 | 29.2 | 29.2 | ok |
| hidden-legion | 3 | combat (multi) | 64 | 120 | 64 | 0.1 | 0.3 | 26.6 | 26.6 | ok |
| mutant-multiplication | 4 | value-incremental | 86 | 89 | 86 | 0.0 | 0.0 | 33.3 | 33.3 | ok |
| pyre-and-panic | 3 | drain | 70 | 120 | 70 | 0.0 | 0.0 | 35.6 | 35.6 | ok |
| silverquill-the-disputant | 3 | (mixed: drain+tokens) | 85 | 120 | 85 | 1.6 | 2.8 | 22.4 | 22.4 | ok |
| superfriends-esika | 3+ | value-incremental | 62 | 120 | 62 | 3.9 | 7.0 | 5.7 | 7.0 | ok |
| the-white-forge | 4 | value-incremental | 69 | 120 | 69 | 0.0 | 0.0 | 14.0 | 14.0 | ok |
| titan-convergence | 4 | discrete-threats | 69 | 93 | 69 | 0.0 | 0.0 | 31.7 | 31.7 | ok |
| verdant-tide | 3 | discrete-threats | 71 | 80 | 71 | 0.0 | 0.0 | 58.8 | 58.8 | ok |
| witherbloom-the-balancer | 3 | drain-x | 71 | 120 | 71 | 0.0 | 0.0 | 27.0 | 27.0 | ok |
| zada-hedron-grinder | 3 | combo (multi) | 69 | 102 | 69 | 0.0 | 0.0 | 48.4 | 48.4 | ok |

**Threshold rationale:**

- `shell_floor=80` clears the four decks that earn B4-shell scores (creeping-corruption 82, dark-dominion 82, silverquill 85, mutant-multiplication 86). Anything below isn't paying B4 tax in the first place, so shell-exceeds-payoff isn't the right diagnosis for it.
- `payoff_floor=15` leaves silverquill (22.4%) above the floor by ~7 points — the canonical multi-axis case that *should not* trigger. Mutant-multiplication (33.3%) and creeping-corruption (46.8%) are well clear.
- `fast_payoff=50%` (CL@T5) and `weak_shell=60` form the opposite warning. No current deck triggers it — the closest is superfriends-esika at shell 62 / CL@T5 3.9%. The rule is forward-looking: it catches a future deck that adds a Thoracle line without strengthening its lands or interaction.

**Sanity checks (from DEC-309 acceptance):**

- silverquill-the-disputant does **not** trigger (shell 85, payoff 22.4% — multi-axis case respected). ✓
- titan-convergence does **not** trigger because its shell (69) is below `shell_floor`. Reason: titan is a B4 *deck* by composition but its shell score is sub-B4. The strategy-ceiling check is specifically about decks that pay the B4 shell tax; titan's gap is "shell needs upgrading," which is a [`metrics.json gaps[]`](../docs/deck-metrics.md) finding, not a ceiling mismatch.
- mutant-multiplication does **not** trigger (tuned multi-axis B4 — shell 86, payoff 33.3%). ✓
