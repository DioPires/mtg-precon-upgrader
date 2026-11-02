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

# 7 (continued). Write DIR/cheat_sheet.html, the page for a phone, and its copy
# for the site, web/public/prerelease/CODE.html. Rebuild both each time the
# sheet changes.
uv run --with markdown python scripts/prerelease/build_html.py --set-dir DIR --publish
uv run --with markdown python scripts/prerelease/build_html.py --set-dir DIR --check-text
```

Browser check of the Star Trek page: Chromium from disk, then WebKit (the
engine of Chrome on an iPhone) from disk and over HTTP. Playwright from
`web/node_modules`; no network; `--shots` also writes the screenshots with
WebKit at 390 x 844, light and dark:

```bash
PLAYWRIGHT_BROWSERS_PATH="$HOME/Library/Caches/ms-playwright" \
  node scripts/prerelease/check_html.mjs --set-dir analysis/prerelease/trk --shots /tmp/shots
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
  dependency) and headless Google Chrome. Its temporary HTML file goes in a
  temporary folder, never `DIR/cheat_sheet.html` (the page; DEC-1223).
  The card links stay clickable in the PDF. If Chrome is not at
  `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`, it stops and
  names that path.
- **`build_html.py`** — writes `DIR/cheat_sheet.html`: the sheet as one page
  for a phone, with inline CSS and JavaScript. It loads nothing from the network
  and works opened from disk; its only addresses are the sheet's Scryfall card
  links. The intro and sections 1 to 5 are the sheet's markdown, rendered with
  python-markdown (`uv run --with markdown`; not a project dependency): every
  word and link stays, mana costs show as CSS symbols that keep their source
  text in `data-mana`, sections 3 and 4 show one block per colour, and section
  5 shows one block per archetype with Signposts and Look for behind a tap.
  Section 6 is one block per card from `grades.json`, in the sheet's groups and
  order (`full_list_groups()` in `build_cheat_sheet.py`). A bar at the bottom of
  the screen links each section. With JavaScript, section 6 gets a name search
  and filter chips, each card a `−`/`+` pool counter (kept in the browser's
  `localStorage`, one key per set code), and a Pool view counts steps 2, 3, 4
  and 7 of the hand procedure. `pool_summary()` is the reference for those
  counts. Two builds write the same bytes. `--publish` also writes the same
  bytes to `web/public/prerelease/<set folder name>.html`; Vite copies
  `web/public/` into the site as it is, so the page is served at
  `/prerelease/CODE.html`. `--check-text` compares the text of the page's intro
  and sections 1 to 5 with python-markdown's render of the sheet. Rebuild the
  page and its copy each time the sheet changes: the tests compare the
  committed Star Trek page with its sheet and its copy with the page.
- **`check_html.mjs`** — drives the Star Trek page with Playwright
  (`web/node_modules` of this tree, or of the main checkout from a worktree)
  three times: Chromium from disk, WebKit with the iPhone 13 profile from disk,
  and WebKit over HTTP from a static server on `web/public/` that it starts on
  127.0.0.1. Each run prints: no sideways scroll at 360 and 390 px in light and
  dark, text contrast, the bar, the search field's font size, tap targets of
  44 x 44 px, the search examples and filter chips, the page with JavaScript
  off, and the Pool view against `pool_summary()` for four pools. It refuses
  every network request and exits 1 when a check fails. Its search
  examples and two of its pools are Star Trek cards (`SEARCH_EXAMPLES` and
  `CHECK_POOLS` in `build_html.py`).
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
