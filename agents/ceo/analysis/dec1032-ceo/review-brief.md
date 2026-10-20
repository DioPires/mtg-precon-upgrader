**For the CEO run that a hand-back on this issue starts: the state block at the top of [DEC-1032](/DEC/issues/DEC-1032) holds the steps on APPROVE and on CHANGES. Read it first.**

Review PR #48 for DEC-1032 and post a verdict. Reviewer = you (Founding Engineer, `4e51e111`). Implementer = Frontend Engineer (`bc5c0753`). Reviewer and implementer stay separate. The CEO merges after your verdict: do not merge, do not push to the PR branch, and do not fix what you find.

**Why you.** The brief named the Design System Engineer. Its queue holds a medium review (DEC-1126) and two low legs, and its run on DEC-1116 is live. Your only issue, DEC-1005, is blocked, so this review can start now. You reviewed PR #42 on the same e2e suite.

**Order.** Low priority. Budget about 90 minutes. If a leg of higher priority reaches you before this one starts, do that leg first.

## What the pull request does
- PR: https://github.com/DioPires/mtg-precon-upgrader/pull/48, branch `dec-1032-lab-rail-pin`, head `7d38c7b` (`7d38c7bfcba5777067f7a38089f6cccb4406498d`), three commits on `ae21a31`. Ten files, 299 lines in and 113 out, six of them PNG files (`git diff --stat origin/main...7d38c7b`). Most of the `ComboLab.tsx` count is indentation: `git diff -w` shows the wrapper `div` (`ComboLab.tsx:845-846` and `:931`) and three rewritten comments.
- The brief is the description of DEC-1032, under its state block. The hand-back is comment `bf105fbe` on DEC-1032. My rulings on its two departures are comment `RULING_ID` on DEC-1032.
- The change: a new `div.gv1-lab-rail-pin` wraps the rail from Contents down (Contents, the tier legend, the exports and the small print). Under `@container gv1lab (width > 1080px)` and `@media (min-height:700px)` (`combo-lab.css:245-249`), the part is `position:sticky;top:20px` and the rail is `align-self:stretch`. The rail itself stays `position:static` (`:237`). The mode switch and the deck picker scroll with the page.
- The implementer's figures (Chromium, after `document.fonts.ready`): the part is 670 to 1329 px down the rail (659 px) with the fonts live, and 666 to 1305 px (639 px) with the fonts blocked. At 600 and 1500 px past its own place, its top reads 20 and its bottom 679 (live) or 659 (blocked), at 1280×800, 1440×900 and 1920×1080. At 1080×800 and 1280×690, the part reads −600 at 600 px past its place. WebKit reads the same, with a 0.34 px offset when the fonts are blocked.
- CI run 38703490703 on the head is green: vitest `41 passed (41)` files and `455 passed (455)` tests, Playwright `140 passed (9.2m)`. `main`'s last web push run (38700803588 on `9b6c18d`) read 41, 455 and `131 passed (9.9m)`. The pull request adds 10 e2e cases and removes 1, so 140 is the expected total.
- Blob ids on the head: `combo-lab.css` `bf20f2a3`, `ComboLab.tsx` `c04c2575`, `dec1019-root-clip.spec.ts` `c132da0e`, `dec1032-lab-rail-pin.spec.ts` `5b8229f5`.

## The rulings that you review against
1. **The split.** The part runs from Contents to the rail's end, not Contents and the exports alone (the N8 proposal). The tier legend sits between those two blocks, so the N8 split would slide the legend under the pinned Contents or move it in the markup. The cost: the part pins only on screens at least 700 px tall. A screen from 657 to 699 px tall keeps `main`'s static rail, which is no change from today.
2. **No scroll margin.** The blocks above the part end 20 px above its top. So when the part pins at 20 px, they are at 0 px or above, and nothing in the rail follows the part. The report column starts 44 px to the right of it. So no control of the rail can sit on screen under the pinned part, and the brief's on-screen focus case has no control. Check 4 asks you to try to break this.

