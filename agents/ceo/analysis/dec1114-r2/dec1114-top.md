**STATE, ROUND 2 (CEO run `a2fd47ea`, 2026-10-15 14:45Z). Read this block first. FIX ROUND 1 below is done; its merge steps are replaced by the steps here. The re-read is out on [DEC-1137](/DEC/issues/DEC-1137) with the Frontend Engineer.**

- **Done:** fix round 1, hand-back comment `bb2804ea`. PR #51 head `f9fc319` (round commits `7de5806` and `f9fc319`, plus three clean merges of `main`).
- **CEO checks at the hand-back (all passed, 14:40Z):**
  - The blob ids of the seven files equal the hand-back's table.
  - CI run 38751237753 on `f9fc319` reads `573 passed, 1 skipped, 1210 subtests passed`: the push run 38750194287 on `092197e` (551 and 1191), plus 15 and 15 from PR #51, plus 7 and 4 from the round.
  - `git merge-tree --write-tree origin/main f9fc319` is clean on `main` `4fdcbb8` (tree `3ed2bac0`), and the path guard since `2cedb4e` prints nothing.
  - Each merge commit's tree equals `git merge-tree --write-tree` of its parents.
  - The B1 lines equal the reviewer's patch. All ten names of the reviewer's kill files are on the head, except `StopLayoutMixin` (replaced by `BulkDataCase.check_stop_text_stands_on_its_own_line`).
- **Where the leg is:** DEC-1137 is `todo` with the Frontend Engineer. Its queue at 14:40Z: a live run on DEC-1135, then DEC-1142 and DEC-1140 (review of PR #55), all low. The server picks the order.
- **Merge order:** PR #32 and PR #46 are on `main`, and PR #51 carries their new text. PR #55 (DEC-1086) is open and conflicts with PR #51 in `scripts/build_price_index.py` (note `b040b060`). The DEC-1140 review builds the resolution as a kit (`dec1086-review/merge-kit/`) on PR #51's head of that moment.
- **At the verdict, on APPROVE:**
  1. Read `gh pr view 55 --json state,mergedAt` and `git diff --stat 2cedb4e origin/main -- scripts priv_data mcp-servers tests pytest.ini conftest.py pyproject.toml uv.toml .github`.
  2. If PR #55 is on `main`, do not merge. Send a merge round to the Simulation Engineer on this issue: merge `main`, take `main`'s `scripts/build_price_index.py` and the kit's two test files, run CI's command, push, hand back. Check the kit's README names `f9fc319`; if not, the kit needs a rebuild first.
  3. If the path guard prints a file, run `gh api -X PUT repos/DioPires/mtg-precon-upgrader/pulls/51/update-branch -f expected_head_sha=<head>` and watch CI on the new head.
  4. Run `gh pr merge 51 --merge --match-head-commit <head>`. Check that `main`'s tree equals `git merge-tree --write-tree origin/main <head>` read before the merge, and that the push run on `main` is green with the expected count.
  5. Delete the remote branch if GitHub did not: `gh api -X DELETE repos/DioPires/mtg-precon-upgrader/git/refs/heads/dec-1114-limiter-notes`.
  6. Remove `wt-dec1114`: `git -C wt-dec1114 status --porcelain` prints nothing (delete an untracked `mcp-servers/archidekt/uv.lock` first), and `git merge-base --is-ancestor HEAD origin/main` exits 0. Then run `git worktree remove wt-dec1114` (never `--force`), `git branch -D dec-1114-limiter-notes` and `git worktree prune`. Check that the verdict names the reviewer's removed trees.
  7. If PR #55 is still open, post on DEC-1086 that PR #51 is on `main`, so PR #55's merge round carries the resolution.
  8. Close DEC-1137, then this issue, with `planned-by: CEO / executed-by: Simulation Engineer / reviewed-by: Frontend Engineer`. The parent DEC-1092 is done, so no parent run starts.
- **At the verdict, on CHANGES:** this is the second failed review round. Tell the board in a comment on this issue what failed and why. Then put "FIX ROUND 2" at the top of this description, assign this issue to the Simulation Engineer (`todo`, `monitor: null`), and keep DEC-1137 with the CEO, `in_review`, with a monitor.
- **Fallback monitor:** 2026-10-15 18:15Z. If it fires while the re-read is still queued, re-park with a new monitor and do nothing else.

---

