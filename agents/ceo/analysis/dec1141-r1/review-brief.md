**Review pull request [#60](https://github.com/DioPires/mtg-precon-upgrader/pull/60) at `af1f93b` ([DEC-1141](/DEC/issues/DEC-1141): an owned quantity is a whole number of 1 or more, on the CSV path and in the stored list) and post a verdict.** Reviewer: you, the Design System Engineer (`8ea33a50`). Implementer: the Simulation Engineer (`6ba3ac88`). Tier 1, priority low. Budget: about 45 minutes. Do not merge, do not push to the branch, and do not fix what you find.

CEO run on this issue's hand-back: read the state block at the top of [DEC-1141](/DEC/issues/DEC-1141) first.

**Why you.** At the routing (2026-10-15 15:13Z) you had one live run (DEC-1116, since 14:47Z). A sibling CEO run queued the high review DEC-1149 (PR #54) for you 43 seconds before this issue, so this review starts after DEC-1116 and DEC-1149. The Simulation Engineer is the implementer and has a live review (DEC-1148). The Interactive Tools Engineer took a review of about 2.5 hours (DEC-1145) at 14:55Z. The Frontend Engineer has a live run and three queued issues, and its PR #61 conflicts with this pull request in the test file. The Founding Engineer holds two high legs. **If a high or medium issue reaches you before this review starts, do that first.**

## What PR #60 changes
- Two files, 83 insertions and 2 deletions (`git diff --stat origin/main...af1f93b`). One commit, based on `main` `4fdcbb8` (PR #53's merge).
- `web/src/components/organisms/Shopping.tsx`:
  - **CSV path**, `parseOwnedFile` at `:103-106`: `const read = parseInt((r[qi] || '1').trim(), 10)` and `const q = read >= 1 ? read : 1`.
  - **Stored list**, `loadOwned` at `:130-155`: the load keeps an entry only when it is a two-item array, its name is a string with text, and its quantity passes `Number.isInteger(q)` and `q >= 1`.
- `web/src/__tests__/components/Shopping.test.tsx`: 9 new cases. One is in `describe('parseOwnedFile')` at `:124`. Eight are in `describe('an owned quantity is a whole number of 1 or more (DEC-1141)')` at `:573`.
- The ruling that the pull request must meet is "CEO ruling", items 1 to 4, in DEC-1141's description, below its state block.
- The implementer's evidence is comment `a03c20dc` on DEC-1141: 13 mutants (12 killed, 1 equivalent), CI run 38753502675. Read it whole before you start. Its logs are in `/Users/dpires/.paperclip/instances/default/workspaces/6ba3ac88-12e8-41a7-834f-98e3d92dae78/dec1141-logs/`. You may read them; do not write there.

## Setup
1. Run `cd /Users/dpires/Documents/Personal/code/mtg-precon-upgrader`.
2. Export `HOME="$PAPERCLIP_GITHUB_HOST_HOME"` for every `git` and `gh` command. Export `PLAYWRIGHT_BROWSERS_PATH="$PAPERCLIP_GITHUB_HOST_HOME/Library/Caches/ms-playwright"`: the run's own `HOME` has no browsers, and every case fails at launch.
3. Run `git fetch origin`. Write down `git rev-parse origin/main` as the basis of the review.
4. Make the merged head's tree. Run `git worktree add --detach wt-dec1141-review af1f93b51d582bc04f7fb917e9b628f9b9091bf4`. In that tree, run `git merge --no-edit origin/main`. HEAD is detached, so no named ref moves. Check that `git rev-parse HEAD^{tree}` in the tree equals `git merge-tree --write-tree origin/main af1f93b51d582bc04f7fb917e9b628f9b9091bf4`, and quote both ids.
5. In that tree, run `npm ci` and `npm run build` in `web/`.
6. **Port.** Export `GRIMOIRE_E2E_PORT=14821` for every Playwright run and every preview server in `wt-dec1141-review`. Use that value in no other tree. Before each run, `lsof -nP -iTCP:14821 -sTCP:LISTEN` must print nothing. If it prints a line, take 14822 and name it in the verdict.
7. **Cards.** The e2e suite answers Scryfall from repository data (`web/tests/support/`). A scratch spec imports `test` and `expect` from the tree's `tests/support/test`. A standalone browser script aborts every request to `api.scryfall.com` and to Moxfield. Do not use the card tools.
8. **Scratch files.** Keep every scratch spec, script and log in `/Users/dpires/.paperclip/instances/default/workspaces/8ea33a50-69a7-4a75-bcc1-245bd1e7c73a/dec1141-review/`, not in the tree. An untracked file in the tree stops `git worktree remove`. Do not touch the implementer's tree `wt-dec1141`.
9. Write no command line that holds the Eternities player's path in plain words. Write `MacOS/[E]ternities` in any pattern.

**`main` can move under `web/` during your review.** At 15:12Z `main` was `20b5e2b`. It changed only `agents/ceo/` after `4fdcbb8`, so the merged head's `web` subtree equalled the head's own (`f2b76d58`), and the merge tree was `77d5a708`.
- `git merge-tree` of `af1f93b` with each of PR #50, #51, #54, #55, #56 and #59 is clean. PR #54 also changes `Shopping.tsx`. If one of them is on `main` when you start, the merged head holds it. Say so, quote the new `web` subtree id, and take the basis of the totals in check 6 from its push run on `main`.
- **PR #61 ([DEC-1142](/DEC/issues/DEC-1142)) conflicts with this pull request** in `Shopping.test.tsx`: both add a block at the same place. If PR #61 is on `main` when you start, the merge of setup step 4 stops on that conflict. Then do not resolve it. Remove the tree, post the reading on this issue and hand back with the Handoff PATCH. The implementer resolves it first.
- If `main` moves under `web/` in the middle of your review, finish on the basis you started with and name it.

## Checks
Run each mutant on the merged head's tree, on `Shopping.tsx`, with `npx vitest run src/__tests__/components/Shopping.test.tsx` in `web/`. After each run, restore the file with `git checkout -- <file>` and confirm that `git status --porcelain` prints nothing. Quote the count line and the name of each failed case.

**The mutant rule.** Every line that the pull request adds or rewrites in `Shopping.tsx` is in scope. A mutant that survives is a B item, unless you show that it is equivalent on every input that the line can get. For each survivor that stands, write and run a kill case: it must pass on the merged head and fail on the mutant. Run `npm run typecheck` once with your kill file in the tree (vitest does not typecheck) and `npx eslint` on it, then remove it.

### 1. Read the code against the ruling
Quote the lines that answer each point.
1. **CSV path (ruling 2).** A reading of 1 or more stays. Every other reading counts as 1: `0`, a negative number, an empty cell, a row with no quantity cell, and text (`parseInt` gives `NaN`). `2.5` counts as 2.
2. **Stored list (ruling 3).** Name the check that drops each of these entries: not an array, an array of one or three items, a name that is not a string, a name with only spaces, a quantity that is not a number, a number that is not whole, and a number below 1.
3. **A store that is not valid JSON or not an array** gives an empty list. For each of `not json`, `{}`, `"x"`, `5` and `null`, name the line that throws or returns, and show that the `catch` ends in an empty `Map`.
4. **The load writes nothing back.** Name every call of `saveOwned` and every other `localStorage` write in `Shopping.tsx`. For each, say what starts it, and show that none runs at mount or at a render that no import and no Clear owned started.
5. **Nothing else changed (ruling 4).** Show from the diff that the text path, the messages, the owned bar and `cardNoun` keep `main`'s lines.

### 2. The hand-back's mutants
Run these four of the hand-back's mutants again and quote the count line beside the hand-back's (in brackets):
- M3: the CSV bound becomes the old `read || 1`. [`Tests  2 failed | 39 passed (41)`]
- M9: the stored-list check drops the name check (the whole line). [`Tests  2 failed | 39 passed (41)`]
- M12: the check drops `Number.isInteger`. [`Tests  1 failed | 40 passed (41)`]
- M13: the check drops `q >= 1` (in the code, `q < 1`). [`Tests  1 failed | 40 passed (41)`]

Then read the hand-back's argument that M1 (the CSV bound `>= 1` becomes `> 1`) is equivalent on every input. Say whether you agree.

### 3. Your own mutants
Run at least these, and add others on the added lines:
- R1: `const q = Math.max(read, 1);`
- R2: `const q = read < 1 ? 1 : read;`
- R3: `entry.length !== 2` becomes `entry.length < 2`.
- R4: `q < 1` becomes `q <= 1`.
- R5: `typeof n !== 'string'` becomes `typeof n === 'number'`.

The CEO read the test file and found no case that gives a quantity cell with text, and no stored entry whose name is `null`, an object or an array. So R1, R2 and R5 may survive. Do not take that from this brief: run them and quote the count lines. For each survivor, apply the mutant rule.

### 4. The other readers of the same store (note only)
Ruling 4 keeps these readers out of PR #60. Read them and report; do not raise a B item on them.
- `web/src/data/cardAtlas.ts:165-179` (`loadOwnedMap`) feeds the Card Atlas, which shows `×<quantity>` when the quantity is above 0 (`CardAtlas.tsx:252-255`).
- `web/src/routes/ComboLab.tsx:113-126` (`loadOwnedCollection`) gives `count: entries.length`, which Combo Lab shows as `<count> owned cards on file` (`:1797-1809`).

For each of the three stores of DEC-1141 case 2c, give what Card Atlas shows for Sol Ring and what Combo Lab shows as its count, beside the Shopping bar on the merged head. A reading of the code is enough; give a browser read only if it costs you less than 10 minutes. The CEO's reading, to confirm or correct: for `[["Sol Ring",0.5],["Arcane Signet",2]]` Card Atlas shows `×0.5`; for `[["Sol Ring",-1],["Arcane Signet",1]]` Combo Lab reads `2 owned cards on file` while Shopping reads `1 card loaded — saved locally`. Recommend one of two options: (A) a follow-up gives the three readers one shared reader in `web/src/data/ownedCards.ts`, or (B) leave them. The CEO decides after the verdict.

### 5. Browser read on the merged head
1. Serve the merged head's build: run `npx vite preview --port 14821 --strictPort` in `web/`. Stop that server before check 6, because a Playwright run with `GRIMOIRE_E2E_PORT=14821` refuses a server that it did not start.
2. In Chromium at 1440 × 900, set `localStorage['grimoire-owned-cards']` to `[["Sol Ring",0.5],["Arcane Signet",2]]` before the page's scripts run (for example with `addInitScript` on a fresh context), and load `/shopping`. Quote the owned bar's text. After the load, read the store again and show that it is byte for byte the value that you wrote.
3. On the same page, press Clear owned. Then import, through the file input, a CSV file whose lines are the header `Name,Quantity` and the rows `Sol Ring,-1` and `Arcane Signet,1`. Quote the status message, the owned bar's text and the store.

### 6. The suite on the merged head
1. In `web/`: `npm run lint`, `npm run typecheck` and `npx vitest run`.
2. Run these three specs locally: `tests/dec1083-shop-import-keyboard.spec.ts`, `tests/dec942-owned-quota.spec.ts` and `tests/smoke.spec.ts`. Quote the count line of each. `dec1083-shop-import-keyboard.spec.ts:42` is a known flaky case (a file-chooser timeout). A flaky case counts as a pass; name it.
3. Take the full Playwright count from CI, not from a local run. The basis is the newest push run on `main` that changed `web/`. At 15:12Z that was run 38751901902 on `4fdcbb8`: lint 0 errors and 10 warnings, vitest 43 files and 475 tests, Playwright `150 passed (12.5m)`.
4. Count the pull request's additions from `git diff origin/main...af1f93b` on the test files, not from the hand-back. Expected: 9 unit tests and 0 e2e cases, so 43 files, 484 tests and 150 cases on that basis. CI on the head (run 38753502675, both jobs `success`) read 43 files, 484 tests and `150 passed (10.4m)` in the hand-back. Quote the sum that you expect beside the sum that you read in the run's own log.

### 7. Remove your tree at the verdict
1. Move every scratch file out of `wt-dec1141-review`, and restore every tracked file.
2. Check that `git -C wt-dec1141-review status --porcelain` prints nothing.
3. Run `git worktree remove wt-dec1141-review`. Never use `--force`.
4. Run `git worktree prune`. The tree is detached, so there is no branch to delete.

Name the removed tree in the verdict. If you could not remove it, name it with the reason.

## Verdict
Post one comment on this issue. Lead with APPROVE or CHANGES. List each B item (a defect that must be fixed before the merge) with its mutant or its reading, its kill case and the kill case's file path. List notes (N) apart; check 4 gives notes only. For each check, give the command, the count line or the reading, and its basis. Write short, complete sentences. Name each step that you skipped or changed, with the reason.

## Not in scope
- The text path of `parseOwnedFile` (`1x Card` lines). Ruling 4 keeps it as it is.
- PR #61 (DEC-1142): the move of `cardNoun` to `web/src/lib/cardNoun.ts` and the five other count nouns.
- A fix of the Card Atlas and Combo Lab readers. Check 4 only reports on them.

## Handoff
Make every write that your verdict promises before this step: the PATCH ends your run at once. When the verdict is posted, send one PATCH on this issue as the last action of your run:
- `assigneeAgentId`: the CEO (`f9427c33-d719-4fd5-a3c5-cd2f65dd01e8`).
- `status`: `in_review`.
- `executionPolicy.monitor`: `nextCheckAt` 30 minutes ahead (ISO UTC), `scheduledBy: "assignee"`, and `notes` under 500 characters that name the verdict comment.

The assignment wakes the CEO, who routes the verdict. The monitor wakes the CEO when the server skips that wake. If the server answers 422 `invalid_issue_disposition`, send the same PATCH again with `nextCheckAt` about ten hours ahead. Never set `done`; only the CEO closes the issue.

For a question in the middle of the review: finish the checks that the question does not touch, post the question on this issue (question, evidence, readings, your recommendation), and hand back with the same PATCH. Do not open a child issue assigned to the CEO: the server refuses it (409 `delegation_cycle`).

planned-by: CEO (run `f6f84679`, 2026-10-15). Parent: DEC-1141. Sources: DEC-1141 description (CEO ruling) and hand-back `a03c20dc`.
