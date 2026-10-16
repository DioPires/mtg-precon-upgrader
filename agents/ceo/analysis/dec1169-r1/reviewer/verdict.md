**CHANGES: one B item, a test case only (route A).** PR #69 at `64f2146` meets items 1 and 3 in the code, and every seeded mutant dies as the hand-back says. One mutant of my own survives and is not equivalent. R1 drops the test that focus fell to `body` from case (a), and no unit or e2e case kills it. The kill case K1 is below. The code needs no change.

**Basis.** `origin/main` was `02d085c` at the start. The merged head is `e88a78d` (detached). `git rev-parse HEAD^{tree}` and `git merge-tree --write-tree origin/main 64f2146…` both read `9587e25dca75970aa2932fd3f1f33550050f8dd7`. The merged head's `web` subtree is `c87dded4`, the same as the head's own. During the review `main` moved to `a4cd315`, but not under `web/`, `data/` or `.github/` (`git diff --stat 02d085c origin/main -- web data .github` prints nothing). I kept the basis `02d085c`. All logs and scratch files are in `$PAPERCLIP_GITHUB_HOST_HOME/.paperclip/instances/default/workspaces/6ba3ac88-12e8-41a7-834f-98e3d92dae78/dec1169-review/` (a copy of `/tmp/dec1146-review/`).

## B items
**B1. Mutant R1 survives: no case pins "focus fell to `body`" in case (a).**
- Mutant: `DeckSelector.tsx:256`, `const left = !before.isConnected && (!now || now === document.body);` becomes `const left = !before.isConnected;`.
- Unit file: `Tests  33 passed (33)` (`own/logs/log-R1.txt`). e2e spec: `6 passed (5.0s)` (`own/logs/log-R1-e2e.txt`).
- Not equivalent. Take a deck change that removes the focused element while another element outside the track takes focus in the same commit, for example an element of the new deck with `autoFocus`, or a layout effect that calls `focus()`. The head leaves focus on that element. The mutant moves focus to the active pill. Item 1 step 2 says "move no focus when focus is on an element outside the track that stays on the page".
- Kill case K1: `dec1169-review/kill/DeckSelector.dec1169-kill.test.tsx`. Its harness renders the selector, a `Board Wipes` button with `key={active}`, and an `<input aria-label="Search" autoFocus />` that only deck 5 renders. Focus the chip, then `route(5)`. Expect: the chip is disconnected, pill 5 is active, and `document.activeElement` is the Search input.
- Kill run. On the merged head it passes (`strict/run-merged-head.log`: `✓ … K1`). On R1: `Tests  1 failed (1)`, `AssertionError: expected <button role="tab" …(6)>…(5)</button> to be <input aria-label="Search"></input>` (`kill/log-K1-on-R1.txt`). With the file in the tree, `npm run typecheck` exited 0 and `npx eslint` on it exited 0 (`kill/typecheck.log`, `kill/eslint.log`). I then removed it.
- Fix: add K1, or an equal case, to the DEC-1146 block of `DeckSelector.test.tsx`, and show that it kills R1.

## 1. The code against items 1 and 3 (line numbers on the merged head, the same as `64f2146`)
1. **Item 1, steps 1 to 3, and item 3, step 2.**
   - Cases (a) and (b) use `focusActive` (`:108-110`), which calls `.focus({ preventScroll: true })`. The new branch is `:131`: `else if (before && strayed(before, trackRef.current)) focusActive();`. Case (a) is `:256` and case (b) is `:257` (`!!now && !!track?.contains(now) && !now.classList.contains('gv1-active')`).
   - The first mount: `:121` `useRef(activeIdx)`, so the first render records nothing (`:123-126`), and `before &&` stops at `null`.
   - Nothing focused: `before` is `body`, which stays connected, and `body` is not in the track.
   - Focus outside the track on an element that stays: `before` stays connected, and `now` is not in the track.
   - A click switch: the clicked pill carries `gv1-active` after the commit, so `onOldPill` is false.
   - The key switch: `:130` `if (keyTarget.current === activeIdx) focusActive();` comes first. `:132` `keyTarget.current = null;` is the effect's last line, before `}, [activeIdx, focusActive]);`.
   - Item 3: `DeckGuide.tsx:52` and `Scrying.tsx:47`, `if (next && next.idx !== deck.idx) navigate(…)`.
