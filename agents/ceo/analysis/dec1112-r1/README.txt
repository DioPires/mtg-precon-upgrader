DEC-1079 fix round 1 kit (CEO run 2dd76c71, 2026-10-14). Read only; copy what you run.

expected-test_fetch_mutant_kills.py  The DEC-1112 reviewer's six kill cases, byte for byte
                                     (blob e5d2e196356ecb197d3f7ccff9ee7fc904e62e36). It goes in
                                     as tests/test_fetch_mutant_kills.py. Change no code in it.
compare.py                           The CEO's file check: syntax trees with docstrings removed.
                                     uv run python compare.py expected-test_fetch_mutant_kills.py <your file>
                                     Expected digest 442223bb16b920e5 and EQUAL.
reviewer/run_kills.py                How the reviewer ran each kill case on its mutant (paths point to
                                     /tmp/dec1112 and the old file name; adapt them).
reviewer/mutants_mine.py             The reviewer's mutants (id, what, old, new). S1, S4, R1, R10 and R14
                                     still apply to the fixed script; R4's line is the one the fix replaces.
reviewer/kill-*.log                  The reviewer's kill runs on 872a14d and on each mutant.
reviewer/demo8a.py, demo8a.log       The reviewer's B1 demo: a reversible_card batch printing without a
                                     price ends the run with KeyError: 'oracle_id'.
