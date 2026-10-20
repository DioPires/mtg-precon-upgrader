**STATE (CEO run `a9b35256`, 2026-10-16 10:13Z). Read this first. Fix round 1 is done and checked; only the `e2e` reading is missing, because GitHub refuses hosted jobs in this repository (billing). Hub: [DEC-1178](/DEC/issues/DEC-1178). The board answered card `c6017844` with B; the secrets scan is DEC-1179.**

- Checks 2 and 4 of "CEO: checks at the hand-back" pass, and so does the unit half of check 3 (`Tests  657 passed (657)`, run 38884232804). Comment `5527f57c` holds the readings. Head `3c3a151`.
- **The board answered B at 10:13:03Z** (card `c6017844`): make the repository public after an engineer scans its history for secrets. The scan leg is [DEC-1179](/DEC/issues/DEC-1179) (Interactive Tools Engineer, high), under the hub DEC-1178. This issue waits until GitHub runs hosted jobs again.
- **When the block ends** (the repository is public, or a rerun starts): run `gh run rerun 38884232804 --failed`. Expect `226 passed`, or `main`'s newest `e2e` count. Then do step 5 of "CEO: checks at the hand-back" (merge by "On APPROVE" steps 3, 4 and 6).
- **If this issue's monitor fires before that:** read DEC-1178 and DEC-1179. If the repository is still private, re-park this issue `in_review` with a monitor six hours ahead. Do not rerun the job while it is private: the quota is used up.

---

**FIX ROUND 1 (CEO run `14f85cb1`, 2026-10-15 22:58Z). Read this section first. The STATE block and the first brief below the line are done; they are for the CEO.**

**For the CEO run that the hand-back starts:** go to the heading "CEO: checks at the hand-back" at the end of this section.

The review [DEC-1164](/DEC/issues/DEC-1164) read CHANGES on PR #66 at `ff7ead8` (verdict `72306f25`, ruling `e3be90ce`). Two B items stand. The fix is two unit cases that the reviewer wrote and ran. Tests only, route A: take the cases as they stand, and change no source file. Implementer: Simulation Engineer (`6ba3ac88`). Priority low. Budget about 25 minutes, plus the CI wait.

## The cases
- Kit: `/Users/dpires/Documents/Personal/code/mtg-precon-upgrader/agents/ceo/analysis/dec1164-r1/` (on `main` at `8fda930`). Read `README.txt` first.
- `case.diff` changes two unit files:
  1. **B1.** `web/src/__tests__/routes/ComboLab.test.tsx`: one more row at the end of the `it.each` table of the DEC-1150 block: `[[['Sol Ring', 2], ['Arcane Signet', 1]], '3 owned cards on file'],`. No case on the head reads a store with two kept entries. So `count = q;` and `count = Math.max(count, q);` at `ComboLab.tsx:121` pass the head's cases (R1 and R2).
  2. **B2.** `web/src/__tests__/data/ownedCards.test.ts`: a new `it` in `describe('readOwnedEntries (DEC-1150)')`, after 'reads localStorage when no storage is given'. It stores `' Sol Ring '` and expects `readOwnedEntries()` to give `[[' Sol Ring ', 1]]`. No case on the head stores a name with spaces around it. So `out.push([n.trim(), q])` at `ownedCards.ts:42` passes the head's cases (R9).
- The whole files are under `expected/` (git blobs `75d79f0b` and `603fa04d`).
- You may add or reword comment lines and wrap lines. The CEO's compare drops comments, blank lines, and whitespace outside strings. Keep the text inside each string as it stands, including the test titles. Change no other line and no source file.

## Setup
1. Run `cd /Users/dpires/Documents/Personal/code/mtg-precon-upgrader`.
2. Set `export HOME="$PAPERCLIP_GITHUB_HOST_HOME"` for every `git` and `gh` command.
3. Use the tree `wt-dec1155` (branch `dec-1155-owned-reader`). At 22:50Z it was clean at `ff7ead8`. Run `git fetch origin`.
4. Create the log folder `/Users/dpires/.paperclip/instances/default/workspaces/6ba3ac88-12e8-41a7-834f-98e3d92dae78/dec1155/fix1/`. Keep every log there, not in the tree and not in `/tmp`.
5. Run no local e2e. The round changes two unit files, and CI runs `e2e`.
6. Write no command line that holds the Eternities player's path in plain words. Write `MacOS/[E]ternities` in any pattern.

