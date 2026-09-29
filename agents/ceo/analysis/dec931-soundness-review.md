# DEC-931 — Soundness review of the proposal (revision 2)

**Outcome:** the review found 5 of the 10 lines unsound as written. Revision 2 keeps 4 lines unchanged (A, E, F, G), amends 3 cuts (C, H, I), moves 1 line to another deck (D), and withdraws 2 lines (B, J). The corrected list is at the end; the old verdict card is withdrawn and a new one replaces it. Every claim below was re-checked against Scryfall oracle text, `deck.json` prose, `simulation.json`, the sim scripts, `priv_data/edhrec/*.json`, and the closed-issue records.

**Root cause of the errors:** I named cuts before running the two checks my own checklist requires — the prior-decision files (DEC-929 withdrawn cuts, DEC-930 defers, DEC-436/DEC-574 board adds) and the incumbent-embedding grep (prose, synergies, win conditions, sim). Both checks are now run for every line.

## Line D — Verdant Kraken (the board's flag)

The board is right, and the record already said so. DEC-929 closed with: "Withdrawn cuts (board pushback, don't re-propose): Frontline Rush — only Rush + Staff of the Storyteller make bodies unconditionally at ≤2 MV in stampede." I re-proposed a withdrawn cut. The stampede-acres placement is off the table.

**Revised D: verdant-tide + Verdant Kraken / − Ohran Frostfang.**

- Cheat path: Eladamri's third ability ("{G}, {T}, tap two untapped creatures: reveal a card from your hand or the top card of your library; if it's a creature card, put it onto the battlefield") puts a 7-mana Kraken into play for one green and two taps. Eladamri also lets you cast it from the top of the library.
- Token payoffs already in the 99, all oracle-checked: Parallel Lives doubles every Kraken trigger (two 3/3s per upkeep, eight per turn cycle under the 4-player model); each token is a land entering, so Scute Swarm (copies itself at six or more lands — the tokens raise the land count) and Springheart Nantuko trigger four times per cycle; Craterhoof Behemoth counts every body; each token taps for {G} once summoning sickness passes, which matters in a deck the manabase audit puts at 34 lands against a 40.1 target. Garruk's Uprising, Guardian Project and The Great Henge each draw when the Kraken itself enters (power 6, nontoken).
- Not a payoff: Ezuri, Renegade Leader's overrun pumps Elves only; the Forest Tentacle tokens are not Elves.
- Cut: Ohran Frostfang ({3}{G}{G}: attacking creatures have deathtouch, draw on combat damage to a player). EDHREC inclusion for Eladamri 20.6%. It is the only nonland card in the 99 with zero references in prose, synergies, win conditions, or the sim, and it is not on the DEC-569 or DEC-565 reject lists. Its draw needs 1/1 Elves to connect before the alpha turn.
- Bracket: Kraken is not a Game Changer; verdant-tide stays at 1 GC (the DEC-369 cap) and at B3. Swap-round counter: 0 since e72efb5 (DEC-569), so this is round 1.
- Stampede-acres: Kraken deferred there. The synergy case (landfall for Felidar Retreat, Springheart Nantuko, Scute Swarm; tokens fuel Baylen) stands, but the deck's low-mana token floor is a board-set constraint, and I have no cut outside that floor that beats the incumbent. If the board wants a second copy for stampede later, the cut must come from a non-token slot and I will argue it separately.

## Line B — Vraska, Soul of Stone: withdrawn, deferred

Storm-Kiln Artist is not a loose slot. It is a piece of a named win condition ("Fury Storm + magecraft payoff", pieces Fury Storm + Storm-Kiln Artist), a `KEY_COMBOS` entry in `scripts/export_simulation_results.py`, and a member of three synergies and two more win-condition card lists.

The structural point I missed: Vraska's trigger reads "whenever you cast a noncreature spell". Copies are not cast (CR 707.10), so Fury Storm copies, Twinflame and Dualcaster Mage copies, Naru Meha's copies and Kitsa's copies never trigger her. Storm-Kiln Artist, Archmage Emeritus and Deekah have Magecraft ("cast or copy"), which is why the deck's kill lines run on them. Of the deck's 36 noncreature nonland spells, 26 are instants or sorceries; Vraska's edge is the other 10 (rocks, The One Ring, Mystic Remora, Whirlwind of Thought) plus her legendary-Wizard count for Gandalf's X.

There is no non-engine slot weaker than her without opening an accepted gap: Guardian of Faith is the protection suite (protection gap 2/4 accepted at DEC-472/541), Sakashima was a DEC-541 board add, Archmage of Runes a DEC-472 board add. Vraska, Soul of Stone is deferred for gandalf-party-guest and shield-doctrine. Swap-round counter correction: gandalf-party-guest is at 2 rounds since the DEC-547 baseline (DEC-570, DEC-687), so the next approved change fires Trigger-2; my earlier "probably already fired" was wrong.

## Line C — Emrakul, the Exigent Doom: cut amended

