# DEC-930 — Hoard and Bleed Trigger-2 re-assessment (PASS)

Date: 2026-09-28. Assessor: CEO. Baseline: DEC-548 close (commit `9579a86`). Current: the working tree with the DEC-929 round applied (+Turbulent Crater / −Mountain).

## Verdict

**PASS — no swaps proposed.** Global health flat at 97 with zero gaps, all validators clean, bar check clean, GC count 2 (uncapped at 4−). One prose correction applied (average nonland mana value 2.97 → 2.95). The swap-round counter resets to 0 at the commit that lands this report together with the DEC-929 Hoard and Bleed files.

## Rounds covered (3 board-approved rounds since DEC-548)

1. DEC-579 — +Necropotence / −Idol of Oblivion (commit `f61084e`)
2. DEC-687 — +Lotus Petal / −Rakdos Signet (commit `393a638`)
3. DEC-929 — +Turbulent Crater / −one basic Mountain (board comment 7864d22d; applied 2026-09-28, lands with this report)

## 1. Card pool refresh + top-50 triage

`refresh_card_pool.py --deck hoard-and-bleed` ran today at 14:05Z on the current 99 (DEC-929 post-swap hygiene): mirror 2026-09-28 (post-Reality Fracture), EDHREC rates fetched today (293 cards), 200 candidates, `gaps[]` empty. Reused as-is; nothing changed in the deck since.

