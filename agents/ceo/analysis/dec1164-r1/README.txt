Route A kit for fix round 1 of PR #66 (DEC-1155), review DEC-1164. CEO run 14f85cb1, 2026-10-15.

expected/web/src/__tests__/routes/ComboLab.test.tsx  git blob 75d79f0b, 196 lines. The head's file (ff7ead8, blob
    37787a73) plus the reviewer's B1 row as the fourth row of the it.each table of the DEC-1150 block:
    [[['Sol Ring', 2], ['Arcane Signet', 1]], '3 owned cards on file'],
expected/web/src/__tests__/data/ownedCards.test.ts   git blob 603fa04d, 151 lines. The head's file (970990a8) plus
    the reviewer's B2 case, byte for byte and indented by two spaces, as an `it` of
    describe('readOwnedEntries (DEC-1150)') after 'reads localStorage when no storage is given'.
case.diff          the same two changes as one diff against the head's files (apply from the tree's root:
                   `git apply <kit>/case.diff`). Checked: applied to the head's files it gives both blobs above.
build_expected.py  builds the expected files from head/ and reviewer/ (asserts each anchor).
core.py            the CEO's file check: `python3 -I core.py <repo> <ref>` after `git fetch origin`. It merges SIM
                   (ff7ead8 + the expected files) with `git merge-base <ref> origin/main`, so it holds whether or
                   not the round merged main, and in either order with PR #65.
                   Its compare keeps every character inside a string literal. The dec1151-r1 form dropped all
                   whitespace, so ' Sol Ring ' read EQUAL to 'Sol Ring' (control D read ALL EQUAL before the fix).
ctl_core.py        the six controls of core.py: `python3 -I ctl_core.py <repo>`.
reviewer/          copies of the reviewer's two kill files, its mutant runner mutate.py (unchanged), its
                   mutants-run.txt, verdict.md, and its R1, R2 and R9 logs (DEC-1164 scratch folder).
logs/              the CEO's runs on a detached scratch tree (commit f382f26, never pushed): origin/main a4cd315
    merged into ff7ead8 plus the expected files. Tree 3ee40b56, web subtree 990512aa. main has no change under
    web/, data/ or .github/ since b09f8be (web-ci push run 38792978708: 10 warnings, 51 files, 610 tests,
    `179 passed (9.4m)`).
    typecheck.log: exit 0. eslint.log: no output, exit 0 (the two test files).
    vitest-all.log: `Test Files  51 passed (51)`, `Tests  649 passed (649)` (610 + 37 + 2).
    ctl-all.txt and mutants/: the reviewer's 28 mutants. 21 killed. R1 and R2 each `1 failed | 7 passed (8)`
    and R9 `1 failed | 29 passed (30)`; each fails the new case only. O2 now fails 2 cases (the new case
    reads localStorage too). 7 survive: R5, R6, R7, R11, R15 and R22 (equivalent, shown in the verdict) and
    N1 (outside the mutant rule by ruling 2). Each run left the tree clean.
    core-controls.log: A ff7ead8 NOT EQUAL; B (comments added, the B2 expect wrapped with a trailing comma)
    ALL EQUAL; C ('2 owned cards on file' in the row) NOT EQUAL; D ('Sol Ring' for ' Sol Ring ') NOT EQUAL;
    E (one more line in Shopping.tsx) CHANGED, NOT EQUAL; F (PR #65 f1eae45 merged into main first) ALL EQUAL.

logs/main-43844f7/  PR #65 (DEC-1154) merged to main as 904c74d during the CEO run (tree b9526fbc, the same tree as
    control F's simulated main). The CEO built the round on main 43844f7 (the kit's own commit on 904c74d): ff7ead8
    plus the expected files, then main merged in (clean, tree 7b51fa00, scratch commit a363f33, never pushed).
    core-on-round.txt: ALL EQUAL. typecheck.txt: exit 0.
    vitest-all.txt: `Test Files  51 passed (51)`, `Tests  651 passed (651)` (main 612 + 37 + 2).
    ctl-r1-r2-r9.txt and mutants/: R1 and R2 each `1 failed | 7 passed (8)`, R9 `1 failed | 29 passed (30)`;
    each fails the new case only. Per file: ComboLab 8, ownedCards 30, Shopping 52.
    CI basis after PR #65: its pull_request run 38818813698 on f1eae45 read 10 warnings, 51 files, 612 tests,
    `205 passed (8.9m)`. main's push run 38820146768 on 904c74d was in progress at 22:55Z.
