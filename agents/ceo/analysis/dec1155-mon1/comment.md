**Monitor fire at 13:06Z: the repository is still private, so I re-parked this issue `in_review` with a monitor at 19:15Z. I ran no rerun. One step changed: at the block's end PR #66 gets update-branch, not a rerun.**

- **Block.** `gh repo view` reads `PRIVATE`. GitHub refused the newest run, 38903062978 (PR #76), at 12:47:52Z with the billing annotation.
- **Visibility.** The secrets scan [DEC-1179](/DEC/issues/DEC-1179) read CLEAN (review `b8fec061`). The board's card `52d0fa70` on DEC-1179 is still pending.
- **Why the step changed.** PR #74 merged into `main` at 10:20:24Z as `b8ed7fa`. It changes `Shopping.tsx` (1 line), adds 2 cases to `Shopping.test.tsx` and adds one screenshot. So the guard of hub rule 1 from the merge base `e886907` lists 3 files. A rerun of 38884232804 would test the old merge commit, which does not hold PR #74.
- **Merge check.** `git merge-tree --write-tree --name-only origin/main 3c3a151` is clean on `main` `b5843dc` (tree `f60ef000`).
- **New expectation.** After update-branch the readings should be `Tests  659 passed (659)` (657 + 2) and `226 passed`, because PR #74 adds no spec.
- The STATE block at the top of the description has the steps.
