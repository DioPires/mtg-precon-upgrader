**Opened by the CEO on 2026-10-15 at 08:50Z, after PR #38 (pull request 2) reached `main` as `9b6c18d`. This brief is current: do the work.**

**Card data, pull request 3 of design D (DEC-1072).** Names that `card-metadata.json` lacks go to Scryfall in batches of up to 75 names, through `/cards/collection`. Prices older than 24 hours refresh the same way, on /shopping and in deck tiles. /shopping shows a line while a stop holds the refresh. This pull request also takes the eleven notes of the PR #38 review that I sent to pull request 3.

- Implementer: you, the Founding Engineer (`4e51e111`). You wrote the proposal (DEC-1072 comment `627e62a7`) and pull request 2.
- Tier 2, priority high. Budget: about 9 hours (your 5 hours for the batch in the proposal, 1 hour for the tile refresh, and my 3 hours for the notes). If the leg runs past 12 hours, hand back what is done and name what is left.
- Reviewer at the hand-back: the CEO names it from the queues. It is never you.
- **Your queue (read at 08:51Z).** Your DEC-1129 review (low) runs since 08:31:36Z. Two runs are queued before this issue's run `6cef475c` (08:50:35Z): your DEC-1078 fix round (low, 08:31:31Z) and your DEC-1130 review (high, 08:44:39Z). The server chooses the order. On 2026-10-14 it started a high wake before an older low one, but one case does not prove the rule.

## Why
- Since PR #38 a deck card needs no request. A name outside the file still takes one `/cards/named` lookup at 600 ms. /combos art takes about 10 s for 16 lookups, and the Apothecary hover's 9 names take about 5 s (merge record `aeaf883c` on DEC-1102).
- Every page shows the file's prices. `data/card-metadata.meta.json` holds `prices_as_of` `2026-10-13T21:56:40+00:00`, and no workflow refreshes the file.
- One batch answers up to 75 names. So /combos and the hover need 1 request where they need 16 or 9 today.

## Rulings that fix the design
1. **R1 (where prices refresh): option B, the 24-hour rule also on tiles.** The owner's card `116a1d02` on DEC-1072 is still open. Its own text says that option B applies when no answer has come by the merge of pull request 2. So /shopping and the tile foot refresh a price that is older than 24 hours.
   - A tile takes its price from the deck file's highlights first (`normalize.ts:174`, `:352`; `CardTile.tsx:90-91`). Only a tile that shows the cache's price asks for a refresh. Keep that order.
   - Put the tile's refresh in one call site. If the owner answers A before your hand-back, I post the answer on this issue, and you remove that call site.
2. **R2 (the stop line on /shopping).** While a stop holds and at least one row waits for a refresh, /shopping shows one line with `role="status"`. The line says three things: the refresh is paused, the date of the prices shown, and the clock time of the next try. Example: "Price refresh paused. Prices shown are from 13 Oct 2026. Next try at 22:41:05."
   - The line does not say that Scryfall asked. The app cannot tell a 429 from a lost network: both are a rejected `fetch`.
   - The line goes when the stop ends, also when no request waits. The reviewer rules on the style.
3. **The price date.** Each price has a date: `prices_as_of` for the file's price, and the answer's time for a refreshed price. The footer (`Shopping.tsx:828`) and the stop line show the oldest date among the rows that the page counts as priced. When the file is newer than a stored refresh, the file's price wins.
4. **Every lookup becomes a batch.** At its turn, bucket 1 sends one `POST /cards/collection` with up to 75 waiting names. Names with `first` (the hover, the commander art) go before the others, and lookups go before refreshes. No `/cards/named` request remains in `web/src`, also not for the lookup after a failed picture (`cardCache.ts:330-345`).
   - A `//` name goes out as its front face. The answer is stored under the name that the app asked for. Match the answer to the names by the fold that the stub uses (`normalizeName`, `web/src/lib/spellbookMatch.ts:20`), on the full name and on the front face. Do not match by position.
   - Two names with one front face (`Bonecrusher Giant` and `Bonecrusher Giant // Stomp`) go out once, and both get the answer.
   - A transform or modal_dfc card has `image_uris` only in `card_faces[]` (live reading 1 of the proposal). `cardEntryFromScryfall` (`cardEntry.ts:68-80`) already reads the first face; keep that.
   - A name in `not_found` gets no other request for 24 hours, also after a reload. Today an error lives 30 s in memory only (`cardCache.ts:56`, `:316`).
   - A batch that fails as a whole (a 429, a rejected `fetch`, or the timeout of note N3) keeps all its names first in the queue, as one lookup does today (`scryfallLimiter.ts:356-361`).
   - A batch answer with another status (a 400 or a 422) fails its names as one 404 does today. It starts no stop.
   - A refresh that gets no price (`not_found`, a 400 or 422, or `usd` `null`) keeps the price shown and is not asked again inside 24 hours.
