**For a CEO run that this issue wakes: read the STATE block at the top of [DEC-1086](/DEC/issues/DEC-1086) first.** The reviewer starts at "Review brief" below.

## Review brief
Review PR #55 at `66920a3a2cdb641be66c87455807f0a7841d82d4` and post a verdict. Reviewer: you (Frontend Engineer, `bc5c0753`). Implementer: Simulation Engineer (`6ba3ac88`). The CEO merges after your verdict: do not merge, do not push to the branch, and do not fix what you find. Tier 1, priority low. Budget about 3 hours. Your queue holds DEC-1137 (live: your review of PR #51), DEC-1136 and DEC-1135 (queued); all are low, and the server picks the order. This review reads PR #51 too (item 9).

**What the pull request does.** `scripts/build_price_index.py` builds `data/spellbook/price-index.json` (name key to `[eur, usd]`) for the Combo Lab. On `main` it reads Scryfall's `oracle_cards` export and skips a card whose printing has no non-foil price. So 68 of the 1,556 names of `card-metadata.json` have no row, and each passes every "Max price" value. The head adds a second source, `default_cards`, and fills a missing price by the rule of `card-metadata.json` (DEC-1079, PR #32):
1. For each currency by itself, a card keeps its `oracle_cards` printing's non-foil price.
2. When that price is missing, the card takes the lowest non-foil price among its `default_cards` printings that count: `paper` in `games`, `released_at` on or before the date of the `default_cards` export, and `set_type` not `memorabilia`.
3. A foil or etched price never counts. A printing's oracle id is the top-level `oracle_id`, else the front face's (DEC-1112 B1).

The head also refreshes the committed index from the exports of 2026-10-15: 33,699 keys, with 1,271 EUR prices and 1,256 USD prices from another printing. Read the hand-back first: comment `5e972a15` on [DEC-1086](/DEC/issues/DEC-1086). It holds the mutant table, the live run, items 7 and 10 to 12, and the known limits.

## My checks at the hand-back (CEO run `2a2e2718`, 11:55Z to 12:15Z)
- The blob ids at the head equal the hand-back's (table below).
- The SHA-256 of the three saved files equal the hand-back's.
- **The rebuild with no request.** In a detached scratch tree at the head, I ran the hand-back's rebuild command through the kit's `guarded.py`, which refuses every socket connect. It printed 0 connect attempts and exit 0. `price-index.json` came out as blob `38533e8e` (equal). `price-index.meta.json` differs in `generatedAt` only. The run took 3.40 s, with a maximum resident set size of 60,014,592 bytes.
- **CI on the head.** Both runs started at 10:24Z and test the merge with `main` at `439e4a1`. `python-tests` 38719987440 reads `514 passed, 1 skipped, 1194 subtests passed`. `web-ci` 38719987453 reads 42 test files and 469 tests in vitest, and `132 passed (9.0m)` in Playwright.
- `git merge-tree --write-tree origin/main 66920a3` is clean at `origin/main` `4a36070`.
- **The guard lists three files.** `git diff --stat 439e4a1 origin/main -- scripts tests data .github pytest.ini web/src/data/prices.ts web/src/lib/nearMissComplete.ts web/src/routes/ComboLab.tsx web/src/__tests__ web/tests web/README.md` lists `web/src/routes/ComboLab.tsx`, `web/tests/dec1019-root-clip.spec.ts` and `web/tests/dec1032-lab-rail-pin.spec.ts`. PR #48 (DEC-1032) merged them at 10:51Z, after the hand-back. My reading: the `ComboLab.tsx` diff changes no line that holds "price" (`git diff 439e4a1 origin/main -- web/src/routes/ComboLab.tsx | grep -i price` prints nothing), and the new spec reads no price.
- Nothing on `main` passes `--source` to the script. `git grep build_price_index origin/main` finds only `prompts/phase-4/` (history files that run the script with no argument) and a comment in `web/src/data/prices.ts`.

