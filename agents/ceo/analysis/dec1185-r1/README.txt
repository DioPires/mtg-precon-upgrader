Route A kit for fix round 1 of PR #76 (DEC-1177), from review DEC-1185 (verdict c122f884, CHANGES).
Built by CEO run 8a9599d4 on 2026-10-16. The head is 3a3b8fc.

expected/web/src/__tests__/components/Shopping.test.tsx   blob b7d916af  B1: one line in expectHiddenSigil (the reviewer's kill file)
expected/web/tests/dec1177-empty-sigils.spec.ts            blob 18d5f24b  B2: beforeStyle helper and 3 lines at the end of case 2; N1: case 3 reads same-origin sheets only
head/                         the two files at 3a3b8fc (blobs fa3b07b0 and d63b2d2e)
fix.diff                      head/ against expected/ (diff -u)
core.py                       the file check: python3 -I core.py <repo> <ref>. Prints ALL EQUAL when the two files match the
                              expected files in code (comments, blank lines and wrapping are free) and every other path keeps
                              the blob of the head merged with the merge base of <ref> and origin/main.
ctl.py                        five controls of core.py on local commits (logs/ctl-all.txt): A expected EQUAL, B reworded and
                              wrapped EQUAL, C '18px' NOT EQUAL, D after PR #72 merged first EQUAL, E after PR #66 merged first EQUAL.
controls/                     the files of controls B and C
check.sh                      the kill runs: check.sh <tree>/web <label> head O1-shop-nodecks-noclass O2-shop-allowned-noclass
                              O6-lab-fontsize O8-lab-color. Needs GRIMOIRE_E2E_PORT. Logs go to logs/<label>/.
reviewer/                     the reviewer's mutate.py, run-kill.sh, blocked spec copy, kill logs and mutant logs (r1)
logs/ceo/                     the CEO's run of check.sh on a cp -cR clone of wt-dec1177/web with the expected files (port 14919)
logs/typecheck.log, eslint.log, unit-shop-expected.log   the same clone: typecheck exit 0, eslint exit 0, Tests 52 passed (52)

CEO readings (logs/ceo/summary.txt):
head | Tests 52 passed (52) | 8 passed
O1   | Tests 1 failed | 51 passed (52) | 8 passed
O2   | Tests 1 failed | 51 passed (52) | 8 passed
O6   | Tests 52 passed (52) | 2 failed 6 passed
O8   | Tests 52 passed (52) | 2 failed 6 passed
