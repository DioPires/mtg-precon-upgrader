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
| WR | 55.2% | 5.35 | 14.6% | 27.4% | 29.3 | 5.70 | 0.90 | 1.52 |
| BR | 57.3% | 5.32 | 13.5% | 25.0% | 27.7 | 6.54 | 0.99 | 1.45 |
| UR | 49.6% | 5.30 | 10.3% | 21.4% | 28.6 | 4.57 | 0.91 | 1.63 |
| WG | 48.9% | 5.30 | 11.5% | 22.4% | 29.4 | 4.71 | 0.85 | 1.64 |
| WB | 55.8% | 5.30 | 11.4% | 22.2% | 28.4 | 6.13 | 0.93 | 1.54 |
| RG | 54.0% | 5.29 | 9.5% | 19.2% | 28.9 | 5.58 | 0.90 | 1.57 |
| BG | 55.0% | 5.27 | 8.4% | 18.0% | 28.3 | 5.74 | 0.95 | 1.65 |
| WU | 42.3% | 5.25 | 8.0% | 16.5% | 28.4 | 3.88 | 0.84 | 1.64 |
| UG | 39.9% | 5.23 | 6.2% | 13.8% | 28.9 | 3.59 | 0.87 | 1.69 |
| UB | 51.5% | 5.22 | 6.6% | 14.0% | 27.6 | 4.99 | 0.95 | 1.61 |

P(at least one viable pair in the pool): **75.3%**. Mean pool size (basics excluded): 82.3 cards.

## Per colour (mean over the 4 pairs containing it)

| Colour | Mean playables | Mean removal in deck |
|---|---:|---:|
| W | 28.9 | 5.11 |
| U | 28.4 | 4.26 |
| B | 28.0 | 5.85 |
| R | 28.7 | 5.60 |
| G | 28.9 | 4.91 |

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