5. **Bucket 1 spacing becomes 1,200 ms.** A JSON POST from the browser goes after a CORS preflight (`OPTIONS`); live reading 2 of the proposal gave `access-control-max-age: 300`. Nobody knows whether Scryfall counts the preflight, so each POST counts as two starts. With 600 ms, three requests (the last POST, the next preflight and the next POST) can fall inside 1 s. After ruling 4 every bucket 1 request is a POST, so `LOOKUP_SPACING_MS` (`scryfallLimiter.ts:25`) becomes 1,200 ms. Bucket 1 still waits for the last answer.
6. **The limiter sends a body.** Today `send()` calls `fetchImpl(url)` or `fetchImpl(url, { signal })` (`scryfallLimiter.ts:343`). Give `fetch()` and `next()` a way to pass the method, the headers and the body. Only `api.scryfall.com` stays allowed (`:44-50`).
7. **The refresh on /shopping.** At first paint every row shows the file's price. Then the page asks for the refresh of its rows. 88 rows take 2 batches (75 and 13 names). The estimate changes once when the answers arrive.
8. **What a refresh changes.** Only the price and its date. Mana cost, type line and pictures stay the file's. A refreshed price lives 24 hours under `gv1-card:`, and `seed()` keeps it. Today `seed()` removes the `gv1-card:` entry of a seeded name unless the entry holds a picture refresh (`cardCache.ts:208-226`).

## The notes from the PR #38 review
From the first verdict (`fe36545b` on DEC-1110; ruling `88d6d272`):
- **N2. The rate check stamps at the browser's send.** In real mode, stamp a bucket 1 request at `context.on('request')`, not in the route handler (`web/tests/support/test.ts:200`). A spec that holds an answer with `route.fallback()` then reads the browser's send times.
- **N3. A timeout.** A request that has no answer after 20 s is aborted, and it counts as a rejected `fetch`: it starts or doubles the stop. An abort by the caller stays no failure. Today a request that never answers holds bucket 1 in every tab (P1 of the verdict: a 90 s hold, 0 lookups in either tab).
- **N4. An old stop record goes.** A record whose end lies more than `MAX_STOP_MS` (300 s) in the past counts as no record, so the next failure stops for 30 s. Today a 300 s stop from three days ago makes the next failure stop for 300 s.
- **N5. Autocomplete during a stop.** `scryfallSuggest()` (`cardAtlas.ts:142-157`) sends nothing while `stoppedUntil()` is set, and it returns `[]` at once. The Atlas keeps its local suggestions.
- **N6. No empty file in storage.** When `/data/card-metadata.json` fails, `loadCardMetadata()` persists `{}` for 1 hour (`loader.ts:403-410`). Persist no failed or empty file, and let the next load ask again.
- **N7. Two tabs at the end of a stop: a reading only.** Run the case of the reviewer's `reading-3b.test.ts` again on your branch, and quote the stop's length after it. PR #38 read one doubling, to 60 s, with no burst. Change nothing for it unless your reading differs.
- **H7. A page-clock case with `/cards/collection`.** One e2e case with `test.use({ rateClock: 'page' })` sends a batch, so that page mode is shown to count a POST.

From the delta re-read (`05eb6940` on DEC-1110; my rulings in `9e8e248c`):
- **Delta N1. Cap a stop in memory.** `readStop()` caps a stored stop at now plus its length (`scryfallLimiter.ts:170-179`). When storage is missing or refuses the write, it returns `memoryStop` with no cap (`:164`). Cap that one too.
- **Delta N2. The stop line reads `stoppedUntil()` when it renders.** In the tab that caps, a listener keeps the end from before the cap until the stop ends. Do not show the listener's value.
- **Delta N3. A stop number, not wall times.** `fail()` and `succeed()` compare a request's start time with the stop's end (`:223-234`). After a jump back larger than the stop's length, a request that was out before the stop can double the stop (K1) or end it (K2). Keep a number in the stop record. A request notes the number when it starts, and it can double or end only the stop whose number it noted.
- **Delta N4. Spacing inside a tab on `performance.now()`.** A forward clock step of more than about 500 ms while a lookup is out lets 3 lookups go in 1 s, once (sends at `[0, 100, 700, 1300]` ms of elapsed time). Measure the spacing inside a tab with `performance.now()`. The last start in storage, which other tabs read, stays wall time.

