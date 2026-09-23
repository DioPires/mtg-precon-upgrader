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
| UR | 38.9% | 5.19 | 11.6% | 23.2% | 28.8 | 5.24 | 0.58 | 0.00 |
| BR | 47.4% | 5.18 | 12.5% | 23.6% | 28.0 | 7.50 | 0.70 | 0.00 |
| WB | 46.3% | 5.18 | 11.6% | 22.8% | 29.3 | 6.20 | 0.67 | 0.00 |
| WR | 45.9% | 5.17 | 11.0% | 22.0% | 29.3 | 6.50 | 0.67 | 0.00 |
| WG | 44.7% | 5.17 | 13.1% | 23.5% | 29.4 | 4.61 | 0.77 | 0.00 |
| WU | 27.3% | 5.15 | 9.5% | 19.4% | 29.1 | 3.56 | 0.51 | 0.00 |
| UG | 19.2% | 5.13 | 7.8% | 17.1% | 29.2 | 3.43 | 0.35 | 0.00 |
| BG | 33.4% | 5.13 | 7.6% | 16.7% | 28.6 | 5.81 | 0.47 | 0.00 |
| UB | 36.9% | 5.12 | 7.8% | 16.3% | 28.7 | 4.97 | 0.53 | 0.00 |
| RG | 44.4% | 5.10 | 7.4% | 15.3% | 28.4 | 6.35 | 0.65 | 0.00 |

P(at least one viable pair in the pool): **85.0%**. Mean pool size (basics excluded): 81.6 cards.

## Per colour (mean over the 4 pairs containing it)

| Colour | Mean playables | Mean removal in deck |
|---|---:|---:|
| W | 29.3 | 5.22 |
| U | 28.9 | 4.30 |
| B | 28.7 | 6.12 |
| R | 28.6 | 6.40 |
| G | 28.9 | 5.05 |

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

