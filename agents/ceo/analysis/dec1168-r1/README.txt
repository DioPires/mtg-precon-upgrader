DEC-1156 fix round 1 kit (CEO run ddb11b99, 2026-10-16). Route A: the reviewer's kill case for
mutant VMIN (DEC-1168 verdict 54c9d6d5, B1) goes into web/tests/dec1156-engine-title.spec.ts as a
case of its own, and the panel-head comment in styles.css takes the reviewer's figures (N1).
Read this kit; write nothing into it.

expected/web/tests/dec1156-engine-title.spec.ts
        The file to put at web/tests/dec1156-engine-title.spec.ts.
        git blob 903b4583523deff050624b51c9759b4f82ca258c; core.py digest 1112c987d4eab6e3.
        It is the head's file (fe65b82, blob 2acdda7) with 16 lines added after case 1, inside
        `DEC-1156 rules: where they act`: a blank line, a two-line comment and the kill case.
head-dec1156-engine-title.spec.ts
        The head's file (fe65b82).
build_expected.py
        How the expected file was made. Usage:
        python3 -I build_expected.py head-dec1156-engine-title.spec.ts reviewer/short-viewport.spec.ts <out>
        The block already has `test.use({ cards: 'seeded', fonts: 'blocked' })`, the kill file's only
        setting, so the kill file's import and test.use lines stay out. The case's code is unchanged,
        indented by two spaces.
core.py
        The file check. Usage: python3 -I core.py <repo or tree> <ref>, after `git fetch origin`.
        1. The spec: blank lines and lines that hold only a // comment dropped, all whitespace and a
           comma before ) ] or } dropped, then compared with the expected file.
        2. styles.css: every /* */ comment and all whitespace dropped, then compared with the file of
           the merge tree below. Only comments may change. A last line says whether the panel-head
           comment names 299px and 327px (N1).
        3. Every other path: the blob that `git merge-tree --write-tree <merge-base ref origin/main>
           fe65b82` gives.
        Comments and wrapping are free; code is not.
reviewer/
        The reviewer's kill file (short-viewport.spec.ts), its mutant script (mutants.py; usage
        `python3 -I mutants.py apply <id> <tree root>`, which edits styles.css in place) and its logs:
        kill-base.log (head: 2 passed), kill-VMIN.log (1 failed: "740x360": "36px"),
        mutant-VMIN-spec.log (spec 5 passed) and mutant-VMIN-all.log (suite 184 passed).
controls/
        control-A-reworded.spec.ts (one comment reworded, the evaluate call wrapped with a trailing
        comma) and control-B-figure.spec.ts ('390x300': '39px' to '38px').
logs/
        All on the scratch commit f829de2 = 74c3abc (origin/main c704c86 merged with fe65b82, tree
        0701c08) plus the expected spec and the N1 comment. Never pushed. Port 14768.
        compare.txt: core.py on f829de2 ALL EQUAL; on fe65b82 NOT EQUAL (spec DIFFERENT); control A
          ALL EQUAL; control B spec DIFFERENT; control C (VMIN in styles.css) styles.css DIFFERENT.
        lint-typecheck-expected.log: `✖ 10 problems (0 errors, 10 warnings)`, none in the spec;
          typecheck exit 0.
        spec-expected.log: both specs, --workers 1: 13 passed (6 in the new spec).
        mutant-VMIN-expected.log: 1 failed (the new case: "740x360": "36px", "390x300": "30px",
          "320x280": "30px"), 5 passed.
        mutant-C10a-expected.log: 2 failed (case 1 "320": "30px"; the new case "320x280": "30px"),
          4 passed.
        unit-expected.log: `Test Files  51 passed (51)`, `Tests  618 passed (618)`.
        `npx playwright test --list`: 217 tests in 34 files on f829de2; 211 in 33 on c704c86.
