# DEC-933 — Field of Blades (stampede-acres) Trigger-2 re-assessment (PASS)

Date: 2026-09-29. Assessor: CEO (DEC-461: card reviews are CEO-executed). Baseline: commit `9d3e67f` (DEC-931 apply, 2026-09-29). Previous assessment: DEC-581 (commit `18e7db6`, 2026-09-01).

## Verdict

**PASS — the deck keeps its 4− bar. One optional swap goes to the board on a verdict card; the PASS does not depend on it.** Global health 85 (normalized 93), sim health 72.8 grade B, two known gaps (both board-accepted), all validators clean, 7 Game Changers (uncapped at 4−). Two prose corrections and one missing source entry were fixed. The swap-round counter resets to 0 at the commit that lands this report.

## Rounds covered (3 board-approved rounds since DEC-581)

1. DEC-685 — +Gleaming Splendor / −Raise the Alarm, +The Queen of Dale / −Parallel Lives (commit `a5832e2`)
2. DEC-929 — +Draconic Visitor / −Wedding Announcement (commit `0b4dd9f`)
3. DEC-931 — +Rockfall Vale / −Jungle Shrine, +Overgrown Farmland / −Path of Ancestry (commit `9d3e67f`)

## 2. Before/after table

Metrics (`compute_deck_metrics.py`, weights A) and re-sim (`export_simulation_results.py --deck stampede-acres`, 100k mana games, 10k goldfish) run today on the current 99. Baseline columns read from the committed files at each commit.

| Signal | DEC-581 close (`18e7db6`) | Baseline `9d3e67f` | Today (re-run) |
|---|---|---|---|
| global_health / normalized | 85 / 93 | 85 / 93 | 85 / 93 |
| manabase / roles / curve | 76 / 88 / 98 | 78 / 89 / 98 | 78 / 89 / 98 |
| interaction / cohesion / resilience | 104 / 53 / 80 | 104 / 52 / 80 | 104 / 52 / 80 |
| gaps[] | 2 | 2 | 2 |
| sim health (grade) | 72.3 (B) | 72.8 (B) | 72.9 (B) |
| manaReliability / threats / interaction / combo / cmdr-indep. | 70.9 / 99.5 / 73.1 / 50.8 / 59.0 | 71.6 / 99.5 / 73.1 / 50.9 / 61.5 | 71.7 / 99.5 / 73.1 / 50.9 / 61.5 |
| lethalProxy T6 / T7 / T8 | 14.1 / 35.3 / 55.6 | 19.9 / 44.1 / 64.1 | 19.9 / 44.1 / 64.1 |
| comboLethal T6 / T7 / T8 | — / 10.6 / — | 8.7 / 10.8 / 13.6 | 8.7 / 10.8 / 13.6 |
| commander median cast turn (T3 %) | 3 | 3 (74.1) | 3 (74.3) |

