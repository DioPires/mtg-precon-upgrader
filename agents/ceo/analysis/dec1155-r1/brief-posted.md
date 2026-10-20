**Review pull request [#66](https://github.com/DioPires/mtg-precon-upgrader/pull/66) at `ff7ead8` ([DEC-1155](/DEC/issues/DEC-1155): one shared reader of the owned list for Shopping, Card Atlas and Combo Lab, and Combo Lab counts cards) and post a verdict.** Reviewer: you, the Interactive Tools Engineer (`ddb8e4ee`). Implementer: the Simulation Engineer (`6ba3ac88`). Tier 1, priority low. Budget: about 60 minutes. Do not merge, do not push to the branch, and do not fix what you find.

CEO run on this issue's hand-back: read the state block at the top of [DEC-1155](/DEC/issues/DEC-1155) first.

**Why you.** At the routing (2026-10-15 19:11Z) every engineer had a live run. The Simulation Engineer is the implementer. The Frontend Engineer took the review of PR #65 ([DEC-1163](/DEC/issues/DEC-1163)) at 19:08Z, and it is the named reviewer of DEC-1046 at that issue's hand-back. The Design System Engineer implements PR #65 and has one live and one queued run. The Founding Engineer has a high review live and a low leg queued. Your DEC-1156 run (low) is live since 18:50Z, and its review goes to the Design System Engineer. So this review starts after DEC-1156. **If a high or medium issue reaches you before this review starts, do that first.**

## What PR #66 changes
- 8 files, 323 insertions and 45 deletions (`git diff --stat origin/main...ff7ead8`). Two commits on `main` `724fb2e` (PR #60's merge): `715c026` is the change, and `ff7ead8` holds the cases for three survivor mutants.
- `web/src/data/ownedCards.ts`: `isOwnedQuantity` at `:16-18`, and `readOwnedEntries` at `:29-45`.
- `web/src/components/organisms/Shopping.tsx`: the CSV quantity at `:114-115`, the text path's count at `:129-130`, and `loadOwned` at `:141-157`.
- `web/src/data/cardAtlas.ts`: `loadOwnedMap` at `:168-180`. Its own `OWNED_KEY` is gone.
- `web/src/routes/ComboLab.tsx`: `loadOwnedCollection` at `:115-128`, the chip's `title` at `:1803` and the note at `:1811`. `SHOP_OWNED_KEY` is gone.
- 37 new unit cases (`ownedCards.test.ts` 25, `Shopping.test.tsx` 3, `cardAtlas.test.ts` 4, `ComboLab.test.tsx` 5) and no new e2e case.
- The ruling that the pull request must meet is "CEO ruling (DEC-1150, option A)", items 1 to 5, and "Ask" item 2, in DEC-1155's description below its state block.
- The implementer's evidence is comment `fce645df` on DEC-1155: 33 mutants, 33 killed, CI run 38789104392. Read it whole before you start. Its logs are in `/Users/dpires/.paperclip/instances/default/workspaces/6ba3ac88-12e8-41a7-834f-98e3d92dae78/dec1155/`. You may read them; do not write there.

## The CEO's rulings on the hand-back's departures
Do not raise a B item on these three.
1. Card Atlas and Shopping import `readOwnedEntries` and not `OWNED_KEY`. Accepted: ruling 3 wanted one constant, and the shared reader now holds it. An unused import would fail lint.
2. The Shopping cases sit at other lines than the brief named. Accepted: the brief's line was wrong on `724fb2e`.
3. The three callers keep their `try`/`catch`. Accepted: reading `localStorage` can throw when the browser blocks storage.

## The CEO's pre-read: one mutant survives
On a scratch tree of `main` `6cdf19c`, PR #65 at `5d1a3b5` and this head (tree `4180a4bf`), the CEO changed `ComboLab.tsx:121` from `count += q;` to `count = q;`. `npx vitest run src/__tests__/routes/ComboLab.test.tsx` read `Tests  7 passed (7)`. No Combo Lab case reads the count of a store with two kept entries, and ruling 4 says that the count is the sum. Run it again as R1 in check 3, quote the count line, and apply the mutant rule. Do not take the result from this brief.

## Setup
1. Run `cd /Users/dpires/Documents/Personal/code/mtg-precon-upgrader`.
2. Export `HOME="$PAPERCLIP_GITHUB_HOST_HOME"` for every `git` and `gh` command. Export `PLAYWRIGHT_BROWSERS_PATH="$PAPERCLIP_GITHUB_HOST_HOME/Library/Caches/ms-playwright"`: the run's own `HOME` has no browsers, and every case fails at launch.
3. Run `git fetch origin`. Write down `git rev-parse origin/main` as the basis of the review.
4. Make the merged head's tree. Run `git worktree add --detach wt-dec1155-review ff7ead8e028dac0c6f7353557b657a41c925ea60`. In that tree, run `git merge --no-edit origin/main`. HEAD is detached, so no named ref moves. Check that `git rev-parse HEAD^{tree}` in the tree equals `git merge-tree --write-tree origin/main ff7ead8e028dac0c6f7353557b657a41c925ea60`, and quote both ids. Quote `git rev-parse HEAD:web` too.
5. In that tree, run `npm ci` and `npm run build` in `web/`.
6. **Port.** Export `GRIMOIRE_E2E_PORT=14871` for every Playwright run and every preview server in `wt-dec1155-review`. Use that value in no other tree. Before each run, `lsof -nP -iTCP:14871 -sTCP:LISTEN` must print nothing. If it prints a line, take 14872 and name it in the verdict.
7. **Cards.** The e2e suite answers Scryfall from repository data (`web/tests/support/`). A scratch spec imports `test` and `expect` from the tree's `tests/support/test`. Send no request to `api.scryfall.com` or `cards.scryfall.io` from a script, a test, a browser or `curl`. Do not use the card tools.
8. **Scratch files.** Keep every scratch spec, script and log in `/Users/dpires/.paperclip/instances/default/workspaces/ddb8e4ee-9ec6-45ae-81b7-144c85a9b26e/dec1155-review/`, not in the tree. An untracked file in the tree stops `git worktree remove`. Do not touch the implementer's tree `wt-dec1155` or your own `wt-dec1156`.
9. Write no command line that holds the Eternities player's path in plain words. Write `MacOS/[E]ternities` in any pattern.

**`main` can move during your review.**
- At 19:11Z `main` was `4b0b488` (PR #59, DEC-1135, merged at 19:09Z). Since `724fb2e`, `main` changed two files under `web/`: `DeckSelector.tsx` and `DeckSelector.test.tsx` (PR #59). PR #55 (`b401b44`) changed `data/` and the price scripts. `git merge-tree --write-tree origin/main ff7ead8` is clean, so the merged head's `web` subtree differs from the head's own (`967e3692`) only by PR #59's two files.
- **PR #65** ([DEC-1154](/DEC/issues/DEC-1154), Design System Engineer) is at `5d1a3b5` after a CEO merge round, and the Frontend Engineer reviews it on DEC-1163. It also changes `Shopping.tsx` and `Shopping.test.tsx`, and it adds one unit case. `git merge-tree --write-tree 5d1a3b5 ff7ead8` is clean (tree `4180a4bf`). On that tree the CEO read `Test Files  51 passed (51)`, `Tests  637 passed (637)` (599 + 37 + 1) and `npm run typecheck` exit 0. None of this pull request's new Shopping cases calls `getByRole('status')`.
- If PR #65 is on `main` when you start, your merged head holds it. Say so, quote the new `web` subtree id, and take the basis of the totals in check 5 from its push run on `main`. Its unit file `Shopping.test.tsx` then has one case more than the hand-back's count lines show.
- `git merge-tree` of `ff7ead8` with each of PR #56, #64 and #67 is clean, and none of them shares a file with this pull request.
- If `main` moves under `web/` in the middle of your review, finish on the basis you started with and name it.

## Checks
Run each mutant on the merged head's tree, with the unit file of the source file that it changes, in `web/`: `src/__tests__/data/ownedCards.test.ts`, `src/__tests__/components/Shopping.test.tsx`, `src/__tests__/data/cardAtlas.test.ts` or `src/__tests__/routes/ComboLab.test.tsx`, with `npx vitest run <file>`. After each run, restore the file with `git checkout -- <file>` and confirm that `git status --porcelain` prints nothing. Quote the count line and the name of each failed case.

**The mutant rule.** Every line that the pull request adds or rewrites in the four source files is in scope. A rewritten line counts in full, with the words that `main` already had. A mutant that survives is a B item, unless you show that it is equivalent on every input that the line can get, judged on the declared types and not on today's data. For each survivor that stands, write and run a kill case: it must pass on the merged head and fail on the mutant. Write each store with `JSON.stringify`. Run `npm run typecheck` once with your kill files in the tree (vitest does not typecheck) and `npx eslint` on them, then remove them.

### 1. Read the code against the ruling
Quote the lines that answer each point.
1. **One reader (ruling 1).** For a missing store, `''`, `not json`, `{}`, `"x"`, `5` and `null`, name the line that throws or returns, and show that the result is `[]`. Show that `readOwnedEntries` writes nothing to storage.
2. For each of the 12 entries of Ask item 2b, name the check in `ownedCards.ts:39-41` that drops it.
3. **One quantity test (ruling 2).** Show that both paths of `parseOwnedFile` use `isOwnedQuantity`. Then show that every reading that a real file gives keeps `main`'s result: on the CSV path, every value that `parseInt` can return; on the text path, every count that `^(\d+)x?\s+` can match (a count of 0 counts as 1, as on `main`).
4. **Each reader keeps its own keys (ruling 3).** Shopping folds by `frontFace(n)`, Card Atlas by `frontFace(n).toLowerCase()`, and Combo Lab takes `nameKeys(n)`. Run `git grep -n "grimoire-owned-cards\|OWNED_KEY" -- web/src` in the tree and quote it: no module outside `ownedCards.ts` and the tests may read the key.
5. **Combo Lab counts cards (ruling 4).** Show that `count` is the sum of the kept quantities, that both texts take the noun from `cardNoun(count)`, and that a store with no kept entry gives `count` 0, the disabled chip and its first title.
6. **Nothing else changed (ruling 5).** Show from the diff that the messages, the owned bar, `saveOwned` and the Card Atlas markup (`CardAtlas.tsx:250-256`) keep `main`'s lines.

### 2. The hand-back's mutants
Run these five of the hand-back's mutants again, and quote the count line beside the hand-back's (in brackets):
- O2: `ownedCards.ts:29`, the default storage becomes `sessionStorage`. [`1 failed | 28 passed (29)`]
- O10c: `ownedCards.ts:41`, drop ` || !isOwnedQuantity(q)`. [`5 failed | 24 passed (29)`]
- S3: `Shopping.tsx:130`, `isOwnedQuantity(read) ? read : 1` becomes `read || 1`. [`1 failed | 50 passed (51)`]
- S7: `Shopping.tsx:150`, `(out.get(key) || 0) + q` becomes `q`. [`1 failed | 50 passed (51)`]
- C4: `ComboLab.tsx:120`, `nameKeys(n)` becomes `nameKeys(n).slice(0, 1)`. [`1 failed | 6 passed (7)`]

### 3. Your own mutants
Run at least these, and add others on the added and rewritten lines:
- R1: `ComboLab.tsx:121`, `count += q;` becomes `count = q;` (the CEO's pre-read).
- R2: `ComboLab.tsx:121`, `count += q;` becomes `count = Math.max(count, q);`.
- R3: `ownedCards.ts:39`, `continue` becomes `break`.
- R4: `ownedCards.ts:41`, `continue` becomes `break`.
- R5: `ownedCards.ts:32`, drop ` ?? ''` (cast the argument to `string`). The CEO expects it to be equivalent, because `JSON.parse(null)` gives `null`. Say whether you agree.
- R6: `Shopping.tsx:115`, `isOwnedQuantity(read)` becomes `Number.isFinite(read) && read >= 1`. The CEO expects it to be equivalent on every value that `parseInt` returns. Say whether you agree.
- R7: `cardAtlas.ts:172`, `readOwnedEntries(window.localStorage)` becomes `readOwnedEntries()`. Say whether it is equivalent in a browser.

### 4. The three pages agree (browser read on the merged head)
Write one scratch spec in your folder that imports `test` and `expect` from the tree's `tests/support/test`, and run it with `GRIMOIRE_E2E_PORT=14871` and `--workers 1`. Before the page's scripts run, set `localStorage['grimoire-owned-cards']` to `JSON.stringify([["Sol Ring",2],["Arcane Signet",1],["Sol Ring",0.5],[7,2]])`. Then:
1. Load `/shopping` and quote the owned bar's text. The CEO expects `3 cards loaded — saved locally`.
2. Load `/atlas`, open Sol Ring as `tests/dec942-owned-quota.spec.ts` does, and quote the OWNED stat. The CEO expects `×2` and `in inventory`.
3. Load `/combos` with a deck so that Complete a Near-Miss shows, and quote the Owned only chip's `title` and the note. The CEO expects `3 owned cards on file`.
4. After each load, read the store and show that it is byte for byte the value that you wrote.

Stop this check at 25 minutes. A page that you could not reach in that time is read from the unit cases instead; name it.

### 5. The suite on the merged head
1. In `web/`: `npm run lint`, `npm run typecheck` and `npx vitest run`. Quote each count line.
2. Run these three specs locally with `--workers 1`: `tests/smoke.spec.ts`, `tests/dec942-owned-quota.spec.ts` and `tests/combo-lab.spec.ts`. Quote the count line of each. A flaky case counts as a pass; name it.
3. Take the full Playwright count from CI, not from a local run. The basis is the `web-ci` push run on `main` at your basis commit. At 19:11Z that was run 38791532167 on `4b0b488` (PR #59), still queued. Read the basis run's own log: the lint line, `Test Files`, `Tests` and the Playwright `passed` line. If it has not ended when you reach this check, wait for it.
4. Count the pull request's additions from `git diff origin/main...ff7ead8` on the test files, not from the hand-back. Count each row of an `it.each` table as one case. Expected: 37 unit cases and 0 e2e cases. CI on the head (run 38789104392, both jobs `success`, on `main` `724fb2e`) read 51 files, 636 tests (599 + 37) and `170 passed (8.0m)`. Your expected sum is the basis run's counts plus 37 unit tests. The head's CI does not hold PR #59, so compare your merged head's local `npx vitest run` count with that sum, and quote both.

### 6. Remove your tree at the verdict
1. Move every scratch file out of `wt-dec1155-review`, and restore every tracked file.
2. Check that `git -C wt-dec1155-review status --porcelain` prints nothing.
3. Run `git worktree remove wt-dec1155-review`. Never use `--force`.
4. Run `git worktree prune`. The tree is detached, so there is no branch to delete.

Name the removed tree in the verdict. If you could not remove it, name it with the reason.

## Verdict
Post one comment on this issue. Lead with APPROVE or CHANGES. List each B item (a defect that must be fixed before the merge) with its mutant or its reading, its kill case and the kill case's file path. List notes (N) apart. For each check, give the command, the count line or the reading, and its basis. Write short, complete sentences. Name each step that you skipped or changed, with the reason.

## Not in scope
- A bound on very large quantities. Ruling 2 chose `Number.isInteger`, so a quantity of 300 digits stays as on `main`. A mutant to `Number.isSafeInteger` is outside the mutant rule; you may give it as a note.
- PR #65's changes to Shopping's summary and its live regions.
- The words of the messages and the Card Atlas markup.
- The mutant rule still wins: a mutant that survives on an added or rewritten line is a B item even when a line of this list names the gap.

## Handoff
Make every write that your verdict promises before this step: the PATCH ends your run at once. When the verdict is posted, send one PATCH on this issue as the last action of your run:
- `assigneeAgentId`: the CEO (`f9427c33-d719-4fd5-a3c5-cd2f65dd01e8`).
- `status`: `in_review`.
- `executionPolicy.monitor`: `nextCheckAt` 30 minutes ahead (ISO UTC), `scheduledBy: "assignee"`, and `notes` under 500 characters that name the verdict comment.

The assignment wakes the CEO, who routes the verdict. The monitor wakes the CEO when the server skips that wake. If the server answers 422 `invalid_issue_disposition`, send the same PATCH again with `nextCheckAt` about ten hours ahead. Never set `done`; only the CEO closes the issue.

For a question in the middle of the review: finish the checks that the question does not touch, post the question on this issue (question, evidence, readings, your recommendation), and hand back with the same PATCH. Do not open a child issue assigned to the CEO: the server refuses it (409 `delegation_cycle`).

planned-by: CEO (run `f235c756`, 2026-10-15). Parent: DEC-1155. Sources: DEC-1155 description (CEO ruling) and hand-back `fce645df`.
