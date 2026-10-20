**Reviewer: the Frontend Engineer (`bc5c0753`). Tier 1, priority low. Budget: about 1.5 hours. Ports: `GRIMOIRE_E2E_PORT=14935` for the head tree and `14936` for the `main` tree. Web only. Do not push to the branch, and do not merge.** `<N>` is this issue's number.

CEO run that this issue's hand-back starts: read the STATE block at the top of [DEC-1199](/DEC/issues/DEC-1199) first, then the verdict.

## Why you
You reviewed PR #79 ([DEC-1193](/DEC/issues/DEC-1193)). PR #82 changes two specs from that work (`dec1177-empty-sigils.spec.ts` and `dec1190-glyph-names.spec.ts`), and you know both. You did not write PR #82. At the routing ({T}) you had no open issue and no queued run.

## What you review
- [PR #82](https://github.com/DioPires/mtg-precon-upgrader/pull/82), branch `dec-1199-one-mark`, head `014984a`, base `main` `e6d472e`. 8 files, +74 −17, all under `web/`.
- The brief is the description of DEC-1199, below its STATE block: the owner's answers A and B on card `345bc3b0`, the sites, the tests, the mutants M1 to M5 and the shot rule. The hand-back is comment `81ea90b7` on DEC-1199.
- The owner's answers, one line each:
  - **A.** The 3 /shopping boxes and the Compare box keep their 32 px `.gv1-rune` span (◇, or ◆ on "All cards owned"). Their 24 px `.gv1-empty::before` ◇ goes.
  - **B.** The two Combo Lab loading lines lose the inline `<Glyph>◇ </Glyph>`. The box's own `::before` ◇ (`combo-lab.css:255`) stays.
- CI on the head: `web-ci` run 39019266244 is green. It read lint `✖ 10 problems (0 errors, 10 warnings)`, Vitest `Test Files 57 passed (57)` and `Tests 719 passed (719)`, and Playwright `270 passed`. `main`'s push run 38964707867 on `e6d472e` read the same lint and Vitest lines and `266 passed`. The pull request adds 4 e2e cases and no Vitest case.
- The implementer's evidence, under `$PAPERCLIP_GITHUB_HOST_HOME/.paperclip/instances/default/workspaces/8ea33a50-69a7-4a75-bcc1-245bd1e7c73a/dec1199/`:
  - `shots/`: 56 files. Each of 7 states at 2 widths has a "before" and an "after" PNG, each with a JSON box size.
  - `kit/`: I copied it from `/tmp/dec1199/` at {T}, byte for byte (`diff -rq` printed nothing). It holds `shots.spec.ts` (the shot spec), `diff.cjs` (the pixel count), `diff-result.txt` (the hand-back's table), `mutate.py` and `mutants.sh` (M1 to M5), and the suite and mutant logs.

## My rulings on the hand-back (read these before the checklist)
1. **The control box does not test A's rule.** The implementer's control is the Combo Lab paste box. Its `::before` comes from `combo-lab.css:255`, `[data-gv1-screen="combolab"] .gv1-empty::before`, which is more specific than any `.gv1-empty` rule in `states.css`. So a leak of A's rule to every `.gv1-empty` would still read 0 px there. That control covers B only. Item 5 adds one control outside Combo Lab.
2. **Box heights.** Each A box is 44 px shorter after: 235 px to 191 px, and 249 px to 205 px for two boxes at 390 px. The brief expected a smaller box. I accept the 44 px if your reading of the `::before` line box plus the box's `gap` gives it.

## Checklist
1. **Basis.** Run `HOME="$PAPERCLIP_GITHUB_HOST_HOME" git fetch origin`. Check that `origin/dec-1199-one-mark` is `014984a`. Run `git diff --stat e6d472e origin/main -- web data .github` and quote what it prints. If it prints nothing, review the head. If it prints files, review the merged head: run `git merge-tree --write-tree origin/main origin/dec-1199-one-mark`, then `git commit-tree` of that tree with both parents, and make a detached tree on that commit. Name the basis in the verdict.
2. **Scope.** `git diff --stat e6d472e 014984a` lists the 8 files of the hand-back and no file outside `web/`. `git diff --stat e6d472e 014984a -- web/src/styles/styles.css web/src/components/atoms/Glyph.tsx` prints nothing.
3. **The brief's items.** Give the file and line of each on the basis, or name the item as missing.
   - **A, markup.** `gv1-empty--own-rune` is on exactly 4 containers: `Shopping.tsx:584`, `:821`, `:897` and `Compare.tsx:171`. Each container's first child is a `.gv1-rune` span. Quote `git grep -n gv1-empty--own-rune -- web/src ':!web/src/__tests__'`.
   - **A, rule.** `states.css` holds `.gv1-empty--own-rune::before { content: none; }` after `.gv1-empty::before`, with no `:has()`. Check that no later rule sets `::before` on these 4 boxes. `main.tsx:6` to `:11` imports `states.css` before `styles.css`, `app.css` and `combo-lab.css`. `combo-lab.css:255` applies only inside the `data-gv1-screen="combolab"` div of `ComboLab.tsx:539`.
   - **B.** `ComboLab.tsx:615` and `:629` hold the words alone, unchanged. The `Glyph` import stays, and the file still uses `<Glyph>`.
   - **Tests.** The two changed DEC-1177 cases and the two new ones call `expectOneMark`. The two new DEC-1190 cases call `expectOneLabMark`. The Vitest DEC-1177 cases of `Shopping.test.tsx` and `Compare.test.tsx` assert the class on all 4 boxes.
   - **The "All cards owned" case** writes `localStorage` key `grimoire-owned-cards`. The app reads that key (`OWNED_KEY`, `web/src/data/ownedCards.ts:13`). Check that the case reaches the state and does not pass on a fallback.
4. **Suites.** On the basis, run lint, typecheck, Vitest and the full Playwright suite with 3 workers at most. Quote each count line. Expected: lint `✖ 10 problems (0 errors, 10 warnings)`, Vitest `Test Files 57 passed (57)` and `Tests 719 passed (719)`, and Playwright `270 passed`. A count that differs is a B item unless you name its cause.
5. **Shots.** Copy `kit/shots.spec.ts` into a tree's `web/tests/` for a run, and delete it after the run; never commit it. Run it on the `main` tree with `DEC1199_TAG=before` and on the head tree with `DEC1199_TAG=after`. Set `DEC1199_SHOTS` to your own folder, `/tmp/dec<N>/shots/`. Run `kit/diff.cjs` on that folder; its first argument is the path of `pngjs` in a tree's `node_modules`. Then:
   - Compare your box sizes and changed-pixel counts with `kit/diff-result.txt`. Expected: the same sizes, 1,522 and 1,179 changed pixels for the two loading lines, and 0 for the control at both widths.
   - Open each pair by eye. Each A "after" shows one mark (the span) and the same words. Each B "after" shows one ◇ above the same words. Nothing else changes but the 44 px band.
   - Add one control outside Combo Lab (ruling 1): an empty box with no modifier that the stub reaches, for example `WinCons.tsx:18`, `Combos.tsx:18`, `Engine.tsx:23` or `Apothecary.tsx:158`. Take it at both widths on both trees. Expected: 0 changed pixels, and its `::before` computes `"◇" / ""` on both trees. If the stub reaches none of these boxes, name each one and why.
6. **Mutants.** A mutant that survives on a line that the pull request adds or rewrites is a B item. A rewritten line counts in full, also the words that `main` already had.
   - Rerun M1 to M5 with the implementer's runner. First copy `kit/mutants.sh` and `kit/mutate.py` to `/tmp/dec<N>/`. Then change the tree path, the log path (`/tmp/dec<N>/mut/`), the port (14935) and the path of `mutate.py`. Without these changes, your run edits the implementer's tree and writes over its logs.
   - Write and run your own mutants, at least these five. Each must fail at least one case:
     - R1: drop the modifier from `Shopping.tsx:584` ("No decks loaded.") alone.
     - R2: drop the modifier from `Shopping.tsx:821` ("All cards owned.") alone.
     - R3: `content: none` becomes `content: ''`. An empty string still makes a `::before` box, so the box keeps one more `gap`.
     - R4: move the new rule above `.gv1-empty::before`. Both selectors have the same specificity, so the later rule wins.
     - R5: the fleet loading line reads `◇ consulting the curated corpus …` as plain text, with no `Glyph`.
   - R6 is a guard, not a B item: add the modifier to `WinCons.tsx:18`, a box with no `.gv1-rune` span, so that the box loses its only mark. The pull request does not add that line. If R6 survives, give an N item. Give a guard case as exact text if you can write one in 15 minutes.
   - Run each mutant on the Vitest suite and on the two specs (`dec1177-empty-sigils.spec.ts` and `dec1190-glyph-names.spec.ts`), not on the full Playwright suite. Save one log for each under `/tmp/dec<N>/mut/`, and restore the file after each run. Before the verdict, check that `git status --porcelain` in your tree prints nothing.

## Not in this review
- The screen-reader text. PR #76 and PR #79 hid all these marks, and the DEC-1177 cases still read each message alone. A change there is a B item.
- Other empty boxes. The owner ruled on these 4 boxes and the 2 loading lines only.
- The mutant rule wins over this list: a mutant that survives on an added line is a B item even when a limit here names the gap.

## Setup
1. Make the head tree: `cd /Users/dpires/Documents/Personal/code/mtg-precon-upgrader && HOME="$PAPERCLIP_GITHUB_HOST_HOME" git fetch origin && HOME="$PAPERCLIP_GITHUB_HOST_HOME" git worktree add --detach wt-dec<N> origin/dec-1199-one-mark`. If item 1 gives a merged head, make this tree on that commit instead.
2. Make the `main` tree: `HOME="$PAPERCLIP_GITHUB_HOST_HOME" git worktree add --detach wt-dec<N>-main e6d472e`, or on `origin/main` if item 1 printed files.
3. Run `npm ci` in the `web/` of each tree. Or clone `node_modules` from the head tree with `cp -cR` when `cmp` shows the same `package-lock.json`.
4. Set `HOME="$PAPERCLIP_GITHUB_HOST_HOME"` for every `git` and `gh` command.
5. Set `PLAYWRIGHT_BROWSERS_PATH="$PAPERCLIP_GITHUB_HOST_HOME/Library/Caches/ms-playwright"` for every Playwright run. Set `GRIMOIRE_E2E_PORT=14935` in `wt-dec<N>` and `14936` in `wt-dec<N>-main`. Use 3 workers at most; the Mac is shared.
6. Send no request to `api.scryfall.com` or `cards.scryfall.io`. The e2e stub answers every case.
7. Keep scratch under `/tmp/dec<N>/`, and keep any scratch Playwright config outside the trees. Do not write into `wt-dec1199`, `/tmp/dec1199/` or the implementer's workspace folder.

## Verdict
Post one comment on this issue. Start it with `APPROVE at 014984a` (or at the merged head) or with `CHANGES`. Give:
1. The basis, with the output of item 1.
2. Items 2 and 3, each with its file and line.
3. The count line of each suite.
4. The shot table: each state and width, the box size before and after, the changed pixels, and your control outside Combo Lab.
5. Each mutant, its result, the failing case and the log path.
6. B items (they block the merge), each with the failing case or reading that shows it, and the fix as exact text where you can.
7. N items (they do not block), each with a proposed action.

Keep your evidence in `$PAPERCLIP_GITHUB_HOST_HOME/.paperclip/instances/default/workspaces/bc5c0753-6b0d-419c-9581-fa46ceb4a236/dec<N>/` and give that path.

## Handoff
1. Post the verdict comment.
2. Remove each of your scratch trees: `git status --porcelain` must print nothing, then run `git worktree remove <path>` (never `--force`), then `git worktree prune`. Name each tree in the verdict. Do not touch `wt-dec1199`.
3. As the last action of your run, send one PATCH on this issue: `assigneeAgentId` the CEO (`f9427c33-d719-4fd5-a3c5-cd2f65dd01e8`), `status: in_review`, and `executionPolicy.monitor` with `nextCheckAt` 30 minutes ahead, `scheduledBy: "assignee"` and `notes` under 500 characters that name your verdict comment.
4. If the server answers 422 `invalid_issue_disposition`, send the same PATCH again with `nextCheckAt` about ten hours ahead. Never set `done`.
5. **A question in the middle of the leg.** Do the parts that the question does not touch first. Post the question with its evidence, the count by cause, the readings and your recommendation. Then send the PATCH of step 3 as the last action of your run. Do not open a child issue assigned to the CEO (409 `delegation_cycle`).

planned-by: CEO (run `8d1902ed`). Source: DEC-1199 hand-back `81ea90b7`. Parent: DEC-1199.
