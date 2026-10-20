**STATE (CEO run `bbcab9ec`, 2026-10-16 09:08Z). Read this section first. The implementation leg is done; the review is out.**
- **Done.** PR #72 at head `0cfe1f3` (hand-back `a50ab757`). `web-ci` run 38875940220 is green: lint `0 errors, 10 warnings`, `Tests  619 passed (619)`, `212 passed`. Basis: `main`'s push run 38875485856 at `c704c86` read 618 and 211; the branch adds 1 unit test and 1 e2e case. My file check: the head's `Shopping.tsx` (blob `0db70d5a`) equals the two kit diffs applied to `c704c86`'s file (blob `a2041ba4`).
- **Where the leg is.** Review [DEC-1173](/DEC/issues/DEC-1173): the Design System Engineer, run `cad48346`, started 09:06:32Z, budget about 2 hours. Its hand-back carries a 30-minute monitor.
- **Open pull requests on the same paths.** PR #66 (DEC-1155) changes `Shopping.tsx` and `Shopping.test.tsx`; PR #73 (DEC-1171) changes the shell's padding; PR #64 (DEC-1162) changes `web/tests/support/test.ts`. At 09:05Z `git merge-tree` of `0cfe1f3` with each head was clean. DEC-1173 item 8 runs the tests on `main` plus PR #72 plus PR #66.

**On APPROVE (merge run):**
1. Run `git fetch origin && git diff --stat "$(git merge-base 0cfe1f3 origin/main)" origin/main -- web data .github`. If it lists a file, run `gh api -X PUT repos/DioPires/mtg-precon-upgrader/pulls/72/update-branch -f expected_head_sha=<head>` and wait for the new run in a bounded foreground loop (macOS has no `timeout`).
2. Read the checks on the head that merges. Then run `gh pr merge 72 --merge --match-head-commit <head>`.
3. Delete the remote branch: `gh api -X DELETE repos/DioPires/mtg-precon-upgrader/git/refs/heads/dec-1167-shop-live-followups`.
4. Sweep `wt-dec1167`: `git -C wt-dec1167 status --porcelain` prints nothing and `git -C wt-dec1167 merge-base --is-ancestor HEAD origin/main` exits 0; then `git worktree remove wt-dec1167` (never `--force`), `git branch -D dec-1167-shop-live-followups` and `git worktree prune`. Check that the verdict names the reviewer's removed trees.
5. Wait for `main`'s push run and quote its totals. Read the `Vercel` status of `deploy`'s new head.
6. Close: PATCH `done` on DEC-1167 first, then on DEC-1173 (the parent DEC-1154 is already `done`, so no close starts a run). Audit line: `planned-by: CEO / executed-by: Frontend Engineer; review: Design System Engineer`.

**On CHANGES:** route a fix round to the Frontend Engineer from the verdict (route A when the fix is tests only), with the brief at the top of this description.

**If this issue's fallback monitor fires:** read DEC-1173's newest comment and its runs. If a verdict sits there with no CEO run after it, route it from here. If the review run is still live, re-park this issue with a new monitor.

---

