## DEC-1166 verdict on PR #64 at `824d0c0`: CHANGES (one B item, two N items)

**Outcome.** CHANGES. The change does everything that DEC-1152 asks, and items 1 to 5 and 7 pass. One mutant of a rewritten line survives the whole suite (B1). Under your ruling it is a B item, but `main` has the same gap in the same words. One 12-line case fixes it. If you rule that a gap in `main`'s words is outside this PR, B1 becomes an N item and the verdict is APPROVE.

- **B1. S4 survives: no case pins that the real clock counts only `/cards/named` and `/cards/collection`.** S4 changes `test.ts:330` from `BUCKET_ONE.test(url.pathname)` to `url.pathname.startsWith('/cards/')`. The real clock then also stamps `GET /cards/autocomplete`. That is bucket 2: Scryfall allows 10 a second there, and the app spaces them 120 ms apart. The four specs read `33 passed (32.2s)`, and the whole suite reads `186 passed (3.0m)`.
  - Why B: the PR rewrote `:330` (`main`'s one-line `if … stamp(context, Date.now());` became a block), so your ruling counts it in full. S4 changes what the check stamps, and the browser's request reaches it: the Atlas sends autocompletes through `scryfallLimiter.ts:424` (`cardAtlas.ts:153`).
  - Effect today: none. No case sends 3 autocompletes in 1 s. A future case that types fast would fail on a false count.
  - Fix: copy the case `three autocompletes at once pass` (kill file `:16`) into `dec1152-rate-check-post.spec.ts`.
- **N1. R1 survives (`33 passed (32.6s)`).** R1 differs only for `fetch(request, init)` when `init.method` and the `Request`'s method differ. No code under `web/src` calls `fetch` with a `Request` (item 2), so your ruling makes it an N item. The kill case is kill file `:30`. To fix it, add a fourth form, `fetch(new Request(url), init)`, to the loop at `dec1152-rate-check-post.spec.ts:45`.
- **N2. README wording.** At `web/README.md:92`–`:93`, "The app also counts each POST as two starts, and spaces its POSTs 1,200 ms apart, so two batches in 1 s fail the test." Each fact is true, but the "so" names the wrong cause. The check's double count fails two batches in 1 s; the app's spacing does not. I propose: "… spaces its POSTs 1,200 ms apart. Two batches in 1 s start 4 requests and fail the test." Two older sentences are now weaker, and `main` has both in the same words. `test.ts:37` reads "one every 600 ms or more"; the spacing is 1,200 ms, and at 600 ms the check now fails 3 cases (item 5). `test.ts:16`–`:18` reads "every case proves the app's limit", but `README.md:93` reads "A case proves the app's limit only when …".

Kill file: `/Users/dpires/.paperclip/instances/default/workspaces/6ba3ac88-12e8-41a7-834f-98e3d92dae78/dec1166-review/dec1166-kills.spec.ts`, blob `3acbb3be681858a090ab87fd8e332a8d9c21f45e`. It imports from `./support/test`.
- On the head, both cases pass. The run held the kill file and the item 2 reading file together: `12 passed (4.1s)`.
- Under R1: `1 failed, 1 passed (4.0s)`. `:30` fails: it expected to fail, and it passed.
- Under S4: `1 failed, 1 passed (4.1s)`. `:16` fails with `One browser context started 3 requests to /cards/named and /cards/collection in 1 s; Scryfall allows 2.` and `Sends (method, ms after the first, real time): GET 0, GET 6, GET 8`.

### Setup
- `git merge-tree --write-tree origin/main origin/dec-1152-rate-check-post` printed `9a4ef560330dd7b3b112a1309a8daf908a1848a2` with no conflict. Its `web` subtree is the head's (`6e3efa75`). The merge commit `889f079` moved no ref. `npm ci` ran in `wt-dec1166-review/web`.
- During the review, `main` moved from `822f2da` to `02d085c`: 3 commits of CEO notes. `git diff --stat 822f2da origin/main -- web data .github` printed nothing, so the reading holds. PR #64's head is still `824d0c0`. `web-ci` run 38794546350 reads `success` on `824d0c0`.

### Item 1. The change against DEC-1152 "What to change": confirmed
- **The method in both clocks.** The real clock calls `stamp(context, Date.now(), request.method())` (`test.ts:331`). The page clock reads the method at `:133`, and passes it at `:136` (`report?.(Date.now(), method)`). The binding at `:317`–`:318` gives it to `stamp`. `stamp` (`:205`–`:209`) stores `method.toUpperCase()` (`:207`).
- **The starts.** `startTimes` (`:107`–`:109`) gives `[time, time]` for `POST` and `[time]` for any other method. The peak reads `peakPerWindow(startTimes(sends))` (`:349`). The limit check is `peak > RATE_LIMIT` (`:385`). `RATE_LIMIT = 2` (`:85`) and `RATE_WINDOW_MS = 1000` (`:86`) did not change.
- **The error.** `rateCheckFailure` (`:112`–`:121`) gives `started ${peak} requests` (`:115`) and the line "A POST counts twice: …" (`:116`). It lists `${send.method} ${send.time - first}` for each send (`:117`–`:118`). `first` is the earliest send of that context (`:113`, `Math.min`). `:386` passes the sends of the first context with the highest peak.
- **The three texts.** These are the header (`test.ts:10`–`:18`), the `rateClock` doc (`:58`–`:65`) and the README paragraph (`README.md:85`–`:103`). They agree: a GET counts once and a POST counts twice, for a preflight that neither a route nor the `request` event shows. They also agree that the page clock reads the method of the call. I found no sentence that the change made wrong. N2 names one unclear sentence and two older ones.
- `git grep -n -E 'Send times|sent [0-9]+ requests|context sent' HEAD -- web` printed nothing (exit 1). The new words include `test.ts:115`–`:117`, `dec1152-rate-check-post.spec.ts:80`–`:85` and `README.md:87`, `:96`, `:103`.

### Item 2. The page clock's method (`test.ts:133`): confirmed
I ran a scratch reading, `dec1166-forms.spec.ts` (blob `f5e5adbdacd3229b91d7376f62210c1281846b03`, now in my workspace folder). It wraps the binding in the page, makes one call per case, and compares the method that the init script reports with the method of the `request` event. All 10 cases passed. Each one reads `status 200`. The GET rows use `/cards/named`, and the POST rows use `/cards/collection`.

| Call form | The page reports | `stamp` stores | The browser sends |
|---|---|---|---|
| `fetch(string, { method: 'POST' })` | `POST` | `POST` | `POST` |
| `fetch(URL, { method: 'POST' })` | `POST` | `POST` | `POST` |
| `fetch(new Request(url, { method: 'POST' }))` | `POST` | `POST` | `POST` |
| `fetch(new Request(url), { method: 'POST' })` (init wins) | `POST` | `POST` | `POST` |
| `fetch(new Request(url, { method: 'POST' }), { method: 'GET' })` (init wins) | `GET` | `GET` | `GET` |
| `fetch(new Request(url, { method: 'POST' }), { headers })` (no `init.method`) | `POST` | `POST` | `POST` |
| `fetch(string)` | `GET` | `GET` | `GET` |
| `fetch(string, {})` | `GET` | `GET` | `GET` |
| `fetch(string, { method: 'post' })` | `post` | `POST` | `POST` |
| `fetch(new Request(url, { method: 'post' }))` | `POST` (the `Request` normalizes it) | `POST` | `POST` |

`git grep -n 'fetch(' HEAD -- web/src ':!web/src/__tests__'` printed 4 hits:
- `cardAtlas.ts:153` `limiter.fetch(autocompleteUrl(q), { signal })`: the limiter's own method. It sends `GET /cards/autocomplete` (bucket 2) through `scryfallLimiter.ts:424`. It cannot reach `/cards/named` or `/cards/collection`.
- `scryfallLimiter.ts:97`: a doc comment. It is not a call.
- `scryfallLimiter.ts:110`: the `fetch` signature of the `ScryfallLimiter` interface. It is not a call.
- `ComboLab.tsx:93`: `/data/commanders/${id}/spellbook-combos.json`, on the app's own origin. It cannot reach Scryfall.

That grep does not see a call through a `fetchImpl` variable, so I also ran `git grep -n fetchImpl`.
- `loader.ts:371`, `prices.ts:36`, `spellbook.ts:123`, `synergy.ts:129` and `tierBIndex.ts:95` fetch `/data/…` paths.
- `deckUrl.ts:156` fetches Moxfield or Archidekt (`:53`, `:58`).
- Only `scryfallLimiter.ts:424` sends to `api.scryfall.com`, and `isApiUrl` (`:73`) guards it. Bucket 1 has one caller, `collectionRequest` (`cardCache.ts:602`). That call is `fetchImpl(string, init)` with `init.method = 'POST'`.
- No `XMLHttpRequest`, `sendBeacon`, `EventSource` or `new Request(` is under `web/src` outside the unit tests.

### Item 3. The two cases that read the fixture's error: ruling 3 holds
- `npx playwright test tests/dec1152-rate-check-post.spec.ts --workers 3` read `7 passed (6.1s)`. Six cases show ✘ in the list, and each one failed as expected: `test.fail()` marks four of them, and the fixture's `testInfo.fail()` marks `:133` and `:137`.
- `node -p "require('@playwright/test/package.json').version"` printed `1.59.1`. `package-lock.json:1215`–`:1216` pins 1.59.1.
- **T1** deletes `testInfo.fail();`. Result: `2 failed, 5 passed (8.5s)`. Both cases (now at `:132` and `:136`) fail, each on the bare rate check error: `Error: One browser context started 4 requests to /cards/named and /cards/collection in 1 s; Scryfall allows 2.`
- **T2** changes `'page'` to `'real'` at `:131`. Result: `2 failed, 5 passed (7.4s)`. `:133` and `:137` each fail with two errors: the rate check's error, then `Error: The test did not end with the rate check's error alone:` with that message below it.
- **T3** changes `i < 2` to `i < 1` in `sendTwoBatches`. Result: `2 failed, 5 passed (5.8s)`. `:133` and `:137` fail with `Error: The test did not end with the rate check's error alone:` and then `(no error)`.
- No case passes under T1, T2 or T3. `git status --porcelain` was empty after each mutant.

### Item 4. The suite on the merged tree: matches the Basis
I ran `npm run lint && npm run typecheck && npm test -- --run && GRIMOIRE_E2E_PORT=14841 npm run test:e2e -- --workers 3` (log: `item4-suite.log`, JSON: `item4-e2e.json`).
- lint: `✖ 10 problems (0 errors, 10 warnings)`. The Basis expects 0 errors and 10 warnings.
- typecheck: exit 0.
- vitest: `Test Files  51 passed (51)` and `Tests  610 passed (610)`. The Basis expects 51 and 610.
- Playwright: `186 passed (3.0m)`. The JSON reads expected 186, unexpected 0, flaky 0. The Basis expects 179 + 7 = 186. The load average was 12.61 at the start and 18.90 at the end.

### Item 5. The control at 600 ms: the same 3 cases as the implementer
`LOOKUP_SPACING_MS = 600`, with `tests/dec1131-card-batches.spec.ts` and `tests/dec1102-card-data.spec.ts` and 3 workers. Result: `3 failed, 18 passed (27.3s)`. The implementer's `control-600.log` reads the same.
- `dec1102:176` (the hover case): `One browser context started 4 requests … Scryfall allows 2.` and `Sends (method, ms after the first, real time): POST 0, POST 974, POST 1949, POST 2925, …`.
- `dec1131:98` (the prices case): the gap check fails first (`Expected: >= 1100`, `Received: 602`). Then the rate check fails: `started 4 requests …`, `POST 0, POST 602`.
- `dec1131:165` (the `//` case): `started 4 requests …`, `POST 0, POST 602`.
- Each message holds the line `A POST counts twice: …`. No case failed for another cause. After the restore, `git status --porcelain` printed nothing, and `scryfallLimiter.ts:40` read `1_200`.

### Item 6. Mutants
I ran each mutant against `dec1152-rate-check-post`, `dec1110-harness`, `dec1131-card-batches` and `dec1102-card-data` (33 cases, 3 workers, port 14841). After each one, `git status --porcelain` was empty.

| ID | Mutant | Count line | Failed cases | Class |
|---|---|---|---|---|
| MA1 | a POST counts once | `7 failed, 26 passed` | dec1152 `:22`, `:46` ×3, `:71`, `:133`, `:137` | killed |
| MC | the page clock stamps GET | `5 failed, 28 passed` | dec1152 `:46` ×3, `:133`, `:137` | killed |
| MI6 | the fixture passes `'real'` to the error | `2 failed, 31 passed` | dec1152 `:133`, `:137` | killed |
| MI8 | the error takes the first context's sends | `1 failed, 32 passed` | dec1152 `:137` | killed |
| R1 | the `Request`'s method wins over `init`'s | `33 passed` | none | **N1** (kill file `:30`) |
| R2 | a POST's second start falls one window later | `7 failed, 26 passed` | dec1152 `:22`, `:46` ×3, `:71`, `:133`, `:137` | killed |
| R3 | the peak reads `startTimes(sends).slice(1)` | `4 failed, 29 passed` | dec1110 `:11`, `:26`; dec1152 `:133`, `:137` ("started 3") | killed |
| R4 | the error lists the sends sorted by time | `1 failed, 32 passed` | dec1152 `:71` | killed |
| S1 | the page reads `'POST'`, not `'GET'`, for a call with no method | `1 failed, 32 passed` | dec1110 `:38` (4 starts) | killed |
| S2 | the page clock's binding stamps real time | `5 failed, 28 passed` | dec1110 `:38`; dec1131 `:298`, `:361`; dec1152 `:133`, `:137` | killed |
| S3 | the real clock stamps every request as `POST` | `1 failed, 32 passed` | dec1110 `:17` (4 starts) | killed |
| S4 | the real clock stamps every `/cards/` path (`:330`) | `33 passed`; the whole suite `186 passed (3.0m)` | none | **B1** (kill file `:16`) |

- **Against `f1cfee46`.** MI6 and MI8 fail the same cases as the implementer's run 3. MA1 and MC also fail `:133` and `:137`. Those two cases came after the implementer's MA1 and MC runs, in `8f3902e`. In the implementer's runs, MA1 and MC also failed `dec1102` cases from load. Mine failed none.
- I struck no survivor as equivalent.
- I did not add `!== 'GET'` for `=== 'POST'` in `startTimes`. It differs only for methods (PUT, DELETE, HEAD) that nothing sends to bucket 1.
- The `rateCheckFailure` text lines (`:115`–`:119`) are all pinned by `:71`'s exact compare (MI1–MI4, R4).

### Item 7. The preflight reading: confirmed
`npx playwright test -c <workspace>/e2e/pw-preflight.config.ts`, port 14841, read `1 passed (3.8s)`:
`item 5 reading: status 200; CDP ["requestWillBeSent POST https://api.scryfall.com/cards/collection type=Fetch","requestWillBeSent OPTIONS https://api.scryfall.com/cards/collection type=Other","responseReceived 204 type=Preflight","responseReceived 200 type=Fetch"]; request events ["POST"]; route ["POST"]`
CDP sees the `OPTIONS` request and its `204` answer. The `request` event and the route see `["POST"]` only. The two `requestWillBeSent` events came in the opposite order to the implementer's reading; the content is the same. I made no change in the tree for this item.

### Flakes, timeouts and load
- No case failed outside the rate check in any run. I saw no flake and no timeout.
- The 1-minute load average ran from 3.15 to 18.90. Every runner summary lists the load before and after each mutant.

### Deviations from the brief
1. **The runner copy also changes the port.** `run_mutants.py` hardcodes `GRIMOIRE_E2E_PORT='14831'`. The brief says to never use 14831, so my copy sets 14841. `diff` shows 3 changed lines: `TREE`, `OUT` and the port. I read the copy before the run. It asserts that each mutant's old text occurs once, and restores the file with `git checkout` after each mutant.
2. **My own runner, `run_hand.py`, ran T1–T3, the control, R1–R4, S1–S4 and the kill runs.** It works the same way. It also restores in a `finally` block, and checks porcelain before and after each mutant. My first S4 run stopped at the old-text assert, because that line also occurs at `test.ts:259`. The file did not change. I made the old text two lines long and ran S4 again.
3. **Item 2 has a scratch reading.** I added `dec1166-forms.spec.ts` beside the kill file. It ran once in the tree, and then I moved it out.
4. **The item 7 folder holds two more files.** As in `/tmp/dec1152/e2e`, it holds `package.json` (`{"type":"module"}`) and a `node_modules` link into my tree. Without them, the config outside the tree cannot import `@playwright/test`. The link now points nowhere.

### Tree and files
- I removed `wt-dec1166-review` with `git worktree remove wt-dec1166-review` (exit 0, no `--force`). Its `git status --porcelain` was empty before the removal. I did not touch `wt-dec1152` or `/tmp/dec1152/`, and I sent no request to `api.scryfall.com` or `cards.scryfall.io`.
- Workspace folder: `/Users/dpires/.paperclip/instances/default/workspaces/6ba3ac88-12e8-41a7-834f-98e3d92dae78/dec1166-review/`. It holds:
  - `dec1166-kills.spec.ts` and `dec1166-forms.spec.ts`;
  - `run_mutants.py` (the copy) and `run_hand.py`;
  - `mutants/` and `hand/`, each with `summary.txt` and the logs and JSON of each run;
  - `item3-spec.log`, `item4-suite.log`, `item4-e2e.json` and `item7-preflight.log`;
  - `e2e/` (the item 7 copies) and this verdict, `verdict.md`.
