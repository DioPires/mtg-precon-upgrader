## DEC-935 — sim model recommendation, v3 (after a second adversarial review)

**Revised recommendation: fix the goldfish's mana model first, then build the Atla hatch engine on the fixed base. The review found that the shared goldfish lets a deck spend its turn's mana more than once, so every deck's lethal curve is inflated today; extending that model for one deck would be measuring on a broken base.**

The second review (16 findings, all verified against the code this heartbeat) changes the answer in one big way and corrects v2 in several smaller ones. What changed and why is in section 3; the decision is in section 5.

### 1. The finding that changes the answer: the goldfish double-spends mana (verified)

`simulate_goldfish_game` casts spells in a loop that rebuilds the mana pool from every active source on each pass (`while True: pool = GoldfishManaPool(turn_sources(permanents, turn))`, line 2288–2289). The pool left after a cast (`pool.after_spending`, line 2329) is thrown away on the next pass. Reproduced with a synthetic deck (40 Forests, 59 two-mana creatures): on turn 2 with two lands the goldfish casts **four** two-drops. The same fresh-pool check is used by the DEC-405 transform (line 2421) and by every engine that "checks affordability like a cast". The behaviour dates from the goldfish's first commit (4ae9fc7, 2026-03-21).

Consequences:
- Every `lethalProxy` and `comboLethal` curve in the fleet is inflated, most on the early turns where hands are full. The DEC-559 bracket bands, the B4 reality-check rows in `data/bracket-philosophy.md`, and the DEC-309 strategy-ceiling thresholds were all fitted on these curves. Relative rankings between decks may survive; the absolute meaning of "50% lethal at turn 6" does not.
- v2's Phase 1 assumed "spend leftover mana after casts on Egg activations". There is no leftover: after the cast loop the pool is full again. Built on the DEC-405 pattern, Egg activations would be free from turn 2 — a ceiling, the opposite of the floors the engines promise.
- Fixing it is a small code change (track mana spent within the turn, roughly a counter and one subtraction in the cast loop) with a large data consequence: all 21 `simulation.json` files re-export and the calibration extract is re-run. That is why it is a board decision and not something I fold into a child issue quietly.

### 2. Corrections to v2 (from the review)

- **"Cannot be met by any combat deck" was right in v1; v2's correction was wrong.** No deck in the fleet reaches 50% lethal proxy at turn 6 (best: gathering-shadow 49.8 with its amass engine; best without an engine: verdant-tide 26.2). armory-protocol's 37% comes with the DEC-405 engine, not from casting alone. The turn-6 gate in this deck's own text is unmet fleet-wide, so a hatch engine measures the plan; it does not make the gate reachable.
- **Six engine blocks, not four:** cascade, copy, token swarm, transform-deploy, permanent-draw (DEC-472) and amass-army (DEC-533). The amass engine's extra-combat damage ledger is the closest precedent for "hatched bodies attack".
- **Combat keywords:** the profile already gives +1 for Double strike and First strike (a keyword list, not an evasion list); printed Haste is ignored fleet-wide — which matters for Aurelia and Raph & Mikey.
- **Atla is summoning-sick the turn she is cast** (`{2},{T}`); the engine must gate own-turn activations on `commander_play_turn < turn`, as the DEC-404 token engine does, unless a team-haste source is on the battlefield (Rhythm's riot covers her).
- **Thornbite Staff** pays for the next Egg only with Ashnod's Altar ({C}{C}); with Phyrexian Altar each loop is net −1, with Goblin Bombardment −2. The free attach only happens if the Staff was already on the battlefield when Atla entered; the sim has no equip path, so otherwise the Staff does not count.
- **Seedborn Muse's three activations happen on opponents' turns**, after that turn's combat: those hatches are ready next turn regardless of haste, and only instant-speed outlets serve them (Skullclamp's equip is sorcery-speed).
- **Egg sources besides Atla:** Palani's Hatcher enters with two Eggs (doubled by Mondrak/Elspeth, and its enters-the-battlefield trigger is doubled by Elesh Norn) and sacrifices one Egg per own-turn combat for free; Nesting Dragon makes a Dragon Egg per land drop, which is an Egg for Atla's trigger. Both need modelling or an explicit floor line.
- **Raph & Mikey:** printed haste (ignored by the profile) and their hatched creature attacks in the same combat — both need `combatReadyTurn = entry turn`; Annie Joins Up doubles their trigger too.
- **Consumers that move:** hatches change the board and dig past pieces, so `comboAssembly`, `comboConsistency`, `commanderIndependence`, `deckHealthScore` and `comboLethal` all move, not just `lethalProxy`. The metrics code needs no change, but the health score the Grimoire shows will. Acceptance must include a before/after table of those fields.
- **"Byte-identical control deck" is not achievable:** only the goldfish is seeded; the mana simulation and `generatedAt` vary per run. The right check is equality of the `goldfish` section and the deterministic reliability fields for a control deck, or a unit test on `compute_goldfish_section`.
- **Test precedent is thin:** of the engine commits only DEC-393 shipped tests. The hatch engine needs new test scaffolding; realistic size 350–500 lines including tests, not 200–300.
- **Phase 2 metadata:** the local Scryfall mirror already carries power and toughness, so the backfill is a local join, not a refetch; DEC-405's per-deck `equipmentPower` table is the lighter precedent.
- **Smaller fixes:** Lightning Greaves is out because it is single-target with no equip path (equip is {0}, not sorcery-speed as v2 said); Skullclamp's two-card draw per Egg should be credited; Maskwood Nexus turning every creature into an Egg belongs in the floor list; static haste sources also cover creatures already on the battlefield (entry-time rule undercounts by at most one creature-turn, a floor); v2 changed Annie/Throne from "double" to "+1 hatch each", which is correct (three hatches with both) and should have been listed as a change.
- **Housekeeping:** the DEC-559 calibration extract (`agents/ceo/analysis/dec559-fleet-t50.json`) was untracked; it is committed with this comment.

