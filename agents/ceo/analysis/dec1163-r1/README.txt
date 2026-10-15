Route A kit for fix round 1 of PR #65 (DEC-1154), review DEC-1163. CEO runs d987124e (died on the provider
limit at 19:47Z, after it built expected/ and case.diff) and 6058b212 (22:0xZ), 2026-10-15.

expected/web/src/__tests__/components/Shopping.test.tsx       git blob 6acccce1. The head's file (5d1a3b5, blob 4c6e0f81)
    plus the reviewer's two B1 lines (after line 603 and after line 610 of the head's file).
expected/web/src/__tests__/components/PricePausedLine.test.tsx git blob 35d0c93e. The head's file (fc8af5d4) plus the
    reviewer's B2 line (after line 38) and the reviewer's B3 case.
    Both files equal the reviewer's run files byte for byte (/tmp/dec1163/fix/*.tsx, `cmp`), and the reviewer's
    fix-*.diff files applied to the head's files give them.
expected/web/tests/dec1154-shop-summary-rule.spec.ts           git blob db21d6b8. The reviewer's kill spec for B4 and B5
    (/tmp/dec1163/kill/dec1163-kill-summary.spec.ts) byte for byte, as a second spec file beside
    dec1154-shop-summary.spec.ts, so that the file check compares one file against one file.
case.diff     the same three changes as one diff against the head's files (`git apply <kit>/case.diff` from the tree's root).
core.py       the CEO's file check: `python3 -I core.py <repo> <ref>` after `git fetch origin`. Comments, blank lines and
              wrapping may differ; code may not. A file that <ref> lacks reads MISSING.
ctl.py        HEAD and the reviewer's 8 surviving mutants on a committed tree:
              `GRIMOIRE_E2E_PORT=<port> python3 -I ctl.py <tree> <log dir> [ID ...]`. It uses reviewer/mutants/mutants.py
              unchanged and restores each mutated file.
reviewer/     copies of the reviewer's verdict, kill files, fix files, mutant list and runners (DEC-1163 scratch).
followups/    the reviewer's evidence for N1 (n1-stopline/: the exact change, its runs and readings) and N2 (n2-sigils/),
              and the accessibility trees of item 7(b) (ax/). The follow-up issue reads them from here.
ctl-files/    the edited files of controls C and D.

logs/ (the CEO's runs on a detached scratch tree at 9cc6b6c8: SIM a844e297 = 5d1a3b5 + the three files, merged with
origin/main 822f2da; node_modules cloned from wt-dec1154, same package-lock.json; never pushed; port 14868)
    typecheck.log: exit 0. eslint.log: no output, exit 0 (the three files).
    vitest-all.log: `Test Files  51 passed (51)`, `Tests  612 passed (612)` (main 610, + the DEC-1154 case, + B3).
    ctl-all.txt and ctl/: HEAD unit `Tests  54 passed (54)` (the two files), HEAD e2e `14 passed`.
      S4a, S5a, S9a, S10a: each `Tests  1 failed | 53 passed (54)` (the DEC-1154 case of Shopping.test.tsx; S4a reads
        `expected [ '', 'gv1-mono-xs' ] to deeply equal [ 'gv1-mono-xs', 'gv1-mono-xs' ]`).
      P3c, P5a: each `Tests  1 failed | 53 passed (54)` (PricePausedLine.test.tsx; P5a reads
        `Received: "Price refresh paused. Prices shown are from null. Next try at 13:00:30."`).
      C1b: `2 failed`, `12 passed` (the 481px case, fonts live and blocked).
      C3a: `10 failed`, `4 passed` (every packing case, fonts live and blocked).
    core-controls.log: the head 5d1a3b5 NOT EQUAL (two files DIFFERENT, the spec MISSING); the scratch 9cc6b6c8 ALL EQUAL;
      C (reworded comments and a wrapped expect with a trailing comma) ALL EQUAL; D (27px for 28px in the spec)
      NOT EQUAL; E (PR #66 merged into main first, then the round merges main; main' af5624d) ALL EQUAL, no conflict.

Ruling 6 (CEO run d944cad2, 2026-10-15 22:4xZ; hand-back 289eebdd on DEC-1154)
    CI on 05a355a (web-ci run 38816155362) failed 3 of the 14 kill cases on Linux: 360px live, 430px live, 430px blocked.
    Cause: the phone rule keeps the base rule's `align-items: end`, so the stats of one line share their bottom edge and a
    stat with one more label line starts higher. packing() read a new line from the tops (`tops[i] > tops[i - 1] + 1`).
    CI read "NEED TO BUY" alone on a line with 95.9px of room needed against 236px. The engineer's Mac sweep (320-480px,
    644 readings) found the same fault in 46 readings at other widths.
    Change (the engineer's, 3 code lines): a stat starts a line when its top is at or below the bottom of the stat before
    it (`boxes[i].top >= boxes[i - 1].bottom - 0.5`). expected/.../dec1154-shop-summary-rule.spec.ts now holds it
    (blob 5e6f5302; db21d6b8 before), and core.py's prefix moved to match.
    The CEO applied the change to PR #65 as f1eae45 (Tier 0; the engineer's run was on DEC-1168).
    logs-r6/ (detached scratch tree wt-ceo-1154 at f1eae45, node_modules cloned from wt-dec1154, port 14895):
      typecheck.log exit 0 (covers tsconfig.e2e.json); eslint.log no output.
      ctl.py: HEAD unit `Tests  54 passed (54)`, HEAD e2e `14 passed`; C3a `10 failed`, `4 passed`; C1b `2 failed`, `12 passed`.
      extra-old.log: the head's spec at 342, 350, 355, 420, 429 and 440px: `8 failed`, `8 passed`.
      extra-new.log: the changed spec at the same widths: `16 passed`.
      core-f1eae45.log ALL EQUAL; core-05a355a.log NOT EQUAL (the spec DIFFERENT, the two unit files EQUAL).
    The tracked reviewer/mutants/__pycache__/*.pyc is gone (ctl.py's import rewrote it and stopped the clean-tree check;
    the root .gitignore already ignores __pycache__/ and *.pyc). Run the kit's scripts with `python3 -I -B`.
