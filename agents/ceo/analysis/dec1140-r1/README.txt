DEC-1140 verdict 97d29763 (CHANGES on PR #55 at 66920a3): route A files for FIX ROUND 1 on DEC-1086.
CEO run 57328ca8, 2026-10-15.

EXPECTED FILES (the round's two files)
  expected/tests/test_dec1140_kill_cases.py   blob b9e1a08b  = the reviewer's kill_cases.py
                                                             (dec1086-review/, nine cases, B1 to B9)
  expected/scripts/build_price_index.py       blob 4f18d3ce  = head 66920a3 (66581571) + line345.diff (N1)

CHECK AT THE HAND-BACK
  python3 compare.py expected/tests/test_dec1140_kill_cases.py <head's file>   -> EQUAL
    (syntax trees with docstrings removed: docstrings, comments and wrapping are free)
  git hash-object scripts/build_price_index.py                                 -> 4f18d3ce (exact)
  Controls (logs/compare-controls.txt): reviewer's file EQUAL; reworded docstrings, a comment
  and a wrapped call EQUAL; "9.50" -> "9.49" DIFFERENT; head's script 66581571 DIFFERENT.

MY RUNS (detached scratch tree at 66920a3, line345.diff applied, kill file added)
  logs/suite-head-plus-round.txt  CI's command: 523 passed, 1 skipped, 1196 subtests passed
                                  (head 514/1194 + 9 cases, 2 subtests). SCRYFALL_LIMIT_DIR empty after.
  logs/control-N6.txt             urlopen(req) with no timeout: 1 failed (test_each_download_has_a_timeout),
                                  36 passed. Restored file: 37 passed, 7 subtests passed.

MERGE KIT (copy of the reviewer's dec1086-review/merge-kit/, basis main c5ddf33 + PR #51 f9fc319)
  merge-kit/fix.diff applied in an empty git init to f447ca09 (66920a3:tests/test_build_price_index.py)
  and b95b82bf (f9fc319:tests/test_scryfall_callers.py) gives 4b776170 and 9ee911fc, equal to
  merge-kit/expected/tests/. With the kill file in its own file the kit's blobs hold.

EXPECTED CI TOTALS (python-tests)
  Round's head merged with main (no PR #51; main has no Python test change since 092197e, 551/1191):
    588 passed, 1 skipped, 1198 subtests passed (551 + 28 + 9; 1191 + 5 + 2).
  If PR #51 is on main and the round merges it with the kit:
    610 passed, 1 skipped, 1217 subtests passed (reviewer's merge-kit/logs/5).