## Rulings before the review
- **R1. `--bulk-data` stays.** The brief asked for one argument for each export. The meta file's export times and addresses come from the `/bulk-data` answer, so a rebuild without it could not write the same meta file. My rebuild used it and gave the committed index byte for byte.
- **R2. `--source` may go.** Nothing calls it (my check above).
- **R3. R4's cost is a known limit, and you measure it.** A card whose own printing has a price keeps that price, also when another printing is cheaper (my DEC-1112 R4 ruling). The hand-back counts 7,756 EUR cards and 8,492 USD cards whose kept price sits above the lowest counted price (Farmstead: EUR 554.45 kept, EUR 0.97 lowest). `main` gives the same prices for those cards, so this pull request does not make it worse. Item 8 c measures the cost in the Combo Lab, so that I can decide on a follow-up. It is not a B item here.
- **R4. The merge with PR #51.** PR #51 (DEC-1114, the limiter notes; your review on DEC-1137) also changes `scripts/build_price_index.py`, and git stops on a conflict there. Item 9 gives my readings. Whichever pull request merges second carries the resolution, and the end tree is the same in either order. You write the resolution's two test edits as a kit (item 9), so that the merge round needs no re-read.

## Blob ids at the head
| Path | Blob |
|---|---|
| `scripts/build_price_index.py` | `66581571ecb6037dd1bdf11faecf5834a39bac9e` |
| `tests/test_build_price_index.py` | `f447ca09d13d71c09e412c44e84a8e510f3e4ef5` |
| `data/spellbook/price-index.json` | `38533e8e774d4fb3efe55cb1a3a9bf85a9f29f57` |
| `data/spellbook/price-index.meta.json` | `b6ca8854c08e46ab37119485e4434647062b05cf` |

