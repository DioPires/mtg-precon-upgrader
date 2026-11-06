# Star Trek back-test plan (DEC-1218 R5)

Written on 5 November 2026, before the event of 6 November and before Arena opens on
10 November. It fixes, in advance, which result changes which rule. The back-test runs about
1 December 2026, on 17Lands data from 10 November to the fetch day.

## Data and method

- **Copy** `analysis/prerelease/fra/backtest/retro.py` into `trk/backtest/` and point it at the
  Star Trek files. Fetch the same three 17Lands files as for Reality Fracture: card ratings
  (Premier Draft), and colour ratings for Sealed and for Premier Draft (`combine_splash=true`).
- **Cards scored:** commons and uncommons with a GIH WR (win rate when drawn) on 17Lands.
  17Lands publishes no Sealed card data and no useful rare data.
- **Score:** Spearman rank correlation with GIH WR. Every comparison of two grade sets is paired
  (same cards) and reports a bootstrap 95% interval (10,000 resamples of cards).
- **Residuals at equal grade:** fit GIH WR on our final grade plus rarity, as the Reality
  Fracture adversarial review did. A group's residual is its mean gap from that fit, with a
  bootstrap interval.

## Grade sets to score

| Set | File | What it is |
|---|---|---|
| Pass 1 | `grades_src_pass1.py` | First blind pass |
| Blind | `grades_src_blind.py` | Blind, after the two rarity re-reads (1 November) |
| Pre-check | `grades_src_precheck.py` | After the token re-read of 2 November (✚ fix) |
| After MTG Arena Zone | `grades_src_pre_draftsim.py` | After the check of 2 November |
| After pick order | `grades_src_pre_review.py` | After Draftsim's pick order, 3 November |
| After Draftsim review | `grades_src_pre_lr.py` | After Draftsim's set review, 3 November |
| Final | `grades_src.py` | After Limited Resources (4 November) and the self-review (5 November: U.S.S. Cerritos 6 to 5.5); the sheet's grades |
| MTG Arena Zone | `mtgaz_grades.json` | 0 to 5 |
| Draftsim pick order | `draftsim_pick_ratings.json` | 0 to 5, read 3 November |
| Draftsim review | `draftsim_review_ratings.json` | 0 to 10 |
| Limited Resources | `lr_grades.json` | Letters, commons and uncommons only |
| Consensus | mean of the three reviews after each one's offset | Built in the back-test |

## Questions and decision rules

1. **Do our final grades predict as well as the reviews?**
   - If the best review or the consensus beats our final grades by 0.10 or more, and the paired
     interval excludes 0: the next set starts from the review consensus (I1 as first proposed).
     I then change a grade only with a written reason from the card text.
   - Otherwise: keep R1 (grade first, then check against the reviews).
2. **Did the R1 checks help?** Compare final with blind, and each step with the one before.
   - If final does not beat blind: question 1 decides alone.
   - Report each step's change. A step that lowers the score does not change a rule by itself,
     because each step moved only 11 to 34 grades.
3. **The cards I kept against the reviews.** `grade_review_log.md` lists the cards that I kept
   although a review differed by 2 or more. For each, check whether GIH WR sits nearer our grade
   or the consensus (by percentile).
   - If the consensus is nearer on two thirds or more of 9 or more cards: the next set follows
     the consensus wherever two reviews agree by 2 or more, unless the card text gives a reason
     that both reviews missed.
   - Removal counts here too (70,000 Light-Years from Home, kept at 7.5 against all three).
4. **Removal at equal grade (R2c, and "removal keeps its grade").**
   - If the removal residual's interval sits wholly below 0: removal follows the consensus on the
     next set.
   - If it crosses 0: keep the rule. Reality Fracture's interval also crossed 0.
5. **Card advantage at equal grade (R2b, ✚ +1).**
   - If the ✚ residual's interval sits wholly above 0: keep the +1.
   - If it crosses 0 on Star Trek: keep the +1 for one more set, because Reality Fracture showed
     +2.3 (+1.0 to +3.6). If it crosses 0 again on the next set, drop the +1 and keep ✚ for the
     tie-break only.
   - If it sits wholly below 0: drop the +1.
6. **Rarity at equal grade (R2a, the 1.0 floor).**
   - If uncommons win 1 point or more over commons at equal grade, and the interval excludes 0:
     the floor was right, and the next set enforces it by re-reading until it holds.
   - If the interval crosses 0: drop the floor and keep only the re-read of the largest gaps.
7. **Colour bias.** Our mono-colour cards graded 6+ were W 11, U 7, B 17, R 10, G 15 (4
   November). Rank the five colours by 17Lands Sealed win rate (mean over the pairs that hold
   the colour).
   - If the colour that our grades rank last is in the top two again (blue was the best Sealed
     colour on Reality Fracture): add a colour check to step 4 of the playbook. It compares each
     colour's mean common and uncommon grade with the consensus and re-reads the colour that sits
     lowest against it.
8. **Splash rule (N1).** Read the share and the win rate of three-colour decks in 17Lands Sealed.
   - If three-colour decks win within 0.5 points of two-colour decks or better: keep the rule.
   - If they lose by 1.5 points or more and the interval excludes 0: go back to Reality
     Fracture's rule (up to 2 cards graded 7+).
9. **Which sources to use.** Score Limited Resources for the first time.
   - The next R1 check uses every review that scores within 0.05 of our final grades or better.
   - A review that scores 0.10 or more below ours on two sets is dropped.
   - If Draftsim's pick order scores 0.10 or more below its review, the playbook names the
     review only.
10. **Your feedback after the event (step 10).** The pair you played, your record, and what in
    the sheet, the PDF or the page helped or misled you. It goes into `notes.md`. It changes the
    sheet's layout; it does not change a grading rule by itself.
11. **A pair order by common removal (added 6 November).** Joel Are Magic's guide of 4 November
    ranks the pairs RW, RG, GW, BR, WB, WU, UR, BG, GU, UB, by each pair's common removal
    (`joel_guide_check.md`). WotC's prerelease guide advises at least five removal spells.
    Score his order against the pairs' 17Lands Sealed win rates, as the Reality Fracture pair
    ranking was scored. With 10 pairs the interval is wide: Reality Fracture's ranking scored
    -0.09, with an interval of -0.68 to +0.57.
    - Also count each pair's common and uncommon removal by our tags, and score that count
      against the same win rates.
    - If his order or the removal count scores +0.5 or more: re-open R4 (no removal floor) with
      both sets' results, and the next sheet may print his order beside the archetypes as one
      source's view, with its score.
    - If both score under +0.5: the order stays off the sheet, and R4 stands.

## Not tested

- Rares and mythics: 17Lands publishes no useful data for them. So Joel Are Magic's calls on
  the rares and mythics (`joel_guide_check.md`) cannot be scored either.
- The ten archetype plans and the hand procedure as a whole: one player's result cannot score
  them.
- The pair simulation (R3): Star Trek has no collation config.

## Limits

One set; Premier Draft card data for a Sealed sheet; mostly best-of-one games; GIH WR favours
cards in the strongest colours; about 180 cards at most. Read the size and the direction of each
result, not one card's number.
