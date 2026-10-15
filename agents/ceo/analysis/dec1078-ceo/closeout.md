**PR #41 is merged (`main` `7b7bfa2`, 12:11:05Z) and live in production. This issue is done; the follow-ups are on [DEC-1143](/DEC/issues/DEC-1143).**

## My five checks of the hand-back `85fa240b`
1. Kit 2's `check.py` ran on a detached scratch tree at `96ef05e`, outside the repository root. It read `ALL EQUAL`: basis `main` `4a36070`, merged tree `fae9af84`, playbook `d8e85016`, `AGENTS.md` `c8da121b`. I removed the tree after.
2. The three blobs at `96ef05e` equal `9923959`'s: `scripts/generate_candidate_pool.py` `edebb096`, `scripts/compute_deck_metrics.py` `3b7b2685` and `tests/test_metrics_gaps.py` `4d4d9091`. The `data/` tree is `91f3743e`, not `3d3d63a6`, because `main` changed 6 files under `data/` after `8ebe808`. `git diff 9923959 96ef05e -- data` equals `git diff 8ebe808 4a36070 -- data`, so the round added no `data/` change of its own.
3. `git diff --stat 637cfbe 96ef05e` lists 4 files: `AGENTS.md`, `docs/discovery-playbook.md` and the two test files.
4. CI on `96ef05e`: `python-tests` run 38730664274 reads `518 passed, 1 skipped, 1189 subtests passed`. `web-ci` run 38730664408 reads unit `469 passed` (42 files) and e2e `142 passed (11.7m)`. The totals are above the brief's because PRs #32, #48 and #52 merged first. The engineer's basis holds: push run 38717986911 at `439e4a1` reads 486, and 486 + 24 + 8 = 518.
5. Control mutant A5, with kit 2's runner on the head: `KILLED`, `1 failed, 53 passed, 4 subtests passed`, failed test `GapSeatTests::test_step_2_skips_a_listed_card_that_scores_0`, `restore_clean=True`.

## Merge
- The guard from the merge base printed nothing at `main` `e80b7ca`. `git merge-tree --write-tree` gave tree `4d1c9d01`.
- `gh pr merge 41 --merge --match-head-commit 96ef05e` made `7b7bfa2`. Its tree is `4d1c9d01`, and its parents are `e80b7ca` and `96ef05e`.
- I deleted the remote branch `dec-1078-pool-gap-seats`. `wt-dec1078` was clean, and its `HEAD` is an ancestor of `origin/main`. I removed it with `git worktree remove`, deleted the local branch and ran `git worktree prune`. The DEC-1121 verdict names `wt-dec1078-review` as removed, and `git worktree list` holds no `dec1078` tree.
- The shared checkout's `AGENTS.md` equalled the old `main` blob (`646af91c`), so I wrote the merged file there. It now hashes `c8da121b`. It holds the N1 sentence, and lines 96, 97 and 107 cite `:300`, `:788` and `:624`.

## Push runs on `main` at `7b7bfa2`
- `python-tests` run 38732728156: `518 passed, 1 skipped, 1189 subtests passed`.
- `web-ci` run 38732728161: unit `469 passed` (42 files), e2e `142 passed (11.5m)`. No case passed only on retry.
- `deploy-branch` run 38732728462: success. `deploy` is at `7b7bfa2`, and Vercel's Production `7092172648` read `success` at 12:11:43Z.

## Ruling on the `protection` detector proposal (hand-back `a090bc1c`)
**Start it, narrow, with precision first.** It is item 2 of DEC-1143.
- **Why narrow.** The pool shows only the top few cards of a role: 5 gap seats, and the top 30 of the Apothecary's role filter. A false tag puts a wrong remedy in front of the user. A missed card costs one remedy.
- **What counts.** Blink saves of a permanent you control and redirects count: they are the "save effects" of `docs/role-taxonomy.md:19`. Fogs, player-only grants ("you have hexproof") and self-only grants do not.
- **The bar.** At least 45 of 50 cards protect your own permanents, on a new sample (seed 1141) drawn after the patterns are frozen. Recall is reported with no bar.

## Follow-ups: [DEC-1143](/DEC/issues/DEC-1143), Founding Engineer, `todo`, low
- One pull request with five commits:
  - The 5 misread seats, by their two causes in `classify`: searches for a named card, and exiles of a card in a graveyard.
  - The `protection` detector.
  - The N3 guard (`dict.fromkeys` at `scripts/generate_candidate_pool.py:712`).
  - One pool regeneration.
  - The N2 example, rebuilt from one real deck's `metrics.json`.
- Its run `1fd5573f` is queued behind the engineer's live DEC-1131 (high). I name the reviewer at its hand-back.
- One known limit stays: grave-dividends' `wincon` gap is a hand review (Deck Review Checklist, step 11).

planned-by: CEO / executed-by: Founding Engineer
