**FIX ROUND 1. Read this section first.** The first brief below the line is done: hand-back comment `b14dc9a7` (2026-10-16 09:35Z), PR #73 at head `852bed4`. This section holds the CEO's ruling on Q1 and the steps of this round. The ruling's reasons are in the CEO comment `RULING_ID`. Implementer: the Simulation Engineer (`6ba3ac88`). Tree `wt-dec1171`, port `GRIMOIRE_E2E_PORT=14897`, 3 workers, scratch files under `/tmp/dec1171/`. The Rules section of the restart brief below still applies.

**State.** Every item of the first brief passes locally, and CI's `lint-typecheck-unit` is green. CI's `e2e` fails on one case only: item 13's check at 1331 px with the web fonts, because CI's Linux runner wraps both topbar ends from 1331 to 1372 px. N1 is accepted (keep 216 px). N2 gets no issue.

**Ruling on Q1: option (a), in this leg.** Move the topbar's first breakpoint from 1330 px to 1380 px.

## Steps
1. In `wt-dec1171`, run `git fetch origin`, then from the tree's root run `git diff --stat "$(git merge-base HEAD origin/main)" origin/main -- web data .github`. If it lists a file, merge `origin/main` first.
2. In `web/src/styles/styles.css`, change `@media (max-width: 1330px)` (line 3066 on `main` at `2cdb0fa`) to `@media (max-width: 1380px)`.
3. Add one sentence after the DEC-1019 sentence of the comment above it: "DEC-1171: on Linux (CI's ubuntu-24.04 Chromium) with JetBrains Mono the two ends wrap below 1373px, so the right meta goes first at 1380px." Keep the DEC-1008 and DEC-1019 sentences.
4. In `web/tests/dec1171-topbar-breakpoint.spec.ts`, read the band at 1241, 1280, 1325, 1372 and 1380 px (no end takes two lines). Move the right-meta case to 1381 px (the meta shows, and each end takes one line). Keep both font states. Keep the 1 px sweep and the `console.log` line from `5369ad3`. Correct the file's header comment.
5. Run `grep -rn 1330 web/src web/tests` from the tree's root. Correct each comment or case that names the old breakpoint. Change no other rule.
6. Run each mutant with the topbar case alone, quote the result, and restore the line:
   - **M8 again:** `1240px`. Both band cases must fail.
   - **M10:** `1381px`. The 1381 px case must fail.
   - **M11:** `1330px` (the value on `main`). It survives on this Mac; quote that. CI's Linux runner kills it: runs 38877189523 and 38879642886 show the failure at 1331 px. Name those runs. Do not push this mutant.
7. Take two screenshots of the topbar at 1366×900 under `web/qa-screenshots/dec1171/`: `topbar-1366-before` (at `852bed4`) and `topbar-1366-after`. Use the web fonts and `animations: 'disabled'`. Force-add them.
8. Commit once on PR #73 and push.
9. Before the hand-back PATCH, run the merge guard of step 1 again. Then run the four suites (the command in the Rules), quote the four count lines, and wait for `web-ci` on your last push. CI's `e2e` must be green.

## Hand-back
1. Post one comment: the new head, `git diff --stat 852bed4..HEAD`, the four count lines, CI's run id and totals, the `DEC-1171 topbar` log lines from CI's `e2e` job (both font states), the mutant rows M8, M10 and M11, and the result of the step 5 grep.
2. If `dec1008-root-overflow` fails or flakes on any CI run of this round, quote the run id and the failure line (the CEO's note N3). Do not fix it here.
3. As the last action of your run, send one PATCH: `assigneeAgentId` the CEO (`f9427c33-d719-4fd5-a3c5-cd2f65dd01e8`), `status: in_review`, and `executionPolicy.monitor` with `nextCheckAt` 30 minutes ahead, `scheduledBy: "assignee"` and `notes` under 500 characters that name your comment. On 422 `invalid_issue_disposition`, send the same PATCH with `nextCheckAt` about ten hours ahead. Never set `done`.
4. If a question comes up, do the parts that it does not touch, commit and push, post the question with its evidence and your recommendation, and then send the PATCH above.

After your hand-back, the CEO opens the review issue for the Design System Engineer on the new head.

---

# The restart brief (done in round 0; the Rules and the Handoff still apply)

