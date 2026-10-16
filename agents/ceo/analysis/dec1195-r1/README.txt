Route A kit for fix round 1 of PR #80 (DEC-1188), review DEC-1195, verdict 80e28807. CEO run 9159fe30, 2026-10-16.

expected/  the reviewer's test file, byte for byte (proposed/body-timeout.test.ts of the verdict's evidence folder; it equals
           the head's file with proposed.patch applied, checked by cmp):
    web/src/__tests__/dec1188/body-timeout.test.ts   git blob 88b46c82 (10 cases: 8a with three body kinds, B1 x2,
           B2, B3, and B4: a 400, a 422 and a 429 whose body never ends)
apply.py   the round's edits: `python3 -I apply.py <tree>`. It copies the test file and makes five edits; each finds its
           old text once or stops, and a second run prints "already" for each:
    B3                   web/src/data/scryfallLimiter.ts: the reviewer's condition `response.status !== 429` and its
                         comment line (verdict B3, byte for byte).
    N4-settle            the `settle` doc: "When it runs, the body of the answer has ended or has failed (DEC-1188)."
                         (verdict N4, byte for byte).
    D1-fetchWithTimeout  the doc of fetchWithTimeout: "an answer other than a 429 comes when its body has ended" (the
                         CEO's words: B3 would make the old doc wrong for a 429).
    N4-readme            web/README.md: "has its answer only when the body has ended or failed" (verdict N4).
    N5-readme            web/README.md: "goes first in its tab when the stop ends" (verdict N5); the bullet is wrapped
                         again at the file's width, 94, by the same greedy wrap that reproduces main's bullet.
           After apply.py on 27e34a4: scryfallLimiter.ts is blob 5f12a85a, web/README.md is blob c5d5b40c.
core.py    the CEO's file check: `python3 -I core.py <repo> <ref>` after `git fetch origin`. It builds SIM (27e34a4 plus
           apply.py's edits and the test file), merges SIM with `git merge-base <ref> origin/main`, compares the test
           file with comments, blank lines and whitespace dropped, and checks that every other path (the limiter and the
           README among them) keeps the merge's blob byte for byte. On 27e34a4 it prints NOT EQUAL.
ctl.py     the CEO's controls for core.py: `python3 -I ctl.py <repo>` (logs/ctl.txt), all as expected:
    A  27e34a4: the test file DIFFERENT, two paths CHANGED, NOT EQUAL.
    B  origin/main 349e13f merged into 27e34a4, then apply.py: ALL EQUAL.
    B2 B with a comment of the test file reworded and one call wrapped: ALL EQUAL.
    C1 B with the head's condition `if (response && wholeBody) {`: the limiter CHANGED, NOT EQUAL.
    C2 B with `T0 + 31_000` in the 429 case: DIFFERENT, NOT EQUAL.
    C3 B without N5's "in its tab": the README CHANGED, NOT EQUAL.
    D  PR #78 (ed8a1a6) merged into main first, then the round: ALL EQUAL.
mut.py     four control mutants of the new lines: run `python3 -I <kit>/mut.py <log folder>` from `<tree>/web` after
           apply.py. It writes each mutant into src/data/scryfallLimiter.ts, runs the test file, saves mut-<id>.log and
           restores the file (also on an error). Expected:
    C1-head-line    the head's condition                       1 failed | 9 passed: the 429 case
    R1-first-chunk  read the copy's first chunk only           1 failed | 9 passed: 8a (one chunk, and never ends)
    R3-ok           `response.ok` for `response.status !== 429` 2 failed | 8 passed: B4 a 400, B4 a 422
    M503            `!== 503` for `!== 429`                     1 failed | 9 passed: the 429 case
reviewer/  the reviewer's files: proposed.patch, its run file of the limiter, the logs (P-no429, P-R1, P-R3, the patch's
           vitest, lint and typecheck runs), the N2 variant (p3variant.patch and its vitest log) and verdict.md.
logs/      the CEO's runs on a detached scratch tree at 27e34a4 with apply.py (node_modules cloned from wt-dec1188;
           package-lock.json equal by cmp; the tree removed after the runs):
      typecheck.log exit 0.  eslint-files.log no output, exit 0 (the limiter and the test file).
      eslint-all.log `✖ 10 problems (0 errors, 10 warnings)`.
      unit-all.log `Test Files  55 passed (55)`, `Tests  706 passed (706)` (the head's 702 plus 4 new cases).
      body-timeout.log `Tests  10 passed (10)`.  mut-*.log: the four mutants above, each as expected.
    The CEO ran no e2e case. The implementer's runs are the record for the pushed head.

Not taken into this round (ruling on DEC-1188, CEO run 9159fe30):
    N2  a body that fails before its end counts as a rejected fetch. No follow-up now: the fault needs a network error in
        the middle of a /cards/collection body, and its cost (a /shopping refresh keeps the file's dated price for 24 h in
        that browser; a lookup fails for 30 s in that tab) shows no wrong price. The change would also stop every tab
        for 30 s on one such error. The reviewer's tested change is reviewer/p3variant.patch; after B3 its condition
        reads `response && wholeBody && response.status !== 429`. Take it into the next issue that changes the card cache.
    N3  a tab's own error entry in memory hides a loaded entry that another tab stored (one extra request for each such
        name; main does the same). Take it into the next issue that changes the card cache.
