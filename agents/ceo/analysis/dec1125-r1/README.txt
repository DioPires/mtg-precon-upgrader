DEC-1077 fix round 1 kit (CEO run b9be56ec, 2026-10-15). Route A: the reviewer's kill cases
(DEC-1125 verdict 49e08dfa, B1 to B3) go into web/src/__tests__/components/Apothecary.test.tsx.
Read this kit; write nothing into it.

expected/web/src/__tests__/components/Apothecary.test.tsx
        The file to put at web/src/__tests__/components/Apothecary.test.tsx.
        git blob beea251e3c073401a9a3a7d5e9b08ab8288e7144; core.py digest dfdc76531882187a.
head-Apothecary.test.tsx
        The head's file (854aad6, blob 7cb69550336d2245f434811499bb852849412ae0).
build_expected.py
        How the expected file was made from the head's file. Usage:
        python3 -I build_expected.py head-Apothecary.test.tsx <out>.
          K1 (B1) and K2 (B2): into `resilience maladies (DEC-1007)`, after the redundancy table.
                  `fig(container)` reads as `part(chips(container)[0], '.gv1-apo-malady-fig')`.
          K3 (B3): into `role labels from the shared map (DEC-1077)`, after the Win-Cons case, as
                  the reviewer's nested describe, without its `remedy` helper (the block has it).
core.py
        The file check. Usage: python3 -I core.py <repo or tree> <ref>, after `git fetch origin`.
        The unit file: blank lines and lines that hold only a // comment dropped, all whitespace
        and a comma before ) ] or } dropped, then compared with the expected file. Every other
        path: the blob that `git merge-tree --write-tree <merge-base ref origin/main> 854aad6`
        gives. Comments and wrapping are free; code is not.
mut.py
        The reviewer's runner (/tmp/dec1077-review/mut.py) with one change: the log folder comes
        from MUT_LOG_DIR. Env: MUT_TREE (the tree's root, clean: commit first), MUT_LOG_DIR.
        Default command: npx vitest run src/__tests__/components/Apothecary.test.tsx in web/.
mutants-route-a.json
        The reviewer's 12 kill-file mutants (reviewer/mutants-kill.json) renamed RA-*, with the
        unit file as the command, and M1 of the DEC-1125 brief as a control (RA-M1-floor-plus-2).
reviewer/
        The reviewer's kill file (blob 2d03ca52, the verdict's code block), its runner, its
        mutant list and its kill logs, as they ran on the merged head 3eea17e.
controls/
        control-A-reworded.tsx (reworded comments, a wrapped render call with a trailing comma)
        and control-B-figure.tsx ('2.3 / 3.7 lines' to '2.3 / 3.6 lines').
logs/
        runner.txt: the 13 mutants on the expected file (scratch commit c30103a on the merged head
        2f2473a, tree of main 695dabd merged with 854aad6; never pushed). RA-A8 49 passed (the
        equivalent mutant); the 11 kill mutants each fail their kill case; RA-M1 2 failed.
        compare-controls.txt: 854aad6 NOT EQUAL; the expected file on the merged tree ALL EQUAL;
        control A ALL EQUAL; control B NOT EQUAL; a one-word change in Apothecary.tsx NOT EQUAL.
        typecheck.log, eslint.log, unit.log, lint.log, suite.log: the same tree. typecheck exit 0,
        eslint exit 0, the unit file 49 passed (49), lint 0 errors and 10 warnings, vitest 41 files
        and 468 tests.
        head-vs-expected.diff: diff of the head's file and the expected file.
