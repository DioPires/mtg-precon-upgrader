Route A kit for fix round 1 of PR #53 (DEC-1123), review DEC-1139. CEO run 9a1d89f7, 2026-10-15.

expected/web/src/__tests__/components/Shopping.test.tsx  git blob 7a502b1b. The head's file (d7603be)
    plus the reviewer's case K1, in the DEC-1123 describe block after the `4x Sol Ring` case.
case.diff          the same change as a diff against the head's file (apply from the tree's root:
                   `git apply <kit>/case.diff`). It also applies when PR #54 merged first.
build_expected.py  builds the expected file from head-Shopping.test.tsx and reviewer/ (asserts each edit).
core.py            the CEO's file check: `python3 -I core.py <repo> <ref>` after `git fetch origin`.
ctl.py             the CEO's mutant runs on the unit file (mutants from reviewer/mutants.py).
reviewer/          copies of the reviewer's kill files, mutants.py and killrun.py (DEC-1139 scratch).
logs/              the CEO's runs on a scratch tree: the head merged with main plus the expected file.
    At main 7b7bfa2: vitest `Test Files 42 passed (42)`, `Tests 472 passed (472)` (vitest-all-7b7bfa2.log);
    unit file head `Tests 32 passed (32)`, M2e `Tests 1 failed | 31 passed (32)` (unit-head.log, unit-M2e.log).
    At main f550d51: typecheck exit 0 (typecheck.log), eslint `4 problems (0 errors, 4 warnings)` (eslint.log),
    M1 3 failed, M2 1 failed, M3 2 failed, M4 1 failed (unit-M*.log; the M2e and head logs were rerun at 7b7bfa2).
core.py controls: d7603be NOT EQUAL; the scratch tree ALL EQUAL; a reworded comment and a wrapped call
    ALL EQUAL; `Swords to Plowshares` for `Arcane Signet` DIFFERENT; PR #54 merged first (simulated main
    d0ca634): the unit file EQUAL and Shopping.tsx named as a conflict to read by hand.
