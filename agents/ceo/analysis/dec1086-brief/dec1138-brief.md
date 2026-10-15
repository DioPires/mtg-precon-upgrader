**Backlog. Nothing starts this issue yet. The CEO sets `todo` at the close-out of [DEC-1086](/DEC/issues/DEC-1086), because DEC-1086 is the same engineer's leg and the owner sees its result.** If you find this issue `todo` with this paragraph still at the top, the owner started it: do the work, and read the line numbers again on your tree.

**Outcome wanted.** The suite checks the order check of `scripts/fetch_card_metadata.py` against two pages that Scryfall really sent, not only against the fake's model. Implementer: Simulation Engineer (`6ba3ac88`). Reviewer: the CEO names one at the hand-back, not you. One pull request; tests only. Tier 1, priority low. Budget about 1 hour.

## Why
- DEC-1112 note N8 (verdict `59b3d5a0`): the suite holds no saved Scryfall page, so only the review kit checked the fake's model of Scryfall's order. My ruling `773e9c70` accepted it as this follow-up.
- PR #32 merged as `4a21353` on 2026-10-15. Since then `FirstPageProofCases` in `tests/test_fetch_other_printings.py` builds every page by hand (`run_pass`, line 426 at `4a21353`).
- The order changed once already: run 1 sent no `dir` and got the printings without a key last; run 2 sent `dir=asc` and got them first (ruling `7cdc61ee` on DEC-1079).

## Sources (read only)
Both are Forest `usd` searches, answer 37 of each run, in `$PAPERCLIP_GITHUB_HOST_HOME/.paperclip/instances/default/workspaces/6ba3ac88-12e8-41a7-834f-98e3d92dae78/dec1079-scratch/live/`:
- `run2/answer-37.json` (`dir=asc`, 851,568 bytes): `has_more` true, 175 printings. The first 100 have no sort key, then 75 keys from the cheapest up. Printings 98 to 106 (from 1) are three with no key (`wc01`, `wc01`, `olep`, all `memorabilia`), then `m20`, `c15`, `dtk` and `m14` at `usd` 0.09, then `war` and `hou` at 0.10.
- `run1/answer-37.json` (no `dir`, 889,666 bytes): `has_more` true, 175 printings, all with a key, most expensive first. The last six are `wc02` 1.82, `wc03` 1.79, `cma` 1.74, `brb` 1.74, `wc97` 1.72 and `zen` 1.60.

## Ask
1. Write `tests/fixtures/scryfall/forest-usd-run2-trimmed.json`: the run 2 page with `data` cut to printings 98 to 106 (nine cards). Keep every other top-level key and value as Scryfall sent it, and keep each kept card whole and unchanged, in Scryfall's order.
2. Write `tests/fixtures/scryfall/forest-usd-run1-trimmed.json` the same way: the run 1 page with `data` cut to its last six printings.
3. Commit the small script that cuts them (`tests/fixtures/scryfall/trim_page.py`, with the source path, the slice and the date in its docstring). pytest collects only `test_*.py`, so the script is not a test.
4. Add two cases to `FirstPageProofCases`, each through `run_pass` with `raw_page` set to the fixture's `data`:
   - (a) The run 2 page. Expect `usd` 0.09 and no line that holds "does not prove".
   - (b) The run 1 page, sent for a request with `dir=asc`. Expect `usd` `None` and the line `    Forest: the first page does not prove the lowest usd price: no price taken`.
   - Name the source file and the slice in each case's docstring.
5. Mutants, each on a clone of your tree with `PYTHONDONTWRITEBYTECODE=1` after you remove every `__pycache__`, against `tests/test_fetch_other_printings.py`:
   - T1, the old check (printings without a key last): case (a) must fail.
   - T8, the check wants the most expensive first: case (a) must fail.
   - T11, the order is not checked: case (b) must fail (it takes 1.60 from `zen`).
   - Give a table: mutant, change, result, the case that fails, the log's path.

## Rules
1. Send no request to a Scryfall host, and use no card tool.
2. Start no browser and no preview server.
3. Export `HOME="$PAPERCLIP_GITHUB_HOST_HOME"` for every `git` and `gh` command. Use `uv run` for every Python command.
4. Work in `wt-dec1138` only. Keep scratch files in `/tmp/dec1138/`.
5. Run one pytest process at a time, and export a new, empty `SCRYFALL_LIMIT_DIR` for each run.
6. Change no file under `scripts/` and no data file.

## Setup
1. `cd /Users/dpires/Documents/Personal/code/mtg-precon-upgrader`
2. `git fetch origin`
3. `git worktree add -b dec-1138-saved-pages wt-dec1138 origin/main`
4. The suite is CI's command, from the tree's root: `CI=true uv run --with pytest python -m pytest -q -rfEs`. On `main` at `4a21353`, CI's push run 38716323591 reads `486 passed, 1 skipped, 1189 subtests passed`. Expect two more passed. If `main` gained tests, add them and name the cause.

## Hand-back
Before the hand-back PATCH: `git fetch origin`, then `git diff --stat "$(git merge-base HEAD origin/main)" origin/main -- scripts tests pytest.ini`. It must print nothing. If it prints, merge `main` (no rebase), run the suite again, push and wait for CI.

Post one comment that holds:
- the pull request number, its head, and the blob id of each file that it adds or changes;
- the SHA-256 of each source page, and for each fixture the slice and its byte size;
- the suite's count line, and CI's run id with its total line;
- the mutant table.

## Handoff
- Post the hand-back comment first. Then send one PATCH on this issue as the last action of your run: `assigneeAgentId` the CEO (`f9427c33-d719-4fd5-a3c5-cd2f65dd01e8`), `status` `in_review`, and `executionPolicy.monitor` with `nextCheckAt` 30 minutes ahead, `scheduledBy: "assignee"`, and `notes` under 500 characters that name the hand-back comment.
- If the server answers 422 `invalid_issue_disposition`, send the same PATCH again with `nextCheckAt` about ten hours ahead. Never set `done`.
- For a question in the middle of the leg: do the parts that it does not touch, commit and push, post the question on this issue (question, evidence, readings, your recommendation), and hand back with the same PATCH. Do not open a child issue assigned to the CEO: the server refuses it (409 `delegation_cycle`).

## CEO: at the hand-back
The Simulation Engineer does nothing under this heading.
1. Check each fixture against its source by script: the top-level keys equal, and `data` equals the named slice of the source's `data`.
2. Run the three mutants on a scratch clone and read CI. Then name the reviewer, who is not the implementer. For a tests-only change whose assertions all come from saved pages, a checklist review by the CEO on these two checks is enough.

planned-by: CEO. Parent: DEC-1079. Source: DEC-1112 N8 (verdict `59b3d5a0`), ruling `773e9c70`.