### 3. Revised plan

**Issue A — fix the double-spend (fleet-wide, do first).** Track mana spent within the turn in the cast loop and make every affordability check (casts, commander, tutors, engine activations) see the remaining pool. Re-export all 21 decks. Re-run the DEC-559 calibration extract and re-check the B4 reality-check rows in `data/bracket-philosophy.md` against the new curves; report before/after per deck. No threshold is retuned in the same change — the numbers move first, the bands are re-fitted in a separate CEO analysis with the board. No bracket label changes without a board decision (the doc already says the curve test is a necessary floor, not a sufficient classifier). Tier 2, one engineer, reviewed by me. Acceptance: the synthetic two-land test casts one two-drop on turn 2; a fleet before/after table; the existing exporter tests pass.

**Issue B — Atla hatch engine + team-haste rule (broodfire, after A).** As in v2 with the corrections above: gate on Atla untapped-and-ready plus an instant-speed outlet; Eggs per own turn from the remaining pool in pairs (cap 4 before doublers), plus Palani's Hatcher's two on entry and its free combat sacrifice, plus Nesting Dragon's one per land drop; Seedborn's three opponent-turn hatches ready next turn; Mondrak/Elspeth ×2 each; Annie/Throne +1 hatch each; Raph & Mikey +1 hatch per combat, ready on entry; Thornbite untap only with Ashnod's; hatch cap 8 per turn; a generic `hatch_from_library()` helper (the cascade dig without the mana-value filter) so verdant-tide's Eladamri, Korvecdal — a reveal-and-put commander with no engine today — can be a config entry later. Team-haste rule: Rhythm of the Wild, Samut, Rising of the Day, Palani's Hatcher with Maskwood Nexus. Acceptance: unit tests per rule on synthetic decks; control-deck goldfish-section equality; before/after table for lethalProxy, comboLethal, comboAssembly, comboConsistency, commanderIndependence and deckHealthScore; methodology paragraph in the exporter. Tier 2, one engineer, reviewed by me. Size 350–500 lines with tests.

**Phase 2 (extra combats, power multipliers)** stays deferred until B has produced a curve; it starts with a per-deck power table or a local join from the mirror.

**Option C — change nothing in code.** Re-gate this deck's brewing text on the turn-7/turn-8 bands from bracket-philosophy's B2/B3 table and record in the deck's sources that the goldfish does not model hatching. Zero cost, but it leaves the double-spend in place for every deck, which I now consider the more important problem.

### 4. What I recommend and why

A then B. A is a correctness bug in a tool the board uses for bracket decisions; leaving it because fixing it moves numbers would be choosing the wrong numbers on purpose. B is the deck-specific measurement the board asked about, and it only makes sense on the fixed base. I will not predict either curve. If after A and B this deck still reads below turn 6, that is a fact about the deck on an honest model.

### 5. Decision asked of the board (one verdict per item on the card)

- **A.** Approve the double-spend fix issue (fleet re-export, calibration re-run, no threshold or label change without a further board decision).
- **B.** Approve the Atla hatch engine + team-haste issue, sequenced after A.

Rejecting both means Option C.
