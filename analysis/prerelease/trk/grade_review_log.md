# Star Trek grade review log (DEC-1218 R1)

**Check of 2 November 2026: our grades against MTG Arena Zone's Limited set review.** I re-read the oracle text of all 49 cards that differ by 2 or more after the scale offset. I changed 20 grades and kept 29, each with the reason below. Draftsim's set review and the Limited Resources episode were not out at 14:00Z (Draftsim's set list: "Set Review (coming soon!)"; lrcast.com's latest episode, 877, is a Q&A of 30 October). When Draftsim's review comes out by the evening of 4 November, I run the same check against it.

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
