# Reality Fracture Sealed pool simulation

`100,000` pools, seed `20260925`, 6 Play Boosters + 1 promo. Grades: **CEO grades**.

## Assumptions

- Slot 6's 1.82% Special Guest is off-set and unusable in Sealed, so that slot always yields a main-set common.
- Slot 8's 3% 'other' folds into non-paired uncommon.
- Slots 9-11: the third echoed-pair card is drawn independently of the pair in slots 9-10 and may duplicate one of its halves.
- Slot 12's 10.8% booster-fun variants are still set rares/mythics, split proportionally (R 83.4% / M 16.6%).
- Slot 13 'full main set' means the 270-card main numbering, so the 10 common duals are not in the foil slot; the 2.8% residual is normalized away proportionally.
- Every slot's published weights are normalized to sum to 1. The published figures for slots 8, 9-11 and 13 sum to 0.97-0.972; the CEO's target of 4.81 uncommons per pack was computed without that normalization and is not reachable by any proper distribution. The normalized model gives ~4.94. Commons, rares+mythics and duals match the targets.
- Promo: one card uniform over the 64 main-set rares + 26 mythics (64/90 vs 26/90). FLAGGED - board to confirm from the pack.
- Basic lands are dropped from the pool (unlimited at the event).
- Eligibility is castability, not colour identity (DEC-927): every pip of the front-face mana cost must be payable by the pair. A hybrid pip {W/B} needs W or B; {2/W}, Phyrexian, generic, {X} and {C} are always payable. So Blessed Ghoul ({W/B}) is eligible for all 7 pairs containing W or B and Karn, Gilded Guardian ({2/W}{2/U}{2/B}{2/R}{2/G}) for all 10 -- its 8-mana reality is priced into its grade, not its eligibility. For `prepare` DFCs the front face is card_faces[0]. Lands are never deck spells; they enter only as fixers.
- Splash gate is LANDS ONLY (board ruling, DEC-926 CEO review): up to 2 cards of a single third colour at effective grade >= 7, allowed when the pool holds >= 2 lands that produce that colour -- the common duals, the rare slowlands, Room of Refuge. Basic-landcycling spells do NOT count as fixers: they are spells, they cost a deck slot, and they only fix when drawn. Splash cards are graded against the two-colour eligible set's synergy counts.
- `playables` counts the pair's available cards (eligible + any splash taken) at effective grade >= 4, not base grade; the same effective grade drives deck choice, score and the bomb count.
- A pool shorter than 23 eligible cards is padded to 23 at grade 1 so scores stay comparable.

## Per pair

| Pair | P(viable) | Mean score | P(best) | P(top 2) | Playables | Removal | Bombs | Splash |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| WU | 41.7% | 5.52 | 34.3% | 54.8% | 27.8 | 2.92 | 1.42 | 1.20 |
| UG | 22.0% | 5.43 | 17.1% | 35.7% | 26.5 | 2.16 | 1.30 | 1.31 |
| UB | 47.0% | 5.43 | 18.1% | 35.5% | 26.6 | 3.49 | 1.38 | 1.26 |
| UR | 47.9% | 5.31 | 5.5% | 14.6% | 27.0 | 3.55 | 1.38 | 1.33 |
| WG | 44.3% | 5.27 | 7.1% | 16.4% | 26.2 | 3.50 | 1.27 | 1.34 |
| WB | 58.5% | 5.25 | 5.6% | 14.3% | 26.6 | 4.94 | 1.35 | 1.44 |
| BG | 47.7% | 5.23 | 6.0% | 13.1% | 25.7 | 4.17 | 1.20 | 1.42 |
| WR | 60.4% | 5.15 | 2.5% | 6.9% | 27.0 | 4.93 | 1.35 | 1.41 |
| RG | 45.3% | 5.08 | 2.0% | 4.6% | 24.9 | 4.39 | 1.20 | 1.41 |
| BR | 54.9% | 5.07 | 1.7% | 4.0% | 25.5 | 5.40 | 1.27 | 1.45 |

P(at least one viable pair in the pool): **85.3%**. Mean pool size (basics excluded): 82.3 cards.

## Per colour (mean over the 4 pairs containing it)

| Colour | Mean playables | Mean removal in deck |
|---|---:|---:|
| W | 26.9 | 4.07 |
| U | 27.0 | 3.03 |
| B | 26.1 | 4.50 |
| R | 26.1 | 4.57 |
| G | 25.8 | 3.56 |

## Pool composition (grade-independent)

**Rares + mythics per pool** — mean 8.94

| Count | Share |
|---:|---:|
| 7 | 22.2% |
| 8 | 22.8% |
| 9 | 22.7% |
| 10 | 15.5% |
| 11 | 9.2% |
| 12 | 4.5% |
| 13 | 2.0% |
| 14 | 0.8% |
| 15 | 0.3% |
| 16 | 0.1% |

**Common dual lands per pool** — mean 3.26

| Count | Share |
|---:|---:|
| 0 | 0.9% |
| 1 | 6.5% |
| 2 | 19.2% |
| 3 | 30.4% |
| 4 | 27.2% |
| 5 | 13.2% |
| 6 | 2.6% |

## Per-pack sanity check

| Rarity | Simulated | Closed form | CEO target |
|---|---:|---:|---:|
| common | 6.741 | 6.739 | 6.710 |
| uncommon | 4.933 | 4.936 | 4.810 |
| rare_plus_mythic | 1.326 | 1.325 | 1.310 |
| dual_land | 0.542 | 0.545 | 0.545 |



---