2. **The record in render: no path leaves a wrong record today.**
   - **A second render (StrictMode, development builds only).** For an update, both calls share the hook's ref objects. The first call records and sets `renderedIdx`. The second call sees `renderedIdx === activeIdx` and records nothing. Both calls run in one synchronous pass, so the first read is the right one. At the mount both calls start `renderedIdx` at `activeIdx`. StrictMode's second effect run at the mount reads `null`.
   - **A render that React throws away.** `git grep` finds no `Suspense`, `lazy`, `startTransition`, `useTransition`, `useDeferredValue` or error boundary in `web/src`. Back, Forward, a click and a key are discrete events, so React 18 renders the route update at the sync lane, and that render never yields. A sync render that throws is rendered again at once. The discarded pass records, and the retry does not. Both happen in the same task with no DOM change between them, so the record is right.
   - **A new render with the same `activeIdx`.** It records nothing, and the effect does not run because its deps did not change.
   - Scratch evidence: `strict/DeckSelector.dec1169-strict.test.tsx` under `<StrictMode>`, `Tests  8 passed (8)` with K1 (`strict/run-merged-head.log`). S1 case (a): the update renders twice, then one focus call with `{ preventScroll: true }`. S2 case (b). S3 a first mount that removes a focused element: no focus call. S4 nothing focused and S5 outside the track: no focus call. S6 a render that throws once at deck 5, then case (a): one focus call, on pill 5. S7 the same with nothing focused: no focus call. S8 a render with the same `activeIdx` while the chip has focus, then `Stays` takes focus, then `route(5)`: no focus call.
   - The limit is note N4.
3. **A stub pill.** At Back, `strayed` reads a focused stub pill as case (b) and moves focus to the active pill, with no scroll. Scratch case S9 (`strict/DeckSelector.dec1169-stub.test.tsx`, `strict/run-stub.log`): focus and click the stub pill. Nothing opens. Then `route(2)`: focus is on pill 2, after one call with `{ preventScroll: true }`. A user sees no fault. The tabs pattern puts focus on the active tab, and no key reaches a stub pill (`tabIndex` -1, and the keys skip unscribed decks). Item 1 (b) names "a pill that is no longer active". A stub pill was never active, so this is outside its words but within its purpose. The rail holds no stub pill today (see check 4).
4. **The open-deck check drops no real pick.** `useDeckBundle.ts:55` computes `deck` as `decks.find((d) => d.slug === id)` in the same render that reads `id` from the URL. `status` can lag `id` by one render, but `deck` cannot. If the URL names no loaded deck, `deck` is `null`, and the route renders no selector. The selector holds the `onSelect` of the last commit. A Back or Forward update commits in a microtask, before any later input event. So `deck.idx` is the URL's deck at every pick, and `next.idx !== deck.idx` drops only a pick of the open deck. One more effect is note N6.
5. **N4 of the hand-back holds.** R8 (`<DeckSelector key={deck.slug} …>` in `DeckGuide.tsx`) on the e2e spec reads `4 failed | 2 passed (6.5s)`. All four focus cases fail at both widths: `Back after a chip press …` (case (a)) and `Back after a click switch …` (case (b)). So the claim is true, and it covers case (b) too.

