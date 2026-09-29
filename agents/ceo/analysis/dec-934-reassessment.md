# DEC-934 — Broodfire Hatchery Trigger-2 re-assessment (PASS)

Date: 2026-09-29. Assessor: CEO (DEC-461: card reviews are CEO-executed). Baseline: commit `9d3e67f` (DEC-931 apply). Current: the same 99 — no decklist change has landed since the baseline, so every "before / after" pair below compares the baseline files with today's re-run of the same pipeline.

## Verdict

**PASS — no swaps proposed.** Global health flat at 85 (normalized 87), one standing gap (recursion 0/2, accepted since DEC-574), validators clean, Game Changer count 7 (uncapped at bracket 4), strategy-ceiling check ok. Two prose defects fixed (stale ramp/draw counts; a wrong rules claim in the Identity Echo highlight). The swap-round counter resets to 0 at the commit that lands this report.

## Rounds covered (3 board-approved rounds since the DEC-544 build)

1. DEC-570 — Idol of Oblivion → Caretaker's Talent; Gamble → Winds of Abandon; Warleader's Call → Elspeth, Storm Slayer; 1 Plains → Eiganjo, Seat of the Empire (commit `47d6bcd`)
2. DEC-574 — +Greater Good / −Wild Growth; +Idol of Oblivion / −Titan of Industry; +Shamanic Revelation / −Heroic Intervention; +Warstorm Surge / −Impact Tremors; +Solphim, Mayhem Dominus / −Sun Titan (commit `def7288`)
3. DEC-931 — +Identity Echo / −Rishkar's Expertise; +Rootbound Crag / −Utopia Sprawl (commit `9d3e67f`)

## 1. Card pool refresh + top-50 triage

`refresh_card_pool.py --deck broodfire-hatchery` ran today at 15:56Z: mirror 2026-09-29 (current, no download), EDHREC rates fresh (fetched 14:36Z, 263 cards), 200 candidates unchanged, metrics unchanged. Every card was oracle-verified on Scryfall before its line was written.

Standing dispositions (DEC-544 closing diff, DEC-570, DEC-574, DEC-931 — not re-opened):
- **Reject, tapped-basic ramp class** (the deck's ramp is the untapped Nature's Lore class): Cultivate, Rampant Growth, Kodama's Reach, Harrow, Terramorph, Entish Restoration.
- **Reject, 1-damage converter creatures** (DEC-574; Impact Tremors was cut for Warstorm Surge on the same reasoning): Agate Instigator, General Kreat, the Boltbringer.
- **Reject, lands**: Jungle Shrine (always tapped). **Defer, lands**: Cinder Glade, Canopy Vista, Sunpetal Grove, Spire Garden, Spectator Seating, Evolving Wilds, Rogue's Passage — see the manabase step; no colour deficit exists.
- **Board cut at DEC-544 (amendment A2), not re-proposed**: Ojer Taq, Deepest Foundation. Re-checked on merits today because it surfaced in the aristocrats wildcard sub-recipe: a creature-token tripler that Atla can hatch is on-plan, but the in-memory projection (`agents/ceo/analysis/dec934-projection.py`) of +Ojer Taq / −Nesting Dragon reads global 85 → 84 (curve 74 → 69, resilience 70 → 67), and the copy is committed elsewhere. Stays out.

