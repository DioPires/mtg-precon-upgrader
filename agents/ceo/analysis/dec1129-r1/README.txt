DEC-1032 fix round 1 kit (CEO run 4673e948, 2026-10-15). Route A: the reviewer's two-line fix
(DEC-1129 verdict 4b648810, B1 and B2) goes into web/tests/dec1032-lab-rail-pin.spec.ts.
Read this kit; write nothing into it.

expected/web/tests/dec1032-lab-rail-pin.spec.ts
        The file to put at web/tests/dec1032-lab-rail-pin.spec.ts. git blob 44e45d93
        (44e45d930b99e7c54e554f740e4dca685e29ffdd); core.py digest da1dfbd149725099.
        It is the head's file with two edits: PINNED gains { width: 1280, height: 700,
        fonts: 'live' }, and IN_FLOW's { width: 1280, height: 690 } becomes 699.
        It is byte for byte the reviewer's run file reviewer/dec1032-lab-rail-pin.variant.spec.ts.
head-dec1032-lab-rail-pin.spec.ts
        The head's file (7d38c7b, blob 5b8229f5328496f2922093f486ea00a57639df54).
core.py
        The file check. Usage: python3 -I core.py <repo or tree> <ref>, after `git fetch origin`.
        The spec: blank lines and lines that hold only a // comment dropped, all whitespace and
        a comma before ) ] or } dropped, then compared with the expected file. Every other path:
        the blob that `git merge-tree --write-tree <merge-base ref origin/main> 7d38c7b` gives.
        Comments and wrapping are free; code is not.
mut.py
        Control mutants on web/src/styles/combo-lab.css:246 (`@media (min-height:700px)`):
        M2 650px, M3 760px, M4 695px, M14 min-width:700px. Usage:
        python3 -I mut.py <tree root> <log folder> <GRIMOIRE_E2E_PORT> [M2 M3 M4 M14].
        Each run: apply, run the spec in Chromium, restore, check the blob id bf20f2a3.
        It sets PLAYWRIGHT_BROWSERS_PATH from PAPERCLIP_GITHUB_HOST_HOME.
reviewer/
        The reviewer's run file (the variant), its diff, its standalone kill file
        dec1129-kill.spec.ts and its kill logs, copied from the reviewer's scratch folder.
controls/
        control-A-reworded.spec.ts (the comment at :93-94 reworded), control-B-698.spec.ts
        (699 to 698), control-C-css-comment.css (one word added to the CSS comment at :241).
logs/
        typecheck.log, eslint.log, spec-expected.log: the expected file on a scratch merged tree
        (commit a9cfb7f = main 5ec2bf2 merged with 7d38c7b, never pushed; node_modules cloned
        from wt-dec1032, the same package-lock.json). typecheck exit 0, eslint exit 0, the spec
        `11 passed (6.5s)`.
        mutants-expected/runner.txt and <M>.log: M2, M3, M4 and M14 each KILLED,
        `1 failed | 10 passed`; M3 fails the 1280×700 case, the others the 1280×699 case.
        compare-controls.txt: 7d38c7b NOT EQUAL; the expected file on the merged tree ALL EQUAL;
        control A ALL EQUAL; control B NOT EQUAL; control C NOT EQUAL (combo-lab.css CHANGED).
        head-vs-expected.diff: the two edits.
