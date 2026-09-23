## Final report (revised after the 2026-09-23 self-review): what the set makes likely, and how to use it on the day

**Answer to the question you asked.** No two-colour pair is a pre-commit. On 100,000 simulated 6-booster pools, the best pair's mean deck score ranges only from 5.35 (RG) to 5.49 (WB), and no pair is the best build of more than 13.6% of pools. What the set does make likely: a white or black pair is the best build in about 45% of pools each (they overlap in WB), green pairs in 34%; black and red have the most removal cards, white has fewer but its common and uncommon removal is the best-graded in the set, and blue pairs are removal-poor. Your pool decides the rest, and the cheat sheet's hand procedure is how you read it in ten minutes.

**Deliverables** (all on `main`, folder `agents/ceo/analysis/dec925/`):

- `cheat_sheet.md`: scoring procedure, format rules, removal and tricks per colour, the ranking below, the full graded list. Open it on your phone from GitHub.
- `grades.json` and `grade_review_log.md`: 280 Sealed grades graded blind, then checked against Draftsim (full set) and Limited Resources 872 (commons and uncommons); every change logged with its reason.
- `sim_results.md`: the headline run. `sim_results_spec_splash.md` and `sim_results_nosplash.md` give the range. `scripts/sealed_sim.py` reruns any of them in about 20 seconds.
- `notes.md`: every verified fact, every assumption, and the corrections made in review, with sources.

### Ranking (headline run: pip castability, splash gated on lands only, dual rate 54.5%, grades v3)

| Pair | P(best) | P(viable) | Mean score | Removal in deck | Bombs |
|---|---:|---:|---:|---:|---:|
| WB | 13.6% | 69.2% | 5.49 | 5.9 | 1.35 |
| BR | 11.5% | 62.6% | 5.45 | 6.4 | 1.13 |
| WG | 11.2% | 63.7% | 5.45 | 4.5 | 1.41 |
| UB | 10.4% | 57.1% | 5.44 | 4.9 | 1.11 |
| UR | 10.4% | 55.2% | 5.45 | 4.4 | 1.11 |
| WU | 10.1% | 50.1% | 5.45 | 3.6 | 1.24 |
| WR | 9.7% | 67.9% | 5.43 | 5.5 | 1.32 |
| BG | 9.2% | 62.6% | 5.44 | 5.5 | 1.19 |
| UG | 7.9% | 43.1% | 5.42 | 3.4 | 1.10 |
| RG | 5.9% | 61.0% | 5.35 | 5.4 | 1.13 |

P(viable) = the pool holds 23 playables at grade 4 or higher, 3 removal spells and one card at grade 8 or higher for that pair, allowing a 2-card splash when 2 lands in the pool make the third colour. At least one pair is viable in 86.6% of pools. Every pool averages 8.9 rares or mythics and 3.3 common duals.

**Read P(best) as tiers, not an order.** In review, one-point changes on a dozen grades and one collation fix moved pairs by up to 2 points and reordered the middle of the table. Tier 1: WB. Tier 2: BR, WG, UB, UR, WU, WR (9.7% to 11.5%, inside grade noise). Tier 3: BG, UG, RG. Stable across every version of the model: white pairs have the highest P(viable), UG and WU the lowest, RG the lowest P(best), and at least one viable pair exists in about 87% of pools.

**By colour** (sum of P(best) over the four pairs holding the colour): B 45%, W 45%, U 39%, R 38%, G 34%. Removal cards by colour (creature or planeswalker answers only; common / uncommon / rare+mythic): B 3/4/5, R 3/3/2, W 2/3/2, G 2/2/0, U 1/1/0. White's five common and uncommon removal spells average grade 6.0 against red's 6.3 and black's 5.9, so white is short on count, not quality.

### What the self-review found and fixed (2026-09-23)

