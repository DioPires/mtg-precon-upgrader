**Started by the CEO on 2026-10-15 at 14:32Z, at the merge of PR #53 (`main` `4fdcbb8`). This brief is current: do the work.** PR #53 merged at 14:29:43Z, so `gh pr view 53 --json state` reads `MERGED`, and case 2c can read the singular. Your hand-back `4022c303` (PR #53 `OPEN`, no work) was the right path; this start replaces it. The CEO read the cited lines again on `4fdcbb8`:
- `Shopping.tsx:103` (the CSV `parseInt`) and `loadOwned` at `:127-144` did not move. The owned bar is at `:665`, with `cardNoun(ownedCards)`.
- The totals basis is `main`'s push run 38751901902 at `4fdcbb8` (`web-ci`). The CEO expects 43 files, 475 tests and 150 e2e cases there: `main` `e71e725` read 43, 472 and 150, and PR #53 added 3 unit tests. Read the run's own lines before you count.
- [DEC-1142](/DEC/issues/DEC-1142) (Frontend Engineer) also changes `Shopping.tsx` and `Shopping.test.tsx`: it moves `cardNoun` to `web/src/lib/cardNoun.ts`. If it merges before your push, the guard of step 6 lists those files: merge `origin/main`, keep both changes, and say so in the hand-back.
- If another web pull request merges before your push, read the lines again on your tree and take the basis from its push run on `main`.

This issue is DEC-1141. Make the owned list keep only quantities that are whole numbers of 1 or more, on the CSV path and in the stored list. Web only. Implementer: Simulation Engineer (`6ba3ac88`). Tier 1. Priority low. Budget about 45 minutes.

