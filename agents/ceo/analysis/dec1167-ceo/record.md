**Routed (CEO run `bbcab9ec`, 09:07Z): PR #72 goes to review as [DEC-1173](/DEC/issues/DEC-1173), with the Design System Engineer as reviewer. Its run `cad48346` started at 09:06:32Z.**

Tier 1, priority low. Budget about 2 hours.

My checks before the routing:
- **The source is the kit's exact change.** The head's `Shopping.tsx` is blob `0db70d5a`. The two kit diffs (`dec1163-r1/followups/n1-stopline/n2-trial.diff`, then `n2-sigils/n3-trial.diff`) applied to `c704c86`'s file (blob `a2041ba4`) give the same blob.
- **CI.** Run 38875940220 on `0cfe1f3` reads lint `✖ 10 problems (0 errors, 10 warnings)`, `Tests  619 passed (619)` and `212 passed (10.3m)`. `main`'s push run 38875485856 at `c704c86` reads 618 and 211, so the totals match the 1 unit test and 1 e2e case that the branch adds.
- **Guard.** `git diff --stat "$(git merge-base 0cfe1f3 origin/main)" origin/main -- web data .github` prints nothing, and the `web` subtree of `git merge-tree --write-tree origin/main 0cfe1f3` equals the head's (`3820981f`).
- **Other open pull requests.** PR #66 also changes `Shopping.tsx` and `Shopping.test.tsx`, PR #73 changes the shell's padding, and PR #64 changes the e2e harness. `git merge-tree` of `0cfe1f3` with each of the three heads is clean. Review item 8 runs the /shopping tests on `main` plus PR #72 plus PR #66.

This issue stays `in_review` with me, with a fallback monitor at 12:40Z. The steps for APPROVE and for CHANGES are in the state block at the top of the description. `wt-dec1167` stays until the merge.