- **Dual-land rate was wrong: 43.6% was the non-foil duals only.** WotC's land slot lists common duals at 43.6% non-foil plus 10.9% foil, so the rate is 54.5%. An independent collation model (magic-search-engine, PR #636) agrees at 30/55. Duals per pool rose from 2.6 to 3.3, which loosens the splash gate for every pair.
- **Five cards were counted as removal that do not answer creatures**: Tether Technician (2 damage), Way of the Warlord (one 2-damage shot), Budding Insurgent and Archive Arbiter (noncreature permanents only), Living Library (6-mana shuffle). Tags removed, grades kept. Red pairs lost about one removal spell per deck in the model.
- **Twelve grades moved one point** after checking Limited Resources 872 (Perfected Theory, Sphinx's Approach, Rampart Hunter and Yargle down; Extended Absence, Thalia, Loot the Nexus, Break Under Pressure, Theorix Charm, Mindseeker Oculus, Massacre Girl up; Living Library down and untagged). Logged in `grade_review_log.md`.
- **Cheat sheet fixes**: the hand procedure used two different playable thresholds (5 in step 2, 4 in step 4); now 4 throughout, with a 6-or-higher count as the quality tiebreak. The "3 damage kills 68%" line was a quote; it is now counted from the card file (68% of creatures have toughness 3 or less, 48% 2 or less). The tricks list dropped pure draw and regrowth instants. Three card notes corrected (Countersculpt cost, Graft Surgeon size, Ajani Unrelenting's -3 hits your non-token creatures too).
- **Verified and unchanged**: set size and preview status (Scryfall), every other collation slot (WotC verbatim text and the PR model agree), the 43-pair echoed-pair table (the PR pairs Jace with Tam the same way), per-pack expectations, the castability rule, mechanic counts. Scryfall has no rulings yet for `prepared` or `empower Jace`; the cheat sheet relies on the printed reminder text.

### Effect of the corrections on the ranking

P(best) before and after: WB 11.9 to 13.6, BR 11.0 to 11.5, WG 12.8 to 11.2, UB 7.6 to 10.4, UR 11.3 to 10.4, WU 10.1 to 10.1, WR 11.5 to 9.7, BG 8.5 to 9.2, UG 8.2 to 7.9, RG 7.2 to 5.9. Black pairs gained from four black cards moving up a grade; red pairs lost the two red cards untagged as removal. This is why the report now presents tiers.

### Where the model stops

- It scores a 23 by mean grade. It does not play games, so it ignores curve, tempo, and how the Jace token performs in play. Both external reviews call Empower Jace the format's engine; the model credits it only through synergy grades.
- The promo is modelled as one uniform rare or mythic. Confirm from the pack; it is one card in 83.
- The third echoed-pair card is drawn independently of the pair; the PR model excludes the same pair. This differs in about 2% of packs and was left as is.
- Two-Headed Giant and casual REL are out of scope.
- Draft archetype write-ups rank BR first for Draft. In Sealed the evidence points to white or black depth plus premium removal, with BR the deepest removal pair but thin on playables.

### On the day

1. Run section 1 of the cheat sheet on the pool.
2. Count black and red removal first. Three or more usually means WB, WR or BR.
3. Count white and black playables. They are the most likely main colours in this set.
4. Take a blue pair only when the pool gives it removal (Infinite Coursework, Plan for All Outcomes, the charms) or a bomb.
5. Splash only off lands. Landcyclers are flood insurance, not fixing.

### Process record

For reuse on the next set: verify the set on Scryfall; pull the collation from WotC verbatim and cross-check against a second, machine-readable model; grade blind from oracle text; compare to two external reviews and log disagreements; simulate pools; review the sim's rules and tags before ranking; ship a phone-readable cheat sheet with a hand procedure; then do a cold self-review of every number against its source. The simulator is set-agnostic (`--config`).

planned-by: CEO / executed-by: Simulation Engineer (DEC-926, DEC-927); card grades, review and report by CEO (DEC-461)
