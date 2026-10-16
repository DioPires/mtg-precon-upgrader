## Verdict: CHANGES (2 B items, 4 N items)

Parts A, B and C do what the brief says. Every count matches: 625 unit tests, 181 e2e passed, 1 batch of 16 in each two-tab run, `meta: ["cold"]` in each meta run. The controls on `main`'s sources fail as expected. Two B items come from the mutant rule. Four of my own mutants survive on lines that the pull request adds or rewrites, and none of the four is equivalent. Both fixes are small. B2 needs only a test, and B1 needs a test and possibly a 2-line change.

- **B1, a meta file with `prices_as_of: ""`.** Three mutants survive: U-D1 (`loader.ts:439`), U-D2 (`:425`) and U-D6 (`:372`). The declared type `prices_as_of?: string` allows `""`. The head stores the file with `pricesAsOf: ""` and reads it from storage for 1 h with no request. Each mutant leaves that file unstored or unread, so the next load inside 1 h fetches both files again. Kill case K1 passes on the head and fails on each of the three mutants.
- **B2, a failed `card-metadata.json`.** Mutant U-D11 (`loader.ts:432`) adds `.catch(() => null)` to the file fetch, and it survives. With it, a 500 or a rejected fetch loads every page without the file, and the cache then looks up every deck card on Scryfall. The head shows the error page instead. The pull request rewrote this line (`main`: `cached ?? fetchJson<RawCardMetadata>(...)`), so the mutant rule counts it. `main`'s suite has the same gap: the same mutant on `main`'s sources survives, with 281 of 281 tests passed (`main-UD11.log`). The code is no worse than `main`. Kill case K2 (2 cases) passes on the head and fails on the mutant.

My recommendation:
- **B2:** commit K2 as it is.
- **B1:** pick one of two fixes.
  - (a) Commit K1 as it is. K1 pins the head's behaviour.
  - (b) Count a date that `Date.parse` cannot read as no date, on both checks (`:425` and `:439`), and invert K1 to expect `[2, 2]` and no envelope. I prefer (b). Ruling 2 refuses to store an undated file, and `""` is an undated file. On both the stored path and the cold path, `seed()` already reads `""` as no date.

All logs are in `/tmp/dec1170-review/`. A copy is in `/Users/dpires/.paperclip/instances/default/workspaces/bc5c0753-6b0d-419c-9581-fa46ceb4a236/dec1170-review/`. The scratch and kill files are in `scratch/`: `dec1170-loader-scratch.test.ts` and `dec1170-limiter-scratch.test.ts` go in `web/src/__tests__/dec1170/` byte for byte, and `e2e/dec1170-scratch.spec.ts` goes in `web/tests/`.

## Basis
- `origin/main` was `ae9e33f` at my start (22:37Z) and `a4cd315` at the hand-back (22:51Z). Both times, `git diff --stat 32e1057 origin/main -- web data .github` printed nothing. My readings hold on `a4cd315`.
- `T` = `749ed6567b4f1394169a18aecc029fe9b02af137`, and `git rev-parse "${T}:web"` = `b7676bbfab4e4fa44ba5b22480aad49ea3aae59f`, which equals `de82474:web`. `T` differs from the CEO's `19a6fb6d` only because `main` moved outside `web`, `data` and `.github`. The review commit is `4f04597` (no ref).
- Pair tree: `T2` = `110860436d99e07058c0be5b56c28e7047de89f3`, `web` = `5de3ca0512da2609f55bc72562ae475bf4456b9c`, the CEO's value. PR #64's head is still `824d0c0`, and the pull request is open.

## Items
**1. P2 case: the PR's case against the DEC-1149 reviewer's case.** The times are the same: visit 1 at T−40 min, visit 2 at T and visit 3 at T+21 min, with the old date T−30 h and the new date T−25 min. The prices are the same: $1.42 in the file, $2.50 from the refresh and $3.00 in the new file. The stored state is split the same way, with one storage for the loader and one for the cache and the limiter. Only the variable names differ. These are the differences:
- At visit 2, the reviewer's case expected the bug ($1.42 dated with the new date). The PR's case expects the fix: $2.50 dated T−40 min.
- The PR's case counts the meta requests as well as the file requests (`[1, 1]` at visit 2 and `[2, 2]` at visit 3). The reviewer's case counted file requests only.
- The PR's case also reads `loadCardMetadataMeta()` at visit 2 and gets `OLD_DATE`.
- For URLs other than the two files, the PR's fetch answers `payloadFor(url)` and the reviewer's answers `{}`. Neither case requests another URL.

