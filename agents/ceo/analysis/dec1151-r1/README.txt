Route A kit for fix round 1 of PR #61 (DEC-1142), review DEC-1151. CEO run 94bcde49, 2026-10-15.

expected/web/src/__tests__/components/Shopping.test.tsx  git blob a3cac46b. The head's file (e882c60, blob 27e5e1db)
    plus the reviewer's B1 case as a fifth `it` at the end of the DEC-1142 block.
expected/web/src/__tests__/lib/cardNoun.test.ts         git blob 1ad7b50b. The head's file (8c53c23d) with 1.5 in
    the it.each list (B2) and a comment that names the rounding mutants.
expected/web/src/__tests__/components/Engine.test.tsx   git blob ce9fce8f. The head's file (85d06b73) plus the
    reviewer's offered case for N2 (a role of count 1 that lists two tiles).
case.diff          the same three changes as one diff against the head's files (apply from the tree's root:
                   `git apply <kit>/case.diff`).
build_expected.py  builds the expected files from head/ and reviewer/ (asserts each anchor).
core.py            the CEO's file check: `python3 -I core.py <repo> <ref>` after `git fetch origin`.
ctl.py             runs the reviewer's mutant list (reviewer/mutants.py, unchanged) on a committed tree:
                   `python3 -I ctl.py <tree> <log dir> [ID ...]`.
reviewer/          copies of the reviewer's three kill files, mutants.py and kill.py (DEC-1151 scratch).
logs/              the CEO's runs on a detached scratch tree of e882c60 with the expected files committed locally
    (19d7fae, never pushed). main 8a8f2fb has no change under web/ or data/ since the merge base b703bde, so the
    head's web tree is the merged web tree.
    vitest-all.log: `Test Files  46 passed (46)`, `Tests  496 passed (496)` (493 + 3).
    typecheck.log: exit 0. eslint.log: no output, exit 0 (the three test files).
    ctl-all.txt and mutants/: all 75 of the reviewer's mutants, 74 killed, 1 survived (H17 `count == 1`,
    equivalent on `count: number`). S3-S6 and S13-S16 each `1 failed | 36 passed (37)`; H20 and H21 each
    `1 failed | 6 passed (7)`; E2 and E5 each `1 failed | 2 passed (3)`.
    core-controls.log: e882c60 NOT EQUAL; 19d7fae ALL EQUAL; 23f6dde (reworded comments, a wrapped expect with a
    trailing comma) ALL EQUAL. Not logged, read in the run: '3 card' for '3 cards', 1.25 for 1.5, and count: 2 for
    count: 1 each NOT EQUAL.
