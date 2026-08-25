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

### Explosive Ramp (Burst Mana)

Added from DEC-481 (2026-08-15), adopting lesson L4 (as amended) from the DEC-474 video review.

**Category definition.** Explosive ramp (burst mana) is one-shot or temporary mana acceleration, distinct from the persistent rocks and dorks above. It covers rituals, treasure bursts, cost-cheat effects, and extra turns used as mana. The definition merges two videos by Gage (@TheCommanderChallenge): V2 (*…I will change how you think about Commander Forever*, 2026-05-27) supplies the mana-doubling framing plus cost-cheat and extra turns; V1 (*How to Build a Commander Deck from Scratch*, 2026-05-11) supplies rituals and treasures.

**Count ladder (creator-sourced heuristic — cross-check only).** Every rung below is the creator's stated practice, not a validated target. Use the ladder only as a cross-check until we validate it against our mana sims.

- ~2 pieces at Bracket 2 (his practice)
- 3–5 pieces at Bracket 3 (his practice)
- 9 pieces at Bracket 4 — his stated B4 practice, one example deck, no range given

**Source credibility cross-check.** His land counts independently corroborate our Karsten formula. He runs 38 lands; our formula (35 + 1.5×avg_cmc) gives ≈39–40 at typical curves (39.8 at the default 3.2 avg CMC), and 38 sits inside the formula's ±1–2 credit tolerance.

**No role-taxonomy change.** Burst-mana cards keep their existing role tags (`ramp` per [`docs/role-taxonomy.md`](../docs/role-taxonomy.md)); this category is descriptive only.

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

## Tutor Quality Ladder (per bracket)

*Added from DEC-560 (2026-08-25), option B of the DEC-557 process review. Tutor efficiency is a bracket signal on its own, separate from Game Changer status. This section defines three tutor classes and a per-bracket expectation, so swap proposals can name the bracket implication of a tutor add. The per-rung counts are house guidelines set by this proposal, not sim-validated targets.*

### Tutor classes

Class measures speed and freedom of search, not price.

- **T1 — Premium**: MV ≤ 3, searches for any card, puts it in hand or on top of the library. The drawback is small or irrelevant on the turn you win. Examples (Scryfall-verified): Demonic Tutor ({1}{B}, any card to hand), Vampiric Tutor ({B} instant, any card to top, lose 2 life), Imperial Seal ({B} sorcery, any card to top, lose 2 life), Grim Tutor ({1}{B}{B}, any card to hand, lose 3 life), Wishclaw Talisman ({1}{B} artifact; {1}, {T}, remove a wish counter: any card to hand, then an opponent gains control of it), Diabolic Intent ({1}{B}, sacrifice a creature as an additional cost, any card to hand), Gamble ({R}, any card to hand, discard a card at random), Beseech the Mirror (bargained: tutor plus free cast at MV ≤ 4 — see the comboLethal tags below).
- **T2 — Cheap restricted**: MV ≤ 3, search restricted by card type or destination. Examples: Mystical Tutor, Worldly Tutor, Enlightened Tutor ({U}/{G}/{W} instants, one type class, to top of library), Solve the Equation and Fabricate ({2}{U}, one type, to hand), Green Sun's Zenith and Chord of Calling (to the battlefield, but total cost scales with X).
- **T3 — Slow or taxed**: MV ≥ 4 unconditional, or cheaper with a real cost or a symmetric gift. Examples: Diabolic Tutor ({2}{B}{B}), Final Parting ({3}{B}{B}, second card to graveyard), Demonic Bargain ({2}{B}, exile your top 13), Scheming Symmetry ({B}, a chosen opponent also searches), transmute cards.

### Game Changer overlay

Seven pure tutors sit on the official GC list: Demonic Tutor, Vampiric Tutor, Imperial Seal, Enlightened Tutor, Mystical Tutor, Worldly Tutor, Gamble. Tutor-adjacent GCs also exist (Intuition, Gifts Ungiven, Survival of the Fittest, Natural Order, Crop Rotation). GC caps therefore bind most T1/T2 adds at B3 and below: brackets ≤ 3 allow at most 3 GCs.

Class and GC status are independent. Wishclaw Talisman, Diabolic Intent, and Grim Tutor are T1 and are not GCs. A non-GC T1 tutor raises deck power without touching the GC count — the ladder exists to catch exactly that case.

### Ladder