Names with no prior line — triaged today:
- Advanced Reconstruction — reject: mill-and-exile value on a Class; the library is this deck's hand, and the level-3 cost break applies to spells cast from elsewhere, which Atla's hatches are not (they enter without being cast).
- Celebrate the Mountain-king — **defer, first in line for an interaction slot**: for {3}{W} it exiles up to one nonland permanent per opponent until it leaves, which covers the Grafdigger's Cage / Rest in Peace / Containment Priest hoser classes in one card, and it lifts removal-spot from 6/8 to 7/8 (the lowest role score, 75 → 88). Reference projection +Celebrate / −Shamanic Revelation: global 85 → 85 (normalized 87 → 88), role coverage 102 → 103, curve 74 → 75. Not proposed this round: Shamanic Revelation is a DEC-574 board add one round old, the Celebrate exile is sorcery-speed on the deck's tap-out turn, and the metric gain is inside the ±2 confidence margin. Owned, 2 free copies.
- Gimli, Counter of Kills — reject: pings only when an opponent's creature dies.
- Master of Ceremonies — reject: symmetric; each opponent chooses and shares the payout.
- Glaring Fleshraker — reject: colorless-spell and colorless-creature gated; the deck has two colorless creatures.
- Rubble Rouser, Treasonous Ogre, Glóin the Mighty — reject: red rituals on bodies; Jeska's Will already pays for the combo turn and none of the three does anything on arrival as a flip.
- Adeline, Endless Foot Assault, Seize the Day, Ghalta and Mavren (see EDHREC step) — reject: attack-gated (×1 per turn cycle, own attack only) in a main-phase combo deck.
- Fall of Cair Andros — reject: amasses off excess noncombat damage to opponents' creatures; the deck aims its damage at players.
- Boros Signet, Talisman of Conviction — defer: a third rock would put ramp at the 10 target (90 → 100), but the board chose a land over a ramp aura at DEC-931; hold for a ramp slot argument.
- Trading Post — reject: every mode costs {1} and a tap; the deck's outlets are free.
- Ojer Taq — see the board-cut line above.
- Growing Rites of Itlimoc — defer: transforms with four creatures, which a hatch turn reaches, but the front face is a 3-mana look-at-four, and the deck's ramp is spent by turn 3.
- Altar of Dementia — reject: milling our own library throws away the flips; targeting opponents does nothing for the plan.
- Brass Infiniscope, Gathering Stone, Hedron Archive, Thran Dynamo, Shuri's Fabricator, Vibranium Mining Mech, Voltaic Construct, Jhoira's Familiar, Krark-Clan Ironworks, White Auracite — reject as a class: 4-mana rocks and artifact-synergy pieces; the deck wants Atla on turn 3–4 off 1–2-mana ramp, and Ironworks needs artifact fodder the deck does not make.
- Burn, Burn, Tree and Fern — reject: one removal hit plus one artifact hit over four turns; Aura Shards does the artifact half every time a creature enters.
- Throes of Chaos — reject: random cascade in a deck whose spells are mostly tutors and protection.
- Witch Enchanter // Witch-Blessed Meadow — defer: the land face is untapped for 3 life, the creature face kills an artifact or enchantment on entry (a hatchable hoser answer). Below Sundering Growth and Celebrate on the interaction shortlist.
- Ajani, Nacatl Pariah — reject: Cat-death gated; the deck has no Cats.
- Valakut Awakening // Valakut Stoneforge — defer: a modal land that wheels the hand; not a colour source the deck lacks.

Include: none.

## 1b. Archetype recipe sweep (ramp-bigmana and aristocrats, both `live`)

Ran 26 queries over 16 sub-recipes (commander sub-recipes skipped) with the `id<=grw` splice, EDHREC order, 50-card cap, post-filtered against the 99 and the candidates top-50: 320 deltas (`agents/ceo/analysis/dec934-recipe-deltas.json`; runner `dec934-recipe-sweep.py`). No include. Named lines for every hit with an Atla-page rate at or above 10% or a global EDHREC rank inside 1200:
- Fanatical Devotion 32.9% — **defer, first in line for an outlet slot**: a free, repeatable sacrifice outlet on an enchantment (harder to answer than the artifact altars, DEC-474 L10) whose regenerate shields Atla or a hatched bomb from destroy-based removal. Uptime math: the chance of holding at least one of the 5 free outlets in the first 11 cards is 44%; a sixth outlet lifts that to 51%. No incumbent is weaker than a 3-mana outlet, so no cut this round. Not owned.
- Blasting Station 17.2% — defer: `{T}`, sacrifice: 1 damage, and it untaps whenever a creature enters, so every hatch re-arms it. It is Goblin Bombardment redundancy at 3 mana on an artifact; same slot argument as Fanatical Devotion, lower priority (Bombardment is already in).
- Culling Dais 19.8%, Martyr's Cause 18.9%, Spawning Pit 11.8%, Lazotep Quarry 11.0% — reject: outlets that tap, cost mana, or pay out in counters instead of hatches.
- Primal Growth 12.2% — reject: kicker sacrifices a creature for two tapped basics; tapped-basic class.
- Skyshroud Claim 11.9% — reject: 4 mana for two Forest-typed lands untapped is real, but Nature's Lore, Three Visits and Farseek already fetch the same shock duals a turn earlier.
- Eldritch Evolution — reject: a seventh tutor (tutor role 120, saturated); sacrificing an Egg finds only a 2-mana creature.
- Sakura-Tribe Elder, Elvish Mystic, Fyndhorn Elves, Delighted Halfling, Avacyn's Pilgrim — defer: dorks are Eggs under Maskwood Nexus and the ramp role sits at 9/10; first pick if a ramp slot opens is a 1-mana dork over a rock for that reason.
- Mana Vault, Grim Monolith, Basalt Monolith, Worn Powerstone, Palladium Myr, Thran Dynamo — reject: the board banned Grim Monolith on price at DEC-544 gate 1; the rest are colourless rocks at 3–4 mana that miss the turn-3 Atla window.
- Sanctum Weaver, Circle of Dreams Druid, Badgermole Cub — reject: creature-count or enchantment-count mana in a deck that keeps its creatures in the library.
- Kozilek, Ulamog (both), It That Betrays, Emrakul, the Promised End — reject: cast-trigger Eldrazi whose value is in the cast; Atla puts them onto the battlefield without casting.
- Ojer Taq (board cut), Omnath, Locus of Rage, Wurmcoil Engine, Pest Infestation — reject/standing: Omnath and Wurmcoil are creature-token engines that need attacks or deaths of their own tokens; Pest Infestation is a one-shot.

