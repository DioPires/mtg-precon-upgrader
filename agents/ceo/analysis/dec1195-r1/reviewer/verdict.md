**CHANGES at `27e34a4`. Three B items: two mutants survive on added lines (R1 and R3), and a 429 now waits for its body before the stop starts. One fix covers all three: one condition on `scryfallLimiter.ts:454` and four cases in `body-timeout.test.ts`. I tested the fix: 706 unit cases pass, and each of the three mutants fails a new case.**

Reviewer: Design System Engineer (run `c51e7f25`). Evidence: `$PAPERCLIP_GITHUB_HOST_HOME/.paperclip/instances/default/workspaces/8ea33a50-69a7-4a75-bcc1-245bd1e7c73a/dec1195/` (copy of `/tmp/dec1195/`). Below, `mut/` and `proposed/` are folders under that path.

## 1. Basis
- After `git fetch origin`, `origin/main` is `349e13f`, a CEO notes commit. `git diff --stat 8f15c33 origin/main -- web data .github` printed nothing.
- I reviewed the head itself: `27e34a4`. Its `web` tree is `d5d9bb04`, and the blob of `scryfallLimiter.ts` is `0ff90790`, as the brief says.
- Trees: `wt-dec1195` (detached at `27e34a4`) and `wt-dec1195-main` (detached at `8f15c33`). I remove both after this comment.

## 2. Counts
**Item 2, the control and the fix**
- `main` tree, with the head's `body-timeout.test.ts` copied in: `Tests  3 failed | 3 passed (6)`. The cases that fail are the two 8a cases and B1 at 10,000 ms. I deleted the copy after the run. Log: `control-main-8f15c33.log`.
- Head: `Tests  6 passed (6)`. Log: `fix-head.log`.

Each case read against the brief:
- **8a, both body kinds.** At 19,999 ms there is no stop, and tab B has sent nothing. At 20 s the stop is `{until: T0+50,000, ms: 30,000}`, and A1 is `loading` with no error. Tab A sends A1 at 0, A1 again at 51,200 and A2 at 52,400. Tab B sends B1 at 50,000. All three names are `loaded`, and no stop is left. This meets the brief: A1 goes again first in its tab, and A2 goes after it. B1 goes first across the two tabs because tab B waits on the lock through the stop. The stopped batch goes first only in its own tab (N5).
- **B1.** A head at 10 s and a body 9,999 ms later: one send, no stop, `loaded`. A body 10,000 ms later: a stop of 30,000 ms, sends at 0 and 50,000, `loaded`. So the deadline counts from the start.
- **B2.** One send. The name is `{status: 'error', errorStatus: 0}` in memory. Nothing is stored, and no stop starts. This is ruling 2's named limit.
- **B3.** `fetch()` resolves with status 200 at once. At 30 s there is no stop and only one send.

**Item 3, the edited DEC-1153 case** (`scryfallLimiter.test.ts:541`). The case keeps its intent. It expects one send of all 16 names, and both tabs read all 16 `loaded`. It passes on the head. The lock now holds through the limiter's own read of the body, so the case no longer kills X1. X1 is still killed by three cases, as the hand-back says: `:595` and both 6b cases in `kill-limiter.test.ts` (`699 passed / 3 failed`). Log: `mut/X1.log`.

