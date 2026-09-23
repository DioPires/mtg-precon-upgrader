# Prerelease playbook

How to prepare for a Sealed prerelease in about one working day, with every number traceable to a source. Worked example: Reality Fracture, DEC-925 (`agents/ceo/analysis/dec925/`). Board decision to make this repeatable: DEC-925, 2026-09-23.

## When to start

Start 4 to 5 days before the event. All inputs must exist:

- Scryfall lists every main-set card (`unique=cards` count equals WotC's stated rarity totals plus lands).
- WotC's "Collecting <set>" article is out (booster slot percentages).
- At least two external reviews are out: Draftsim's full-set review and Limited Resources' commons-and-uncommons episode usually land about a week before prerelease.

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
4. **Compare to two external sources.** Parse Draftsim's ratings and search the Limited Resources transcript for the cards you are least sure of.
   ```bash
   uv run python scripts/prerelease/compare_grades.py --set-dir DIR --draftsim URL
   ```
   Re-read the oracle text for every disagreement of 3 or more points and decide; log each decision in `DIR/grade_review_log.md`. Expect a scale offset (Draftsim runs about one point below this scale). Two real misses per set is normal.
5. **Simulate.** Three runs: headline (lands-only splash gate), spec gate (landcyclers count), no splash.
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
   Output `DIR/cheat_sheet.md`: hand-scoring procedure, format rules, removal and tricks per colour, the ranking as tiers, the full graded list. Phone-readable on GitHub. Section 2 is `format_rules.md` verbatim; everything else is generated. A handful of sentences in sections 1, 3 and 5 are judgement calls about the set rather than facts the tool can derive (which cards fix a splash, how to read the ranking at the table); write those into `DIR/prose.json` — without it the tool emits a generic version of each, and `--print-tiers` shows the tier reading computed from the data.
8. **Report.** Post on the issue: the tier reading of P(best), P(viable) per pair, colour depth, what moved the numbers, the model's limits, the day-of steps. Commit and push the folder.
9. **Self-review.** Cold pass, every number against its source: re-read the WotC slot text, re-count mechanics, audit removal tags with a regex over oracle text, re-check any quoted statistic by computing it, re-read the cheat sheet procedure for inconsistent thresholds. Post the findings even when nothing changes.
10. **After the event.** Ask the board how the cheat sheet held up. Record what was wrong in `DIR/notes.md` and, if it is a process lesson, in this playbook.

## Reading the output

- Report P(best) as tiers, not an order. One-point changes on a dozen grades move pairs by up to 2 points.
- P(viable) is more stable than P(best); colour-level statements (which colours carry removal, which are deep) are the most stable.
- The durable deliverables are the verified fact sheet, the graded list and the ten-minute hand procedure. The ranking is background.

## Known traps

- Sum foil and non-foil shares inside a slot (DEC-925: dual rate 43.6% versus the true 54.5%).
- Eligibility is pip castability, not Scryfall's colour field (DEC-927: hybrids belong to seven pairs, and a five-colour hybrid card was castable nowhere).
- Count mechanics case-insensitively; reminder text lowercases keyword actions (Empower Jace 16 versus 35).
- Basic-landcycling spells are not fixers for the splash gate; only lands are (DEC-926 ruling).
- Scryfall has no rulings for a set's new mechanics before release; rely on the printed reminder text and say so.
- Secondary fact sheets summarise WotC's article and drop treatments; read the primary text.
- A CLI pool evaluator is not useful at an LGS with a phone; the cheat sheet's hand procedure replaces it.

## Issue template

Create one issue per event, titled `Prerelease: <set name> (<date>)`, assigned to the CEO, with this body:

```
Event: <date>, <venue>. Format: Sealed, 6 Play Boosters + promo.
Deliverables: pair ranking as tiers, phone-readable cheat sheet (agents/ceo/analysis/prerelease/<code>/cheat_sheet.md).
Inputs available? Scryfall full preview [ ] WotC Collecting article [ ] Draftsim review [ ] Limited Resources episode [ ]
Steps (docs/prerelease-playbook.md): 1 verify set [ ] 2 collation config [ ] 3 blind grades [ ] 4 external compare [ ] 5 sim x3 + tests [ ] 6 sim review [ ] 7 cheat sheet [ ] 8 report [ ] 9 self-review [ ] 10 post-event notes [ ]
Assumptions to confirm at the event: promo pool.
```
