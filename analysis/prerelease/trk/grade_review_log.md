# Star Trek grade review log (DEC-1218 R1)

**Check of 2 November 2026: our grades against MTG Arena Zone's Limited set review.** I re-read the oracle text of all 49 cards that differ by 2 or more after the scale offset. I changed 20 grades and kept 29, each with the reason below. Draftsim's set review and the Limited Resources episode were not out at 14:00Z (Draftsim's set list: "Set Review (coming soon!)"; lrcast.com's latest episode, 877, is a Q&A of 30 October). When Draftsim's review comes out by the evening of 4 November, I run the same check against it. The two checks of 3 November, against Draftsim's pick order and against Draftsim's set review, follow this one.

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

**Correction (3 November, after this check):** the set review had been out since 2 November at 17:00Z, and on Star Trek the pick order does not hold the review's ratings (rank correlation 0.68). The next section checks the grades against the review itself.

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

# Check of 3 November 2026: Draftsim's set review

**I re-read the oracle text of all 62 cards that differ from Draftsim's set review by 2 or more after the scale offset. I changed 34 grades (20 up, 14 down) and kept 28.** The board pointed me to the review at 10:40Z. It was published on 2 November at 17:00Z (Andrew Quinn); Draftsim's set list still read "coming soon" on 3 November, so my check of the set list missed it.

## Source

- **Page:** https://draftsim.com/mtg-trk-limited-set-review/, saved on 3 November at about 11:00Z (not committed). `parse_draftsim_review.py` read 276 ratings into `draftsim_review_ratings.json`: every non-land card, plus Starfleet Academy and Unexplored Territory. The review rates the other lands by cycle: planet duals 4, anomaly lands 3, shock lands 4, the five rare surveil lands 5.
- **Ratings:** 0 to 10, whole numbers, for Draft. Commons mostly sit at 2 to 4 on its scale ("the average Limited card").
- **Mapping:** the rating as written plus the mean offset, +0.37 on the 274 shared non-land cards before the check.
- **Files:** `grades_src_pre_review.py` keeps our grades before this check. `compare_draftsim.py --review` prints the comparison, with the pick order beside each gap.

## The review is not the pick order on this set

- On Reality Fracture, the pick order from before the Arena release ranked the cards as the review did (0.99). On Star Trek the pick order of 3 November and the review rank the 276 cards at 0.68, and the commons at 0.41. Only 19 cards have a review rating equal to twice the pick-order rating.
- So the morning's check against the pick order (above) was a check against a different source, with no back-test of its own. The back-test figure of 0.33 belongs to the review.
- The review does not contradict the morning's changes: none of the 11 cards that changed then differs from the review by 2 or more now. Primary Unimatrix Adjunct (ours 7, review 5.4 mapped) is the widest at 1.6.

## Result

- **Rank correlation with Draftsim's review:** 0.61 before the check, 0.69 after. By rarity after: commons 0.36, uncommons 0.56, rares 0.78, mythics 0.83. With MTG Arena Zone: 0.70 before, 0.76 after. With the pick order: 0.65 before, 0.68 after.
- **Gaps of 2 or more:** 62 before, 40 after: the 28 kept cards, and 12 changed cards that moved toward the review but not all the way (for example Chang, Sisko and Overflow Submatrix).
- **Rarity check (R2):** our uncommons sit 0.62 above our commons (0.58 before). The review's gap is 1.22 on its own scale. Its spread is wider (standard deviation 2.16 against our 1.42), so in standard deviations the two are 0.57 and 0.44. The review supports the 1.0 floor more than the other two sources did. I raised every uncommon the review flagged where MTG Arena Zone agreed. I do not force the floor with raises that I cannot give a reason for. The sheet's intro gives the three gaps.
- **Bombs:** still 10. Holo-Engineer joins (8); Gul Dukat leaves (7). **✚:** 28 (Lieutenant Commander Data joins).
- **Colours:** mono-colour cards graded 6+ are W 11, U 7, B 17, R 10, G 14 (before: 10, 5, 16, 10, 14).
- **Archetype lists:** six grades changed in the look-for lines. Pure Energy (now 3) leaves WG's list.

