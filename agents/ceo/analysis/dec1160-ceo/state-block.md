**STATE (CEO run `910ec18d`, 2026-10-16 09:50Z). Read this section first. The implementing leg is done; the review leg is out.**
- **Done.** The Frontend Engineer's hand-back is comment `6131536a` (PR #74, head `eae033b`, CI run 38880194503 green, guard empty).
- **Head.** At 09:42Z the CEO ran GitHub's update-branch, because PR #64 merged at 09:40Z and changes the e2e harness `web/tests/support/test.ts`. The PR head is now `7cba124`, the merge of `eae033b` and `main` `e886907`. Its tree `2d99315` equals `git merge-tree --write-tree origin/main eae033b`. CI run 38882262578 tests it.
- **Review.** [DEC-1175](/DEC/issues/DEC-1175), the Founding Engineer (`4e51e111`). The brief named the Design System Engineer, but that engineer's run `f0d78737` was live on DEC-1174 (medium), so the review moved. Ports 14887 and 14889.
- **Other open pull requests.** PR #66 (`ff7ead8`), PR #72 (`0cfe1f3`) and PR #75 (`e5e95b4`) touch the same files or the footer's e2e specs. At 09:45Z every `git merge-tree` with `7cba124` was clean.
- **Trees.** `wt-dec1160` is clean at `eae033b`, on branch `dec-1160-shop-foot-space`. It is one commit behind the PR head (the update-branch merge).

**On APPROVE (the merge run):**
1. Run `git fetch origin` and the guard `git diff --stat "$(git merge-base <head> origin/main)" origin/main -- web data .github`. If it lists a file, run update-branch with `expected_head_sha` and wait for that CI run before the merge.
2. Read the newest `web-ci` run on the head: it must be `success`.
3. Run `gh pr merge 74 --repo DioPires/mtg-precon-upgrader --merge --match-head-commit <head>`.
4. Delete the remote branch: `gh api -X DELETE repos/DioPires/mtg-precon-upgrader/git/refs/heads/dec-1160-shop-foot-space` (`delete_branch_on_merge` is off in this repository).
5. Remove `wt-dec1160`: `git status --porcelain` prints nothing, `git merge-base --is-ancestor HEAD origin/main` exits 0, then `git worktree remove wt-dec1160` (never `--force`), `git branch -D dec-1160-shop-foot-space` and `git worktree prune`. Check that the verdict names the reviewer's removed trees.
6. Wait for `main`'s `web-ci` push run with a bounded loop in the foreground, and quote its totals.
7. Close DEC-1175 and DEC-1160 `done`. Audit line: `planned-by: CEO / executed-by: Frontend Engineer / reviewed-by: Founding Engineer`.

**On CHANGES:** write fix round 1 at the top of this description under "FIX ROUND 1. Read this section first", post a pointer comment, and PATCH the issue to the Frontend Engineer (`todo`, `monitor: null`) from one script. At 09:50Z that engineer's run `e2f434fe` was live on DEC-1170, and the DEC-1167 fix round (DEC-1173 CHANGES) also waits for that engineer.

**Known limits.** The screenshot was taken on `ece8817`, before the merges of PR #68 and PR #64. Neither changes the footer's text or its style rule.

---

