## Final report: what the set makes likely, and how to use it on the day

**Answer to the question you asked.** No two-colour pair is a pre-commit. On 100,000 simulated 6-booster pools, the best pair's mean deck score ranges only from 5.32 (RG) to 5.40 (UR, WB, WG), and no pair is the best build of more than 12.8% of pools. What the set does make likely: a white pair is the best build in 46% of pools, a green pair in 37%; red and black pairs carry the removal; blue pairs are removal-poor. Your pool decides the rest, and the cheat sheet's hand procedure is how you read it in ten minutes.

**Deliverables** (all on `main`, folder `agents/ceo/analysis/dec925/`):

- `cheat_sheet.md`: scoring procedure, format rules, removal and tricks per colour, the ranking below, the full graded list. Open it on your phone from GitHub.
- `grades.json` and `grade_review_log.md`: 280 blind Sealed grades, Draftsim comparison, 48 disagreements adjudicated.
- `sim_results.md`: the headline run. `sim_results_spec_splash.md` and `sim_results_nosplash.md` give the range. `scripts/sealed_sim.py` reruns any of them in about 20 seconds (`--pools 100000 --seed 20260925`).
- `notes.md`: every verified fact and every assumption, with sources.

### Ranking (headline run: hybrid castability, splash gated on lands only, CEO grades)

| Pair | P(best) | P(viable) | Mean score | Removal in deck | Bombs |
|---|---:|---:|---:|---:|---:|
| WG | 12.8% | 65.9% | 5.40 | 5.1 | 1.33 |
| WB | 11.9% | 68.8% | 5.40 | 6.4 | 1.27 |
| WR | 11.5% | 68.9% | 5.39 | 6.9 | 1.24 |
| UR | 11.3% | 61.1% | 5.40 | 5.8 | 1.05 |
| BR | 11.0% | 63.7% | 5.38 | 7.8 | 1.08 |
| WU | 10.1% | 54.5% | 5.38 | 4.1 | 1.15 |
| BG | 8.5% | 62.4% | 5.36 | 6.2 | 1.11 |
| UG | 8.2% | 48.2% | 5.37 | 4.0 | 1.01 |
| UB | 7.6% | 59.7% | 5.34 | 5.5 | 1.04 |
| RG | 7.2% | 63.4% | 5.32 | 6.9 | 1.08 |

P(viable) = the pool holds 23 playables at grade 4 or higher, 3 removal spells and one card at grade 8 or higher for that pair, allowing a 2-card splash when 2 lands in the pool make the third colour. At least one pair is viable in 86.6% of pools. Every pool averages 9.0 rares or mythics and 2.6 common duals.

**By colour** (sum of P(best) over the four pairs holding the colour): W 46%, R 41%, B 39%, U 37%, G 37%. Removal per deck by colour: R 6.9, B 6.5, W 5.6, G 5.6, U 4.8. The removal order R > B > W > G > U survived every model change and matches limitedmtg's independent count.

### What moved the numbers, and what did not

- **The castability fix (DEC-927) reordered the table.** With eligibility on Scryfall's colour field, each hybrid card belonged to one pair and Karn was castable nowhere. RG and UB were the top two by P(best) under that rule and are the bottom two now. This was a spec error of mine, caught in review.
- **The splash gate (lands only, not landcyclers) moved levels, not order.** P(viable) fell about 11 points per pair; the largest P(best) move was 0.4 points. The range columns in the cheat sheet show both gates.
- **My grades drive the ranking.** Blind grades correlate 0.79 with Draftsim after review; the 15 residual disagreements are logged with reasons. Different grades would move P(best) by a few points, not the colour-level picture.

### Where the model stops

- It scores a 23 by mean grade. It does not play games, so it ignores curve, tempo, and how the Jace token actually performs in play. Both external reviews call Empower Jace the format's engine; the model only credits it through synergy grades.
- The promo is modelled as one uniform rare or mythic. Confirm from the pack; it is one card in 82.
- Two-Headed Giant and casual REL are out of scope.
- Draft archetype write-ups rank BR first for Draft. In Sealed the evidence points to white depth plus black or red removal, with BR the deepest removal pair but the thinnest on playables.

### On the day

1. Run section 1 of the cheat sheet on the pool.
2. Count black and red removal first. Three or more usually means WB, WR or BR.
3. Count white playables. White is the most likely main colour in this set.
4. Take a blue pair only when the pool gives it removal (Infinite Coursework, Plan for All Outcomes, the charms) or a bomb.
5. Splash only off lands. Landcyclers are flood insurance, not fixing.

### Process record

The process we ran, for reuse on the next set: verify the set on Scryfall; pull the collation from WotC and a second source; grade blind from oracle text; compare to two external reviews and log disagreements; simulate pools with the collation and grades; review the sim against the spec and fix rule errors before ranking; ship a phone-readable cheat sheet with a hand procedure. The simulator is set-agnostic (`--config`), so the next prerelease needs a new collation file and a new grade file only.

planned-by: CEO / executed-by: Simulation Engineer (DEC-926, DEC-927); card grades and report by CEO (DEC-461)
