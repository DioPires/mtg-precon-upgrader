Route A kit for fix round 1 of PR #69 (DEC-1146), review DEC-1169. CEO run 2c51a85a, 2026-10-15.

expected/web/src/__tests__/components/DeckSelector.test.tsx   git blob 2d480abf, 723 lines.
    The head's file (64f2146, blob 62f959b3, 691 lines) plus the reviewer's kill case K1 (B1, mutant R1):
    1. The harness AutoFocusGuide, with its comment, after the head's Guide (18 lines). It is Guide with a
       field `<input aria-label="Search" autoFocus />` that only deck 5 renders, in place of `Stays`.
    2. The case as the last `it` of describe('... no key started (DEC-1146)'), after 'moves no focus when
       focus is on an element outside the track that stays', with a two-line comment (14 lines).
       Its body is the reviewer's, byte for byte. Its name drops the review's label "K1: ".
case.diff          the same change as one diff against the head's file (apply from the tree's root:
                   `git apply <kit>/case.diff`). Checked: applied to the head's file it gives blob 2d480abf.
build_expected.py  builds the expected file from head/ and reviewer/kill/ (asserts each anchor).
core.py            the CEO's file check: `python3 -I core.py <repo> <ref>` after `git fetch origin`. It merges SIM
                   (64f2146 + the expected file) with `git merge-base <ref> origin/main`, so it holds whether or
                   not the round merged main. Comments, blank lines and wrapping are free; code and the text
                   inside strings (the case's name, the label 'Search') are not. Keep the field's JSX line as it
                   stands: JSX wrapped in parentheses reads as other code.
ctl_core.py        the six controls of core.py: `python3 -I ctl_core.py <repo>`.
mut.py             the DEC-1146 review kit's runner (unchanged). MUT_TREE and MUT_LOG_DIR are required.
round-mutants.json the 19 unit mutants: R1 first, then the seed mutants M2, M3, M4 and RA-M4, then the reviewer's
                   R2 to R7, R11 to R14, R16 and R19 to R21 (byte for byte from reviewer/).
reviewer/          copies of the reviewer's kill file and its logs (kill/), the StrictMode and stub cases
                   (strict/), its own mutants and summaries (own/), the seed mutants (seed-mutants.json) and
                   verdict.md (DEC-1169 scratch folder dec1169-review/).
head/              the head's test file (64f2146).
logs/              the CEO's runs on a detached scratch tree /tmp/dec1169-ceo/wt (commit 72c92b1, never pushed):
    origin/main dc50857 merged into 64f2146 plus the expected file. Tree a0adc79e, web subtree 3c705e4f.
    package.json and package-lock.json are the head's (lock blob dfa9fe65), so node_modules was cloned from
    wt-dec1146. main gained PR #65 (DEC-1154, 904c74d) under web/ since 02d085c; it touches no file of PR #69.
    main's push run 38820146768 on 904c74d read lint 10 warnings, `Test Files  51 passed (51)`,
    `Tests  612 passed (612)` (e2e still running at 23:02Z; PR #65's own run 38818813698 read `205 passed (8.9m)`).
    typecheck.log: exit 0. eslint.log: no output, exit 0. lint.log: `✖ 10 problems (0 errors, 10 warnings)`.
    unit-file.log: `Tests  34 passed (34)`.
    vitest-all.log: `Test Files  51 passed (51)`, `Tests  618 passed (618)` (612 + 5 + 1).
    mutants-run.txt and mutants/: R1 `1 failed | 33 passed (34)`, the new case only. R4 `5 failed | 29 passed (34)`
    (its four before, and the new case). R5, R7 and R13 `34 passed (34)` (equivalent, shown in the verdict).
    Every other mutant fails the cases of the verdict, no more. Each run left the tree clean.
    core-controls.log: A 64f2146 NOT EQUAL; B (comments reworded, the `it(` call wrapped with a trailing comma)
    ALL EQUAL; C ('Find' for 'Search') NOT EQUAL; D (the case's name changed by one word) NOT EQUAL;
    E (one more line in DeckSelector.tsx) CHANGED, NOT EQUAL; F (PR #68 fe65b82 merged into main first) ALL EQUAL.
