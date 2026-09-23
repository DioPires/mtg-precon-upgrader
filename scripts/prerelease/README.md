# Prerelease toolkit

Everything a Sealed prerelease needs beyond a set code, a collation config and a
grade file. The process these commands serve is in
[`docs/prerelease-playbook.md`](../../docs/prerelease-playbook.md); the worked
example is `agents/ceo/analysis/dec925/` (Reality Fracture).

Set `CODE` to the Scryfall set code and `DIR` to the set directory, normally
`agents/ceo/analysis/prerelease/CODE`.

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
  `tags_default.json` here.
- **`build_cheat_sheet.py`** — writes `DIR/cheat_sheet.md`. Section 2 is copied
  from `DIR/format_rules.md`, written by hand. The rest is generated from
  `grades.json` and whichever of `sim_results.json`,
  `sim_results_spec_splash.json` and `sim_results_nosplash.json` exist.
  `--print-tiers` prints just the tier reading.
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
