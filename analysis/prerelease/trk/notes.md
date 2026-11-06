# Star Trek prerelease: notes (DEC-1218)

Event: Friday 6 November 2026, Sealed, 6 Play Boosters plus 1 foil rare or mythic. Sheet due Thursday 5 November.

## Sources
- WotC, "Collecting Magic: The Gathering | Star Trek" (https://magic.wizards.com/en/news/feature/collecting-star-trek): slot rates. Common duals appear only in the land slot (40% non-foil, 10% foil). Commons draw from 81 cards (the 10 duals are not among them). Rare slot: 80.1% rare, 12.4% mythic, LCARS shock lands 1.4%. Wildcard: 20.8% C, 54.1% U, 16.7% R, 2.6% M. Foil: 51.2% C, 34.7% U, 6.3% R, 1% M.
- WotC, "Magic: The Gathering | Star Trek Mechanics" (Matt Tabak, 20 October 2026): edge cases in `format_rules.md`. A beam-me-up spell is always exiled. A dilemma counts as you choose modes, even if the spell is countered later; choosing several modes counts once; with no legal mode there is no dilemma. A creature that entered this turn can station.
- Draftsim, "Exploring All Ten Star Trek Limited Archetypes" (Peter Smith, updated 22 October 2026, https://draftsim.com/?p=326838): archetype names and two signposts per pair. Every plan sentence in `prose.json` was checked against oracle text. The Look for cards are our picks.
- Not out on 1 November: Draftsim's full review, Limited Resources' episode. I also wrote "a WotC prerelease guide" here, and that was wrong: WotC's "Star Trek Prerelease Guide" (Jubilee Finnegan, https://magic.wizards.com/en/news/feature/star-trek-prerelease-guide) was published on 30 October 2026 at 15:00Z. I found it on 6 November. It advises at least five removal spells across two colours, an extra copy of Perils of the Past, and the curve that our step 6 already uses (7 or 8 two-drops, 17 lands). No grade or rule changed.
- Draftsim, "Star Trek (TRK) Pick Order & Tier List" (https://draftsim.com/TRK-pick-order/, read 3 November 2026): 0 to 5 ratings for every card, the R1 check of 3 November (`grade_review_log.md`). On Reality Fracture the pre-release pick order held the set review's ratings (rank correlation 0.99). I wrote here that Draftsim's set review was still not out at 10:40Z on 3 November; that was wrong (see the next line). A Limited Resources Star Trek episode was still not out.
- Draftsim, "The Ultimate MTG Star Trek Limited Set Review" (Andrew Quinn, published 2 November 2026 at 17:00Z, https://draftsim.com/mtg-trk-limited-set-review/): 0 to 10 ratings for every non-land card, the R1 check of 3 November against the review (`grade_review_log.md`). Draftsim's set list still read "coming soon" on 3 November. On this set the review and the pick order rank the cards at 0.68, so the pick order is not the review here.
- Limited Resources 878, "Star Trek Set Review: Commons and Uncommons" (Marshall Sutcliffe and Luis Scott-Vargas, published 3 November 2026, https://lrcast.com/limited-resources-878-star-trek-set-review-commons-and-uncommons/, YouTube E8GMevAKQ9w): letter grades for 200 commons and uncommons, read from the auto-captions into `lr_grades.json`; the R1 check of 4 November (`grade_review_log.md`, `compare_lr.py`).
- Joel Are Magic, "The COMPLETE Star Trek Prerelease Guide" (YouTube I_sUtDGvJhM, published 4 November 2026; the board sent it on 6 November at 15:38Z): set numbers, the rares and mythics that he would and would not play, and a pair order by common removal. I checked it on 6 November (`joel_guide_check.md`): the numbers hold except one (8 flying ships at rare and mythic, not 7), and no grade changed. His 82% is 2 damage on the 28 cheap common creatures, not 3 damage on all creatures; the sheet's 75% stands.

## Fixing and the splash rule (N1)
`python3 -I splash_sources.py` (200,000 pools, seed 20261106):
- A pool holds 3.00 common duals and 0.96 shock lands on average.
- Non-basic sources of the best third colour (main pair drawn at random), share of pools with at least k:

| Sources | >= 1 | >= 2 | >= 3 | >= 4 | >= 5 | >= 6 |
|---|---:|---:|---:|---:|---:|---:|
| dual and shock lands | 99% | 83% | 46% | 16% | 4% | 1% |
| + Class-F Shuttlecraft, Xenobotanist (green) | 99% | 92% | 70% | 40% | 18% | 6% |
| + Unexplored Territory, Warp Core, Final Frontier (green) | 100% | 98% | 89% | 72% | 50% | 30% |

- Chance to see at least one source of a colour, 40-card deck (hypergeometric). By turn 6 on the play (12 cards): 3 sources 67%, 4 sources 78%, 5 sources 85%. By turn 3 on the play (9 cards): 4 sources 66%, 6 sources 81%.
- Rule written: splash up to 3 cards graded 6+ with 3+ sources, at most 1 a basic. With 4+ non-basic sources, the third colour may fill step 4, with cards of 3+ mana. Reality Fracture's rule was 7+ cards, 2+ lands, at most 2 cards.
- Basis: Star Trek's fixing is close to Reality Fracture's: 3.0 duals per pool against about 3.3 (54.5% per pack). On Reality Fracture, 37% of Arena Sealed games were three-colour decks, at 56.3% against 56.9% for two colours (DEC-1218 back-test). One set, mostly best-of-one, so the rule loosens the splash and does not push a third colour.
- Unexplored Territory, Warp Core and Final Frontier find a basic, so they do not count as sources on the sheet.

## Corrections to my earlier figures
- **Modal cards: 39, not 48.** 39 cards have modes (14 commons, 14 uncommons, 9 rares, 2 mythics); I could not reproduce the 48 in my comment of 1 November. The grade notes of Captain Benjamin Sisko and Seven of Nine said 48; both now say 39.
- **Toughness shares: use the sheet's census.** `set_facts.md` counts 181 creatures, including 16 Spacecraft with a printed toughness. The sheet's section 3 counts 165 creatures. The grade notes and `format_rules.md` now quote the sheet: 46% have toughness 2 or less, 75% 3 or less, 88% 4 or less.

## Self-review of 5 November (step 9, R6)
- **Every number on the sheet holds against its source.** The rarity gaps in the intro come from the compare scripts (ours 0.62 after the Cerritos change; Draftsim's review 1.22; Limited Resources 1.18; MTG Arena Zone 0.51). Section 2's counts (17 Spacecraft, 39 modal cards, 9 dilemma payoffs, 10 beam-me-up sorceries, 13 strange-new-worlds cards, 6 Federation cards, 6 stun cards), the toughness shares (46%, 75%, 88% of 165 creatures) and the section-3 lead (black 7 removal spells, red's mean 6.8, white 6 at common and uncommon) all recount from the card file. All 76 look-for grades match `grades.json`. WotC's land slot still reads 40% plus 10% foil common duals, so 3.0 per pool.
- **Card notes:** 23 fixed, 1 grade changed (`grade_review_log.md`, last section).
- **Rules text fixed:**
  - Station: a Spacecraft becomes a creature at the stripe that shows power and toughness, not at its first stripe (D-7 Battle Cruiser has a 3+ stripe and is a creature at 8+; Deep Space 9 never is).
  - Spacecraft removal: Malfunctioning Holodeck, Marooned and artifact removal hit a Spacecraft too, beside 70,000 Light-Years from Home and Guidance Failure.
  - UB plan: a modal spell or ability triggers the dilemma cards once, however many modes you choose.
  - UG plan: the "4 of the 6 coloured fixers" figure depended on our tags; the plan now names green's four fixers.
- **Procedure wording now matches the page's pool counter:** a hybrid card counts once per pair; a ★ counts as two 6+ cards; step 4 counts colourless non-land cards (the 20 lands are graded 4 and are not playables). The browser check still finds 0 of 382 numbers different.
- **Splash sources:** David and Carol Marcus, Creators makes a New Planet token that taps for any colour, so step 5 now lists it. The table above counted only Class-F Shuttlecraft and Xenobotanist, so the shares with 4+ sources are a little higher than 40%. Saurian Explorer makes a New Planet only for {6}, so it is not listed.
- **Builder issues left for the leg after the event (with R7 and the Chrome 156 exit):**
  - Section 3's census could add the cheap commons: 2 damage kills 23 of the 28 common creatures with mana value 3 or less (82%), against 46% of all creatures. Joel Are Magic's guide gave the figure (`joel_guide_check.md`, `toughness_check.py`). It needs a `set_facts.md` row and a sheet line.
  - Eject the Warp Core and Genesis Effect read "≤6 (100%)"; V'Ger, the Intruder and Crystalline Entity have toughness 7, so the share is 99% (163 of 165).
  - Common Goal's label says "fight"; it is one-sided, and two of your creatures can add their power.
  - Section 3's census leaves out Captain Pike (toughness */*): 165 creatures, not 166.
  - Section 4 sorts by printed cost. Red Alert! costs {R} when a creature attacks you, and Guidance Failure {2}{U} on an attacker; the notes say so, the cost column does not.