All 50 top-50 non-deck candidates fall into standing dispositions. No new printing entered the top 50 since DEC-548:
- **DEC-543 closing-diff rejects (in `sources`)**: Smaug the Magnificent, Magda (needs a Dwarf), Alchemist's Talent, Descent into Avernus, Knuckles the Echidna, Seize the Spoils, Cavern-Hoard Dragon.
- **DEC-548 rejects**: attack-gated (Postmortem Professor, Sanguine Syphoner, Typhoid Mary, General Kreat, Kardur, Send in the Pest), creature-death-gated (Zulaport Cutthroat, Bastion of Remembrance, Blood Artist, Grave Venerations, Sephiroth, Lobelia), lifegain-gated (Marauding Blight-Priest, Starscape Cleric, Leech Collector), rate/uptime (Glóin, Melancholic Poet, Dimension X Pizzasaur, Hazel's Nocturne, Sinister Monolith, Twinflame, Coin of Mastery, Impulsive Pilferer, Fall of Cair Andros, Glaring Fleshraker), consistency (Yahenni).
- **DEC-548 defers, standing**: Soul-Shackled Zombie, Atsushi, Fable of the Mirror-Breaker.
- **Deliberate cuts**: Revel in Riches (round 9), Idol of Oblivion (DEC-579), Infernal Grasp (round 7 for Withering Torment).
- **Names with no prior line — triaged today, oracle verified on Scryfall**:
  - The Misty Mountains Cold (I–IV: one Treasure per chapter; sacrifices itself at four Treasures for a 6/6 Dragon) — defer: one Treasure per turn for four turns is below Storm-Kiln Artist and Professional Face-Breaker rates; no slot beats an incumbent.
  - Mastermind Plum (Smaug's draw clause on a 3-MV body; Treasure half is attack-gated) — defer: a second copy of the commander's engine is real redundancy, but the deck already draws without Smaug (Necropotence, Citadel, Skullclamp, Black Market Connections) and `commanderIndependence` is 72.1. Keep on the list for a future card-draw slot.
  - Torment of Hailfire — reject: the loop already converts infinite mana through Exsanguinate, which gains the life this deck spends; Hailfire adds a fourth mana sink for no new failure case.
  - Sedgemoor Witch — reject: Pest tokens are creature tokens, so they fire Mirkwood Bats on entry and feed Ashnod's Altar, but the deck runs 21 instants and sorceries and Storm-Kiln Artist already converts each into a Treasure (an artifact, which also fires Fireweaver and Weftstalker). Strictly less on-plan than the incumbent.
  - My Precious // Allure of Power — reject: the Adventure half is Deadly Dispute without the Treasure; the Equipment half is combat-gated.
  - Gollum, Riddle Master — reject: opponent-cast-gated, no Treasure or sacrifice interaction.
  - Infectious Inquiry — reject: Night's Whisper class was already cut for Citadel in DEC-548.
  - Perforating Artist — reject: Raid, attack-gated.
  - Scheming Aspirant — reject: proliferate-gated, zero proliferate sources in the 99.
  - Gollum the Abandoned — defer: recurs itself by sacrificing an artifact (a Treasure), two life per loop, but the entry drain is once per cast and the self-return is sorcery-speed for {2}. Fodder role already covered by Skeleton and Bloodghast.
  - Nadier's Nightblade — standing DEC-543 reject (drains on token leaving only; Mirkwood Bats fires on create and sacrifice).

Include: none.

## 1b. Archetype recipe sweep (aristocrats, artifacts-matter, tokens-go-wide — all live)

Ran 34 sub-recipe queries (commander sub-recipes skipped) with the `id<=br` splice, EDHREC order, cap 50, post-filtered against the 99 and candidates top-50. 331 deltas (raw in run scratch). No include. Named lines for anything with a Smaug-page rate at or above 10% or a global EDHREC rank inside 1000:
- Urza's Saga 18.7% — reject: colorless-only land against 45 black and 25 red pips (DEC-543 Dragon-Cursed Halls precedent); also locked to the-white-forge.
- Orcish Bowmasters 12.6% — standing DEC-548 defer for gathering-shadow; not re-litigated.
- Bonehoard Dracosaur 20.1%, There and Back Again 33.0% — defer: both are 5-MV engines whose payoff is turns away; curve sits at 2.93 against a 2.8 target and neither addresses a gap. Both sit below the 40% closing-diff bar.
- Gray Merchant of Asphodel, The Meathook Massacre, Falkenrath Noble, Vengeful Bloodwitch, Funeral Room — reject as a class: creature-death or devotion drain; this deck sacrifices Treasures (strategy record, DEC-543 rev2).
- Foundry Inspector, Mystic Forge, Cranial Plating, Adaptive Omnitool — reject: the deck's artifacts are mostly tokens, which are never cast, and the deck does not attack.
- Bitterblossom — defer with note: a Faerie each upkeep fires Mirkwood Bats and feeds Ashnod's Altar and Skullclamp, but it charges one life per turn on top of Smaug, Necropotence and the painlands. Ophiomancer fills the upkeep-fodder role without the life tax.
- Ichor Wellspring, Mycosynth Wellspring, Prized Statue — defer: card-draw is the lowest role score (8.0 vs target 10, score 80) but is not a `gaps[]` entry; Ichor Wellspring plus Krark-Clan Ironworks is the best of the three if a draw slot opens.
- Scrap Trawler, Myr Retriever, Junk Diver — defer as a class: artifact recursion without a second recursion piece is a value engine, not a loop.
- Liliana, Dreadhorde General, Grave Titan, Wurmcoil Engine, Myr Battlesphere, Army of the Damned and other 6+ MV hits — reject: off-curve top end.
- Krenko lines, Goblin token spells, Empty the Warrens, Hangarback Walker, Pawn of Ulamog — reject as a class: creature-token go-wide is off-idiom; this deck's tokens are Treasures.

## 2. Before/after vs DEC-548 baseline

| Measure | DEC-548 (`9579a86`) | Now (DEC-929 applied) | Δ |
|---|---|---|---|
| manabase_health | 91 | 91 | 0 |
| role_coverage | 104 | 104 | 0 |
| curve_health | 96 | 97 | +1 |
| interaction_density | 120 | 120 | 0 |
| gameplan_cohesion | 57 | 57 | 0 |
| resilience_health | 100 | 100 | 0 |
| **global_health** | **97 / norm 100** | **97 / norm 101** | **0 / +1** |
| gaps[] | 0 | 0 | 0 |
| sim deckHealth (100k) | 71.1 (B) | 70.8 (B) | −0.3 |
| sim manaReliability | 73.2 | 72.1 | −1.1 |
| sim threats / interaction / combo / cmdr-indep | 81.0 / 73.1 / 50.3 / 72.1 | 81.0 / 73.1 / 50.3 / 72.1 | 0 |
| comboLethal T6/7/8 | 5.3 / 7.3 / 9.5 | 5.2 / 7.3 / 9.4 | −0.1 / 0 / −0.1 |
| lethalProxy T6/7/8 | 21.0 / 45.8 / 67.9 | 20.7 / 44.9 / 66.9 | −0.3 / −0.9 / −1.0 |
| commander cast by T6 | 86.0% | 86.1% | +0.1 |
| Game Changers | 1 (Bolas's Citadel) | 2 (+Necropotence) | +1 |
| Karsten B / R sources | 27.1 / 27.0 | 28.1 / 27.0 | +1.0 / 0 |

The sim used here is the 100k run from today's DEC-929 hygiene on the current 99. The −1.1 manaReliability is the Turbulent Crater model: the sim gates it untapped from the 4th land drop (conservative, same model as Turbulent Springs in DEC-688), where the cut Mountain was always untapped. Lotus Petal for Rakdos Signet is neutral in the sim (both count as fast mana; Petal is one-shot). Payoff curves move within one point at every turn.

`win_turn` note: the stored baseline triple reads best/typical/contested 6/7/8; the current file reads 6/8/9. Re-deriving from both sims with the metric's own rule (typical = first turn where max(comboLethal, lethalProxy) ≥ 50%) gives 6/8/9 in **both** cases (lethalProxy at T7 is 45.8 then and 44.9 now, both under 50). The stored baseline triple was computed against an earlier sim file. No real movement.

## 3. Bar check

Bracket 4−, shell 91, payoff 44.9% (max of comboLethal@T6, lethalProxy@T7) — `validate_strategy_ceiling.py` reports ok, no warnings. Fleet bar (≥ B3+/4−) met. `check_game_changers.py`: list drift ok (53/53), ts mirror ok, fleet recount 0 problems; deck at 2 GCs (Bolas's Citadel, Necropotence), uncapped at 4−.

## 4. Stale-reference sweep

Swept `guideContent`, `categories[].description`, `winConditions`, `highlights[].reason`, `synergies` for the three cut names since baseline — Idol of Oblivion, Rakdos Signet, and the Mountain count: **0 live mentions**. The only hits are dated decision records in `sources[]` (round 9 "six Swamp and six Mountain", DEC-579 "OUT Idol of Oblivion"); those describe the deck at that date and stay. `validate_deck_json.py`: 265 references validated, clean. Category card lists carry Turbulent Crater (Mana Base) and Lotus Petal (Rituals and Fast Mana).

One numeric staleness found and fixed: strategyOverview and the Bolas's Citadel highlight both said the average nonland mana value is 2.97. After Idol (2) → Necropotence (3) and Signet (2) → Petal (0) the 59 non-MDFC nonland cards average 2.95 (2.93 if the two MDFCs count, which is the metrics figure). Both strings now read 2.95. Other counts re-checked and still true: "Thirty-eight lands", "Four tutors, none of them a Game Changer", "Eight spot answers plus Vandalblast and three sweepers".

## 5. Deck Review Checklist items

**EDHREC closing diff** (293 rated cards, fetched today 14:05Z). Misses ≥40%, every one with a standing disposition; none reopened:
- Smaug the Magnificent 74.2%, Nadier's Nightblade 50.6%, Terminate 45.5%, Seize the Spoils 41.7% — DEC-543 closing-diff rejects (attack-gated / token-leaves-only / removal count / dead ritual).
- Cavern-Hoard Dragon 61.5%, Magda 53.5%, Alchemist's Talent 51.9%, Generous Plunderer 47.5%, Dragon-Cursed Halls 47.1%, Smaug the Impenetrable 42.8% — DEC-543 rejects.
- Grim Hireling 53.7%, The Reaver Cleaver 42.5%, Ancient Copper Dragon 40.9% — DEC-543 defers (combat-gated).
- Revel in Riches 43.1% (round-9 cut), Rakdos Signet 42.4% (DEC-687 cut), Dark Ritual 42.9% (DEC-687: no qualifying cut) — deliberate.
- The Misty Mountains Cold 43.1% — defer (triaged above).
- Haunted Ridge 42.3%, Blazemire Verge 40.1% — DEC-543 rejected on price; that reason no longer stands (DEC-577: price is not a decision factor). Re-triaged on merits today: Karsten is green with 8.1 black and 9.0 red sources of headroom, the manabase scores 91, and both would replace a basic that Prismatic Vista, Fabled Passage and Bloodstained Mire fetch. Defer — no deficit to fix; Haunted Ridge is also locked to eternal-agony.

**Manabase audit** (`manabase_check.py`): lands 39.1 (target 39.4), untapped 37.7, fetch 3.0, Karsten B 28.1/20, R 27.0/18 — all pass. Unconditional tapped lands: Bojuka Bog (board-kept, DEC-543) and the Malakir Rebirth back face. Top owned candidates (Baxter Building, Nykthos, Study Hall, The Grey Havens at 29) are cost- or condition-gated any-colour producers that the ranking scores optimistically; with no colour deficit, defer all. Restricted-mana lands (Cavern of Souls class) reject.

**Hoser coverage** (top hate classes: artifact hate against Treasures; graveyard hate against Skeleton, Bloodghast, Reanimate, Phyrexian Reclamation; board wipes against the eight creature payoffs):
- Enchantment-carried (Stony Silence, Rest in Peace, Leyline of the Void): Withering Torment, Feed the Swarm, Chaos Warp — 3 answers.
- Artifact-carried (Grafdigger's Cage, Torpor Orb, Damping Sphere): Abrade, Chaos Warp, Vandalblast — 3 answers.
- Creature-carried (Collector Ouphe, Dauthi Voidwalker): 8 primary spot answers plus Goblin Bombardment and Mayhem Devil pings.
- Planeswalker-carried (Karn, the Great Creator): Chaos Warp, Fell the Profane.
- Wipe recovery: Fake Your Own Death, Malakir Rebirth, Deflecting Swat, Phyrexian Reclamation (repeatable). Unchanged since DEC-548; the Interaction category already states this coverage. Pass.

**Commander dependency**: sim commanderIndependence 72.1. Card advantage without Smaug: Necropotence, Bolas's Citadel, Skullclamp, Black Market Connections, Big Score, Deadly Dispute, Unexpected Windfall. All four win conditions are commander-independent. Under a Darksteel Mutation-class lock (Smaug stays on the battlefield, CR 903.3d — no zone change, no command-zone return): three enchantment answers destroy or shuffle the aura, and any of the five creature sacrifice outlets (Ashnod's Altar, Goblin Bombardment, Warren Soultrader, High Market, Diabolic Intent) moves the locked Smaug to the graveyard, where the command-zone replacement applies and he recasts clean. Pass.

## Disposition

PASS, no proposal needed, round counter reset to 0 at the closing commit. Next Trigger-2 fires after 3 new board-approved rounds.
