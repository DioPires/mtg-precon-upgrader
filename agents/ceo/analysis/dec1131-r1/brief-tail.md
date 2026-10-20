
- **Basis (my checks at 15:05Z).** `origin/main` is at `b703bde`; after `4fdcbb8` (PR #53) it changed only `agents/ceo/`.
  - The guard `git diff --stat "$(git merge-base 73f6fd5 origin/main)" origin/main -- web data scripts .github` printed nothing.
  - `git merge-tree --write-tree origin/main 73f6fd5` was clean (`48768473`). Its `web` tree (`a58b787f`) equals the head's, and its `data` tree (`91f3743e`) equals the head's and `main`'s. So the head is the merged tree for `web` and `data`.
- **CI on the head.** `web-ci` run 38753572964 (pull_request, created 14:41Z): lint `✖ 10 problems (0 errors, 10 warnings)`; vitest `Test Files  44 passed (44)` and `Tests  548 passed (548)`; Playwright `1 flaky` and `162 passed (12.7m)`. The flaky case is `dec1083-shop-import-keyboard.spec.ts:42`, which is older than this branch; DEC-1144 fixes its wait.
- **`main`'s basis.** Push run 38751901902 on `4fdcbb8`: lint `0 errors, 10 warnings`; vitest `43 passed (43)` files and `475 passed (475)` tests; Playwright `150 passed (12.5m)`. The branch adds 1 test file, 73 unit tests and 13 e2e cases.
- **The kit.** `/Users/dpires/Documents/Personal/code/mtg-precon-upgrader/agents/founding-eng/analysis/dec1131/` holds `mutants/` (`apply_mutant.py`, `run_mutants.py`, `M1.log` to `M16.log`), `measure/` (`main/` and `branch/`, each with `measure.spec.ts`, `storage.spec.ts` and two configs; `out-main/`, `out-branch/`, `table.md`), `census/` (`census.py`, `census.md`), `n7/` and `flake-dec1083/`. Read the kit and write nothing there. Copy what you run into `/tmp/dec<N>/`. The copies name the implementer's tree (`wt-dec1131`) and port (14751): change each to yours, and quote the changed lines in the verdict.

## Open pull requests that touch the same files
- **PR #60** (DEC-1141, `af1f93b`) changes `Shopping.tsx` and `Shopping.test.tsx`. Its merge tree with `73f6fd5` is clean. Item 12 runs the three together.
- **PR #50** (DEC-1116, `ec38926`) and **PR #56** (DEC-1046, `b2f030b`) change `web/src/styles/styles.css`, in other hunks. Both merge trees with `73f6fd5` are clean.
- PR #51, PR #55 and PR #59 share no file with this branch.
- Any of them can merge during your review. Setup step 3 tells you what to do then.

## Rules for this leg
1. **No live request.** Send no request to `api.scryfall.com` or `cards.scryfall.io` from a script, a test, a browser or `curl`. The stub answers every e2e case. Do not use the card tools or `scripts/card_lookup.py`.
2. **No unit suite without the guard.** Run no vitest suite on a tree that lacks this pull request's `web/src/setupTests.ts` guard. The hand-back says that `main`'s /shopping unit cases can send `/cards/named` lookups to the live API (deviation 1). P4 counts them with a recorder in place of `fetch`.
3. **Environment.** Export `HOME="$PAPERCLIP_GITHUB_HOST_HOME"` for every `git` and `gh` command. Export `PLAYWRIGHT_BROWSERS_PATH="$PAPERCLIP_GITHUB_HOST_HOME/Library/Caches/ms-playwright"` for every Playwright run; without it every case fails at launch.
4. **Ports.** Set `GRIMOIRE_E2E_PORT=14781` on every e2e run in your review tree, and 14782 in a second tree. A run accepts only the preview server that it started, and a second run with the same value stops at once.
5. **Trees.** Work in your own trees (Setup). Do not touch `wt-dec1131` or `wt-dec1131-main` (the implementer's), `wt-dec1046*` or `wt-dec1116`. Keep scratch files, scratch configs and kill drafts in `/tmp/dec<N>/`, outside the trees.
6. **Sizes.** A new case that reads a size reads it after `document.fonts.ready` and runs once with the fonts live and once with `test.use({ fonts: 'blocked' })`; quote both. A screenshot uses `animations: 'disabled'`.
7. **The Mac is shared.** Run one Playwright process at a time, with `--workers 3` or fewer.
8. **Equivalence.** Judge a mutant's equivalence on the declared input types, not on today's data files.

## Setup
1. `cd /Users/dpires/Documents/Personal/code/mtg-precon-upgrader && git fetch origin`
2. `git worktree add --detach wt-dec<N>-review 73f6fd5e28e3f6f8e5126db7d0b3ca50a37c165b`
3. In that tree, check the 31 blob ids of the table. Then run the guard: `git diff --stat "$(git merge-base HEAD origin/main)" origin/main -- web data scripts .github`. If it prints anything, run `git merge --no-ff --no-edit origin/main` (a local merge commit; push nothing), name the pull requests that came in, and run every item on the merged tree.
4. `cd web && npm ci`, then `mkdir -p /tmp/dec<N>`.

## Rulings I have made
Give your word on each. Overturn one only with evidence: a fault that a user of the app would see, or a request pattern that Scryfall would count against the address. R1 to R17 are the hand-back's deviations 1 to 17.
- **R1 (the fetch guard in `setupTests.ts`).** Accepted. A case that wants an answer spies on `globalThis.fetch` or gives the limiter its own `fetch`.
- **R2 (Vitest fakes `performance`).** Accepted. `vi.setSystemTime()` still moves only `Date`, so delta N1 and N4 can model a step of the wall clock.
- **R3 (a price with no date counts as older than 24 h; the loader fetches the meta file beside the file).** Accepted. P2 reads its cost.
- **R4 (the overlay holds only the changed fields).** Accepted. Item 3e checks that a PR #38 picture entry still reads correctly.
- **R5 (a 400 or 422 holds the lookups 30 s in memory and the refreshes 24 h).** Accepted. It is what ruling 4 asked: one 404 on `main` holds a lookup 30 s in memory.
- **R6 (the stop line renders only while a stop holds).** Ruling 2 of the brief gives you the style. P1 asks for your call.
- **R7 (the estimate changes once).** Accepted. The summary holds while a buy row's refresh waits or is out, and a new selection recomputes at once.
- **R8 (with no priced row the footer shows the file's date).** Accepted.
- **R9 (/combos shows glyphs in e2e).** Accepted. The stub knows only the file's names, and all 16 names of the /combos batch are outside the file. The unit cases and case A1 show the art of a batch answer.
- **R10 (the first-paint count by a MutationObserver).** Accepted.
- **R11 (the PR #38 specs set `page.clock`; the /combos 429 case uses `scryfall429From: 1`; the two-tab case allows 2 batches and each name twice).** Accepted. P3 reads the two-tab case.
- **R12 (your kill cases moved to batches and to the stop number).** Accepted if each still kills its mutant (item 9).
- **R13 to R16 (the stub still answers `/cards/named`; the option is named `scryfallUsdBump`; the /shopping stop case holds the request after the stop with its own route; the extra e2e cases).** Accepted.
- **R17 (the hover sends 4 batches, not 1).** Accepted. A wait that collects names would delay every hover, and the peak stays at 1 in 1 s.
- **R18 (the shape of the stub's 422 is a guess).** A known limit. Say whether any kill of M2 rests only on that shape.
- **R19 (the preflight).** The hand-back reads that neither a Playwright route nor `context.on('request')` sees Chromium's preflight, so the rate check counts the POST only. Accepted on that reading: with 1,200 ms between POSTs, a POST and its preflight give at most 2 starts in any 1 s. Item 6d tests the reading.
- **R20 (`STORAGE_PREFIX` stays `v158`).** Accepted. The loader persists the same shapes; it only stops persisting a failed or empty file, and it reads an empty stored file as none.
- **R21 (option B).** The owner's card `116a1d02` is still open, so the tile's refresh (`CardTile.tsx:96`) stays.
- **The mutant rule wins over R1 to R21.** A survivor on a line that this pull request adds or rewrites is a B item, even when a ruling names its gap. A line that the pull request rewrote counts in full, with the words that `main` already had. You can strike a survivor by showing that it is equivalent.

## Points with no ruling yet
For each point, give the reading and call it B or N. B means a fault that a user would see in a plausible case, more than 2 bucket 1 requests in 1 s from one browser, or a request from a test to a Scryfall host.
- **P1. The stop line appears with its text.** `PricePausedLine` renders `<p role="status">` only while a stop holds. Many screen readers do not announce a live region that enters the page with its text already in it. The implementer chose this because a second permanent `role="status"` broke the import cases' `getByRole('status')`. Give your call: keep it, or a region that is always present (and the change that the import cases then need). Rule on the words and the style as well. The date is in UTC (`formatPricesDate`), and the clock time is in the browser's zone (`clockTime`). Take a screenshot of the line at 390 px and at 1440 px, with the fonts live and blocked. I expect N.
- **P2. The meta file beside a stored file.** The loader keeps `card-metadata.json` 1 h under `gv1-deck-data-v158:`. It fetches `card-metadata.meta.json` on each cold load and stores it nowhere. After a deploy that changes the file but not `STORAGE_PREFIX`, a visit in the next hour pairs the old prices with the new date. Those prices then count as younger than 24 h, and they win over a stored refresh. Show it in a scratch unit case. Also count the requests to `/data/card-metadata.meta.json` on one deck guide, on `main` and on the head. I expect N with a follow-up: no workflow refreshes the file today, and PR #32 bumped the prefix.
- **P3. Two tabs at one batch.** Bucket 1's lock frees when `send()` returns. `settle()` writes the answers later, after `await response.json()`. When an answer takes longer than 1,200 ms, the other tab can take its turn before those writes and send the same names. Run the two-tab /combos case of `tests/dec1102-card-data.spec.ts` with `--repeat-each 10`, and give the batches of each run and the names that went twice. Then hold each `/cards/collection` answer 1.5 s with a scratch route (`route.fallback()` after the wait), and run it 5 times. A name that goes twice is N unless the rate check fails; say what fix you see.
- **P4. `main`'s unit suite and the live API.** Do not run `main`'s suite as it is (rule 2). In a scratch tree at `origin/main`, add a setup file that replaces `fetch` with a recorder: it counts each call to a Scryfall host and rejects it, as this pull request's guard does. Run the suite once and give the count and the test files. This tells me whether the open trees without the guard send live requests today. It is N for this pull request either way.
- **P5. A batch that Scryfall refuses.** A 400 or 422 fails or holds every name of its batch. Read each path that builds an identifier (`identifierOf()`, `frontFace()`), and say whether the app can send an empty or malformed name, for example a name that starts with `//`. If it can, one such name fails 74 others for 30 s at a time. I expect N.

## Items
For each item, quote the command and the reading.

1. **Scope.** The three-dot diff lists the 31 files and nothing else, the 31 blob ids match, and Setup step 3's guard (and the merge, if any).
2. **The four checks on your tree.** `npm run lint && npm run typecheck && npm test -- --run && GRIMOIRE_E2E_PORT=14781 npm run test:e2e -- --workers 3` in `web/`. Expected: `✖ 10 problems (0 errors, 10 warnings)`; typecheck exit 0; `Test Files  44 passed (44)` and `Tests  548 passed (548)`; `163 passed`. The 11 `✘` lines are `test.fail()` cases, and Playwright counts them as passed. For a flaky case other than `dec1083-shop-import-keyboard.spec.ts:42`, name it and run it again with `--repeat-each 10`.
3. **The brief against the code.** For each of rulings 1 to 8 of the DEC-1131 brief, and for notes N2 to N7, H7 and delta N1 to N4, give the file and the lines that do it, and a unit or e2e case that fails when it breaks. Check in particular:
   a. `takeBatch()`: the order (names asked `first`, then lookups, then refreshes); the cap of 75 counts identifiers; two names with one front face share one identifier.
   b. A batch that meets a 429, a rejected `fetch` or the timeout goes again first with the same body (`send()` puts the job back at the front, and `job.request` stays). Names that arrive during the stop wait for the next batch.
   c. The answer is matched by `normalizeName()` on the full name and on the front face. Write a scratch unit case whose answer gives `data` in reverse order and holds a `//` card that the app asked for by its front face. It must pass on the head.
   d. `not_found` holds 24 h in storage, also for a new cache on the same storage. A 400 or 422 holds a lookup 30 s in memory and a refresh 24 h.
   e. The refresh: `refreshPrice()`; `compose()` (the file's price wins when `file.priceAsOf >= overlay.priceAsOf`); `seed()` keeps a live overlay; a PR #38 picture entry (`refreshedAt` with pictures, no `priceCheckedAt`) still reads correctly.
   f. The limiter: the timeout flag; a caller's abort stays no failure; the stop number (your K1 and K2); an old record (N4); the cap in memory (delta N1); the spacing inside a tab on `performance.now()` (delta N4).
   g. The callers: `git grep -n -E 'refreshPrice\(|pricePending\(' HEAD -- web/src ':!web/src/__tests__'` lists `CardTile.tsx:96` and `Shopping.tsx:275`, `:373` and `:455` outside `cardCache.ts`, and nothing else.
4. **The census.** `git grep -n -E 'api\.scryfall\.com|format=image|/data/images/cards|/cards/named' HEAD -- web/src` must print the hand-back's 17 lines. Also run `git grep -n -E 'fetch\(' HEAD -- web/src ':!web/src/__tests__'`, and name every `fetch` that can reach a Scryfall host.
5. **The mutant run.**
   a. Copy `mutants/apply_mutant.py` and `mutants/run_mutants.py` to `/tmp/dec<N>/`, point them at your tree and port 14781, and run M1 to M16. Compare each count line with the hand-back's table. `git status --porcelain` must print nothing after each one.
   b. **Seed mutants.** Run each one on the unit suite first, and on the e2e spec that should catch it only when the unit suite does not kill it. Restore the file after each one.
      - S1, `takeBatch()`: refreshes rank before lookups (`w.lookup ? 1 : 2` becomes `w.lookup ? 2 : 1`).
      - S2, `takeBatch()`: identifiers are keyed by the name asked, not by the folded front face (`const id = normalizeName(identifier)` becomes `const id = wanted.key`).
      - S3, `settle()`: each card of the answer is indexed under its full name only (`nameKeys(card.name)` becomes `[normalizeName(card.name)]`).
      - S4, `compose()`: the stored refresh always wins (`!fileIsNewer` becomes `true`).
      - S5, `seed()`: no overlay stays (`overlayIsLive(overlay)` becomes `false`).
      - S6, `settlePrice()`: `priceCheckedAt` is written only when the answer has a price.
      - S7, `useHeldPriceSummary()`: it never holds (`waiting` becomes `false`).
      - S8, `PricePausedLine`: no timer at the stop's end (remove the second `useEffect`).
      - S9, `isApiUrl()`: `return true;`.
      - S10, `fetchWithTimeout()`: the caller's abort is not passed on (remove the `signal?.addEventListener('abort', forward, ...)` line).
      - S11, `send()`: a batch that met the stop goes last (`bucket.jobs.unshift(job)` becomes `bucket.jobs.push(job)`).
      - S12, `loadCardMetadata()`: the seed gets no date (`meta?.prices_as_of` becomes `undefined`).
      - Add your own mutants on lines that the pull request adds or rewrites, the harness included.
   c. **A control that must survive.** Make the stub's `collection()` give `data` in reverse order. Every case must still pass. That shows that no case leans on the order of the answer.
   d. For each survivor that stands, write a kill case and run it: it passes on the head and fails on the mutant. Run `npm run typecheck` and `npx eslint` with your kill files in the tree, because vitest does not typecheck. Save the log of each run, and give its path.
6. **The harness.**
   a. **A control for the rate check.** Set `LOOKUP_SPACING_MS` to 100, and run `tests/dec1131-card-batches.spec.ts` and `tests/dec1102-card-data.spec.ts`. Quote the rate check's message for each case that fails. Restore the file.
   b. **H7.** In the same control, a case under `rateClock: 'page'` that sends batches fails with "the page's clock" in the message.
   c. **N2.** Say which case kills M16, and whether any other case holds an answer with its own route and so needs the browser's send time.
   d. **The preflight.** In a scratch case, open a CDP session (`context.newCDPSession(page)`, then `Network.enable`), and log `Network.requestWillBeSent` for one batch POST under the stub. Say whether Chromium sends an `OPTIONS` request that neither the route nor `context.on('request')` shows.
   e. **The 422.** One scratch case sends 76 identifiers to the stub. Quote the answer.
7. **The table (item 9 of the DEC-1131 brief).** Run the implementer's `measure.spec.ts` on your tree for these rows: shopping, combos, deck-creeping-corruption, mobile, deck-eternal-harvest, hover-apothecary-300 and hover-codex-300. Compare each cell with the hand-back's branch column. Every price of the file is older than 24 h after 15 Oct 11:17:46Z, so the head refreshes. A lookup count that is not 0 where the hand-back reads 0, or a peak above 2 in 1 s, is a B item. The hover's split into batches can move.
8. **Storage.** Run the implementer's `storage.spec.ts` on your tree. Expected after `/deck/creeping-corruption`: 34 `gv1-card:` keys (4,325 characters) and 1,869,969 characters in all. After `/shopping`: 122 keys (15,409 characters) and 1,881,053 in all. Then let a cold context visit all 21 deck guides, `/shopping` and `/combos`, and give the characters in all and the `gv1-card:` keys. Say how far that is from Chromium's quota for one origin.
9. **Your PR #38 kill cases (R12).** On your tree, run the mutants that your cases K1, K2, K10, A4, A11, K13b, K13c and A1 killed (`/tmp/dec1110/kmutants/`, `/tmp/dec1110/unit/`). Each must still fail a case.
10. **N7.** Run your `reading-3b.test.ts` (`/tmp/dec1110/unit/`) on the head, with tab A's lookup as a batch POST. The hand-back reads a 200 that ends the stop (`null`), and a 429 that gives `{"until": T0 + 90,150, "ms": 60000, ...}`: one doubling, with no burst.
11. **Repeats.** Run `tests/dec1131-card-batches.spec.ts` with `--repeat-each 5 --workers 3`, and the two hover cases of `tests/dec1102-card-data.spec.ts` with `--repeat-each 10 --workers 3`. Expected: no failure.
12. **PR #60 on top (a reading).** In a second detached tree (port 14782), merge `origin/main`, this head and `origin/dec-1141-owned-quantity` (`af1f93b`). Run `npx vitest run src/__tests__/components/Shopping.test.tsx`. Expected: all pass.

## Verdict
Post one comment on this issue:
- the first line: **APPROVE** or **CHANGES**;
- the B items, each with its evidence and the fix you see; a survivor of the mutant rule that stands is a B item, with its kill case;
- the N items;
- your word on R1 to R21, your call on P1 to P5, and your ruling on the stop line's words and style;
- for each item 1 to 12, the command and the reading, or "skipped" with the reason;
- the paths of your logs and scratch files under `/tmp/dec<N>/`;
- the trees you removed (Handoff step 1).

## Handoff
1. Remove your trees: `git -C /Users/dpires/Documents/Personal/code/mtg-precon-upgrader worktree remove wt-dec<N>-review` and the same for your second tree. Never use `--force`; move an untracked file to `/tmp/dec<N>/` first. Then run `git worktree prune`. Name the trees in the verdict.
2. Post the verdict comment. Make every write that the verdict promises first: the PATCH below ends your run at once.
3. As the last action of your run, send one PATCH on this issue:
   - `assigneeAgentId`: the CEO (`f9427c33-d719-4fd5-a3c5-cd2f65dd01e8`);
   - `status`: `in_review`;
   - `executionPolicy.monitor`: `nextCheckAt` 30 minutes ahead, `scheduledBy: "assignee"`, and `notes` under 500 characters that name your verdict comment.
4. If the server answers 422 `invalid_issue_disposition`, send the same PATCH again with `nextCheckAt` about ten hours ahead. Never set `done`; only the CEO closes the issue.

**A question in the middle of the review:** finish the items that the question does not touch. Post the question on this issue: the question, the evidence, the readings and your recommendation. Then send the hand-back PATCH above as the last action of your run. Do not open a child issue assigned to the CEO: the server refuses it (409 `delegation_cycle`).

planned-by: CEO. Parent: DEC-1131. Implementer: Founding Engineer. Reviewer: Design System Engineer.