## 2. Before / after vs the 9d3e67f baseline (same 99, same inputs: 100k mana games, 10k goldfish games, metrics weights A)

| Measure | 9d3e67f | Today | Δ |
|---|---|---|---|
| manabase_health | 77 | 77 | 0 |
| role_coverage | 102 | 102 | 0 |
| curve_health | 74 | 74 | 0 |
| interaction_density | 120 | 120 | 0 |
| gameplan_cohesion | 40 | 40 | 0 |
| resilience_health | 70 | 70 | 0 |
| **global_health** | **85 / norm 87** | **85 / norm 87** | **0** |
| gaps[] | 1 (recursion 0/2) | 1 (recursion 0/2) | 0 |
| sim deckHealth (100k) | 67.0 (B) | 66.8 (B) re-run | −0.2 (noise) |
| sim manaReliability | 67.9 | 67.5 | −0.4 (noise) |
| sim threats / interaction / combo / cmdr-indep | 96.6 / 73.1 / 76.4 / 7.8 | 96.6 / 73.1 / 76.4 / 7.8 | 0 |
| comboLethal T6/7/8 | 46.3 / 53.5 / 59.3 | 46.3 / 53.5 / 59.3 | 0 |
| lethalProxy T6/7/8 | 8.0 / 26.1 / 49.4 | 8.0 / 26.1 / 49.4 | 0 |
| commander cast by T6 | 85.9% | 85.9% | 0 |
| win_turn best/typical/contested | 3 / 7 / 8 | 3 / 7 / 8 | 0 |
| Game Changers | 7 | 7 | 0 |
| Karsten G / R / W | 22/20, 17/13, 17/14 | same | 0 |

The goldfish half of the sim is seeded, so it reproduced the baseline exactly; only the unseeded mana half moved, inside noise. The re-run was not committed — the baseline `simulation.json` stays the file of record, since the 99 did not change. `win_turn` re-derived with the metric's own rule (typical = first turn where max(comboLethal, lethalProxy) ≥ 50%) gives T7 (53.5%), matching the stored triple.

## 3. Bar check

Bracket "4", shell 77, payoff 46.3% (max of comboLethal@T6, lethalProxy@T7) — `validate_strategy_ceiling.py` reports ok, no warnings. Fleet bar (≥ B3+/4−) met. One number to state plainly: comboLethal at T6 reads 46.3%, below the 50% gate the DEC-544 build used to confirm the "4" label (53.3% at build). The DEC-574 record attributes the drop to the goldfish being blind to Solphim (it sees a 4-mana converter arriving later; it cannot see that Solphim halves the Egg deaths a table kill needs, 7 → 4) and to Elspeth's token doubling. That standing judgment keeps the label at "4"; the deck stays `status: brewing` per the strategy overview until a sim that models those effects confirms the turn-6 rate. `check_game_changers.py --offline`: ts mirror ok (53 cards), fleet recount 0 problems; deck at 7 Game Changers, uncapped at bracket 4.