**Item 4, the H2 row**
- Head: `Tests  13 passed (13)`. Log: `H2-head.log`.
- Mutant H2 (the runner's exact replacement): `Tests  1 failed | 12 passed (13)`. The one failure is the row `counts the number 2026 as no date`. Log: `H2-mutant.log`. I restored the file.

**Item 8, the suites on the head** (port 14995, 3 workers). All four counts are as expected.
- lint: `✖ 10 problems (0 errors, 10 warnings)`
- typecheck: exit 0
- vitest: `Test Files  55 passed (55)` and `Tests  702 passed (702)`
- Playwright: `246 passed (3.2m)`

Logs: `full-lint.log`, `full-typecheck.log`, `full-vitest.log` and `full-e2e.log`.

## 3. Item 5, the README, sentence by sentence
No sentence is contradicted by the code.
- **`README.md:204-205`**: "keeps a lookup's error in that tab's memory only, so the other tab asks again". This holds. `settleLookup` (`cardCache.ts:535`) calls `put(..., false)`, so nothing goes to storage. In P3, the second tab sends `Outside Name` at 22 s.
- **`:205-206`**: "A refresh's 24 h mark goes to storage, so the other tab sends nothing for that name". This holds. `settlePrice` (`:539-549`) calls `writeOverlay` with `priceCheckedAt`. In P3, `gv1-card:sol ring` is stored, and the second tab sends no `Sol Ring`.
- **`:233-235`**: "fails the batch's lookups for 30 s in that tab's memory, holds its refreshes for 24 h in storage, and starts no stop". This holds. `ERROR_RETRY_MS` is 30,000, the overlay lives 24 h, and no stop starts. It matches the header comment at `cardCache.ts:40-44`.
- **`:210-211`**: "The card cache's batch has its answer only when the body has ended, so a body that has not ended 20 s after the start counts the same". This holds. Line 489 sets `wholeBody` exactly when `settle` is passed, and the card cache always passes it. Lines 454-457 race the read of the copy with the request's own timer, which starts with the request. A timeout leads to `unshift` and `fail` in `send()`. B1 shows this at the boundary. Wording: see N4.

## 4. Mutants
I ran each one on the whole unit suite first, and on e2e only when no unit case killed it. The tree was clean after each run. Logs: `mut/<id>.log`, `mut/<id>-e2e.log`, `mut/results.jsonl` and `mutants.out`. My runner is the implementer's `mutants.py` with its output folder set to `/tmp/dec1195/mut` and my R1-R5 entries added.

| id | mutant | result |
|---|---|---|
| M1 | `if (false)` | killed: 8a ×2, B1 10,000 (`699/3`) |
| M6 | race with the timer dropped | killed: 8a, the body that ignores the abort (`701/1`) |
| M8 | `void` for `await` | killed: 8a ×2, B1 10,000 (`699/3`) |
| M13 | `job.settle === undefined` | killed: 5 cases (N3 abort, 8a ×2, B1 10,000, B3) |
| X1 | `void settledOrAfter(...)` | killed: `:595`, 6b ×2 |
| **R1** | `response.clone().body?.getReader().read()` for `arrayBuffer()` | **survived**: unit `702/0`, e2e `246 passed (3.4m)`. Not equivalent, see B1. My K1 kills it (`mut/R1-kills.log`). |
| R2 | a new 20 s timer from the head (the request's timer cleared at the head) | killed: B1 10,000 (`701/1`) |
| **R3** | `if (response && wholeBody && response.ok)` | **survived**: unit `702/0`, e2e `246 passed (3.3m)`. Not equivalent, see B2. My K2 kills it (`mut/R3-kills.log`). |
| R4 | the read's `.catch` sets `timedOut = true` | killed: B2 (`701/1`) |
| R5 | `clearTimeout(timer)` at the head | killed: 8a ×2, B1 10,000 (`699/3`) |

**R3, by status, for a body that never ends** (K2, K3 and P2):
- **400 or 422.** On the head, there is no answer at 20 s. A stop starts with `until` at T0+50,000, and the batch goes again first at 50,000. On R3, `settle` runs at the head: the lookups get `scryfall 400` in memory for 30 s, the refreshes are held 24 h in storage, and no stop starts. Nothing ever aborts the open body, because the timer is cleared at the head.
- **429.** On the head, the stop starts at 20 s (`until` T0+50,000). On R3, it starts at the head (`until` T0+30,000), as on `main`.
- **For the card cache.** R3 is not equivalent there either. `settle()` reads only an `ok` body, so R3 does not hang the tab. But the outcome differs: a 30 s error and a 24 h hold, against a stop and a resend. R3 also breaks three written sentences: `README.md:210-211`, the limiter's header comment (lines 27-28) and the `settle` doc (lines 110-111).

**M3 and M9 (ruling 3), judged on the declared types.** I agree with the hand-back that both are equivalent.
- **M3** (`if (wholeBody)`). `fetchImpl` is `typeof fetch`, so `fetching` resolves to a `Response`, and an object is never falsy. `response` is null only when the timer has won the race, and then `timedOut` is already `true`. On M3, `null.clone()` throws inside the `try`, and the function returns `{response: null, error: TypeError, timedOut: true}`. In `send()`, `timedOut` takes the same branch as on the head, and the branch does not read `error`. `tsc` also rejects M3 (TS18047).
- **M9** (`text()` for `arrayBuffer()`). On a fresh clone, both methods read the whole stream. Both settle when the stream ends or errors, and both resolve at once for a null body. The `.catch` takes any rejection, and nothing reads the value. Two edges are left: `text()` can reject on a body above the engine's string limit (about 512 MB), and `arrayBuffer()` can reject when memory runs out. Both rejections come after the full read, so the time at which the race ends does not change.

## 5. Probes
Each probe ran in `wt-dec1195/web/src/__tests__/dec1195/`, and I removed the folder after each run. Logs: `probes-head-27e34a4.log` and `probes-main-8f15c33.log`. Files: `probes.test.ts` and `kills.test.ts`.

**P1, a caller's abort at 5 s while the body is still out**
- **The body errors at the abort (a browser's fetch):** the call rejects at 5,000 with `AbortError`. No stop starts, and there is one send. This is as expected.
- **The body ignores the abort:** nothing happens at the abort. At 20 s a stop starts with `until` at 50,000. The call rejects with `AbortError` only at 50,000, when the job's turn comes after the stop. There is one send, so nothing goes again. This is N1.
- **`main`**, for comparison: both kinds hang. At 100 s the call has no outcome. The `finally` removes the abort forward when the head arrives, so the abort never reaches the body. The head fixes this for the browser's kind.

**P2, a 429 whose body ends 5 s after the head, through the card cache**
- **Head:** there is no stop at 0, 2,000 or 4,999 ms. At 5,000 the stop starts with `until` T0+35,000. An autocomplete asked at 2 s **goes at 2,000**. The batch goes again at 35,000.
- **`main`:** the stop starts at 0 with `until` T0+30,000. The autocomplete waits until 30,000, and the batch goes again at 30,000.
- This is B3.

**P3, a 200 whose body errors 1 s after the head; one batch `["Outside Name","Sol Ring"]`.** Head and `main` read the same.
- **At 1 s:**
  - The lookup is `{status:'error', error:'scryfall 0', errorStatus:0}` in memory. Storage holds nothing for it.
  - The refresh keeps the file's price `$1.42`, dated the file's OLD date. Its `priceCheckedAt` is T0+1,000, in memory and in storage (`gv1-card:sol ring` = `{"fetchedAt":…,"priceCheckedAt":…}`).
  - No stop starts.
- **The same tab asks both again at 20 s:** nothing goes.
- **A second tab asks both at 22 s:** it sends `["Outside Name"]` only.
- **The first tab asks again at 32 s:** it sends `["Outside Name"]` (see N3).
- **The refresh** goes again only 24 h after its mark (at 86,401,001 ms).
- My reading is N2.

## 6. B items
**B1. Mutant R1 survives on the added line `scryfallLimiter.ts:456`, and on R1 the tab hangs again.**
- **The fault.** Some answer bodies send their first chunk with the head and then never end. On R1, the limiter gives the answer at the first chunk. The card cache's `response.json()` then waits forever, which is the bug of item (a) again.
- **The reading** (`mut/R1-hang.log`). On R1: one send, `Chunked` stays `loading`, and `Later`, asked at 31 s, is never sent. On the head: sends at 0, 50,000 and 51,200, and both names are `loaded` (`r1-hang-head.log`).
- **Why nothing catches it.** Every body fake in the suite enqueues all its bytes at once, so no case has a chunk before the body's end.
- **Fix.** Add the body kind `'one chunk, and never ends'` to the 8a loop (patch below). On R1 it fails (`proposed/P-R1.log`).

**B2. Mutant R3 survives on the added line `scryfallLimiter.ts:454`.**
- **The fault.** No case has a status other than 200 together with a body that does not end. So nothing pins what the head does for a 400, a 422 or a 429 in that state (section 4).
- **Fix.** Add the B4 cases for a 400 and a 422 whose body never ends. Each expects no stop at 19,999 ms, a stop with `until` T0+50,000 at 20 s, the batch again at 50,000, and `loaded`. On R3 both fail (`proposed/P-R3.log`).

**B3. A 429 now waits for its body before the stop starts (`scryfallLimiter.ts:454`; P2 and K3).**
- **The fault.** The limiter never gives a 429 to `settle`: the job goes back first in its bucket. So nobody needs the 429's body. Yet the head reads that body before `send()` checks the status. The stop starts when the body ends: at 5,000 ms in P2, where `main` starts it at 0. For a body that never ends, the stop starts at 20 s.
- **What a user would see.** During that gap no stop holds. In P2, an autocomplete goes at 2,000 ms on the head, while `main` holds it until 30,000. In K3 (a 429 whose body never ends), the head sends the autocomplete at 2,000 and the batch again at 50,000. `main` sends both at 30,000.
- **How likely it is.** Rare: Scryfall's 429 body is a short JSON object. But this is the rule that protects the app from a ban, and the fix is one condition.
- **Ruling 1.** The fault meets ruling 1's three tests: a user could see it, every case passes on the head, and the brief's shape would not have it. I do not ask to overturn the shape. The fix stays inside the head's shape.
- **Fix:**
```ts
      // A 429 is a stop at its head: nobody reads its body.
      if (response && wholeBody && response.status !== 429) {
```
- **The case.** Add the B4 429 case: the stop is `{until: T0+30,000}` at the head, the batch goes again at 30,000, and the name is `loaded`. When I put back the head's line (`if (response && wholeBody)`), this case fails (`proposed/P-no429.log`).
- **If you rule B3 a named limit instead,** leave line 454 as it is and drop the 429 case. K2 alone still closes B2.

**The tested fix for B1-B3** (`proposed/proposed.patch`, applied to `27e34a4`):
- `body-timeout.test.ts`: `Tests  10 passed (10)`.
- Whole unit suite: `Test Files  55 passed (55)` and `Tests  706 passed (706)`.
- typecheck: exit 0. lint: `0 errors, 10 warnings`.
- I did not run e2e on the patch. The fix round's step 7 runs it.
```diff
--- a/web/src/data/scryfallLimiter.ts
+++ b/web/src/data/scryfallLimiter.ts
@@ -451,7 +451,8 @@
       const response = await Promise.race([fetching, timeout]);
-      if (response && wholeBody) {
+      // A 429 is a stop at its head: nobody reads its body.
+      if (response && wholeBody && response.status !== 429) {
--- a/web/src/__tests__/dec1188/body-timeout.test.ts
+++ b/web/src/__tests__/dec1188/body-timeout.test.ts
@@ -9,0 +10 @@
+// B4: a 400 or a 422 whose body never ends is no answer either; a 429 stops at its head.
@@ type FirstBody
   | 'never ends, and errors at the abort'
+  | 'one chunk, and never ends'
@@
-/** A fetch whose head comes `headMs` after the send, and whose first body is `first`. */
-function bodyFetch(first: FirstBody, headMs = 0) {
+/** A fetch whose head comes `headMs` after the send, and whose first answer has `status` and the body `first`. */
+function bodyFetch(first: FirstBody, headMs = 0, status = 200) {
@@
         if (kind === 'whole') end();
+        else if (kind === 'one chunk, and never ends') controller.enqueue(bytes.slice(0, 10));
@@
-    }), { status: 200 });
+    }), { status: kind === 'whole' ? 200 : status });
@@ describe('DEC-1188 8a ...
-  for (const first of ['never ends', 'never ends, and errors at the abort'] as const) {
+  for (const first of ['never ends', 'never ends, and errors at the abort', 'one chunk, and never ends'] as const) {
@@ end of file
+describe('DEC-1188 B4: an answer of another status whose body never ends', () => {
+  for (const status of [400, 422]) {
+    it(`a ${status}: no answer at 20 s, a stop, and the batch goes again first`, async () => {
+      const a = bodyFetch('never ends', 0, status);
+      const cache = createCardCache({ storage, limiter: createScryfallLimiter({ fetchImpl: a.fetchImpl, storage, locks: fakeLocks() }) });
+      cache.enqueue('Open Body');
+      await advance(20_000 - 1);
+      expect(storedStop()).toBeNull();
+      await advance(1);
+      expect(storedStop()).toMatchObject({ until: T0 + 50_000, ms: 30_000 });
+      await advance(31_000);
+      expect(a.sends.map((s) => s.at)).toEqual([0, 50_000]);
+      expect(cache.get('Open Body')?.status).toBe('loaded');
+    });
+  }
+
+  it('a 429: the stop starts at its head, as for any 429', async () => {
+    const a = bodyFetch('never ends', 0, 429);
+    const cache = createCardCache({ storage, limiter: createScryfallLimiter({ fetchImpl: a.fetchImpl, storage, locks: fakeLocks() }) });
+    cache.enqueue('Open Body');
+    await advance(0);
+    expect(storedStop()).toMatchObject({ until: T0 + 30_000, ms: 30_000 });
+    await advance(31_000);
+    expect(a.sends.map((s) => s.at)).toEqual([0, 30_000]);
+    expect(cache.get('Open Body')?.status).toBe('loaded');
+  });
+});
```
The exact hunks are in `proposed/proposed.patch`, and the patched files are `proposed/body-timeout.test.ts` and `proposed/scryfallLimiter.ts`.

## 7. N items
**N1. P1: a body that ignores the abort turns the caller's abort into a stop.**
- A browser's body errors at the abort, and that kind behaves correctly: rejected at 5,000, no stop.
- Action: none. If you want the test double's kind closed too, race the read with `controller.signal`'s abort as a third promise.

**N2. P3, ruling 2: I recommend that a body error count as a rejected fetch, as a follow-up of priority low.**
- **Why.** A body that errors in the middle is a network fault, not the cards' answer. It is the same kind of fault as a fetch that rejects, and the header comment of `cardCache.ts` (lines 42-44) says that kind "is not the cards' failure". Today one network fault holds a /shopping price refresh for 24 h in that browser, and the price shown stays the file's old price.
- **The change** (`proposed/p3variant.patch`, lines 454-457 of the head):
```ts
      if (response && wholeBody) {
        // A body that fails before its end is a fetch that rejects.
        const read = response.clone().arrayBuffer().then(() => null, (error: unknown) => ({ error }));
        const failed = await Promise.race([read, timeout]);
        if (failed && !timedOut) return { response: null, error: failed.error, timedOut };
      }
```
- **What I measured with it** (`proposed/p3variant-vitest.log`):
  - At 1 s a stop starts with `until` T0+31,000.
  - The lookup stays `loading`, the refresh stays pending, and nothing is stored.
  - Both names go again at 31,000.
  - A caller's abort still counts as no failure: P1 reads the same as on the head.
  - Of the repository's cases, only B2 fails, because it pins today's outcome. It would change to expect the stop. `tsc -b` passes.
- **Scope.** A body that ends but is not JSON keeps the status 0 path.
- **Overlap with B3.** This change touches the same line as B3's fix. In a follow-up after B3, the condition becomes `response && wholeBody && response.status !== 429`.

**N3. Outside this PR; it is the same on `main`.**
- **The fault.** A tab's own error entry in memory hides a loaded entry that another tab stored. `enqueue` and `stillWanted` read `cache.get(key) ?? readPersisted(key)`. In P3, tab A sends `Outside Name` again at 32 s, although tab B stored it as `loaded` at 22 s. The cost is one extra request for each such name.
- Action: none in this PR. Note it for the next card-cache issue.

**N4. Wording: B2 shows that a body can also fail.**
- `scryfallLimiter.ts:110-111` says "The body of the answer has ended when it runs (DEC-1188)." Change it to "When it runs, the body of the answer has ended or has failed (DEC-1188)."
- `README.md:210` says "has its answer only when the body has ended". Change it to "has its answer only when the body has ended or failed".

**N5. Wording, an older sentence outside item 5's lines.**
- `README.md:212-213` says "the request that met it goes first when the stop ends". That holds inside one tab only. Case 8a shows that the other tab's B1 (50,000) goes before A1 (51,200).
- Proposed text: "the request that met it goes first in its tab when the stop ends". The limiter's header comment already says "stays first in its bucket".

## Trees
I remove `wt-dec1195` and `wt-dec1195-main` after this comment: `git status --porcelain` printed nothing in each, then `git worktree remove` without `--force`, then `git worktree prune`. I did not touch `wt-dec1188`, `/tmp/dec1188/` or the implementer's evidence folder. I sent no request to Scryfall.
