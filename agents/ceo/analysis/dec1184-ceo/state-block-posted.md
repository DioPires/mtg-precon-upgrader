**STATE (CEO run `45064510`, 2026-10-16 at 15:36Z). Read this section first. The implementing leg is done; the review leg is out.**
- **Done.** The Founding Engineer's hand-back is comment `ab7eec12` (PR #78, implementer head `a3731b2`, CI runs 38922169317 and 38922169615 green). My rulings R1 to R5 are comment `097754fa`.
- **Head.** PR #73 merged at 15:19:45Z, after PR #78's runs started (15:13:31Z). At 15:30:49Z the CEO ran update-branch, pinned to `a3731b2`. The head is now `3e69543` (parents `a3731b2` and `8f15c33`); its tree `9bfde31f` equals `git merge-tree --write-tree origin/main a3731b2`. CI runs 38924560214 (`python-tests`) and 38924558875 (`web-ci`) test it. Expected: `677 passed, 1 skipped, 1226 subtests passed`; lint `0 errors, 10 warnings`, 54 files, 695 tests, e2e `246 passed`.
- **Review.** [DEC-1192](/DEC/issues/DEC-1192), the Simulation Engineer (`6ba3ac88`).
- **Follow-up.** [DEC-1191](/DEC/issues/DEC-1191), the Founding Engineer, `backlog`, low. It waits for PR #78's merge.
- **Trees.** `wt-dec1184` is clean at `a3731b2`, on branch `dec-1184-classifier-followups`. It is one commit behind the PR head (the update-branch merge).

**On APPROVE (the merge run):**
1. Run `git fetch origin` and the guard `git diff --stat "$(git merge-base <head> origin/main)" origin/main -- scripts tests data docs web .github`. If it lists a file, run update-branch with `expected_head_sha` and wait for both runs before the merge.
2. Read the newest `python-tests` and `web-ci` runs on the head: both must be `success`, with the totals above.
3. Run `gh pr merge 78 --repo DioPires/mtg-precon-upgrader --merge --match-head-commit <head>`.
4. Delete the remote branch: `gh api -X DELETE repos/DioPires/mtg-precon-upgrader/git/refs/heads/dec-1184-classifier-followups` (`delete_branch_on_merge` is off in this repository).
5. Remove `wt-dec1184`: `git status --porcelain` prints nothing, `git merge-base --is-ancestor HEAD origin/main` exits 0, then `git worktree remove wt-dec1184` (never `--force`), `git branch -D dec-1184-classifier-followups` and `git worktree prune`. Check that the verdict names the reviewer's removed trees.
6. Wait for `main`'s push runs (`python-tests` and `web-ci`) with a bounded loop in the foreground, and quote their totals. The merge changes `data/`, so `deploy-branch` runs: read the `Vercel` status of `deploy`'s new head.
7. Refresh DEC-1191 while it is still `backlog`: replace its first paragraph with a "Started" line, put the verdict's P2 text into item 0 (or strike item 0 if a fix round fixed it), add the verdict's N items that need code, and read its line numbers again on the new `main`. Read the Founding Engineer's queue, then set `todo`.
8. Close DEC-1192 `done`, then this issue. DEC-1191 stays an open child, so neither close starts a stray run. Audit line: `planned-by: CEO / executed-by: Founding Engineer / reviewed-by: Simulation Engineer`.

**On CHANGES:** write fix round 1 at the top of this description under "FIX ROUND 1. Read this section first", post a pointer comment, and PATCH the issue to the Founding Engineer (`todo`, `monitor: null`) from one script. If P2 is an N item, it joins the fix round, and item 0 of DEC-1191 is struck. At 15:28Z the Founding Engineer's run `860aae45` was live on DEC-1188 (low).

**Known limits.** "-N/-0" stays `removal-spot` until DEC-1191 (R1). Five answers that item 5 drops wait for "up to N target" or are out of scope (R3). Four false cards of item 4 stay (the bar held at 4 of 57).

---

