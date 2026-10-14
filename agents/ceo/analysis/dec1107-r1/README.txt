DEC-1092 fix round 1 kit (CEO run eb466e52, 2026-10-14). Route A: the reviewer's two kill cases go into
tests/test_scryfall_limit.py. Read this kit; write nothing into it.

expected-test_scryfall_limit.py   The file to put at tests/test_scryfall_limit.py.
                                   git blob bb0318c94a3c3a4c29ebe25ec350df8f358abef4
                                   compare.py digest 3b4454d989b43356 (Python 3.14.5, `uv run --no-project python`)
build_expected.py                  How the expected file was made: the head's file (0febfb6, blob c34457b8) plus
                                   the reviewer's classes TimeOfThe429Tests (after StopTests) and TwoThreadsTests
                                   (after CrossProcessTests), `import threading`, and `AT` -> `AT_10_41_07`.
head-test_scryfall_limit.py        The head's file (blob c34457b8da04a762cee94392231cb6f4a9654b40).
compare.py                         Compares two files' syntax trees with docstrings removed (from
                                   agents/ceo/analysis/dec1112-r1/ on main). Usage: compare.py <expected> <actual>.
kill-run.py                        Applies one mutant of reviewer/mutants-dec1107.py to MUTANT_TREE, runs a command,
                                   restores the files. The tree must be clean (commit first).
reviewer/                          The DEC-1107 reviewer's kill files, runner and kill logs, as they ran at 0febfb6.
logs/root-expected.txt             The root suite with the expected file at 0febfb6: 426 passed, 1 skipped, 1128 subtests.
logs/mutant-K1.txt, -F3, -F1       The test file on each mutant: K1 and F3 fail both TwoThreadsTests cases;
                                   F1 fails TimeOfThe429Tests.
logs/compare-controls.txt          head: DIFFERENT; controls/control-A-reworded.py (docstring, comment, a wrapped
                                   call with a trailing comma): EQUAL; controls/control-B-tolerance.py
                                   (0.002 -> 0.02 in one assertion): DIFFERENT.
pr32-n1/                           DEC-1107 N1: the one-line change to PR #32's AtomicWriteCases case (for DEC-1079),
                                   with the reviewer's merge runs without and with it.
followup/                          DEC-1107 N2 and N4: the reviewer's clockstep.py, huge-retry-after.py and their logs (for the backlog follow-up).
