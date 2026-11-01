# DEC-925 back-test against 17Lands (FRA, fetched 2026-11-01)

Card metric: Premier Draft GIH WR (win rate in games where the card was drawn or in the opening hand), published for 113 of 290 cards. 17Lands' public card endpoint returns a sample (median 380 games a card) and withholds the win rate below its own floor, so it covers 65 commons and 48 uncommons and no rare or mythic. At 400 games one card's GIH WR carries about +/-2.5 points of noise. Sealed card data is not published (23 games in total). The comparison is therefore about commons and uncommons only.

## 1. Card grades against GIH WR

| Grade set | Cards matched | Spearman | Pearson |
|---|---:|---:|---:|
| v1 blind | 103 | 0.11 | 0.11 |
| v2 after Draftsim | 103 | 0.13 | 0.14 |
| v3 final | 103 | 0.14 | 0.14 |
| Draftsim | 103 | 0.33 | 0.37 |

Same card set for every row (cards graded by all four and over the game floor).

Noise ceiling: observed GIH WR spread SD 2.62 points, sampling noise SD 1.62. A perfect grade list would correlate at about 0.78, not 1.0.

Draftsim against v3 on the same 103 cards (rank correlations): Draftsim 0.33, v3 0.14, the two grade lists with each other 0.57. Meng-Rosenthal-Rubin z for the difference: 2.19 (above 1.96 means the gap is unlikely to be noise).

### Overrated by v3 (GIH percentile 50+ below our grade's percentile)

| Card | Rarity | v3 grade | Draftsim | GIH WR | Games | v3 percentile | GIH percentile | Roles |
|---|---|---:|---:|---:|---:|---:|---:|---|
| Prophesied End | U | 7 | 5 | 49.2% | 590 | 93 | 1 | removal |
| Theorix Charm | U | 7 | 4 | 52.5% | 848 | 93 | 16 | removal, trick |
| Fulminous Forte | U | 7 | 7 | 52.8% | 846 | 93 | 19 | removal |
| Silence the Echo | C | 6 | 4 | 50.8% | 992 | 77 | 4 | removal |
| Mind Meanderer | U | 7 | 7 | 53.4% | 828 | 93 | 27 | removal, threat |
| No Admittance | C | 7 | 5 | 53.7% | 1731 | 93 | 34 | removal |
| Clash of Elements | U | 6 | 6 | 53.1% | 815 | 77 | 23 | removal |
| Wrath of the Bloodmane | C | 7 | 5 | 53.9% | 1659 | 93 | 40 | removal |
| Last Gasp | C | 7 | 6 | 53.9% | 1754 | 93 | 41 | removal |
| Ruric Thar, Biomagus | U | 6 | 4 | 53.4% | 785 | 77 | 26 | threat |
| Prudent Fateseer | U | 5 | 4 | 51.1% | 856 | 56 | 6 | threat |

### Underrated by v3 (GIH percentile 50+ above our grade's percentile)

| Card | Rarity | v3 grade | Draftsim | GIH WR | Games | v3 percentile | GIH percentile | Roles |
|---|---|---:|---:|---:|---:|---:|---:|---|
| Sphinx's Approach | C | 3 | 2 | 57.0% | 1164 | 4 | 80 | engine |
| Fblthp, Impossibly Lost | U | 4 | 4 | 61.9% | 1500 | 26 | 100 | engine |
| Countersculpt | U | 4 | 4 | 59.8% | 1320 | 26 | 96 | trick |
| Fblthp, Knows the Way | U | 4 | 6 | 58.6% | 918 | 26 | 94 | threat |
| Teyo, Lightshield Expert | U | 4 | 6 | 58.4% | 615 | 26 | 91 | trick |
| Rewrite Regrets | U | 4 | 3 | 58.3% | 1069 | 26 | 90 | engine |
| Tetsuko Umezawa, Fugitive | U | 3 | 5 | 55.1% | 624 | 4 | 61 | threat |
| Generous Revival | U | 4 | 2 | 56.5% | 637 | 26 | 79 | engine |
| Something Worth Saving | C | 4 | 4 | 56.3% | 1245 | 26 | 77 | engine |
| Vigorbloom Vanguard | U | 4 | 3 | 56.3% | 700 | 26 | 76 | threat |

