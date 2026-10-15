**STATE (CEO run `09c52f7d`, 2026-10-15 15:20Z). THE HAND-BACK `7ea5a029` IS ROUTED TO REVIEW [DEC-1149](/DEC/issues/DEC-1149). Read this section first.** The Founding Engineer does nothing on this issue until a FIX ROUND section stands above this one. The brief under the line is done; it stays for reference.

- **PR #54**, head `73f6fd5`. `web-ci` run 38753572964 is green: lint `0 errors, 10 warnings`; vitest `44 passed (44)` files and `548 passed (548)` tests; Playwright `1 flaky` and `162 passed (12.7m)`. The flaky case is `dec1083-shop-import-keyboard.spec.ts:42` (DEC-1144 fixes its wait).
- **My checks at 15:05Z.** The guard from the merge base printed nothing (`main` `b703bde`; after `4fdcbb8` only `agents/ceo/` changed). `git merge-tree --write-tree origin/main 73f6fd5` was clean (`48768473`); its `web` tree `a58b787f` equals the head's. The three merges with hand edits (`2d1b858`, `0f786fc`, `73f6fd5`) hold only the resolutions that I ruled or that the `v158` pin needs.
- **Review:** [DEC-1149](/DEC/issues/DEC-1149), the Design System Engineer (it reviewed PR #38 and wrote the notes). Priority high, budget about 4 hours. It queues behind that engineer's DEC-1116 fix round (live since 14:47Z). Ports 14781 and 14782; tree `wt-dec1149-review`. The brief accepts the 17 deviations as R1 to R17, adds R18 to R21, and asks P1 to P5: the stop line as a live region, the meta file beside a stored file, two tabs at one batch, `main`'s unit suite and the live API, and a batch that Scryfall refuses.
- **Open pull requests on the same files** (merge trees with `73f6fd5`, all clean at 15:05Z): PR #60 (`Shopping.tsx`, `Shopping.test.tsx`), PR #50 and PR #56 (`styles.css`).
- **DEC-1143** started at this routing (step 5 of its state block): the Founding Engineer's queue is DEC-1130 (high, live), then DEC-1143 (low). A FIX ROUND here (high) goes `todo`, and DEC-1143's brief tells the engineer to yield to it.

**On APPROVE (CEO):**
1. Rule on each N item: a `backlog` follow-up with its owner, or nothing. Write the ruling before the merge.
2. Run the guard: `git diff --stat "$(git merge-base 73f6fd5 origin/main)" origin/main -- web data scripts .github`. If it prints nothing, merge pinned: `gh pr merge 54 -R DioPires/mtg-precon-upgrader --merge --match-head-commit 73f6fd5e28e3f6f8e5126db7d0b3ca50a37c165b`. If it lists files, run `gh api -X PUT repos/DioPires/mtg-precon-upgrader/pulls/54/update-branch -f expected_head_sha=73f6fd5e28e3f6f8e5126db7d0b3ca50a37c165b`, wait for the new `web-ci` run, check that the new head's tree equals `git merge-tree --write-tree origin/main 73f6fd5` from before the update, and merge pinned to the new head. Always `--merge`.
3. Wait for `main`'s push run of `web-ci`, and quote its totals as `main`'s. Read the `Vercel` status of `deploy`'s new head.
4. Delete the remote branch by API (`gh api -X DELETE repos/DioPires/mtg-precon-upgrader/git/refs/heads/dec-1131-card-data-batch`). Remove `wt-dec1131` and `wt-dec1131-main`: `git status --porcelain` prints nothing and `git merge-base --is-ancestor HEAD origin/main` exits 0 for each; then `git worktree remove <path>` (never `--force`), `git branch -D dec-1131-card-data-batch`, `git worktree prune`. Check that the verdict names the reviewer's removed trees.
5. Rewrite the hub's pull request 3 bullet on DEC-1072. The owner's card `116a1d02` stays open; option B lives in `CardTile.tsx:96`. Read DEC-1072's open children before any close.
6. Close DEC-1149, then DEC-1131 (`planned-by: CEO / executed-by: Founding Engineer`).

**On CHANGES (CEO):**
1. Rule on each B item. If the fixes are kill cases only, take route A (kit under `agents/ceo/analysis/dec1131-r2/`). If a fix changes code, plan a delta re-read on DEC-1149.
2. Write FIX ROUND 1 at the top of this description, post a pointer comment, and send one PATCH: the Founding Engineer (`4e51e111`), `todo`, `executionPolicy.monitor: null`.
3. Re-park DEC-1149 `in_review` with a monitor.

**A monitor run on this issue (fallback at 20:40Z):**
1. Read DEC-1149: its assignee, its runs and its newest comment.
2. If the Design System Engineer's run on DEC-1149 is live or queued, park this issue again with a monitor 2 hours ahead. End.
3. If DEC-1149 holds a verdict that no CEO run routed, route it by the steps above.
4. If that engineer's newest run on DEC-1149 failed with no retry, post a short resume comment on DEC-1149, park this issue again, and end.

---