## How I decided

- **Change** when the review and MTG Arena Zone sit on the same side of our grade, and the oracle text gives a reason that our note missed.
- **Keep** when the two reviews bracket our grade, or MTG Arena Zone is within about half a grade of ours.
- **Removal rule:** on Reality Fracture no source misjudged removal at equal grade (see the removal section above), so I kept the five removal spells among the 62: Impossible Choice, Genesis Effect, Marooned, Plasma Cascade and Command Decision.
- **Removal, the morning's open disagreement:** the review grades 70,000 Light-Years from Home, Malfunctioning Holodeck and Khaaaaaaaaaaaannn! 6/10 and Resistance Is Futile 7/10 (6.4 and 7.4 mapped), against our 7 to 7.5. The pick order's 2.5 to 3 of 5 was not the review's view. None of the four is among the 62.

## Decisions

The table lists the grade before the check, the review's rating (with its mapped value), MTG Arena Zone's mapped value, and the grade after.

| Card | Rarity | Before | Draftsim review (+ offset) | MTGAZ | After | Decision and reason |
|---|---|---:|---:|---:|---:|---|
| Gul Dukat, Colonial Prefect | M | 8 | 3/10 (3.4) | 7.1 | 7 | Lowered; no longer a bomb. It costs 7 and does nothing on the turn it enters: the doubling needs damage first. It stays a 6/6 menace that ends the game in two hits. MTG Arena Zone also grades it 7. |
| Support Mission | U | 4.5 | 0/10 (0.4) | 6.1 | 4.5 | Kept. The two reviews bracket our grade (0 and 6.1). Each later creature gets a +1/+1 counter, about ten counters over a Sealed game, but it does nothing on turn 3. |
| Captain Benjamin Sisko | R | 4.5 | 8/10 (8.4) | 5.1 | 5 | Raised half a grade, to MTG Arena Zone's level. A two-colour deck holds 2 to 7 modal cards, 4.3 on average, so expect two or three tokens a game, not Draftsim's build-around. |
| General Chang, Cold Warrior | R | 4.5 | 8/10 (8.4) | 7.1 | 5.5 | Raised. All three Draftsim and MTG Arena Zone grades sit at 7 or more. A 1-mana sacrifice outlet that grows Chang himself each time. Below them: a BR deck holds about 3 other Klingons (creatures and token makers). |
| Deep Space Scan | R | 5 | 1/10 (1.4) | 3.1 | 3.5 | Lowered. Two basic names plus about one non-basic land make it draw three for 6 mana at sorcery speed. Both reviews grade it 3 or less. |
| Impossible Choice | U | 6 | 2/10 (2.4) | 5.1 | 6 | Kept (removal rule). Both modes are playable: an instant kill of any creature, the answer to a bomb, or draw two at instant speed. The two 1/1s are a real price against a small creature. |
| Rules of Acquisition | U | 5 | 1/10 (1.4) | 4.1 | 4 | Lowered again. A steal that gives them three cards is a fair trade only against a bomb. MTG Arena Zone 4.1. |
| Shuttle Ace | C | 5 | 1/10 (1.4) | 3.1 | 4.5 | Lowered half a grade. It flies only on your turn, so it never blocks a flier. Both reviews grade it 3 or less. |
| Test of Conviction | U | 5 | 1/10 (1.4) | 3.1 | 4.5 | Lowered half a grade. The counters mode needs three creatures to beat a 2-mana creature, and the draw mode gives them a card too. |
| Antagonist Incorporator | R | 5 | 8/10 (8.4) | 7.1 | 6 | Raised back to 6, without ✚ (tokens are not cards). Both reviews grade it 7 or more. A 2/3 for 2 is a good body, and a WB deck holds about 6 artifact creatures that each add a 1/1 when they connect. |
| Overflow Submatrix | R | 6 | 9/10 (9.4) | 9.1 | 7 ✚ | Raised. Both reviews grade it 9. It recasts an artifact creature from your graveyard each turn: a black deck holds 3 to 6 artifact creatures, so it trades 1-for-1 removal into card advantage. |
| The Destruction of Praxis | R | 6 | 9/10 (9.4) | 5.1 | 6 | Kept. The reviews bracket our grade (9.4 and 5.1). With the usual 3 land names it is a symmetrical -3/-3 sweeper (75% of creatures) for 5. |
| The City on the Edge of Forever | R | 4 | 7/10 (7.4) | 4.1 | 4 | Kept. MTG Arena Zone agrees (4.1). Everything phases out, yours too, until chapter III or until they kill the 0/1. |
| Cetacean Ops | C | 4.5 | 1/10 (1.4) | 3.1 | 4 | Lowered half a grade. A 4-mana 3/3 is below the rate; it grows only with your noncreature spells. |
| Culber and Stamets, Star-Crossed | U | 5.5 | 2/10 (2.4) | 4.1 | 5.5 | Kept. A 4/5 for 4, or a counter on a better creature; half a grade above Dominion Assault Force (a 4/4 vigilance, now 5). |
| DOT-7 Repair Squad | C | 5.5 | 2/10 (2.4) | 3.1 | 5.5 | Kept (also kept on 2 November). A 4-mana 3/3 flier is a top common body in Sealed, and the untap helps station. |
| Dathon and Picard at El-Adrel | C | 4.5 | 1/10 (1.4) | 2.1 | 4 | Lowered half a grade. A 3-mana trick; the sacrifice mode hits only when they have few nontoken artifacts or enchantments. MTG Arena Zone 2.1. |
| Dominion Assault Force | C | 5.5 | 2/10 (2.4) | 4.1 | 5 | Lowered half a grade. A 4/4 vigilance for 4 with a small bonus; both reviews grade it 4.1 or less. |
| Genesis Effect | C | 6.5 | 3/10 (3.4) | 5.1 | 6.5 | Kept (removal rule). A 5-mana instant that kills every creature (6 damage), and the land swap fixes. |
| Q, Stacking the Deck | M | 6.5 | 9/10 (9.4) | 8.1 | 7.5 | Raised. The ability stays after Q dies, and each turn it turns a spare land in hand into a copy of the exiled spell, so late in a game it works like one more spell a turn. Not ✚: a copy is not a card. Both reviews grade it 8 or more. |
| The Inner Light | R | 5.5 | 8/10 (8.4) | 8.1 | 6.5 | Raised. Both reviews grade it 8. By turn 5 a green or white creature has usually died, so chapter I is a 2-for-1, and chapter II often draws two or more. |
| Academy Instructor | U | 4.5 | 7/10 (7.4) | 6.1 | 5.5 | Raised. A UR or RW deck casts about 8 noncreature spells (Equipment and Spacecraft count), so it makes two or three 1/1s and grows with each. Both reviews grade it 6 or more. |
| Conquest Mission | U | 4.5 | 7/10 (7.4) | 2.1 | 4.5 | Kept. The reviews bracket our grade (7.4 and 2.1). It needs eight or more nontoken artifacts. |
| Tell Me What You See | U | 3.5 | 6/10 (6.4) | 5.1 | 4.5 | Raised. A 2-mana card or 4 damage, the opponent's choice, and each dilemma returns it to your hand to cast again. Both reviews grade it 5 or more. |
| Branching Timeline | R | 3 | 0/10 (0.4) | 2.1 | 1.5 | Lowered. 8 mana for about two random permanents. Both reviews grade it 2 or less. |
| Combadge | U | 3 | 0/10 (0.4) | 3.1 | 3 | Kept. MTG Arena Zone agrees (3.1). |
| Dominion Infiltration | R | 3 | 0/10 (0.4) | 3.1 | 3 | Kept. MTG Arena Zone agrees (3.1). |
| Live Long and Prosper | R | 3 | 0/10 (0.4) | 4.1 | 3 | Kept. The reviews bracket our grade (0.4 and 4.1). |
| Marooned | C | 6 | 3/10 (3.4) | 6.1 | 6 | Kept (removal rule). MTG Arena Zone agrees (6.1). Draftsim notes that the creature keeps its abilities; the note says lock. |
| Mirror Universe Intrusion | R | 6 | 3/10 (3.4) | 9.1 | 6 | Kept. The reviews bracket our grade (3.4 and 9.1). |
| Mugato | U | 7 | 4/10 (4.4) | 5.1 | 6 | Lowered. All three external grades sit near 5. It does nothing beyond its stats, so it ranks below the engines and removal at 7. |
| Pure Energy | C | 4 | 1/10 (1.4) | 2.1 | 3 | Lowered. Two counters at sorcery speed are weak, and the beam me up costs a creature's tempo. Both reviews grade it 2 or less. It leaves WG's look-for list. |
| Rok-Tahk, Budding Scientist | M | 6 | 3/10 (3.4) | 7.1 | 6 | Kept. The reviews bracket our grade (3.4 and 7.1). |
| The Wrath of Khan | R | 8 | 5/10 (5.4) | 8.1 | 8 ★ | Kept as a bomb. MTG Arena Zone agrees (8.1). Draftsim calls it a 3-mana removal spell with upsides; the threaten, the loot and the edict make it more. |
| Troubling Tribbles | R | 3 | 0/10 (0.4) | 2.1 | 2 | Lowered. 0 power and no blocks; it needs an anthem or Holo-Engineer (each copy becomes a 3/3). |
| Borg Cube | M | 7 | 9/10 (9.4) | 8.1 | 7.5 | Raised half a grade. With three artifact creatures out it costs 4 and exiles a creature on entry. Station 12 needs about four creature taps, so the later attacks come late. |
| Death Is Irrelevant | M | 7 | 9/10 (9.4) | 7.1 | 7 ✚ | Kept. MTG Arena Zone agrees (7.1); it costs 8. |
| Dr. Leonard "Bones" McCoy | R | 6 | 8/10 (8.4) | 8.1 | 7 | Raised. Both reviews grade it 8. A 3-mana flash 3/2 that returns a permanent card is a 2-for-1, and at instant speed it can save a creature instead. |
| Elim Garak, Simple Tailor | R | 6 | 8/10 (8.4) | 8.1 | 7 | Raised. Both reviews grade it 8. A 3/3 menace for 3, and each dilemma is a 4-point life swing; a deck holds about 4 modal cards. |
| Excalbian Gamemaster | M | 8 | 10/10 (10.4) | 9.1 | 8.5 ★ | Raised half a grade. Both reviews grade it 9 or more. Three or four bodies for 6, and each death grows the team. |
| Holo-Engineer | R | 7 | 9/10 (9.4) | 9.1 | 8 ★ | Raised to bomb. Both reviews grade it 9. Two 3/3s for 4, and every later token you make (1/1s, Treasures, Food) is a 3/3 instead. |
| Nog, Ambitious Cadet | R | 6 | 8/10 (8.4) | 8.1 | 7 | Raised. Both reviews grade it 8. For 3 mana in total it is a 3/4 menace that surveils 2 each time it taps. |
| Sela, Tal Shiar Paradox | R | 6 | 8/10 (8.4) | 5.1 | 6 | Kept. The reviews bracket our grade (8.4 and 5.1). |
| The Caretaker | R | 7 | 9/10 (9.4) | 7.1 | 7 ✚ | Kept. MTG Arena Zone agrees (7.1). |
| U.S.S. Discovery, at Black Alert | R | 8 | 10/10 (10.4) | 9.1 | 8.5 ★ ✚ | Raised half a grade. Both reviews grade it 9 or more. Its entry alone is a 2-for-1 for 5; station 6 is easy, and each attack casts another free spell. |
| Cloak and Phaser | U | 5 | 7/10 (7.4) | 3.1 | 5 | Kept. The reviews bracket our grade (7.4 and 3.1). |
| David and Carol Marcus, Creators | U | 5 | 7/10 (7.4) | 5.1 | 5 | Kept. MTG Arena Zone agrees (5.1). |
| Deep Space 9 | M | 4 | 6/10 (6.4) | 3.1 | 4 ✚ | Kept. The reviews bracket our grade (6.4 and 3.1); it costs 9. |
| Engineered Explosives | R | 4 | 6/10 (6.4) | 6.1 | 5 | Raised. Both reviews grade it 6. At X=0 it kills every token, at 1 or 2 their cheap permanents. It hits yours too, so pick a value where they have more. |
| Lieutenant Commander Data | M | 5 | 7/10 (7.4) | 7.1 | 6 ✚ | Raised and tagged ✚. It grows with every noncreature spell, the opponent's too, and {1} turns three counters into a card again and again. Both reviews grade it 7. |
| Salt Vampire | R | 5 | 7/10 (7.4) | 8.1 | 6 | Raised. Both reviews grade it 7 or more. A 2-mana lifelink 2/2 that takes their best card in hand, often the removal spell they hold. |
| Seven of Nine, Unassimilated | M | 5 | 7/10 (7.4) | 8.1 | 6 | Raised. Both reviews grade it 7 or more. A 0/4 for 2 that loots each turn without tapping, and draws at 5 land names. |
| Subcommander T'Pol | R | 5 | 7/10 (7.4) | 5.1 | 5 | Kept. MTG Arena Zone agrees (5.1). |
| Sulu, Space Swashbuckler | R | 5 | 7/10 (7.4) | 6.1 | 5.5 ✚ | Raised half a grade. A 2/2 first strike for 2; the draw needs an Equipment or Spacecraft that turn, and a white deck holds about 2 or 3. |
| Command Decision | C | 5.5 | 3/10 (3.4) | 5.1 | 5.5 | Kept (removal rule). MTG Arena Zone 5.1. |
| I'm a Doctor, Not a . . . | C | 3.5 | 1/10 (1.4) | 3.1 | 3.5 | Kept. MTG Arena Zone 3.1. |
| Kira Nerys, Firebrand | R | 6.5 | 4/10 (4.4) | 5.1 | 6 | Lowered half a grade. The enter-attacking rule needs creatures cast during combat (flash or instant tokens); the 4/3 trample body is most of the value. |
| Photosynthetic Physician | C | 5.5 | 3/10 (3.4) | 3.1 | 5 | Lowered half a grade, level with Dominion Assault Force. A 5/5 reach for 5 with a small graveyard bonus. |
| Plasma Cascade | C | 6.5 | 4/10 (4.4) | 6.1 | 6.5 | Kept (removal rule). MTG Arena Zone 6.1. |
| Red Alert! | U | 3.5 | 1/10 (1.4) | 3.1 | 3.5 | Kept. MTG Arena Zone 3.1. |
| Tactical Officer | C | 3.5 | 1/10 (1.4) | 3.1 | 3.5 | Kept. MTG Arena Zone 3.1. |
| Warp Speed | U | 3.5 | 1/10 (1.4) | 3.1 | 3.5 | Kept. MTG Arena Zone 3.1. |

