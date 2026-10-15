**FIX ROUND 2 (CEO run `2c326a6c`, 2026-10-15 07:21Z). Read this section first. The STATE block, FIX ROUND 1 and the briefs below the line are done; they stay for reference.**

**For a CEO run that this issue's hand-back starts:** go to the last heading of this section, "CEO: checks at the hand-back". **For a CEO run that DEC-1103's monitor starts while this issue is with the Frontend Engineer:** read this issue's runs, re-park DEC-1103 with a monitor four hours ahead, and end.

Fix round 2 of PR [#34](https://github.com/DioPires/mtg-precon-upgrader/pull/34). The delta re-read on [DEC-1103](/DEC/issues/DEC-1103) read CHANGES with one B item, B8 (verdict `b7d52830`). My ruling is comment `aeec83f3` on DEC-1103. Implementer: you, the Frontend Engineer (`bc5c0753`). Tier 1, priority low. Budget: about 45 minutes; about 90 minutes if `main` holds PR #38 (step 3).

**When to start.** At 07:16Z your DEC-1077 run was live, and DEC-1118 and DEC-1032 were queued. This leg queues behind them.

## The ruling
- **B8.** No case holds that a spec's own `route.abort()` on a Moxfield URL passes the check. The reviewer's mutant X3 makes the Moxfield line of `judge` (`web/tests/support/test.ts:119`) name every `net::` failure: `else if (outcome === NETWORK_ANSWERED || outcome.startsWith('net::')) moxfield.push(line);`. X3 passed the unit file, the new spec and `combo-lab.spec.ts`. The reviewer wrote a fourth case for `web/tests/dec1071-moxfield-check.spec.ts` and ran it: the case passes on the head and fails on X3 in both font modes.
- **Route A.** Copy the reviewer's file from the kit. Do not retype it, and do not copy it from a comment: the file's `localProxy` line holds two backslash escapes, and the server turns them into line breaks. You may reword a comment; do not change code.
- **N1.** In `web/README.md`, the sentence "Do not give them a Scryfall URL." becomes "Do not give them a Scryfall or a Moxfield URL." You may rewrap the lines.
- Change nothing else. The B1 lines, B2 to B7 and the rest of the README stay as they are at `2ce4f20`.

## Kit
`$PAPERCLIP_GITHUB_HOST_HOME/.paperclip/instances/default/workspaces/bc5c0753-6b0d-419c-9581-fa46ceb4a236/dec1071-fix2-kit/` (16 files). The same files are in the repository under `agents/ceo/analysis/dec1071-r2/`.
- `expected/`: the five test files of the route. `expected/web/tests/dec1071-moxfield-check.spec.ts` is the reviewer's run file (blob `7dd4e117`): the head's file (`f68d7e80`) plus the B8 case. The other four files are round 1's.
- `core.py`: my compare. Run `python3 -I <kit>/core.py <tree> HEAD`. Expected last line: `ALL EQUAL`. It also checks the two B1 lines and the N1 sentence, and it prints the spec's blob.
- `reviewer/`: `kill.diff`, the X3 diff (`K-X3.diff`), the head and X3 logs (`K-head.log`, `K-X3.log`), the typecheck and eslint logs, and the reviewer's `run-mutant.sh` and `logger.py`. The script names `/tmp/dec1071-delta2/`, the tree `wt-dec1071-delta2` and port 14625: change all three before you run it.
- `ruling.md` and `fix-brief.md`: copies of the ruling and of this section.

## Steps
1. Run `cd /Users/dpires/Documents/Personal/code/mtg-precon-upgrader/wt-dec1071` and `git fetch origin`. Check that `git status --porcelain` prints nothing and that `git rev-parse --short HEAD` prints `2ce4f20`.
2. Run `gh pr view 38 --repo DioPires/mtg-precon-upgrader --json state,mergedAt,mergeCommit`. Its re-read ([DEC-1110](/DEC/issues/DEC-1110)) was live at 07:16Z.
3. Run `git merge origin/main`.
   - **`main` without PR #38:** expect no conflict. At 07:16Z `main` (`b19ef4b`) held PR #42 (`ef62968`). PR #42 changed 4 files under `web`, and none of them is one of this pull request's 10 files.
   - **`main` with PR #38:** `web/tests/support/test.ts` and `web/README.md` conflict. Resolve them by item 12 of the reviewer's verdict `fe36545b` on DEC-1110:
     - Keep both imports: `isMoxfieldHost` and `cardMetadataWithoutPrices`.
     - Keep PR #38's bucket 1 block and its `const url = new URL(...)`, without its local `pageGone`: this pull request moved `pageGone` into `stub()`.
     - Keep one `failures` list with this pull request's `requests()` helper, the unanswered Scryfall entry, the Moxfield entry and PR #38's rate-check entry, and one throw.
     - Keep both B1 lines as they are.
     - In the README, keep PR #38's paragraphs (what `'seeded'` means now, `'none'`, the rate check, the 429 option) and this pull request's Moxfield, DNS and seeded-read text.
     - Name each conflict hunk and its resolution in the hand-back.
     - PR #38 moves the /shopping prices to `data/card-metadata.json`, so a B5 or B6 line can read differently. Report such a reading and its cause, and do not loosen a line. Do not run the reviewer's m11 or m12.
4. Copy `expected/web/tests/dec1071-moxfield-check.spec.ts` from the kit into `web/tests/`. Make the N1 change in `web/README.md`.
5. Run `core.py`. Expected: `ALL EQUAL`, and blob `7dd4e117` if you reworded no comment.
6. In `web/`, run `npm run typecheck`, `npx eslint tests/dec1071-moxfield-check.spec.ts` and `GRIMOIRE_E2E_PORT=14611 npx playwright test tests/dec1071-moxfield-check.spec.ts`. Expected: typecheck exits 0, eslint prints nothing, and the spec reads `8 passed`: four cases, each with the fonts live and blocked. Six of the eight are expected failures from `test.fail`.
   - With PR #38 on `main`, also run the acceptance: `npm run lint && npm run typecheck && npm test -- --run && GRIMOIRE_E2E_PORT=14611 npm run test:e2e`. Expected: the totals of `main`'s push run on the merge of PR #38, plus 1 file, 3 tests and 8 cases.
7. Run X3 once, in an export of your committed tree under `/tmp/dec1071/fix2/` with `GRIMOIRE_E2E_PORT=14612`, never in `wt-dec1071`. Change the Moxfield line of `judge` in `tests/support/test.ts` to the X3 form above, and run the new spec.
   - Expected: `2 failed`, `6 passed`. Both failures are the B8 case, one for each font mode. Each reads `Error: 1 request to a Moxfield host got no answer from a route of the spec:` and then `GET https://api2.moxfield.com/v3/decks/all/dec1071 (net::ERR_FAILED)`.
   - X3 needs no proxy and no logger. The spec's route aborts the request before Chromium sends it, and the DNS block still holds every Moxfield name.
   - With PR #38 on `main`, also run F1 in the same export: the Moxfield line goes back to `else if (outcome === NETWORK_ANSWERED) moxfield.push(line);`. Run the new spec. Expected: `2 failed`, each "Expected to fail, but passed" (the B1 case, one for each font mode).
   - Save each log under `/tmp/dec1071/fix2/`.
8. Commit the round on top of the merge, and push once. `web-ci` must read success on both jobs.
   - Expected without PR #38: lint 0 errors and 10 warnings; vitest 37 files and 402 tests; Playwright 125 cases. This is the arithmetic of PR #42's run 38651024519 on `adc697f` (36 files, 399 tests, 117 cases) plus this pull request's 1 file, 3 tests and 8 cases.
   - Expected with PR #38: `main`'s push run on the merge of PR #38, plus 1 file, 3 tests and 8 cases.
9. Before the hand-back PATCH, run `git diff --stat "$(git merge-base HEAD origin/main)" origin/main -- web data scripts .github`. If it prints a file, merge `origin/main` again (step 3 holds, also for a PR #38 that merged after your push), push, wait for CI, and run `core.py` again.

## Rules
The Rules section of the first brief still holds. Use `HOME="$PAPERCLIP_GITHUB_HOST_HOME"` for every `git` and `gh` command, and `PLAYWRIGHT_BROWSERS_PATH="$PAPERCLIP_GITHUB_HOST_HOME/Library/Caches/ms-playwright"` for every Playwright run. Ports: 14611 for `wt-dec1071` and 14612 for the export. Keep scratch outside the tree. Do not touch another agent's tree or server. Send no request to a Scryfall host or a Moxfield host, also not on a mutant. Leave `wt-dec1071` in place at the hand-back, and remove the export.

## Hand-back
Post one comment on this issue. Lead with the outcome and the head.
- The head, its commits and the merge of `main`: the merged `main` commit and, with PR #38, each conflict hunk and its resolution.
- `core.py`'s output, every line.
- Step 6: the typecheck, eslint and spec lines. With PR #38: the acceptance totals and any B5 or B6 reading.
- X3, and F1 with PR #38: the diff, the log's path, the count line and the error lines.
- CI on the head: both jobs, with the lint, vitest and Playwright totals.
- The guard of step 9, and the export that you removed.

## Handoff
Make every write that your hand-back promises before this step: the PATCH ends your run at once. When the comment is posted, send one PATCH on this issue as the last action of your run:
- `assigneeAgentId`: the CEO (`f9427c33-d719-4fd5-a3c5-cd2f65dd01e8`).
- `status`: `in_review`.
- `executionPolicy.monitor`: `nextCheckAt` 30 minutes ahead, `scheduledBy: "assignee"`, and `notes` under 500 characters that name the hand-back comment.

If the server answers 422 `invalid_issue_disposition`, send the same PATCH again with `nextCheckAt` about ten hours ahead. Never set `done`; only the CEO closes the issue (DEC-970). For a question in the middle of the round: finish the parts that the question does not touch, commit and push, post the question on this issue (question, evidence, readings, your recommendation), and hand back with the same PATCH. Do not open a child issue assigned to the CEO: the server refuses it (409 `delegation_cycle`).

## CEO: checks at the hand-back
1. First write: park this issue `in_review` with a monitor 60 minutes ahead, or clear the hand-back's spare monitor in the routing PATCH. Also re-park DEC-1103 or clear its fallback monitor.
2. Run `python3 -I agents/ceo/analysis/dec1071-r2/core.py <repo> origin/dec-1071-e2e-suite`. Expected: `ALL EQUAL`.
3. Read CI on the head: both jobs success, with the totals of step 8.
4. Read the X3 log, and the F1 log with PR #38, against step 7.
5. Read what the round changed besides `main`. `git diff --name-only <the round's merge of main> origin/dec-1071-e2e-suite` lists only the spec and `web/README.md`. Without PR #38, `git show --remerge-diff --format=%h <that merge>` prints only the id (no hand edit), and `test.ts` keeps blob `e81c789b`.
6. **Head without PR #38:** merge by step 3 of "CEO: at the delta verdict" in the STATE block below (a, d, e, g, h), with steps a to i of the first state block. Route A needs no re-read. In step e, expect `main`'s totals plus 1 file, 3 tests and 8 cases. Close DEC-1103 with this issue.
7. **Head with PR #38:** write "CONFLICT RE-READ, ROUND 3. Read this section first" at the top of DEC-1103's description, and assign DEC-1103 to the Design System Engineer (`todo`, `monitor: null`). Its scope: the merge commit's resolution of `test.ts` and the README against item 12 of `fe36545b`, `core.py`, F1 and X3 on the merged tree, and the acceptance totals. Give it the tree `wt-dec1071-delta3` and ports 14627 to 14629. On its APPROVE, merge as in check 6.
8. **Owed start DEC-1118:** it is `todo` already, and its run was queued at 07:06Z (a status change). The merge run does not start it again. Read whether it ran, and drop this step.
9. **Two-round rule:** a third CHANGES, or a check above that fails, goes to the board as a card (ruling on DEC-1103).
