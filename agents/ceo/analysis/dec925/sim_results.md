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
| UR | 61.1% | 5.40 | 11.3% | 22.8% | 30.2 | 5.81 | 1.05 | 1.46 |
| WB | 68.8% | 5.40 | 11.9% | 23.1% | 30.8 | 6.42 | 1.27 | 1.44 |
| WG | 65.9% | 5.40 | 12.8% | 23.4% | 30.9 | 5.12 | 1.33 | 1.48 |
| WR | 68.9% | 5.39 | 11.5% | 22.2% | 30.7 | 6.88 | 1.24 | 1.41 |
| WU | 54.5% | 5.38 | 10.1% | 20.4% | 30.6 | 4.12 | 1.15 | 1.49 |
| BR | 63.7% | 5.38 | 11.0% | 21.0% | 29.4 | 7.85 | 1.08 | 1.32 |
| UG | 48.2% | 5.37 | 8.2% | 18.0% | 30.7 | 3.96 | 1.01 | 1.53 |
| BG | 62.4% | 5.36 | 8.5% | 18.2% | 30.1 | 6.19 | 1.11 | 1.51 |
| UB | 59.7% | 5.34 | 7.6% | 15.9% | 30.2 | 5.49 | 1.04 | 1.47 |
| RG | 63.4% | 5.32 | 7.2% | 15.0% | 29.8 | 6.94 | 1.08 | 1.42 |

P(at least one viable pair in the pool): **86.6%**. Mean pool size (basics excluded): 81.6 cards.

## Per colour (mean over the 4 pairs containing it)

| Colour | Mean playables | Mean removal in deck |
|---|---:|---:|
| W | 30.7 | 5.64 |
| U | 30.4 | 4.84 |
| B | 30.1 | 6.49 |
| R | 30.0 | 6.87 |
| G | 30.4 | 5.55 |

## Pool composition (grade-independent)

**Rares + mythics per pool** — mean 8.96

| Count | Share |
|---:|---:|
| 7 | 22.0% |
| 8 | 22.5% |
| 9 | 22.8% |
| 10 | 15.6% |
| 11 | 9.1% |
| 12 | 4.6% |
| 13 | 2.0% |
| 14 | 0.8% |
| 15 | 0.3% |
| 16 | 0.1% |

**Common dual lands per pool** — mean 2.61

| Count | Share |
|---:|---:|
| 0 | 3.2% |
| 1 | 15.0% |
| 2 | 28.8% |
| 3 | 29.9% |
| 4 | 17.1% |
| 5 | 5.3% |
| 6 | 0.7% |

## Per-pack sanity check

| Rarity | Simulated | Closed form | CEO target |
|---|---:|---:|---:|
| common | 6.742 | 6.739 | 6.710 |
| uncommon | 4.942 | 4.936 | 4.810 |
| rare_plus_mythic | 1.316 | 1.325 | 1.310 |
| dual_land | 0.436 | 0.436 | 0.436 |



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
| UR | 0.0% | 5.00 | 10.0% | 19.9% | 33.6 | 0.00 | 0.00 | 0.00 |
| WR | 0.0% | 5.00 | 9.9% | 20.0% | 33.6 | 0.00 | 0.00 | 0.00 |
| UG | 0.0% | 5.00 | 10.0% | 19.9% | 33.4 | 0.00 | 0.00 | 0.00 |
| WB | 0.0% | 5.00 | 10.2% | 20.2% | 33.4 | 0.00 | 0.00 | 0.00 |
| BR | 0.0% | 5.00 | 9.9% | 19.9% | 33.3 | 0.00 | 0.00 | 0.00 |
| BG | 0.0% | 5.00 | 10.1% | 20.2% | 33.2 | 0.00 | 0.00 | 0.00 |
| WU | 0.0% | 5.00 | 10.0% | 19.9% | 33.2 | 0.00 | 0.00 | 0.00 |
| UB | 0.0% | 5.00 | 10.1% | 20.0% | 33.2 | 0.00 | 0.00 | 0.00 |
| WG | 0.0% | 5.00 | 9.8% | 19.8% | 33.0 | 0.00 | 0.00 | 0.00 |
| RG | 0.0% | 5.00 | 10.0% | 20.0% | 33.1 | 0.00 | 0.00 | 0.00 |

P(at least one viable pair in the pool): **0.0%**. Mean pool size (basics excluded): 81.6 cards.

## Per colour (mean over the 4 pairs containing it)

| Colour | Mean playables | Mean removal in deck |
|---|---:|---:|
| W | 33.3 | 0.00 |
| U | 33.4 | 0.00 |
| B | 33.3 | 0.00 |
| R | 33.4 | 0.00 |
| G | 33.2 | 0.00 |

## Pool composition (grade-independent)

**Rares + mythics per pool** — mean 8.96

| Count | Share |
|---:|---:|
| 7 | 22.0% |
| 8 | 22.5% |
| 9 | 22.8% |
| 10 | 15.6% |
| 11 | 9.1% |
| 12 | 4.6% |
| 13 | 2.0% |
| 14 | 0.8% |
| 15 | 0.3% |
| 16 | 0.1% |

**Common dual lands per pool** — mean 2.61

| Count | Share |
|---:|---:|
| 0 | 3.2% |
| 1 | 15.0% |
| 2 | 28.8% |
| 3 | 29.9% |
| 4 | 17.1% |
| 5 | 5.3% |
| 6 | 0.7% |

## Per-pack sanity check

| Rarity | Simulated | Closed form | CEO target |
|---|---:|---:|---:|
| common | 6.742 | 6.739 | 6.710 |
| uncommon | 4.942 | 4.936 | 4.810 |
| rare_plus_mythic | 1.316 | 1.325 | 1.310 |
| dual_land | 0.436 | 0.436 | 0.436 |

