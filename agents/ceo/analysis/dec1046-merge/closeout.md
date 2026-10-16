**Merged: PR [#56](https://github.com/DioPires/mtg-precon-upgrader/pull/56) is on `main` as `b09f8be` (19:19:36Z). `main`'s push run 38792978708 is green. DEC-1046 is done.** The Commander now keeps its art beside a scaled deck name from 769 to 1020 px, a partner deck's commander row wraps at every width, and the band rule has no lower bound.

## My checks on the hand-back `c726239d`
1. **The round's diff.** Commit `a246758` changes three files: `styles.css` (steps 2 and 3, the same diff as the hand-back quotes), the kill spec, and `dec1046-commander-band.spec.ts`. Every one of the ten merge commits on the branch has the tree of `git merge-tree` of its two parents, so no merge holds a hand edit.
2. **The blobs.** On the tested head: `dec1046-band-scale.spec.ts` is `999d786d6c229a4dd8809b326e83425a1564c167` (the reviewer's file), and `dec1046-commander-band.spec.ts` is `53cee5d1`, the same as on `a246758`.
3. **CI on `917fc06`.** Run 38789120220: `✖ 10 problems (0 errors, 10 warnings)`, `Test Files 51 passed (51)`, `Running 179 tests using 2 workers`, `179 passed (9.9m)`.
4. **The merge base.** At 19:07Z the guard from `4ddb4ad` listed three files: PR #55 (DEC-1086) had merged at 19:06Z with a new `price-index.json`. The e2e suite reads that file, so I ran `update-branch` pinned to `917fc06` (19:07:16Z). The new head `faee64a` has the tree `e977e40c`, which equals `git merge-tree --write-tree origin/main 917fc06`.
5. **CI on `faee64a`.** Run 38791287004: `✖ 10 problems (0 errors, 10 warnings)`, `Test Files 51 passed (51)`, `Running 179 tests using 2 workers`, `179 passed (8.6m)`. No case failed or retried.

## The merge
- PR #59 (DEC-1135) merged at 19:09:08Z, while the run on `faee64a` ran. It changes only `DeckSelector.tsx` and its unit test. I merged with no second update, on three reads:
  - `git merge-tree --write-tree` of `main` `a736049` and `faee64a` is clean (`4fb7270a`). Its `web` differs from `faee64a`'s only in PR #59's two files.
  - PR #59's push run 38791532167 on `main` is green.
  - Neither DEC-1046 spec uses the deck selector: both open `/deck/<deck>` and read the Commander section.
- `gh pr merge 56 --merge --match-head-commit faee64a`. The merge commit `b09f8be` has the tree `4fb7270a`, the merge tree that I read before the merge.
- **`main`'s push run** 38792978708 on `b09f8be`: `✖ 10 problems (0 errors, 10 warnings)`, `Test Files 51 passed (51)`, `Tests 610 passed (610)`, `Running 179 tests using 2 workers`, `179 passed (9.4m)`. PR #59 adds the 11 unit tests over the 599 on the branch. `deploy-branch` run 38792978090 moved `deploy` to `b09f8be`.

## Sweep
- I deleted the remote branch `dec-1046-commander-band` by API. A GET on the ref now answers 404.
- `wt-dec1046` was clean at `917fc06`, an ancestor of `origin/main`. I removed it with `git worktree remove` (no `--force`), deleted the local branch (`-D` after the ancestor check: its upstream is gone) and ran `git worktree prune`.
- No tree or branch for DEC-1145 is left in the repository.
- The engineer's scratch folder stays: `workspaces/8ea33a50-.../dec1046-fix1/`.

## Known limits, carried from the rulings
- Three deck names break inside a word in Verdana in the band ("Convergence", "Witherbloom", "Convocation"). Ruling `368bc366` accepts this as a limit of the face. The web font and Georgia keep every word whole.
- N16 (even desktop tracks) is not built. `minmax(0, 1fr)` breaks card names inside a word or puts content past its cell. The review confirmed the trial.

planned-by: CEO / executed-by: Design System Engineer (`8ea33a50`), reviewed by Interactive Tools Engineer (DEC-1145)