No difference weakens the case, and the three additions make it stronger. The case checks all four points of the brief: it reads the stored file's own date (T−30 h), shows $2.50 dated T−40 min at T, sends no refresh at T (`scry.sends` stays 1 after 10 s), and shows $3.00 dated T−25 min at T+21 min.

**2. The stored paths.**
- (a) A dated envelope inside 1 h gives 0 file and 0 meta requests. It is pinned by "a cold load sends 1 meta request and stores the date; a load from storage sends none and seeds that date".
- (b) An envelope older than 1 h: R15 pins that the file comes again, and P2's visit 3 pins `[2, 2]` and the new date in the cache. No committed case reads the envelope written again. My scratch case 2b shows that the envelope is written again with `fetchedAt` = now and `pricesAsOf` = the new date, and that a load 30 min later sends nothing and seeds the new date. 2b passes on the head.
- (c) An envelope from `main`'s build, with no `pricesAsOf`, inside 1 h: pinned by "takes an envelope from before DEC-1153 (no date) for none" (`[2, 2]`, and the envelope is overwritten with the date).
- (d) A `pricesAsOf` that is not a string: no committed case pins it. My scratch case 2d tries a number, `null` and an object. Each counts as no date: both files are fetched, the seed gets the meta date, and the envelope is written again. 2d passes on the head. See N3.
- (e) A date with an empty payload: pinned by "an envelope with a date and an empty file" (`{}`) and "... and no file" (`null`).

