Route A kit for fix round 1 of PR #54 (DEC-1131), review DEC-1149. CEO run 7d5a7d6f, 2026-10-15.

expected/  the reviewer's three kill files, byte for byte (verdict 7d31d824, /tmp/dec1149/unit/):
    web/src/__tests__/dec1149/dec1149-kills.test.ts                       git blob 967d5309 (12 cases: R1/R2, R3,
        R4, R5, R7 at 0 and 150 ms; S11; R13; R15; R21)
    web/src/__tests__/components/dec1149/dec1149-shopping-kills.test.tsx  git blob 49cc1ad2 (R9, R12)
    web/src/__tests__/components/dec1149/dec1149-tile-kill.test.tsx       git blob 1ead46a9 (R22)
    Copy each file to the same path in the tree. Nothing else changes.
core.py    the CEO's file check: `python3 -I core.py <repo> <ref>` after `git fetch origin`. It builds SIM (73f6fd5
           plus the three files), merges SIM with `git merge-base <ref> origin/main`, compares each kill file with
           comments, blank lines and whitespace dropped, and checks that every other path keeps the merge's blob.
ctl.py     the CEO's controls for core.py: `python3 -I ctl.py <repo> n8-resolved` (logs/ctl.txt):
    A  73f6fd5: the three files MISSING, NOT EQUAL.
    B  origin/main merged into 73f6fd5, then the files with a reworded comment and a wrapped call: ALL EQUAL.
    C  B with priced('2.51') for priced('2.50'): the kill file DIFFERENT, NOT EQUAL.
    D  PR #61 (e882c60) merged first: the three files EQUAL; Shopping.tsx and Shopping.test.tsx named as
       conflicts to read by hand (NOT EQUAL by design).
n8-resolved/  Shopping.tsx and Shopping.test.tsx of main + 73f6fd5 + e882c60 with the N8 resolution: keep
           useCardUpdates() and drop the local cardNoun() (PR #61 imports it from lib/cardNoun); the test imports
           are `vitest` with `type MockInstance` and `@testing-library/react` with `within`.
seed_mutants.py  the reviewer's mutant list, unchanged (/tmp/dec1149/mutants/seed_mutants.py).
run_kills.sh     runs the three kill files on each mutant: `TREE=<tree> LOG=<dir> run_kills.sh R1 R2 ...`.
reviewer/  the reviewer's summaries (kills-final-summary.txt, seed-summary.txt).
logs/      the CEO's runs on a detached scratch tree 690da29 = main 8a8f2fb + 73f6fd5 (merge-tree 950c35eb; its web
           tree a58b787f equals the head's), with the three files copied in, node_modules cloned from wt-dec1131:
    typecheck.log  exit 0.  eslint.log  no output, exit 0 (the three files).
    kills-on-merged.log  `Test Files  3 passed (3)`, `Tests  17 passed (17)`.
    unit-all-merged.log  `Test Files  47 passed (47)`, `Tests  565 passed (565)` (548 + 17).
    control-noKills-head.log  without the kill files `44 passed (44)`, `548 passed (548)`.
    control-R9-noKills.log, control-R7-noKills.log  R9 and R7 each `548 passed (548)` without the kill files.
    kills-summary.txt and kills/  15 mutants on the three files: R1, R1v, R2, R3, R4, R5, R5v, R7 each
        `2 failed | 15 passed (17)`; R9, R12, R13, R15, R21, R22, S11 each `1 failed | 16 passed (17)`; porcelain
        empty after each. Same lines as the reviewer's kills-final-summary.txt.
    kills-with-pr60.log  main + 73f6fd5 + af1f93b (PR #60): kill files and Shopping.test.tsx `4 passed (4)`, `60 passed (60)`.
    kills-with-pr61.log  main + 73f6fd5 + e882c60 (PR #61) with the N8 resolution: kill files, Shopping.test.tsx and
        cardNoun.test.ts `5 passed (5)`, `61 passed (61)`; pr61-typecheck.log exit 0.