## 2. The seeded mutants (kit `mut.py`; `seed/`, `seed-14849/`)
All six match the hand-back. The tree was clean after each run.
- M2: `Tests  1 failed | 32 passed (33)`. Failed: `moves no focus at the first mount`.
- M3: `Tests  2 failed | 31 passed (33)`. Failed: `moves focus to the active pill when focus is on a pill that is no longer active`, and the rewritten PR #59 case `moves no focus at a deck change that no key started from nothing focused, and moves it off the old pill after a key switch`.
- M4: `Tests  1 failed | 32 passed (33)`. Failed: `moves focus to the active pill when the focused element left the page`.
- M6 (e2e, port 14849): `1 failed | 5 passed (6.5s)`. Failed: `/deck: Home and a click on the active pill keep history.length`.
- M7 (e2e, port 14849): `1 failed | 5 passed (5.3s)`. Failed: `/scrying: Home and a click on the active pill keep history.length`.
- RA-M4: `Tests  1 failed | 32 passed (33)`. Failed: `… review cases (DEC-1148) > moves no focus when a route returns to the deck that an earlier key picked`.

## 3. My mutants (`own/own-mutants.json`, `own/own-mutants-2.json`; logs in `own/logs/`)
Killed on the unit file:
- R2 (`!!before && (!now || now === document.body)`, no `isConnected` test): `2 failed | 31 passed`. Failed: `moves no focus when nothing had focus before the change` and the rewritten PR #59 case.
- R3 (no `gv1-active` test): `1 failed`. Failed: `leaves focus on a clicked pill and makes no focus call`.
- R4 (`true` for `track?.contains(now)`): `4 failed`.
- R6 (no `renderedIdx.current = activeIdx;`): `1 failed`. Failed: the case (b) test.
- R11 (record at every render): `1 failed`. Failed: first mount.
- R12 (record `document.body`): `1 failed`. Failed: case (a).
- R14 (the new branch focuses with no `preventScroll`): `2 failed`. Failed: cases (a) and (b).
- R16 (`now = before`): `1 failed`. Failed: case (a).
- R19 (`focusBefore` starts at `document.activeElement`): `1 failed`. Failed: first mount.
- R20 (`left && onOldPill`): `3 failed`.
- R21 (`before.isConnected`): `3 failed`.

Killed on the e2e spec:
- R8: `4 failed | 2 passed` (check 1.5).
- R9 (`===` in `DeckGuide.tsx`): `5 failed | 1 passed`.
- R10 (`===` in `Scrying.tsx`): `1 failed | 5 passed`. Failed: the `/scrying` history case.

Survivors (`33 passed` on the unit file and `6 passed` on the e2e spec):
- R1: B1.
- R5 (no `focusBefore.current = null;`) is equivalent. The effect runs only when `activeIdx` changes, because `focusActive` is stable. React runs a commit's passive effects before it starts the next render. So at an effect run for `a`, `renderedIdx` is `a`. The next run, for `b`, follows a render that recorded after the first run. The clear is never read.
- R7 (`if` for `else if`) is equivalent. After the key branch's `focusActive()`, focus is on the `.gv1-active` element, so `left` and `onOldPill` are both false. If the track has no `.gv1-active` element, a second `focusActive()` makes no call either. The only difference: when the active pill cannot take focus, the mutant makes a second call that also fails.
- R13 (no `!now ||`) is equivalent. `document.activeElement` is `null` only in a document with no root element.
- R17 and R18 (`next!` in place of `next &&`, in each route) are equivalent. The selector reports only the `idx` of an element of its `decks` prop, and that prop is the `stubs` array that the route searches in the same render. The `next` check also predates the pull request.

