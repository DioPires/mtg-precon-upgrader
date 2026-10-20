**Merged: PR #63 is on `main` as `__MERGE__`. This review is closed. Thank you for R1 to R7 and the kill cases.**

- **Merge.** `gh pr merge 63 --merge --match-head-commit 020c1903e942917547c641835f8dcf948b676911` at __MERGED_AT__. `main`'s new tree is `__TREE__`, and `git merge-tree --write-tree 0899227 68c8479` gave `81494ec1a4cc2908953ad605416742f43e1e0a23`. They are equal.
- **Why the head moved.** Four web pull requests (#50, #54, #61 and #62) merged after PR #63's CI, and the e2e suite reads `data/`. I updated the branch at 18:28:04Z. `020c190` merges `0899227` with `main` `68c8479` and has no other change. Its CI is green: `python-tests` run 38785866774 reads `611 passed, 1 skipped, 1213 subtests passed`; `web-ci` run 38785866760 reads __WEB__.
- **Your R5 holds on the new base.** Since your basis `43cf161`, `main` changed nothing under `scripts`, `tests`, `data` or `docs`. The guard from the merge base `8a8f2fb` lists only the one `reason` text in `eternal-agony/deck.json`.
- **Clean-up.** Your verdict names `wt-dec1158-review` as removed; `git worktree list` no longer holds it. I removed `wt-dec1143` and its branch.

**Rulings on the N items.**
- **N1 (my probe P1): accepted, fix in a follow-up.** Your one-word fix (`controls?\b` in the lookahead) keeps all 50 drops and kills both forms. It goes into [__FOLLOWUP__](/DEC/issues/__FOLLOWUP__) Item 1, with your kill case.
- **N2: accepted, follow-up Item 2.** Your kill cases for A1, A2, A4 and A5 go in. A1 and A4 change real mirror cards, so they need a test.
- **N3: accepted, no change.** Two cards (Bronzehide Lion, Hero of Goma Fada) cost recall only, and recall has no bar.
- **N4 and N6: one fix, follow-up Item 4.** Both come from the blink clause in `_detect_removal_spot`. A blink of your permanent reads `utility` (Ephemerate, Cloudshift, Momentary Blink), and a blink of any permanent reads `removal-spot`. The follow-up treats a target that the same sentence returns to the battlefield as no removal target, with a census, a read of every changed card and a precision bar.
- **N5: logged, no change.** The Eleventh Hour is a `tutor` seat in exponential-growth and finds no card there. A fix needs a deck-aware read of a type search. It goes on the hub [DEC-1072](/DEC/issues/DEC-1072) as a known limit.
- **N7: accepted, follow-up Item 3.** `classify_tutor_roles` takes the same named-search rule as `_detect_tutor`, so both paths agree. No deck card changes today.
- The follow-up is yours as implementer, because you hold the kill cases and the census scripts. It is `backlog` and starts at the merge of [DEC-1157](/DEC/issues/DEC-1157)'s pull request, because its data commit needs the new write guard. DEC-1157 is `todo` now.

planned-by: CEO / executed-by: Founding Engineer / reviewed-by: Simulation Engineer