- My claim that It That Betrays "appears in the Annihilator Lockout text" was wrong. It has zero prose, synergy or win-condition references; it appears only in the sim's catalog example list, which is not a stale reference.
- EDHREC head-to-head for Zhulodok: It That Betrays 79.8%, Emrakul, the Exigent Doom 31.8% (three days before release), Blightsteel Colossus 21.8%. Cutting a 79.8% staple for a 31.8% card contradicts the community signal without a deck-specific reason.
- **Revised C: + Emrakul, the Exigent Doom / − Blightsteel Colossus.** Both are MV 12/10 double-cascade payloads. Blightsteel's highlight text gives its role as "double cascade with Zhulodok, 11/11 trample infect one-shot kill, tutored by Eye of Ugin". Emrakul is the same payload class two mana cheaper, refunds its mana (untap all lands on cast), has flying, and adds the hand-exile mode. Blightsteel's infect line kills one player and needs 11 unblocked damage or infinite mana; the deck's infinite-mana wins already close through Eye of Ugin into any titan. Blightsteel appears in `highlights` and `tokens` only, so the prose edit is one highlight entry. If the board prefers to keep the infect line, It That Betrays is the alternative cut, with the 79.8% caveat on record.
- Correction on the exile mode: the land's "{T}: Add {C}{C}" lasts until Emrakul is cast from exile, not for the rest of the game. Casting from exile still fires the untap-all-lands cast trigger; it does not get Zhulodok's cascades (those need a cast from hand).
- Swap-round counter: two DEC-467 commits since the DEC-394 baseline; C is round 3 and fires Trigger-2.

## Line H — broodfire land slot: cut and land both amended

