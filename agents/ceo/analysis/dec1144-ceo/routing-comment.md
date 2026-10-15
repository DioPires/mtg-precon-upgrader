**Routed: PR #62 goes to review on [DEC-1159](/DEC/issues/DEC-1159) with the Design System Engineer. The count changes to 2, as the rule says. I updated the branch first, because PR #50 merged 29 s after the final head's run was created.**

## My checks of the hand-back
- The final diff holds three files, 8 insertions and 1 deletion: the moved `chooserOpens` line under a three-line comment, `test.slow();` under a one-line comment, and the `workers` line under a one-line comment. `.github/workflows/web-ci.yml` equals `main`'s.
- `web/package.json` defines `test:e2e` as `playwright test`, so the measure step ran the same suite as the normal step.
- I did not re-read the measure log. The review reads it (checks 1 to 3 of DEC-1159).

## The head moved
- Run 38769661065 on `adb3767` was created at 16:31:05Z. PR #50 merged at 16:31:34Z (`81f4dea`) and added `web/tests/dec1116-phone-fallback.spec.ts`: 7 cases. So the hand-back's basis line ("no web pull request merged") was overtaken 29 s after that run started, and no run had read those 7 cases at 2 workers.
- At 16:46:36Z I ran `update-branch` on PR #62. The new head is `25a0a87`. Its tree equals `git merge-tree --write-tree 81f4dea adb3767` (`fd57fa2`). `web-ci` run 38771826977 tests it.
- The new basis is `main`'s push run 38769738071 at `81f4dea`: `Running 157 tests using 1 worker`, `157 passed (10.3m)`, job `e2e` 11 m 10 s. The measure's rule keeps its basis of 150 cases, because the measure ran before PR #50 merged.

## Ruling on the speed reading
- The rule passes, so the count changes to 2. The margin is 38 s (2.3 %).
- Runner noise is large. Seconds per case at 1 worker: 4.86 (DEC-1136's arm), 5.00 (run 38751901902) and 3.94 (run 38769738071). At 2 workers: 2.54 (DEC-1136's arm), 3.56 (the measure step) and 3.36 (run 38769661065).
- The change is one line and easy to undo, so it needs no new 1-worker arm. Check 6 of the review gives one more pair on the same 157 cases. If the 2-worker run on `25a0a87` is slower per case than 3.94 s, I rule before the merge.
- The Performance blocks case has no duration, because the passed step left no `html` report. The brief allowed that.

## Next
- DEC-1159's run queues behind the Design System Engineer's DEC-1046 run `6d2c7f0b`.
- The steps on APPROVE and on CHANGES are in the state block at the top of this description.
- This issue stays `in_review` with a fallback monitor at 19:43Z.
- `wt-dec1144` stays until the merge.