## State on `main`
- `main` is at `ded55c6` (PR #40 merged at 08:40:15Z). `STORAGE_PREFIX` is `gv1-deck-data-v156:` (`loader.ts:241`). Totals after PR #38 (push run 38700803588 on `9b6c18d`): lint `0 errors, 10 warnings`; vitest `41 passed (41)` files and `455 passed (455)` tests; Playwright `131 passed (9.9m)`. The newest `web-ci` push run is 38706513178 on `fedf498` (PR #49), green. Read the newest push run again before you compare.
- Bump `STORAGE_PREFIX` only if this pull request changes what the loader persists. A bump goes from `v156` to `v157`, adds a line to the version log above it, and changes the two strings of the pinned case in `web/src/__tests__/data/loaderEnvelope.test.ts`. Read the value on `main` again first: `git show origin/main:web/src/data/loader.ts | grep 'STORAGE_PREFIX ='`.
- On any day after 14 Oct 21:56Z every price of the file is older than 24 hours. So every visit refreshes until it has stored a fresh price.
- The callers of the cache: `Shopping.tsx:255-259` and `:324`, `CardTile.tsx:82-91` and `:108`, `GV1CardHoverLayer.tsx:82-84`, `:137` and `:185`, `GV1CommanderArt.tsx:38`, `Decklist.tsx:147-155`, `Scrying.tsx:143` to `:517`, `ComboLab.tsx:1990`, `useCard.ts:5-15` and `cardType.ts:14`.
- The stub (`web/tests/support/scryfall.ts`) answers `/cards/named` and `/cards/autocomplete` (`answerFor`, `:180`). It has no answer for `/cards/collection`, so every such request fails its test today.
- **Open pull requests that touch your files.** Read each again before your hand-back.
  - PR #34 (DEC-1071, Frontend Engineer; its fix round 2 runs) changes `web/tests/support/test.ts`, `guard.ts` and `web/README.md`. If it merges first, merge `main` and keep both changes.
  - PR #32 (DEC-1079, Simulation Engineer; its delta re-read runs) changes the prices in `data/card-metadata.json` and the meta file. After it merges, the footer reads "as of 14 Oct 2026" before a refresh. Write no fixed price count or date into a test or a wait.
  - PR #45 (DEC-1077) changes `web/src/data/types.ts`.

## Items
1. **The limiter** (rulings 5 and 6; notes N3, N4, delta N1, N3 and N4).
2. **The batch in the cache** (rulings 4 and 8). The hover, the commander art, /combos and the Atlas keep their call sites.
3. **The refresh** (rulings 1, 3, 7 and 8): the /shopping rows and the tile foot.
4. **The stop line and the footer** (rulings 2 and 3; delta N2).
5. **Autocomplete and the loader** (N5 and N6).
6. **The stub and the fixture** (`web/tests/support/`).
   - The stub answers `POST /cards/collection` as live reading 1 of the proposal: `{"object": "list", "not_found": [...], "data": [...]}`. A front-face name matches without regard to case and accents. A full `//` name goes to `not_found`. `data` keeps the request order. Every `//` card has `card_faces`, and a transform or modal_dfc card has `image_uris` only there. More than 75 identifiers get a 422; say in the hand-back that the shape of that answer is a guess.
   - Give the stub one option, off by default, that lets a case tell a refreshed price from the file's price (for example, $1.00 more on each `usd`).
   - The 429 option (`scryfall429From`) counts `/cards/collection` in bucket 1, as now.
   - Say in the hand-back whether a Playwright route sees Chromium's preflight. If it does, the rate check counts it.
   - Notes N2 and H7.
7. **Unit cases** (fake clock, fake `fetch`; answers after 0 ms and after 150 ms):
   - 88 names outside the file go in 2 POSTs of 75 and 13 names. When each POST counts as two starts at its send time, no 1 s window holds more than 2 starts.
   - A `//` name goes out as its front face and is stored under the name asked. Two names with one front face go out once.
   - A `not_found` name is not asked again inside 24 hours, also from a new cache instance on the same storage. After 24 hours it is asked once.
   - A batch that meets a 429, a rejected `fetch` or the 20 s timeout keeps its names first, and the batch after the stop holds them. A 400 or a 422 fails the names and starts no stop.
   - The refresh: a file price older than 24 hours is asked once; a price refreshed less than 24 hours ago is not asked; a file newer than the stored refresh wins; a refresh changes only the price and its date; `seed()` keeps a refreshed price; a refresh with no price keeps the price shown.
   - The notes: N3 (the timeout); N4 (a record that ended 301 s ago and one that ended 299 s ago); N5; N6; delta N1 (the clock goes back 10 h, with no storage and with a storage that refuses the write); delta N3 (cases K1 and K2 of the delta verdict); delta N4 (a forward step of 1 s, 50 ms after the first send).
   - The stop line: it shows the capped end in the tab that capped (delta N2), and it goes at the stop's end when no request waits.
8. **e2e cases** (new specs import `test` and `expect` from `./support/test`):
   - /shopping: the priced count at first paint with 0 requests to `api.scryfall.com`; then 2 POSTs to `/cards/collection` and the refreshed prices (the stub option); then a reload inside 24 hours sends 0. Read the counts from the page and the file; write no figure.
   - /shopping with the 429 option from request 1, under the page clock (H7): the stop line shows with `role="status"`, the price date and the clock time; the page sends 0 requests in the 30 s of `page.clock` after the failure, then 1; then the line goes.
   - /combos at load sends 1 batch, and the art shows.
   - A deck guide: only tiles with no highlight price ask for a refresh, and a reload inside 24 hours sends 0.
   - The Atlas during a stop sends no autocomplete (N5).
9. **The table again.** Run your measure spec from PR #38 (`agents/founding-eng/analysis/dec1102/run2-58ca0b3/measure/`) on `main` and on your branch. Give the leg 1 table with one column for each: lookups, batches (with the names in each), autocomplete, the image host, the peak in 1 s, and the time to the last answer. Add /combos, the Apothecary hover over its 9 names, and the tile refresh of `/deck/creeping-corruption`.
10. **The names census.** The batch matches names exactly (after the fold), where `fuzzy` forgave a misspelling.
    - List every name that the app can send outside `card-metadata.json`: the names of the 21 `candidates.json` files, the names that /combos shows, and any other source that you find.
    - Check each name against the oracle mirror, on the full name and on the front face. The mirror is `/Users/dpires/Documents/Personal/code/mtg-precon-upgrader/priv_data/scryfall-oracle.json` (read only; 32,116 commander-legal cards).
    - Give the counts, and list each name that matches neither. A banned card is a real card that the mirror lacks, so mark the misses that you know to be banned.
    - Change no data file for this. I rule on the list.
11. **Mutants.** Make each mutant in your tree. Run the unit file, and then the e2e spec that should catch it. Restore the file; `git status --porcelain` prints nothing after each one. Quote the count line of each run, and keep a log of each.
    - M1: the spacing is 600 ms again (ruling 5).
    - M2: a batch takes 76 names.
    - M3: a `//` name goes out as its full name.
    - M4: a `not_found` name is asked again inside 24 hours.
    - M5: the refresh ignores the 24-hour age.
    - M6: a tile with a highlight price asks for a refresh.
    - M7: the footer keeps the file's date after a refresh.
    - M8: the stop line shows the listener's value (delta N2).
    - M9: the timeout counts as no failure (N3).
    - M10: a record that ended long ago stays (N4).
    - M11: autocomplete goes during a stop (N5).
    - M12: an empty file is persisted (N6).
    - M13: the stop in memory has no cap (delta N1).
    - M14: `fail()` compares wall times again (delta N3).
    - M15: the spacing inside a tab reads `Date.now()` (delta N4).
    - M16: the rate check stamps in the route again (N2), on a spec that holds an answer with `route.fallback()`.
    - Each mutant must fail at least one case. If one passes everything, add the case that kills it.
12. **Documents.** Update the header comments of `scryfallLimiter.ts` and `cardCache.ts`, and `web/README.md`: the batch, the 1,200 ms spacing, the refresh, the stop line, the timeout, and the stub's new answer and option.
13. **The census of hosts.** In the hand-back, quote the output of `git grep -n -E 'api\.scryfall\.com|format=image|/data/images/cards|/cards/named' HEAD -- web/src`. Only `scryfallLimiter.ts` and test files may name the API host.
14. **Storage.** Measure the characters in `localStorage` after a cold visit to `/deck/creeping-corruption` and then `/shopping`, on `main` and on your branch. Give the count of `gv1-card:` keys in each.

## Rules
- **Tree.** Work in `wt-dec1131`, from `origin/main`, on branch `dec-1131-card-data-batch`: `git worktree add wt-dec1131 -b dec-1131-card-data-batch origin/main`. Run `npm ci` in its `web/`. Keep scratch files outside the tree.
- **Ports.** Set `GRIMOIRE_E2E_PORT=14751` on every e2e run in your tree. Use 14752 in a second tree if you need one. A run accepts only the server that it started, and a second run with the same value stops at once.
- **Environment.** Set `HOME="$PAPERCLIP_GITHUB_HOST_HOME"` for `gh`, `git commit` and every other `git` command. Set `PLAYWRIGHT_BROWSERS_PATH="$PAPERCLIP_GITHUB_HOST_HOME/Library/Caches/ms-playwright"` for every Playwright run; without it every case fails at launch.
- **No live request.** Send no request to `api.scryfall.com` or `cards.scryfall.io` from a script, a test or `curl`. The stub answers every e2e case, and the census of item 10 reads the mirror only.
- **Workers.** Run Playwright with 3 workers at most.
- **Assertions on a size.** Read a height after `document.fonts.ready`. Take a screenshot with `animations: 'disabled'`. Run each new spec that reads a size with the fonts live and with `test.use({ fonts: 'blocked' })`, and quote both.
- **Before the hand-back PATCH.** Merge `origin/main` if `git diff --stat "$(git merge-base HEAD origin/main)" origin/main -- web data scripts .github` prints anything. Then run `cd web && npm run lint && npm run typecheck && npm test -- --run && GRIMOIRE_E2E_PORT=14751 npm run test:e2e`, and quote the four count lines. Wait for `web-ci` on your last push, and quote its run id and totals.
- **Trees.** Touch no tree but your own. At 08:48Z the other trees were `wt-dec1032`, `wt-dec1071`, `wt-dec1077`, `wt-dec1079`, `wt-dec1112-delta`, `wt-dec1114`, `wt-dec1116` and `wt-dec1124`; any tree that a live run holds is also not yours. Never use `git worktree remove --force`.
- Open one pull request against `main`. Its description names this issue and design D.

## Not in this pull request
- The price data in the pipeline (DEC-1079, PR #32), and a workflow that refreshes `card-metadata.json`.
- The scripts' and the card tools' limiter (DEC-1092, closed), and card lookups in agent runs (DEC-1124).
- A change to a data file for a name of item 10.

## Handoff
Post your evidence as one comment on this issue. Put first: the head, the pull request, the four count lines and CI's run id. Then give the table of item 9, the names census, the storage totals, the mutants with their logs, the census of hosts, the readings (N7, the preflight) and each deviation from this brief with its reason.

Then send one PATCH on this issue as the last action of your run:
- `assigneeAgentId`: the CEO (`f9427c33-d719-4fd5-a3c5-cd2f65dd01e8`).
- `status`: `in_review`.
- `executionPolicy.monitor`: `nextCheckAt` 30 minutes ahead, `scheduledBy: "assignee"`, and `notes` under 500 characters that name the hand-back comment.

The assignment wakes the CEO, who routes the review. The monitor wakes the CEO when the server skips that wake. If the server answers 422 `invalid_issue_disposition`, send the same PATCH again with `nextCheckAt` about ten hours ahead. Never set `done`; only the CEO closes the issue. The hand-back PATCH ends your run at once.

**A question in the middle of the leg.** The server refuses a child issue that you assign to the CEO (409 `delegation_cycle`), so a question takes the hand-back:
1. Finish the parts that the question does not touch.
2. Commit and push them.
3. Post the question on this issue: the question, the evidence, the readings and your recommendation.
4. As the last action of your run, send the hand-back PATCH above.

The CEO rules in a comment, writes the ruling into this description and assigns the issue back to you.

planned-by: CEO. Parent: DEC-1072 (hub). Sources: ruling `15c825e9`, proposal `627e62a7`, the PR #38 review on DEC-1110 (`fe36545b`, `88d6d272`, `05eb6940`, `9e8e248c`), and the owner's card `116a1d02`.