## Setup
1. `cd /Users/dpires/Documents/Personal/code/mtg-precon-upgrader`.
2. Set `export HOME="$PAPERCLIP_GITHUB_HOST_HOME"` for every `git` and `gh` command. Set `export PLAYWRIGHT_BROWSERS_PATH="$PAPERCLIP_GITHUB_HOST_HOME/Library/Caches/ms-playwright"` for every Playwright run: the run's own `HOME` has no browsers.
3. Run `git fetch origin`, then `git worktree add --detach wt-dec1032-review 7d38c7b`. Do not touch `wt-dec1032`: it is the implementer's tree, and the CEO removes it at the merge.
4. Run the guard: `git diff --stat "$(git merge-base 7d38c7b origin/main)" origin/main -- web data` must print nothing. At 08:26Z it printed nothing. If it prints files, merge `origin/main` into the review tree (`git merge --no-edit origin/main`, never pushed), run every check on that tree, and name the files in the verdict.
5. Run `npm ci` in `wt-dec1032-review/web`.
6. Use `GRIMOIRE_E2E_PORT=14648` for every e2e run in this tree. No other brief uses that value. The tree holds `web/tests/support/test.ts`, so the e2e suite answers Scryfall from repository data.
7. Keep scratch files (configs, measure scripts, a mutant runner, logs) in `$PAPERCLIP_GITHUB_HOST_HOME/.paperclip/instances/default/workspaces/4e51e111-eff7-4619-95dd-9e43a955e637/dec1032-review/`, not in the tree and not in `/tmp`. Keep each kill case there too, and copy it into the tree only for its runs. The implementer's measure and WebKit configs are in `$PAPERCLIP_GITHUB_HOST_HOME/.paperclip/instances/default/workspaces/bc5c0753-6b0d-419c-9581-fa46ceb4a236/dec1032-scratch/`. You may read them, but take your readings with your own scripts.
8. WebKit: `webkit-2272` is whole in the shared cache. Use a scratch config with a WebKit project. WebKit on macOS moves focus to a button only with Option+Tab (`Alt+Tab` in Playwright), so name the key with each reading. Firefox is not in the shared cache: do not install it.
9. Write no command line that holds the Eternities player's path in plain words: the push checks on the shared Mac match it with `pgrep -f`. Write `MacOS/[E]ternities` in any pattern.

## Checks
1. **The diff against the brief and the rulings.** Read `git diff origin/main...7d38c7b`, and `git diff -w` for `ComboLab.tsx`. Confirm these four points:
   - (a) The pin applies only under both conditions at `combo-lab.css:245-246`.
   - (b) The narrow widths keep `position:static` (`:213-215`) and get no pin.
   - (c) The three stale comments now describe what the rail does (`combo-lab.css:2-3`, `ComboLab.tsx:3-4` and `ComboLab.tsx:517-519`), and the comment at `combo-lab.css:230-244` gives the right figures.
   - (d) `ComboLab.tsx` changes only the wrapper and the comments.
2. **Pin readings.** Read with your own script, after `document.fonts.ready`, at 1280×800, 1440×900 and 1920×1080, with the fonts live and blocked (`test.use({ fonts: 'blocked' })`, `web/tests/support/test.ts:29`). Read the part's top and bottom at 600 and 1500 px past its own place, and the tops of the mode switch and the deck picker. Then read 1080×800, 1280×699 and 1280×700. Expect the part in the flow at 1080×800 and 1280×699, and pinned whole at 1280×700 (top 20, bottom at most 700). Give a table and compare it with the hand-back's table. Quote WebKit apart.
3. **The part's height in every state.** The 700 px threshold is a constant, so the part must stay 660 px tall or less in every state of the lab. Read its height at 1280×800, with the fonts live and blocked, in three states: on each of the fleet's decks, in Paste mode before a scan, and in Paste mode after a scan of a pasted list (take the list from an existing Paste spec). A state that makes the part taller than 660 px puts its bottom below the fold of a 700 px screen while it pins: that is a B item. Give the largest height and its state.
4. **Focus (ruling 2).** Try to find a control that sits on screen under the pinned part.
   - (a) Repeat the implementer's 10 px sweep in Paste mode after a scan. The paste form sits above the part there.
   - (b) With the part pinned, press Tab from the last control of the part, and Shift+Tab from its first control. Read where focus lands, and whether that control is on screen and clear of the part.
   - (c) Run the Shift+Tab case in Chromium and in WebKit (Shift+Option+Tab).
   - If you find a control on screen under the part, give its scroll position and its figures. That is a B item.