## Steps
1. Merge `origin/main` into the branch with `git merge --no-edit origin/main`. Since `724fb2e`, `main` gained PR #59 (`DeckSelector`), PR #56 (DEC-1046) and PR #65 (DEC-1154, which changes `Shopping.tsx` and `Shopping.test.tsx`). The CEO merged `main` `43844f7` with this round, and the merge was clean (tree `7b51fa00`). The merge changes neither `web/package.json` nor `web/package-lock.json`, so do not run `npm ci`. If git reports a conflict, run `git merge --abort` and hand back with the conflicted paths. The round's one push carries the merge, so CI runs once. Nobody runs `gh pr update-branch 66`.
2. From the tree's root, run `git apply /Users/dpires/Documents/Personal/code/mtg-precon-upgrader/agents/ceo/analysis/dec1164-r1/case.diff`.
3. In `wt-dec1155/web`, run the two unit files, then `npx vitest run`, `npm run typecheck`, and `npx eslint` on the two files. Save each log.
   - Expect `Tests  8 passed (8)` for `src/__tests__/routes/ComboLab.test.tsx` and `Tests  30 passed (30)` for `src/__tests__/data/ownedCards.test.ts`.
   - Expect `Test Files  51 passed (51)` and `Tests  651 passed (651)`. That is `main`'s 612 plus this pull request's 37 and the round's 2, and it is the CEO's reading on the same tree. If `main` gained another web pull request after `8fda930`, the figure is `main`'s newest `web-ci` push run plus 39.
   - Expect typecheck exit 0. Expect eslint to print nothing; the CEO's run printed nothing.
4. Commit with a message that names DEC-1164 B1 and B2 and route A. Then check that `git status --porcelain` prints nothing.
5. From the tree's root, run three control mutants with the reviewer's runner: `python3 -I /Users/dpires/Documents/Personal/code/mtg-precon-upgrader/agents/ceo/analysis/dec1164-r1/reviewer/mutate.py "$PWD/web" /Users/dpires/.paperclip/instances/default/workspaces/6ba3ac88-12e8-41a7-834f-98e3d92dae78/dec1155/fix1/mutants R1 R2 R9`. The runner applies each mutant, runs its unit file, writes the log and restores the file. Expect:
   - R1 (`ComboLab.tsx:121`, `count = q;`): `1 failed | 7 passed (8)`.
   - R2 (`ComboLab.tsx:121`, `count = Math.max(count, q);`): `1 failed | 7 passed (8)`.
   - R9 (`ownedCards.ts:42`, `out.push([n.trim(), q])`): `1 failed | 29 passed (30)`.
   - In each log the failed case is the new one, and each line ends with `clean=True`.
6. Push with a plain `git push` (no force). Watch the `web-ci` run on the new head with `gh run watch <id> --exit-status`. It takes about 10 minutes.
   - Expect lint `0 errors, 10 warnings`, 51 files, 651 tests, and `205 passed` in `e2e`. PR #65's own run (38818813698) read 612 tests and `205 passed`, and the round adds no spec.
   - A flaky case counts as a pass; name it.
   - To read the totals, strip the colour codes with `perl -pe 's/\e\[[0-9;]*m//g; s/\^\[\[[0-9;]*m//g'`.
7. Before the hand-back PATCH, run `git fetch origin` and the guard `git diff --stat "$(git merge-base HEAD origin/main)" origin/main -- web data .github`. If it lists files, do not merge again; list them in the hand-back.
8. As the last read, run the CEO's check from `wt-dec1155`: `python3 -I /Users/dpires/Documents/Personal/code/mtg-precon-upgrader/agents/ceo/analysis/dec1164-r1/core.py . HEAD`. Expect `ALL EQUAL`. Quote the output.
9. Leave `wt-dec1155` in place and clean. The CEO removes it at the merge.

## Handoff
1. Post the hand-back as a comment on this issue. Give the new head, the count lines of steps 3 and 5 with the log paths, the CI run id with both jobs' count lines, the guard's output and the output of `core.py`.
2. As the last action of the run, PATCH this issue with `assigneeAgentId` = `f9427c33-d719-4fd5-a3c5-cd2f65dd01e8` (CEO), `status` = `in_review`, and `executionPolicy.monitor` = `{"nextCheckAt": "<30 minutes ahead, ISO UTC>", "scheduledBy": "assignee", "notes": "Fix round 1 hand-back in comment <id>."}`, all in one PATCH. The monitor covers an assignment wake that the server skips.
3. If the PATCH answers 422 `invalid_issue_disposition`, repeat it with `nextCheckAt` about ten hours ahead and `notes` under 500 characters. Never set `done`.
4. A question in the middle of the leg takes the same path. First do the parts that the question does not touch, then commit and push. Post the question with its evidence and your recommendation, then send the same PATCH as the run's last action. Do not create a child issue for the CEO: the server refuses it with 409 `delegation_cycle`.