The scratch cases are in `scratch/dec1170-loader-scratch.test.ts`. Their logs are `scratch-head.log` (11 of 11 passed, before I added K2) and `scratch-main.log` (11 of 11 failed on `main`'s sources, as a control).

**3. The e2e meta case, 5 runs.** All 5 runs passed (`e2e-meta-x5.log` and `.json`). The case asserts `{meta, file}` = `{meta: ["cold"], file: ["cold"]}`, so each run read `meta: ["cold"]` and `file: ["cold"]`. My scratch copy R3 records the values in an annotation, and it read `{"meta":["cold"],"file":["cold"]}` (`e2e-scratch-head.json`).

**4. A failed file on /shopping, one load each on the head and on `main`.** The case is R4 in `e2e/dec1170-scratch.spec.ts`.
- **500:** the head and `main` both show the alert "Could not scry the codex /data/card-metadata.json: HTTP 500". Neither page shows a footer or a date, so the user sees no change, and ruling 5 holds.
- **404 (an extra case):** both builds show "Prices are USD from Scryfall, as of 15 Oct 2026." The date comes from the lookups' answers on both. The request count differs; see N2.
- Logs: `e2e-scratch-r4-head.json` and `e2e-scratch-main.json`.

**5. The e2e two-tab case, 5 runs.** All 5 runs passed. Each run sent 1 `/cards/collection` batch of 16 names, at 533, 568, 511, 437 and 445 ms. The rate check passed in each run: peak 1 start a second, 0 answered 429, and no fixture error (`e2e-twotabs-x5.json`). The spec's annotation holds only `at` and `n`, so I took the names from my scratch copy R5, which follows the same steps. R5 sent 1 batch at 413 ms, with no name twice: Clara Oswald, Crumbling Sanctuary, Panoptic Projektor, The Masamune, Arm-Mounted Anchor, Bontu's Monument, Well of Lost Dreams, Excalibur II, Unassuming Gelatinous Serpent, Elemental Time Flamingo, Relic Vial, Charmed Pendant, Convergence of Dominion, Eden, Seat of the Sanctum, Excavated Wall, Leyline Dowser.

**6. The deadline in `send()`.**
- (a) Pinned by "a caller that never settles frees the other tab's turn 20 s after its own start". The answer arrives at 150 ms, and the other tab starts at exactly 20,000 ms. A deadline counted from the answer would give 20,150 ms. My mutant U-L1 (the deadline taken after the fetch) fails that case.
- (b) No committed case pins it, so I wrote scratch case 6b. In one run the fetch takes 19,900 ms and `settle` takes 1,000 ms. In the other, the fetch takes 19,999 ms and `settle` 1,000 ms. In both runs the other tab starts at 20,000 ms, and `next()` resolves when `settle` ends (at 20,900 and 20,999 ms). 6b passes on the head and fails on `main`'s sources. The time left before the deadline is +100 ms and +1 ms. It goes below 0 only in real time, and `setTimeout` treats a delay below 0 as 0.
- (c) Pinned by "a `settle` that throws rejects next() and frees the turn at once, with no stop". The other tab starts at 1,200 ms (the spacing), and no stop record exists. My mutant U-L4 (`Promise.resolve(job.settle!(sent))`) fails that case.

**7. What did not change.**
- The `scryfallLimiter.ts` hunks are at lines 19–21 (comment), 104–110, 149, 378–386, 476, 496–501 and 539–547. None of them touches `waitFor`, `markStart`, `sharedLastStart`, `waitForTurn`, `withLock`, `drain`, `fail`, `succeed`, `readStop`, `storeStop` or `fetchWithTimeout`.
- `scryfallLimiter.test.ts` only gains lines (0 removed), so every limiter case of `main` runs unchanged, and all pass in the 625.
- Bucket 1 has one caller: `cardCache.ts:612` `limiter.next('lookup', …, { settle })`, which passes `settle`. `cardAtlas.ts:153` is bucket 2 (autocomplete). `PricePausedLine.tsx` reads only `stoppedUntil` and `subscribe`. No caller stores an answer after `send()` returns, so there is no N item here.

**8a. An answer whose body never ends.** Nothing frees the tab's own pump, on `main` or on the head. The limiter clears its timeout when the headers arrive, so `response.json()` is not aborted. My scratch case 8a sends A1 from tab A with a body that never ends. A1 stays `loading`, and A2, asked at 31 s, is never sent, on both builds. On the head the other tab's batch goes at 20,000 ms; on `main` it goes at 1,200 ms. The hang is shared with `main`, so it is N1.

**8b. A subscriber of a blank name that asks for a new name during the call.**
- With another name in the batch, the batches are `[["Arcane Signet"], ["Fresh Name"]]`, at 0 and 1,200 ms.
- When the blank name is alone, the batches are `[["Fresh Name"]]` at 0 ms. The blank-only turn picks nothing and starts nothing, and the next turn takes the new name. The result is the same when the new name is asked with `first`.
- The subscriber heard `not_found` once. At most 1 `next()` call was out at a time, so one pump ran. A later name went alone in the next batch, so `queue` stayed whole.
- On `main`'s sources, the blank name goes out as `""` (control).

**9. The pair with PR #64.** PR #70's spec, run twice, gave 4 passed. In each run the two-tab case sent 1 batch of 16 (at 520 and 373 ms). PR #64's rate check counts each POST as two starts, so it read a peak of 2 starts a second, which is at the limit, not over it. The meta case passed with a bucket-1 count of 2 and a peak of 2. PR #64's spec `dec1152-rate-check-post.spec.ts` gave `7 passed (6.1s)`: 7 expected and 0 unexpected, with six `test.fail()` cases that failed as designed. Logs: `e2e-pair-pr70-x2.*` and `e2e-pair-pr64.*`.

**10. The README.** See N4.
- The blank-name sentence matches the code.
- The sentence "fetches `card-metadata.meta.json` only with the file" matches the code.

**11. Mutants.** I ran my copy of the runner (`/tmp/dec1170-review/mutants.py`). It writes `mutants.jsonl` and writes reports to `mut/mut-<id>.json`. The 6 re-runs match `mutants.jsonl` in each count and each case.

| Mutant | Line | Result: the case that kills it | Log |
|---|---|---|---|
| C3 (re-run) | cardCache.ts:494 | killed, 1: "a price and a picture refresh of a blank name of the file…" | mut/mut-C3.json |
| C5 (re-run) | cardCache.ts:495 | killed, 1: "reads not_found with no request…" | mut/mut-C5.json |
| L2 (re-run) | scryfallLimiter.ts:497 | killed, 63 (first: /shopping price refresh) | mut/mut-L2.json |
| L5 (re-run) | scryfallLimiter.ts:500 | killed, 1: "next() resolves with the answer after `settle`…" | mut/mut-L5.json |
| D3 (re-run) | loader.ts:425 | killed, 1: "an envelope with a date and no file" | mut/mut-D3.json |
| D8 (re-run) | loader.ts:429 | killed, 4 | mut/mut-D8.json |
| **U-D1** `typeof meta?.prices_as_of === 'string'` → `meta?.prices_as_of` | loader.ts:439 | **survived**; killed by K1 | mut/mut-U-D1.json, kill/kill-U-D1.log |
| **U-D2** `typeof stored?.pricesAsOf === 'string'` → `stored?.pricesAsOf` | loader.ts:425 | **survived**; killed by K1 | mut/mut-U-D2.json, kill/kill-U-D2.log |
| **U-D6** `pricesAsOf !== undefined` → `pricesAsOf` | loader.ts:372 | **survived**; killed by K1 | mut/mut-U-D6.json, kill/kill-U-D6.log |
| U-D7 `if (true) env.pricesAsOf = …` | loader.ts:372 | survived, **equivalent**: `env` goes only to `JSON.stringify`, which drops a field whose value is `undefined` | mut/mut-U-D7.json |
| U-D10 `length > 0` → `> 1` | loader.ts:425 | killed, 4 | mut/mut-U-D10.json |
| **U-D11** `.catch(() => null)` on the file fetch | loader.ts:432 | **survived**; killed by K2 (2 cases) | mut/mut-U-D11.json, kill/kill-U-D11.log |
| U-D12 no date passed to `writePersisted` | loader.ts:439 | killed, 7 | mut/mut-U-D12.json |
| U-D13 `catch` returns `memCardMetadataMeta` | loader.ts:450 | survived, **equivalent**: `memCardMetadataMeta` is set only together with a non-empty `memCardMetadata` and cleared with it, so it is `null` whenever `loadCardMetadata()` throws. The test-only `_reset()` is the one exception. | mut/mut-U-D13.json |
| U-D15 a fixed date in the stored path's meta | loader.ts:427 | killed, 2 | mut/mut-U-D15.json |
| Ruling 6: `?? null` removed | loader.ts:360 | killed by typecheck (exit 2): `src/data/loader.ts(360,5): error TS2322: Type 'T \| undefined' is not assignable to type 'T \| null'.` | typecheck-ruling6.log |
| U-L1 the deadline taken after the fetch | scryfallLimiter.ts:476 | killed, 1: "a caller that never settles…" | mut/mut-U-L1.json |
| U-L2 / U-L3 the deadline +1 ms / −1 ms | scryfallLimiter.ts:476 | killed, 1 each (the same case) | mut/mut-U-L2.json, mut-U-L3.json |
| U-L4 `Promise.resolve(job.settle!(sent))` | scryfallLimiter.ts:499 | killed, 1: "a `settle` that throws…" | mut/mut-U-L4.json |
| U-L5 `finish` before `settle` ends | scryfallLimiter.ts:500 | killed, 3 | mut/mut-U-L5.json |
| U-L7 `setTimeout(resolve, 0)` | scryfallLimiter.ts:382 | killed, 2 | mut/mut-U-L7.json |
| U-L20 / U-L21 / U-L22 the job literal: `done: true` / `signal: undefined` / `request` preset | scryfallLimiter.ts:544 / 542 / 541 | killed, 110 / 2 / 95 | mut/mut-U-L20.json … U-L22.json |
| U-C1 `now()` → `0` in the blank branch | cardCache.ts:495 | killed, 2 | mut/mut-U-C1.json |
| U-C2 status `200` → `0` in the blank branch | cardCache.ts:495 | survived, **equivalent**: when `answered` is true, `settleLookup` does not read `status`, and `settlePrice` and `settlePictures` take no status | mut/mut-U-C2.json |
| U-C3 `status` → `200` in `settle()` | cardCache.ts:583 | killed, 5 | mut/mut-U-C3.json |
| U-C6 / U-C7 `settlePrice` / `settlePictures` with `null` | cardCache.ts:590 / 591 | killed, 17 / 5 | mut/mut-U-C6.json, mut-U-C7.json |
| U-C8 `void settle(...)` | cardCache.ts:621 | killed, 1: the two-tab unit case | mut/mut-U-C8.json |
| U-C10 `batch.length >= 0` | cardCache.ts:617 | killed, 5 | mut/mut-U-C10.json |
| U-C11 `taken.batch = batch` removed | cardCache.ts:616 | killed, 60 | mut/mut-U-C11.json |

Kill runs use `npx vitest run dec1170-loader-scratch.test.ts -t 'K1|K2'`. On the head, `kill/kill-head.log` reads 3 passed (K1 and the two K2 cases). On U-D1, U-D2 and U-D6, K1 fails. On U-D11, both K2 cases fail (`kill/killrun.out`). `npm run typecheck` with my scratch and kill files in the tree exited 0 (`typecheck-with-kill-files.log`).

**12. Controls on `main`'s sources.** I put the three `src/data` files and the three unit files of `main` in place in the review tree.
- The meta case failed with `meta: ["cold","reload"]` and `file: ["cold"]`.
- The two-tab case failed with 2 batches of 16 (at 410 and 1,919 ms) that held the same 16 names.
- Logs: `e2e-control-main.log` and `.json`.
- I restored the files with `git checkout HEAD -- <the 6 files>`. `git status --porcelain` then listed only my scratch spec `web/tests/dec1170-scratch.spec.ts`. After I removed that file (its copy is in `/tmp`), the command printed nothing.

**13. Full suites on the review tree.**
- Lint: `✖ 10 problems (0 errors, 10 warnings)`.
- Typecheck: exit 0.
- Unit: `Test Files  51 passed (51)` and `Tests  625 passed (625)`.
- e2e: `181 passed (3.0m)`.
- Logs: `full-lint.log`, `full-typecheck.log`, `full-vitest.log` and `full-e2e.log`.

## N items
- **N1 (shared with `main`).** A `/cards/collection` answer whose body never ends leaves the tab's card cache waiting forever (scratch 8a). In that tab no later name is sent until a reload. A possible fix is to keep the abort armed until `settle` has read the body. The pull request does not make this worse in the tab. The other tab now waits until 20 s after the start, by design.
- **N2.** When `card-metadata.json` answers 404, /shopping on the head fetches the file and the meta file twice each (4 requests), and `main` fetches each once (2 requests). The cause is that `loadCardMetadataMeta()` now calls `loadCardMetadata()`, and a missing file is not kept. The page and its date look the same on both builds. The extra requests go to our own origin, not to Scryfall.
- **N3.** No committed case pins a stored `pricesAsOf` that is not a string. The `typeof` check is equivalent to `!== undefined` on the declared type, so this is not a B item. Scratch case 2d passes on the head, and committing it is optional.
- **N4 (README).**
  - The card-cache passage says less than the code. It does not say that a file without a date stays in memory and is not stored, so the next load asks again.
  - The bucket-1 sentence "so the next tab's batch finds those names in storage" says more than the code. That is true only after a 200. After a 400 or a 422, the card cache keeps the error in that tab's memory only, so the other tab asks again.
  - Line 222 is 137 characters long. The rest of the passage wraps at about 95.

## Trees
I removed `wt-dec1170-review`, `wt-dec1170-pair` and `wt-dec1170-mut`. The third tree was a scratch tree at the review commit `4f04597`, so the mutant runs could run beside the e2e suite. Before each removal, `git status --porcelain` printed nothing. I then ran `git worktree remove` without `--force`, and `git worktree prune`. I did not touch `wt-dec1153`.
