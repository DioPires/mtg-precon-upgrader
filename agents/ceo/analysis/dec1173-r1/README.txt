Route A kit for fix round 1 of PR #72 (DEC-1167), review DEC-1173. CEO run 470e9502, 2026-10-16.

expected/  the reviewer's kill file, byte for byte (verdict 03f766d3, /tmp/dec1173/kill/):
    web/src/__tests__/components/dec1173-stopline-date.test.tsx   git blob f45ce3bb (101 lines; kills E5 and E4)
    Copy it to the same path in the tree. Nothing else changes. You may drop or reword comment lines
    (the last header line, "Copy it to web/src/__tests__/components/ to run it.", is stale in the tree).
core.py    the CEO's file check: `python3 -I core.py <repo> <ref>` after `git fetch origin`. It builds SIM (0cfe1f3
           plus the file), merges SIM with `git merge-base <ref> origin/main`, compares the kill file with comments,
           blank lines and whitespace dropped, and checks that every other path keeps the merge's blob.
           On 0cfe1f3 it prints MISSING and NOT EQUAL (exit 1).
ctl.py     the CEO's controls for core.py: `python3 -I ctl.py <repo>` (logs/ctl.txt):
    A  0cfe1f3: the file MISSING, NOT EQUAL.
    B  origin/main e886907 merged into 0cfe1f3, then the file without its last header line and with one call wrapped: ALL EQUAL.
    C  B with the file's prices 2 days old in place of 3: DIFFERENT, NOT EQUAL.
    D  PR #74 (7cba124) merged into main first: no conflict, ALL EQUAL.
    E  PR #66 (3c3a151) merged into main first: no conflict, ALL EQUAL.
run_kill.sh  the implementer's runs: `TREE=<tree> LOG=<dir> run_kill.sh` on a clean tree with the file committed.
           typecheck, eslint on the file, the file, the full unit suite, then E5 and E4 (each must fail at :96).
reviewer/  the reviewer's kill folder, unchanged (run-kill.sh, kill-head.log, kill-head-repeat5.log, kill-E5.log,
           kill-E4.log, kill-merged66.log, typecheck.log, both mutant diffs).
followups/n2-empty-sigil/  the reviewer's CDP reads (main and head): after Clear, main-stop.json reads the empty state as
           ["◇", "◇", "NO DECKS SELECTED. ..."]. Evidence for the N2 follow-up.
logs/      the CEO's runs on a detached scratch tree 52677e0 = main e886907 + 0cfe1f3 (merge-tree 901e9582),
           node_modules cloned from wt-dec1167 (package-lock.json equal by cmp), the file copied in:
    typecheck.log  exit 0.   eslint.log  no output, exit 0.
    kill-merged.log  `Tests  1 passed (1)`.
    unit-all-merged.log  `Test Files  52 passed (52)`, `Tests  620 passed (620)` (main 618 + PR #72's 1 + the kill case).
    kill-E5.log  fails at :96, Received "Price refresh paused. Prices shown are from 13 Oct 2026. Next try at 11:01:22."
    kill-E4.log  fails at :96, Received "Price refresh paused. Next try at 11:01:25."
    kill-with-pr66.log  + PR #66 3c3a151: the file and Shopping.test.tsx `Tests  54 passed (54)`.
    kill-with-pr70.log  + PR #70 a75bcc2: `Tests  51 passed (51)`.
    kill-with-pr74.log  + PR #74 7cba124: `Tests  53 passed (53)`.
    kill-with-pr75.log  + PR #75 e5e95b4: `Tests  51 passed (51)`.
    kit-run/  run_kill.sh on the same scratch tree with the file committed locally (never pushed): typecheck 0,
        eslint 0, the file 1 passed, E5 and E4 each 1 failed at :96. Its full suite read `1 failed | 619 passed (620)`:
        nearMissComplete.test.ts "scans the full pool within the interactive budget (NF-4)" read 1085.405 ms
        against 1000 under load (load average 5.4). That file alone passed `17 passed (17)` (nf4-rerun.log).
        A timing case of that kind is load, not the kill file.
