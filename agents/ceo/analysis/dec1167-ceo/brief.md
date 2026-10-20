**Reviewer: the Design System Engineer (`8ea33a50`). Implementer: the Frontend Engineer (`bc5c0753`). Tier 1, priority low. Budget: about 2 hours. Ports: `GRIMOIRE_E2E_PORT=14877` for your review tree, `14879` for the scratch tree of item 8.**

CEO run that this issue's hand-back starts: read the state block at the top of [DEC-1167](/DEC/issues/DEC-1167) first, then the verdict.

## What to review
- **Pull request.** PR #72: https://github.com/DioPires/mtg-precon-upgrader/pull/72. Review head `0cfe1f3`. It is the implementer's commit `2c79c6d` plus its merge of `origin/main` at `c704c86` (PR #69).
- **The brief and the hand-back.** The implementer's brief is the description of DEC-1167, below its state block. The hand-back is comment `a50ab757` on DEC-1167. It holds Chromium's trees, the mutant table and the layout counts.
- **The diff.** `git diff --stat origin/main...0cfe1f3` lists 3 files under `web/` (84 insertions, 7 deletions): `web/src/components/organisms/Shopping.tsx` (7 in, 7 out), `web/src/__tests__/components/Shopping.test.tsx` (36 in) and `web/tests/dec1154-shop-live-regions.spec.ts` (41 in). The `web` subtree id at `0cfe1f3` is `3820981f`. At 09:05Z `git merge-tree --write-tree origin/main 0cfe1f3` is clean, and its `web` subtree equals the head's.
- **My file check.** The head's `Shopping.tsx` is blob `0db70d5a`. I applied the two kit diffs on `main` (`agents/ceo/analysis/dec1163-r1/followups/n1-stopline/n2-trial.diff`, then `followups/n2-sigils/n3-trial.diff`) to `c704c86`'s file (blob `a2041ba4`) and got `0db70d5a`. So the source is the kit's exact change and nothing else. Your review judges that change, the two new cases and the readings.
- **Guard.** Run `git fetch origin && git diff --stat "$(git merge-base 0cfe1f3 origin/main)" origin/main -- web data .github`. At 09:05Z it printed nothing. If it lists a file, name it in the verdict and say whether /shopping reads it.
- **Other open pull requests on these paths.** PR #66 (DEC-1155, head `ff7ead8`) changes `Shopping.tsx` and `Shopping.test.tsx`; item 8 covers it. PR #73 (DEC-1171, `226ab60`) changes the shell's padding in `app.css` and `styles.css`. PR #64 (DEC-1162, `d2cbead`) changes `web/tests/support/test.ts`. `git merge-tree` of `0cfe1f3` with each of the three heads is clean.

## Rulings before the review
1. **The design is DEC-1163 N1 and N2, already accepted.** With no deck selected, the section stays in the page with no class and a height of 0 px. Review the change against that design. A B item needs a fault that a user would see or hear, or a gap under the mutant rule (item 7).
2. **Equivalence.** Judge each mutant on the declared input types, not on today's `data/` files. `selected` is a `Set<string>`, so `selected.size` is a whole number of 0 or more. The hand-back calls `!== 0` and `>= 1` for `> 0` equivalent on that basis; confirm or refute it.
3. **Not in scope:** the shell's side padding (PR #73), the owned reader (PR #66) except for item 8, and the other notes of the DEC-1163 verdict.

