**Backlog. Nothing starts this issue yet.** The CEO sets `todo` at the close-out of [DEC-1146](/DEC/issues/DEC-1146), the Frontend Engineer's next leg, or earlier if the owner asks. At the start the CEO reads the line numbers and the totals again on `main` and names a reviewer who is not the Frontend Engineer. This brief is written against `main` `43ff9ac` (2026-10-15 17:21Z, the merge of PR #61). If you find this issue `todo` with this paragraph still at the top, the owner started it: do the work, and read the line numbers again on your tree.

This issue is DEC-1160. Put one space between the two sentences at the end of the Shopping footer. Web only. Implementer: Frontend Engineer (`bc5c0753`). Tier 1. Priority low. Budget about 30 minutes.

## The finding (DEC-1151 item 8, an N item)
- `web/src/components/organisms/Shopping.tsx:875-879` on `main` `43ff9ac` is the footer, `<p className="gv1-mono-xs gv1-dim gv1-shop-foot">`. It holds two lines of text, then the expression `{shownPricesDate ? … : …}` on a line of its own.
- JSX drops a line break that comes just before an expression. So the footer reads `… three decks each wanting Sol Ring shows 3 in the buy list.Prices are USD from Scryfall, as of …`, with no space after `list.`. The footer shows in capitals, so the page reads `… IN THE BUY LIST.PRICES ARE USD …`.
- `56babb7` (DEC-1102, 2026-10-14) made the fault. It replaced the plain text line `Prices are USD from Scryfall and load lazily; …` with the expression. Before it, JSX joined the three lines of text with spaces.
- The Frontend Engineer found it on [DEC-1142](/DEC/issues/DEC-1142) (hand-back `d8a0eb83`). The screenshot `web/qa-screenshots/dec1142/already-own-1-card-1440.png` on `main` shows it.
- Each test that reads the footer uses `toContain('Prices are USD …')`: `web/src/__tests__/components/Shopping.test.tsx:694` and `:700`, `web/tests/dec1102-card-data.spec.ts:116-118` and `web/tests/dec1131-card-batches.spec.ts:147`. So no test sees the missing space.

## CEO ruling
1. Put exactly one space between `list.` and `Prices`, in both branches of the expression (with a prices date and without one).
2. Change no other text of the footer and nothing else.

## Ask
1. Make the change of the ruling.
2. Add unit cases in `Shopping.test.tsx` that read the footer's whole `textContent` with `toBe`, not `toContain`: one with a prices date, and one without. If a unit file cannot reach the branch without a date, say why and how you checked it.
3. **Mutants.** Make one mutant for each line that you add or change, and run each on its unit file first. At least: the old text (no space); two spaces; the space in one branch only. Give a table: the mutant, the line, the count line, killed or survived, and the log's path. Add a case for each survivor, or show that it is equivalent.
4. One screenshot at 1440 px of the footer of `/shopping` under `web/qa-screenshots/dec1160/`. Take it as the first shot on a fresh page, after `document.fonts.ready`, with `animations: 'disabled'`. Keep the scratch spec and its config outside the tree, and do not commit them.

## Setup
1. `cd /Users/dpires/Documents/Personal/code/mtg-precon-upgrader`.
2. Set `export HOME="$PAPERCLIP_GITHUB_HOST_HOME"` for every `git` and `gh` command.
3. Run `git fetch origin`. Then run `git worktree add -b dec-1160-shop-foot-space wt-dec1160 origin/main`. Give the base commit in the hand-back.
4. In `wt-dec1160/web`, run `npm ci`.
5. For every e2e run, set `GRIMOIRE_E2E_PORT=14857` and `PLAYWRIGHT_BROWSERS_PATH="$PAPERCLIP_GITHUB_HOST_HOME/Library/Caches/ms-playwright"`. No other brief uses `14857`. The tree holds `web/tests/support/test.ts`, so the suite answers Scryfall from repository data. A new spec imports `test` and `expect` from `./support/test`.
6. Create the log folder `/Users/dpires/.paperclip/instances/default/workspaces/bc5c0753-6b0d-419c-9581-fa46ceb4a236/dec1160-logs/`. Keep every log there, not in the tree and not in `/tmp`.
7. Write no command line that holds the Eternities player's path in plain words. Write `MacOS/[E]ternities` in any pattern.

## Steps
1. Make the change and the cases (Ask 1 and 2), then the mutants (Ask 3) and the screenshot (Ask 4). Before each mutant, `git status --porcelain` prints nothing but your uncommitted work. Restore the file after each run.
2. In `wt-dec1160/web`, run `npx vitest run`, `npm run typecheck` (exit 0) and `npx eslint` on each changed file (0 errors). Take the expected totals from `main`'s newest `web-ci` push run (give its id) plus your new cases. On `main` `43cf161` (run 38772493401) the totals read 47 files, 565 tests and `170 passed`. PR #61 added 3 files and 21 tests.
3. Run once: `npx playwright test dec1019 dec1083 dec1102 dec1110 dec1131 dec181 dec184 dec942 smoke --workers 3`. These are the specs on `main` that open `/shopping` or read the footer. Quote the count lines. `dec1083-shop-import-keyboard.spec.ts:42` is a known flaky case (a file-chooser timeout). A flaky case counts as a pass; name it.
4. Commit, push the branch with a plain `git push` (no force) and open a pull request against `main`. Name no reviewer.
5. Watch the `web-ci` run on the head with `gh run watch <id> --exit-status`. To read the totals, strip the colour codes with `perl -pe 's/\e\[[0-9;]*m//g'`.
6. Before the hand-back PATCH, run `git fetch origin` and the guard in `wt-dec1160`: `git diff --stat "$(git merge-base HEAD origin/main)" origin/main -- web data`. If it lists a file under `web/src`, merge `origin/main`, repeat step 2, push, and watch CI again.
7. Leave `wt-dec1160` in place and clean. The CEO removes it at the merge.

## Handoff
1. Post the hand-back as a comment on this issue: the pull request link, the head, the base, `git diff --stat origin/main...HEAD`, the count lines of steps 2 and 3, the mutant table, the screenshot's path, the CI run id with both jobs' count lines and the guard's output.
2. As the last action of the run, PATCH this issue with `assigneeAgentId` = `f9427c33-d719-4fd5-a3c5-cd2f65dd01e8` (CEO), `status` = `in_review`, and `executionPolicy.monitor` = `{"nextCheckAt": "<30 minutes ahead, ISO>", "scheduledBy": "assignee", "notes": "Hand-back in comment <id>."}`, all in one PATCH. The monitor covers an assignment wake that the server skips.
3. If the PATCH answers 422 `invalid_issue_disposition`, repeat it with `nextCheckAt` about ten hours ahead and `notes` under 500 characters. Never set `done`.
4. A question in the middle of the leg takes the same path. Do the parts that the question does not touch first, commit and push. Post the question with its evidence and your recommendation, then send the same PATCH as the run's last action. Do not create a child issue for the CEO: the server refuses it with 409 `delegation_cycle`.

planned-by: CEO (run `4728985c`). Found on DEC-1142 (hand-back `d8a0eb83`); DEC-1151 item 8. Parent: [DEC-1142](/DEC/issues/DEC-1142) (PR #61, merged as `43ff9ac`).
