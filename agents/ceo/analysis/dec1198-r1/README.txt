Route A kit for fix round 1 of PR #81 (DEC-1191), review DEC-1198, verdict 14a16973 (Simulation Engineer, 09:11Z).
CEO run 15bb14f0, 2026-10-17. Head 699cb7e (branch dec-1191-classifier-followups), main e6d472e.

apply.py   the round's edits: `python3 -I apply.py <tree>`. Three edits; each finds its old text once or stops, and a
           second run prints "already" for each:
    B4      scripts/auto_tag_roles.py: `_REPEATABLE_DRAW` also reads "exile this card from your graveyard" as a cost
            that spends the card. The pattern is the reviewer's (reviewer/atr_fix_p2.py), wrapped over two string
            literals; compare.py reads it EQUAL to the reviewer's file (digest 4258a3f7bf19205d).
    KILL-a  tests/test_auto_tag_roles.py: the reviewer's ToughnessCutKillTests (B3), byte for byte, after
            ToughnessCutTests.
    KILL-b  tests/test_auto_tag_roles.py: the reviewer's CantripKillTests (B1), DrawCountKillTests (B2) and
            GraveyardCostFaultTests (B4's case), byte for byte, after CantripTests.
           After apply.py on 699cb7e: scripts/auto_tag_roles.py is blob d325d1fc, tests/test_auto_tag_roles.py is
           blob 30e11b5f.
expected/  the round's files: the two files above, and the two pools that the generator writes again on them
           (data/commanders/anvil-chorus and stampede-acres: Campus Crier's deck_role goes from card-draw to null;
           no other field but generated_at changes, and no other pool changes).
core.py    the CEO's file check at the hand-back: `uv run --no-project python -I core.py <repo> <ref>` after
           `git fetch origin`. The two Python files by syntax tree with docstrings removed (comments, docstrings,
           blank lines and wrapping are free), the two pools as JSON without generated_at, and every other path
           against `git merge-tree --write-tree <merge-base of ref and origin/main> 699cb7e`.
ctl.sh     the controls of core.py, on local commits in a scratch tree (logs/ctl.txt), all as expected:
    A   699cb7e: 4 paths DIFFERENT, NOT EQUAL.
    B   the round (apply.py and the pool run): ALL EQUAL.
    B2  B with a docstring and a comment reworded and one call wrapped: ALL EQUAL.
    C1  B with mutant G3: scripts DIFFERENT, NOT EQUAL.
    C2  B with anvil-chorus's pool from 699cb7e: that pool DIFFERENT, NOT EQUAL.
    C3  B with one more line in docs/role-taxonomy.md: CHANGED, NOT EQUAL.
mut.py     the mutants on the round's tree: `uv run --no-project python -I mut.py <tree> <log folder>`. It writes
           each mutant into scripts/auto_tag_roles.py, runs tests/test_auto_tag_roles.py, saves mut-<id>.log and
           restores the file's bytes (also on an error). logs/mut.txt holds the CEO's run:
    baseline  94 passed, 39 subtests passed.
    the 25 survivors of the verdict (B1: X1, X3, X4, X6, X7, X9; B2: X5, X10 and the 12 XW-*; B3: Y1, Y2, Y4,
              Y6, Y7), with X6 moved to the round's line: each fails its own kill case, and no other test fails.
    M3, A11   the hand-back's M3 and the reviewer's A11, moved to the round's line: each still fails (3 and 6).
    G1  the head's lookahead (the graveyard alternative dropped)   fails GraveyardCostFaultTests.
    G2  "from your hand" for "from your graveyard"                 fails GraveyardCostFaultTests.
    G3  "exile this card" for "exile this card from your graveyard" SURVIVES (94 passed). Ruled: its only kill case
        would pin a fault that the head shares (a one-shot draw behind "exile this card from your hand:" reads
        card-draw), so it goes to DEC-1197 item 3 as a candidate rule.
    G4  "from a graveyard" for "from your graveyard"               fails GraveyardCostFaultTests.
logs/      the CEO's runs on a detached scratch tree at 699cb7e with apply.py (the tree removed after):
    suite-links.log              713 passed, 1256 subtests passed (before the pool run).
    suite-links-after-pools.log  713 passed, 1256 subtests passed.
    suite-nolinks.log            712 passed, 1 skipped, 1256 subtests passed (the skip is the Scryfall mirror test).
    pools-run1.log               19 "no change", anvil-chorus and stampede-acres written.
    pools-run2.log               21 "no change".
    metrics.log                  Wrote 0 metrics file(s) (weights=A).
    mut.txt, mut/                the mutant run above.  ctl.txt  the controls above.
reviewer/  the reviewer's files from /tmp/dec1198/: the kill file and its log, kill_run.py, the mutant definitions,
           atr_fix_p2.py (the B4 run file) and verdict.md.
followups/ the reviewer's evidence for DEC-1197 (probe P3, the B4 census, probes P1 and P2): atr_fix_p3.py and
           atr_fix_p23.py (the narrow `_DRAW_AGAIN` rule), fix_p3_changed.txt (its 20 cards), fix_p2_changed.txt
           (B4's 10 cards), p3.py, p3_item1.txt, p3_names.txt, probes.py, probes.txt, the lookups and pool70_show.txt.
