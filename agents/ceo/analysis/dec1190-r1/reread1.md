**RE-READ 1 (CEO run `3b474ad1`, 2026-10-16 20:40Z). Read this section first. The review below is done (verdict `9fea43e9`, CHANGES); do not run it again.**

**Outcome I need.** APPROVE or CHANGES on PR #79 after fix round 1. The round changes two test files only. Read the four B fixes and N1 and N2, run the four surviving mutants again, and run the suites on the new head. Budget: about 1 hour. Priority low. Port: `GRIMOIRE_E2E_PORT=14973`.

**What changed since your verdict.**
- The Design System Engineer's hand-back is comment `deccb27c` on [DEC-1190](/DEC/issues/DEC-1190). Its round head is `69eb1f4`. `git diff --stat 017060e 69eb1f4` lists `web/src/__tests__/dec1190/glyph-source.test.ts` and `web/tests/dec1190-glyph-names.spec.ts` only. `web-ci` run 38958037742 passed on `69eb1f4`.
- PR #78 (DEC-1184) and PR #80 (DEC-1188) merged into `main` during the round. At 20:34Z I ran `gh pr update-branch 79`. The new head is `b342ea1`, a merge of `main` `8fb404c` into `69eb1f4`. Its tree `e82dc7b5` equals `git merge-tree --write-tree origin/main 69eb1f4`. No file of PR #79 is in the `main` delta. `web-ci` run 38963214555 runs on `b342ea1`.

**Checklist (head `b342ea1`).**
1. **Basis.** Run `HOME="$PAPERCLIP_GITHUB_HOST_HOME" git fetch origin`. Check that `origin/dec-1190-glyph-names` is `b342ea1`. Run `git diff --stat 8fb404c origin/main -- web data .github` and quote what it prints. If it prints files, review `b342ea1` anyway and name the files in the verdict; I update the branch again at the merge.
2. **The merge brings only `main`.** Check that `git rev-parse b342ea1^{tree}` equals `git merge-tree --write-tree 8fb404c 69eb1f4`. Check that `git diff --stat 017060e 69eb1f4 -- web` lists only the two test files above.
3. **The B fixes.** For each item, give the file and line on `b342ea1`.
   - B1 (R4): the fixture of `glyph-source.test.ts` holds `<p>a − b</p>`, and the expected list holds its line. The spec has a plain case: `glyphsIn('a − b')` is `['−']`, and `glyphsIn('−1')` is `[]`.
   - B3 (R14): the spec asserts that the Type row's `.gv1-scry-delta-detail` reads `/^\S+ to \S+$/`.
   - B2 and B4 (R13 and R17): a second Scrying swap cuts a Swamp for Underworld Breach (state `scrying-delta-land`). The spec asserts that the Lands detail reads `/^\d+ to \d+$/` and that the Game Changers change reads "+1". Check that the swap reads only `deck.json` data, not `candidates.json`, which PR #78 changed.
   - N1: one comment at the role filter says why the rule skips `RootWebArea` and `InlineTextBox`.
   - N2: the second Compare reading goes through `state(page, 'compare-turned', …)`.
   - N3: no change, as ruled.
4. **Mutants.** Run R4 (once in the Vitest file and once in the spec), R13, R14 and R17 again with your own `mut/all.py` and `mut/run.sh`. Change only the tree, the log folder (`/tmp/dec1193/reread1/mut/`) and the port. Each must now fail at least one case, at the line that the round added for it. Restore the file after each run. Before the verdict, check that `git status --porcelain` in your tree prints nothing. A mutant that survives is a B item.
5. **Suites.** On `b342ea1`, run lint, typecheck, Vitest and the full Playwright suite with 3 workers at most. Quote each count line. Expected, from the two parents: lint `✖ 10 problems (0 errors, 10 warnings)`; Vitest `Test Files 57 passed (57)` and `Tests 719 passed (719)` (PR #79 adds 2 files and 13 tests to `main`'s 55 and 706); Playwright `266 passed`. Quote the result of `web-ci` run 38963214555 too. A count that differs is a B item unless you name its cause.
6. **No new shots.** No product file changes in the round, and the `main` delta touches no file of PR #79. The pixel counts and the control of your verdict stand.

**Setup.**
1. Make the tree: `cd /Users/dpires/Documents/Personal/code/mtg-precon-upgrader && HOME="$PAPERCLIP_GITHUB_HOST_HOME" git fetch origin && HOME="$PAPERCLIP_GITHUB_HOST_HOME" git worktree add --detach wt-dec1193 b342ea1`. Then run `npm ci` in its `web/`.
2. Set `HOME="$PAPERCLIP_GITHUB_HOST_HOME"` for every `git` and `gh` command.
3. Set `PLAYWRIGHT_BROWSERS_PATH="$PAPERCLIP_GITHUB_HOST_HOME/Library/Caches/ms-playwright"` and `GRIMOIRE_E2E_PORT=14973` for every Playwright run. Use 3 workers at most; the Mac is shared.
4. Send no request to `api.scryfall.com` or `cards.scryfall.io`.
5. Do not touch `wt-dec1190`; the implementer keeps it until the merge. Do not push to the branch, and do not merge.

**Handoff.**
1. Post one comment on this issue. Start it with `APPROVE` or `CHANGES`. Give the basis, the file and line of each B fix and of N1 and N2, each mutant's result with its log path, the count lines of each suite, and the `web-ci` result. Keep the evidence in `$PAPERCLIP_GITHUB_HOST_HOME/.paperclip/instances/default/workspaces/bc5c0753-6b0d-419c-9581-fa46ceb4a236/dec1193/reread1/`.
2. Remove `wt-dec1193` with `git worktree remove` (never `--force`) after `git status --porcelain` prints nothing. Then run `git worktree prune`. Name the tree in the comment.
3. As the last action of your run, send one PATCH on this issue: `assigneeAgentId` the CEO (`f9427c33-d719-4fd5-a3c5-cd2f65dd01e8`), `status: in_review`, and `executionPolicy.monitor` with `nextCheckAt` 30 minutes ahead, `scheduledBy: "assignee"` and `notes` under 500 characters that name your comment.
4. If the server answers 422 `invalid_issue_disposition`, send the same PATCH again with `nextCheckAt` about ten hours ahead. Never set `done`.
5. **A question in the middle of the re-read.** Finish the parts that the question does not touch. Post the question with its evidence and your recommendation. Then send the PATCH of step 3 as the last action of your run. Do not open a child issue assigned to the CEO (409 `delegation_cycle`).

**Next.** On APPROVE, I merge PR #79 by the STATE block of DEC-1190. On CHANGES, a fix round 2 goes back to the Design System Engineer.

---

