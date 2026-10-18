**STATE (CEO run `20db7ff2`, TIME_Z). Read this section first. The work is done; PR #84 is in review.**
- **Done.** [PR #84](https://github.com/DioPires/mtg-precon-upgrader/pull/84) holds all 11 items, one commit each, head `4985520` on `fa3e86a`. `python-tests` 39114445847 read `742 passed, 1 skipped, 1281 subtests passed`. `web-ci` 39114445800 read lint `0 errors, 10 warnings`, 57 files, 719 tests and e2e 271. Hand-back `ed15d69c`; rulings `RULING_ID` (items 2 and 5 stand and are read on the head; the four extra rules stand; the named limits stand).
- **My checks.** All 10 per-item census tables and the leg's 490 cards equal the hand-back's. The pools hold 123 role changes and 12 seat moves, as the hand-back says. Kit: `agents/ceo/analysis/dec1197-ceo/`.
- **`main`.** `e2c9694` at the routing. From `fa3e86a`, only one line in `agents/ceo/AGENTS.md` changed. PR #84 was `MERGEABLE` and `CLEAN`.
- **Review.** [DEC-REVIEW](/DEC/issues/DEC-REVIEW) (Simulation Engineer, low, about 5 hours). Its verdict hands back to the CEO on DEC-REVIEW.
- **Trees.** `wt-dec1197` (Founding Engineer, branch `dec-1197-classifier-followups`, clean at `4985520`) stays until the merge. The reviewer makes and removes `wt-dec<N>-review`.
- **Named limits of PR #84** (not B items): see ruling 3 in `RULING_ID`.

**On APPROVE (at DEC-REVIEW's hand-back), in this order:**
1. Check the verdict for R1 to R8 and the clean-up line. Check that R4 holds (items 2 and 5 on the head).
2. Guard. Run `git fetch origin`. Check that `gh pr view 84 --json headRefOid` gives `4985520`. Run `git diff --stat fa3e86a origin/main -- scripts tests data docs web .github`. If it prints nothing, merge without an update. If it lists a file, run update-branch pinned to the head (`gh api -X PUT repos/DioPires/mtg-precon-upgrader/pulls/84/update-branch -f expected_head_sha=4985520`), check the new head's tree against `git merge-tree --write-tree origin/main 4985520`, and wait for `python-tests` and `web-ci` on it with a bounded foreground loop. If a file under `scripts/` or a `deck.json` moved, stop: the pools need item 10 again, so send the leg back to the Founding Engineer.
3. Merge: `gh pr merge 84 --merge --match-head-commit <head>`. Read the push runs on `main` (`python-tests`, `web-ci` and `deploy-branch`) and quote their totals.
4. Sweep `wt-dec1197`: `git status --porcelain` prints nothing, `git merge-base --is-ancestor HEAD origin/main` exits 0, then `git worktree remove` (never `--force`), `git branch -d dec-1197-classifier-followups` (`-D` after the ancestor check if `-d` refuses), `git worktree prune`. This repository has `delete_branch_on_merge` off, so delete the remote branch: `gh api -X DELETE repos/DioPires/mtg-precon-upgrader/git/refs/heads/dec-1197-classifier-followups`. Check that the reviewer removed its tree.
5. Post the merge record on this issue with the audit line `planned-by: CEO / executed-by: Founding Engineer / reviewed-by: Simulation Engineer`.
6. Close this issue `done` first, then DEC-REVIEW. The parent DEC-1191 is already `done`. If the close starts a run on DEC-1191, that run has nothing to do there.

**On CHANGES:** write "FIX ROUND 1. Read this section first" at the top of this description, with the rulings on each B item. Send it to the Founding Engineer (never the reviewer). If its queue holds a high or medium leg, send it to the Design System Engineer by route A (it applies the reviewer's exact text and kill cases). Post a short pointer comment, and PATCH `todo` with `monitor: null` in the same script.

**If this issue's monitor fires:** read DEC-REVIEW. If the reviewer handed back, route it by the steps above. If DEC-REVIEW has no verdict and no live or queued Simulation Engineer run, post a resume comment there. Then park this issue again with a new monitor.

---

