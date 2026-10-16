Route A kit for fix round 1 of PR #64 (DEC-1162), review DEC-1166. CEO run 4770a8ed, 2026-10-15.

expected/web/tests/dec1152-rate-check-post.spec.ts  git blob 50707b7b. The head's file (824d0c0) with:
    B1: the reviewer's case `three autocompletes at once pass` (kill file :16) in a new describe block
        after the first one, and the constant AUTOCOMPLETE after LOOKUP;
    N1: the fourth call form 'fetch(request, init)' (fetch(new Request(url), init)) in the loop of
        the page's clock (kill file :30's case, as a loop entry);
    the header comment names the new case.
expected/web/README.md         git blob efe019e4. The head's file with N2: the reviewer's sentence ("... spaces
    its POSTs 1,200 ms apart. Two batches in 1 s start 4 requests and fail the test."), and the paragraph's
    tail rewrapped.
expected/web/tests/support/test.ts  git blob 3ed9f6dd. The head's file with N2's two older sentences, comments
    only: the header (lines 17-19) no longer says that every case proves the app's limit, and the 'repo'
    doc (line 38) reads 1,200 ms, not 600 ms. No code changes.
case.diff          the same changes as one diff against the head's three files (apply from the tree's root:
                   `git apply <kit>/case.diff`; checked: it gives the three blob ids above).
build_expected.py  builds the expected files from the head (asserts each anchor once).
core.py            the CEO's file check: `python3 -I core.py <repo> <ref>` after `git fetch origin`.
                   The spec: code compare (comments and wrapping free). README.md and test.ts: words
                   compare (wrapping free, words exact). Every other path keeps the blob of SIM merged
                   with the ref's merge base with origin/main.
ctl.py             the CEO's copy of the reviewer's run_hand.py (reviewer/): `python3 -I ctl.py <tree> <log dir>
                   <port> [ID ...]`. BASE (the four specs, no mutant), S4 and R1 (the round's spec), S4X and
                   R1X (the four specs). It refuses a tree with tracked changes.
reviewer/          copies of the reviewer's kill file (blob 3acbb3be), run_hand.py and verdict.md.
logs/              the CEO's runs on a detached scratch tree of 824d0c0 with the expected files committed
    locally (85e9921, never pushed). main has no change under web/, data/ or .github/ since the head's merge
    base 1e1634a, so the head's web tree is the merged web tree.
    lint.log: `10 problems (0 errors, 10 warnings)`. eslint.log: exit 0 on the two files. typecheck.log: exit 0.
    e2e-all.log: `188 passed (3.0m)` at 3 workers (186 + 2).
    ctl/summary.txt: BASE 35 passed; S4 `expected 8, unexpected 1` (:46 three autocompletes); R1 `expected 8,
    unexpected 1` (:66 fetch(request, init)); S4X and R1X each 34 and 1, the same case. BASE-port-in-use.log
    is a first BASE run whose preview server did not start (port in use for a moment); the rerun passed.
    core-controls.log: 824d0c0 NOT EQUAL; 85e9921 ALL EQUAL; 85e9921 merged with origin/main ALL EQUAL;
    reworded comments and rewrapped code and README ALL EQUAL; [0, 1] for [0, 1, 2], '3 requests' for
    '4 requests' and '1200' for '1,200' each NOT EQUAL.