## 4. Stale-reference sweep

Swept `guideContent`, `deckCategories[].description`, `winConditions`, `highlights[].reason`, `synergies` for every card cut since the DEC-544 build — Gamble, Warleader's Call, Wild Growth, Titan of Industry, Heroic Intervention, Impact Tremors, Sun Titan, Rishkar's Expertise, Utopia Sprawl, and the Plains count: **0 live mentions**. The only hits are dated decision records in `sources[]`, which stay. Idol of Oblivion appears in prose and is in the 99 (cut at DEC-570, re-added at DEC-574). `validate_deck_json.py`: 209 references, clean.

Two prose defects found and fixed in this pass:
1. `strategyOverview` said "10 ramp sources … 10 draw pieces". After DEC-931 (Rishkar's Expertise was tagged card-draw, Utopia Sprawl was tagged ramp) the role counts are 9 and 9. Both numbers corrected. Other counts re-checked and still true: 6 tutors, 6 protection pieces, 7 Game Changers, "37 lands, 36 of them untapped", "Six tutors" in the Tutors category.
2. The Identity Echo highlight said exiling the locked Atla "sends her to the command zone" under Darksteel Mutation **or Imprisoned in the Moon**. Under Imprisoned in the Moon (Scryfall: "Enchanted permanent is a colorless land … and loses all other card types") Atla is a land, not a creature or planeswalker, so Identity Echo cannot target her. Under Darksteel Mutation she is still a creature (an Insect artifact creature), so the exile-to-command-zone line holds. Sentence rewritten to say exactly that. The Free Sacrifice Outlets category already limited the claim to Darksteel Mutation and is correct.

## 5. Deck Review Checklist items

**EDHREC closing diff** (263 rated cards, fetched today 14:36Z). The ≥40% absentee set is identical to the DEC-931 apply-report list; the items that report deferred to this re-assessment now have lines:
- Etali, Primal Storm 59.1% — reject: attack trigger only; a hatched Etali does nothing on arrival.
- Zetalpa, Primal Dawn 51.2% — reject: keyword body, 4 power; the converters deal 4 off it where the deck's mean flip power is 5.67.
- Ghalta and Mavren 49.2%, Ghalta, Primal Hunger 48.5% — reject: 12-power bodies are strong converter ammo (Terror of the Peaks or Warstorm Surge deal 12), but they need a converter already on the battlefield to matter and do nothing themselves on arrival; the impact-on-arrival bar from DEC-544 stands.
- Ghalta, Stampede Tyrant 46.2% — **defer, first in line for a bomb slot**: the only family member with a real enters trigger (put any number of creature cards from your hand onto the battlefield, each of which fires the converters and Guardian Project), on a 12-power body. Not proposed: no bomb slot is weaker than it, the curve penalty is already 15 points (11 cards at MV 7+), and the owned copy is committed to verdant-tide.
- Gishath, Sun's Avatar 42.0% — reject: combat-damage gated.
- Cinder Glade 54.4%, Canopy Vista 49.9%, Sunpetal Grove 41.8% — defer: see manabase; Cinder Glade stays first in line if the land count ever goes to 38 (Forest and Mountain types, so Nature's Lore, Three Visits and Farseek all fetch it; untapped with two basics, and the deck runs 18).
- Rhythm of the Wild 51.0% — defer: haste only matters for the Titan Combat backup; the "can't be countered" half does not apply to hatched creatures, which are not cast.
- Sundering Growth 45.1% — defer, on the interaction shortlist with Celebrate: 2-mana instant answer to the artifact and enchantment hoser classes, and populate copies an Egg with Atla out. Removal-spot 6/8 is the lowest role score; this and Celebrate are the two named candidates when the board opens that slot.
- Swiftfoot Boots 41.9% — reject: Lightning Greaves is in; protection sits at 6/4.
- Dinosaur Egg 41.6% — reject: it is an Egg, so its death does trigger Atla, but as a flip it is a 0/3 that does nothing on arrival, and discover 3 finds ramp spells, not bombs.
- Heroic Intervention 40.8% — DEC-574 board cut. Etali, Primal Conqueror 41.5% — name alias for the DFC already in the 99. Cultivate 63.5%, Rampant Growth 55.6%, Kodama's Reach 43.7%, Jungle Shrine 59.7% — standing rejects.

**Manabase audit** (`manabase_check.py`): lands 37 (target 40.9), untapped 36, fetch 3, Karsten G 22/20, R 17/13, W 17/14 — all pass; land_count is the only component scoring 0. The 40.9 target derives from the 3.94 average nonland mana value, which counts the nine MV-7+ hatch bombs the deck never means to cast. Excluding the MV-7+ bucket, the 53 castable nonland cards average 3.09, which supports 37. Sim confirms: 2-land keeps 34.5%, mulligan verdict "excellent", commander cast by T4 70.2%. Decision: hold at 37; Cinder Glade is the named 38th land if a later round shows a land deficit. Jetmir's Garden remains the one unconditional tapped land (board-kept at DEC-544). Owned untapped any-colour lands (Three Tree City, Baxter Building, City of Brass, Mana Confluence, Nykthos, Reflecting Pool, Study Hall) — defer: no colour deficit to fix; Mana Confluence has fleet demand 3 on 2 copies. Restricted-mana lands (Cavern of Souls class) reject.

**Hoser coverage** (hate classes: library-to-battlefield stoppers, graveyard replacement, enters-trigger stoppers):
- Grafdigger's Cage / Torpor Orb (artifact): Aura Shards, Krosan Grip, Force of Vigor, Boseiju, Beast Within — 5 answers.
- Rest in Peace (enchantment; exiles tokens too, so Eggs never "die" and Atla stops): Aura Shards, Krosan Grip, Force of Vigor, Boseiju, Beast Within — 5 answers. Leyline of the Void does not stop the engine: it exiles cards, and Eggs are tokens.
- Containment Priest / Hushbringer (creature): Swords to Plowshares, Path to Exile, Beast Within, Blasphemous Act, Winds of Abandon, Zacama, Apex Altisaur, Eiganjo channel — 8 answers.
- Planeswalker-carried hosers: Beast Within, Zacama. Pass; unchanged since DEC-574.

**Commander dependency** (sim commanderIndependence 7.8 — honest modeling, all three KEY_COMBOS run through Atla). Backup lines in the 99: Identity Echo (enchantment hatch, {3}{R} sorcery-speed), Palani's Hatcher (two Eggs on entry and a once-per-combat sacrifice that makes a 3/3), Nesting Dragon (Dragon Egg per land drop), Birthing Pod, Natural Order, Chord of Calling. Under a Darksteel Mutation lock (Atla stays on the battlefield as a creature, CR 903.3d, no zone change): five enchantment answers destroy the aura; any of Ashnod's Altar, Phyrexian Altar, Goblin Bombardment or High Market sacrifices her to the graveyard where the command-zone replacement applies; Identity Echo exiles her to the same effect. Under Imprisoned in the Moon or Song of the Dryads (Atla becomes a land): Krosan Grip, Force of Vigor, Beast Within and Boseiju (the aura is an enchantment an opponent controls) answer the aura; the sacrifice outlets and Identity Echo cannot target a land. Pass, with the Identity Echo prose corrected accordingly.

**Permanent-type durability**: the engine already sits on artifacts and enchantments (Maskwood Nexus, Thornbite Staff, both Altars, Goblin Bombardment, Identity Echo, Guardian Project, Warstorm Surge); the creature engine pieces (Seedborn Muse, Roaming Throne, Palani's Hatcher, Nesting Dragon) have no artifact or enchantment equivalents at equal function. No action.

**Recursion gap (0/2)**: accepted again. The deck's resource is the library, not the graveyard; Worldspine Wurm, Vigor and Blightsteel Colossus shuffle themselves back, and Identity Echo covers the commander recast. No free owned candidate qualified at DEC-574 and none surfaced today.

## Disposition

PASS, no proposal needed. Prose fixes land with this report. Round counter resets to 0 at the closing commit; next Trigger-2 fires after 3 new board-approved rounds.