# Reality Fracture Sealed pool simulation

`100,000` pools, seed `20260925`, 6 Play Boosters + 1 promo. Grades: **placeholder (flat grade 5)**.

## Assumptions

- Slot 6's 1.82% Special Guest is off-set and unusable in Sealed, so that slot always yields a main-set common.
- Slot 8's 3% 'other' folds into non-paired uncommon.
- Slots 9-11: the third echoed-pair card is drawn independently of the pair in slots 9-10 and may duplicate one of its halves.
- Slot 12's 10.8% booster-fun variants are still set rares/mythics, split proportionally (R 83.4% / M 16.6%).
- Slot 13 'full main set' means the 270-card main numbering, so the 10 common duals are not in the foil slot; the 2.8% residual is normalized away proportionally.
- Every slot's published weights are normalized to sum to 1. The published figures for slots 8, 9-11 and 13 sum to 0.97-0.972; the CEO's target of 4.81 uncommons per pack was computed without that normalization and is not reachable by any proper distribution. The normalized model gives ~4.94. Commons, rares+mythics and duals match the targets.
- Promo: one card uniform over the 64 main-set rares + 26 mythics (64/90 vs 26/90). FLAGGED - board to confirm from the pack.
- Basic lands are dropped from the pool (unlimited at the event).
- Eligibility is castability, not colour identity (DEC-927): every pip of the front-face mana cost must be payable by the pair. A hybrid pip {W/B} needs W or B; {2/W}, Phyrexian, generic, {X} and {C} are always payable. So Blessed Ghoul ({W/B}) is eligible for all 7 pairs containing W or B and Karn, Gilded Guardian ({2/W}{2/U}{2/B}{2/R}{2/G}) for all 10 -- its 8-mana reality is priced into its grade, not its eligibility. For `prepare` DFCs the front face is card_faces[0]. Lands are never deck spells; they enter only as fixers.
- Splash gate is LANDS ONLY (board ruling, DEC-926 CEO review): up to 2 cards of a single third colour at effective grade >= 7, allowed when the pool holds >= 2 lands that produce that colour -- the common duals, the rare slowlands, Room of Refuge. Basic-landcycling spells do NOT count as fixers: they are spells, they cost a deck slot, and they only fix when drawn. Splash cards are graded against the two-colour eligible set's synergy counts.
- `playables` counts the pair's available cards (eligible + any splash taken) at effective grade >= 4, not base grade; the same effective grade drives deck choice, score and the bomb count.
- A pool shorter than 23 eligible cards is padded to 23 at grade 1 so scores stay comparable.

## Per pair

| Pair | P(viable) | Mean score | P(best) | P(top 2) | Playables | Removal | Bombs | Splash |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| WR | 0.0% | 5.00 | 9.9% | 19.9% | 33.5 | 0.00 | 0.00 | 0.00 |
| UR | 0.0% | 5.00 | 10.1% | 20.2% | 33.6 | 0.00 | 0.00 | 0.00 |
| WB | 0.0% | 5.00 | 9.9% | 19.8% | 33.5 | 0.00 | 0.00 | 0.00 |
| WU | 0.0% | 5.00 | 10.1% | 20.1% | 33.3 | 0.00 | 0.00 | 0.00 |
| UG | 0.0% | 5.00 | 10.1% | 20.1% | 33.4 | 0.00 | 0.00 | 0.00 |
| BG | 0.0% | 5.00 | 10.0% | 20.2% | 33.2 | 0.00 | 0.00 | 0.00 |
| BR | 0.0% | 5.00 | 10.0% | 19.9% | 33.3 | 0.00 | 0.00 | 0.00 |
| UB | 0.0% | 5.00 | 10.0% | 20.0% | 33.3 | 0.00 | 0.00 | 0.00 |
| WG | 0.0% | 5.00 | 9.9% | 19.7% | 33.0 | 0.00 | 0.00 | 0.00 |
| RG | 0.0% | 5.00 | 10.0% | 20.0% | 33.1 | 0.00 | 0.00 | 0.00 |

P(at least one viable pair in the pool): **0.0%**. Mean pool size (basics excluded): 82.3 cards.

## Per colour (mean over the 4 pairs containing it)

| Colour | Mean playables | Mean removal in deck |
|---|---:|---:|
| W | 33.3 | 0.00 |
| U | 33.4 | 0.00 |
| B | 33.3 | 0.00 |
| R | 33.4 | 0.00 |
| G | 33.2 | 0.00 |

## Pool composition (grade-independent)

**Rares + mythics per pool** — mean 8.94

| Count | Share |
|---:|---:|
| 7 | 22.2% |
| 8 | 22.8% |
| 9 | 22.7% |
| 10 | 15.5% |
| 11 | 9.2% |
| 12 | 4.5% |
| 13 | 2.0% |
| 14 | 0.8% |
| 15 | 0.3% |
| 16 | 0.1% |

**Common dual lands per pool** — mean 3.26

| Count | Share |
|---:|---:|
| 0 | 0.9% |
| 1 | 6.5% |
| 2 | 19.2% |
| 3 | 30.4% |
| 4 | 27.2% |
| 5 | 13.2% |
| 6 | 2.6% |

## Per-pack sanity check

| Rarity | Simulated | Closed form | CEO target |
|---|---:|---:|---:|
| common | 6.741 | 6.739 | 6.710 |
| uncommon | 4.933 | 4.936 | 4.810 |
| rare_plus_mythic | 1.326 | 1.325 | 1.310 |
| dual_land | 0.542 | 0.545 | 0.545 |

