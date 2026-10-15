Route A kit for fix round 1 of PR #60 (DEC-1141), review DEC-1150. CEO run 20028206, 2026-10-15.

expected/web/src/__tests__/dec1150/kill-shopping.test.tsx   git blob 1901f11a. The reviewer's kill file
    (verdict a5985620, R/kill/Shopping.dec1150-kill.test.tsx, sha256 ef25ceee), byte for byte, at a new path.
    Its imports (../../components/organisms/Shopping, ../../data/types) resolve to the same files from
    web/src/__tests__/dec1150/ as from web/src/__tests__/components/, where the reviewer ran it. The folder
    follows main's web/src/__tests__/dec1110/kill-*.test.ts. Copy the file to that path. Nothing else changes.
core.py      the CEO's file check: `python3 -I core.py <repo> <ref>` after `git fetch origin`. It builds SIM
             (af1f93b plus the kill file), merges SIM with `git merge-base <ref> origin/main`, compares the kill
             file with comments, blank lines and whitespace dropped, and checks that every other path keeps the
             merge's blob. When PR #61 merged first, Shopping.test.tsx conflicts; the script then checks the
             resolution (no marker, each side's added blocks byte for byte, main's line count + 70).
ctl_core.sh  the CEO's controls for core.py: `sh ctl_core.sh <repo>` (logs/ctl-core.txt):
    A  af1f93b: the kill file MISSING, NOT EQUAL.
    B  origin/main 1336e32 merged into af1f93b, then the kill file with a reworded comment and a wrapped
       expect with a trailing comma: ALL EQUAL.
    C  B with toBe(2) for toBe(1) in K1: DIFFERENT, NOT EQUAL.
    D  a simulated main with PR #61 (e882c60) merged, af1f93b merged into it, Shopping.test.tsx resolved
       by keeping both blocks (the two shared closing lines and a blank line between them), plus the kill
       file: resolution KEPT BOTH, ALL EQUAL.
    E  D with the DEC-1141 describe line dropped: resolution BAD, NOT EQUAL.
ctl.py       runs the reviewer's 21 mutants (reviewer/run_mutants.py, unchanged) on the kill file and on
             Shopping.test.tsx in one vitest call each: `python3 -I ctl.py <tree> <log dir> [ID ...]`.
reviewer/    copies of the reviewer's kill file, run_mutants.py, run_kill.py, kill-logs/summary.txt, verdict.md.
logs/        the CEO's runs on a detached scratch tree 00d7e54 = (main 1336e32 + af1f93b, merge tree 2a22dbf0,
             web subtree f2b76d58 = the head's) + the kill file committed locally (never pushed);
             node_modules cloned from wt-dec1141 (package-lock blob dfa9fe65 on main, PR #54 and PR #61 alike):
    typecheck.log  exit 0.  eslint.log  no output, exit 0 (the kill file).
    vitest-all.log  `Test Files  44 passed (44)`, `Tests  488 passed (488)` (484 + 4).
    ctl-all.txt and mutants/  head `Tests  45 passed (45)`; 17 of 21 killed. R1, R2 (K1), R5 (K3), R8 (K2) and
        R13 (K4) each `1 failed | 44 passed (45)`. R6, R7, R14, R16 pass: the reviewer's equivalents.
    kill-with-pr54.log  the scratch tree + PR #54 (73f6fd5): kill file and Shopping.test.tsx `47 passed (47)`.
    kill-with-pr61.log  control D's tree (main + PR #61 + af1f93b resolved + kill file): kill file,
        Shopping.test.tsx and cardNoun.test.ts `55 passed (55)`; pr61-typecheck.log exit 0.
