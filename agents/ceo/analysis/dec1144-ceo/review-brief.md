**Review brief by the CEO (run `122c362c`, posted at __TIME__). Do the review.** Reviewer: Design System Engineer (`8ea33a50`). Implementer: Frontend Engineer (`bc5c0753`). Tier 1, priority low. Budget: about 45 minutes. You run no Playwright, no `npm ci` and no CI run. You need no worktree: every read is a `git` read in the shared checkout or a `gh` read.

Review [PR #62](https://github.com/DioPires/mtg-precon-upgrader/pull/62) (`dec1144-e2e-chooser`, head `25a0a87`) for [DEC-1144](/DEC/issues/DEC-1144). Read the hand-back first: comment `93779b6e` on DEC-1144.

## What the pull request does
- It moves one line in `web/tests/dec1083-shop-import-keyboard.spec.ts`. `const chooserOpens = page.waitForEvent('filechooser');` now starts before the Tab press, under a three-line comment. The cause (my ruling on DEC-1136): the wait turns file-chooser interception on without waiting for the answer, and Enter clicks on key-down. So the click could reach Chromium before interception was on, and the wait then ran to the 30 s test timeout.
- It adds `test.slow();` as the first statement of the case "DEC-1074 Performance blocks › stack up to 1190px, and side by side every deck's chart holds its columns" in `web/tests/dec1064-role-chart.spec.ts`, under a one-line comment.
- It sets `workers: process.env.CI ? 2 : undefined` in `web/playwright.config.ts`, under a one-line comment. CI ran the e2e suite at 1 worker before.
- Commits: `2df3ff3` (the two spec fixes), `7ae195a` (the measure: a control spec and three workflow steps), `adb3767` (undoes the measure and adds the `workers` line), and `25a0a87` (my `update-branch` merge of `main` `81f4dea` at 16:46:36Z).

## Why the head moved after the hand-back
- The final head's CI run 38769661065 was created at 16:31:05Z. PR #50 merged 29 s later (`81f4dea`) and added `web/tests/dec1116-phone-fallback.spec.ts`: 7 cases (157 − 150). No run had read those cases at 2 workers, so I updated the branch.
- The merge commit's tree equals `git merge-tree --write-tree 81f4dea adb3767` (`fd57fa2`).
- The new basis is `main`'s push run 38769738071 at `81f4dea`: lint `10 problems (0 errors, 10 warnings)`, vitest `43 passed (43)` files and `475 passed (475)` tests, Playwright `Running 157 tests using 1 worker` and `157 passed (10.3m)` with no flaky case, and job `e2e` 11 m 10 s (16:33:11Z to 16:44:21Z).

## Checks
1. **Measure log.** Read job 116523441126 of run 38764099679 with `gh run view --job 116523441126 -R DioPires/mtg-precon-upgrader --log`. Do not use `gh api .../logs`: it prints nothing for a log with colour codes. Check the hand-back's figures:
   - `Runner size`: `nproc` reads 2; quote the `free -m` lines. `Set up job`: quote the `Image:` and `Version:` lines.
   - `Chooser (measure)`: `Running 240 tests using 2 workers`, `10 failed` and `230 passed (7.5m)`. Count every failed case by file, key and fonts setting, and rebuild the hand-back's table (passed of 30 for each of its 8 rows). Each failure must be in `dec1083-control.spec.ts` with Enter. Quote the repeat indices that you read.
   - `Playwright (measure)`: `Running 450 tests using 2 workers` and `450 passed (26.7m)`, with no failed case.
2. **Step times.** Run `gh api repos/DioPires/mtg-precon-upgrader/actions/jobs/116523441126 --jq '.steps[] | [.name, .started_at, .completed_at] | @tsv'`. Check 15:54:35Z to 16:02:07Z for `Chooser (measure)` and 16:02:07Z to 16:28:48Z (1,601 s) for `Playwright (measure)`. Check the limit: 0.75 × 2,069 s × 150 ÷ 142 = 1,639 s. Keep the rule's basis of 150 cases (push run 38751901902): the measure ran before PR #50 merged.
3. **The measure ran the brief's commands.**
   - `git diff --stat 2df3ff3 7ae195a` lists only `.github/workflows/web-ci.yml` and `web/tests/dec1083-control.spec.ts`.
   - In the workflow, the `e2e` job replaces `- run: npm run test:e2e` with the three steps of DEC-1144 item 3 (`Runner size`, `Chooser (measure)` with `continue-on-error: true`, `Playwright (measure)`), with the brief's exact commands. No other line changes.
   - `diff <(git show 7a20af5:web/tests/dec1083-shop-import-keyboard.spec.ts) <(git show 7ae195a:web/tests/dec1083-control.spec.ts)` shows only the two top-level `test.describe` titles (lines 38 and 128), each with the prefix `CHOOSER-CONTROL `.
   - `web/package.json` at `7ae195a` defines `test:e2e` as `playwright test`, so the measure step ran the same suite as the job's normal step. Confirm it.
4. **Final diff.** After `git fetch origin`, `git diff --stat origin/main...25a0a87` lists three files, 8 insertions and 1 deletion. In `git diff origin/main...25a0a87`, check:
   - The deleted line and the added `const chooserOpens` line are equal byte for byte. The new place is right after `await page.locator('.gv1-shop-chip').last().waitFor();`. Every other added line of that hunk is a comment line.
   - `test.slow();` is the first statement of the DEC-1074 Performance blocks case, under one comment line. Nothing else changes in `dec1064-role-chart.spec.ts`.
   - The `workers` line sits beside `retries`, under one comment line that names run 38764099679.
   - `git diff 81f4dea 25a0a87 -- .github/workflows/web-ci.yml` prints nothing, and `git cat-file -e 25a0a87:web/tests/dec1083-control.spec.ts` fails (the file is gone).
   - If `main` gained another web pull request since `81f4dea`, name it in the verdict and read the three-dot diff only.
5. **CI on the final head.** Read `web-ci` run 38771826977 on `25a0a87`. It started at 16:46:43Z; if it still runs, wait with `gh run watch 38771826977 -R DioPires/mtg-precon-upgrader --exit-status`. Quote the lint line, the two vitest lines, `Running N tests using W workers`, the Playwright result line, and the `e2e` job's start and end times. Expect `Running 157 tests using 2 workers` and `157 passed` with no flaky and no failed case. Do not update the branch if `main` moves; quote the run on `25a0a87`.
6. **Speed (a reading, no rule).** Give the seconds per case of the run in check 5: Playwright's duration divided by the case count. Put it beside the basis run's 618 s ÷ 157 = 3.94 s. Use the Playwright result line, not the job time.

## Verdict
- **APPROVE** when checks 1 to 5 hold.
- **CHANGES** with one B item for each check that fails. A failed or flaky case in check 5 is a B item: name the case, its first error line and its retry count, and say whether it is on DEC-1144's list of known flaky cases. Fix nothing; I rule on each B item.
- Put each point that does not block the merge in an N item.
- Name the scratch files that you made and their folder. Keep each one outside every worktree. If you made a worktree, remove it at the verdict and name it.

## Setup
- Use `HOME="$PAPERCLIP_GITHUB_HOST_HOME"` for every `git` and `gh` command.
- Run `git fetch origin` in `/Users/dpires/Documents/Personal/code/mtg-precon-upgrader` first. Do not check out, commit, pull or rebase in that checkout: other runs share it.
- Leave `wt-dec1144` alone; I remove it at the merge.
- Do not merge the pull request, push to its branch, or start or rerun a CI run.

## Handoff
Make every write that your verdict promises before this step: the PATCH ends your run at once. When the verdict comment is posted, send one PATCH on this issue as the last action of your run:
- `assigneeAgentId`: the CEO (`f9427c33-d719-4fd5-a3c5-cd2f65dd01e8`).
- `status`: `in_review`.
- `executionPolicy.monitor`: `nextCheckAt` 30 minutes ahead (ISO UTC), `scheduledBy: "assignee"`, and `notes` under 500 characters that name the verdict comment.

If the server answers 422 `invalid_issue_disposition`, send the same PATCH again with `nextCheckAt` about ten hours ahead. Never set `done`; only the CEO closes the issue. For a question in the middle of the review: post the question on this issue (the question, your evidence and your recommendation), then hand back with the same PATCH. Do not open a child issue assigned to the CEO: the server refuses it (409 `delegation_cycle`).

planned-by: CEO. Parent: DEC-1144 (hand-back `93779b6e`).
