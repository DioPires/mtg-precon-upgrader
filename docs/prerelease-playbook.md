# Prerelease playbook

How to prepare for a Sealed prerelease in about one working day, with every number traceable to a source. Worked example: Reality Fracture, DEC-925 (`agents/ceo/analysis/dec925/`). Board decision to make this repeatable: DEC-925, 2026-09-23.

## When to start

Start 4 to 5 days before the event. All inputs must exist:

- Scryfall lists every main-set card (`unique=cards` count equals WotC's stated rarity totals plus lands).
- WotC's "Collecting <set>" article is out (booster slot percentages).
- At least two external reviews are out: Draftsim's full-set review and Limited Resources' commons-and-uncommons episode usually land about a week before prerelease.
- Optional: WotC's "<set> Prerelease Guide" article (archetype names and plans) and one video primer (Tolarian Community College usually posts one the week of the event). These feed step 7b only.

If any input is missing, do the steps that do not need it and mark the rest pending.

## Roles

- CEO: verifies facts, grades cards, reviews the sim, writes the cheat sheet text and the report (DEC-461: card evaluation is not delegated).
- Simulation Engineer: collation config, sim runs, tests, any new slot kind the set needs.
- Board: answers the scoping questions (event date, deliverables) and confirms the promo from the pack.

## Steps

Set `CODE` to the Scryfall set code and `DIR` to `agents/ceo/analysis/prerelease/CODE`.

1. **Verify the set.** Query the Scryfall sets API for the code, release date and card count. Never take a set code from memory.
   ```bash
   uv run python scripts/prerelease/dump_set.py --set CODE --out-dir DIR
   ```
   Writes the card dump, the prints dump, the grading sheet, and `set_facts.md` (rarity and colour counts, keyword and oracle-text mechanic counts, toughness census, collector-number gaps, watermarks, two-colour uncommons per pair). Check the rarity totals against WotC's article. Collector gaps are usually showcase-first printings, not missing cards; the tool resolves each one against the prints dump. `--from-dump` rebuilds the two text files from dumps already on disk, without the network.
2. **Collation config.** Copy `scripts/prerelease/collation_template.json` to `DIR/collation.json`. Fill every slot from the WotC article's verbatim slot text. Rules:
   - Sum every treatment of the same card class inside a slot (non-foil plus foil plus showcase). A foil dual is still a dual. This was the DEC-925 error.
   - Booster-fun variants of rares and mythics are still rares and mythics; fold them proportionally.
   - Off-set cards (Special Guests, The List) are not in the Sealed pool unless the event rules say otherwise; note the assumption.
   - Cross-check against a machine-readable model when one exists (`taw/magic-search-engine`, `data/boosters/CODE-play.yaml`, fetch with `gh pr diff` or the raw file). Record every disagreement.
   - Write the per-pack expectation by hand (commons, uncommons, rares plus mythics, duals) into `sanity_targets`; the sim's test pins it.
   - A slot kind the sim does not support (like echoed pairs) is an engineer leg. Spec it as a config `kind` with its own test.
3. **Grade blind.** Read `DIR/grading_sheet.txt` and write `DIR/grades_src.py` (one tuple per non-basic card: grade 0 to 10, roles, one-line note, optional synergy triple). Grade from oracle text only, before reading any review. Scale: 10 game-winning bomb, 8 to 9 bomb or premium removal, 5 to 7 good playable, 2 to 4 filler, 1 weak, 0 unplayable. Tag `removal` only for cards that answer a creature or planeswalker: 3 damage or more, minus 3 or more, destroy, exile, tuck, fight or bite, or a hard lock. Artifact-only, 2-damage and 6-mana answers are not removal.
   ```bash
   uv run python scripts/prerelease/build_grades.py --set-dir DIR
   ```
   The builder fails if any card is missing, duplicated, or not in the set. The `provides` tag rules live in `DIR/tags.json`; copy `scripts/prerelease/tags_default.json` and rewrite them for the set, keeping only tags some card's grade actually depends on.

   **Grading rules (DEC-1218, from the Reality Fracture back-test).** Apply them to every grade:
   - **Rarity check.** After the build, the mean uncommon grade over non-land cards must sit at least 1 grade above the mean common grade (`build_grades.py` prints the gap since DEC-1219). If the gap is under 1, re-read the uncommons before step 4. Basis: on 17Lands, Reality Fracture's uncommons won 2.1 points more than its commons; our gap was 0.5 and Draftsim's 1.4. Within each rarity, our grades and Draftsim's ranked the cards equally well.
   - **Card advantage.** A card that draws or makes extra cards again and again (every turn, every attack, every activation) gets +1 over the same card without that ability. Give it the role `cardadv` (the sheet marks it ✚). A one-time draw is not `cardadv`. Basis: at equal grade, the 13 true card-advantage cards won 2.3 points more (+1.0 to +3.6).
   - **Removal has no default grade.** Grade each removal spell by what it kills (the toughness census in `set_facts.md`), its cost and its condition. The removal tag rule above does not change.
   - **Half grades** (6.5) are allowed, to break ties.
   - **Save the blind file.** Copy `grades_src.py` to `grades_src_blind.py` before you read any external grade. The next back-test scores the blind file too.
4. **Compare to two external sources.** Parse Draftsim's ratings and search the Limited Resources transcript for the cards you are least sure of.
   ```bash
   uv run python scripts/prerelease/compare_grades.py --set-dir DIR --draftsim URL
   ```
   Re-read the oracle text for every disagreement of 2 or more points (after the scale offset) and decide; log each decision in `DIR/grade_review_log.md`, with the reason when you keep your grade. Expect a scale offset (Draftsim runs about one point below this scale). Two real misses per set is normal.
   - Do not start from Draftsim's grades or copy them over. Draftsim+1 put 47 Reality Fracture cards at 8 or more against our 16, which breaks the sheet's thresholds, and the next back-test would score Draftsim instead of us (DEC-1218 R1).
   - `compare_grades.py` keeps Draftsim's raw grades in `DIR/draftsim_grades.json`; keep that file beside `grades_src_blind.py`.
   - If Draftsim's review is not out by the evening two days before the event, ship your own grades and say so in the sheet's intro.
5. **Simulate (optional since DEC-1218).** The sheet no longer prints the simulated ranking or P(viable). On Reality Fracture the ranking's value could not be shown either way (10 pairs, a 27% chance to detect a real correlation of 0.5), and P(viable)'s gate of 3 removal spells and a bomb carried no signal under any grade set. Run the sim only to test it again after an event, with better grades. Three runs: headline (lands-only splash gate), spec gate (landcyclers count), no splash.
   ```bash
   uv run python scripts/sealed_sim.py --config DIR/collation.json --cards DIR/CODE_all_cards.json --grades DIR/grades.json --pools 100000 --seed <event date as YYYYMMDD> --splash-fixers lands --out DIR/sim_results.json
   uv run python scripts/sealed_sim.py ... --splash-fixers spec --out DIR/sim_results_spec_splash.json
   uv run python scripts/sealed_sim.py ... --splash-max 0 --out DIR/sim_results_nosplash.json
   uv run --with pytest python -m pytest tests/test_sealed_sim.py -q
   ```
   Pass `--pairs` only when the set has a paired-card slot.
6. **Review the sim before ranking.** Check: eligibility is castability by mana-cost pips (hybrid cards belong to both colours); the removal count uses the tag rule above; the per-pack sanity check matches the targets within 0.05; the assumptions header lists every modelling choice.
7. **Cheat sheet.** Write `DIR/format_rules.md` by hand (the set's mechanics in plain words, the interactions that decide games, the damage-to-toughness census from `set_facts.md`). Then:
   ```bash
   uv run python scripts/prerelease/build_cheat_sheet.py --set-dir DIR
   ```
   Output `DIR/cheat_sheet.md`: hand-scoring procedure, format rules, removal and tricks per colour, the archetypes (or, with a sim, the ranking as tiers), the full graded list.

   **The hand procedure (DEC-1218 R4).** Write it into `prose.json` as the `procedure` list (DEC-1219). Removal is information and a late tiebreak, not a gate. Start from this text and change only the splash step:
   1. Sort by colour. A hybrid card counts for either colour; put gold cards aside.
   2. For each colour, count the cards graded 6+, the cards graded 4+, and the bombs (★).
   3. Pick the two colours with the most 6+ cards. A ★ counts as two. Add the pair's gold cards (step 1 put them aside; Star Trek, DEC-1218).
   4. Check that you have 22 or 23 cards graded 4+ and 15 or more creatures. If not, look at the next colour or a splash.
   5. Splash: the set's own rule (below).
   6. Build 17 lands and 23 spells, with 7 or 8 two-drops. Play the removal you have, but do not pick colours for it.
   7. If two pairs tie, pick more ★ first, then more ✚, then more ✕, then more two-drops.

   **The splash rule comes from the set's fixing (DEC-1218 N1).** Count the fixing a pool holds: the expected common duals per pool from the land slot, the rare fixers, and the fixing spells. Write the rule from that count. Do not copy another set's rule. Basis: on Reality Fracture, 37% of Arena Sealed games were three-colour decks, at 56.3% against 56.9% for two colours, while our sheet allowed at most a 2-card splash. Phone-readable on GitHub. Section 2 is `format_rules.md` verbatim; keep each rule to one bold line and one number. Everything else is generated, including the toughness table and the per-spell kill share in section 3. A handful of sentences in sections 1, 3 and 5 are judgement calls about the set rather than facts the tool can derive (which cards fix a splash, how to read the ranking at the table); write those into `DIR/prose.json` — without it the tool emits a generic version of each, and `--print-tiers` shows the tier reading computed from the data.
7b. **Pair plans (section 5 since DEC-1218).** Without a sim, section 5 is the archetypes: write the ten `pair_plans` entries whenever a source exists (WotC's guide, Draftsim's archetype article, a video primer). The builder prints them without a sim since DEC-1219. For each colour pair add a `pair_plans` entry to `DIR/prose.json`: the archetype `name` (WotC's), one `plan` sentence (what the deck does and how it wins, in the imperative), and a `look_for` line of the key commons and uncommons the sources name, each with our grade in brackets. Rules: one sentence per plan; name only cards that exist in the card file; keep our grade next to every card so a source's "key card" we grade low reads as such; where the two sources disagree, prefer the WotC guide for the archetype's identity and the video for play advice, and say nothing you cannot verify against oracle text. The tool adds the **Signposts** line itself (the pair's two-colour cards graded 5+), so with no sources at all the block still shows every pair's signposts. Rebuild with the same command as step 7.
8. **Report.** Post one short comment on the issue: the verified facts, the sources, colour depth, the grading checks (rarity gap, external comparison), the limits, the day-of steps. Add sim tables only if a sim ran. Commit and push the folder.
9. **Self-review.** Cold pass, every number against its source: re-read the WotC slot text, re-count mechanics, audit removal tags with a regex over oracle text, re-check any quoted statistic by computing it, re-read the cheat sheet procedure for inconsistent thresholds. **Every comparison sentence in the sheet and the report states its number** (DEC-1218 R6): check each line of `prose.json` and `format_rules.md` against `grades.json`, and re-check after every grade change. Reality Fracture's sheet called white's removal the best when our own grades put red's ahead (6.33 against 6.00). Post the findings even when nothing changes.
10. **After the event.** Ask the board how the cheat sheet held up. Record what was wrong in `DIR/notes.md` and, if it is a process lesson, in this playbook. Then open a dated back-test issue, assigned to the CEO, for about three weeks after the Arena release (DEC-1218 R5): copy `agents/ceo/analysis/dec1218/fra-retro/retro.py` and score the blind and final grades against 17Lands. Before the event, write `DIR/backtest-plan.md`: which result changes which rule. Do not close the event issue while step 10 is open; Reality Fracture's step 10 never ran, and nobody saw its findings for a month.

## Reading the output

- Report P(best) as tiers, not an order. One-point changes on a dozen grades move pairs by up to 2 points.
- P(viable) is more stable than P(best); colour-level statements (which colours carry removal, which are deep) are the most stable.
- The durable deliverables are the verified fact sheet, the graded list and the ten-minute hand procedure. Since DEC-1218 the sheet shows the archetypes, not the ranking.
- Write the sheet as instructions, not explanations: one imperative line per step, the number first, reasons in the report. Show colour at a glance (the ⚪🔵⚫🔴🟢 pips) and put the creature-toughness table next to the removal list with what each spell kills. Both came from a reader of the FRA sheet (DEC-925, step 10).

## Known traps

- Sum foil and non-foil shares inside a slot (DEC-925: dual rate 43.6% versus the true 54.5%).
- Eligibility is pip castability, not Scryfall's colour field (DEC-927: hybrids belong to seven pairs, and a five-colour hybrid card was castable nowhere).
- Count mechanics case-insensitively; reminder text lowercases keyword actions (Empower Jace 16 versus 35).
- Basic-landcycling spells are not fixers for the splash gate; only lands are (DEC-926 ruling).
- Scryfall has no rulings for a set's new mechanics before release. Read WotC's mechanics article and the release notes for the edge cases; reminder text does not carry them. Star Trek: a spell cast with beam me up is always exiled, and a modal trigger with no legal mode is not a dilemma (DEC-1218 R8).
- `dump_set.py` counts mechanics from Scryfall's keyword field. It misses a keyword that Scryfall does not list (Star Trek's beam me up, 11 cards) and lists mode labels as keywords. Count the set's mechanics by hand with a case-insensitive oracle-text regex until the fix lands (DEC-1218 R7).
- A group of cards that sits below its results is not a grading error by itself. With weak grades, any group graded high shows that gap (regression to the mean). Compare at equal grade and rarity before you write a rule (DEC-1218: the removal finding did not survive this test).
- Secondary fact sheets summarise WotC's article and drop treatments; read the primary text.
- `set_facts.md` counts creature toughness over every card with a printed toughness, Spacecraft and vehicles included (Star Trek: 181). The sheet's section 3 counts creatures only (165). Quote the sheet's figures in `format_rules.md`, `prose.json` and the grade notes (DEC-1218: 72% against 75% for toughness 3 or less).
- A CLI pool evaluator is not useful at an LGS with a phone; the cheat sheet's hand procedure replaces it.

## Issue template

Create one issue per event, titled `Prerelease: <set name> (<date>)`, assigned to the CEO, with this body:

```
Event: <date>, <venue>. Format: Sealed, 6 Play Boosters + promo.
Deliverables: phone-readable cheat sheet with the archetypes (agents/ceo/analysis/prerelease/<code>/cheat_sheet.md) and its PDF.
Inputs available? Scryfall full preview [ ] WotC Collecting article [ ] Draftsim review [ ] Limited Resources episode [ ] Optional: WotC Prerelease Guide [ ] video primer [ ]
Steps (docs/prerelease-playbook.md): 1 verify set [ ] 2 collation config [ ] 3 blind grades + rarity check [ ] 4 external compare [ ] 5-6 sim (optional) [ ] 7 cheat sheet + splash rule [ ] 7b archetypes [ ] 8 report [ ] 9 self-review [ ] 10 post-event notes + dated back-test issue [ ]
Assumptions to confirm at the event: promo pool.
```