## CEO: checks at the hand-back
1. Re-park this issue `in_review` with a monitor about three hours ahead, so that the hand-back's 30-minute monitor does not start a second run.
2. Run `git fetch origin`. Then run `python3 -I agents/ceo/analysis/dec1164-r1/core.py . <new head>` from the shared checkout. Expect `ALL EQUAL`.
3. Read the CI run on the new head: lint 0 errors, 51 files, 651 tests (or `main`'s newest push run plus 39), and `205 passed` (or `main`'s newest e2e count).
4. Read the three control logs of step 5: each reads `1 failed`, and the failed case is the new one.
5. If these three hold, merge by the STATE block's "On APPROVE" steps 3, 4 and 6 below, with the new head. If the guard of step 7 listed files under `web`, `data` or `.github`, first run `gh pr update-branch 66` and wait for its CI, as in step 1 and 2 there. No delta re-read: route A. If a check fails, send the round back with the reading, or open a delta re-read with the Interactive Tools Engineer.
6. At the sweep (step 4 there), delete the remote branch by API: `delete_branch_on_merge` is off in this repository. Run `gh api -X DELETE repos/DioPires/mtg-precon-upgrader/git/refs/heads/dec-1155-owned-reader`.

---

**STATE (CEO run `f235c756`, 2026-10-15 19:1xZ). The review leg ended in CHANGES at 22:18Z; FIX ROUND 1 above is the open leg. "On APPROVE" steps 3, 4 and 6 below still hold; the last heading of FIX ROUND 1 says how to use them.** The work leg is done. Hand-back `fce645df` gives PR #66 at `ff7ead8` (base `724fb2e`, two commits), with CI run 38789104392 green: 10 warnings, 51 files, 636 tests (599 + 37), `170 passed (8.0m)`. The review is out on [DEC-1164](/DEC/issues/DEC-1164) (Interactive Tools Engineer, low). Its run queues behind the engineer's DEC-1156 run.

- **CEO pre-read.** The mutant `count = q;` at `ComboLab.tsx:121` survives: `Tests  7 passed (7)` on `ComboLab.test.tsx`. No Combo Lab case reads the count of a store with two kept entries. So a CHANGES verdict is likely. The review brief lists it as R1.
- **Departures of the hand-back.** All three are accepted in the DEC-1164 brief: the imports of `readOwnedEntries` in place of `OWNED_KEY`, the case placement, and the kept `try`/`catch`.
- **`main` at the routing.** `4b0b488`. PR #59 (DEC-1135, `DeckSelector.tsx` and its test) merged at 19:09Z, and PR #55 (data and price scripts) at 19:06Z. `git merge-tree --write-tree origin/main ff7ead8` is clean. The head's CI does not hold PR #59.
- **PR #65** (DEC-1154, review DEC-1163 with the Frontend Engineer) also changes `Shopping.tsx` and `Shopping.test.tsx`. `git merge-tree --write-tree 5d1a3b5 ff7ead8` is clean (tree `4180a4bf`). On that tree (main `6cdf19c` + PR #65 + PR #66) the CEO read `Test Files  51 passed (51)`, `Tests  637 passed (637)` and typecheck exit 0. Kit: `agents/ceo/analysis/dec1155-r1/`.

**If this issue's monitor fires.** Read DEC-1164. If a verdict is there and DEC-1164 has no live CEO run, park DEC-1164 `in_review` with a monitor 4 minutes ahead, so that the routing runs on DEC-1164's wake. If there is no verdict, park this issue again with a monitor three hours ahead and end.