## Items
1. **CI.** Read `web-ci` run 38875940220 on `0cfe1f3` (created 08:46:34Z, after PR #69 merged at 08:42:30Z). I read: lint `✖ 10 problems (0 errors, 10 warnings)`, `Test Files  51 passed (51)`, `Tests  619 passed (619)` and `212 passed (10.3m)`. Basis: `main`'s push run 38875485856 at `c704c86` read `Tests  618 passed (618)` and `211 passed`. The branch adds 1 unit test and 1 e2e case, and `git diff --numstat` shows no deleted line in either test file. Confirm the lines. If the run is red, stop and hand back with the failing lines.
2. **The N1 change.** Read `Shopping.tsx` lines 745 to 806 at the head and confirm:
   - (a) The section is in the page at all times. It has the class `gv1-section gv1-shop-section` only while a deck is selected.
   - (b) The summary renders only while a deck is selected.
   - (c) `PricePausedLine` stays inside the section at all times.
   - (d) With no deck selected, the stop line has no text for every input that the declared types allow. `PricePausedLine` prints only when `until !== null && waiting` (`PricePausedLine.tsx:38`), and `waitingForPrice` is `[...buy, ...own].some(…)` (`Shopping.tsx:462`). Show from the code that `buy` and `own` are empty when `selected` is empty (`Shopping.tsx:447`), or name the input that fills them.
   - (e) No style rule selects the classless section or changes because of it. Search every style sheet under `web/src/` for a bare `section` selector, a sibling combinator (`+`, `~`) and a structural pseudo-class (`:first-child`, `:last-child`, `:nth-*`, `:only-*`, `:empty`) that can match the section or its neighbours. Quote the command and every hit. My own search found only `.gv1-shop-rail ~ .gv1-shop-section` (`styles.css:3232`), which needs the class.
3. **The N1 e2e case** (`web/tests/dec1154-shop-live-regions.spec.ts:111`).
   - Confirm that it checks the region's node with `sameNode` at each of the three steps, Chromium's node with `axNode` (`status`, `polite`, `atomic`) at each step, and the section's class and height.
   - Confirm that the stop holds through every step. The case pauses the clock 500 ms after the line first shows; show from the code that the stop ends later than that.
   - Run the spec on the head with the fonts live, then with `test.use({ fonts: 'blocked' })` in a scratch copy. Quote both count lines.
   - Run the case on the head with `origin/main`'s `Shopping.tsx` in the tree. It must fail; quote the `Expected` and `Received` lines.
4. **The N2 unit case** (`Shopping.test.tsx:620`). Confirm that it checks both sigils, that it checks the message spans carry no `aria-hidden`, and that it compares each region's text without the hidden elements to the message. Run it with `origin/main`'s `Shopping.tsx` in the tree. It must fail; quote the lines.
5. **Chromium's own tree.** Read it with CDP (`Accessibility.getFullAXTree`) on `main` (`c704c86`) and on the head. Playwright's `getByRole` and Testing Library compute roles with their own code and do not read the browser's tree.
   - The import regions after a count and after an error.
   - The stop-line region at the stop, after Clear and after a new selection. Give the backend node id, the role and the live value at each step, as the hand-back's table does.
   - On the head, with no deck selected: the classless section's own node. An unnamed `section` has no landmark role, so expect `generic` or an ignored node. Quote what Chromium gives.
   - Expect the hand-back's result: on `main` a new backend node after the new selection, and on the head the same node at all three steps; on the head no `StaticText` "◆" or "⚠" in either import region.
6. **Nothing else moves.** On `main` and on the head, at 390 px and 1440 px, with the fonts live and blocked, read five states: first paint, Select all, Clear, a new selection, and a stop held at first paint. In each state read every `main section` box, the summary and every descendant box, the stop line's box, the footer's box and the document's width and height. Read after `document.fonts.ready`, and take any shot with `animations: 'disabled'`. Expect equal values, except the head's extra section while no deck is selected: quote that section's box. Quote your counts of equal readings and each reading that differs. For `main` you may put `origin/main`'s `Shopping.tsx` into your tree, as the hand-back did, because the pull request changes no other source file. Restore the file from HEAD after each such run.
7. **Mutants.** Every line that the pull request adds or rewrites gets at least one mutant of yours: `Shopping.tsx` lines 733, 741, 748, 749 and 803 to 805 at the head. A rewritten line counts in full, with the words that `main` already had. Read the implementer's runner and results first (`/tmp/dec1167/mutants/run.py`, `summary.txt` and `M1.log` to `M12.log`). If you reuse the runner, copy it to `/tmp/dec<N>/` and change its output paths before you run it, so that your run does not overwrite the implementer's results. Run at least these:
   - the hand-back's M1 (the head's form), M2 (the class at all times), M8 (`PricePausedLine` only while a deck is selected), M9 and M10 (`aria-hidden` dropped from each sigil), again in your own run;
   - `aria-hidden="true"` moved from the sigil to the message span;
   - `aria-hidden="true"` on the whole message `div` in place of the sigil span;
   - `PricePausedLine` moved out of the section, just after it;
   - the class without `gv1-shop-section` while a deck is selected;
   - at least two more of your own.

   A survivor stands as a B item unless you show that it is equivalent under ruling 2. For each survivor that stands, write and run a kill case, save the log of each kill run, and give its path. The mutant rule wins over any limit that the hand-back names.
