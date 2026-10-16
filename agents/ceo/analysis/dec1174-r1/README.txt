Route A kit for fix round 1 of PR #75 (DEC-1172), review DEC-1174. CEO run 557edb27, 2026-10-16.

expected/  the reviewer's kill file for B1, byte for byte (verdict bab1dab3, /tmp/dec1174/kill/dec1174-deck-route-kill.test.tsx,
           equal to the verdict's code block):
    web/src/__tests__/components/DecklistNoRefresh.test.tsx   git blob b4c59efc (kills M10 at :58)
apply.py   the round's edits: `python3 -I apply.py <tree>` (git blob e019e4de). It copies the kill file and makes
           N2 and N1 (web/tests/dec1102-card-data.spec.ts), N3 and N4 (web/src/data/cardCache.ts header, web/README.md
           twice, the spec header). Each edit finds its old text once or stops; a second run prints "already".
           The spec after apply.py equals the reviewer's run file reviewer/dec1102-card-data.n-items.spec.ts except
           for the N4 header lines 7 to 9 (comments).
core.py    the CEO's file check: `python3 -I core.py <repo> <ref>` after `git fetch origin` (git blob be6efbc8). It
           builds SIM (e5e95b4 plus apply.py's edits and the kill file), merges SIM with `git merge-base <ref>
           origin/main`, compares the kill file with comments, blank lines and whitespace dropped, and checks that
           every other path (the spec, cardCache.ts and the README among them) keeps the merge's blob byte for byte.
           When PR #70 merged first, web/README.md conflicts; if main's README is blob 0e372b5f (e886907 + a75bcc2),
           the check reads pr70/README.resolved.md plus the edits. On e5e95b4 it prints MISSING and NOT EQUAL.
ctl.py     the CEO's controls for core.py: `python3 -I ctl.py <repo>` (logs/ctl.txt), all as expected:
    A  e5e95b4: the kill file MISSING, three paths CHANGED, NOT EQUAL.
    B  origin/main e886907 merged into e5e95b4, then apply.py: ALL EQUAL (commit 53e1cfd).
    B2 B with the kill file's first comment line reworded and one call wrapped: ALL EQUAL.
    C1 B with `LOOKUP_SPACING_MS + 30` in the kill file: DIFFERENT, NOT EQUAL.
    C2 B with waitForTimeout(300) for N1's 3_000: the spec CHANGED, NOT EQUAL.
    C3 B without N3's ", and asks for none itself": cardCache.ts CHANGED, NOT EQUAL.
    D  PR #70 a75bcc2 merged into main first, README resolved with pr70/README.resolved.md, then apply.py:
       ALL EQUAL (commit 2c07848).
pr70/README.resolved.md  the reviewer's resolution of web/README.md for main e886907 + e5e95b4 + a75bcc2 (item 9,
           /tmp/dec1174/pr70-merge-README.reviewer.md, git blob 71462b63). Use it only when the round's merge of
           origin/main stops on web/README.md and `git rev-parse origin/main:web/README.md` is 0e372b5f.
reviewer/  the reviewer's files: the kill file, the N1/N2 diff and run spec, the kill logs (head passes, M10 fails at
           :58), the N item logs, the typecheck log, and the verdict text.
logs/      the CEO's runs on detached scratch trees (node_modules cloned from wt-dec1172; package-lock.json equal by cmp;
           both trees removed after the runs):
    B 53e1cfd (main e886907 + e5e95b4 + apply.py):
      typecheck.log exit 0.  eslint-files.log no output, exit 0 (kill file, spec, cardCache.ts).
      eslint-all.log `✖ 10 problems (0 errors, 10 warnings)` (main's count).
      unit-all-B.log `Test Files  51 passed (51)`, `Tests  618 passed (618)` (main's push run 38882028694 count:
        the branch deletes dec1149-tile-kill.test.tsx with 1 case and adds this file with 1 case).
      kill-B.log `Tests  1 passed (1)`.  kill-M10-B.log fails at DecklistNoRefresh.test.tsx:58:26,
        `expected "spy" to not be called at all, but actually been called 1 times`; Decklist.tsx restored after.
    D 2c07848 (main e886907 + a75bcc2 + e5e95b4 + apply.py): typecheck-D-pr70.log exit 0;
      unit-all-D-pr70.log `Test Files  53 passed (53)`, `Tests  650 passed (650)` (the reviewer's merged70 read 52 and
      649 without the kill file).
    The CEO ran no e2e case. The reviewer ran the N1/N2 spec on the head (n-items-head.log, 6 passed) and N1 on main's
    tile (n-items-281-main-tile.log, 6 of 6 failed). The implementer's runs are the record for the merged head.
