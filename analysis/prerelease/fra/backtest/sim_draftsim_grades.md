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
| UR | 69.1% | 5.88 | 12.1% | 24.1% | 27.1 | 4.14 | 2.96 | 1.77 |
| BG | 71.8% | 5.87 | 13.5% | 25.4% | 25.9 | 5.14 | 3.11 | 1.76 |
| RG | 63.5% | 5.87 | 12.9% | 24.3% | 25.1 | 4.49 | 3.56 | 1.76 |
| UG | 45.5% | 5.86 | 11.2% | 22.9% | 26.2 | 2.83 | 3.15 | 1.77 |
| BR | 82.1% | 5.86 | 10.8% | 21.6% | 27.1 | 6.38 | 2.90 | 1.75 |
| WR | 82.0% | 5.84 | 9.5% | 19.7% | 27.8 | 5.47 | 2.99 | 1.77 |
| WG | 65.2% | 5.83 | 11.1% | 21.4% | 25.5 | 4.33 | 3.37 | 1.76 |
| WB | 79.8% | 5.76 | 6.8% | 14.2% | 26.9 | 6.26 | 2.64 | 1.76 |
| UB | 72.7% | 5.75 | 5.5% | 12.7% | 26.7 | 4.93 | 2.45 | 1.77 |
| WU | 61.0% | 5.73 | 6.6% | 13.6% | 27.1 | 3.54 | 2.94 | 1.77 |

P(at least one viable pair in the pool): **99.6%**. Mean pool size (basics excluded): 82.3 cards.

## Per colour (mean over the 4 pairs containing it)

| Colour | Mean playables | Mean removal in deck |
|---|---:|---:|
| W | 26.8 | 4.90 |
| U | 26.8 | 3.86 |
| B | 26.6 | 5.68 |
| R | 26.8 | 5.12 |
| G | 25.7 | 4.20 |

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

