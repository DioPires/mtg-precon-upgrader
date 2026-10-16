**Verdict on PR #65 at `5d1a3b5`: CHANGES. Five B items, all test gaps; no product line needs a change.**

The code does what the brief asks. CI is green. Part A holds at 320 to 480 px and nothing changes above 480 px. Part B holds in Chromium's own accessibility tree. The style of both messages is unchanged. I ran 48 mutants of the lines that the PR adds or rewrites. 8 survive the unit and e2e suites, and none of the 8 is equivalent, so under item 10 they stand as B items. Each fix is a few test lines. I give each fix as exact text, and I ran it: it passes on the head and fails on its mutants.

## Guard (run at 19:41Z)
`origin/main` is now `822f2da`, not `b401b44`. `git diff --stat "$(git merge-base 5d1a3b5 origin/main)" origin/main -- web data .github` lists 21 files:
- `data/spellbook/price-index.json` and `price-index.meta.json` (PR #55). Only Combo Lab reads them.
- `web/src/components/organisms/DeckSelector.tsx` and its test (PR #59, `4b0b488`, 19:09Z). /shopping does not read it: only `routes/Scrying.tsx` and `routes/DeckGuide.tsx` import `DeckSelector`.
- `web/src/styles/styles.css` (+17 lines, PR #56, `b09f8be`). /shopping reads this file, but the change touches only `.gv1-cmd-*` rules (the deck guide's Commander band). `Shopping.tsx` holds no `gv1-cmd` class.
- `web/tests/dec1046-band-scale.spec.ts`, `web/tests/dec1046-commander-band.spec.ts` and 14 PNG files of DEC-1046. /shopping's pages do not read them.

`git merge-tree --write-tree origin/main 5d1a3b5` is clean (tree `b5998a5`). The PR's `@media (max-width: 480px)` block is byte-identical in that tree. The merged `web` subtree is `7ecfd225`, not `002a4d6c`, because of the files above.

## Items
1. **CI, run 38790883664 on `5d1a3b5`: success.** lint `✖ 10 problems (0 errors, 10 warnings)`. typecheck passes. `Test Files  51 passed (51)`, `Tests  600 passed (600)`. e2e `Running 182 tests using 2 workers` and `182 passed (10.2m)`. Logs: `/tmp/dec1163/logs/ci-unit.log` and `ci-e2e.log`.
2. **Merge commit: as stated.** `git show --remerge-diff 5d1a3b5` shows only these changes in `Shopping.test.tsx`: the three marker lines gone, `  });` and one blank line in place of `=======`, and `screen.getByRole('status')` changed to `importStatus()` at line 632. Mutant M0 (`const q = read;`, so the CSV path keeps -1) fails the PR #60 case at line 632:
   `Expected: Added 2 unique cards (2 total). 2 cards loaded. To replace the list, use Clear owned first.`
   `Received: ◆Added 2 unique cards (0 total). 0 cards loaded. To replace the list, use Clear owned first.`
   Log: `/tmp/dec1163/mutants/M0-unit0.log`.
3. **Part A on the head: `10 passed`.** In all 20 readings, the widest stat ends exactly at the box's content edge (overflow +0.0 px). Edges: 223, 263, 293, 333 and 383 px at 320, 360, 390, 430 and 480 px. This holds for fonts live and blocked, and for the first deck and every deck with the brewing decks. Log: `/tmp/dec1163/logs/head-partA.log`.
4. **Control: `10 failed`.** The run used the head with `origin/main`'s `styles.css`. The worst reading is "TOTAL UNIQUE" "1169" at 384.1 against an edge of 223 (+161.1 px, 320 px, fonts blocked, every deck). Log: `/tmp/dec1163/logs/control-partA.log`.
5. **Nothing changes above 480 px.** I compared `origin/main` (`4b0b488`'s `src`) with the head at 481, 600, 768, 1080 and 1440 px, with fonts live and blocked, for the first deck and for every deck. The summary and its 5 children give 120 readings: 120 equal, 0 differ. All 380 descendant boxes are equal too. The 20 summary shots are byte-identical. Data: `/tmp/dec1163/geom/{main,head}/`.
6. **Nothing passes the screen at 480 px and below.** At 320 px, fonts blocked, every deck: `scrollWidth` is 320. The widest element in the summary section is the section itself (right edge 256 px). The summary box's border edge is at 240 px. "A–Z" ends at 230.5 px against a content edge of 223 px: 7.5 px past the edge, inside the padding, as on `main`. "Copy buy list" ends at 226.9 px. The same holds at 360 to 480 px. Data: `/tmp/dec1163/geom/head/narrow-*.json`.
7. **Part B.**
   - (a) The cases check it. In the unit case at `Shopping.test.tsx:583`, `waitFor` reads the captured nodes, and lines 614 and 615 compare them with `toBe`. In `PricePausedLine.test.tsx`, line 56 captures the region, line 57 reads it empty, and lines 65 and 70 compare it with `toBe`. The e2e cases read each region empty, read its accessibility node, and compare `elementHandle` nodes after the text arrives.
   - (b) I read `Accessibility.getFullAXTree` at first paint, then after a count, an error, a second count and a second error. I also read it before and after a stop. In every step: the import status region is `status`/`polite`, the import alert region is `alert`/`assertive`, and the stop-line region is `status`/`polite`. All three are atomic, none is ignored, and they are the only live nodes in the tree. Data: `/tmp/dec1163/ax/head/{import,stop}.json`.
   - (c) Holds in the browser for the sequence count, error, count, error. A count goes only to the status region. An error goes only to the alert region. Each message empties the other region.
8. **Test edits: each case keeps its assertion.** Each of the 9 calls (lines 488, 495, 514, 521, 543, 550, 560, 570 and 576), and the merge's line 632, changes only `screen.getByRole('status')` to `importStatus()`. Mutant T1 changes the message's words and fails at lines 488, 514, 543, 560, 570 and 632. Mutant T2 makes the loaded count read the file, not the list. It fails the second calls at lines 495, 521, 550 and 576. In `PricePausedLine.test.tsx`, each `toBeNull()` that became `toBeEmptyDOMElement()` still fails when the line shows while it should not:
   - line 45 fails on P2a (`waiting` dropped);
   - lines 48 and 57 fail on P2b (`until !== null` dropped);
   - line 69 fails on T3 (the end-of-stop render comes 60 s late).

   `queryByRole` became `getByRole`, which is stricter. The new class check at line 38 kills P3a and P3b. Logs: `/tmp/dec1163/mutants/{T1,T2,T3,P2a,P2b}-unit0.log`.
9. **Style: unchanged.** At 390 and 1440 px, with fonts live and blocked, I read `main` and the head. I read the count, the error and the stop line: size, margin, padding, border, colour, background, font and each child's style. I also read the offset from the element above (the owned bar, or the summary's bottom for the stop line) and the top and height of every section. 486 values are equal and 18 differ. All 18 are at 390 px: Part A makes the summary section 28 px shorter, and the sections below it move up 28 px. The import shots are byte-identical (8 of 8). The first stop-line shots differ, because the line's background is transparent and the clock time changes. With the clock text fixed and an opaque backdrop, the 4 stop-line shots have 0 differing pixels. Data: `/tmp/dec1163/style/{main,head}/` and `/tmp/dec1163/stopshot/`.
10. **Mutants: 48 of the PR's lines; 40 killed and 8 survive.** Runner: `/tmp/dec1163/mutants/run.py`. Table: `mutants.py`. Results: `batch1.jsonl`. The killing cases of each mutant: `killers.txt`. Every added code line has at least one mutant. The comment lines have none. The closing lines are covered by the "region renders only with its text" mutants (S11a, S11b, P2c) and by P3c. Among the killed mutants are all the brief's mutants:
    - the error region's role changed to `status`: S6a;
    - the error put in the status region: S6c;
    - the stop line's wrapper without its role: P1a;
    - `flex: 1 1 0` changed to `0 1 auto`: C3b, killed 10 of 10. The change to `1 1 auto` is C3a, which **survives** (B5);
    - the 28 px rule removed: C4a, killed at 320 px with the fonts blocked;
    - `flex: 1 1 100%` removed: C5a, killed at 480 px;
    - `nowrap` removed: C6a, killed at 320 px;
    - the media query at 430 px: C1a, killed at 480 px.

    S7b, P2a, P2b and P6a also stop the e2e build (the web server exits with code 2), and the unit suite kills each of them.
11. **The removed 768 px line.** `git grep -n "gv1-shop-summary-stat" 5d1a3b5 -- web` gives only `web/src/styles/styles.css:3370`, the new comment.

## B items (they block the merge)
**B1. The import message's spans can lose `gv1-mono-xs` and no test fails.**
- Lines: `Shopping.tsx:733`, `:734`, `:741` and `:742`. These lines are rewritten: `main`'s `{importMsg.ok ? '◆' : '⚠'}` span was split in two, and the text span was re-indented.
- Mutants: S4a, S5a, S9a and S10a each drop `className="gv1-mono-xs"` from one span. The input is any import. The part then renders in the inherited 16 px serif, not 11 px mono.
- The mutants pass all 600 unit tests and the 26 cases of the four e2e specs that cover the import and the stop line (`dec1154-shop-live-regions`, `dec1083-shop-import-keyboard`, `dec942-owned-quota` and `dec1131-card-batches`).
- The kill case `/tmp/dec1163/kill/dec1163-kill-import-style.test.tsx` fails on each mutant. Logs: `/tmp/dec1163/kill/kill-{S4a,S5a,S9a,S10a}-unit.log`.
- Fix (verified; logs `/tmp/dec1163/fix/fix-{S4a,S5a,S9a,S10a}-unit.log`): in the DEC-1154 case of `Shopping.test.tsx`, add one line after line 603 and one after line 610:
  ```ts
      expect([...status.firstElementChild!.children].map((el) => el.className)).toEqual(['gv1-mono-xs', 'gv1-mono-xs']);
  ```
  ```ts
      expect([...alert.firstElementChild!.children].map((el) => el.className)).toEqual(['gv1-mono-xs', 'gv1-mono-xs']);
  ```

**B2. The stop line can become a `<div>` and no test fails.**
- Line: `PricePausedLine.tsx:39` and its `</p>`. P3c changes the `<p>` to a `<div>`.
- Effect: the `<p>`'s 11 px bottom margin goes (computed margin `8px 0px 11px`), so the summary section gets 11 px shorter.
- Kill: `/tmp/dec1163/kill/kill-P3c-unit.log` (`Expected: "P"`, `Received: "DIV"`).
- Fix (verified, `/tmp/dec1163/fix/fix-P3c-unit.log`): after `PricePausedLine.test.tsx:38`, add:
  ```ts
      expect(line().firstElementChild?.tagName).toBe('P');
  ```

**B3. No test renders the stop line without a date.**
- Line: `PricePausedLine.tsx:41`. P5a makes the date sentence unconditional.
- The input is `pricesDate={null}`, which the declared type `string | null` allows. The line then reads "Price refresh paused. Prices shown are from null. Next try at 13:00:30."
- Kill: `/tmp/dec1163/kill/kill-P5a-unit.log`.
- Fix (verified, `/tmp/dec1163/fix/fix-P5a-unit.log`): add this case to `PricePausedLine.test.tsx`:
  ```tsx
    it('leaves out the date of the prices when it is unknown', () => {
      storage.setItem(STOP_KEY, JSON.stringify({ until: T0 + 30_000, ms: 30_000, n: 1 }));
      const limiter = createScryfallLimiter({ fetchImpl: fakeScryfall().fetch, storage, locks: null });
      render(<PricePausedLine waiting pricesDate={null} limiter={limiter} />);
      expect(line().textContent).toBe(`Price refresh paused. Next try at ${clockTime(T0 + 30_000)}.`);
    });
  ```

**B4. No test holds the rule's upper bound.**
- Line: `styles.css:3373`. C1b changes `max-width: 480px` to `600px`.
- Effect: at 481 to 600 px the summary changes from the 3-column grid with 42 px figures to the phone layout. All 10 cases of the summary spec still pass.
- The kill cases fail at 481 px with fonts live and blocked: `"display": "flex"` against `"grid"`, and `28px` against `42px`. Log: `/tmp/dec1163/kill/kill-C1b-e2e.log`.
- Fix: add the cases "at 480px / at 481px the summary is a flex / grid box with 28px / 42px figures" from `/tmp/dec1163/kill/dec1163-kill-summary.spec.ts` to `tests/dec1154-shop-summary.spec.ts`. The assertion:
  ```ts
  expect(read).toEqual({ display, figures: [figure, figure, figure, figure] });
  ```
  where `read` is the summary's computed `display` and the computed `font-size` of each `.gv1-shop-stat .gv1-serif-xl`.

**B5. No test holds the packing that `flex: 1 1 0` gives.**
- Line: `styles.css:3375`. C3a changes it to `flex: 1 1 auto`.
- Effect: all 20 readings of the spec differ. At 320 px each stat takes its own line. At 390 px two stats share a line, not three, and the summary gets taller. The spec still passes 10 of 10 (compare `/tmp/dec1163/logs/head-partA.log` with `/tmp/dec1163/mutants/C3a-e2e0.log`).
- The PR's own comment states the rule: "a line takes as many stats as their narrowest widths allow".
- The kill cases check that rule. For each line of stats but the last, the next line's first stat must not fit on the line at the stats' min-content widths. They fail 10 of 10 on C3a. For example, at 390 px with fonts blocked, the three stats need 152.4 px of 196 px. Log: `/tmp/dec1163/kill/kill-C3a-e2e.log`.
- Fix: add the cases "at <width>px a line of stats takes every stat that fits at its narrowest width" and the `packing()` helper from `/tmp/dec1163/kill/dec1163-kill-summary.spec.ts` to `tests/dec1154-shop-summary.spec.ts`.

The kill files are under `/tmp/dec1163/kill/`: `dec1163-kill-import-style.test.tsx`, `dec1163-kill-paused-line.test.tsx` and `dec1163-kill-summary.spec.ts`. Runner: `run_kills.py`. On the head, the kill files pass: 3 of 3 unit (`kill-HEAD-unit.log`) and 14 of 14 e2e with fonts live and blocked (`kill-HEAD-e2e.log`). I ran `npm run typecheck` once with the three kill files in the tree: exit 0 (`/tmp/dec1163/kill/typecheck.log`). I also ran it once with the fix lines in the PR's test files: exit 0 (`/tmp/dec1163/fix/fix-typecheck.log`). The fix lines pass on the head: 54 of 54 in the two files (`/tmp/dec1163/fix/fix-HEAD-unit.log`). Diffs: `/tmp/dec1163/fix/fix-*.diff`.

## N items (notes)
- **N1 (ruling 6, the stop-line region needs a selected deck).** I reproduced it on the head with a stop held. Clear removes the region. Selecting a deck brings a new node (backend id 1602, not 64) that arrives with its text. This exact change keeps one region from first paint, and I ran it (`/tmp/dec1163/n2-trial.diff`):
  ```diff
  -      {selected.size > 0 && (
  -        <section className="gv1-section gv1-shop-section">
  +      <section className={selected.size > 0 ? 'gv1-section gv1-shop-section' : undefined}>
  +        {selected.size > 0 && (
             <div className="gv1-shop-summary">
  ...
             </div>
  -          <PricePausedLine waiting={waitingForPrice} pricesDate={shownPricesDate} />
  -        </section>
  -      )}
  +        )}
  +        <PricePausedLine waiting={waitingForPrice} pricesDate={shownPricesDate} />
  +      </section>
  ```
  The checks with the change:
  - The region is the same accessibility node (21) through the stop, Clear and a new selection, and it stays `status`/`polite`.
  - While no deck is selected, the section has no class and a height of 0 px, and the other sections keep their tops and heights. `waitingForPrice` is false then, because `buy` and `own` are empty.
  - The layout matches the head: 120 of 120 boxes, 380 of 380 descendant boxes, 504 of 504 style values and 20 of 20 shots.
  - `Tests  600 passed (600)`, and 76 of 76 e2e cases in the nine specs that visit /shopping.

  Logs: `/tmp/dec1163/logs/n2-*.log` and `/tmp/dec1163/n2/`.
- **N2 (ruling 7, the sigils are read aloud).** Exact change: `aria-hidden="true"` on the two sigil spans, as the import button's `⬆` already has.
  ```tsx
                <span className="gv1-mono-xs" aria-hidden="true">◆</span>
                <span className="gv1-mono-xs" aria-hidden="true">⚠</span>
  ```
  Chromium's tree then gives each region only the message text: `["ADDED 1 UNIQUE CARD …"]`, where the head gives `["◆", "ADDED 1 UNIQUE CARD …"]`. The words in the DOM and the tests' `textContent` checks do not change. Style: 504 of 504 values equal, and the import shots are byte-identical. `Tests  600 passed (600)`, and 13 of 13 import e2e cases pass. Logs: `/tmp/dec1163/logs/n3-*.log` and `/tmp/dec1163/n3/`.
- **N3 (no action needed).** At 320 to 430 px the labels wrap inside their stats ("NEED TO / BUY", "ALREADY / OWN"). That is the packing that the PR describes, and no text passes its stat. Shots: `/tmp/dec1163/out-head-A/`.

## Tree
I removed `wt-dec1163-review`. `git status --porcelain` printed nothing, then I ran `git worktree remove wt-dec1163-review` and `git worktree prune`. All scratch files stay under `/tmp/dec1163/`. I pushed nothing.