Mean gap (GIH percentile minus v3 percentile) by role; negative means we graded the role too high:

| Role | Cards | Mean gap |
|---|---:|---:|
| removal | 24 | -34 |
| threat | 56 | -1 |
| trick | 7 | +19 |
| fixing | 2 | +22 |
| engine | 19 | +26 |

## 2. Removal and colour depth

Mean GIH WR of commons and uncommons, mono-coloured, by colour, and of the removal-tagged ones:

| Colour | C+U cards | Mean GIH WR | Removal cards | Removal mean GIH WR |
|---|---:|---:|---:|---:|
| W | 13 | 55.0% | 4 | 54.2% |
| U | 21 | 55.7% | 2 | 56.2% |
| B | 14 | 54.6% | 5 | 55.3% |
| R | 10 | 54.0% | 5 | 54.6% |
| G | 16 | 53.6% | 2 | 52.6% |

## 3. Pair ranking against Arena Sealed results

17Lands two-colour decks, splash decks folded into their pair. Share = the pair's games over all two-colour games; it is the nearest observed analogue of P(best). SE is the binomial standard error of the win rate.

| Pair | Our tier | P(best) | P(viable) | Sealed WR | SE | Sealed share | Premier Draft WR |
|---|---:|---:|---:|---:|---:|---:|---:|
| WU | 2 | 10.1% | 50.1% | 58.9% | 0.6 | 14.2% | 56.3% |
| UB | 2 | 10.4% | 57.1% | 58.3% | 0.6 | 15.0% | 55.4% |
| BG | 2 | 9.2% | 62.6% | 57.9% | 0.8 | 9.1% | 54.8% |
| WR | 2 | 9.7% | 67.9% | 57.2% | 1.0 | 5.8% | 53.2% |
| UR | 2 | 10.4% | 55.2% | 57.0% | 0.8 | 9.5% | 55.1% |
| UG | 3 | 7.9% | 43.1% | 56.4% | 0.9 | 6.0% | 52.5% |
| WB | 1 | 13.6% | 69.2% | 55.8% | 1.0 | 6.0% | 53.6% |
| BR | 2 | 11.5% | 62.6% | 55.6% | 0.8 | 9.4% | 53.8% |
| WG | 2 | 11.2% | 63.7% | 55.5% | 0.7 | 11.7% | 53.8% |
| RG | 3 | 5.9% | 61.0% | 55.4% | 0.6 | 13.3% | 55.2% |

- Spearman of P(best) with Sealed WR: -0.09; with Sealed share: -0.01.
- Spearman of P(viable) with Sealed WR: -0.37; with Sealed share: -0.48.
- Spearman of mean score with Sealed WR: 0.08; with Sealed share: -0.01.
- Same sim, Draftsim grades + 1 in place of ours (`sim_draftsim_grades.md`, same seed and roles): Spearman of P(best) with Sealed WR -0.42, with share -0.20; of mean score with Sealed WR -0.32.
  P(best) under Draftsim grades: BG 13.5%, RG 12.9%, UR 12.1%, UG 11.2%, WG 11.1%, BR 10.8%, WR 9.5%, WB 6.8%, WU 6.6%, UB 5.5%.
- Spearman of Sealed WR with Premier Draft WR: 0.37.

By colour (the four pairs that hold it, games-weighted): U 58.0%, B 57.2%, W 57.1%, G 56.2%, R 56.1%.

## 4. Limits of this check

- One set. Read the direction and size of each gap, not a rule.
- Card data is Premier Draft, not Sealed, and covers commons and uncommons only; the public endpoint returns a recent sample and ignores date parameters.
- GIH WR credits cards in the strongest decks: blue won most in this format, so blue cards look better, and that is part of the engine gap.
- Sealed WR is the result of decks that Arena players built; P(best) is a statement about pools. Share is the nearer analogue, and it does not match either.
- Arena Sealed is mostly best-of-one and 17Lands users play above the average. A paper prerelease differs on both.
