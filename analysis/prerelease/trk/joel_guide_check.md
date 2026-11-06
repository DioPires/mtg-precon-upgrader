# Joel Are Magic's Star Trek prerelease guide: check (DEC-1218, 6 November 2026)

**Source.** Joel Are Magic, "The COMPLETE Star Trek Prerelease Guide", YouTube `I_sUtDGvJhM`,
published 4 November 2026, 39 minutes. I read the guide from the auto-captions. The `en` track
returned HTTP 429, and the `en-orig` track downloaded:
`yt-dlp --skip-download --write-auto-subs --sub-langs en-orig --sub-format vtt <url>`.
The board sent the link on 6 November 2026 at 15:38Z, the day of the event.

**Result.** Joel's set numbers hold against the card file, with one small miss. His card calls
change no grade before the event: on every card where he differs a lot from us, at least one of
Draftsim's review and MTG Arena Zone's review sits with our grade or above it. His pair order is
not on the sheet. It ranks the pairs by their common removal, and the Reality Fracture back-test
found that removal predicted the pairs' results poorly. Question 11 of `backtest-plan.md` scores it.

## Set numbers, recounted from `trk_all_cards.json`

| Time | Joel's claim | Recount | Verdict |
|---|---|---|---|
| 3:53 | 8 flying creatures at common and uncommon; 4 of the 47 common creatures | 8; 4 of 47 | Holds |
| 4:34 | 8 Spacecraft at common and uncommon fly once fully stationed | 8 | Holds |
| 4:44 | At rare and mythic, 7 flying ships and 1 flying creature (Crystalline Entity) | 8 flying ships: Enterprise-A, Bounty, Romulan Bird-of-Prey, Reliant, D-7 Battle Cruiser, Discovery, Borg Cube, Enterprise-D | 8 ships, not 7 |
| 5:11 | Artifacts are 26% of the commons | 21 of the 81 commons that are not dual lands (25.9%) | Holds |
| 8:11 to 8:18 | -2/-2 kills 24 of the 47 common creatures; -3/-3 kills 34 | 24 of 47; 34 of 47 (72%) | Holds |
| 8:22 | 82% of the common creatures with mana value 3 or less have toughness 2 or less | 23 of 28 (82.1%) | Holds |
| 8:29 | The normal figure in recent sets is about 70% | Reality Fracture: 21 of 29 (72.4%) | Holds on the one set I can check |
| 21:27 | The average common two-drop is smaller than a 2/2; only Starfleet Spanner Jockey has 3 power | 12 common two-drops, mean 1.92/1.67; Spanner Jockey is the only one | Holds |

`toughness_check.py` prints the toughness figures.

## The 82% and the sheet's 75%

The board asked which figure is right. Both are, because they count different groups.

| Whose figure | Creatures counted | Toughness | Share |
|---|---|---|---:|
| Joel, 8:22 | 28 common creatures with mana value 3 or less | 2 or less | 23 of 28 = 82% |
| Joel, 8:11 to 8:18 | all 47 common creatures | 3 or less | 34 of 47 = 72% |
| Our sheet, section 3 | all 165 creatures | 3 or less | 124 of 165 = 75% |
| Recount, weighted by how often each rarity opens in a Play Booster | all 165 creatures | 3 or less | 74% |
| `set_facts.md`, Spacecraft included | 181 cards | 3 or less | 130 of 181 = 72% |

What the sheet lacks: 2 damage kills 23 of the 28 common creatures that cost 3 or less, while the
sheet gives 46% for 2 damage over all creatures. A future sheet can add the census of cheap
commons to section 3 (`notes.md`, the leg after the event).

## Card calls against our grades

Joel would not play 9 of the 25 mythics in Sealed (12:45). Our grades for them: Kobayashi Maru
Scenario 0, Seven of Nine, Unassimilated 6, Death Is Irrelevant 7, Infinite Diversity 1.5, Q,
Stacking the Deck 7.5, Quark, Humble Proprietor 3, Captain Kathryn Janeway 6, Dr. Joseph
M'Benga 5.5, Starfleet Academy 2.5.