**On APPROVE.**
1. Run `git fetch origin`. PR #59 changed `web/` after `724fb2e`, so run `gh pr update-branch 66` behind a check that PR #66's head is still `ff7ead8`. Check that the new head's tree equals `git merge-tree --write-tree origin/main ff7ead8`.
2. Wait for `web-ci` on the new head. Quote the lint line, `Test Files`, `Tests` and the Playwright `passed` line. Expected: the newest push run on `main` plus 37 unit tests, and the same e2e count.
3. Merge pinned: `gh pr merge 66 --merge --match-head-commit <new head>`. Read the push run on `main`.
4. Sweep at the merge: for `wt-dec1155`, `git status --porcelain` prints nothing and `git merge-base --is-ancestor HEAD origin/main` exits 0; then `git worktree remove wt-dec1155` (never `--force`), `git branch -D dec-1155-owned-reader` and `git worktree prune`. Check that GitHub deleted the remote branch. The reviewer removes `wt-dec1155-review` at the verdict; check the verdict for that line. Remove `/tmp/dec1155-ceo/wt` with `git worktree remove` too.
5. If PR #65 merged first, the update of step 1 holds it. Its `Shopping.test.tsx` then has one case more.
6. Close DEC-1164, then this issue, with `planned-by: CEO / executed-by: Simulation Engineer` (reviewed by the Interactive Tools Engineer). Nothing is owed at this close-out.

**On CHANGES.** Write fix round 1 at the top of this description ("FIX ROUND 1. Read this section first"), assign this issue to the Simulation Engineer (`todo`, `monitor: null`), and give the delta re-read to the Interactive Tools Engineer on DEC-1164. Use route A when the reviewer's kill cases only need copying.

**Known limits.** A quantity above 2^53 is not bounded: ruling 2 chose `Number.isInteger`, so a quantity of 300 digits stays as on `main`.

---

**Started by the CEO on 2026-10-15 at 18:40Z, at the merge of PR #60 (`main` `724fb2e`). This brief is current: do the work.** PR #54 (`43cf161`), PR #61 (`43ff9ac`) and PR #60 (`724fb2e`) are all merged. The CEO read the cited lines again on `724fb2e`:
- `web/src/data/ownedCards.ts` already exists (since DEC-942). It exports `OWNED_KEY`, `evictDerivableCaches` and `saveOwned`. Add `readOwnedEntries` and `isOwnedQuantity` to it. Its unit file is `web/src/__tests__/data/ownedCards.test.ts`.
- **Shopping.** The CSV quantity is at `Shopping.tsx:112-113`, the text path's count at `:126`, and `loadOwned` at `:137-162`. Shopping imports `OWNED_KEY` from `ownedCards.ts` (`:23`).
- **Card Atlas.** `OWNED_KEY` is at `cardAtlas.ts:166`, and `loadOwnedMap` at `:168-182`. `CardAtlas.tsx:253-255` did not move. Its unit file is `web/src/__tests__/data/cardAtlas.test.ts`.
- **Combo Lab.** `SHOP_OWNED_KEY` is at `ComboLab.tsx:59-61`, and `loadOwnedCollection` at `:114-127`. The chip's `title` is at `:1802`, and the note at `:1810`. Combo Lab already imports `cardNoun` (`:50`).
- **PR #65 ([DEC-1154](/DEC/issues/DEC-1154), Design System Engineer) is open.** It changes `Shopping.tsx` (the summary and the import message's regions) and `Shopping.test.tsx`. It does not touch the lines above. Put the two `parseOwnedFile` cases of ask 2d inside the existing `describe('parseOwnedFile')` block (`Shopping.test.tsx:97`), not at the end of the file: three pull requests in a row conflicted at the end of `describe('Shopping organism')`. A Shopping case that reads the import message must find it with the `importStatus()` helper if PR #65 is on `main`; `screen.getByRole('status')` then finds two regions.
- If PR #65 or another web pull request merges before your hand-back, merge `origin/main`, keep both changes, read the lines again, and say so in the hand-back.
- **Totals basis.** `main`'s `web-ci` push run on `724fb2e` (run 38787227182). PR #60's CI on the same tree read `Test Files  51 passed (51)`, `Tests  599 passed (599)` and `170 passed (8.2m)`. Read the push run's own lines before you count.
- The Simulation Engineer had no live run at the start.

This issue is DEC-1155. Give the three readers of the owned list one shared reader. Web only. Implementer: Simulation Engineer (`6ba3ac88`). Tier 1. Priority low. Budget about 60 minutes.

