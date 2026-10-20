**Implementer: the Design System Engineer (`8ea33a50`). Tier 1, priority low. Budget: about 1.5 hours. Port: `GRIMOIRE_E2E_PORT=14917`. Web only. One pull request; do not merge it.**

## The owner's decision
The owner answered card `345bc3b0` on [DEC-1182](/DEC/issues/DEC-1182) at 2026-10-17 08:43Z. Both answers are the options that your census recommended (DEC-1182 hand-back `12805aca`, section 4):
- **A. /shopping (3 boxes) and Compare (1 box): "Keep the larger mark, drop the small one."** The `.gv1-rune` span stays (◇, or ◆ on "All cards owned", 32 px). The `.gv1-empty::before` ◇ (24 px) goes in these 4 boxes only.
- **B. Combo Lab loading line: "Drop the ◇ inside the text, keep one mark."** The inline `<Glyph>◇ </Glyph>` goes. The `::before` ◇ of `combo-lab.css` stays.

Screen readers already skip all of these marks (PR #76 and PR #79), so what a reader hears does not change. Only what users see changes.

## The sites on `main` `e6d472e`
Read each line again on your tree; `main` can move.
- **A:** `web/src/components/organisms/Shopping.tsx:584` ("No decks loaded."), `:821` ("All cards owned. …", ◆) and `:897` ("No decks selected. …"), and `web/src/components/organisms/Compare.tsx:171` ("No decks loaded."). Each is `<div className="gv1-empty">` with a `.gv1-rune` span as its first child. The extra mark comes from `web/src/styles/states.css:67` (`.gv1-empty::before`, `content: '◇'; content: '◇' / '';`).
- **B:** `web/src/routes/ComboLab.tsx:616` (`<Glyph>◇ </Glyph>consulting the curated corpus …`, fleet mode) and `:632` (`<Glyph>◇ </Glyph>consulting the corpus …`, paste mode). Both sit in `.gv1-empty gv1-lab-unscribed`, and `combo-lab.css:255` gives that box its own `::before` ◇.

## What to do
1. **Tree.** Run `cd /Users/dpires/Documents/Personal/code/mtg-precon-upgrader && HOME="$PAPERCLIP_GITHUB_HOST_HOME" git fetch origin && git worktree add -b dec-<N>-one-mark wt-dec<N> origin/main`, then `npm ci` in its `web/`. `<N>` is this issue's number. Keep scratch under `/tmp/dec<N>/`.
2. **A, the markup.** Add one modifier class to each of the 4 containers. I suggest `gv1-empty--own-rune` (the repository already uses `--` modifiers, such as `.gv1-cmp-th--num`); another clear name is fine. Do not add it to any other `.gv1-empty`.
3. **A, the rule.** Add one rule in `states.css`, after `.gv1-empty::before`: `.gv1-empty--own-rune::before { content: none; }`. Do not use `:has()`: your census found that Vite's default build targets (Firefox 78, Safari 14) do not support it. Do not change `styles.css:1824` (the 32 px size of the span).
4. **B.** Delete `<Glyph>◇ </Glyph>` from `ComboLab.tsx:616` and `:632`. Keep the words as they are. The `Glyph` import stays, because the file keeps 7 other `<Glyph>` uses.
5. **Tests.**
   - `web/tests/dec1177-empty-sigils.spec.ts:71` to `:73` (/shopping, "No decks selected") and `:142` to `:144` (Compare, "No decks loaded") assert that "the two glyphs still show". Change each to assert one mark: the `.gv1-rune` span shows its glyph, and the box's `::before` computes `content` `none`.
   - In the e2e spec, add the same assertion for each other A state that the stub can reach: /shopping "No decks loaded" (route `**/data/index.json` to `{ commanders: [] }`, as the Compare case does) and "All cards owned" if you can reach it. Name each state that you could not reach, and why.
   - In `web/src/__tests__/components/Shopping.test.tsx:816` and `Compare.test.tsx` (the DEC-1177 cases), assert that each of the 4 containers has the modifier class. These cases already render all 4 states.
   - **B:** assert that the fleet loading box's text holds no ◇ and that its `::before` still shows ◇ (one mark). The `loading-combos-fleet` state of `web/tests/dec1190-glyph-names.spec.ts:186` already holds the data; reuse its helper. For the paste loading line, use the same hold if it can reach the state; otherwise add a Vitest case that renders it.
   - **A control.** Show that no other empty box changed: a `git grep` that lists the modifier on exactly the 4 containers, and a before-and-after shot of one box that this leg does not touch (the Combo Lab paste box, "Paste a decklist to consult the corpus"), with a changed-pixel count of 0.
6. **Mutants.** Make each change below on a scratch copy and run the suite. Each must fail at least one test; give the failing test's name.
   - M1: drop the modifier from `Shopping.tsx` "No decks selected".
   - M2: drop the modifier from `Compare.tsx`.
   - M3: delete the new `states.css` rule.
   - M4: put `<Glyph>◇ </Glyph>` back on the fleet loading line.
   - M5: put `<Glyph>◇ </Glyph>` back on the paste loading line.
7. **Shots, before and after.** "Before" is `origin/main` (the pull request's base), and "after" is your head. Take each shot of the box only (a locator shot), at 1280 px and at 390 px. Read after `document.fonts.ready`, and take the shot with `animations: 'disabled'`. Cover every state of A and B that you reach, plus the control box. Give each box's height before and after; the box loses one line of the flow, so a smaller height is expected. Save the files as `<state>-<width>-before.png` and `-after.png` under `$PAPERCLIP_GITHUB_HOST_HOME/.paperclip/instances/default/workspaces/8ea33a50-69a7-4a75-bcc1-245bd1e7c73a/dec<N>/shots/`.
8. **Pull request.** Run the web suites in `web/`: `npm run lint`, `npm run typecheck`, `npm test` and `npm run test:e2e`. Commit, push the branch and open one pull request: "fix(web): one mark in each two-mark box on /shopping, Compare and the Combo Lab loading line (DEC-<N>)". Wait for `web-ci` to pass on the head. Do not merge it; I merge after the review.

## Rules
- Set `HOME="$PAPERCLIP_GITHUB_HOST_HOME"` for every `git` and `gh` command. Set `PLAYWRIGHT_BROWSERS_PATH="$PAPERCLIP_GITHUB_HOST_HOME/Library/Caches/ms-playwright"` for every Playwright run.
- Give every e2e run in this tree `GRIMOIRE_E2E_PORT=14917`. No other tree uses this value.
- Send no request to `api.scryfall.com` or `cards.scryfall.io`. The e2e stub answers every case.
- Run Playwright with 3 workers at most; the Mac is shared.
- Change no file outside `web/`. Do not change `styles.css`, the `Glyph` atom or any other `.gv1-empty`.
- Keep `wt-dec<N>` until the merge; I remove it at the merge. Remove any scratch trees that you add, with `git worktree remove` (never `--force`), and name them in your hand-back.

## Handoff
1. Post one comment: the pull request number and head, the suites' results with counts, the `web-ci` run, the 5 mutants with each failing test, the shot paths with the box heights, the control's pixel count, and each state that you could not reach.
2. As the last action of your run, send one PATCH on this issue: `assigneeAgentId` the CEO (`f9427c33-d719-4fd5-a3c5-cd2f65dd01e8`), `status: in_review`, and `executionPolicy.monitor` with `nextCheckAt` 30 minutes ahead, `scheduledBy: "assignee"` and `notes` under 500 characters that name your comment.
3. If the server answers 422 `invalid_issue_disposition`, send the same PATCH again with `nextCheckAt` about ten hours ahead. Never set `done`.
4. **A question in the middle of the leg.** Do the parts that the question does not touch first, then commit and push. Post the question with its evidence and your recommendation. Then send the PATCH of step 2 as the last action of your run. Do not open a child issue assigned to the CEO (the server refuses it with 409 `delegation_cycle`).

planned-by: CEO (run `2eaaabd9`). Source: owner card `345bc3b0` on DEC-1182 (answered 2026-10-17 08:43Z) and census hand-back `12805aca`, section 4. Parent: DEC-1182. The review goes to an engineer who is not the implementer, chosen by queue at your hand-back.
