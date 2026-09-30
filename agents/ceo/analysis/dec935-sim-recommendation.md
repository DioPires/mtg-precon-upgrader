## DEC-935 — sim model: recommendation

**Yes, change it — as a scoped Atla engine plus three opt-in combat modifiers, built the way the four existing commander engines were built. Do not build a combat simulator.**

### What the goldfish does today (verified in `scripts/export_simulation_results.py`)

1. **It has never modeled Atla's hatch.** The deck's own sim module says the Egg-hatch loops "are measured by the shared goldfish", and the shared goldfish has no hatch path: a creature reaches the battlefield only by being cast from hand. The old 46% combo-lethal came from the Mirror Entity one-card "combo-ready" flag (a `comboLethal` assembly check, not damage). So the deck's core engine has been invisible to the sim since it was built at DEC-544; the remake only removed the flag that hid that.
2. **Combat value is crude and static.** Each creature contributes `min(8, mana value)` damage per turn, plus 1 if it has an evasion keyword, starting the turn after it enters (`combatReadyTurn = turn + 1`). Lethal proxy means 40 cumulative damage. There is no haste, no power doubling, no double strike, no extra combat phase, and no token combat except Namor's ledger. Every amplifier this deck now runs reads as zero, and a hatched Worldspine Wurm would count 9 damage a turn if the sim could hatch it.
3. **There is a precedent and a slot for exactly this.** Four commander engines already sit in the exporter as a config block plus a code path — Zhulodok's cascade (DEC-385), Zada's copies (DEC-393), Namor's token swarm (DEC-404), Tony Stark's transform-deploy (DEC-405). Each is "floors, not ceilings", each was recorded in a DEC, and each moved only the deck it was configured for.

### What to build (in order of value per line of code)

- **(a) Atla hatch engine — broodfire only, on by default.** With Atla on the battlefield and a free outlet on the battlefield (Ashnod's Altar, Phyrexian Altar, Goblin Bombardment; Skullclamp at {1}; High Market once a turn), each {2} activation makes an Egg, the outlet kills it, and the engine reveals from the library until a creature card and puts it onto the battlefield, crediting it exactly like a free cast (pressure, combat, draw triggers). Eggs per turn cycle: 1 on your turn, plus 3 with Seedborn Muse, plus 1 per untap from Aurelia / Combat Celebrant / Tifa / Thornbite Staff; Mondrak and Elspeth double the count; Annie Joins Up and Roaming Throne double the hatches. Raph & Mikey hatch once per attack. This closes the biggest gap and is the part that makes the deck's own "brewing until the sim confirms the turn-6 kill rate" gate meaningful — today that gate cannot be met by any combat deck.
- **(b) Haste — generic, opt-in per deck.** A config set of team-haste permanents (Rhythm of the Wild, Samut, Rising of the Day, Palani's Hatcher with Maskwood Nexus, Lightning Greaves on the commander) sets `combatReadyTurn` to the entry turn for creatures that enter while one is on the battlefield.
- **(c) Extra combats — generic, opt-in.** Multiply the turn's combat damage by one plus the number of ready extra-combat sources (Aurelia and Combat Celebrant on their first attack, Tifa only when a power-7 body is attacking, Aggravated Assault once per {3}{R}{R} the pool can still pay after the turn's casts). Cap at three extra combats per turn; Annie Joins Up doubles the legendary ones.
- **(d) Power multipliers — generic, opt-in.** Zopandrel doubles the team's combat each combat; Xenagos adds the largest attacker's power once per combat; Raphael, the Nightwatcher doubles all attackers. Applied as multipliers on the combat sum, in that order.

Floors, not ceilings, as with the other engines: no blockers, no opponent interaction, no fogs. Keep the 40-damage lethal proxy and the existing thresholds unchanged so the number stays comparable with the rest of the fleet.

### Cost and fleet impact

- Engineering: one Tier 2 child issue for an engineer, review by me. Same shape as DEC-404 (config block, one code path in `simulate_goldfish_game`, a unit test per modifier, a broodfire re-export). A few hundred lines.
- Fleet: (b)–(d) would also touch shield-doctrine (Aggravated Assault, three double-strike sources), armory-protocol (Genji Glove), slivers (Blur Sliver), zada (Great Train Heist), and the double-strike or damage-doubler cards in eternal-agony, gathering-shadow, hidden-legion and anvil-chorus. Because the modifiers are opt-in per deck config, nothing moves until a deck's review turns them on; when one does, re-export that deck and re-run the DEC-559 calibration extract, since the bracket bands were fitted on curves without these effects.
- I will not predict the new broodfire curve. The point of the change is to measure the deck, not to hit a number; if the modelled curve still reads below the turn-6 bar, that is information about the deck, not a reason to tune the model.

### What not to do

- No hand-tuned "combat bonus" or threshold change — that would hide the gap instead of measuring it.
- No opponent or blocker modelling — the goldfish is a consistency measure by design, and adding opponents would invalidate every other deck's number.
- No change to the metrics layer — `win_turn` and the strategy-ceiling check already read `lethalProxy` for combat decks; they will pick the new curve up unchanged.

### Decision asked of the board

Approve opening the engineering child issue with the scope above (a on by default for broodfire; b–d opt-in). If you would rather not spend engineering on the sim, the alternative is to accept the goldfish as a mana-and-curve measure only and drop the "brewing until the sim confirms" gate for combat decks; I would then add that note to the deck's sources. My recommendation is the first option.
