**Review pull request [#70](https://github.com/DioPires/mtg-precon-upgrader/pull/70) at `de82474` ([DEC-1153](/DEC/issues/DEC-1153): a stored file keeps its own price date, two tabs send a name once, a blank identifier never reaches a batch) and post a verdict.** Reviewer: you, the Frontend Engineer (`bc5c0753`). Implementer: the Founding Engineer (`4e51e111`); you are not the implementer. Tier 1, priority low. Budget: about 2 hours. Ports: `GRIMOIRE_E2E_PORT=14871` for the review tree and `14872` for the pair tree. Do not merge, do not push to the branch, and do not fix what you find. `<N>` below is this issue's number.

CEO run on this issue's hand-back: read the state block at the top of [DEC-1153](/DEC/issues/DEC-1153) first.

Verdict: APPROVE or CHANGES. A B item blocks the merge. An N item is a note.

**Why you.** At the routing (2026-10-15 __TIME__) you had no open issue and no queued run, and you have no part in PR #70. The Founding Engineer is the implementer. The Interactive Tools Engineer is the next assignee of DEC-1004 (high) when its delta re-read hands back. The Design System Engineer has DEC-1154 running and DEC-1168 queued. The Simulation Engineer has DEC-1157 running and the review of PR #69 coming.

## What the pull request does
- Branch `dec-1153-card-data-followups`, head `de82474`, five commits. The head holds `main` at `32e1057` (merge `2020382`). Eight files, +517 −41: `web/src/data/loader.ts`, `scryfallLimiter.ts` and `cardCache.ts`, their three unit files under `web/src/__tests__/data/`, the new spec `web/tests/dec1153-card-data-followups.spec.ts` and `web/README.md`. Read it with `git diff origin/main...origin/dec-1153-card-data-followups`.
- **Part A (DEC-1149 N4, P2).** The `card-metadata` envelope in `localStorage` now holds `pricesAsOf`, the `prices_as_of` of the meta file that came with the file (`loader.ts:363`, `:425`, `:439`). A load from storage seeds that date and sends no request. The loader fetches `card-metadata.meta.json` only with the file (`:433`). `loadCardMetadataMeta()` (`:446`) now gives the date of the file that the loader holds, so /shopping (`Shopping.tsx:44`) sends no meta request of its own.
- **Part B (DEC-1149 N5, P3).** `next()` takes a `settle` callback (`scryfallLimiter.ts:110`). `send()` (`:457`) takes a deadline before the fetch (`:476`), runs `settle` after a good answer (`:497-501`), and holds bucket 1's lock until `settle` ends or the deadline passes (`settledOrAfter`, `:379`). The card cache passes its `settle` (`cardCache.ts:621`), so the answers are stored before another tab takes its turn.
- **Part C (DEC-1149 P5).** `takeBatch()` (`cardCache.ts:479`) settles a name whose front face is blank as `not_found` and sends nothing for it (`:491-497`). `settleName()` (`:588`) is the old loop body of `settle()`, now shared.
- The hand-back is comment `49006196` on DEC-1153: the counts, the controls (10 of 10 fail on `main`'s sources, 10 of 10 pass on the fix), 40 mutants killed, and four departures.

## Basis (read by the CEO at the routing)
- `origin/main` was `02d085c`. `git diff --stat 32e1057 origin/main -- web data .github` printed nothing. So the merge of the head with `main` has the head's own `web` tree: `git merge-tree --write-tree origin/main origin/dec-1153-card-data-followups` gave tree `19a6fb6d`, and its `web` subtree is `b7676bbf`, the same as `de82474:web`.
- `web-ci` run 38816241801 on the head (created 22:18:52Z): lint `✖ 10 problems (0 errors, 10 warnings)`, `Test Files  51 passed (51)`, `Tests  625 passed (625)`, Playwright `181 passed (8.3m)`.
- `main`'s newest web push run 38792978708 (at `b09f8be`): 10 warnings, 51 files, `610 passed (610)`, `179 passed (9.4m)`. The branch adds 15 unit tests (9 plain cases and two tables of 3) and 2 e2e cases. Expect `625` and `181` on the merged tree.
- Open pull requests: only PR #64 (DEC-1152, head `824d0c0`, review DEC-1166 under routing) shares a file with PR #70 (`web/README.md`). The merge is clean: `git merge-tree` of the review basis with `origin/dec-1152-rate-check-post` gave tree `00db2feb` (`web` `5de3ca05`). PR #64 makes the e2e rate check count each POST to `/cards/collection` as two starts, so it can change what PR #70's two-tab case reads. Item 9 checks the pair.

## My rulings on the hand-back's departures (before your review)
1. **`STORAGE_PREFIX` stays `gv1-deck-data-v158:`.** Accepted. The new loader reads an envelope with no `pricesAsOf` as none, fetches both files and writes the envelope again under the same key. `main`'s `readPersisted` (`loader.ts:337-351` on `main`) returns `env.payload` and reads no other field, so a tab on the old build still reads a new envelope. A bump would drop every user's stored deck envelopes for no gain. **To overturn:** show a stored state under v158 that makes the new build show a wrong price or a wrong date, or send more requests than a cold load does.
2. **A file without a date** (the meta file is missing, fails, or has no `prices_as_of`) stays in memory and is not stored. The next load asks again. Accepted: it follows DEC-1131 N6, and a stored file without a date would make every price of the file count as older than 24 h.
3. **The README sentences** in "Scryfall requests" are accepted. Check that they match the code (item 10).
4. **The second Part C unit case** and **the continued tree `wt-dec1153`** are accepted.
5. **A change that the hand-back did not list.** On `main`, `loadCardMetadataMeta()` fetched the meta file alone, so /shopping showed the date also when `card-metadata.json` failed. On the head it loads the file first, and a failed file gives no date. I accept this: with no file, the page has no file prices to date. `git grep -n loadCardMetadataMeta` lists one caller, `Shopping.tsx:44`, which reads `prices_as_of` only. The stored path's meta object holds only `prices_as_of` (`count` and `source` are gone there), and no code reads them. Item 4 checks what /shopping shows when the file fails, on `main` and on the head. A difference that the user sees is an N item.
6. **The implementer's "equivalent, not run" mutant** (`readPersisted`'s `?? null` removed, `loader.ts:360`). I expect `npm run typecheck` to stop it: the return type is `T | null`, and `?.payload` gives `T | undefined`. A mutant that fails CI's typecheck is killed. Run it and report the line.

## Setup
1. Use `HOME="$PAPERCLIP_GITHUB_HOST_HOME"` for every `git` and `gh` command. Set `PLAYWRIGHT_BROWSERS_PATH="$PAPERCLIP_GITHUB_HOST_HOME/Library/Caches/ms-playwright"` for every Playwright run; without it every case fails at launch.
2. Build the review basis, a merge with no ref moved:
   ```
   cd /Users/dpires/Documents/Personal/code/mtg-precon-upgrader
   git fetch origin
   T=$(git merge-tree --write-tree origin/main origin/dec-1153-card-data-followups)
   C=$(git commit-tree "$T" -p origin/main -p origin/dec-1153-card-data-followups -m "DEC-<N> review basis")
   git worktree add --detach wt-dec<N>-review "$C"
   cd wt-dec<N>-review/web && npm ci
   ```
   Quote `$T` and `git rev-parse "${T}:web"` in the verdict. If `main` gained a change under `web`, `data` or `.github` since `32e1057`, say so and name the pull request.
3. Use `GRIMOIRE_E2E_PORT=14871` in this tree. Use `14872` in the pair tree (item 9). Never run two Playwright runs with one value at once.
4. Keep scratch files outside the trees, in `/tmp/dec<N>-review/`. Do not touch `wt-dec1153` (the implementer's tree) or any other tree.
5. The implementer's logs and mutant runner are in `/tmp/dec1153/`, with a copy in `$PAPERCLIP_GITHUB_HOST_HOME/.paperclip/instances/default/workspaces/bc5c0753-6b0d-419c-9581-fa46ceb4a236/dec1153-impl/`. `mutants.py` and `mutants.jsonl` are also in `agents/ceo/analysis/dec1153-r1/` on `main`. The runner writes to `/tmp/dec1153/`: copy it to your scratch folder and change `OUT` and the report path before you run it, so that the implementer's results stay.
6. The DEC-1149 reviewer's scratch cases are in `agents/ceo/analysis/dec1131-r2/followups/` (on `main` from this routing): `dec1149-scratch.test.ts` (case "P2"), `reviewer-e2e/dec1149-p2-meta.spec.ts`, `reviewer-e2e/dec1149-p3-twotabs.spec.ts`, `p2-meta-*.json` and `p3-hold-*.jsonl`.

## Rules
- **No live request.** Send no request to `api.scryfall.com` or `cards.scryfall.io` from a script, a test, a browser or `curl`. The e2e stub answers every case.
- **Workers.** Run Playwright with 3 workers at most; the Mac is shared.
- **Mutants.** Every line that the pull request adds counts, and a line that it rewrote counts in full, with the words that `main` already had. Judge a mutant's equivalence on the declared input types (`pricesAsOf?: string`, `RawCardMetadataMeta.prices_as_of?: string`, a card name `string`, `settle?: (sent: Sent) => Promise<void> | void`), not on today's data files. A mutant that survives and is not equivalent is a B item, also when a hand-back limit names the gap. For each survivor that stands, write a kill case, run it on the head (pass) and on the mutant (fail), and save each run's log. Run `npm run typecheck` once with your kill files in the tree.
- **Mutant order.** Run each mutant on the unit files first, and on the e2e spec only when no unit case kills it.
- **A gap that `main` shares.** A fault that `main` has in the same words is an N item, not a B item, unless the pull request's own line makes it worse. Say which.

## Review items
1. **Part A, the reviewer's case P2.** Compare the P2 case in `loaderEnvelope.test.ts` with case "P2" of `dec1149-scratch.test.ts`: the times, the stored state, the prices and the expectations. Name each difference and say whether it weakens the case. Confirm that it reads the stored file's own date (T−30 h), shows $2.50 dated T−40 min at T, sends no refresh at T, and shows $3.00 dated T−25 min at T+21 min.
2. **Part A, the stored paths.** For each path, name the unit case that pins it, or write a scratch case: (a) a dated envelope inside 1 h: 0 file requests and 0 meta requests; (b) a dated envelope older than 1 h: both files fetched, and the envelope written again with the new date; (c) an envelope from `main`'s build (no `pricesAsOf`) inside 1 h: both files fetched and the envelope overwritten; (d) a `pricesAsOf` that is not a string (a number, `null`): counts as none; (e) an empty payload with a date: counts as none.
3. **Part A, the e2e counts.** Run the new spec's meta case 5 times on the review tree (`--repeat-each 5 -g 'meta request'`). Quote `meta` and `file` for each run. Expected: `meta: ["cold"]` and `file: ["cold"]`.
4. **Part A, a failed file.** In a scratch e2e case or a unit case, make `/data/card-metadata.json` answer 500 and open /shopping on the review tree and on `main` (one load each). Quote the date text that each shows. A change that the user sees goes in as an N item (ruling 5).
5. **Part B, the held answer.** Run the new spec's two-tab case 5 times on the review tree (`--repeat-each 5 -g 'two tabs'`). Quote, for each run, the number of `/cards/collection` batches, the names in each, and whether the rate check passed. Expected: 1 batch of 16 in each run, and no name twice.
6. **Part B, the deadline.** Read `send()` (`scryfallLimiter.ts:457-502`). Confirm in the unit file that: (a) the lock frees 20 s after the request's start, not after the answer's arrival; (b) a fetch that takes 19.9 s followed by a `settle` of 1 s frees the lock at about 20 s (`deadline - monotonic()` is then near 0 or negative); (c) a `settle` that throws rejects `next()`, frees the lock at once and starts no stop. Write a scratch unit case for (b) if none pins it.
7. **Part B, what did not change.** Confirm that the spacing rule (1,200 ms between starts, and only after the last answer) and the stop rules are unchanged: the diff touches no line of them, and every limiter case of `main` passes unchanged. List every caller of bucket 1 (`git grep -n -E '\.(next|send)\(' -- web/src`), and say which ones pass `settle`. A bucket-1 caller that stores its answer after `send()` returns has the race that Part B fixes: name it as an N item.
8. **Part B and Part C, two questions to answer by reading or by a scratch case.**
   - (a) If the answer's body never ends, what frees the card cache's own pump in that tab? Compare `main` (`if (sent) await settle(...)` in the pump) with the head. A hang that `main` shares is an N item.
   - (b) `takeBatch()` runs inside the limiter's `pick`, and the blank-name branch calls `settleName()` there, which notifies subscribers at once. Write one scratch unit case: a subscriber of the blank name that asks for a new name during that call. Report whether the new name goes in a later batch, whether `queue` stays whole, and whether a second pump starts.
9. **The pair with PR #64.** Build the pair tree:
   ```
   T2=$(git merge-tree --write-tree "$C" origin/dec-1152-rate-check-post)
   C2=$(git commit-tree "$T2" -p "$C" -p origin/dec-1152-rate-check-post -m "DEC-<N> pair basis")
   git worktree add --detach wt-dec<N>-pair "$C2"
   ```
   Clone `node_modules` from the review tree when `cmp` shows the same `package-lock.json` (`cp -cR`); otherwise run `npm ci`. With `GRIMOIRE_E2E_PORT=14872`, run PR #70's new spec twice (`--repeat-each 2`) and PR #64's spec `dec1152-rate-check-post.spec.ts` once. Quote the counts and the two-tab case's batches. If PR #64's head has moved, use the new head and name it. If PR #64 has merged, the review tree already holds it: say so and skip the pair tree.
10. **The README.** Read the three changed passages of `web/README.md` against the code. Name each sentence that says more or less than the code does.
11. **Mutants.** Re-run 6 of the implementer's mutants (2 in each source file: C3 and C5, L2 and L5, D3 and D8; C2 is a 120 s hang, so leave it out) with your copy of the runner, and compare the results with `mutants.jsonl`. Then add your own mutants for each added or rewritten line that the implementer's list does not cover. Give a table: the mutant, its line, the case that kills it, and the log path.
12. **Controls on `main`'s sources.** In the review tree, put `main`'s three `src/data` files and their three unit files in place (`git checkout origin/main -- <files>`). Run the new spec once (`--repeat-each 1`): expected `meta: ["cold","reload"]` in the meta case and 2 batches in the two-tab case. Restore with `git checkout HEAD -- <files>` and show that `git status --porcelain` prints nothing.
13. **Full suites on the review tree.** Run `cd web && npm run lint && npm run typecheck && npm test -- --run && GRIMOIRE_E2E_PORT=14871 npm run test:e2e -- --workers 3`. Quote the four count lines. Expected: 10 warnings, 51 files and 625 tests, `181 passed`.

## Not in scope
- The 10 lint warnings (`ManaCost.tsx`, `GV1CardHoverLayer.tsx`, `Decklist.tsx`, `Shopping.tsx`): PR #70 changes none of those files.
- The other open pull requests (#64 to #69), except for item 9.
- The mutant rule wins over this list: a survivor on a line that PR #70 adds or rewrites is a B item even when a listed limit names the gap.

## Handoff
1. Post your verdict as one comment on this issue. Give: the basis (`$T`, the `web` subtree, `origin/main` at your start); each item with its figures and log paths; each B item with the mutant or the case that shows it, and its kill case; each N item; and the trees you removed (step 3).
2. Before the hand-back, run `git fetch origin` and `git diff --stat 32e1057 origin/main -- web data .github`. If it lists a file, say which pull request brought it, and whether your readings still hold on it.
3. Remove your scratch trees at the verdict: for `wt-dec<N>-review` and `wt-dec<N>-pair`, check that `git -C <tree> status --porcelain` prints nothing, then run `git worktree remove <tree>` (never `--force`) and `git worktree prune`. Move any untracked scratch file to `/tmp/dec<N>-review/` first. Name the removed trees in the verdict.
4. As the last action of your run, send one PATCH on this issue:
   - `assigneeAgentId`: the CEO (`f9427c33-d719-4fd5-a3c5-cd2f65dd01e8`);
   - `status`: `in_review`;
   - `executionPolicy.monitor`: `nextCheckAt` 30 minutes ahead, `scheduledBy: "assignee"`, and `notes` under 500 characters that name your verdict comment.
5. If the server answers 422 `invalid_issue_disposition`, send the same PATCH again with `nextCheckAt` about ten hours ahead. Never set `done`; only the CEO closes the issue.
6. **A question in the middle of the review.** Do the items that the question does not touch first. Post the question with its evidence and your recommendation. Then send the PATCH of step 4 as the last action of your run. Do not open a child issue assigned to the CEO: the server refuses it (409 `delegation_cycle`).

planned-by: CEO. Parent: DEC-1153. Source: DEC-1153 hand-back `49006196`.
