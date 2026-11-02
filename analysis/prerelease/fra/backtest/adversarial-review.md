# Adversarial review of the DEC-925 back-test and the nine proposed changes (DEC-1218, 2026-11-01)

The board asked for an adversarial review before it decides the nine changes (I1 to I9) in comment `0e93b06b`. Two independent reviewers ran read-only. One re-ran `retro.py` and tested each claim statistically. The other tested each change against the code, the DEC-925 outputs and the Friday 6 November timeline. Neither saw my conclusions, only the claims to test. Their scripts and sim outputs are in `review/` (they read the repo by absolute path and write to `/tmp`; they are a record of the method, not a tool). I re-computed the claims that reverse my findings (`review/ceo_verify.py` and the colour-count check below).

**Result.** The arithmetic of `retro.md` reproduces byte for byte. Two of its readings do not hold, one cannot be told, and three cost or premise claims in the proposals were wrong. The revised list is at the end.

## Claims of `retro.md`

| Claim | Verdict | Basis (95% intervals, bootstrap or Fisher z) |
|---|---|---|
| Draftsim grades better than ours (0.33 against 0.14) | Holds overall; it is a rarity offset | Difference 0.20 (0.03 to 0.36). Within commons: v3 0.20, Draftsim 0.21 (55 cards). Within uncommons: v3 -0.02, Draftsim 0.08 (48 cards). Stratified by rarity the difference is 0.06 (-0.14 to 0.25). Published uncommons won 2.1 points more than commons (55.8% against 53.7%); Draftsim grades them 1.8 higher on these cards, v3 0.5. Over every graded card: Draftsim 1.42, v3 0.52. Re-computed by the CEO. |
| Noise ceiling 0.78 | Optimistic | Games cluster within decks. A design effect of 1.2 to 1.5 lowers it to 0.73 to 0.65. |
| Removal graded too high (-34 over 24 cards) | Does not hold as a removal error | Regression to the mean. With a correlation of 0.14 any group graded high shows a negative gap: removal's mean v3 percentile (84) alone predicts -30 of the -34. At equal grade and rarity, removal is -0.6 GIH points (-2.2 to +0.8) and -0.2 IWD (-1.7 to +1.4). Colour is not the confound (deck-colour baselines 54.3 to 55.3). |
| Engines graded too low (+26 over 19 cards) | Holds weakly | The tag includes cards that are not card advantage (Medic's Kitesail, Heartwood Crafter, Stingerquill Voxmancer, Saheeli). At equal grade the 13 true card-advantage cards are +2.3 GIH (+1.0 to +3.6) and +1.5 IWD (-0.1 to +3.0). It leans on one card (Fblthp, Impossibly Lost). |
| What survives of the role finding | Holds | We graded removal 2.2 grades above engines (6.50 against 4.26); on Arena the two groups played alike (IWD difference +0.2, -1.3 to +1.8). |
| The pair ranking has no predictive value (P(best) -0.09) | Cannot tell | n = 10. P(best) against win rate -0.09 (-0.68 to 0.57). The true pair order is known with reliability 0.62; power to detect a true correlation of 0.5 was 27%. The data rules out strong value, not moderate value. The fairer target is deck share (game share over expected games per run): +0.13 (-0.55 to 0.70). |
| Better grades do not fix the sim (Draftsim rerun -0.42) | Does not hold | The Draftsim rerun also dropped all 27 synergy grades; v3 with synergy dropped gives -0.43. Grades fitted to Arena GIH (commons and uncommons only, rares unchanged) make the sim rank WU first and UB second (+0.61, -0.09 to 0.91). That test is partly circular. It points to the grades, not the sim's structure, as the bottleneck. |
| P(viable) (3 removal + 1 bomb gate) | Holds, and it is the strongest point against the gate | -0.37 with v3 grades and -0.03 even with the Arena-fitted grades. The gate carries no signal under any grade set. |
| Blue pairs were best; the sheet pointed away | Holds at colour level | Blue pairs won 58.0% against 56.1% for the others: +1.85 (+0.94 to +2.76). P(WU truly best) 0.62. Win rate is conditional on choosing blue, so it cannot show that the conditional advice cost games. |
| The sheet's white-removal sentence contradicts our grades | Holds narrowly | Mono-coloured C+U removal: red 6.33 (6 cards), white 6.00 (5), black 6.00 (7). With gold and hybrid it is a tie (W 6.38, R 6.36, B 6.27). The sentence was unsupported, not clearly wrong. |

## Findings the back-test missed

1. **Three-colour decks.** 27,438 of 74,345 Arena Sealed games (36.9%) were three-colour decks under 17Lands' `combine_splash=true` (splash decks already counted as two-colour). They won 56.3%, against 56.9% for two-colour decks. The sim never builds them, and the sheet allowed at most a 2-card splash. Re-computed by the CEO from `17lands_fra_color_ratings_Sealed.json`.
2. **Red** had the most top-graded removal and was the worst Sealed colour (56.1%). Nothing suggests removal matters more in Sealed than in Draft.
3. **Premier Draft stands in weakly for Sealed at pair level:** Sealed and Draft pair win rates correlate 0.37 (-0.36 to 0.82). RG was third in Draft and last in Sealed.
4. **Rares and mythics are untested.** 17Lands publishes GIH only above about 500 games drawn: 65 of 82 commons, 48 of 110 uncommons, no rare. Its card endpoint ignores the `colors` filter (the WU response was byte-identical to the unfiltered one, fetched 2026-11-01 19:32Z), and Sealed card data holds 23 games.
5. **The ten common dual lands** are the gap between 113 published and 103 matched cards (Draftsim did not grade them); with them, v3 scores 0.19.
6. **Grade compression:** 34 of the 103 cards sit at grade 4, which limits how well any list can rank.

## The nine proposals

| # | Verdict | Reason |
|---|---|---|
| I1 start from Draftsim | Amend | Draftsim's lead is the rarity offset. Starting from Draftsim+1 also breaks the sheet's thresholds: it puts 47 FRA cards at 8+, we put 16, and the share of pools with a viable pair rises from 86.6% to 99.6%. The next back-test would score Draftsim, not us. If Draftsim is late, the rule has no fallback. |
| I2 removal and engine rules | Amend | The removal error did not survive. The rarity offset and card advantage (weakly) did. "Grade by cost, condition and the card it costs" is not a rule anyone can apply. |
| I3 drop the sim ranking | Keep, reason and cost corrected | Its value is unproven, not disproven. The cost claim was wrong: `build_cheat_sheet.py` prints the pair plans and signposts only inside `if "headline" in sims:` (about lines 386 to 454), so dropping the sim needs a builder change. Porting the sim to Star Trek also needs new synergy tags (`sealed_sim.py` near line 235 holds FRA-only tags; an unknown tag raises an error). |
| I4 removal stops being a gate | Keep, amend | Steps 3, 4 and 6 of the procedure are hard-coded (`build_cheat_sheet.py` lines 283 to 289); only the splash and tiebreak lines read `prose.json`. Same builder change as I3. The procedure has no creature count. |
| I5 back-test after every event | Amend | An engineer leg for a 206-line one-off script is premature. Copy it for Star Trek; generalise after the second use. Decide in advance which result changes which rule. |
| I6 check every hand-written claim | Keep, widen | Step 9 checks numbers, not claims. `final-report.md` line 31 also quotes a stale figure. Rule: every comparison sentence states its number. |
| I7 fix `dump_set.py` mechanic counts | Defer to after the event | The claim holds ("Beam me up" on 11 cards, missing; mode labels listed as keywords; "Enchant" 16 matches "enchantment"). Nothing on Friday depends on the script; hand counts suffice. |
| I8 WotC mechanics article as primary source | Amend | The premise was wrong: 8 of the 9 dilemma cards carry reminder text; only Captain Benjamin Sisko (#6) has none (re-computed by the CEO). Release notes still matter for edge cases. Rewrite the existing playbook trap instead of adding a rule. |
| I9 first Arena days for a late event | Drop | The event is on 6 November, before Arena opens. |

Hand counts for Star Trek (oracle text, case-insensitive, `trk_all_cards.json`): Beam me up 11 cards; face a dilemma 9; modal ("choose one", "choose two", "choose one or more", "choose up to") 48 cards: 16 commons, 19 uncommons, 11 rares, 2 mythics.