The re-run reproduces the committed sim within Monte Carlo noise (±0.1), so the rerun file was reverted, not committed. Trend across the three rounds: lethalProxy T7 35.3 → 44.1 and T8 55.6 → 64.1 (Visitor's 5/5 flyers plus the two untapped lands), manabase 76 → 78, cohesion 53 → 52 (Took-class artifact-token cards are outside the tokens-go-wide in-set match).

## 1. Card pool refresh + top-50 triage

`refresh_card_pool.py --deck stampede-acres` at 14:36Z: mirror current (2026-09-29), EDHREC rates fresh (2026-09-28, 277 cards), 200 candidates unchanged, `gaps[]` = removal-board 2/3 and recursion 1/3 (both board-accepted at DEC-378/DEC-581; not re-flagged).

New lens this round: Draconic Visitor (DEC-929) turns every artifact-token maker into a 5/5 flying Dragon maker, so the Food/Treasure/Clue candidates were re-read against it. The Visitor pairing is single-card-gated (Visitor is 1 of 99), so each card is judged on its base case first.

**Standing dispositions (no new evidence, not reopened):**
- Parallel Lives 71.3 — DEC-685 board cut. Second Harvest 69.2, Exalted Sunborn 57.0, Carrot Cake 54.0 — DEC-378 board cuts.
- Doubling Season 70.2 — DEC-581 defer. The 99 now runs three multipliers after the Parallel Lives cut; the board accepted the lower doubler density in DEC-685 (P(≥1 doubler in the first 13 cards) 44% → 35% on record). Same Tithe + Splendor Spellbook class as the three included lines (near-miss 4682-4772-7890). Defer stands.
- Tireless Tracker 57.0, Wojek Investigator 56.7 — DEC-378 defers (owned draw leads).
- Jacked Rabbit, Finneas, Farmer Cotton, Cadira (EDHREC 40–44%, ranks 50–51 or below) — DEC-931 defer class, re-read today: Jacked Rabbit, Finneas and Cadira are attack- or combat-damage-gated (×1 per turn cycle); Farmer Cotton is a one-shot X spell on a body. Defer behind the instant-speed X makers.

**Triaged today (oracle text from the Scryfall mirror; every card considered for inclusion was re-verified through the Scryfall MCP):**
- **Peregrin Took 68.1 (41.1%) — proposal line A, see below.** DEC-931 deferred it as "not oracle-verified this round"; verified today.
- Wildfire Awakener 65.6 — defer. X convoke Elementals that deal 1 damage to a player whenever they become tapped; Baylen's three tap costs and Prosperous Partnership tap 2–4 tokens per activation, so each activation pings. Strongest new one-shot producer, but sorcery-speed and creature-bound versus Secure the Wastes, March of the Multitudes and Grand Crescendo. First in line for the next producer slot.
- Agate Instigator 64.9 — defer. A fourth "creature enters: 1 damage to each opponent" on a creature body; Impact Tremors, Purphoros and Warleader's Call already cover it on enchantments (DEC-474 L10 tiebreak). Revisit if wincon redundancy drops.
- Tireless Provisioner 64.6 — defer. Landfall Food or Treasure at ~1.1 per turn cycle; the same Visitor upside as Took at a fraction of the rate.
- Hare Apparent 63.5 — reject. Singleton; makes zero tokens alone.
- Academy Manufactor 62.9 — defer. Triples every Treasure/Food/Clue event (Tithe, Splendor, Partnership, Rosie's Food); with Took it is an infinite Food/Clue/Treasure loop. Revisit only if line A lands.
- For the Common Good 59.0 — reject. XXG sorcery that copies one token; Second Harvest class.
- Fall of Cair Andros 58.7 — reject. Needs excess noncombat damage to opponents' creatures; the deck has no burn.
- Intangible Virtue 58.4 — defer. Warleader's Call holds the anthem slot; vigilance fights Halo Fountain's tapped-creature costs.
- Springleaf Parade 58.4 — reject. Tokens tapping for mana duplicates Baylen's first ability and Prosperous Partnership.
- Gilded Goose 57.9 — reject. Ramp is 11 against a target of 10.
- Call the Coppercoats 57.2 — defer. Instant, X equals opponents' creatures; table-dependent; behind the three instant X makers.
- Cathars' Crusade 57.2 — defer. Spellbook near-miss 2744-4186 with Scurry Oak at distance 1 (creature enters → counter on Oak → Squirrel → repeat), on an enchantment. 5 MV against a 2.87 curve, and the resilience redundancy component is already at its 25-point maximum with three lines. Owned x3; the anvil-chorus copy is in a brewing deck and does not lock. Revisit if a 5+ MV slot opens or resilience drops.
- Endless Foot Assault 56.7, Hammers of Moradin 56.7, Redoubled Stormsinger 53.7 — reject. Attack-gated (×1 per cycle); Hammers' myriad copies and Stormsinger's copies leave at end of combat or end step.
- General Kreat 56.7 — reject (Goblin-gated; no Goblins). Glaring Fleshraker 56.7, Basking Broodscale 55.9 — reject (colorless- or counter-gated).
- Monologue Tax 56.7 — defer. Treasure on an opponent's second spell each turn; fires roughly once per cycle at a four-player table, below Smothering Tithe's three.
- Chord of Calling 56.6 — defer. Fourth tutor (role 3/4), instant, convoke off tokens fetches Rosie, Oak, Seedborn or an X=8 Craterhoof. No incumbent slot; first in line if the tutor gap is prioritized.
- Professional Face-Breaker 56.2 — reject. Combat-damage-gated Treasure.
- Ajani, Nacatl Pariah 54.8 — defer (Scryfall-verified). Two bodies for two mana with no condition, which is exactly the low-MV floor the board named in DEC-929. The flip needs a Cat to die, and the 99 has no sacrifice outlet (Skullclamp or combat only). Flipped, the 0 makes a 2/1 Cat and deals creature-count damage to any target while Baylen (a red permanent) is out. No incumbent 2-drop is weaker: Springheart Nantuko makes a free 1/1 Insect on every land drop and copies a bestowed creature for {1}{G}. Owned x1, free. First in line for the next ≤2-MV slot.
- Coruscation Mage 54.8, Vivi's Persistence 54.8 — reject. Noncreature-cast pingers; 19 instants and sorceries.
- Spiteful Banditry 54.8, Martial Coup 54.6 — reject. The board capped the deck at two sweepers (DEC-378, Blasphemous Act); removal-board 2/3 stays an accepted deviation.
- Tataru Taru 54.8 — defer. One tapped Treasure per turn on an opponent's off-turn draw (up to three per cycle); Tithe class at a lower rate.
- Witch's Mark 54.8 — reject. One-shot loot plus a Role token.
- Finale of Glory 54.3, Forth Eorlingas! 53.1 — defer. Sorcery X makers behind the instant ones.
- Celebrate the Mountain-king 54.2 — defer. Exiles up to one nonland permanent per opponent (×3) on an enchantment plus a recruit; removal-spot is 6.5/8. First in line for a removal-spot add.
- Master of Ceremonies 54.2 — reject. Opponents choose the mode.
- Divine Visitation 54.0 — reject. 4/4 Angels stop Skullclamp from killing the fodder; 5.9% on the page.
- Awakening Zone 53.9 — defer. One Spawn per own upkeep.
- Determined Iteration 53.8 — reject. The populated copy is sacrificed at end step.
- Tendershoot Dryad 53.8 — defer. A Saproling on each upkeep (×4 per cycle) is the best token rate on the list, on a 5-MV creature. Revisit for a 5-MV slot with Cathars' Crusade.
- Assault on Osgiliath, Book of Mazarbul, Swarming of Moria 53.7 — reject. Amass grows one Army token; no width.
- Fractal Harness 53.7 — reject. One token with counters.
- Samwise Gamgee 53.4 — defer. Food per nontoken creature entering (~1 per turn) and "sacrifice three Foods: return a historic card" (Skullclamp, Cori-Steel Cutter, Idol, every legend) — a recursion answer for the accepted 1/3 gap. Revisit after line A, when Took would supply the Foods.

Include: **one** (Peregrin Took, as a proposal only).

Archetype recipe sweep (Research Workflow step 1b) was not run; it is not in the DEC-933 rubric, and DEC-931 swept the Reality Fracture set fleet-wide yesterday.

**Spellbook near-miss triage (step 4):** 120 near-misses on the corpus 2026-09-29T15:10 file; 4 included (Rosie + Oak; Tithe + Splendor with each of Procession, Mondrak, Elspeth). Named lines: Cathars' Crusade + Oak — defer (above). Doubling Season and Parallel Lives Tithe lines — standing defer / board cut. The rest (Kodama of the East Tree ×7, Ghost Town ×7, Sylvan Awakening, Nissa and land-animation lines, Tidespout Tyrant, Storm Herd, Kenrith) are off-plan land or storm loops — reject as a class.

## 3. Bar check

Bracket 4−, shell 78, payoff 44.1% (max of comboLethal@T6, lethalProxy@T7) — `validate_strategy_ceiling.py` ok, no warnings. Fleet bar (≥ B3+/4−) met. `check_game_changers.py --offline`: ts mirror ok (53 cards), fleet recount 0 problems; deck at 7 GCs, uncapped at 4−.

## 4. Stale-reference sweep

Swept `guideContent`, `deckCategories[].description`, `winConditions`, `highlights`, `synergies` against the 32,116-name oracle mirror: **zero references to cards outside the 99**. The cut names since baseline (Raise the Alarm, Parallel Lives, Wedding Announcement, Jungle Shrine, Path of Ancestry) appear only in dated `sources[]` decision records. `validate_deck_json.py`: 194 references, clean. `deckCategories` carry no land category by design (unchanged since DEC-347).

Two prose errors found and fixed (oracle-verified today):
- Halo Fountain win condition said "on a wide, vigilant board". Fountain's costs read "untap fifteen tapped creatures you control", so vigilance works against it. Rewritten: Baylen's tap abilities and attacks set it up; Seedborn Muse untaps the Fountain for reuse.
- Scurry Oak line named only Impact Tremors and Purphoros as the damage converters. Warleader's Call ("whenever a creature you control enters, 1 damage to each opponent") is the third; added to the description and the `cards` list.

One attribution gap fixed: the DEC-931 apply added no `sources[]` entry for this deck's two land swaps. Entry added (verdict card 682b6545, lines E and F, with the recorded numbers).

## 5. Deck Review Checklist items

**Manabase audit** (`manabase_check.py`): lands 37.0 (target 39.3 — the 37 count is the DEC-378 board decision; land_count component 0 since then), untapped 37 of 37, fetch 3.0, Karsten G 23/14, R 18/13, W 26/18 — all met; pip census G 23, R 11, W 49. Top owned candidates: Three Tree City (21%), City of Brass, Mana Confluence — all any-colour untapped, but there is no colour deficit and every swap would replace a fetchable basic; defer. Cinder Glade (38%), Sungrass Prairie, Bountiful Promenade — conditional; defer. Restricted producers (Cavern of Souls class) — reject. Jetmir's Garden 43% — reject (always tapped, the class DEC-931 just cut).

**EDHREC closing diff** (277 rated cards, fetched 2026-09-28). Every ≥40% miss carries the DEC-931 apply-report call, re-affirmed today: Second Harvest 50.2 (DEC-378 cut), Doubling Season 46.3 (defer), Farseek 43.7 (defer: Nature's Lore plus four dorks; enters tapped), Jacked Rabbit 43.6 (defer, attack-gated), Jetmir's Garden 43.3 (reject), Parallel Lives 42.8 (DEC-685 cut), Jungle Shrine 42.4 (DEC-931 cut), Heroic Intervention 42.4 (defer: Clever Concealment, Flawless Maneuver, Grand Crescendo), Aura Mutation 42.4 (defer: Artifact Mutation in; Aura Shards and Pest Infestation cover enchantments), Peregrin Took 41.1 (line A), Finneas 40.7, Farmer Cotton 40.7, Cadira 40.1 (defer, above).

**Hoser coverage** (top hate classes for a go-wide tokens deck: sweepers; ETB and token hate on permanents; tax effects):
- Sweepers (spells): Clever Concealment, Flawless Maneuver, Grand Crescendo — 3 mass-protection instants, plus Sevinne's Reclamation to rebuild — pass.
- Enchantment-carried (Authority of the Consuls, Ghostly Prison, Propaganda, Blind Obedience): Aura Shards (repeatable — fires on every creature entering, so every token wave), Pest Infestation — 2 answers, one repeatable.
- Artifact-carried (Torpor Orb, Cursed Totem, Winter Orb, Static Orb): Aura Shards, Artifact Mutation, Pest Infestation — 3 answers.
- Creature-carried (Elesh Norn, Grand Cenobite; Hushbringer; Kaervek): Swords to Plowshares, Path to Exile, Winds of Abandon, Elspeth, Storm Slayer, The Battle of Bywater (power ≥ 3) — 5 answers.
- Planeswalker-carried: no direct answer; combat (Visitor's 5/5 flyers, Moonshaker) covers it. Noted, not a gap for a go-wide deck. Pass.

**Commander dependency**: sim commanderIndependence 61.5. All three win conditions are commander-independent. Draw without Baylen: Skullclamp, Bennie Bracks, Idol of Oblivion, Belladonna Took, Staff of the Storyteller, Caretaker's Talent, Enduring Innocence, Sylvan Library, The Great Henge, Halo Fountain. Under a Darksteel Mutation-class lock (Baylen stays on the battlefield; CR 903.3d — no zone change, no command-zone return): Aura Shards destroys the aura on the next creature entering, Pest Infestation is the second answer. The 99 has no sacrifice outlet to move him instead; the two enchantment answers are the covering cards. Pass.

**Permanent-type durability**: engines sit on 11 enchantments (Procession, Tremors, Purphoros, Tithe, Splendor, Partnership, Retreat, Aligned Heart, Warleader's Call, Caretaker's Talent, Sylvan Library) and 6 artifacts (Skullclamp, Staff, Idol, Fountain, Cutter, Henge) against 11 creature engines. Line A moves one slot from an enchantment to a creature; that is the L10 tiebreak against it, stated on the card.

## Proposal — line A (optional; verdict card)

- [ ] **IN Peregrin Took — OUT Felidar Retreat.**

Basis: same board, per turn cycle, vanilla four-player model. Retreat fires on own land drops only (×1 per cycle, ~1.1 with the three fetches): one 2/2 Cat, or +1/+1 counters and vigilance. Took's replacement adds one Food to **every** token-creation event: own turn 2–4 events (a producer cast, Adeline and Anim Pakal attacks, Partnership activation, a landfall), opponents' turns 1–3 (Smothering Tithe fires once per opponent draw step ×3, The Queen of Dale up to ×3, instant makers). Call it 3–7 Foods per cycle once two engines are online.

What the Foods do without Visitor: Baylen's "tap three untapped tokens: draw a card" and Took's own "sacrifice three Foods: draw a card" (no mana) turn 3–7 Foods into 1–2 extra cards per cycle; every Food is also a Rosie trigger ("whenever you create a token", per token) and Baylen mana fuel. With Visitor out, each Food becomes a 5/5 flying Dragon instead (Visitor is 1 of 99, so this is upside, not the case). Card-draw is the deck's weakest scored role (7.5 of 10).

What Retreat gives up: creature bodies (each Cat pings 3 with Tremors, Purphoros or Warleader's Call, and counts for Craterhoof); the counters mode seeds the Oak loop (any Rosie trigger does the same). Retreat was the alternative cut I offered in DEC-929; the board chose Wedding Announcement.

In-memory metrics projection (no files written): global 85 → 86, normalized 93 → 94, roles 89 → 91 (card-draw 7.5 → 8.5), curve 98 → 99 (avg MV 2.87 → 2.85), cohesion 52 → 50 (Took is outside the tokens-go-wide in-set match), interaction 104, resilience 80, gaps unchanged. Owned x2, both free. Visible costs: enchantment → creature (L10), Hour of Reckoning kills Took along with the other nontoken creatures.

If accepted: apply with the DEC-929 tail (card-metadata check, card pool, `compute_tokens.py` for the Food token, Combo Lab trio, validator, re-sim, prose sweep — Retreat is only in the Token Producers category list), and the round counter stays at 0 (the swap lands inside the reset).

## Disposition

PASS. Round counter reset to 0 at the closing commit. Next Trigger-2 fires after 3 new board-approved rounds (a line-A apply inside this issue does not count).

## Addendum — line A applied (board verdict card 031e35bb, accepted 2026-09-30 13:56)

**IN Peregrin Took — OUT Felidar Retreat.** Owned x2, no purchase. Applied inside the Trigger-2 reset, so the swap-round counter stays at 0.

Before/after, same inputs (100k mana games, 10k goldfish games, metrics weights A, oracle mirror 2026-09-30):

| Signal | Before (68c99ec) | After |
|---|---|---|
| global_health / normalized | 85 / 93 | 86 / 94 |
| roles (card-draw) / curve / cohesion / interaction / resilience | 89 (7.5) / 98 / 52 / 104 / 80 | 91 (8.5) / 99 / 50 / 104 / 80 |
| avg nonland MV | 2.87 | 2.85 |
| gaps[] | 2 | 2 (unchanged) |
| sim health (grade) | 72.8 (B) | 72.9 (B) |
| manaReliability / commanderIndependence | 71.6 / 61.5 | 71.9 / 61.6 |
| drawEngineReliability count, T6 | 13, 83.5 | 14, 85.8 |
| lethalProxy T6 / T7 / T8 | 19.9 / 44.1 / 64.1 | 22.6 / 47.7 / 67.5 |
| comboLethal T6 / T7 / T8 | 8.7 / 10.8 / 13.6 | 9.0 / 11.2 / 13.9 |
| strategy ceiling payoff | 44.1% | 47.7% (LP@T7), shell 78, no warning |

The lethalProxy gain (+3.4 to +3.6 per turn) is above the ±0.1 noise band measured yesterday: the goldfish model counts Took as a body and a token-rate engine where Retreat was a land-drop enchantment. The projection posted on the card (86 / 94, roles 91, curve 99, cohesion 50) reproduced exactly.

Hygiene tail: `card-metadata.json` +Peregrin Took; `refresh_card_pool.py` (Retreat now a candidate, Took removed); `compute_tokens.py` (Cat Beast token dropped, Took added as a Food producer); Combo Lab trio for stampede-acres (included 4 / near-miss 120 / total 282, unchanged; Tier C pairs 80 / triples 40 / cycles 30; Tier B 0 novel). The per-deck Spellbook sync advanced the shared corpus (2026-09-29T15:10 → 2026-09-30T13:11, 7,302 → 7,306 cards, 107,731 → 108,278 variants, API 7.1.2), so the fleet was re-emitted with `--offline --force`; no deck's `included[]` changed, so no Tier B rebuild elsewhere. `validate_deck_json.py` 4,791 references across 21 decks clean; `check_game_changers.py --offline` ts mirror ok (53), fleet recount 0; `validate_strategy_ceiling.py` stampede-acres ok (the grave-dividends shell-exceeds-payoff warning is pre-existing: its deck, metrics and simulation files did not change). Prose: Retreat removed from the Token Producers category; Took added to Card Draw, to the Draconic Visitor synergy, and to the roles list (card-draw / engine); `sources[]` decision record added. Web cache key v135 → v136.

Round counter after this apply: 0.
