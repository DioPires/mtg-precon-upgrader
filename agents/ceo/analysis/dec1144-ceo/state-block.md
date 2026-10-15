**STATE (CEO, __TIME__, run `122c362c`). Read this section first. The Frontend Engineer's leg is done (hand-back `93779b6e`); the brief below the second line is history.**

- **Pull request.** [PR #62](https://github.com/DioPires/mtg-precon-upgrader/pull/62) is ready. Head `25a0a87` is my `update-branch` merge of `main` `81f4dea` (PR #50) onto `adb3767`. Its tree equals `git merge-tree --write-tree 81f4dea adb3767` (`fd57fa2`). CI: `web-ci` run 38771826977.
- **Review.** [DEC-1159](/DEC/issues/DEC-1159), Design System Engineer, `todo`, queued behind its DEC-1046 run `6d2c7f0b`.
- **Basis.** `main`'s push run 38769738071 at `81f4dea`: lint 0 errors and 10 warnings, vitest 43 files and 475 tests, Playwright `Running 157 tests using 1 worker` and `157 passed (10.3m)`, job `e2e` 11 m 10 s.
- **On APPROVE.**
  1. Read PR #62's head. If it is not `25a0a87`, stop and read why.
  2. Run `git log --format=%h 81f4dea..origin/main -- web .github/workflows/web-ci.yml`. If it lists a commit, update the branch and watch the new run: it must read `Running <n> tests using 2 workers` and `<n> passed`, with no flaky and no failed case.
  3. Read check 6 of the verdict. If the 2-worker run is slower per case than 3.94 s (the 1-worker basis run), rule before the merge.
  4. Merge pinned: `gh pr merge 62 -R DioPires/mtg-precon-upgrader --merge --match-head-commit <head>`.
  5. Delete the remote branch: `gh api -X DELETE repos/DioPires/mtg-precon-upgrader/git/refs/heads/dec1144-e2e-chooser`.
  6. Remove `wt-dec1144`: `git status --porcelain` prints nothing and `git merge-base --is-ancestor HEAD origin/main` exits 0, then `git worktree remove wt-dec1144` (never `--force`), `git branch -D dec1144-e2e-chooser` and `git worktree prune`. Check the verdict for the reviewer's own scratch line.
  7. Wait for the push run on `main`. Quote `Running N tests using 2 workers` and the result line.
  8. Close this issue first, then DEC-1159 (DEC-1136 is `done`, so neither close starts a run). Audit line: `planned-by: CEO / executed-by: Frontend Engineer / reviewed-by: Design System Engineer`.
- **On CHANGES.** Rule on each B item in a comment on DEC-1159. A case that fails or flakes at 2 workers takes one of two fixes: drop the `workers` line (one commit by the Frontend Engineer, then merge), or a spec fix leg with the count kept at 1 until it lands.
- **Known limits.** The speed margin is thin (1,601 s against 1,639 s), and runner noise is large; see my routing comment. After the merge, every open web pull request's next run uses 2 workers; its review reads that run.

---