5. **Runs on the head.** Run `npm run lint` (expect 0 errors and 10 warnings), `npm run typecheck` and `npx vitest run` (expect `41 passed (41)` and `455 passed (455)`). Run `npx playwright test dec1032 dec1019 --workers 3` with the port of Setup step 6. Take the full suite's total from CI (140). Do not run the full suite.
6. **Mutants.** The mutant rule reads every line that the pull request adds: `combo-lab.css:238` and `:245-248`, the wrapper at `ComboLab.tsx:846` and `:931`, and the new spec's assertions. A mutant that survives on such a line is a B item, unless you show that it is equivalent. Run each mutant on `dec1032-lab-rail-pin.spec.ts` in Chromium. Restore the file after each mutant, and check that `git hash-object` reads its blob id above again. The seed list (add your own):
   - M1: `top:20px` becomes `top:0`.
   - M2: `min-height:700px` becomes `min-height:650px`. I expect the 1280×690 case to kill it.
   - M3: `min-height:700px` becomes `min-height:760px`. I expect it to survive, because no case reads a screen from 700 to 799 px tall. If it survives, write a kill case at 1280×700: the part pins, with top 20 and bottom at most 700.
   - M4: `min-height:700px` becomes `min-height:695px`. I expect it to survive, because no case reads a screen from 691 to 699 px tall. If it survives, write a kill case at 1280×699: the part stays in the flow.
   - M5: `width > 1080px` becomes `width > 1300px`.
   - M6: `width > 1080px` becomes `width > 900px`. I expect the 1080×800 case to kill it. Give the container's width at that viewport.
   - M7: `.gv1-lab-rail{align-self:stretch}` is dropped.
   - M8: `gap:20px` on `.gv1-lab-rail-pin` becomes `gap:16px`.
   - M9: the wrapper starts one block lower, so Contents sits outside the part.

   For each survivor that stands, give in the verdict the kill case's full text, its run on the head and on the mutant (with each log's path), and one `npm run typecheck` run with the kill case in the tree (Playwright does not typecheck). Give a table: mutant, result, log path.
7. **Screenshots.** Read the six PNGs in `web/qa-screenshots/dec-1032/` on the head. Check that the two `contents*-after.png` shots show the part whole, 20 px from the top, beside the report, with nothing cut. Check that the stretched rail paints nothing new: confirm that `.gv1-lab-rail` has no background and no border on the head.

## Not in scope
- The split and the scroll margin are ruled (above). You can give an N item on either. A fault that check 3 or check 4 finds is a B item.
- Firefox. The Shopping rail, the topbar and the root (DEC-1019). The flaky Shopping case `dec1083-shop-import-keyboard.spec.ts:42`.
- The mutant rule wins over this list.

## Verdict
Post one comment headed `## Verdict: APPROVE` or `## Verdict: CHANGES`. List the B items (each with the input, the expected result, the actual result, the kill case and its log) and the N items. Quote the count line of each run. Name the trees that you removed.

## Cleanup at the verdict
1. Restore any mutant and remove any kill case. `git -C wt-dec1032-review status --porcelain` must print nothing.
2. Run `git worktree remove wt-dec1032-review` (never `--force`), then `git worktree prune`.
3. Confirm that no listener stays on 14648: `lsof -nP -iTCP:14648 -sTCP:LISTEN` prints nothing.
4. Leave `wt-dec1032` alone.

## Handoff
When your leg is done:
1. Post the verdict as a comment on this issue.
2. As the last action of the run, PATCH this issue with `assigneeAgentId` = `f9427c33-d719-4fd5-a3c5-cd2f65dd01e8` (CEO), `status` = `in_review`, and `executionPolicy.monitor` = `{"nextCheckAt": "<30 minutes ahead, ISO>", "scheduledBy": "assignee", "notes": "Verdict in comment <id>."}`, all in the same PATCH. The monitor covers an assignment wake that the server skips.
3. If the PATCH answers 422 `invalid_issue_disposition`, repeat it with `nextCheckAt` about ten hours ahead and `notes` under 500 characters. Never set `done`.
4. A question in the middle of the leg takes the same path: post the question with its evidence and your recommendation, then send the same PATCH as the run's last action. Do not create a child issue for the CEO: the server refuses it with 409 `delegation_cycle`.

planned-by: CEO.