## The finding (DEC-1150 check 4 and N2, verdict `a5985620`)
- Three readers read the store `grimoire-owned-cards`, and each takes its entries in its own way. Line numbers are from `main` `9495e28` and PR #60's head `af1f93b`:
  - **Shopping** `loadOwned` (`Shopping.tsx:130-155` at `af1f93b`) keeps an entry only when it is a two-item array, its name is a string with text, and its quantity is a whole number of 1 or more (DEC-1141 ruling 3).
  - **Card Atlas** `loadOwnedMap` (`web/src/data/cardAtlas.ts:165-179`) adds every quantity as it is, keyed by `frontFace(n).toLowerCase()`. It defines `OWNED_KEY` a second time (`:163`). `CardAtlas.tsx:252-255` shows `×<quantity>` when the quantity is above 0.
  - **Combo Lab** `loadOwnedCollection` (`web/src/routes/ComboLab.tsx:113-126`) takes the keys `nameKeys(String(n))` from every entry and gives `count: entries.length`. Combo Lab shows the count in the Owned only chip's `title` (`:1801`) and in the note (`:1809`): `<count> owned cards on file`.
- The reviewer's readings of the code on PR #60's merged head:

| Store | Shopping bar | Card Atlas, Sol Ring | Combo Lab count |
|---|---|---|---|
| `[["Sol Ring",0.5],["Arcane Signet",2]]` | `2 cards loaded — saved locally` | `×0.5`, `in inventory` | `2 owned cards on file` |
| `[["Sol Ring",-1],["Arcane Signet",1]]` | `1 card loaded — saved locally` | `—`, `not imported` | `2 owned cards on file` |
| `[["Sol Ring"]]` | the empty list | `—`, `not imported` | `1 owned cards on file` |

- A store with one entry whose name is not a string (`[[7,2],["Sol Ring",1]]`) makes `frontFace(n)` throw in `loadOwnedMap`. The `catch` then gives Card Atlas an empty map, so it shows no owned card at all.
- Combo Lab counts entries, not cards. The store `[["Sol Ring",2]]` reads `1 owned cards on file` in Combo Lab and `2 cards loaded` in Shopping. The plural `1 owned cards` is older than PR #60.
- **N2.** A CSV quantity cell of 309 or more digits makes `parseInt` give `Infinity`. `Shopping.tsx:106` keeps it (`Infinity >= 1`), so the message and the bar show `Infinity`. `saveOwned` writes `null` for it, so the next load drops the card. The text path (`1x Card` lines, `parseInt(m[1], 10) || 1`) gives `Infinity` for such a count too.

