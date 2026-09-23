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
| WG | 73.8% | 5.38 | 13.1% | 24.5% | 28.5 | 5.53 | 1.69 | 1.95 |
| RG | 66.9% | 5.38 | 14.3% | 25.7% | 27.4 | 7.33 | 1.31 | 1.92 |
| WU | 64.2% | 5.37 | 11.5% | 22.8% | 28.7 | 4.30 | 1.53 | 1.95 |
| WR | 73.4% | 5.37 | 11.3% | 22.5% | 27.7 | 7.25 | 1.56 | 1.91 |
| WB | 74.4% | 5.37 | 10.3% | 21.3% | 27.9 | 6.64 | 1.64 | 1.93 |
| UB | 65.1% | 5.37 | 13.8% | 24.4% | 27.3 | 5.64 | 1.37 | 1.94 |
| BR | 65.9% | 5.32 | 8.3% | 17.5% | 27.0 | 8.14 | 1.33 | 1.87 |
| UR | 64.2% | 5.30 | 6.4% | 14.8% | 26.8 | 6.09 | 1.34 | 1.93 |
| BG | 69.3% | 5.30 | 6.2% | 14.6% | 27.1 | 6.51 | 1.48 | 1.95 |
| UG | 57.9% | 5.27 | 4.9% | 11.8% | 27.2 | 4.30 | 1.40 | 1.96 |

P(at least one viable pair in the pool): **86.8%**. Mean pool size (basics excluded): 81.6 cards.

## Per colour (mean over the 4 pairs containing it)

| Colour | Mean playables | Mean removal in deck |
|---|---:|---:|
| W | 28.2 | 5.93 |
| U | 27.5 | 5.08 |
| B | 27.3 | 6.73 |
| R | 27.2 | 7.20 |
| G | 27.6 | 5.92 |

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
- Card colours come from Scryfall's top-level `colors`, i.e. the front face. Every card in the set whose colour identity is wider than that has a hybrid back face, so front-face colours are the correct castability set.
- Splash: up to 2 cards of a single third colour, effective grade >= 7, allowed when the pool holds >= 2 fixers for that colour. A fixer is any land in the pool that can produce it (the common duals, the rare slowlands, Room of Refuge) or any basic-landcycling card. Splash cards are graded against the two-colour eligible set's synergy counts.
- `playables` counts the pair's available cards (eligible + any splash taken) at effective grade >= 4, not base grade; the same effective grade drives deck choice, score and the bomb count.
- A pool shorter than 23 eligible cards is padded to 23 at grade 1 so scores stay comparable.

## Per pair

| Pair | P(viable) | Mean score | P(best) | P(top 2) | Playables | Removal | Bombs | Splash |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| BR | 0.0% | 4.98 | 10.0% | 20.1% | 29.3 | 0.00 | 0.00 | 0.00 |
| WU | 0.0% | 4.98 | 10.1% | 20.1% | 29.2 | 0.00 | 0.00 | 0.00 |
| UB | 0.0% | 4.98 | 10.2% | 20.1% | 29.2 | 0.00 | 0.00 | 0.00 |
| WR | 0.0% | 4.98 | 9.9% | 20.0% | 29.0 | 0.00 | 0.00 | 0.00 |
| WG | 0.0% | 4.98 | 9.8% | 20.0% | 29.0 | 0.00 | 0.00 | 0.00 |
| UR | 0.0% | 4.98 | 10.0% | 19.9% | 29.0 | 0.00 | 0.00 | 0.00 |
| RG | 0.0% | 4.98 | 10.1% | 20.0% | 29.0 | 0.00 | 0.00 | 0.00 |
| WB | 0.0% | 4.97 | 10.1% | 20.1% | 28.8 | 0.00 | 0.00 | 0.00 |
| UG | 0.0% | 4.97 | 9.9% | 19.7% | 28.8 | 0.00 | 0.00 | 0.00 |
| BG | 0.0% | 4.97 | 10.0% | 20.0% | 28.6 | 0.00 | 0.00 | 0.00 |

P(at least one viable pair in the pool): **0.0%**. Mean pool size (basics excluded): 81.6 cards.

## Per colour (mean over the 4 pairs containing it)

| Colour | Mean playables | Mean removal in deck |
|---|---:|---:|
| W | 29.0 | 0.00 |
| U | 29.0 | 0.00 |
| B | 29.0 | 0.00 |
| R | 29.1 | 0.00 |
| G | 28.8 | 0.00 |

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