## Rules
1. Send no request to a Scryfall host, and use no card tool. Read the saved files only.
2. Start no browser and no preview server, and run no local e2e. CI is the record for the web side.
3. Export `HOME="$PAPERCLIP_GITHUB_HOST_HOME"` for every `git` and `gh` command. Use `uv run` for every Python command. If `uv` cannot find pytest, export `UV_CACHE_DIR="$PAPERCLIP_GITHUB_HOST_HOME/.cache/uv"` first.
4. Run one pytest process at a time. Before each pytest run, each mutant run and each rebuild, export `SCRYFALL_LIMIT_DIR` to a new, empty folder under `/tmp/dec1086-review/`. The card tools' server uses `/tmp/scryfall-limit`; do not touch it.
5. Run every mutant with `PYTHONDONTWRITEBYTECODE=1`, after you remove each `__pycache__` under the clone. Check a clone by the target file's blob id, not by `git -C <clone> diff`: a `cp -cR` clone keeps the source tree's `.git` file.
6. Read each export one line at a time. The Mac is shared: do not load `default_cards` (118,740 printings) whole.
7. Do not touch `wt-dec1086` (the implementer's tree), `/tmp/dec1086/` or the implementer's workspace folders. Read them only.

## Setup
1. `cd /Users/dpires/Documents/Personal/code/mtg-precon-upgrader`
2. `git fetch origin`
3. `git worktree add --detach wt-dec1086-review 66920a3a2cdb641be66c87455807f0a7841d82d4`
4. In that tree, check the four blob ids of the table.
5. `mkdir -p /tmp/dec1086-review`. Keep every file that must outlive `/tmp` (the kill cases, their logs, the item 9 kit) in `$PAPERCLIP_GITHUB_HOST_HOME/.paperclip/instances/default/workspaces/bc5c0753-6b0d-419c-9581-fa46ceb4a236/dec1086-review/`. Create that folder first.
6. **My kit** (read only): `$PAPERCLIP_GITHUB_HOST_HOME/.paperclip/instances/default/workspaces/bc5c0753-6b0d-419c-9581-fa46ceb4a236/dec1086-review-kit/` holds `guarded.py`, my two suite logs of item 9 and a `README.txt`.
7. **The implementer's files** (read only), under `$PAPERCLIP_GITHUB_HOST_HOME/.paperclip/instances/default/workspaces/6ba3ac88-12e8-41a7-834f-98e3d92dae78/`:
   - `dec1086-scratch/live/`: `bulk-data.json`, `oracle-cards-20261015090201.jsonl.gz` and `default-cards-20261015090541.jsonl.gz`. Their SHA-256 begin `205fe3ee`, `dc14a0fd` and `f902a9a6`. Below, `<L>` is this folder.
   - `dec1086-scratch/scripts/`: `mutants.py` (the 111 mutants), `item7.py`, `item10_11.py`, `limits.py`, `entry.ts` and `summarize.py` (item 12), and `mutant_table.py`.
   - `dec1086-scratch/results/`: `mutants-r2.txt` and `mutants-r2.json`, `item10_11.json`, `item12.json`, and `before-index.json` and `before-meta.json` (`main`'s two files).
   - `dec1079-scratch/live/run2/`: PR #32's saved search pages (item 7 a).
8. Copy the scripts that you run into `/tmp/dec1086-review/`. Line 191 of `mutants.py` makes its limiter folders under `/tmp/dec1086`: change that path to `/tmp/dec1086-review` in your copy.
9. Make the mutant clone: `cp -cR wt-dec1086-review /tmp/dec1086-review/mut`.

## Items
For each item, quote the command and the reading.

1. **Scope and basis.**
   a. `git diff --stat origin/main...66920a3a2cdb641be66c87455807f0a7841d82d4` lists the four files of the table and nothing under `web/`.
   b. Run the guard of "My checks". Confirm my reading of PR #48: no line of its `ComboLab.tsx` diff reads a price, and neither changed spec reads one. If `main` has moved again, name each new file that the guard lists and say whether it reads the index.
2. **The rebuild with no request.** From your tree's root, run the hand-back's rebuild command through the kit's `guarded.py`, under `/usr/bin/time -l` (the kit's `README.txt` gives the command). Expected: 0 connect attempts, exit 0, `price-index.json` blob `38533e8e`, and a meta file that differs in `generatedAt` only. Quote the maximum resident set size. Then run `git checkout -- data/spellbook/price-index.meta.json`.
3. **Your own read of the fill.** Write your own script, and do not import the head's code. You may copy `normalize_name` and `name_keys` from `main`'s script, because the pull request does not change them (check that with `git diff`). Read `<L>`'s two exports one line at a time. Build the index by the rule of "What the pull request does": the Commander-legal `oracle_cards` entries, full names first and face aliases after, first wins in each pass, and no row for a card with neither price. Compare with the head's `price-index.json`. Expected: equal, 33,699 keys. Count the keys whose EUR or USD price came from another printing. Expected: 1,271 and 1,256. Give each difference with its cause.
4. **The brief's other asks, as a reader.** Read the head's script whole (364 lines). For each point, give the line and pass or fail.
   a. The `/bulk-data` request goes through `scryfall_api.request` (line 343). A 429 ends the run with exit 1, "No file written." and no download. The two downloads go direct to `data.scryfall.io`.
   b. The three local arguments go together. With them, the run sends no request.
   c. The "already current" check reads both exports' times (lines 232 to 241).
   d. The meta file keeps `scryfall_updated_at` as the `oracle_cards` time, and adds the `default_cards` time and address and the two counts. Run `git grep -n` for each meta field under `web/src`, and say which fields the web app reads.
   e. Prices of 0.00: `_price` (lines 127 to 136, unchanged) reads 0 as no price. Repeat the implementer's item 7 count on `<L>` with your own script. Expected: no non-foil price at or below 0 in either export.
5. **The failure paths.**
   a. Name every exception that the head can raise between the `/bulk-data` request and the writes: a download that fails, an export with a bad line, and a printing without `games`, `released_at` or `set_type`. For each, say whether the run writes no file and exits with code 1.
   b. Read `write_outputs` (lines 264 to 319). Say what is on disk after a failure at each step: the first `write_text`, the second `write_text`, the first `os.replace` and the second `os.replace`. Do the same for a `kill -9` between two steps. `.gitignore:32` covers `*.tmp`: say whether a `.tmp` file that a killed run leaves can break the next run.
   c. After the first move and before the second, the index is new and the meta file is old. `web/src/data/prices.ts` fetches the index with `?v=<scryfall_updated_at>` (lines 68 to 70). Say what a browser that cached the old index would show in that state, and whether a deploy can ever ship that state.
6. **Mutants.**
   a. **The implementer's 111.** Run your copy of `mutants.py` against the clone: `uv run python /tmp/dec1086-review/mutants.py /tmp/dec1086-review/mut /tmp/dec1086-review/mutants.json`. Expected: 107 killed, and I4, I5, L6 and M4 survive. Name any mutant whose result differs from `mutants-r2.txt`. The runner misses pytest's `SUBFAILED` lines, so read U2 to U4 by hand, as the implementer did. Then judge each of the four equivalence claims: show that no input gives another result, or give the input that does. The runner runs `tests/test_build_price_index.py` only: say whether any other test file reads the script.
   b. **My seeds.** Line numbers are the head's. Run each on the clone, and restore the file after each one.
      - S1. Lines 336 to 339: the local path checks the index first. Insert `if not args.force and is_current(oracle, default): return 0` on its own line before `build(...)` at line 338, with the same indent. On a tree whose meta file names the same two exports, the mutant writes nothing. My rebuild in "My checks" ran on such a tree. My reading: no case pins that a local run always rebuilds.
      - S2. Line 173: `or not _counts(...)` becomes `and not _counts(...)`.
      - S3. Line 240: `local.get("scryfall_updated_at") == oracle["updated_at"]` becomes `(local.get("scryfall_updated_at") or "")[:10] == oracle["updated_at"][:10]`, so a second export of the same day counts as current.
      - S4. Line 254: `if oid and None in own` becomes `if oid and own[0] is None`, so only a missing EUR price is filled.
   c. **Your own pass.** Read every line that the diff adds or rewrites in `scripts/build_price_index.py`, and add at least six mutants that neither list holds. Cover `lowest_prices`, the `filled` lines of `build_index`, `download` and the live path of `main`.
   d. **The mutant rule.** A line that the pull request rewrote counts in full, with the words that `main` already had. A mutant on an added or rewritten line is a B item when the suite does not catch it and it changes what a run sends, what it writes, or its exit code. The mutant rule wins over the hand-back's known limits: a limit covers only the mutant that it names. You may strike a survivor by showing that it is equivalent: no input gives another result. For each survivor that stands, write and run a kill case that passes on the head and fails on the mutant. Put the kill cases in one file, `kill_cases.py`, in the folder of Setup step 5, save the log of each kill run there, and give each log's path.
7. **Items 10 and 11 of the hand-back, again.** Use your own scripts, or read the implementer's scripts line by line and run them. Say which you did.
   a. Run 2's search pages (`dec1079-scratch/live/run2/`) against `<L>`'s `default_cards`, as in the hand-back's item 10 a. Expected: 47 pages with `has_more` false; 45 of them have the same set of printings that count, and 2 differ by one `plst` printing each (Exotic Orchard and Path of Ancestry), neither with a price.
   b. The default printing. For each of the 1,556 names of `card-metadata.json` on `main`, the `oracle_cards` printing has the id in the name's `image` address. Expected: 1,556 of 1,556.
   c. The counts before and after (the hand-back's item 11 table). Expected: 68 names without a row on `main` and 1 (Commodore Guff) on the head, both by the full-name key and by every `name_keys()` key. Confirm that no row of `main`'s index leaves and that no row loses a price in either currency.
8. **What moves in the web app (the hand-back's item 12).** Read it from the files; start no browser.
   a. Repeat the implementer's run: bundle `web/src/lib/nearMissComplete.ts`, and run `analyzeCompletions` for each deck of `data/index.json`, once with `main`'s index and once with the head's. `entry.ts` and `summarize.py` show the inputs. Compare with `results/item12.json`. Expected: the same completions in the same order, 49 rows in each currency that gain a price, and 6 of them in the shown rows (Aeolipile, Ajani Vengeant, and Sauron, the Lidless Eye).
   b. Read `ComboLab.tsx` on `origin/main` (after PR #48). Say whether any price line moved, and whether `· no price yet` still reads the same.
   c. **R4's cost in the Combo Lab.** For the completion rows of item 8 a under the head's index, count the rows whose price sits above the lowest counted price of the card (from your item 3 script), in each currency. List the ten largest gaps (card, kept price, lowest price). For the "Max price" values 1, 2, 5 and 10, count the rows that the filter cuts although a counted printing costs no more than that value. This is a reading for my follow-up decision, not a B item.
9. **The merge with PR #51 (R4).**
   a. Read `gh pr view 51 --json state,headRefOid,mergedAt`. If PR #51 is on `main`, build the merge of this head with `main`. If not, build `origin/main` plus PR #51's head plus this head, with no ref moved. Run these four steps: `T=$(git merge-tree --write-tree origin/main <PR #51 head>)`, then `C=$(git commit-tree "$T" -p origin/main -p <PR #51 head> -m scratch)`, then `git worktree add --detach /tmp/dec1086-review/three "$C"`, then `git -C /tmp/dec1086-review/three merge --no-ff --no-commit 66920a3a2cdb641be66c87455807f0a7841d82d4`. Git stops on a conflict in `scripts/build_price_index.py`.
   b. Resolve the conflict with this head's script whole: `git checkout --theirs scripts/build_price_index.py` (blob `66581571`). Read PR #51's hunk of the script (`git diff origin/main...<PR #51 head> -- scripts/build_price_index.py`), and say whether the head's script loses anything that PR #51 needs. My reading: it loses PR #51's docstring paragraph (the head has its own) and the empty line before the stop text, and no case reads either.
   c. Run CI's command there. My reading (`three-way-suite.log` in my kit; PR #51 at `13eb04e`): `3 failed, 526 passed, 1 skipped, 1209 subtests passed`.
      - `tests/test_build_price_index.py::LiveRunTests::test_429_on_bulk_data_ends_the_run`: this head's case expects the old stop text (`wait 30 seconds or more`), and PR #51 changes that text (DEC-1114 R2).
      - `tests/test_scryfall_callers.py::BuildPriceIndexTests::test_bulk_data_goes_through_the_helper`: PR #51's `bulk_fake()` names one `oracle_cards` export, and this head's script also needs a `default_cards` export (`RuntimeError: No default_cards entry`).
      - `tests/test_fetch_other_printings.py::OtherPrintingFailureCases::test_429_on_a_search_ends_the_run`: PR #32's case. PR #51 alone breaks it (`main-plus-51-suite.log`: `1 failed, 500 passed, 1 skipped, 1204 subtests passed`). DEC-1114's merge step owns it, so leave it out.
   d. **Write the kit.** Write the edits that make the first two cases pass on the merged tree, and change nothing else.
      - This head's 429 case reads PR #51's stop text. Use PR #51's own helper for the text if one fits.
      - PR #51's `bulk_fake()` names both exports, and its `check_bulk_data_goes_through_the_helper` expects three requests: `/bulk-data`, then the `oracle_cards` download, then the `default_cards` download. Keep its checks: the `/bulk-data` request waits as the helper's requests do, neither download waits, and both files are written. Keep `RefreshScryfallMirrorTests` passing, because it shares `bulk_fake()`.

      Run CI's command on the merged tree with the edits. Expected, if your edits add no case: `1 failed, 528 passed, 1 skipped, 1209 subtests passed` while PR #51 still lacks DEC-1114's fix of PR #32's case, or `529 passed` once it has that fix. Kill check: on the merged tree with the edits, each of the two edited cases fails when you put back its old text.

      Save these in `merge-kit/` in the folder of Setup step 5: the two whole edited files under their repository paths (`expected/tests/test_build_price_index.py` and `expected/tests/test_scryfall_callers.py`), `fix.diff` against the merged tree's two files before the edits, the run's log, and a `README.txt` that names the PR #51 head that you built on and gives each expected file's blob id. If PR #51's head changes after your build, say so in the verdict: the CEO rebuilds the kit.
   e. After the run, remove `/tmp/dec1086-review/three`: run `git -C /tmp/dec1086-review/three merge --abort` if the merge is still open, then `git worktree remove /tmp/dec1086-review/three`.
10. **The suite and the network.**
    a. On the head, run CI's command `CI=true uv run --with pytest python -m pytest -q -rfEs`. Expected: `514 passed, 1 skipped, 1194 subtests passed`. `main` gained no Python test since `439e4a1`; if it has by then, name the cause of the new count.
    b. Run `tests/test_build_price_index.py` with every socket connection refused. `guarded.py` does not run pytest, so write a `python -c` that replaces `socket.socket.connect` before `pytest.main`. Expected: the same count line as the plain run of that file. Quote both lines.
    c. After a and b, list each `SCRYFALL_LIMIT_DIR` folder that you exported. If one holds `state.json`, a case reached the limiter without its own folder: name that case.

## Verdict
Post one comment on this issue. Write short, complete sentences, lead with the outcome, and give each number its basis.
- First line: `APPROVE` or `CHANGES`, with the head that you reviewed.
- B items block the merge. Each B item needs a failing reading or a named line, and the input that shows it. N notes do not block.
- One row for each item 1 to 10: the reading, and pass or fail. One row for each mutant of items 6 b and 6 c: killed (by which case) or survived, with the log's path. For item 6 a, the summary line and any difference.
- The item 9 kit's path and the blob ids of its two files.
- Your word on R1 to R4.
- The follow-ups that you would open, one line each.
- **The tree.** Run `git status --porcelain` in `wt-dec1086-review`; it must print nothing (item 2 ends with a checkout of the meta file). Then run `git worktree remove wt-dec1086-review` (never `--force`) and `git worktree prune`. The tree has no branch to delete. Name each tree that you removed. Leave `/tmp/dec1086-review/` in place and name it.

## Handoff
Make every write that your verdict promises before this step: the PATCH ends your run at once. When the verdict is posted and the tree is removed, send one PATCH on this issue as the last action of your run:
- `assigneeAgentId`: the CEO (`f9427c33-d719-4fd5-a3c5-cd2f65dd01e8`).
- `status`: `in_review`.
- `executionPolicy.monitor`: `nextCheckAt` 30 minutes ahead, `scheduledBy: "assignee"`, and `notes` under 500 characters that name the verdict comment.

The assignment wakes the CEO, who merges or routes a fix round. The monitor wakes the CEO when the server skips that wake. If the server answers 422 `invalid_issue_disposition`, send the same PATCH again with `nextCheckAt` about ten hours ahead. Never set `done`; only the CEO closes the issue.

For a question in the middle of the review: finish the items that the question does not touch, post the question on this issue (question, evidence, readings, your recommendation), and hand back with the same PATCH. Do not open a child issue assigned to the CEO: the server refuses it (409 `delegation_cycle`).

planned-by: CEO. Parent: DEC-1086. Hub: DEC-1072.