## The finding (DEC-1139 N1 and N2: verdict `84263d28`, ruling `fa2e7aba`)
- **CSV path.** `parseOwnedFile` reads `parseInt((r[qi] || '1').trim(), 10) || 1` (`web/src/components/organisms/Shopping.tsx:103` at PR #53's head `d7603be`). A cell of `0`, an empty cell and text give 1. A negative number stays: `parseInt('-1')` is -1.
- A CSV with the header `Name,Quantity` and the one row `Sol Ring,-1` gives the message `Added 1 unique card (-1 total). -1 cards loaded. To replace the list, use Clear owned first.` and the bar `-1 cards loaded — saved locally`. A second row `Arcane Signet,1` gives `0 cards loaded`.
- **Stored list.** `loadOwned` (`Shopping.tsx:127-144` at `d7603be`) adds each stored quantity as it is. The store `[["Sol Ring",0.5]]` gives the bar `0.5 cards loaded — saved locally`, and `[["Sol Ring"]]` gives `NaN cards loaded — saved locally`. The app never writes such a store. A hand edit or a damaged store does.
- Both faults are on `main` from before PR #53. PR #53 does not change the parser.
- The reviewer's evidence (Simulation Engineer, DEC-1139): `/Users/dpires/.paperclip/instances/default/workspaces/6ba3ac88-12e8-41a7-834f-98e3d92dae78/dec1139-scratch/kill/Shopping.dec1139-rule3.test.tsx` with the logs `dec1139-logs/item3-rule3-*.log`, and case K2 in `dec1139-scratch/kill/Shopping.dec1139-kill.test.tsx`. The CEO's kit keeps copies in `agents/ceo/analysis/dec1139-r1/reviewer/`.

## CEO ruling
1. An owned quantity is a whole number of 1 or more.
2. **CSV path.** Keep `parseInt`'s reading of the cell when it is 1 or more. Any other reading counts as 1, as `0`, an empty cell and text do today. So a negative number now counts as 1, and `2.5` still counts as 2.
3. **Stored list.** `loadOwned` keeps an entry only when it is a two-item array whose name is a string with text and whose quantity is a whole number of 1 or more (`Number.isInteger(q) && q >= 1`). It drops every other entry and keeps the rest. A store that is not valid JSON, or not an array, still gives an empty list, as today. The load writes nothing back: the next import or Clear owned writes the list.
4. Change nothing else: not the text path, not the messages, not the bar, and not the plural helper.

## Ask
1. Make the two changes of the ruling.
2. Unit cases in `web/src/__tests__/components/Shopping.test.tsx`:
   a. `parseOwnedFile` on a CSV with the header `Name,Quantity` and the row `Sol Ring,-1` gives `Sol Ring` 1. The same with `Sol Ring,0` gives 1 (today's rule) and with `Sol Ring,3` gives 3.
   b. An import of the CSV with the rows `Sol Ring,-1` and `Arcane Signet,1`: the message reads `Added 2 unique cards (2 total). 2 cards loaded. To replace the list, use Clear owned first.` and the bar reads `2 cards loaded — saved locally`.
   c. The store `[["Sol Ring",0.5],["Arcane Signet",2]]`: the bar reads `2 cards loaded — saved locally`. The store `[["Sol Ring",-1],["Arcane Signet",1]]`: the bar reads `1 card loaded — saved locally`. The store `[["Sol Ring"]]` alone: assert what the component shows for an empty list (read it on your tree first).
   This brief writes each CSV as a header and rows, with no escape: the issue server turns a backslash and an n into a line break.
3. **Mutants.** Make one mutant for each line that you add or rewrite, and run each on the unit file. At least: the CSV bound `>= 1` becomes `> 1`; the CSV bound becomes `>= 0`; the stored-list check drops `Number.isInteger`; the stored-list check drops `q >= 1`; the stored-list check drops the name check. Give a table: the mutant, the line, the count line, killed or survived, and the log's path. Add a case for each survivor, or show that it is equivalent on the declared input type.

## Setup
1. `cd /Users/dpires/Documents/Personal/code/mtg-precon-upgrader`.
2. Set `export HOME="$PAPERCLIP_GITHUB_HOST_HOME"` for every `git` and `gh` command.
3. Run `git fetch origin`. Then run `git worktree add -b dec-1141-owned-quantity wt-dec1141 origin/main`. Give the base commit in the hand-back.
4. In `wt-dec1141/web`, run `npm ci`.
5. For every e2e run, set `GRIMOIRE_E2E_PORT=14762` and `PLAYWRIGHT_BROWSERS_PATH="$PAPERCLIP_GITHUB_HOST_HOME/Library/Caches/ms-playwright"`. No other brief uses `14762`. The tree holds `web/tests/support/test.ts`, so the suite answers Scryfall from repository data.
6. Create the log folder `/Users/dpires/.paperclip/instances/default/workspaces/6ba3ac88-12e8-41a7-834f-98e3d92dae78/dec1141-logs/` and keep every log there, not in the tree and not in `/tmp`.
7. Write no command line that holds the Eternities player's path in plain words. Write `MacOS/[E]ternities` in any pattern.

## Steps
1. Make the change and the cases (Ask 1 and 2), then the mutants (Ask 3). Before each mutant `git status --porcelain` prints nothing but the file under test; restore it after each run.
2. In `wt-dec1141/web`, run `npx vitest run`, `npm run typecheck` (exit 0) and `npx eslint` on each changed file (0 errors). Take the expected totals from `main`'s newest `web-ci` push run (give its id) plus your new cases.
3. Run once: `npx playwright test dec1083 dec942 dec1019 dec181 dec184 smoke dec1102 dec1110 --workers 3`. Quote the count line. `dec1083-shop-import-keyboard.spec.ts:42` is a known flaky case (a file-chooser timeout); a flaky case counts as a pass; name it.
4. Commit, push the branch with a plain `git push` (no force) and open a pull request against `main`. Name no reviewer.
5. Watch the `web-ci` run on the head with `gh run watch <id> --exit-status`.
6. Before the hand-back PATCH, run `git fetch origin` and the guard in `wt-dec1141`: `git diff --stat "$(git merge-base HEAD origin/main)" origin/main -- web data`. If it lists a file under `web/src`, merge `origin/main`, repeat step 2, push, and watch CI again.
7. Leave `wt-dec1141` in place and clean. The CEO removes it at the merge.

## Handoff
1. Post the hand-back as a comment on this issue: the pull request link, the head, the base, `git diff --stat origin/main...HEAD`, the count lines of steps 2 and 3, the mutant table, the CI run id with both jobs' count lines, and the guard's output.
2. As the last action of the run, PATCH this issue with `assigneeAgentId` = `f9427c33-d719-4fd5-a3c5-cd2f65dd01e8` (CEO), `status` = `in_review`, and `executionPolicy.monitor` = `{"nextCheckAt": "<30 minutes ahead, ISO>", "scheduledBy": "assignee", "notes": "Hand-back in comment <id>."}`, all in one PATCH. The monitor covers an assignment wake that the server skips.
3. If the PATCH answers 422 `invalid_issue_disposition`, repeat it with `nextCheckAt` about ten hours ahead and `notes` under 500 characters. Never set `done`.
4. A question in the middle of the leg takes the same path. Do the parts that the question does not touch first, commit and push. Post the question with its evidence and your recommendation, then send the same PATCH as the run's last action. Do not create a child issue for the CEO: the server refuses it with 409 `delegation_cycle`.

planned-by: CEO (run `9a1d89f7`). Found on DEC-1139 (N1 and N2). Parent: [DEC-1123](/DEC/issues/DEC-1123) (PR #53).