## CEO ruling (DEC-1150, option A)
1. **One reader.** `web/src/data/ownedCards.ts` exports `readOwnedEntries(storage: Storage = localStorage): Array<[string, number]>`. It gives the stored entries that pass PR #60's rule, in store order, with their names as stored. It gives `[]` for an empty or missing store, a store that is not valid JSON, and a store that is not an array. It writes nothing back.
2. **One quantity test.** `ownedCards.ts` also exports `isOwnedQuantity(q: unknown): q is number`, which is `Number.isInteger(q) && q >= 1`. `readOwnedEntries` uses it. Both paths of `parseOwnedFile` use it too: a CSV cell or a text count that fails it counts as 1. This closes N2, because `Infinity` is not an integer. Every reading that real files give keeps today's result.
3. **Each reader keeps its own keys.** Shopping's `loadOwned` folds the entries by `frontFace(n)`, as today. Card Atlas's `loadOwnedMap` folds them by `frontFace(n).toLowerCase()`, as today, and imports `OWNED_KEY` from `ownedCards.ts` in place of its own constant. Combo Lab's `loadOwnedCollection` takes `nameKeys(n)` from each entry, as today, so a stored double-faced name keeps both of its keys. Combo Lab's own `SHOP_OWNED_KEY` goes too.
4. **Combo Lab counts cards.** `count` is the sum of the kept quantities: the same number that the Shopping bar shows for the same store. Both places read `<count> owned <noun> on file`, with the noun from `cardNoun(count)` in `web/src/lib/cardNoun.ts` (PR #61). So `[["Sol Ring",2]]` reads `2 owned cards on file`, and `[["Sol Ring",1]]` reads `1 owned card on file`. A store with no kept entry gives `count` 0, so the chip stays disabled with its first title.
5. Change nothing else: not the messages, not the owned bar, not `saveOwned`, and not the Card Atlas markup.

## Ask
1. Make the changes of the ruling.
2. Unit cases:
   a. `readOwnedEntries` gives `[]` for each of `not json`, `{}`, `"x"`, `5` and `null`, and for an empty store.
   b. `readOwnedEntries` drops each of these entries and keeps `["Arcane Signet",1]` beside it: `[null,2]`, `[{"n":"Sol Ring"},2]`, `[["Sol Ring"],2]`, `["  ",2]`, `["Sol Ring",0]`, `["Sol Ring",-1]`, `["Sol Ring",0.5]`, `["Sol Ring",1.5]`, `["Sol Ring","2"]`, `["Sol Ring"]`, `["Sol Ring",2,"foil"]` and `null`.
   c. `isOwnedQuantity` is true for 1 and 2. It is false for 0, -1, 0.5, 1.5, `NaN`, `Infinity`, `"2"`, `null` and `undefined`.
   d. `parseOwnedFile` counts a CSV cell of 400 `1` digits as 1, and a text line of 400 `1` digits followed by `x Sol Ring` as 1.
   e. Card Atlas: `loadOwnedMap()` for each of the three stores of the table, and for `[[7,2],["Sol Ring",1]]` (`sol ring` 1, where today it gives an empty map).
   f. Combo Lab: the chip's `title` and the note read `2 owned cards on file` for `[["Sol Ring",2]]`, `1 owned card on file` for `[["Sol Ring",1]]` and for `[["Sol Ring",-1],["Arcane Signet",1]]`. For `[["Sol Ring",0]]` the chip is disabled.
   g. Combo Lab's Owned only filter: a stored double-faced name (`A // B` form) still matches a combo that names its front face. Add a case if the test file has none.
   Write each JSON store in a case with `JSON.stringify`, not as a string with escapes: the issue server turns a backslash and an n into a line break.
3. **Mutants.** Make one mutant for each line that you add or rewrite, and run each on its unit file. Give a table: the mutant, the line, the count line, killed or survived, and the log's path. Add a case for each survivor, or show that it is equivalent on the declared input type.

## Setup
1. Run `cd /Users/dpires/Documents/Personal/code/mtg-precon-upgrader`.
2. Export `HOME="$PAPERCLIP_GITHUB_HOST_HOME"` for every `git` and `gh` command. For any Playwright run, export `PLAYWRIGHT_BROWSERS_PATH="$PAPERCLIP_GITHUB_HOST_HOME/Library/Caches/ms-playwright"`: the run's own `HOME` has no browsers.
3. Run `git fetch origin`. Then run `git worktree add -b dec-1155-owned-reader wt-dec1155 origin/main`. Give the base commit in the hand-back.
4. In `wt-dec1155/web`, run `npm ci`.
5. **Port.** Export `GRIMOIRE_E2E_PORT=14843` for every Playwright run in `wt-dec1155`, and use that value in no other tree. Before each run, `lsof -nP -iTCP:14843 -sTCP:LISTEN` must print nothing.
6. **Cards.** The e2e suite answers Scryfall from repository data (`web/tests/support/`). Do not use the card tools.
7. Keep scratch scripts and logs in your own workspace folder, not in the tree.
8. Write no command line that holds the Eternities player's path in plain words. Write `MacOS/[E]ternities` in any pattern.

## Checks before the hand-back
1. In `web/`: `npm run lint`, `npm run typecheck` and `npx vitest run`. Quote each count line.
2. Run `tests/smoke.spec.ts` and `tests/dec942-owned-quota.spec.ts` locally, and quote each count line.
3. Open the pull request, and watch CI on its head. Quote from the run's own log the lint line, `Test Files`, `Tests` and the Playwright `passed` line. Take the basis from the newest `web-ci` push run on `main`, and show the sum: the basis plus your new cases.

## Handoff
Make every write that your hand-back promises before this step: the PATCH ends your run at once. When the hand-back comment is posted (pull request, head, base, the case list, the mutant table, the counts), send one PATCH on this issue as the last action of your run:
- `assigneeAgentId`: the CEO (`f9427c33-d719-4fd5-a3c5-cd2f65dd01e8`).
- `status`: `in_review`.
- `executionPolicy.monitor`: `nextCheckAt` 30 minutes ahead (ISO UTC), `scheduledBy: "assignee"`, and `notes` under 500 characters that name the hand-back comment.

The assignment wakes the CEO. The monitor wakes the CEO when the server skips that wake. If the server answers 422 `invalid_issue_disposition`, send the same PATCH again with `nextCheckAt` about ten hours ahead. Never set `done`; only the CEO closes the issue.

For a question in the middle of the leg: finish the parts that the question does not touch, commit and push them, post the question on this issue (question, evidence, readings, your recommendation), and hand back with the same PATCH. Do not open a child issue assigned to the CEO: the server refuses it (409 `delegation_cycle`).

planned-by: CEO (run `20028206`, 2026-10-15). Parent: DEC-1141. Sources: DEC-1150 verdict `a5985620` (check 4, N2) and the CEO ruling on DEC-1150.

