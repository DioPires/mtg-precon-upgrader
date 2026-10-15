DEC-1135 fix round 1 kit (CEO run fd7e150f, 2026-10-15). Route A: the reviewer's kill cases
(DEC-1148 verdict f7d67673, B1 to B4) go into web/src/__tests__/components/DeckSelector.test.tsx.
Read this kit; write nothing into it.

expected/web/src/__tests__/components/DeckSelector.test.tsx
        The file to put at web/src/__tests__/components/DeckSelector.test.tsx.
        git blob 3cb069d765a4db56dcb8a5c415423bf137aa33b4; core.py digest 711125f0d6fc0d93.
head-DeckSelector.test.tsx
        The head's file (a83a297, blob 666c3c1f147921c0ac12829142360929adcb0670).
build_expected.py
        How the expected file was made. Usage:
        python3 -I build_expected.py head-DeckSelector.test.tsx reviewer/DeckSelector.kill.test.tsx <out>.
        One new describe block at the end of the file: the reviewer's block, titled
        'DeckSelector focus after a key switch: review cases (DEC-1148)', the case names without
        their mutant tags, and no copies of the imports, makeDecks, route and Harness (the head's
        file holds the same code; the script asserts it).
core.py
        The file check. Usage: python3 -I core.py <repo or tree> <ref>, after git fetch origin.
        The unit file: blank lines and lines that hold only a // comment dropped, all whitespace
        and a comma before ) ] or } dropped, then compared with the expected file. Every other
        path: the blob that git merge-tree --write-tree <merge-base ref origin/main> a83a297
        gives. Comments and wrapping are free; code is not.
mut.py
        The DEC-1125 kit runner with the DeckSelector unit file as the default command.
        Env: MUT_TREE (the tree's root, clean: commit first), MUT_LOG_DIR (the log folder).
mutants-route-a.json
        The reviewer's 21 mutants (reviewer/mutate.py: S1 to S3 and M4 to M21), renamed RA-*,
        made from mutate.py's table by ast, with no edit changed.
reviewer/
        The reviewer's kill file (blob b003f559f4108575184d349c777c013e98d9be73), its stale-target demo file, its mutate.py and its
        mutant logs (mut-*.log), as they ran on the merged head 69053f1.
controls/
        control-A-reworded.tsx (a reworded comment, an unwrapped render call, a wrapped call with
        a trailing comma) and control-B-value.tsx (toHaveBeenCalledWith(2) for (1)).
logs/
        runner.txt: the 21 mutants on the expected file (scratch commit 3384226 on main c5ddf33
        merged with a83a297, tree 5815e543; never pushed). RA-M4, RA-M5, RA-M15 and RA-M18 each
        fail their own kill case (1 failed | 27 passed (28)); RA-M9, RA-M16, RA-M17 and RA-M21
        28 passed (the equivalent mutants). mutants/ holds one log for each.
        compare-controls.txt: a83a297 NOT EQUAL; the expected file on the merged tree ALL EQUAL;
        control A ALL EQUAL; control B NOT EQUAL; a one-word comment change in DeckSelector.tsx
        NOT EQUAL (CHANGED).
        typecheck.log, eslint.log, unit.log, lint.log, suite.log: the same tree. typecheck exit 0,
        eslint exit 0, the unit file 28 passed (28), lint 0 errors and 10 warnings, vitest 43 files
        and 486 tests.
        head-vs-expected.diff: diff of the head's file and the expected file.
