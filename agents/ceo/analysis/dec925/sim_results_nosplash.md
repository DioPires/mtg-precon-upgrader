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
- Splash is DISABLED in this run (lower bound): decks are strictly two colours.
- `playables` counts the pair's available cards (eligible + any splash taken) at effective grade >= 4, not base grade; the same effective grade drives deck choice, score and the bomb count.
- A pool shorter than 23 eligible cards is padded to 23 at grade 1 so scores stay comparable.

## Per pair

| Pair | P(viable) | Mean score | P(best) | P(top 2) | Playables | Removal | Bombs | Splash |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| WB | 44.1% | 5.24 | 12.9% | 24.9% | 28.2 | 5.54 | 0.67 | 0.00 |
| BR | 44.1% | 5.22 | 13.0% | 24.4% | 26.9 | 5.92 | 0.70 | 0.00 |
| UR | 30.3% | 5.21 | 10.4% | 21.3% | 27.4 | 3.68 | 0.58 | 0.00 |
| UB | 32.0% | 5.20 | 10.8% | 21.0% | 26.7 | 4.27 | 0.52 | 0.00 |
| WG | 38.2% | 5.19 | 12.0% | 21.6% | 28.9 | 3.79 | 0.77 | 0.00 |
| WU | 20.9% | 5.19 | 9.4% | 19.3% | 27.7 | 2.89 | 0.51 | 0.00 |
| WR | 41.8% | 5.18 | 9.4% | 19.2% | 28.7 | 4.95 | 0.67 | 0.00 |
| BG | 30.7% | 5.18 | 8.3% | 18.4% | 27.4 | 4.99 | 0.47 | 0.00 |
| UG | 13.7% | 5.16 | 7.5% | 16.5% | 27.7 | 2.65 | 0.34 | 0.00 |
| RG | 38.5% | 5.11 | 6.2% | 13.2% | 27.7 | 4.58 | 0.64 | 0.00 |

P(at least one viable pair in the pool): **83.4%**. Mean pool size (basics excluded): 82.3 cards.

## Per colour (mean over the 4 pairs containing it)

| Colour | Mean playables | Mean removal in deck |
|---|---:|---:|
| W | 28.4 | 4.30 |
| U | 27.4 | 3.37 |
| B | 27.3 | 5.18 |
| R | 27.7 | 4.78 |
| G | 27.9 | 4.00 |

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
- Splash is DISABLED in this run (lower bound): decks are strictly two colours.
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

