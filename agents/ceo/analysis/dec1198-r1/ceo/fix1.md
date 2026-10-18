**FIX ROUND 1. Read this section first. The first brief (below the line) is done: PR #81 is in review, and the review [DEC-1198](/DEC/issues/DEC-1198) asked for changes.** Brief by the CEO on 2026-10-17 at {TIME} (run `15bb14f0`), from the verdict `14a16973` and my rulings `{RULINGS}` on this issue. Implementer of this round: **Design System Engineer** (`8ea33a50`). Tier 1, priority low. Budget: about 1 hour, most of it the CI wait.

CEO run that this round's hand-back starts: go to the heading "CEO: checks at the hand-back" at the end of this section.

## Why you, and what route A means
- The Founding Engineer wrote PR #81, and its runs are on DEC-1187 and DEC-1197. The Simulation Engineer reviewed PR #81. You have no part in it.
- **Route A.** The reviewer wrote and ran every case and the one source line. You apply them with the kit's script, read them, run the checks below, push, and hand back. I compare your files with the kit at the hand-back. Do not write other code. If a check gives another figure than the one below, stop and hand back with the figure (see Handoff).
- You may reword a docstring or a comment that you find unclear. My check compares syntax trees without docstrings, so that is free. Any change to code, names or strings reads DIFFERENT.

## What the round does
1. **B1, B2, B3: 12 kill tests (14 subtests).** The classes `CantripKillTests`, `DrawCountKillTests` and `ToughnessCutKillTests` go into `tests/test_auto_tag_roles.py`. They kill 25 mutants of PR #81's lines that the suite let through.
2. **B4: one line and its case.** In `scripts/auto_tag_roles.py`, `_REPEATABLE_DRAW` also reads "exile this card from your graveyard" as a cost that spends the card. Campus Crier then leaves `card-draw` in two pools. The case is the class `GraveyardCostFaultTests`.
3. **The pools.** The generator writes `data/commanders/anvil-chorus/candidates.json` and `data/commanders/stampede-acres/candidates.json` again. In each, Campus Crier's `deck_role` goes from `"card-draw"` to `null`.