- **B1–B2**: T3 only, 0–2 total. No GC tutors. The deck should find pieces by drawing, not searching.
- **B3**: 2–3 tutors from T2/T3. At most one T1, treated as a deliberate power statement: if it is a GC it consumes one of the deck's ≤3 GC slots; GC or not, it concentrates the deck's best line.
- **B4**: T1 expected. One to two premium tutors is the norm — Budget Tiers Y/Z below already encode this (Y = one of Demonic/Vampiric; Z = both). Add strategy-matched T2 tutors as redundancy.
- **B5**: multiple T1 plus strategy-matched T2 redundancy. Tutor density must support the T4–T5 win this bracket expects.

### Why efficiency scales with bracket

A tutor plays as an extra copy of the best piece still in your library. The comboLethal proxy (below) models this directly: it substitutes tutors for missing combo pieces. Each cheap tutor therefore raises comboLethal at a given turn, and the kill-turn thresholds convert that into bracket pressure. This is why the same card is expected at B4 and is a relabel risk at B3. Tier R (below) is the deliberate inverse: redundancy instead of premium tutors.

### Swap-proposal rule

Any proposal that adds a T1 or T2 tutor to a deck labeled B3 or lower must include a "bracket implication" line with three parts:

1. **GC accounting** — is the tutor a GC, and what is the deck's GC count after the add (cap 3 at ≤B3; verdant-tide capped at 1 per DEC-369)?
2. **Consistency shift** — projected comboLethal/lethalProxy movement, or a stated reason the tutor does not feed a win line.
3. **Relabel exposure** — whether the add pushes the deck toward the next bracket, noting the relabel floor is GC-gated (DEC-374).

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

### B2/B3 Reality Check (sub-B4 turn bands)

Added from DEC-559 (2026-08-25, child of DEC-557), calibrated against the fleet's own `comboLethal` / `lethalProxy` curves — not the DEC-557 chart. Same statistic as the B4 test: the better of `comboLethal` / `lethalProxy` from `data/commanders/{id}/simulation.json`. "T50" below means the first turn that statistic reaches 50%. Per-deck calibration extract: `agents/ceo/analysis/dec559-fleet-t50.json`.

| Reading | Classification |
|---|---|
| ≥ 50% at T7 (but not T6) | **B3+ / Soft-B4 straddle** — already the Soft-B4 row in the B4 table; split 3+ vs 4- on non-proxy criteria (GC count, fast mana, tutor density) |
| < 50% at T7, ≥ 50% at T8 | **True B3** — wins open at T6 (T6 reading typically 10–30%), games close ~T8 |
| 40–50% at T8 | **Soft B3** — B3 label holds if the T6 reading is ≥ ~5% (real wins exist from T6) |
| < 40% at T8, ≥ 50% by T10 | **B2 band** — games run ~T10; T7-8 wins happen but are not the norm |
| < 50% at T10 | **Sub-B2 payoff** — precon-level; run `validate_strategy_ceiling.py` and the blind-spot audit |

Two mandatory caveats ship with this table:

1. **The proxy is a floor. It can promote, never demote.** A high reading argues the deck is stronger than its label. A low reading does not demote a deck by itself. Before any down-label, audit the known blind spots: `lethalProxy` misses token combat and noncombat damage, and `comboLethal` holds back tagged combo pieces. Five decks labeled 4/4- read T50 ≥ 9 at calibration time for exactly these reasons (shield-doctrine, the-white-forge, stampede-acres, eternal-agony, grave-dividends) — their labels stand.
2. **The B2 band is extrapolated.** The fleet holds zero B2 decks (DEC-369 bar is ≥ B3+/4-). Two independent anchors agree on the band: (a) fleet medians shift about one turn per bracket step — true B4 ≤ T6, soft B4 = T7, B3+ median 7.5, B3 median 8, so B2 lands at 9–10; (b) the qualitative anchor from DEC-557, games ~T10 with wins T7-8. Recalibrate this row if the fleet ever gains a real B2 deck.

Honesty note: labels 3 through 4 overlap on T50 in our fleet. This test is a necessary floor, not a sufficient classifier — the same framing the B4 table uses. Labels also ride on GC count, fast mana, tutors, and interaction quality.

### comboLethal proxy schema (cross-link)

The proxy lives in `scripts/export_simulation_results.py`. Its v2 model substitutes for missing combo pieces via: (1) bargain free-cast tutor (Beseech-style), (2) type-matched regular tutor, (3) reanimation for permanent pieces. Decks must tag the right fields to be read correctly:

- `winConditions[].kind: "combo"` + `winConditions[].pieces: [card names]` — without these, comboLethal stays 0.
- `decklist[].tutor_targets: ["instant", "sorcery"]` — restrict tutors that can't fetch creatures/planeswalkers (e.g., Mystical Tutor, Spellseeker). Default `["any"]`.
- `decklist[].tutor_mv_cap: N` — restrict tutors that have an MV cap (e.g., Spellseeker MV ≤ 2). Default `null`.
- `decklist[].tutor_free_cast_via_bargain: true` — Beseech the Mirror and similar bargain-tutor cards.
- `decklist[].primary_role: "recursion"` (or `secondary_role`) — for reanimation spells (Reanimate, Animate Dead, etc.).

Forgetting these tags will under-count comboLethal and make a real B4 deck look weaker than it is.

### Assembly consistency (combo bracket weight)

A combo's bracket weight is its **presence** multiplied by its **assembly consistency**. A decklist that merely contains a two-card infinite does not automatically climb a bracket; the weight comes from how often the deck actually assembles the line inside its win window. The official bracket rules gate on presence alone; this principle adds the consistency axis our sims measure. Both factors have metric hooks: presence is what `winConditions[]` / `KEY_COMBOS` tagging records, and assembly consistency is what the goldfish measures as `reliabilityMetrics.comboAssembly`, surfaced as `deckHealthScore.components.comboConsistency` (floor-anchored — combo-less decks read 50). The product cuts both ways. A tagged combo with no tutor or draw support has low assembly consistency, so it adds little weight. And a deliberately incomplete loop has presence near zero, so it adds almost none: this is the **retain-as-soft-combo** outcome (DEC-474 L7). Worked example: tidal-legion sits exactly at the Bracket 3+ cap of 3 Game Changers and keeps its near-miss loops — e.g., Hullbreaker Horror + Sol Ring, one cheap permanent short of infinite mana — as soft-combo value engines, because completing one would add real assembly-backed weight and could force a bracket relabel.

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

DEC-205 Gathering Shadow retune (commits [`4094952`](https://github.com/DioPires/mtg-precon-upgrader/commit/4094952) through [`a62d993`](https://github.com/DioPires/mtg-precon-upgrader/commit/a62d993)) — slow value-pile B5 (T8+ goldfish lethal, comboLethal not tracked) → tutored combo B4+ (comboLethal T6 48.2%, T7 53.3%, median combo-ready turn T7). DeckHealthScore C(65) → B(67.5), manabase_health 74 → 82, global_health 78 → 85. Total spend: $56. Six combo lines tagged (3 wincon-permanents × 2 finishers).

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
| gathering-shadow | 4+ | value-incremental | 82 | 118 | 82 | 46.2 | 57.4 | 19.0 | 57.4 | ok |
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

- `shell_floor=80` clears the four decks that earn B4-shell scores (creeping-corruption 82, gathering-shadow 82, silverquill 85, mutant-multiplication 86). Anything below isn't paying B4 tax in the first place, so shell-exceeds-payoff isn't the right diagnosis for it.
- `payoff_floor=15` leaves silverquill (22.4%) above the floor by ~7 points — the canonical multi-axis case that *should not* trigger. Mutant-multiplication (33.3%) and creeping-corruption (46.8%) are well clear.
- `fast_payoff=50%` (CL@T5) and `weak_shell=60` form the opposite warning. No current deck triggers it — the closest is superfriends-esika at shell 62 / CL@T5 3.9%. The rule is forward-looking: it catches a future deck that adds a Thoracle line without strengthening its lands or interaction.

**Sanity checks (from DEC-309 acceptance):**

- silverquill-the-disputant does **not** trigger (shell 85, payoff 22.4% — multi-axis case respected). ✓
- titan-convergence does **not** trigger because its shell (69) is below `shell_floor`. Reason: titan is a B4 *deck* by composition but its shell score is sub-B4. The strategy-ceiling check is specifically about decks that pay the B4 shell tax; titan's gap is "shell needs upgrading," which is a [`metrics.json gaps[]`](../docs/deck-metrics.md) finding, not a ceiling mismatch.
- mutant-multiplication does **not** trigger (tuned multi-axis B4 — shell 86, payoff 33.3%). ✓
