# Prerelease toolkit

Everything a Sealed prerelease needs beyond a set code, a collation config and a
grade file. The process these commands serve is in
[`docs/prerelease-playbook.md`](../../docs/prerelease-playbook.md); the worked
example is `analysis/prerelease/fra/` (Reality Fracture).

Set `CODE` to the Scryfall set code and `DIR` to the set directory, normally
`analysis/prerelease/CODE`.

## Run order

```bash
# 1. Dump the set and get the facts to check against WotC's article.
uv run python scripts/prerelease/dump_set.py --set CODE --out-dir DIR

# 2. Copy the collation template and fill it from the article's slot text.
cp scripts/prerelease/collation_template.json DIR/collation.json

# 3. Grade blind from DIR/grading_sheet.txt into DIR/grades_src.py, then build.
uv run python scripts/prerelease/build_grades.py --set-dir DIR

# 4. Compare against Draftsim's review and log every 3-point disagreement.
uv run python scripts/prerelease/compare_grades.py --set-dir DIR --draftsim URL

# 5. Simulate (three runs; see the playbook for the exact flags).
uv run python scripts/sealed_sim.py --config DIR/collation.json \
  --cards DIR/CODE_all_cards.json --grades DIR/grades.json \
  --pools 100000 --seed YYYYMMDD --splash-fixers lands --out DIR/sim_results.json

# 7. Write DIR/format_rules.md by hand, then build the cheat sheet.
uv run python scripts/prerelease/build_cheat_sheet.py --set-dir DIR

# 7 (continued). Render the sheet to DIR/cheat_sheet.pdf; needs Google Chrome.
uv run --with markdown python scripts/prerelease/build_pdf.py --set-dir DIR
```

Tests: `uv run --with pytest python -m pytest tests/test_prerelease_tools.py`.

## What each command does

- **`dump_set.py`** — verifies the set code against the Scryfall sets API, downloads
  the card and printing dumps, and writes `grading_sheet.txt` (one block per
  non-basic card, sorted by colour then rarity) and `set_facts.md` (rarity and
  colour counts, keyword and oracle-text mechanic counts, creature toughness
  census, collector-number gaps, watermarks, two-colour uncommons per pair).
  `--from-dump` rebuilds the two text files from dumps already on disk.
- **`build_grades.py`** — turns `DIR/grades_src.py` into `DIR/grades.json`. Stops
  if the grade file misses a card, names a card that is not in the set, or lists
  one twice. Tag rules come from `DIR/tags.json`, falling back to
  `tags_default.json` here. Grades may be halves (6.5). The summary ends with
  the mean grade by rarity over non-land cards and the `uncommon - common gap`;
  below 1.0 it prints a `CHECK:` line to re-read the grades (the exit code
  stays 0).
- **`build_cheat_sheet.py`** — writes `DIR/cheat_sheet.md`. Section 2 is copied
  from `DIR/format_rules.md`, written by hand. The rest is generated from
  `grades.json` and whichever of `sim_results.json`,
  `sim_results_spec_splash.json` and `sim_results_nosplash.json` exist.
  Without `sim_results.json`, section 5 lists the ten archetypes from
  `prose.json`'s `pair_plans` (the named pairs first, then the rest in the
  order WU, WB, WR, WG, UB, UR, UG, BR, BG, RG); with no `pair_plans` either,
  there is no section 5. The role `cardadv` gets the tag ✚.
  Every card name on every line except headings links to the card's Scryfall
  page: the card's `scryfall_uri` from the dump, without its query string. The
  tool matches whole, case-sensitive names only, longer names first, and never
  inside a link ("Eject the Warp Core" is one link, not two). A two-faced card
  is linked by its full name and by its front face. `--no-scryfall-links`
  writes the sheet without links. `--print-tiers` prints just the tier reading.
- **`build_pdf.py`** — renders `DIR/cheat_sheet.md` to `DIR/cheat_sheet.pdf`
  (A4) with python-markdown (`uv run --with markdown`; not a project
  dependency) and headless Google Chrome, and removes the temporary HTML file.
  The card links stay clickable in the PDF. If Chrome is not at
  `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`, it stops and
  names that path.
- **`compare_grades.py`** — fetches a Draftsim review, reads the `Rating: N/10`
  lines back to card names, writes `DIR/draftsim_grades.json` and prints the
  means, the correlation, the mean absolute difference and every disagreement of
  3 points or more. `--html FILE` parses a saved page instead.

## Files you write by hand

| File | What it is |
|---|---|
| `DIR/collation.json` | the booster model, from `collation_template.json` |
| `DIR/grades_src.py` | one tuple per non-basic card: name, grade, roles, note, optional synergy |
| `DIR/format_rules.md` | section 2 of the cheat sheet: the set's rules that decide games |
| `DIR/tags.json` | optional; the set's `provides` tag rules, from `tags_default.json` |
| `DIR/prose.json` | optional; replaces the few cheat-sheet sentences that are judgement calls about the set rather than facts the tool can derive |

### `prose.json` keys

Every key is optional; a key that starts with `_` is a comment.

| Key | Replaces |
|---|---|
| `title`, `intro` | the first heading and the legend sentence |
| `procedure` | a list of lines: all seven steps of section 1, verbatim. Cannot be combined with the two keys below |
| `procedure_splash`, `procedure_tiebreak` | steps 5 and 7 of the default procedure |
| `removal_lead` | the sentence that opens section 3 |
| `ranking_heading` | the section 5 heading (default with a sim: the Monte Carlo heading; without: `## 5. The ten archetypes`) |
| `ranking_commentary` | the paragraph after the section 5 heading (default with a sim: the computed tier reading) |
| `ranking_reading` | the paragraph after the ranking table (sim path only) |
| `pair_plans` | per pair (`WU`, `WB`, …): `name`, `plan`, `look_for` |