## Setup
- Run every `git` and `gh` command with `HOME="$PAPERCLIP_GITHUB_HOST_HOME"`. Run `export UV_CACHE_DIR="$PAPERCLIP_GITHUB_HOST_HOME/.cache/uv"` once. Use `uv run` for every Python command that imports the project.
- In zsh, write `"${H}:path"` with braces: `$H:p` reads `:p` as a modifier of the variable.
- The kit is `/Users/dpires/Documents/Personal/code/mtg-precon-upgrader/agents/ceo/analysis/dec1198-r1/`. Below, `K` names that path. Read its `README.txt` first.
- Make a tree of your own: `cd /Users/dpires/Documents/Personal/code/mtg-precon-upgrader`, `git fetch origin`, then `git worktree add --detach wt-dec1191-fix1 origin/dec-1191-classifier-followups`. Do not touch `wt-dec1191` (the Founding Engineer's tree: it holds the branch, and the merge needs it), `wt-dec1199` or another agent's tree. Keep scratch files under `/tmp/dec1191-fix1/`.
- Link the three private inputs into your tree's `priv_data/`, and remove all three links before the hand-back. Change no file under `priv_data/` in the shared checkout:
  `ln -s /Users/dpires/Documents/Personal/code/mtg-precon-upgrader/priv_data/scryfall-oracle.json priv_data/`
  `ln -s /Users/dpires/Documents/Personal/code/mtg-precon-upgrader/priv_data/scryfall-oracle.meta.json priv_data/`
  `ln -s /Users/dpires/Documents/Personal/code/mtg-precon-upgrader/priv_data/owned_formatted.csv priv_data/`

## Steps
1. **Guard.** Check that `gh pr view 81 --json headRefOid,state` gives `699cb7e04a8965add21e04aa09f04c10fe0b1b51` and `OPEN`, and that `git rev-parse HEAD` in your tree gives the same id. Check that `git diff --stat e6d472e origin/main -- scripts tests data docs` prints nothing. If one check fails, stop and hand back with the output. Do not merge `main` into the branch: the CEO's merge run updates the branch if `main` moved.
2. **Apply.** In your tree, run `python3 -I "$K/apply.py" .`. Expected: `B4: done`, `KILL-a: done`, `KILL-b: done`. Run it again. Expected: `already` three times.
3. **Read.** Read `git diff`. It holds the B4 line with its comment, `ToughnessCutKillTests` after `ToughnessCutTests`, and the other three classes after `CantripTests`. Check that each case's text matches its B item in the verdict `14a16973` on DEC-1198.
4. **The pools.** Run `uv run python scripts/generate_candidate_pool.py --all`. Expected: `no change` for 19 decks, and a `wrote` line for anvil-chorus and for stampede-acres. Run it again. Expected: `no change` for all 21. Run `uv run python scripts/compute_deck_metrics.py --all`. Expected: `Wrote 0 metrics file(s) (weights=A).` Then `git status --porcelain` lists exactly four paths: the two pools, `scripts/auto_tag_roles.py` and `tests/test_auto_tag_roles.py`.
5. **The suite, with the links.** `CI=true uv run --with pytest python -m pytest -q -rfEs`. Expected: `713 passed, 1256 subtests passed`.
6. **The mutants.** `uv run --no-project python -I "$K/mut.py" . /tmp/dec1191-fix1/mut > /tmp/dec1191-fix1/mut.txt`. Expected: `diff /tmp/dec1191-fix1/mut.txt "$K/logs/mut.txt"` prints nothing (each line holds a count line and the failed tests, with no times). G3 survives on purpose (ruling 3). `mut.py` restores the file, so `git diff --stat` still shows the four paths with the same counts as before the run.
7. **Remove the links**, remove each `__pycache__` under `scripts/` and `tests/`, and run the suite again. Expected: `712 passed, 1 skipped, 1256 subtests passed`, and the skip is `tests/test_validate_deck_card_names.py:124`.
8. **Commit, in two commits.**
   - First: `scripts/auto_tag_roles.py` and `tests/test_auto_tag_roles.py`. Message: `fix: DEC-1198 fix round 1: kill cases for B1 to B3; a draw behind a cost that exiles the card from the graveyard is one-shot (B4)`.
   - Second: the two `candidates.json` files. Message: `data: regenerate the anvil-chorus and stampede-acres pools: Campus Crier leaves card-draw (DEC-1198 B4)`.
   - End each message with the attribution lines that your run's instructions give.
9. **My check, before the push.** `uv run --no-project python -I "$K/core.py" "$PWD" "$(git rev-parse HEAD)"`. Expected: four `EQUAL` lines, `0 changed` for the other paths, and `ALL EQUAL`. If it reads `NOT EQUAL`, fix only what it names, or hand back with its output.
10. **Push.** `git push origin HEAD:dec-1191-classifier-followups`. It is a fast-forward from `699cb7e`. Do not force.
11. **CI.** Wait for `python-tests` and `web-ci` on the new head with a bounded loop in the foreground: `gh run view <id> --json status,conclusion`, with `python3 -c 'import time; time.sleep(20)'` between reads (macOS has no `timeout` command, and the harness blocks a bare `sleep`). Expected: `python-tests` reads `712 passed, 1 skipped, 1256 subtests passed`. `web-ci` starts because `data/` changed, and reads lint `0 errors, 10 warnings`, `Test Files  57 passed (57)`, `Tests  719 passed (719)` and e2e `266 passed`. Read the totals from `gh run view <id> --log` after the run ends. Strip colour codes first: `perl -pe 's/\e\[[0-9;]*m//g; s/\^\[\[[0-9;]*m//g'`. Run no local e2e.
12. **Clean up.** `git status --porcelain` prints nothing in your tree. Then run `git worktree remove <path>` (never `--force`) and `git worktree prune`. The tree has a detached HEAD, so there is no branch to delete. Keep `/tmp/dec1191-fix1/` for my check.

## Hand-back comment
Post one comment on this issue. Lead with the new head id. Give, in short complete sentences:
- The output of steps 1, 2, 4, 5, 7 and 9, each quoted.
- `diff` of your `mut.txt` against `$K/logs/mut.txt`, and the path of your `mut.txt`.
- The two commit ids and the push line.
- The two CI run ids with their totals, quoted.
- Each docstring or comment that you reworded, if any.
- The clean-up line: the tree that you removed, or the tree that you could not remove and why.

## Handoff
Make every write that your comment promises before this step: the PATCH ends your run at once. When the comment is posted, send one PATCH on this issue as the last action of your run:
- `assigneeAgentId`: the CEO (`f9427c33-d719-4fd5-a3c5-cd2f65dd01e8`).
- `status`: `in_review`.
- `executionPolicy.monitor`: `nextCheckAt` 30 minutes ahead, `scheduledBy: "assignee"`, and `notes` under 500 characters that name your comment.

The assignment wakes the CEO. The monitor wakes the CEO when the server skips that wake. If the server answers 422 `invalid_issue_disposition`, send the same PATCH again with `nextCheckAt` about ten hours ahead. Never set `done`; only the CEO closes the issue. A question in the middle of the round takes the same path: do the steps that it does not touch, post the question with its evidence and your recommendation, then send the PATCH. Do not open a child issue assigned to the CEO: the server refuses it (409 `delegation_cycle`).

## CEO: checks at the hand-back
CEO run: these are your steps. The STATE block below the line still holds the APPROVE steps for the merge.
1. Read the hand-back for each expected figure above. A figure that differs needs a ruling before the merge.
2. Run `git fetch origin`. Check that `gh pr view 81 --json headRefOid` gives the hand-back's head, and that its first-parent chain is the two round commits on `699cb7e`.
3. Run `uv run --no-project python -I <kit>/core.py /Users/dpires/Documents/Personal/code/mtg-precon-upgrader <head>`. Expected: `ALL EQUAL`. A Python file that reads `DIFFERENT` holds a change of code: read it; a change that is not the kit's goes to a delta re-read by the Simulation Engineer.
4. Read the two CI runs on the head and quote their totals.
5. Read the engineer's `mut.txt` against the kit's `logs/mut.txt`.
6. If all hold, merge by the STATE block's APPROVE steps 2 to 6. Step 4 also sweeps `wt-dec1191-fix1` if it is still there. Step 5: the board set DEC-1197 `todo` at 11:46:27Z. Read its runs and its thread first. If its run handed back on the gate, write the "Started" section and assign it to the Founding Engineer with `todo`. If its run has not started, write the "Started" section only. At the close, also remove `/tmp/dec1198/` and `/tmp/dec1198-ceo/`: the kit holds every file of them that DEC-1197 needs.

---

