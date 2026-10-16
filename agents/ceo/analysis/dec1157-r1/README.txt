DEC-1157 fix round 1, route A kit (CEO run 55662e1e, 2026-10-15). Verdict: DEC-1165 comment 7c96121f.

expected/tests/test_generate_candidate_pool.py   git blob 7523883a (1,308 lines). The head's file (PR #67 at f5eda73,
    blob 494b8754, 1,276 lines) plus the reviewer's three kill methods K1, K2 and K3 at the end of GapSeatWriteTests,
    after test_file_that_differs_only_in_role_pool_is_rewritten, with their code unchanged.
    K1 kills R1 and X4 (B1), K2 kills X2 (N2), K3 kills R5, R6 and R7 (N1).
    Syntax digest without docstrings (compare.py under uv's Python 3.14.5): 4bc531a7dee7c4e5.

build_expected.py   builds the expected file: `uv run --no-project python -I build_expected.py <head file> <kill file> <out>`.
compare.py          syntax trees with docstrings removed (copied from dec1121-r1, from dec1112-r1).
check.py            the file check: `uv run --no-project python -I check.py <repo> <ref>` after `git fetch origin`.
                    The test file by compare.py; every other path against `git merge-tree --write-tree
                    <merge-base of ref and origin/main> f5eda73`. Prints ALL EQUAL or NOT EQUAL.
ctl.sh              the head and the six survivors on a clean committed tree: `bash ctl.sh <tree> <log dir> [ID ...]`.
                    It applies reviewer/mutate.py unchanged, runs tests/test_generate_candidate_pool.py with
                    PYTHONDONTWRITEBYTECODE=1 after it removes every __pycache__ under scripts/ and tests/, and
                    restores the script with `git checkout`.
ctl-check.sh        the controls of check.py (local commits only, never pushed). ctl-files/ holds their files.
reviewer/           the reviewer's kill file (blob d04d750a), mutate.py, runners, verdict, N3 demo and summaries, unchanged.

logs/ (the CEO's runs on a detached scratch tree at a2379a0: SIM f31be8d = f5eda73 + the expected file, merged with
origin/main 32e1057; tree 554acff2; never pushed; no private input linked)
    suite.log: 655 passed, 1 skipped, 1220 subtests passed (the head 652, plus 3).
    file.log: 62 passed, 4 subtests passed (the head 59, plus 3).
    ctl-all.txt and ctl/: head 62 passed. R1, X4, X2, R5, R6 and R7 each `1 failed, 61 passed, 4 subtests passed`:
      R1 and X4 fail K1 (R1 finds no `wrote` line; X4 raises JSONDecodeError), X2 fails K2, R5, R6 and R7 fail K3.
    check-controls.txt: head f5eda73 NOT EQUAL (DIFFERENT); SIM ALL EQUAL; SIM merged with main ALL EQUAL;
      good (a reworded docstring, a comment line and a wrapped assertEqual) ALL EQUAL; bad (7 for 8 in K1) NOT EQUAL;
      script (a comment on the new_text line of scripts/generate_candidate_pool.py) NOT EQUAL (1 CHANGED).

pytest.ini sets testpaths = tests, so no file under agents/ceo/analysis/ joins the root suite.