## 4. Browser reads
I used Playwright at 390 × 844 on port 14849, through a scratch config (the tree's config with no `webServer`) and the tree's Scryfall stub (`cards: 'seeded'`). The merged head's build is `index-Bio0ff-4.js`. A wrapper on `HTMLElement.prototype.focus` counts the calls. Logs: `read/`.
1. **Chromium 147, N2's steps** (`read/chromium-merged.log`):
   - Before Back: `/deck/titan-convergence`, `BUTTON`, no role, "Board Wipes2 / 3", in the Apothecary, `scrollY` 21389.
   - After Back: `/deck/stampede-acres`, `BUTTON`, role `tab`, `aria-selected` `true`, `tabIndex` 0, "Field of Blades", `scrollY` 0. One focus call: Field of Blades, `{"preventScroll":true}`. A timeline (`read/scroll-merged.log`) shows the call at 17 to 18 ms, with `scrollY` 21389 before and after it. The browser's own scroll restoration sets 0 at 35 to 39 ms.
   - After one Tab: `BUTTON`, role `tab`, `aria-selected` `true`, `tabIndex` 0, "01Token Producers16" (the Engine's first tab), not in the Apothecary, `scrollY` 3758, no focus call.
   - After Forward: `/deck/titan-convergence`. Focus stays on the same Engine tab, whose text now reads "01Game Changers ★2". It has role `tab`, `aria-selected` `true` and `tabIndex` 0, `scrollY` is 21389, and there is no focus call. This is not case (b): after the Tab, focus is outside the track on an element that stays, so step 2 holds.
   - Forward with no Tab, which is case (b): the "Titan Convergence" pill, role `tab`, `aria-selected` `true`, `tabIndex` 0, `scrollY` 21389, one call with `{"preventScroll":true}`. See N2.
2. **A stub pill: skipped.** The rail holds none (`.gv1-stub` count 0 on `/deck/titan-convergence`). Check 1.3 covers it in jsdom.
3. **Control** with `main`'s `DeckSelector.tsx` (build `index-BvMBxIaK.js`, `read/control.log`). After Back: `BODY`, `tabIndex` -1, `scrollY` 0, no focus call. After the Tab: `BUTTON` "Show breakdown" in the Apothecary, `scrollY` 18983, the same as the DEC-1135 hand-back. Forward: `BODY`, `scrollY` 21389. I restored the file and rebuilt; the build is `index-Bio0ff-4.js` again, and the tree was clean.
4. **WebKit 26.4** (`webkit.launch()` started and printed `26.4`; `read/webkit-merged.log`):
   - The pill click focuses the pill. The pill has an explicit `tabindex`, and WebKit focuses such a button on a click.
   - The chip press leaves focus on `BODY` (`scrollY` 21390). The chip has no `tabindex`, so WebKit does not focus it.
   - After Back: `BODY`, `scrollY` 0, no focus call. Nothing had focus, so step 2 holds.
   - After the Tab: "Field of Blades", role `tab`, `aria-selected` `true`, `tabIndex` 0, `scrollY` 0.
   - After Forward: "Titan Convergence", `aria-selected` `true`, `tabIndex` 0, `scrollY` 21390, one call with `preventScroll` (case (b)). On `main`, the same Forward leaves focus on "Field of Blades" with `aria-selected` `false` and `tabIndex` -1.
   - A user sees no fault. A WebKit user who clicks the chip has no focus to lose, and the first Tab goes to the rail, on `main` too.
   - Added read, the chip focused from the keyboard and then Back (`read/keyboard-chip-merged.log`). WebKit: "Field of Blades", one `preventScroll` call, `scrollY` 233. The Tab goes to "01Token Producers16" at `scrollY` 3781. Chromium: the same pill at `scrollY` 0, and the Tab goes to the same tab at 3758. For the 233, see N3.

## 5. The suite on the merged head
- `npm run lint`: `✖ 10 problems (0 errors, 10 warnings)`. `npm run typecheck`: exit 0. `npm test -- --run`: `Test Files  51 passed (51)` and `Tests  615 passed (615)`.
- Local specs (port 14849): `dec1146-selector-back-focus` `6 passed (4.6s)`. `dec1048-selector-rail` `11 passed (30.5s)`, so the first Tab from load still holds. `dec1077-apothecary-deck-switch` `1 passed (4.2s)`.
- Basis: push run 38792978708 on `b09f8be` (PR #56). `git log origin/main -- web` names `b09f8be` as the newest change under `web/`. It read lint 0 errors and 10 warnings, `Test Files  51 passed (51)`, `Tests  610 passed (610)` and `179 passed (9.4m)`.
- Additions, from `git diff origin/main...64f2146` on the test files:
  - Unit: 6 `it(` lines added and 1 removed. The removed line is the PR #59 case, which comes back under its new name. So the net is +5.
  - e2e: 2 `test(` in a loop over 2 widths, and 1 `test(` in a loop over 2 routes, so +6.
- Expected: 51 files, 615 tests, 185 cases. Read on head run 38815410508 (`pull_request`, `64f2146`; `lint-typecheck-unit` 116698712092 and `e2e` 116699411460 both passed): lint 0 errors and 10 warnings, `Test Files  51 passed (51)`, `Tests  615 passed (615)`, `185 passed (10.4m)`. The log has no flaky line and no failed line. The sums match.

## 6. The tree
I removed `wt-dec1146-rev-head`. `git status --porcelain` printed nothing, `git worktree remove` exited 0 with no `--force`, and `git worktree prune` exited 0. The tree was detached, so there was no branch to delete. I did not touch `wt-dec1146`.

## Notes (N), not blocking
- **N1. Port collision.** From about 22:37Z, a `vite preview` of `/private/tmp/dec1166-ceo/wt` held port 14846. My first M7 run failed at start with `Port 14846 is already in use`. The first M6 run had started its own server before that and read `1 failed | 5 passed (7.9s)`. I took 14849 for M6 and M7 again (`seed-mutants-14849.json`, changed only in the port), for my e2e mutants, for the browser reads and for the specs.
- **N2. Forward puts focus on a pill above the viewport.** On Forward, the browser restores the entry's scroll position (21389 in N2's steps), and the focus call does not scroll. The focused pill is then above the viewport. The next Tab goes to the Engine and scrolls the page up to about 3758. The focus call does not scroll the page, and item 1 asks for this focus, so this is not a defect of PR #69. Recommendation: no change here. The CEO can weigh it if Forward matters.
- **N3. WebKit's `scrollY` after Back varies, also on `main`.** On `main`, which makes no focus call here, WebKit read 233 once and 0 once in the keyboard-chip runs, and 0, 0 and 233 in the mouse runs. On the merged head I read 233 in 2 of 2 keyboard-chip runs and 0 in 3 of 3 mouse runs. The track's top is at 229 in the document. So the 233 comes from a race between WebKit's scroll restoration and the DEC-1048 centring's `window.scrollBy`, not from the focus call (`before` equals `after` at the call). My few runs cannot show whether the focus call makes 233 more likely. The page then shows the rail at the top edge. CI runs Chromium only.
- **N4. The record in render depends on synchronous route renders.** Suppose the app adopts React Router's `v7_startTransition` flag or v7. A route render can then yield and start again. The second attempt does not read focus again, so a focus change between the two attempts leaves a stale record. Example: the user clears focus during the yielded render, and Back still moves focus to the pill. No path exists today. A `focusout` record would not have this limit.
- **N5. A comment is narrower than the code.** The comment at `:117` says "(b) Focus is on a pill that is no longer active". `strayed` acts on any pill without `gv1-active`, stub pills included (check 1.3). A one-word fix ("not active") is optional.
- **N6. The open-deck check also keeps the URL's query.** `Decklist` keeps `?manifest=` in the URL. On `main`, a click on the active pill pushed the bare path and reset that mode. With PR #69 the URL does not change. No deck pick is lost.

## Steps that I changed or added
1. Port 14849 for every e2e run and preview server after the collision (N1). The kit's own file is unchanged.
2. Check 4.2 was skipped in the browser because the rail has no stub pill. A jsdom case covers it.
3. Check 4.1: I quoted Forward after the Tab as the brief asks. That Forward is not case (b), so I added a Forward with no Tab, which is.
4. I added reads that the brief did not ask for: a scroll timeline in both browsers, and a chip focused from the keyboard in both browsers.
5. The browser reads ran through a scratch Playwright spec with the tree's Scryfall stub, not through a standalone script. No request went to Scryfall or Moxfield, and I used no card tools.
6. I wrote R2 and R4 so that the e2e build would still pass (`!!before && …` and `!!track && true &&`). Both died on the unit file, so neither ran on the e2e spec.