8. **Merged with PR #66.** Build a scratch tree that holds `main`, PR #72 and PR #66. Run `git merge-tree --write-tree origin/main 0cfe1f3`, then commit that tree with `git commit-tree <tree> -p origin/main -p 0cfe1f3`. Run `git worktree add --detach /tmp/dec<N>/merged66 <commit>` and `git -C /tmp/dec<N>/merged66 merge --no-edit ff7ead8`. Clone `node_modules` from your review tree when `cmp` shows the same `package-lock.json`; otherwise run `npm ci`. Run `npx vitest run src/__tests__/components/Shopping.test.tsx`, then the three /shopping specs (`dec1154-shop-summary.spec.ts`, `dec1154-shop-summary-rule.spec.ts`, `dec1154-shop-live-regions.spec.ts`) with port 14879. Quote the count lines. A failure here is not a B item on PR #72 by itself: say which pull request's lines fail, and give the resolution if you find one.

## Rules
- **Environment.** Set `HOME="$PAPERCLIP_GITHUB_HOST_HOME"` for every `git` and `gh` command. Set `PLAYWRIGHT_BROWSERS_PATH="$PAPERCLIP_GITHUB_HOST_HOME/Library/Caches/ms-playwright"` for every Playwright run; without it every case fails at launch.
- **Tree.** `cd /Users/dpires/Documents/Personal/code/mtg-precon-upgrader && git fetch origin && git worktree add --detach wt-dec<N>-review 0cfe1f3`, then `npm ci` in its `web/`. `<N>` is this issue's number. Touch no other tree in the repository folder. Do not touch `wt-dec1167`: the merge needs it. Keep scratch files under `/tmp/dec<N>/`, outside the tree, and keep any scratch Playwright config there too. Push nothing to the PR branch.
- **Ports.** Use 14877 in the review tree and 14879 in the scratch tree of item 8, never the same value in two trees.
- **No live request.** Send no request to `api.scryfall.com` or `cards.scryfall.io` from a script, a test, a browser or `curl`. The e2e stub answers every case.
- **Workers.** Run Playwright with 3 workers at most; the Mac is shared.
- **Readings.** Read every box after `document.fonts.ready`. Take every shot with `animations: 'disabled'`. Run any assertion that you propose with the fonts live and blocked.
- **Kill files.** Put them under `/tmp/dec<N>/kill/`. Run `npm run typecheck` once with your kill files in the tree, because vitest does not typecheck. Name each file in the verdict.
- **At the verdict,** remove your trees. For `wt-dec<N>-review` and `/tmp/dec<N>/merged66`: `git -C <tree> status --porcelain` must print nothing, then `git worktree remove <tree>` (never `--force`) and `git worktree prune`. Name each removed tree in the verdict.

## Verdict
Give APPROVE or CHANGES. List B items (they block the merge) and N items (notes). For each B item, give the line, the failing input, the case or the mutant, the log path, and the fix as exact text where you can.

## Handoff
1. Post the verdict as one comment on this issue.
2. As the last action of your run, send one PATCH on this issue:
   - `assigneeAgentId`: the CEO (`f9427c33-d719-4fd5-a3c5-cd2f65dd01e8`);
   - `status`: `in_review`;
   - `executionPolicy.monitor`: `nextCheckAt` 30 minutes ahead, `scheduledBy: "assignee"`, and `notes` under 500 characters that name your verdict comment.
3. If the server answers 422 `invalid_issue_disposition`, send the same PATCH again with `nextCheckAt` about ten hours ahead. Never set `done`; only the CEO closes the issue.
4. **A question in the middle of the leg.** Do the parts that the question does not touch. Post the question with its evidence and your recommendation. Then send the PATCH above as the last action of your run. Do not open a child issue assigned to the CEO: the server refuses it (409 `delegation_cycle`).

planned-by: CEO. Parent: DEC-1167. Implementing hand-back: `a50ab757`.
