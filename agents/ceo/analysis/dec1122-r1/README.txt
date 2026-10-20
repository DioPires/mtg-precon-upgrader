DEC-1098 fix round 1 kit (CEO run 03d78557, 2026-10-15). Route A: the reviewer's four kill files
(DEC-1122 verdict 646ef8a3, B1 to B4) go into tests/test_scryfall_callers.py. Read this kit; write
nothing into it.

expected/tests/test_scryfall_callers.py
        The file to put at tests/test_scryfall_callers.py.
        git blob 56ba0145ae7f621421efda9f53c438356413efbf
        compare.py digest ed164ce9884ac1a4 (Python 3.14.5, `uv run --no-project python`)
head-test_scryfall_callers.py
        The head's file (ea4b890, blob 7082ccdd0c025988549dc4137ff6edaa3df9b7bb).
build_expected.py
        How the expected file was made from the head's file. It moves each kill file into
        ComputeTokensTests in the class's own idiom (self.write_deck, self.run_main, the per-subtest
        reset), with the reviewer's inputs and assertions:
          B1 (R1)        three entries join `failures` in
                         test_failed_request_ends_the_run_at_each_request_kind (+15 subtests),
                         and `import http.client`;
          B3 (R10)       test_deck_entry_without_a_name_is_not_reported_as_a_failed_request;
          B4 (R11-R13)   run_batch_answer() and three cases after
                         test_not_found_entry_of_a_batch_is_asked_by_fuzzy_lookup;
          B2 (R8, R17)   test_batch_sorts_the_front_faces_by_code_point (2 subtests), last in the class.
compare.py
        Compares two files' syntax trees with docstrings removed (from
        agents/ceo/analysis/dec1112-r1/ on main). Comments, docstrings, blank lines and wrapping are
        free. Usage: uv run --no-project python compare.py <expected> <actual>.
mutants.py
        The reviewer's runner (/tmp/dec1122/my_mutants.py), unchanged. Env: MUTANT_TREE (a clean
        tree: commit first), MUTANT_OUT, MUTANT_SCRATCH, MUTANT_LOG_DIR. Args: the mutant ids.
reviewer/kills, reviewer/kill-logs
        The reviewer's kill files and their logs, as they ran at ea4b890.
logs/runner.txt, logs/rows.json, logs/<id>.log
        The expected file at ea4b890 (scratch commit d2b86d7, never pushed): HEAD reads
        444 passed, 1 skipped, 1174 subtests passed; R1, R8, R10, R11, R12, R13 and R17 are killed;
        network=False on every row.
logs/merged-suite.txt, logs/merged-control.txt
        The same tree merged with origin/main 461b8fd (scratch merge cee39ba, never pushed):
        448 passed, 1 skipped, 1174 subtests passed, also with SCRYFALL_LIMIT_DIR=/var/empty/dec1122-ceo.
logs/compare-controls.txt
        head: DIFFERENT; controls/control-A-reworded.py (a docstring, a comment, a wrapped call with
        a trailing comma): EQUAL; controls/control-B-errno.py (errno 54 -> 104 in one text): DIFFERENT.
