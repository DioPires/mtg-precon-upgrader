# Star Trek grade review log (DEC-1218 R1)

**Check of 2 November 2026: our grades against MTG Arena Zone's Limited set review.** I re-read the oracle text of all 49 cards that differ by 2 or more after the scale offset. I changed 20 grades and kept 29, each with the reason below. Draftsim's set review and the Limited Resources episode were not out at 14:00Z (Draftsim's set list: "Set Review (coming soon!)"; lrcast.com's latest episode, 877, is a Q&A of 30 October). When Draftsim's review comes out by the evening of 4 November, I run the same check against it. The check of 3 November against Draftsim's ratings (its pick order) is at the end of this file.

## Source

- **Review:** MTG Arena Zone, "Star Trek (TRK) Limited Set Review" by J2SJosh, seven pages (white, blue, black, red, green, multicolor, artifacts and lands). They were published from 30 October to 2 November 2026 and last changed on 2 November at about 09:40Z. I saved them at 14:1xZ.
- **Ratings:** 0 to 5 in half points, for Draft. Scale: 2.0 is filler for the last deck slots, 2.5 a solid playable, 3.0 a good playable, 4.0 a great rare or premium removal, 4.5 a bomb. `parse_mtgaz.py` read 281 ratings into `mtgaz_grades.json`. Three group ratings matched no card: Planets, Shock lands and Surveil lands. Every non-land card has a rating.
- **Mapping:** twice the rating plus the mean offset, +0.02 on the 274 shared non-land cards. The offset changes by rarity: before the check, the review graded rares 0.98 and mythics 0.96 above our scale, and commons 0.42 below it.
- **Files:** `grades_src_precheck.py` keeps our grades before this check, and `grades_src_blind.py` keeps the blind grades. `compare_mtgaz.py` prints the comparison.

## Why this source, and its limits

R1 names Draftsim and Limited Resources. Neither was out, and this review was. I scored the same reviewer's Reality Fracture review in the back-test, on the 103 commons and uncommons of `retro.py` section 1 (`../fra/backtest/score_mtgaz.py`). That review was published on 20 and 21 September 2026 and last changed on 26 September, before the Arena release on 29 September, so it saw no Arena data.

| Grades (Reality Fracture) | Rank correlation with GIH WR | 95% interval | Within commons | Within uncommons |
|---|---:|---:|---:|---:|
| Ours, blind (v1) | 0.11 | -0.08 to 0.30 | 0.25 | -0.03 |
| Ours, final (v3) | 0.14 | -0.06 to 0.32 | 0.20 | -0.02 |
| Draftsim | 0.33 | 0.14 to 0.50 | 0.21 | 0.08 |
| MTG Arena Zone | 0.38 | 0.20 to 0.55 | 0.27 | 0.18 |

- MTG Arena Zone against our v3: z = 3.11, so its lead is unlikely to be noise. Against Draftsim: z = 0.76, so the two are level.
- **Limits:** the back-test covers one set, and Premier Draft commons and uncommons only. It holds no rare or mythic data, so it cannot say whether the review's higher rare grades are right. The review grades for Draft; our grades are for Sealed. Where the difference comes from the format (5-drops, 7-drops, evasive bodies, removal), I kept our grade.

## Result

- **Rank correlation between our grades and the review's:** 0.61 before the check, 0.69 after. By rarity after: commons 0.43, uncommons 0.57, rares 0.79, mythics 0.78.
- **Gaps of 2 or more:** 49 before, 38 after. Every one has a reason below.
- **Direction:** I raised 12 cards and lowered 8. Six raises are card-advantage engines that I under-read: Scotty, Captain Pike, Collation Trimatrix, Tasha Yar, Dr. McCoy and The Inner Light. That is the same error as on Reality Fracture. Three cards gained ✚ (Scotty, Captain Pike, Collation Trimatrix): 26 cards now have ✚, against 23.
- **Rarity check (R2):** our mean uncommon grade is now 0.61 above our mean common grade (it was 0.65). The review's own gap on the same cards is 0.51 on our scale. So an independent grader also puts Star Trek's uncommons only about half a grade above its commons. I do not force the 1.0 floor.
- **Colours:** the review also rates blue (mean 2.20) and white (2.23) as the weakest colours and black (2.54) as the strongest. Our mono-colour cards graded 6+ are now W 10, U 6, B 16, R 10, G 14 (before: 10, 5, 17, 10, 11).
- **Bombs:** no card crossed 8 in either direction; 9 cards are graded 8 or more.

