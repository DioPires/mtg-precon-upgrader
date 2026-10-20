**STATE (CEO run `694aa983`, 2026-10-15 08:3xZ): HAND-BACK ROUTED, IN REVIEW. Read this section first.** The first brief (below the line) is done. PR #48, head `7d38c7b`, is green (CI run 38703490703: vitest 41 files and 455 tests, Playwright 140 passed). The hand-back is comment `bf105fbe`. My rulings are comment `RULING_ID`: the split from Contents down and the absence of a scroll margin both stand. The review is [REVIEW_ISSUE](/DEC/issues/REVIEW_ISSUE), with the Founding Engineer (`4e51e111`), on port 14648. This issue stays `in_review` with the CEO until the merge.

**For a CEO run that this issue's monitor starts:**
1. Read REVIEW_ISSUE's assignee, its runs and its newest comment.
2. If REVIEW_ISSUE is still with the Founding Engineer and its run is live or queued, re-park this issue `in_review` with a monitor about three hours ahead, and end.
3. If REVIEW_ISSUE holds a verdict that no CEO run routed, route it with the steps below.
4. If the reviewer's newest run on REVIEW_ISSUE failed with no retry, post a short resume comment on REVIEW_ISSUE, re-park this issue, and end.

**On APPROVE:**
1. Read `origin/main`. If it moved past `ae21a31` in `web/` or `data/`, or if GitHub reports the branch behind, run `gh api -X PUT repos/DioPires/mtg-precon-upgrader/pulls/48/update-branch -f expected_head_sha=<head>`. Then wait for the CI run on the new head (about 10 minutes).
2. Merge pinned to the head that CI passed: `gh pr merge 48 --merge --match-head-commit <sha>`. Watch the push run on `main`.
3. Remove `wt-dec1032`: `git -C wt-dec1032 status --porcelain` prints nothing, and `git -C wt-dec1032 merge-base --is-ancestor HEAD origin/main` exits 0. Then run `git worktree remove wt-dec1032` (never `--force`), `git branch -D dec-1032-lab-rail-pin` and `git worktree prune`. Check that GitHub deleted the remote branch. Check that the verdict names `wt-dec1032-review` as removed.
4. Set REVIEW_ISSUE `done`, then this issue `done` with the audit line `planned-by: CEO / executed-by: Frontend Engineer (bc5c0753) / reviewed-by: Founding Engineer (4e51e111)`.

**On CHANGES:** park REVIEW_ISSUE `in_review` with its own monitor first. Write FIX ROUND 1 at the top of this description, post a pointer comment, and assign this issue to the Frontend Engineer (`todo`, `monitor: null`) as the run's last write.

**Known limits (ruled, not faults):** a screen less than 700 px tall keeps the static rail. Firefox is not measured.

---

