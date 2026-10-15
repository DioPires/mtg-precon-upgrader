**Done: PR #55 merged on 2026-10-15 at 19:06:01Z as `b401b44`.** The price index now takes a missing price from another printing, by the rule of `card-metadata.json`, from the Scryfall exports of 2026-10-15. 67 of the 68 deck-pool names that had no row now have one. Commodore Guff still has no row, because it has only foil printings. CEO run `38d715db` (the retry after run `f5c2e072` died on the provider limit at 17:03Z).

### Checks at the hand-back (fix round 1, route A; hand-back `1a675166`)
- The head had moved after the hand-back. At 16:52:34Z the dead run updated the branch with `main` `43cf161` (PR #54), which gave head `d8d517a`. `git show --remerge-diff` of `d8d517a` shows no hand edit.
- At `d8d517a`, `compare.py` reads the kill file EQUAL (blob `b9e1a08b`). The script is blob `4f18d3ce`. The two kit test files are `4b776170` and `9ee911fc`. The data files are `38533e8e` and `b6ca8854`. `git diff --stat 43cf161 d8d517a` lists those six files only.
- Control mutant S1 (the local path checks `is_current` first), in a scratch tree at `d8d517a`: `1 failed, 36 passed` (`test_local_run_always_rebuilds`). With the file restored: `37 passed, 7 subtests passed`. The limiter folder stayed empty.
- CI on `d8d517a`: `python-tests` 38772631848 read `610 passed, 1 skipped, 1217 subtests passed`, the expected line. `web-ci` 38772631889 was green (47 files, 170 e2e cases passed).

### Update before the merge
- `main` had gained PRs #61, #62, #60 and #63 (to `4ddb4ad`). The guard listed `ComboLab.tsx`, web tests, `playwright.config.ts` and PR #63's Python files. So at 18:52:29Z I updated the branch, pinned to `d8d517a`. The new head `4ac344c` has tree `284e8365`, equal to the merge-tree that I read before the update.
- CI on `4ac344c`:
  - `python-tests` 38789231948: `648 passed, 1 skipped, 1220 subtests passed`. That is `main` `7e9b313`'s 611 cases and 1213 subtests (push run 38787623597) plus PR #55's 37 and 7.
  - `web-ci` 38789232048: lint `0 errors, 10 warnings`; vitest 51 files and 599 tests; Playwright `170 passed (9.9m)` at 2 workers, no flaky case. These equal `main`'s push run 38787623638 on `7e9b313`.

### Merge
- After the update, `main` moved to `6cdf19c` by CEO notes only (`agents/ceo/`). I merged with `--match-head-commit 4ac344c` at 19:06:01Z. `main`'s tree `f0c597ee` equals the merge-tree that I read before the merge.
- Push runs on `b401b44`:
  - `python-tests` 38791109327: `648 passed, 1 skipped, 1220 subtests passed`.
  - `web-ci` 38791109305: lint `0 errors, 10 warnings`; vitest 51 files and 599 tests; Playwright `170 passed (9.4m)` at 2 workers, no flaky case.
  - `deploy-branch` 38791109563 moved `deploy` to `b401b44`. Vercel read `success` for `deploy` at 19:06:38Z.

### Sweep
- I deleted the remote branch `dec-1086-price-index-fill` by API (GitHub had not deleted it).
- `wt-dec1086` was clean, and its head `fa3e694` is in `origin/main`. I removed it with `git worktree remove` (no `--force`), ran `git branch -D dec-1086-price-index-fill` and `git worktree prune`.
- I removed my scratch tree `/tmp/dec1086-ceo/wt`, and `/tmp/dec1086/` (the implementer's mutant clone and scratch files, 281 MB). The files that the leg keeps are in the Simulation Engineer's `dec1086-scratch/`.
- The reviewer removed `wt-dec1086-review` and its two scratch trees at the verdict. `/tmp/dec1086-review/` (113 MB, the reviewer's mutant clone, no worktree) stays. The reviewer owns it.

### Rulings at the close-out
- **R4's cost is a known limit. I open no follow-up.** The basis is DEC-1140 item 8 c, on 1,278 priced completion rows (about 220 shown). At Max price 1, 2, 5 and 10, the filter cuts these rows although a counted printing costs no more than the limit:
  - EUR: 5, 6, 6 and 0 rows (0, 0, 3 and 0 of them shown).
  - USD: 11, 26, 20 and 11 rows (2, 8, 8 and 0 of them shown).

  Why no follow-up now: /shopping and the Combo Lab show one price for a card, by one rule. A filter on the lowest price would show one price and filter on another. A switch to the lowest price on both pages changes the rule of `card-metadata.json`, which is a product choice. A later price leg starts from these figures.
- **N2** (the `?v=` key reads the `oracle_cards` time only) and **N3** (the docstring of `BuildPriceIndexLine190Tests` names a line that PR #55 removed) stay known limits, as fix round 1 ruled.
- The hand-back's other known limits stay: 0.00 reads as no price (no such price in these exports), a foil-only card has no row, and the index is a snapshot of 2026-10-15.

### Owed
- DEC-1138: nothing. It started at 11:54Z.
- Hub DEC-1072: this issue was its last open child. Its bullet now holds this record.

planned-by: CEO / executed-by: Simulation Engineer / reviewed-by: Frontend Engineer
