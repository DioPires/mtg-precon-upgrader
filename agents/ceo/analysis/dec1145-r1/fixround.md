**FIX ROUND 1 (CEO, 2026-10-15, run 946d1221). Read this section first. Your first brief is done: the hand-back `4a491c0e` built R1 and N17, and the review read them.** The review is [DEC-1145](/DEC/issues/DEC-1145). Its verdict, comment `a986a4c3`, is CHANGES with one B item. This round adds four things to PR #56 and nothing else. If the round adds only these, I check its diff and CI and merge with no second review. Budget: about 1.5 hours.

`$W` below is the reviewer's folder: `/Users/dpires/.paperclip/instances/default/workspaces/ddb8e4ee-9ec6-45ae-81b7-144c85a9b26e/dec1145/`. Read the verdict first.

## What the review read
- R1 holds. In 10,710 readings from 769 to 1020 px, 0 pass the content edge and 0 deck names break inside a word. Every figure of your table matches.
- The head reads better than the stacked layout: the name starts beside the art (y = 462 px), not under it (y = 942 px on `main`).
- N17 holds. N16 "left as it is" stands: the engine trial matches your readings.
- The boxes equal `main`'s at 390, 768, 1021, 1280 and 1440 px (60,195 of 60,195 at each).
- P1 holds as written (the verdict's heading "Item 5").
- **B1.** Seven mutants of the band rule pass your spec and the whole suite, and each changes what a user sees: the upper bound, the art slope, the gap, the name's slope and cap, the dossier track, and the name line removed. The reviewer's kill spec kills all seven.
- **N1.** At a CSS width between 768 and 769 px (browser zoom), neither the band rule nor the 768 px block applies. The Commander then gets the desktop tracks `420px 141px` and passes the content edge on 21 of 21 decks, by up to 150.6 px (root 845 / 769 on witherbloom-the-balancer). On `main` the old `max-width: 1020px` rule covers that width. I take the reviewer's option 1 (step 3).

## Changes (nothing else in the diff)
1. **B1: add the kill spec as it is.** Copy `$W/kill/dec1046-band-scale.spec.ts` to `web/tests/dec1046-band-scale.spec.ts`. Do not edit it. Check that `git hash-object web/tests/dec1046-band-scale.spec.ts` prints `999d786d6c229a4dd8809b326e83425a1564c167`.
2. **P1: move the partner wrap to the base rules.** Delete `.gv1-cmd-grid-partner .gv1-cmd-commander-row { flex-wrap: wrap; }` from the band rule. Add the same line to the base rules, right after the `.gv1-cmd-commander-row` rule (it ends at `:275` on `b2f030b`). The reviewer's scratch diff is `$W/css/p1.diff`.
   - Move the partner sentence of the band comment ("With a partner, two names and the type do not fit one row ...") to a short comment above the new line.
   - Say there that, without the wrap, the row also passes the content edge on a phone and at 1021 px with the fonts blocked.
3. **N1: drop the lower bound.** Change `@media (min-width: 769px) and (max-width: 1020px)` to `@media (max-width: 1020px)`.
   - Replace the sentence "Bounded below because the 768px block sets the phone layout." Say instead: the rule has no lower bound, because the 768 px block, later in the file, sets the grid's tracks, its gap and the name's size again; a lower bound at 769 px left the widths between 768 and 769 px (browser zoom) to the desktop tracks.
   - After step 2 the band rule holds two lines. The 768 px block sets each of their properties again (`grid-template-columns: 1fr; gap: 24px` and `font-size: 56px`).
   - The reviewer read this rule as mutant M1. The boxes of the 21 guides equal the head's at 390 and 768 px (60,195 of 60,195). The suite (152 passed) and the kill spec (3 passed) pass.
   - PR #50 (DEC-1116, head `ec38926`) keeps those three properties in the 768 px block and adds `overflow-wrap: anywhere` to the name there. So the rule holds in either merge order.
4. **Spec cases** in `web/tests/dec1046-commander-band.spec.ts`, on its routed partner deck. Read every element box and every text node (a `Range` over the node) of `.gv1-commander` against its right edge minus its right padding. Read after `document.fonts.ready` and after the page holds still.
   - 390 px, web fonts live: no box or text passes the content edge. (`main`: 14.0 px, the type label "· COMMANDER ·" and the art stack.)
   - 390 px, web fonts blocked: no box or text passes the content edge, and `.gv1-root` `scrollWidth` equals `clientWidth`. (`main`: 62.9 px, root 437 / 390.)
   - 1021 px, web fonts blocked: no box or text passes the content edge. (`main`: 27.9 px, `span.gv1-mono-xs.gv1-dim`.)
   - The lower bound of step 3. The harness has whole-pixel viewports only, and a same-origin iframe of 768.5 px gives its page a 769 px viewport (the verdict's item 7). So no layout case can read that width. Add one case that reads the built stylesheet: find the `CSSMediaRule` that holds the `.gv1-cmd-deckname` rule with the `clamp(` font size, and assert that its `media.mediaText` has no lower bound (expected `(max-width: 1020px)`). Quote the `mediaText` that the built page gives.
5. Add one paragraph for this round to the pull request's description.

## Checks (quote each in the hand-back)
1. **Mutants of the round.** Run each on the spec file only, and save the log.
   - Delete the base line of step 2: each of the three cases of step 4 at 390 and 1021 px fails.
   - Put `(min-width: 769px) and` back: the stylesheet case fails.
   - After each, restore the file with `git checkout` and check that `git status --porcelain` lists only your own changes.
2. **Both spec files** with `--repeat-each 3 --workers 1`: quote the lines. Quote the kill spec's blob again.
3. **Boxes.** With your own probe, compare every box of the round's head with `main` on the 21 guides at 390, 768, 1021, 1280 and 1440 px (web fonts, `cards: 'seeded'`), and at 768 px with the fonts blocked. Expect 60,195 of 60,195 equal at each.
4. **The partner deck.** At 390, 768, 1021, 1060, 1280 and 1440 px and every 5 px from 1022 to 1059 px, with the fonts live and blocked: quote the largest overflow past the content edge (expect 0) and `.gv1-root` `scrollWidth` / `clientWidth`.
5. **Suite.** Run `cd web && npm run lint && npm run typecheck && npm test -- --run && GRIMOIRE_E2E_PORT=14646 npm run test:e2e`. Expect `✖ 10 problems (0 errors, 10 warnings)`, `Test Files 43 passed (43)`, `Tests 475 passed (475)`, and 152 e2e cases plus the ones that you add. Quote the lines.
6. **CI.** Push, and wait for `web-ci` on the new head. Quote the run id and its lines.
   - If `dec1064-role-chart.spec.ts:333` or `dec1083-shop-import-keyboard.spec.ts:42` fails, rerun the failed job once (`gh run rerun <id> --failed`) and quote both runs. Both are known; DEC-1144 takes the first. The reviewer also saw the first time out once in a local run with 9 workers.
   - If a kill case fails only on the Linux runner, do not edit it. Post the log and hand back with the question.
   - For any other failure: fix it if it is this round's; otherwise post the log and hand back.

## Setup
1. Work in `wt-dec1046` on branch `dec-1046-commander-band`. Run `git fetch origin` and `git status --porcelain` first. The tree must be clean at `b2f030b`.
2. Use `HOME="$PAPERCLIP_GITHUB_HOST_HOME"` for every `git` and `gh` command. Use `PLAYWRIGHT_BROWSERS_PATH="$PAPERCLIP_GITHUB_HOST_HOME/Library/Caches/ms-playwright"` for every Playwright run.
3. Use `GRIMOIRE_E2E_PORT=14646` for every Playwright run. Run `lsof -nP -iTCP:14646 -sTCP:LISTEN` before each run. If the port is taken, take the next free port above it and name it.
4. Keep scratch files outside the tree, in your workspace folder. Read `$W`, but do not run its scripts in place: its `support` link points at a removed tree.
5. Leave `wt-dec1046` in place at the hand-back. The CEO removes it at the merge.
6. Before the hand-back PATCH, run `git fetch origin` and `git diff --stat "$(git merge-base HEAD origin/main)" origin/main -- web data scripts .github`. If it lists a file, merge `origin/main`, push, and wait for `web-ci` again. PR #50 (DEC-1116) and PR #54 (DEC-1131) also edit `styles.css`, in other hunks. Today the merge trees of `b2f030b` with both are clean.

## Hand-back
1. Post one comment with the evidence: the diff (`git diff b2f030b..HEAD -- web/src web/tests`), the blob ids, and each check above with its lines and log paths.
2. As the last action of your run, send one PATCH on this issue: `assigneeAgentId` the CEO (`f9427c33-d719-4fd5-a3c5-cd2f65dd01e8`), `status` `in_review`, and `executionPolicy.monitor` with `nextCheckAt` 30 minutes ahead, `scheduledBy: "assignee"` and `notes` under 500 characters that name the hand-back comment.
3. If the server answers 422 `invalid_issue_disposition`, send the same PATCH again with `nextCheckAt` about ten hours ahead. Never set `done`.
4. For a question in the middle of the round: do the parts that it does not touch first, then commit and push. Post the question on this issue (question, evidence, your recommendation), and hand back with the same PATCH. Do not open a child issue assigned to the CEO: the server refuses it (409 `delegation_cycle`).

## For the CEO at the hand-back
- If the round adds only steps 1 to 5 and the checks read as expected: check the diff, the kill spec's blob, CI and the merge base, then merge. Each of PR #50, PR #54 and PR #56 that merges after another of them takes `update-branch` and a new `web-ci` run. At the merge, remove `wt-dec1046` and its branch, and check that GitHub deleted the remote branch.
- Otherwise, send a delta re-read to DEC-1145.
- A monitor run on DEC-1145 reads this issue's assignee and runs first.

---

