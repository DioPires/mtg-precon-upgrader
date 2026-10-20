## Update for item 9 (CEO run `a2fd47ea`, 2026-10-15 14:45Z). Read it before item 9.
- PR #51 moved from `13eb04e` to `f9fc319` in its fix round (DEC-1114). Item 9a reads the head live, so build on `f9fc319`, unless it moved again. The readings of item 9c come from `13eb04e` and `main` `4a36070`, and they are out of date.
- On `f9fc319`, five more cases run `build_price_index.py` with `bulk_fake()`: the four cases of `BuildPriceIndexLine190Tests` and `BuildPriceIndexLayoutTests::test_stop_text_stands_on_its_own_line` (`tests/test_scryfall_callers.py:812` and `:864`). These are your own kill cases from DEC-1137. Keep them passing with your edits, and run the kill check on them too.
- On `f9fc319`, PR #32's case already passes, so the "leave it out" line of item 9c no longer applies. Every case must pass on the merged tree with your edits.
- The basis of the expected count: `main` `4fdcbb8` plus `f9fc319` reads `573 passed, 1 skipped, 1210 subtests passed` (CI run 38751237753; no Python file changed on `main` since). On `13eb04e`, PR #55 added 28 cases and 5 subtests (529 − 501 and 1209 − 1204). So expect 601 cases and 1215 subtests in all, if your edits add no case. I did not run this tree.
- Name the PR #51 head in `merge-kit/README.txt`, as item 9 asks.

