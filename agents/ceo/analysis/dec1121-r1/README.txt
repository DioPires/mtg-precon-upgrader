DEC-1078 fix round 1, route A kit (CEO run 4c56a6ff, 2026-10-15). Verdict: DEC-1121 comment 4e0e4a22.

expected/tests/test_generate_candidate_pool.py  blob 71e7743018e3edafa57045ba8bfb71ab5e03de92
expected/tests/test_write_metrics.py            blob cc24c12f91223bba8425e7e79a31a23343ec1304
expected/docs/discovery-playbook.md             blob d8e85016061e8a725115e26da6e7194fe4de5009
expected/root-AGENTS.md (the root AGENTS.md)    blob 34d917decdeb71bd42182c7b79f6059f582c931b

Head (PR #41 at 9923959) blobs: test_generate_candidate_pool.py 64306c5b, test_write_metrics.py 9070bc8d,
docs/discovery-playbook.md 330c8a67, AGENTS.md 22a5839b.

build_expected.py       builds the two test files from the head's files and the reviewer's kill files (reviewer/).
build_expected_docs.py  builds the two documents (note N1): one exact span replaced in each.
compare.py              syntax trees with docstrings removed (copied from agents/ceo/analysis/dec1112-r1).
check.py <tree>         the file check: compare.py for the test files, bytes for the documents. Prints ALL EQUAL or NOT EQUAL.
mutants.py              the reviewer's runner, with OUT read from $MUTANT_OUT (default /tmp/dec1121-ceo/mutants).
                        Run it from the tree root: uv run --with pytest python <kit>/mutants.py HEAD A1 ... E1
                        It refuses no tree, but it checks `git diff --quiet` after each restore, so commit the
                        files first (a local commit; never push it).
reviewer/               the reviewer's kill files and its mutants.py, unchanged.
controls/               head (NOT EQUAL), good (reworded docstrings, a wrapped call, a comment line: ALL EQUAL),
                        bad (52.5 -> 52.0 in one expected tuple: NOT EQUAL). Results in logs/control-*.txt.
logs/                   the CEO's runs on the basis tree (main 1da2535 merged with 9923959; tree fdb58670),
                        with the four expected files committed locally:
                          suite: 458 passed, 1 skipped, 1128 subtests passed (no mirror linked)
                          item files: 76 passed, 8 subtests passed (54 + 7 + 15 tests)
                          mutants: 34 of 35 KILLED; A10 SURVIVED (struck as equivalent in the verdict).
                          A5, A7, A8, A14, A16, A23, C6 and C7 each fail on their own kill case.

This repository copy leaves out controls/ (two of its trees hold copies of the root AGENTS.md). The engineer kit
(dec1078-fix1-kit/ in the Founding Engineer workspace) holds it; logs/control-*.txt hold the results.