- Warstorm Surge was a DEC-574 board-approved add one month ago and a named piece of the Hatch-and-Burn win condition. Cutting it is withdrawn.
- Ownership-blind ranking of the land: DEC-570 already deferred **Rootbound Crag** for broodfire "for a future manabase pass" — EDHREC 44.4% for Atla, owned (3 free copies), and it enters untapped whenever you control a Mountain or a Forest (14 basics plus Stomping Ground, Sacred Foundry, Temple Garden and Jetmir's Garden carry those types), so it is untapped from turn 2 in most games. Rockfall Vale (30.6%) is tapped on turns 1 and 2 by rule. Crag ranks above Vale for this deck on power and is free.
- **Revised H: + Rootbound Crag / − Utopia Sprawl.** Utopia Sprawl: 6.9% EDHREC (lowest noncreature spell in the 99 that is not removal or a DEC-574 add), one guide mention, present in the broodfire mana sim (model edit on apply). Trading a 1-mana ramp Aura for a land keeps mana development level, raises the land count 36 → 37 toward the 40.9 target, adds a G and an R source (Karsten G 21 → 22 against 20), and removes an Aura that dies with its Forest. Rockfall Vale for broodfire is deferred behind Crag.
- Line G (+ Identity Echo / − Rishkar's Expertise) stands: Rishkar's is 17.6% EDHREC and appears only in the Card Advantage category list. Broodfire is at 2 rounds since the DEC-544 build; G or H fires Trigger-2.

## Line I — Darklight Phoenix: cut amended

- Forsaken Miner is not a loose slot either. It is a piece of the "Crime Loop Drain" synergy (Forsaken Miner + Phyrexian Altar + Blood Artist, Commander Spellbook combo 2842-4050-5544, Soultrader variant 2842-5544-5670), named in two highlights, and a DEC-436 board-approved add.
- My "rarely commits crimes" claim was wrong. Altar of Dementia ("target player mills") and Priest of Forgotten Gods ("any number of target players") are repeatable crimes, and Assassin's Trophy, Deadly Rollick, Hagra Mauling and Bojuka Bog add one-shots. Miner's return is live most turns.
- **Revised I: + Darklight Phoenix / − Culling the Weak.** Culling the Weak ({B} instant: sacrifice a creature, add {B}{B}{B}{B}) is 11.1% EDHREC, appears in one highlight only, and is a one-shot ritual whose "sacrifice is upside" argument is already served by 14 sacrifice outlets. Phoenix supplies the fodder side of those outlets every turn instead. The Phoenix loop itself re-verified: Yawgmoth, Warren Soultrader and Priest of Forgotten Gods all say "another creature" or "two other creatures", so Phoenix is a legal sacrifice to each; Ashnod's Altar, Phyrexian Altar, Altar of Dementia and Greater Good take any creature.
- Gravecrawler checked and kept: its Zombie enablers are Gray Merchant, Mikaeus and Warren Soultrader (three), and it anchors the Gravecrawler Loop prose (24 references).
- Swap-round counter: 1 since the DEC-572 baseline (DEC-929); I is round 2.

## Line J — Haunted Ridge for hoard-and-bleed: withdrawn

DEC-930 (2026-09-28) deferred Haunted Ridge for hoard-and-bleed on merits: "no colour deficit". Nothing new since then; re-proposing it a day later was an error. Head-to-head for the record: Haunted Ridge 42.3%, Foreboding Ruins 36.6%, and the deck holds 13 Swamp-or-Mountain-typed cards among 38 lands (10 basics plus Blood Crypt, Smoldering Marsh, Turbulent Crater), not 10 as I wrote. Deferred; DEC-930 stands.

## Lines A, E, F, G — kept, with corrections

- **A (tidal-legion + The Theorist / − Quick Study)** stands. Corrections: the deck runs 13 counterspells plus two creature counter effects (Vodalian Hexcatcher, Lullmage Mentor). Quick Study is named in the guide prose ("Quick Study draws two at instant speed"), so one sentence changes on apply. The goldfish sim cannot model a draw that happens in opponents' draw steps, so `simulation.json` may show a small draw-consistency dip that is a modeling gap, not a deck change. Price note for the board's DEC-467 cost-consciousness: EUR 19.73, information only.
- **E (stampede + Rockfall Vale / − Jungle Shrine)** stands but is downgraded. Head-to-head favours the incumbent: Jungle Shrine 42.4% vs Rockfall Vale 20.9%. DEC-580 closed the last stampede manabase follow-up with "no change, Karsten all clear", and this line reopens it on tempo grounds only. Both lands are modeled by name in `scripts/mana_simulation_stampede_acres.py` (edit on apply). If the board takes one land line, take F.
- **F (stampede + Overgrown Farmland / − Path of Ancestry)** stands. Head-to-head is a tie (27.0% vs 27.0%). Path of Ancestry's scry fires only when its mana is spent on a creature sharing a type with Baylen (Rabbit Warrior); the 99 has no other Rabbit or Warrior creature, so the scry never fires. Any accepted stampede line is round 3 and fires Trigger-2.
- **G (broodfire + Identity Echo / − Rishkar's Expertise)** stands, see above.

## Corrections to the deferred and rejected notes

- **Jace, Reality Sculptor**: The Theorist contributes its whole loyalty to the 25-count, not "+1 per turn". With X = 5 Islands the totals run 15, 22, 29, so the 0 is legal on the fourth turn (not the fifth); with X = 7 they run 17, 26, so the third turn. Cast-to-win is about five turns at X = 5 and four at X = 7, not six. The reject stands on the unchanged facts: the loyalty sits on a separate 0-loyalty Jace token, two planeswalkers must survive three or four turn cycles, the 0 does not win by itself (each opponent draws their last card, then loses on the following draw), and Cephalid Coliseum finishes only one opponent.
- **Vraska, the Cutting Glare** land gate, exact hypergeometric on 35 lands in 99 with natural draws only: P(six or more lands) = 0.21 on turn 6 on the play, 0.28 on the draw, 0.36 on turn 7, 0.45 on turn 8. Sakura-Tribe Elder, Simulacrum Shaper and a fetched Dryad Arbor add roughly one land when drawn. Defer stands.
- **Omnipresence**: the X = 0 claim is the published ruling on Omniscience (2018-07-13): "If a spell has {X} in its mana cost, you must choose 0 as the value of X when casting it without paying its mana cost."
- **Roiling Canopy**: Fabled Passage finds basics only, so it is not the point. The point is that Nature's Lore, Three Visits and Skyshroud Claim look for Forest cards and cannot find a land typed "Land", and the Canopy does not count as one of the "five other Forests" its own trigger needs.
- **Storm-Kiln Artist** was described as strictly worse than Vraska. It is not, for the reason in Line B.

## Trigger-2 counters, corrected

| Deck | Rounds since baseline | This proposal |
|---|---|---|
| tidal-legion | 0 (DEC-468) | A = round 1 |
| verdant-tide | 0 (e72efb5, DEC-569) | D = round 1 |
| eternal-harvest | 1 (DEC-929, since DEC-572) | I = round 2 |
| titan-convergence | 2 (DEC-467 × 2, since DEC-394) | C = round 3, fires |
| stampede-acres | 2 (DEC-685, DEC-929, since DEC-581) | E or F = round 3, fires |
| broodfire-hatchery | 2 (DEC-570, DEC-574, since DEC-544) | G or H = round 3, fires |
| gandalf-party-guest | 2 (DEC-570, DEC-687, since DEC-547) | no line now |

## Revised proposal (verdict card v2)

- A. tidal-legion: + The Theorist, Jace Beleren / − Quick Study
- C. titan-convergence: + Emrakul, the Exigent Doom / − Blightsteel Colossus (alternative cut: It That Betrays)
- D. verdant-tide: + Verdant Kraken / − Ohran Frostfang
- E. stampede-acres: + Rockfall Vale / − Jungle Shrine (low priority; take F first)
- F. stampede-acres: + Overgrown Farmland / − Path of Ancestry
- G. broodfire-hatchery: + Identity Echo / − Rishkar's Expertise
- H. broodfire-hatchery: + Rootbound Crag (owned) / − Utopia Sprawl
- I. eternal-harvest: + Darklight Phoenix / − Culling the Weak

Withdrawn: B (Vraska, Soul of Stone → deferred), J (Haunted Ridge → DEC-930 defer stands), and the stampede-acres Kraken placement (→ deferred). Rockfall Vale for broodfire is deferred behind Rootbound Crag. All other defers and rejects from the first report stand with the corrections above.
