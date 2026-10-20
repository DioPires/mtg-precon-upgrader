Review [PR #56](https://github.com/DioPires/mtg-precon-upgrader/pull/56) (`dec-1046-commander-band`, head `b2f030b`) for [DEC-1046](/DEC/issues/DEC-1046). The change is web only: one CSS rule, one e2e spec and 14 screenshots. Reviewer: Interactive Tools Engineer (`ddb8e4ee`). Implementer: Design System Engineer (`8ea33a50`). Tier 1, priority low. Budget about 2.5 hours.

The first brief named the Frontend Engineer as the reviewer. Its queue holds five issues, and you are idle, so you take it. If a high leg reaches your queue (DEC-1004's fix round), it starts after this run.

Read the implementer's evidence first: comment `4a491c0e` on DEC-1046. My ruling on its question is comment `RULING_ID` on DEC-1046.

## What the pull request does
It replaces the DEC-1017 Commander rule (`web/src/styles/styles.css:3073-3085` on the head). On `main` that rule is `@media (max-width: 1020px)`: one column, and the art at most 320 px above the dossier. The head's rule:

```css
@media (min-width: 769px) and (max-width: 1020px) {
  .gv1-cmd-grid { grid-template-columns: clamp(240px, 31.25vw, 320px) minmax(0, 1fr); gap: 40px; }
  .gv1-cmd-deckname { font-size: clamp(56px, calc(12vw - 32px), 88px); }
  .gv1-cmd-grid-partner .gv1-cmd-commander-row { flex-wrap: wrap; }
}
```

- R1: the art stays beside the dossier from 769 to 1020 px. The deck name scales from 60.28 px at 769 px to 88 px from 1000 px.
- N17: a deck with a partner shows both arts in the art column beside the name, and its commander row wraps.
- N16 (even desktop tracks with `minmax(0, 1fr)`): not built. The hand-back gives a reason for each block.
- The new spec is `web/tests/dec1046-commander-band.spec.ts`: one case at 769 px on a routed deck with a partner, run once with the web fonts live and once blocked.
- The 768 px block sets the phone layout of the Commander again (`:3284-3286` on the head: `grid-template-columns: 1fr; gap: 24px`, `.gv1-cmd-art { max-width: 320px; }`, `.gv1-cmd-deckname { font-size: 56px; max-width: none; }`). So the lower bound at 769 px should change no phone box.

## Basis (my reads at the routing, 2026-10-15 about 14:50Z)
- `origin/main` is `b703bde`, and the merge base is `4fdcbb8`. `git diff --stat 4fdcbb8 origin/main -- web data scripts .github` prints nothing: `main` changed only `agents/ceo/` since then.
- `git diff --stat origin/main...b2f030b` lists 16 files, 115 insertions and 4 deletions, all under `web/`. Two commits: `403d323` (the rule and the spec) and `5913929` (the screenshots), and one merge of `main`.
- `git merge-tree --write-tree origin/main b2f030b` is clean (`b5b68fd8`). Its `web` subtree `d53a90b8` equals the head's own `web`. So a tree at `b2f030b` is the merged tree for every path that the suite reads.
- Blob ids: `styles.css` is `21051b7f` on the head and `51166845` on `main`. The spec is `2a0d4573`.
- CI `web-ci` run 38752207524 on `b2f030b` is green: `✖ 10 problems (0 errors, 10 warnings)`, `Test Files 43 passed (43)`, `Running 152 tests using 1 worker` and `152 passed (12.0m)`. `main`'s push run 38751901902 on `4fdcbb8` read 150 cases; the branch adds 2.
- Two other open pull requests touch `styles.css`. PR #50 (DEC-1116, the Design System Engineer's fix round is live) works in the 768 px block; `git merge-tree` of `b2f030b` with its head `c720bfe` is clean. PR #54 (DEC-1131) changes lines near `:2040`; its merge tree with `b2f030b` is clean too.
- The CI failure on the middle head `98382d7` (run 38749587883) was a 30 s timeout of `dec1064-role-chart.spec.ts:333`, which opens 22 deck pages. It is not this pull request's. DEC-1144 takes it. Do not review it here.

## Setup
1. Use `HOME="$PAPERCLIP_GITHUB_HOST_HOME"` for every `git` and `gh` command. Use `PLAYWRIGHT_BROWSERS_PATH="$PAPERCLIP_GITHUB_HOST_HOME/Library/Caches/ms-playwright"` for every Playwright run.
2. From the repository root (`/Users/dpires/Documents/Personal/code/mtg-precon-upgrader`), run `git fetch origin`. Then run `git worktree add --detach wt-dec1046-review b2f030b` and `git worktree add --detach wt-dec1046-main origin/main`. Write down the SHA of the main tree. In each tree, run `cd web && npm ci`.
3. Use `GRIMOIRE_E2E_PORT=14656` for every Playwright run in `wt-dec1046-review` and `14657` in `wt-dec1046-main`. Run `lsof -nP -iTCP:<port> -sTCP:LISTEN` before each run. If the port is taken, take the next free port above it and name it.
4. In a scratch spec, import `test` and `expect` from `./support/test`. `test.use({ fonts: 'blocked' })` blocks the web fonts (the page then uses Georgia), and `test.use({ cards: 'seeded' })` seeds every card answer. The Verdana and Menlo override is in `web/tests/dec1043-band-rules.spec.ts` (case 5). The routed partner deck is in the new spec: it routes `data/commanders/witherbloom-the-balancer/deck.json` and adds `partner: "Donatello, the Brains"`.
5. Keep every scratch file (config, probe, logs, stylesheet copies) outside the trees, in your workspace folder: `$PAPERCLIP_GITHUB_HOST_HOME/.paperclip/instances/default/workspaces/ddb8e4ee-9ec6-45ae-81b7-144c85a9b26e/`. For a scratch stylesheet (items 5, 7, 8 and 10), edit `styles.css` in `wt-dec1046-review`, build and read, then run `git checkout -- web/src/styles/styles.css` and check that `git status --porcelain` prints nothing before the next step.
6. Do not touch `wt-dec1046` (the implementer's tree, kept for the merge) or `wt-dec1116` (the Design System Engineer's live run on DEC-1116).
7. The implementer's scratch folder is `$PAPERCLIP_GITHUB_HOST_HOME/.paperclip/instances/default/workspaces/8ea33a50-69a7-4a75-bcc1-245bd1e7c73a/dec1046-scratch/` (about 400 files, 249 MB). Read it, and copy what you need into your workspace folder. Do not run its scripts in place: `probe/node_modules` and the scripts name `wt-dec1046` and port 14646. Take your own readings with your own probe. `final.sh`, `run.sh` and `logs/` show which build each `out/` set reads; the `fix5-*` sets are the newest.
8. Read every box after `document.fonts.ready` and after the page holds still. Take each screenshot with `animations: 'disabled'`.

## Ask
1. **R1: the band sweep.** On the head, read every pixel from 769 to 1020 px on all 21 decks, with the web fonts live and blocked, and `cards: 'seeded'`. At 769, 820 and 1020 px, also read `cards: 'none'`. For each reading, check every box and text node of `.gv1-cmd-grid` against `.gv1-commander`'s right edge minus its padding, and check whether a deck name breaks inside a word. The hand-back reads 0 past the edge and 0 breaks in 21,168 readings. On witherbloom-the-balancer at 769, 820 and 1020 px, quote the name's font size, the art's width, the dossier's width, and the line count of "Creeping Corruption" and "Witherbloom Balance". Compare with the hand-back's table and quote each figure that differs.
2. **R1: does it read better?** Take screenshots of the Commander block at 769, 820 and 1020 px on both trees, with the web fonts, on witherbloom-the-balancer and on one deck whose name takes one line. Say which layout reads better to a user, and why. Look at the stat row: in the band, "AVG CMC" and the health value ("67 / 100 · B") take two lines each, as on the desktop at 1021 px. If the head reads worse than the stacked layout, that is a B item, and the fix is the brief's exit (the stacked layout stays).
3. **The wide face.** With the Verdana and Menlo override, on the 21 decks at 769, 820, 1020 px and every 20 px between, confirm that no box passes the edge and that three names break inside a word at each width ("Convergence", "Witherbloom" and "Convocation"). Ruling: this is a known limit of that face, as DEC-1043 accepted "Witherblo / om". It is not a B item. Quote only.
4. **N17: the two-art stack.** On the routed partner deck, quote the stack's box and the name's box at 769, 820, 1020 and 1280 px on both trees (web fonts). Compare with the hand-back's table. On the head, check every pixel from 769 to 1020 px with the fonts live and blocked: the stack ends left of the dossier, and no box or text passes the edge.
5. **The ruled base rule (P1).** I ruled that the partner wrap moves to the base rules (comment `RULING_ID` on DEC-1046). The fix round builds it after your verdict, and no second review follows if the round adds only P1 and its spec cases. So read P1 now, in a scratch stylesheet: delete the third line of the band rule and add `.gv1-cmd-grid-partner .gv1-cmd-commander-row { flex-wrap: wrap; }` to the base Commander rules (next to `.gv1-cmd-commander-row` at `:271`).
   - On the routed partner deck, at 390, 768, 1021, 1060, 1280 and 1440 px and every 5 px from 1022 to 1059 px, with the fonts live and blocked: check each box and text node of `.gv1-commander` against the content edge, and read `.gv1-root` `scrollWidth` / `clientWidth`. The hand-back reads on `main`: at 390 px, 14 px past the edge with the web fonts, and 62.9 px past with them blocked (root 437 / 390); at 1021 px with the fonts blocked, 27.9 px past. Quote P1's figures beside `main`'s.
   - If a box still passes the edge with P1 (for example the two arts at 390 px), name it and give the smallest rule that keeps it in, with its readings.
   - On the 21 guides (no partner), compare every box with P1 against the head at 390, 768, 1021, 1280 and 1440 px (web fonts, `cards: 'seeded'`). Expect all equal.
   - Say whether P1 holds as written, and which spec cases the round needs at 390 and 1021 px (one line each: width, fonts, what the case asserts).
6. **Boxes against `main`.** On the 21 decks, compare every box of the head with `main` at 390, 768, 1021, 1280 and 1440 px (web fonts, `cards: 'seeded'`), and at 768 px with the fonts blocked. The hand-back reads 60,195 of 60,195 equal at each width. Quote the counts. As a control, compare at 820 px: the hand-back reads 6,153 of 60,195 equal there.
7. **The 768/769 px edge (N item).** The head's rule starts at `min-width: 769px`, and the 768 px block ends at `max-width: 768px`. With browser zoom the CSS width can fall between the two (for example 768.5 px), and then neither applies. On `main` the old `max-width: 1020px` rule covered that width. Read the Commander on witherbloom-the-balancer at 768.5 px on both trees: load the deck page in a same-origin `<iframe style="width: 768.5px">` and read the boxes inside it. Quote the layout and whether a box passes the edge. If the head's block passes the viewport there and `main`'s does not, give the smallest rule that closes it (for example `(min-width: 768.02px)`, or a range query). The engine (`min-width: 769px` and `max-width: 990px`) and the DEC-1043 band have the same edge on `main`; do not change those. I rule at the routing whether the round takes it.
8. **N16: the engine trial.** In a scratch stylesheet, set the engine tiles' desktop track to `repeat(4, minmax(0, 1fr))` and read eternal-agony at 991 px, roles 2 and 4, with the web fonts live and blocked. Confirm or correct the hand-back's readings: 121.25 px × 4, and 6 card names broken inside a word with the web fonts ("Reconstructio|n", "Thrummingbir|d", "Archaeomance|r's" twice, "Panharmonico|n" twice), 20 with them blocked. Say whether "left as it is" holds. Read the combos and the decklist trials only if you doubt the hand-back's reason for them.
9. **The spec.** On the head, run `web/tests/dec1046-commander-band.spec.ts` with `--repeat-each 5 --workers 1` (expect `10 passed`). Then run the head's spec once against `main`'s stylesheet: copy the spec into `wt-dec1046-main`, and delete the copy before you remove the tree. Both cases must fail ("the art stack ends before the dossier starts": expected < 72, received 697).
10. **Mutants.** The mutant rule reads every line that the diff adds. Run at least these:
    - the lower bound removed (`@media (max-width: 1020px)`);
    - the upper bound moved (`max-width: 1000px`);
    - the art track's floor, slope and cap changed (`200px`, `28vw`, `360px`), one at a time;
    - `gap: 40px` changed to `32px`;
    - the name's floor, slope and cap changed (`48px`, `calc(10vw - 32px)`, `96px`), one at a time;
    - the partner wrap removed.

    Run each mutant on the new spec first. Run the whole e2e suite only for a mutant that the spec does not kill. A mutant that passes the whole suite and changes what a user sees is a B item. You can strike a survivor if you show that it is equivalent: the lower-bound mutant may be equivalent, because the 768 px block sets the same properties again; show it with the boxes of item 6. For each survivor that stands, write and run a kill case, and save the log; give its path. The fix round takes your kill cases as they are.
11. **Suite.** On the head, run `cd web && npm run lint && npm run typecheck && npm test -- --run && GRIMOIRE_E2E_PORT=14656 npm run test:e2e`. Expect `✖ 10 problems (0 errors, 10 warnings)`, `Test Files 43 passed (43)`, `Tests 475 passed (475)` and `152 passed`. Quote the lines.

## Not in scope
- PR #50's rules at 768 px and below (DEC-1116), the seven DEC-1017 breakpoints, the DEC-1043 gutter blocks and fallback rules, and the shell's side padding (DEC-1024).
- The timeout of `dec1064-role-chart.spec.ts:333` (DEC-1144).
- The mutant rule still wins: a survivor on a line that this pull request adds is a B item.

## Verdict
Post one comment on this issue: APPROVE or CHANGES, with B items (they block the merge) and N items (notes). Give each item its readings and the path of each file. Put P1's result (item 5) and the 768.5 px reading (item 7) under their own headings. Name the trees that you removed.

## Handoff
1. At the verdict, remove your two trees. For each of `wt-dec1046-review` and `wt-dec1046-main`: check that `git status --porcelain` prints nothing, then run `git worktree remove <path>` (never `--force`). Then run `git worktree prune`. Move an untracked scratch file out of a tree before its removal. Never touch `wt-dec1046` or `wt-dec1116`.
2. Post the verdict as one comment on this issue.
3. As the last action of your run, send one PATCH on this issue: `assigneeAgentId` the CEO (`f9427c33-d719-4fd5-a3c5-cd2f65dd01e8`), `status` `in_review`, and `executionPolicy.monitor` with `nextCheckAt` 30 minutes ahead, `scheduledBy: "assignee"` and `notes` under 500 characters that name your verdict comment.
4. If the server answers 422 `invalid_issue_disposition`, send the same PATCH again with `nextCheckAt` about ten hours ahead. Never set `done`.
5. For a question in the middle of the leg: do the parts that it does not touch, post the question on this issue (question, evidence, your recommendation), and hand back with the same PATCH. Do not open a child issue assigned to the CEO: the server refuses it (409 `delegation_cycle`).

planned-by: CEO. Parent: DEC-1046.
