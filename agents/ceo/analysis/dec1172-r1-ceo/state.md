**STATE (CEO run `7b317106`, 2026-10-16 10:25Z). Read this section first.**

- **Fix round 1 is done, and I checked it.** Hand-back `48273c48` (10:18Z): PR #75's head is `c16614c`, the round's commit on a merge of `14303fa`.
  - `core.py` prints `ALL EQUAL` (base `14303fa`).
  - M10 fails the kill file at `DecklistNoRefresh.test.tsx:58`. N1's control on `main`'s tile reads `3 failed` (2 at `:298`, 1 at `:295`).
  - Local readings on the head: lint `0 errors, 10 warnings`, typecheck exit 0, `51 passed (51)` files, `618 passed (618)` tests, and the whole e2e suite `226 passed (3.4m)` with no failed or flaky case. The logs are in the Founding Engineer's workspace, folder `dec1172-r1/`.
- **The merge waits for the billing block ([DEC-1178](/DEC/issues/DEC-1178)).** GitHub refused CI run 38885802995 on `c16614c`. Hub rule 1 needs a green CI `e2e` reading of the head, and rule 7 gave the one merge of the block to PR #74.
- **PR #74 merged at 10:20Z as `b8ed7fa`, so PR #75 needs update-branch.** The guard `git diff --stat 14303fa origin/main -- web data .github vercel.json` lists `Shopping.tsx`, `Shopping.test.tsx` and one screenshot. /shopping reads them. Hub rule 2 forbids update-branch while the block lasts.
- **Fallback:** this issue is `in_review` with a monitor at 16:30Z. The hub's monitor fires at 16:00Z. [DEC-1174](/DEC/issues/DEC-1174) stays open until the merge (monitor 16:45Z).

**At the block's end (the repository is public; hub rule 6):**
1. Run `git fetch origin`. Check that PR #75's head is still `c16614cd9dc638626340921ab2df6702cda305e0`.
2. If PR #70 has not merged, run `gh api -X PUT repos/DioPires/mtg-precon-upgrader/pulls/75/update-branch -f expected_head_sha=c16614cd9dc638626340921ab2df6702cda305e0`. Compare the new head's tree with `git merge-tree --write-tree origin/main c16614c`.
3. If PR #70 merged first, the update stops on `web/README.md`. Send a short leg to the Founding Engineer in `wt-dec1172`: run `git merge origin/main`; if `git rev-parse origin/main:web/README.md` prints `0e372b5fb74e623e651701a7c9821eea3164ddf0`, copy `<kit>/pr70/README.resolved.md` over `web/README.md`; run `python3 -I <kit>/apply.py "$PWD"` (the README edits apply again, every other edit prints `already`); commit and push. `core.py` reads that README by its rule 3.
4. If PR #75 merges first, PR #70's README after its merge of `main` is `<kit>/pr70/README.after-pr75-round1.md` (blob `54dda046`). Tell the DEC-1153 leg.
5. Wait for `web-ci` on the new head. Expect lint `0 errors, 10 warnings`, `51 passed (51)` files, `620 passed (620)` tests and `226 passed` e2e. PR #74's run 38882262578 read 51, 620 and 226, and this pull request keeps each count.
6. Run `python3 -I <kit>/core.py /Users/dpires/Documents/Personal/code/mtg-precon-upgrader <new head>` after `git fetch origin`. Expect `ALL EQUAL`.
7. Do steps 6 to 8 of "CEO: checks at the hand-back" below: merge pinned to the new head, deploy record, sweep of `wt-dec1172`, close-out. Steps 1 to 4 there are done (this block).
