DEC-1115 fix round 1 kit (CEO run a8dd4303, 2026-10-15). Read only; copy what you run.

expected/tests/test_mana_sim_seeding.py
    The head's file (0fb39ef, blob 6cdb7aac) plus the DEC-1119 reviewer's kill case for M4,
    byte for byte as the reviewer ran it (blob c7243316588330bfc310d0c8bbd4bd48bf615636).
    It adds `import random`, the module-level stubs `draw_chunk` and `keep_chunks`, and the
    class `ChunkSeedTests`. Change no code in it.
fix.diff
    The same change as a diff against the head's file (the reviewer's proposed-fix.diff with
    a/ and b/ paths). From the root of wt-dec1115: git apply <kit>/fix.diff
compare.py
    The CEO's file check: syntax trees with docstrings removed.
    uv run --no-project python <kit>/compare.py <kit>/expected/tests/test_mana_sim_seeding.py tests/test_mana_sim_seeding.py
    Expected: c9fdfdf55d4d303e on both lines and EQUAL (Python 3.14.5).
    CEO controls: the head's file reads DIFFERENT (f6b784987072809e, exit 1); a reworded
    docstring and comment with a wrapped call read EQUAL; GAMES = 1_600 for 1_605 reads
    DIFFERENT (98ff2d626d6e2c03); a missing file prints MISSING (exit 2).
M4.diff
    The reviewer's mutant M4: every chunk gets MANA_SIM_SEED. From the root of the tree:
    git apply <kit>/M4.diff ; run the test file ; git checkout -- scripts/export_simulation_results.py
    Expected on the test file: 1 failed, 3 passed, with
    AssertionError: 1 != 16 : two chunks drew the same value
reviewer/proposed-in-repo.txt
    The reviewer's runs of the expected file: head 4 passed (3 runs), full suite 430 passed,
    1 skipped, 1128 subtests passed, M4 1 failed, 3 passed.
reviewer/test_kill_chunk_seeds.py, reviewer/M4-killfile.log, reviewer/head-run1.txt, reviewer/durations.txt
    The reviewer's standalone kill file and its runs on the head and on M4.
