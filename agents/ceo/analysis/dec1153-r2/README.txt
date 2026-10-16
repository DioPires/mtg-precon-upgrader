DEC-1153 fix round 1 kit (PR #70, head de82474). CEO run 3a6232d8, 2026-10-15.

Source: the DEC-1170 review verdict cf5fd931 (Frontend Engineer, run f095c42a),
CHANGES with B1 and B2, N1 to N4. Copied from /tmp/dec1170-review/ at 23:2xZ.

reviewer/verdict.md                       the verdict as the reviewer posted it
reviewer/scratch/dec1170-loader-scratch.test.ts   cases 2b, 2d, K1 (B1), K2 (B2)
reviewer/scratch/dec1170-limiter-scratch.test.ts  cases 6b, 8a, 8b
reviewer/scratch/e2e/dec1170-scratch.spec.ts      R3, R4, R5 (not taken into the round)
reviewer/kill/                            kill runs: head, U-D1, U-D2, U-D6, U-D11
reviewer/mut/                             the four survivors' reports
reviewer/mutants.py, mutants.jsonl        the reviewer's runner and its 32 results
reviewer/main-UD11.log                    U-D11 on main's sources: 281 of 281 passed
reviewer/scratch-head.log, scratch-main.log   the scratch cases on the head and on main

The round (description of DEC-1153, "FIX ROUND 1"):
- B1: fix (b). loader.ts counts a price date only when Date.parse reads it
  (the test of cardCache.seed(), cardCache.ts:356-357), at :425 and :439.
- kill-loader.test.ts = the loader scratch file with K1 inverted (rows '' and
  'not a date': no envelope, [2, 2] on the next load) and two new 2d rows.
- kill-limiter.test.ts = the limiter scratch file without 8a (8a pins the N1 hang).
- README: N4's three points.
Expected on the merged branch: 53 files, 612 (main 904c74d, push run 38820146768)
+ 15 (round 1) + 15 (this round) = 642 unit tests, plus any new kill case;
205 + 2 = 207 e2e; lint 10 warnings.
