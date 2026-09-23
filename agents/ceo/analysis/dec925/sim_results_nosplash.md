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
- Card colours come from Scryfall's top-level `colors`, i.e. the front face. Every card in the set whose colour identity is wider than that has a hybrid back face, so front-face colours are the correct castability set.
- Splash: up to 2 cards of a single third colour, effective grade >= 7, allowed when the pool holds >= 2 fixers for that colour. A fixer is any land in the pool that can produce it (the common duals, the rare slowlands, Room of Refuge) or any basic-landcycling card. Splash cards are graded against the two-colour eligible set's synergy counts.
- `playables` counts the pair's available cards (eligible + any splash taken) at effective grade >= 4, not base grade; the same effective grade drives deck choice, score and the bomb count.
- A pool shorter than 23 eligible cards is padded to 23 at grade 1 so scores stay comparable.

## Per pair

| Pair | P(viable) | Mean score | P(best) | P(top 2) | Playables | Removal | Bombs | Splash |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| RG | 38.6% | 5.06 | 14.7% | 26.3% | 25.5 | 6.64 | 0.65 | 0.00 |
| WG | 41.8% | 5.06 | 13.3% | 24.2% | 26.6 | 4.96 | 0.76 | 0.00 |
| WU | 25.9% | 5.05 | 11.0% | 22.1% | 26.7 | 3.65 | 0.50 | 0.00 |
| UB | 31.5% | 5.05 | 13.9% | 24.7% | 25.3 | 5.10 | 0.53 | 0.00 |
| WR | 39.1% | 5.05 | 10.9% | 22.0% | 25.8 | 6.73 | 0.65 | 0.00 |
| WB | 39.8% | 5.04 | 10.0% | 20.6% | 26.0 | 6.44 | 0.66 | 0.00 |
| BR | 39.8% | 5.02 | 9.5% | 19.8% | 25.2 | 7.69 | 0.70 | 0.00 |
| UR | 32.1% | 4.99 | 6.6% | 15.5% | 24.9 | 5.42 | 0.58 | 0.00 |
| BG | 28.2% | 4.96 | 5.6% | 13.6% | 25.2 | 6.20 | 0.47 | 0.00 |
| UG | 17.9% | 4.93 | 4.4% | 11.1% | 25.2 | 3.82 | 0.35 | 0.00 |

P(at least one viable pair in the pool): **83.7%**. Mean pool size (basics excluded): 81.6 cards.

## Per colour (mean over the 4 pairs containing it)

| Colour | Mean playables | Mean removal in deck |
|---|---:|---:|
| W | 26.3 | 5.45 |
| U | 25.5 | 4.50 |
| B | 25.4 | 6.36 |
| R | 25.3 | 6.62 |
| G | 25.6 | 5.41 |

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

