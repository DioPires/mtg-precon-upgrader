DEC-1124 fix round 1 kit (CEO run c2780f3f, 2026-10-15). Read only; copy what you run.
Review: DEC-1126, verdict 112aed95 (CHANGES), correction 8bd08426. Reviewer folder:
/Users/dpires/.paperclip/instances/default/workspaces/8ea33a50-69a7-4a75-bcc1-245bd1e7c73a/dec1126-review/

expected/tests/test_card_lookup.py
    The reviewer's kill file, byte for byte (blob 43579aa1dd7e8a57bdf9479bfda0ec384c251700).
    It is the head's file (7ca7e9a, blob 8cfd61d1) plus `import sys`, `import urllib.error`,
    one docstring line (item 5) and the class `ReviewCases` (10 cases). It changes no case of
    the head. Change no code in it.
compare.py
    The CEO's file check: syntax trees with docstrings removed.
    uv run --no-project python <kit>/compare.py <kit>/expected/tests/test_card_lookup.py tests/test_card_lookup.py
    Expected: 0a571eaeb6c0250e on both lines and EQUAL (Python 3.14.5 from uv).
    CEO controls (logs/compare-controls.txt, read with Python 3.15.0, so other digests):
    the head's file reads DIFFERENT; a reworded docstring with a wrapped call reads EQUAL;
    a date one second later in one case reads DIFFERENT; a missing file prints MISSING (exit 2).
    Under uv's 3.14.5 the head's file reads 44a5c899578f7eed.
expected/card-pool-line.txt
    N1: the whole "- **Card pool**:" line of AGENTS.md, with two sentences added after the
    agent-run command: "QUERY takes Scryfall's search syntax, `released<=YYYY-MM-DD` included.
    Put single quotes around a QUERY that holds a double quote." Built by build_line.py from
    AGENTS.md of `main` 2e2d32a merged with 7ca7e9a.
check_line.py
    uv run --no-project python <kit>/check_line.py <kit>/expected/card-pool-line.txt AGENTS.md
    Expected: 25d57655ec59ed18 on both lines and EQUAL. The merged head reads 8388ef9e92704f6b
    and DIFFERENT. Controls: logs/line-controls.txt (one word changed reads DIFFERENT).
build_line.py
    How the CEO built the line. You do not need to run it.
run_survivors.sh, diffs/
    The 14 mutants that survived the head's 21 cases, as the reviewer wrote them (a/ b/ paths).
    From the tree's root, with a clean tree:
    <kit>/run_survivors.sh "$PWD" <kit>/diffs <your log folder> <ID> [<ID> ...]
    It applies each diff, removes every __pycache__, runs tests/test_card_lookup.py with
    PYTHONDONTWRITEBYTECODE=1, restores scripts/card_lookup.py and checks `git diff --quiet`.
    Expected with the kill file: "1 failed, 30 passed, 2 subtests passed" for 13 of them and
    "2 failed, 31 passed" for ms-narrow-except.
logs/
    The CEO's runs on main 2e2d32a merged with 7ca7e9a plus the kill file (scratch commit,
    never pushed): suite 549 passed, 1 skipped, 1191 subtests passed; the test file with every
    socket connect refused 31 passed, 2 subtests passed; the 14 survivors (mutants-kill/), each
    one failed as above; three survivors on the head's own file (mutants-headfile/), 21 passed.
reviewer/
    The reviewer's verdict text and its kill runs (kill-<mutant>.log, kill-base-*.log).