# Check of 4 November 2026: Limited Resources 878

**I re-read the oracle text of all 27 cards that differ from Limited Resources by 2 or more after the scale offset. I changed 11 grades (7 up, 4 down) and kept 16.** The episode came out on 3 November; my check of 4 November at 09:00Z did not run (CLI version error, then a revoked login), so this check ran at 11:15Z.

## Source

- **Episode:** Limited Resources 878, "Star Trek Set Review: Commons and Uncommons" (Marshall Sutcliffe and Luis Scott-Vargas, published 3 November 2026; https://lrcast.com/limited-resources-878-star-trek-set-review-commons-and-uncommons/, YouTube `E8GMevAKQ9w`, 4 hours 1 minute). Commons and uncommons only.
- **How I read it:** the episode's auto-captions (`yt-dlp --skip-download --write-auto-subs`, not committed), cut at the episode's section times (Gold 0:19:29, White 0:46:36, Blue 1:31:24, Black 2:10:10, Red 2:39:57, Green 3:06:20, Artifacts and Lands 3:39:51). Each section was read in full, and a script checked every quoted line against the captions.
- **Grades:** letters as spoken, A to F. `lr_grades.json` keeps each card's letter, whether the hosts called it a build-around, the time, the quote and a confidence. 201 cards were discussed and 200 graded (Test of Courage got no letter). Where the hosts split and never settled, the file keeps both letters (for example "C+/B-") and the comparison uses their mean. For Worf, Honor-Bound Warrior and Pure Energy the hosts said "build around C, in other words a D"; I use D.
- **Mapping:** a grade-point scale doubled (A 8, B 6, C 4, D 2, F 0; a plus or minus moves a third of a letter), plus the mean offset, +0.45 on the 184 shared non-land cards before the check. `compare_lr.py` prints the comparison, with Draftsim's review and MTG Arena Zone beside each gap. `grades_src_pre_lr.py` keeps our grades before this check.
- **Limits:** a Draft review, read from auto-captions. Some letters are pick order in Draft rather than power: for Cha'DIch Investigator and Dominion Assault Force the hosts rate the power a C and give the D as a pick. No back-test scores this source: on Reality Fracture I read excerpts for 50 cards, not a full list. The back-test after Star Trek (R5) can score it.

## Result

- **Rank correlation with Limited Resources:** 0.55 before the check, 0.60 after (commons 0.37 to 0.41, uncommons 0.47 to 0.53). With Draftsim's review: 0.69 before, 0.71 after. With MTG Arena Zone: 0.76 before, 0.77 after. Limited Resources and Draftsim's review rank the same 184 cards at 0.66; Limited Resources and MTG Arena Zone at 0.52.
- **Gaps of 2 or more:** 27 before, 19 after: the 16 kept cards, and DOT-7 Repair Squad, Dr. McCoy, Surly Surgeon and Melkotian Adjudicator, which moved half a grade toward the sources.
- **Rarity check (R2):** our uncommons sit 0.63 above our commons (0.62 before). Limited Resources' gap on the same cards is 1.18 on its scale; in standard deviations it is 0.79 against our 0.62. Like Draftsim's review, it supports the 1.0 floor more than our grades do. I do not force the floor.
- **Bombs:** still 10. **✚:** still 28.
- **Colours:** mono-colour cards graded 6+ are W 11, U 7, B 17, R 10, G 15 (before: 11, 7, 17, 10, 14). David and Carol Marcus joins green; Spock (6) is gold.
- **Archetype lists:** four grades changed in the look-for lines (Melkotian Adjudicator twice, Dr. McCoy, David and Carol Marcus). Organic Avulsion Unit (now 5) joins WB's list.

## How I decided

- **Change** when Limited Resources and at least one other source (Draftsim's review, MTG Arena Zone) sit 1 or more on the same side of our grade, no source sits 1 or more on the other side, and the card text or the Sealed format gives a reason that our note missed. Move half a grade or one grade, not all the way.
- **Move half a grade** when all three sources sit 2 or more on the same side, even without a new reason: three reviews that agree outweigh my read (on the Reality Fracture back-test each review ranked the cards better than we did).
- **Keep** when the sources bracket our grade, when only Limited Resources sits 1 or more away, or when the Sealed format explains the gap.
- **Removal:** kept, as before. On Reality Fracture no source misjudged removal at equal grade.

## Decisions

The table lists the grade before the check, Limited Resources' letter (with its mapped value), Draftsim's review and MTG Arena Zone (mapped), and the grade after.

| Card | Rarity | Before | Limited Resources (+ offset) | Draftsim review | MTGAZ | After | Decision and reason |
|---|---|---:|---:|---:|---:|---:|---|
| 70,000 Light-Years from Home | U | 7.5 | D/C+ (3.8) | 6.6 | 5.4 | 7.5 | Kept (removal rule). All three sources sit lower; the hosts split C+ and D and never settled. A 2-mana exile of any creature or Spacecraft; the land goes to their hand, not into play. 7 or 7.5 changes no count on the sheet. |
| Cleveland Booker, Empath | U | 6 | D (2.5) | 6.6 | 5.4 | 6 | Kept. The sources bracket our grade (Draftsim 6.6, Limited Resources 2.5). |
| Rules of Acquisition | U | 4 | F (0.5) | 1.6 | 4.4 | 4 | Kept. MTG Arena Zone agrees (4.4). In Sealed the steal answers a bomb, and the other mode gives away a token for three cards. |
| Cha'DIch Investigator | C | 5.5 | D (2.5) | 4.6 | 3.4 | 5.5 | Kept (also kept on 2 and 3 November). The hosts rate its power "about a C" (4.5) and give the D as a Draft pick. In Sealed you play the cards you open: a 4/4 and a 2/1 haste for 5. |
| DOT-7 Repair Squad | C | 5.5 | D (2.5) | 2.6 | 3.4 | 5 | Lowered half a grade: all three sources sit 2 or more below. The hosts say 4-mana 3/3 fliers like it play worse than they look. The untap is sorcery-speed, so the body is the card. |
| Vengeance Mission | U | 3 | C+/B build-around (5.8) | 4.6 | 4.4 | 4 | Raised. Every creature that dies, theirs, yours or a token, drains 1 (2 after seven deaths), and a Sealed game has many trades. All three sources grade it 4.4 or more. |
| Those Old Scientists | U | 4.5 | D- (1.8) | 3.6 | 3.4 | 3.5 | Lowered. Chapter I is card-neutral (draw two, discard two), so the saga is one card ahead over two turns for 3 mana, with no board. My note called it a 2-for-1. |
| Dominion Assault Force | C | 5 | D (2.5) | 2.6 | 4.4 | 5 | Kept (lowered half a grade on 3 November). The hosts rate its power a C (4.5) and give the D as a Draft pick. A 4/4 vigilance for 4 is above the rate. |
| Dr. McCoy, Surly Surgeon | U | 5 | D (2.5) | 3.6 | 4.4 | 4.5 | Lowered half a grade. The shield works only while McCoy lives, and McCoy is a 4-mana 2/2. |
| Melkotian Adjudicator | C | 5 | D (2.5) | 3.6 | 4.4 | 4.5 | Lowered half a grade. A 2/1 dies to 1 damage, and a deck holds about 4 modal cards, so it often stays a 2/1. |
| Suus Mahna Practitioner | C | 5 | D (2.5) | 4.6 | 4.4 | 5 | Kept. Draftsim and MTG Arena Zone sit within 0.6. The hosts call the tap too expensive, but with the usual 3 land names it costs {1}{U}. |
| Andromedan Automatons | C | 3 | C+/B- (5.5) | 4.6 | 5.4 | 3.5 | Raised half a grade. The hosts' grade assumes two or three copies; a Sealed pool holds a second copy 11% of the time. It is a 3/1 artifact creature that counts for WB's payoffs. |
| Emergency Medical Hologram | C | 2 | C (4.5) | 2.6 | 3.4 | 3 | Raised. It is the cheapest creature to return for beam me up (11 cards) and cast again for another counter, and it counts for WB's artifact payoffs. My note saw neither. |
| Organic Avulsion Unit | U | 4 | B build-around (6.5) | 5.6 | 5.4 | 5 | Raised. A 2/3 for 3 blocks well early; later, {2} gives every artifact creature menace, which turns a WB board (about 6 artifact creatures) into a lethal attack. Joins WB's look-for list. |
| Cloak and Phaser | U | 5 | B+ build-around (7.1) | 7.6 | 3.4 | 5 | Kept. The sources bracket our grade (Draftsim 7.6 and Limited Resources 7.1 above, MTG Arena Zone 3.4 below), as on 3 November. |
| David and Carol Marcus, Creators | U | 5 | B+ (7.1) | 7.6 | 5.4 | 6 | Raised. The Planet token is a land: it puts you a land ahead, makes any colour, adds a land name for strange new worlds, and triggers landfall. My note counted the colour only. |
| Federation Probe | C | 3 | C+ (5.1) | 4.6 | 4.4 | 4 | Raised. Its modes are a dilemma, it is an artifact creature, and at 1 mana it is the cheapest creature to return for beam me up. All three sources grade it 4.4 or more. |
| Interstellar Effigy | C | 5 | B+ (7.1) | 5.6 | 4.4 | 5 | Kept. Draftsim and MTG Arena Zone sit within 0.6. The bounce is tempo, which counts for less in Sealed. |
| Spock, Always Your Friend | U | 5 | B+ (7.1) | 6.6 | 7.4 | 6 | Raised. With 9 noncreature spells in 40 cards, the top four hold one 66% of the time, so two times in three it is a 2-for-1 for 2 mana. All three sources grade it 6.6 or more. |
| Zefram Cochrane, Warp Pioneer | U | 5 | B+ build-around (7.1) | 5.6 | 4.4 | 5 | Kept. Only Limited Resources sits 1 or more away, and its grade is for the artifact deck. |
| Class-F Shuttlecraft | C | 4.5 | D (2.5) | 3.6 | 3.4 | 4.5 | Kept. The sheet's splash rule counts it as a source; fixing matters more in Sealed than in Draft. |
| Emergency Holographic Crew | C | 4.5 | D (2.5) | 4.6 | 3.4 | 4.5 | Kept. Draftsim agrees (4.6). The hosts call it replaceable in Draft; in Sealed a 3/4 for 4 with surveil 2 makes the deck. |
| Highly Illogical | U | 4.5 | D (2.5) | 4.6 | 3.4 | 4.5 | Kept. Draftsim agrees (4.6), and the hosts say it is better in Sealed and long games. |
| Shuttle Ace | C | 4.5 | D (2.5) | 1.6 | 3.4 | 4.5 | Kept (lowered half a grade on 3 November, because it never blocks a flier). MTG Arena Zone sits 1.1 below, not 2. |
| Support Mission | U | 4.5 | D (2.5) | 0.6 | 6.4 | 4.5 | Kept. The sources bracket our grade (MTG Arena Zone 6.4 above). |
| Worf, Honor-Bound Warrior | U | 4.5 | D build-around (2.5) | 6.6 | 4.4 | 4.5 | Kept. The sources bracket our grade (Draftsim 6.6 above), and MTG Arena Zone agrees (4.4). |
| Xindi Surveyors | C | 4.5 | D (2.5) | 3.6 | 4.4 | 4.5 | Kept. MTG Arena Zone agrees (4.4); only Limited Resources sits 1 or more away. |

# Self-review of 5 November 2026 (playbook step 9, DEC-1218 R6)

**A cold read of every card note against the oracle text found 3 wrong notes and 11 misleading ones, plus 9 notes that left out a condition. I fixed 23 notes and changed 1 grade: U.S.S. Cerritos, Following Up, 6 to 5.5.** Two read-only reviewers did the cold read; each one saw only the files, not my conclusions. I checked each finding against the oracle text before I changed anything.

## The grade change

| Card | R | Ours before | Limited Resources | Draftsim review | MTG Arena Zone | Ours now | Decision |
|---|---|---:|---|---:|---:|---:|---|
| U.S.S. Cerritos, Following Up | U | 6 | B (6.5) | 4.4 | 4.1 | 5.5 | Lowered half a grade. My note said the two 1/1s station it to a flying 4/4. It becomes a creature at 6 counters, so the two tokens alone take three turns. The reviews bracket our grade (mean 5.0), so I took off only the misread. |

## Grades kept after a wrong note

- **U.S.S. Enterprise-A, Free Spirit (8.5 ★):** my note said the three 1/1s station it at once. They give 3 counters a turn and it needs 6, so it takes two turns with the tokens alone, or one with another creature of power 3. Draftsim's review gives it 10/10 and MTG Arena Zone 4.5/5, so the bomb grade stands.
- **Georgiou, Terran Emperor (8 ★):** the note left out the 3 life you lose each end step, and that you lose the game if she leaves while you are at 0 or less. The grade already counted the draw against the life.
- **Q, Stacking the Deck (7.5), Borg Cube (7.5), De-evolve (6), Picard, Leading by Example (5.5), Vengeance Mission (4):** each note now says what the card does; each grade's reason still holds.

## Tags

- **⚡ means trick.** The builder prints ⚡ for the role `trick`; my intro called it "instant-speed". The legend now says "⚡ trick". Three sorceries lost the role: Pure Energy, Test of Conviction and Energize. Test of Courage, a 1-mana instant, gained it and now shows in section 4.
- **✚ edge cases, not changed:** Seven of Nine, Unassimilated draws each turn at 5 land names, and Dathon, His Heart Open draws on each enchantment spell. Neither has ✚, while Kirk, Commanding Officer (also conditional) has it. Only the tie-break (step 7) reads ✚, so I left them for the back-test.
