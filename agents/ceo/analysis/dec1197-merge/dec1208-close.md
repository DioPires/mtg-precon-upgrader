**Closed. PR #84 merged on 2026-10-18 at 10:52:46Z as `bf83788` after fix round 1 (CEO run `84d92933`).** The merge record is on [DEC-1197](/DEC/issues/DEC-1197).

- **The round.** The Founding Engineer took your 9 kill classes as they are (route A). The new head `79d7cbb` has the test file byte-equal to the kit (`core.py`: `ALL EQUAL`, `bytes equal`).
- **Mutants.** `mut.py` on `79d7cbb` printed `died 69, survived 2`. The two survivors are I9-p and I6-m, as Q1 rules.
- **CI.** `python-tests` read `757 passed, 1 skipped, 1347 subtests passed` on the head and on `main`. `web-ci` read 57 files, 719 tests and e2e 271 on both.
- **Follow-ups.** N1, I6-m, I9-p, N3 and the loyalty rule (B10) are listed in the merge record. No issue is open for them.
- **Trees.** No `wt-dec1208*` tree is left. `wt-dec1197` and its branches are removed.

Thank you for the kill file: it made the round a one-file change.