The rows below are the cards where Joel differs from our grade by a lot. The reviews' figures are
raw: MTG Arena Zone rates 0 to 5 and Draftsim's review 0 to 10.

| Card | Ours | MTG Arena Zone | Draftsim review | Joel | Decision |
|---|---:|---:|---:|---|---|
| Q, Stacking the Deck | 7.5 | 4.0 | 9 | Would not run | Keep. Both reviews rate it high. The copy ability has no once-a-turn limit. |
| Death Is Irrelevant | 7 | 3.5 | 9 | Would not run: 8 mana | Keep. Both reviews sit at or above ours. Its cost is the risk, and the note says 8 mana. |
| Seven of Nine, Unassimilated | 6 | 4.0 | 7 | Would not run: needs 5 land names | Keep. Without the names it still loots every turn on a 2-mana 0/4. |
| Captain Kathryn Janeway | 6 | 4.0 | 6 | Would not run | Keep. Every creature that enters explores. |
| Captain Pike, Fullness of Time | 6 | 4.0 | 7 | Built for Commander | Keep. Both reviews sit at or above ours. |
| Sarek, Federation Ambassador | 5 | 1.5 | 6 | Five creature types will not happen | Keep. The reviews bracket ours. Our count of 3 November found five types on 90% of boards with two other creatures. Joel gives no count. |
| Collation Trimatrix | 5.5 | 3.0 | 7 | A 1/1 for 1 in most pools | Keep. The reviews bracket ours, and the note names its WB home. |
| Dr. Joseph M'Benga | 5.5 | 3.0 | 4 | A 3/3 for 4 without counters | Keep. The reviews bracket ours. |
| Stable Wormhole | 3 | 2.0 | 4 | B+ to A | No change before the event. Both reviews sit above ours, and our note misses that each New Planet also triggers landfall, and the first one adds a land name. A re-read would raise it to 4, which makes it a playable in step 4. It matters only if the board opens it. |

His other calls agree with our grades or sit near them: U.S.S. Enterprise-A (S+, ours 8.5 ★),
U.S.S. Discovery (S, 8.5 ★), Borg Cube (7.5), Excalbian Gamemaster (A, 8.5 ★), Armus (8 ★),
Georgiou (8 ★), The Wrath of Khan (8 ★), Holo-Engineer (8 ★), Crystalline Entity (8 ★),
Mr. Spock, Science Officer (8 ★), Nog (high B to low A, 7) and Mirror Universe Intrusion (B, 6).

## Advice that differs from our sheet

- **Removal floor.** Joel (33:12) repeats WotC's prerelease guide (Jubilee Finnegan, 30 October
  2026, https://magic.wizards.com/en/news/feature/star-trek-prerelease-guide): "aim to include at
  least five removal spells across your two colors", and "don't be afraid to run an extra copy of
  Perils of the Past". Our step 6 says to play the removal you have but not to pick colours for it (R4). On
  Reality Fracture, the removal gate predicted the pairs' Sealed results at -0.37. That is one set
  with a wide interval, so `backtest-plan.md` questions 4 and 11 test removal again.
- **Pair order.** Joel ranks the pairs RW, RG, GW, BR, WB, WU, UR, BG, GU, UB, "easiest to
  hardest" (24:32 to 32:16). The order follows each pair's common removal. On Reality Fracture
  the two best Sealed pairs were blue (WU 58.9%, UB 58.3%), and UB is last here. The sheet keeps
  no pair order (R3).
- **Splash.** Joel says to play two colours on a first build. Our step 5 allows a splash of up to
  3 cards graded 6+ with 3 or more sources (N1). Keep N1: question 8 tests it.
- **Agrees with our sheet:** 17 lands, 7 or 8 two-drops (WotC's curve), the planet duals in your
  colours, and that artifact removal also answers Spacecraft.

## Joel's Reality Fracture guide

"The COMPLETE Reality Fracture Prerelease Guide" (YouTube `zarJgn6KF74`, 22 September 2026,
14 minutes) is a guide for new players. It gives prices, the sorting method, "four or five pieces
of removal minimum", "14 15 creatures", and two colours with 17 lands. It has no card grades and
no pair order, so the Reality Fracture back-test has nothing of his to score.