## Decisions

The table lists the grade before the check, the review's rating (with its mapped value), and the grade after.

| Card | Rarity | Before | MTGAZ (x2 + offset) | After | Decision and reason |
|---|---|---:|---:|---:|---|
| Replicator | R | 3 | 4.5/5 (9.0) | 5 | Raised. I graded only the Food copy. A pool holds about 5 creature-token makers at common and uncommon (about 2 in your two colours), plus Clues and Treasures; each turn {2} copies the best one, and the copy of a temporary Klingon (D-7 Battle Cruiser) stays. Below the review: it needs a token and does nothing alone. |
| Hit It! | R | 3 | 3.5/5 (7.0) | 4.5 | Raised. I missed the ramp: the top five hold a land about 95% of the time (17 lands in 40 cards). Team haste is the bonus. Below the review: it draws no card, and it is gold. |
| General Chang, Cold Warrior | R | 3.5 | 3.5/5 (7.0) | 3.5 | Kept. A 1-mana 1/2 needs both fodder and Klingons; outside BR the counters go on Chang alone. Sealed games are slow, so a 1-drop body matters less than in Draft. |
| MACO Strike Team | R | 3.5 | 3.5/5 (7.0) | 3.5 | Kept. A Sealed opponent holds about 3 to 5 spells that target your creatures, so the 1/1 comes once or twice a game; a 1-mana 2/1 falls behind by turn 4. |
| Salt Vampire | R | 4.5 | 4.0/5 (8.0) | 5 | Raised half a grade. I under-weighted the swap: on turn 2 their best of about 6 cards (often a bomb or removal) becomes a random card. The 2/2 lifelink body keeps it below the review's grade. |
| Scotty, Miracle Worker | M | 4.5 | 4.0/5 (8.0) | 6.5 | Raised and tagged ✚. I missed the engine: each instant and sorcery in your graveyard can be cast again in your main phase, and cards played from a graveyard count as extra cards (playbook step 3). The cost is a bounce of another creature, which can reuse an enters ability. |
| Seven of Nine, Unassimilated | M | 4.5 | 4.0/5 (8.0) | 5 | Raised half a grade. The loot needs no tap and no mana, so the 0/4 still blocks. Not ✚: it discards unless you control 5 land names. |
| Year of Hell | R | 3.5 | 0.0/5 (0.0) | 1.5 | Lowered. I under-counted: they draw as many cards as you, you spent a card, and you take 6 damage too. |
| Engineered Explosives | R | 3 | 3.0/5 (6.0) | 4 | Raised. You choose the mana value after you see the board, and X=0 kills every token for {2}; this set has many token makers. It is symmetric, so not higher. |
| Captain Pike, Fullness of Time | R | 5 | 4.0/5 (8.0) | 6 | Raised and tagged ✚. I missed the tag: lands played from the top are cards played from your library (playbook step 3). |
| Georgiou, Terran Emperor | M | 7 | 5.0/5 (10.0) | 7 | Kept. She costs 3 life a turn, and if she leaves while you are at 0 or less, you lose. Removal that does not deal damage answers her (He's Dead, Jim; 70,000 Light-Years from Home; Resistance Is Futile). |
| Jadzia Dax, Living Legacy | M | 5 | 4.0/5 (8.0) | 6 | Raised. I under-weighted the growth: she adds {G}, then {G}{G}, then {G}{G}{G}, and is a 3/4 by her fourth upkeep. |
| Mirror Universe Intrusion | R | 6 | 4.5/5 (9.0) | 6 | Kept. It copies only their creature, so it is weak against a poor board, and it removes nothing. |
| Overflow Submatrix | R | 6 | 4.5/5 (9.0) | 6 | Kept; ✚ already gives +1. A black deck outside WB holds about 3 or 4 artifact creatures, so early in the game the recast often has no target. |
| The Inner Light | R | 5 | 4.0/5 (8.0) | 5.5 | Raised half a grade. Chapter II can draw cards off any creature's combat damage, a second card beyond the reanimation. It is gold and needs a green or white creature in the graveyard. |
| Bat'leth | U | 6 | 1.5/5 (3.0) | 5 | Lowered. I graded it near Eject the Warp Core (6), but it is sorcery speed, costs 3, and kills only toughness 2 or less (46%). The Equipment keeps it playable. |
| V'Ger, the Intruder | U | 7 | 2.0/5 (4.0) | 6 | Lowered. It costs 7: with 17 lands you hold 7 lands on turn 7 less than half the time. It keeps ✚. Above the review: Sealed games reach 7 mana more often than Draft games. |
| Vulcan Mind-Meld | U | 4 | 0.5/5 (1.0) | 2.5 | Lowered. I counted your two cards, not the card they get: you end at card parity with them, and the cards are random. |
| Collation Trimatrix | R | 3.5 | 3.0/5 (6.0) | 4.5 | Raised and tagged ✚. I missed that it can tap itself (the cost has no {T}), so it needs two other artifact creatures; a WB pool holds about 8. Without them it is a 1/1 for 1. |
| Tasha Yar, Out of Time | R | 4.5 | 3.5/5 (7.0) | 5.5 | Raised. I missed that the graveyard copy has the dies trigger too, so she gives two extra cards over a game. Not ✚: two cards, both tied to a death. |
| Dr. Leonard "Bones" McCoy | R | 5.5 | 4.0/5 (8.0) | 6 | Raised half a grade. The return mode is a 2-for-1 on a flash 3-drop; I had weighted the save mode. |
| Encounter the Unknown | R | 5.5 | 4.0/5 (8.0) | 5.5 | Kept. The sweeper also hits your creatures, and impulse two is a one-time draw. |
| 70,000 Light-Years from Home | U | 7.5 | 2.5/5 (5.0) | 7.5 | Kept. Exile of any creature for 2 is premium in Sealed, where removal is short; the land goes to their hand, not the battlefield. |
| Cha'DIch Investigator | C | 5.5 | 1.5/5 (3.0) | 5.5 | Kept. Sealed decks play more 5-drops than Draft decks; 6 power over two bodies is the best common rate at 5. |
| Cloak and Phaser | U | 5.5 | 1.5/5 (3.0) | 5 | Lowered half a grade. With 3 land names it costs 6, and 7 or more early; I had assumed about 5. |
| Conquest Mission | U | 4.5 | 1.0/5 (2.0) | 4.5 | Kept; re-read this morning. A WB pool holds about 14 nontoken artifacts (W, B and colourless), so it makes about 4 tokens a game there. It does nothing the turn it lands and little outside WB. |
| DOT-7 Repair Squad | C | 5.5 | 1.5/5 (3.0) | 5.5 | Kept. A 3/3 flyer for 4 wins Sealed games; the review grades for Draft. |
| Dathon and Picard at El-Adrel | C | 4.5 | 1.0/5 (2.0) | 4.5 | Kept. The sacrifice mode hits Spacecraft and artifact creatures, which are common here; when they hold only one, it is removal. |
| Exploratory Mission | U | 5.5 | 1.5/5 (3.0) | 5 | Lowered half a grade. You must play the card the turn the land enters, so it competes with your hand for that turn's mana. It keeps ✚. |
| Photosynthetic Physician | C | 5.5 | 1.5/5 (3.0) | 5.5 | Kept. Same reason as Cha'DIch Investigator: Sealed decks need 5-drops. |
| Pure Energy | C | 4.5 | 1.0/5 (2.0) | 4 | Lowered half a grade. The second cast costs 3 and a bounce of your own creature, a tempo loss in the attacking deck that wants it. |
| Rules of Acquisition | U | 6.5 | 2.0/5 (4.0) | 6 | Lowered half a grade. They draw three when you steal. The other mode (give them a token, draw three) is the floor. |
| Set Phasers to . . . | C | 5.5 | 1.5/5 (3.0) | 5.5 | Kept. A 1-mana instant that kills 75% of attackers; Sealed decks are short of removal. |
| Andromedan Automatons | C | 3 | 2.5/5 (5.0) | 3 | Kept. A Sealed pool rarely holds two copies, so the tutor finds nothing. |
| Antagonist Incorporator | R | 5 | 3.5/5 (7.0) | 5 | Kept; re-read this morning. Each token needs combat damage to a player and {1}. |
| Lieutenant Commander Data | M | 5 | 3.5/5 (7.0) | 5 | Kept. Both players cast about 8 noncreature spells a game, so Data gains about a counter a turn cycle; each card costs {1} and three counters. |
| Nyota Uhura, Communications | R | 5 | 3.5/5 (7.0) | 5 | Kept; ✚ already. The draws depend on the opponent's curve. |
| Open Communications | C | 3 | 2.5/5 (5.0) | 3 | Kept. A cantrip; the beam-me-up recast costs 3 and a bounce. |
| Spock, Always Your Friend | U | 5 | 3.5/5 (7.0) | 5 | Kept. With 9 noncreature spells in 40 cards, the top four hold one about 66% of the time; the grade already counted that. |
| Tricorder | C | 3 | 2.5/5 (5.0) | 3 | Kept. +1/+1 for 2 mana in total; surveil is card selection, not cards. |
| Captain James T. Kirk | M | 6 | 4.0/5 (8.0) | 6 | Kept; re-read this morning. A 2/2 rarely attacks safely after turn 4, so the attack trigger comes once or twice. |
| Captain Jonathan Archer | R | 6 | 4.0/5 (8.0) | 6 | Kept. Already graded as a 3/3 and a 1/1 for 3; the pump taps Archer. |
| Captain Kathryn Janeway | M | 6 | 4.0/5 (8.0) | 6 | Kept; ✚ already. A 2/3 for 4 dies to most removal before the explores pay off. |
| D-7 Battle Cruiser | R | 6 | 4.0/5 (8.0) | 6 | Kept. Station 3 costs a creature's tap, the token is gone each end step, and it flies only at 8. |
| Elim Garak, Simple Tailor | R | 6 | 4.0/5 (8.0) | 6 | Kept. A deck holds about 4 modal cards, so the drain is 2 to 8 life a game: life, not cards or board. |
| Gowron, Eager for Battle | R | 6 | 4.0/5 (8.0) | 6 | Kept. A 3/3 for 4 often dies in its first trade before it grows; the draw needs Klingons. |
| Holo-Engineer | R | 7 | 4.5/5 (9.0) | 7 | Kept. Two 3/3s for 4 is the floor; the replacement needs other token makers, about 2 in your two colours. |
| Nog, Ambitious Cadet | R | 6 | 4.0/5 (8.0) | 6 | Kept. Already graded as a 3/4 menace surveil engine for 3 mana in total. |
| U.S.S. Enterprise-D, Galaxy-Class | R | 7 | 4.5/5 (9.0) | 7 | Kept; ✚ already. The card comes only on a turn you station it, at sorcery speed, by tapping a creature. |

# Check of 3 November 2026: Draftsim's pick-order ratings

**I re-read the oracle text of all 18 cards that differ from Draftsim's ratings by 2 or more after the scale offset. I changed 11 grades and kept 7.** Draftsim's set review was still "coming soon" on its set list at 10:40Z, and lrcast.com's latest episode was still 877. The board pointed me to Draftsim's pick order on 3 November; I had seen the page on 2 November and called it not comparable without a test.

## Source

- **Page:** https://draftsim.com/TRK-pick-order/, a JavaScript page. Its app bundle (`index-Ctt7WR6J.js`, saved on 3 November at about 10:35Z, not committed) holds a table of ratings for every Star Trek card. `parse_draftsim_pick.py` read 311 ratings (306 cards and the 5 basics) into `draftsim_pick_ratings.json`. The 30 Stardates rows are left out.
- **Ratings:** 0 to 5, one decimal, for Draft. Arena opens on 10 November, so these ratings saw no Star Trek play data.
- **Mapping:** twice the rating plus the mean offset, -0.60 on the 274 shared non-land cards, as for MTG Arena Zone.
- **Files:** `grades_src_pre_draftsim.py` keeps our grades before this check. `compare_draftsim.py` prints the comparison.

## Why this source counts as Draftsim's review

`../fra/backtest/score_draftsim_pick.py` reads two copies of Draftsim's Reality Fracture pick order: one from the Wayback Machine (25 September, before the Arena release on 29 September) and today's.

| Grades (Reality Fracture), 103 commons and uncommons | Rank correlation with GIH WR | 95% interval |
|---|---:|---:|
| Ours, final (v3) | 0.14 | -0.06 to 0.32 |
| Draftsim's set review | 0.33 | 0.14 to 0.50 |
| MTG Arena Zone | 0.38 | 0.20 to 0.55 |
| Draftsim's pick order, 25 September | 0.32 | 0.13 to 0.49 |
| Draftsim's pick order, 3 November | 0.69 | 0.56 to 0.80 |

- Before the release, the pick order ranked the cards as the set review did: rank correlation 0.99 on 265 cards. So it is the review's ratings on a 0 to 5 scale.
- Today's copy scores 0.69, near the noise ceiling of about 0.78, because Draftsim updated it with Arena data. Only a pre-release copy is a fair test. The Star Trek copy is pre-release.
- **Limits:** the same as for MTG Arena Zone. One set, Draft commons and uncommons only, no rare data.

## Result

- **Rank correlation with Draftsim:** 0.61 before the check, 0.65 after. By rarity after: commons 0.47, uncommons 0.37, rares 0.79, mythics 0.74. Draftsim and MTG Arena Zone correlate 0.66 with each other; our grades correlate 0.70 with MTG Arena Zone after this check.
- **Gaps of 2 or more:** 18 before, 9 after: the six kept cards above 2, Chang and Sarek after their raises, and Emergency Medical Hologram, which the moved offset put at exactly 2.0. Resistance Is Futile, kept, now sits at 1.98. MTG Arena Zone gaps stay at 38.
- **Rarity check (R2):** our uncommons sit 0.58 above our commons (0.61 before). Draftsim's gap on the same cards is 0.23 on our scale, and MTG Arena Zone's is 0.51. Both reviewers put Star Trek's uncommons closer to its commons than our 1.0 floor asks. I do not force the floor.
- **Bombs:** Georgiou crosses 8, so 10 cards are graded 8 or more. Sarek gains ✚, so 27 cards have it.
- **Colours:** mono-colour cards graded 6+ are W 10, U 5, B 16, R 10, G 14. Blue loses Rules of Acquisition.

## Removal: the largest open disagreement

Both reviewers grade four Star Trek removal spells at 2.5 to 3.0 of 5; we grade them 7 to 7.5. The back-test cannot say who is right. On Reality Fracture, removal (24 cards) played about as each source graded it, at equal grade and rarity:

| Source | Removal's mean grade percentile | GIH residual at equal grade | 95% interval |
|---|---:|---:|---:|
| Ours (v3) | 76 | -0.24 | -0.84 to +0.34 |
| Draftsim's review | 61 | -0.41 | -1.22 to +0.43 |
| MTG Arena Zone | 64 | -0.56 | -1.36 to +0.26 |

Every interval crosses zero, so the data supports neither our grades nor the reviewers'. I keep ours. With the reviewers' grades, the four cards would fall to about 5, under the procedure's 6+ count; the back-test gives no reason to make that change.

## Decisions

The table lists the grade before the check, Draftsim's rating (with its mapped value), MTG Arena Zone's mapped value, and the grade after.

| Card | Rarity | Before | Draftsim (x2 + offset) | MTGAZ | After | Decision and reason |
|---|---|---:|---:|---:|---:|---|
| Sarek, Federation Ambassador | R | 2.5 | 3.8/5 (7.0) | 3.0 | 5 ✚ | Raised and tagged ✚. I misjudged how easy five creature types are. Sarek has two (Vulcan, Advisor); Star Trek's non-Borg creatures average 1.97 types. With two other random common or uncommon creatures, 90% of boards reach five types, so he draws a card in each of your combats. Below Draftsim: he costs three colours, so he needs a splash under the N1 rule. |
| General Chang, Cold Warrior | R | 3.5 | 4.0/5 (7.4) | 7.0 | 4.5 | Raised. Both reviewers grade him about 7. Chang is a Klingon himself, so each sacrifice grows him at least, and he turns a chump block or a creature that removal targets into counters. Below the reviewers: Star Trek has 10 Klingon creatures at common and uncommon, 9 of them black or red, and a BR pool holds about 3. Outside BR the counters go mostly on Chang. |
| Collation Trimatrix | R | 4.5 | 3.8/5 (7.0) | 6.0 | 5.5 | Raised. The cost taps creatures but has no {T}, so you can pay it at the opponent's end step, after blocks; your creatures untap in your untap step. A card a turn for 1 life, with no combat cost, once you hold three artifact creatures. A WB pool holds about 7 or 8 artifact creatures (white, black, WB and colourless), plus cards that make artifact tokens. |
| Georgiou, Terran Emperor | M | 7 | 5.0/5 (9.4) | 10.0 | 8 | Raised to bomb. Both reviewers give her their top grade. She draws a card at each of your end steps, and at 0 life or less she makes ten 1/1s each end step. The risk I weighted, removal while you are at 0 or less, needs a spell that answers a 4/6, and it starts only when her drain and their attacks take you to 0. |
| Primary Unimatrix Adjunct | R | 6 | 4.4/5 (8.2) | 7.0 | 7 | Raised. Alone it is a 2/3 double striker for 4. A white pool holds about 4 artifact creatures (white and colourless), and each deals double damage. |
| Death Is Irrelevant | M | 6.5 | 4.7/5 (8.8) | 7.0 | 7 | Raised half a grade. The first creature comes back at the end of the turn you cast it, from either graveyard, and every creature it returns is indestructible. The cost of 8 keeps it below the reviewers. |
| Quark, Humble Proprietor | M | 2 | 2.5/5 (4.4) | 3.0 | 3 | Raised, and the note was wrong. The Treasures make no mana while Quark is on the battlefield, but they stay: two per turn cycle (each upkeep). When Quark leaves, for example after he chump blocks, you can use them all. |
| Rules of Acquisition | U | 6 | 2.0/5 (3.4) | 4.0 | 5 | Lowered. Both reviewers grade it about 4. The steal gives them three cards, and the floor is a 5-mana sorcery that draws three and gives them a permanent. |
| Type-2 Phaser | U | 5 | 1.5/5 (2.4) | 3.0 | 4 | Lowered. The stun removes one blocker for about two turns; after that it is +3/+0 for equip 3. |
| Khan, Despot by Design | U | 6.5 | 2.5/5 (4.4) | 5.0 | 6 | Lowered half a grade. The ping kills only 1-toughness creatures and tokens; the 5/4 trample body is most of the value. |
| Federation Resupply | R | 3 | 0.7/5 (0.8) | 2.0 | 2.5 | Lowered half a grade, and the note now says when to play it: only with an Aura, Equipment or Spacecraft graded 6+. Then it is a 2-mana copy of that card, and beam me up finds a second. |
| Kobayashi Maru Scenario | M | 0 | 2.4/5 (4.2) | 1.0 | 0 | Kept. On your fourth upkeep the only mode left is "You lose the game". Three cards can remove it first: Ghost of Illyria (the flicker makes it a new object), Targ Wrangler and Rules of Acquisition. A Sealed deck rarely holds one of them. MTG Arena Zone also grades it near 0. |
| Deep Space 9 | M | 4 | 4.0/5 (7.4) | 3.0 | 4 | Kept. It costs 9: with 17 lands in 40 cards, you hold 9 lands by turn 12 on the play 29% of the time. MTG Arena Zone agrees. |
| 70,000 Light-Years from Home | U | 7.5 | 2.5/5 (4.4) | 5.0 | 7.5 | Kept. Exile of any creature for 2; the land goes to their hand. See the removal section above. |
| Malfunctioning Holodeck | C | 7.5 | 2.8/5 (5.0) | 6.0 | 7.5 | Kept. Exile of any nonland permanent for 3, and ward 2 protects it. See the removal section. |
| Khaaaaaaaaaaaannn! | U | 7.5 | 2.9/5 (5.2) | 6.0 | 7.5 | Kept. An instant that exiles a creature of toughness 4 or less (88% of creatures) for 3 mana, and scales. See the removal section. |
| Resistance Is Futile | U | 7 | 2.8/5 (5.0) | 5.0 | 7 | Kept. A 2-mana kill of a nonartifact creature; 34 of the set's 166 creature cards are artifacts, and Spacecraft are artifacts too. See the removal section. |
| Mugato | U | 7 | 2.5/5 (4.4) | 5.0 | 7 | Kept. A 5-mana 6/6 with deathtouch, reach and vigilance blocks every creature, fliers included, and attacks without leaving you open. I found nothing in the oracle text that the grade missed. |
| Emergency Medical Hologram | C | 2 | 2.3/5 (4.0) | 3.0 | 2 | Kept. Not among the 18: the moved offset put it at 2.0 after the changes. A 1-mana 0/1; on itself it is a 1/2. |
