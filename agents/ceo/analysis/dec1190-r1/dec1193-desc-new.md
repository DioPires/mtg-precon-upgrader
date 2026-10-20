**RE-READ 1 (CEO run `3b474ad1`, 2026-10-16 20:40Z). Read this section first. The review below is done (verdict `9fea43e9`, CHANGES); do not run it again.**

**Outcome I need.** APPROVE or CHANGES on PR #79 after fix round 1. The round changes two test files only. Read the four B fixes and N1 and N2, run the four surviving mutants again, and run the suites on the new head. Budget: about 1 hour. Priority low. Port: `GRIMOIRE_E2E_PORT=14973`.

**What changed since your verdict.**
- The Design System Engineer's hand-back is comment `deccb27c` on [DEC-1190](/DEC/issues/DEC-1190). Its round head is `69eb1f4`. `git diff --stat 017060e 69eb1f4` lists `web/src/__tests__/dec1190/glyph-source.test.ts` and `web/tests/dec1190-glyph-names.spec.ts` only. `web-ci` run 38958037742 passed on `69eb1f4`.
- PR #78 (DEC-1184) and PR #80 (DEC-1188) merged into `main` during the round. At 20:34Z I ran `gh pr update-branch 79`. The new head is `b342ea1`, a merge of `main` `8fb404c` into `69eb1f4`. Its tree `e82dc7b5` equals `git merge-tree --write-tree origin/main 69eb1f4`. No file of PR #79 is in the `main` delta. `web-ci` run 38963214555 runs on `b342ea1`.

**Checklist (head `b342ea1`).**
1. **Basis.** Run `HOME="$PAPERCLIP_GITHUB_HOST_HOME" git fetch origin`. Check that `origin/dec-1190-glyph-names` is `b342ea1`. Run `git diff --stat 8fb404c origin/main -- web data .github` and quote what it prints. If it prints files, review `b342ea1` anyway and name the files in the verdict; I update the branch again at the merge.
2. **The merge brings only `main`.** Check that `git rev-parse b342ea1^{tree}` equals `git merge-tree --write-tree 8fb404c 69eb1f4`. Check that `git diff --stat 017060e 69eb1f4 -- web` lists only the two test files above.
3. **The B fixes.** For each item, give the file and line on `b342ea1`.
   - B1 (R4): the fixture of `glyph-source.test.ts` holds `<p>a − b</p>`, and the expected list holds its line. The spec has a plain case: `glyphsIn('a − b')` is `['−']`, and `glyphsIn('−1')` is `[]`.
   - B3 (R14): the spec asserts that the Type row's `.gv1-scry-delta-detail` reads `/^\S+ to \S+$/`.
   - B2 and B4 (R13 and R17): a second Scrying swap cuts a Swamp for Underworld Breach (state `scrying-delta-land`). The spec asserts that the Lands detail reads `/^\d+ to \d+$/` and that the Game Changers change reads "+1". Check that the swap reads only `deck.json` data, not `candidates.json`, which PR #78 changed.
   - N1: one comment at the role filter says why the rule skips `RootWebArea` and `InlineTextBox`.
   - N2: the second Compare reading goes through `state(page, 'compare-turned', …)`.
   - N3: no change, as ruled.
4. **Mutants.** Run R4 (once in the Vitest file and once in the spec), R13, R14 and R17 again with your own `mut/all.py` and `mut/run.sh`. Change only the tree, the log folder (`/tmp/dec1193/reread1/mut/`) and the port. Each must now fail at least one case, at the line that the round added for it. Restore the file after each run. Before the verdict, check that `git status --porcelain` in your tree prints nothing. A mutant that survives is a B item.
5. **Suites.** On `b342ea1`, run lint, typecheck, Vitest and the full Playwright suite with 3 workers at most. Quote each count line. Expected, from the two parents: lint `✖ 10 problems (0 errors, 10 warnings)`; Vitest `Test Files 57 passed (57)` and `Tests 719 passed (719)` (PR #79 adds 2 files and 13 tests to `main`'s 55 and 706); Playwright `266 passed`. Quote the result of `web-ci` run 38963214555 too. A count that differs is a B item unless you name its cause.
6. **No new shots.** No product file changes in the round, and the `main` delta touches no file of PR #79. The pixel counts and the control of your verdict stand.

**Setup.**
1. Make the tree: `cd /Users/dpires/Documents/Personal/code/mtg-precon-upgrader && HOME="$PAPERCLIP_GITHUB_HOST_HOME" git fetch origin && HOME="$PAPERCLIP_GITHUB_HOST_HOME" git worktree add --detach wt-dec1193 b342ea1`. Then run `npm ci` in its `web/`.
2. Set `HOME="$PAPERCLIP_GITHUB_HOST_HOME"` for every `git` and `gh` command.
3. Set `PLAYWRIGHT_BROWSERS_PATH="$PAPERCLIP_GITHUB_HOST_HOME/Library/Caches/ms-playwright"` and `GRIMOIRE_E2E_PORT=14973` for every Playwright run. Use 3 workers at most; the Mac is shared.
4. Send no request to `api.scryfall.com` or `cards.scryfall.io`.
5. Do not touch `wt-dec1190`; the implementer keeps it until the merge. Do not push to the branch, and do not merge.

**Handoff.**
1. Post one comment on this issue. Start it with `APPROVE` or `CHANGES`. Give the basis, the file and line of each B fix and of N1 and N2, each mutant's result with its log path, the count lines of each suite, and the `web-ci` result. Keep the evidence in `$PAPERCLIP_GITHUB_HOST_HOME/.paperclip/instances/default/workspaces/bc5c0753-6b0d-419c-9581-fa46ceb4a236/dec1193/reread1/`.
2. Remove `wt-dec1193` with `git worktree remove` (never `--force`) after `git status --porcelain` prints nothing. Then run `git worktree prune`. Name the tree in the comment.
3. As the last action of your run, send one PATCH on this issue: `assigneeAgentId` the CEO (`f9427c33-d719-4fd5-a3c5-cd2f65dd01e8`), `status: in_review`, and `executionPolicy.monitor` with `nextCheckAt` 30 minutes ahead, `scheduledBy: "assignee"` and `notes` under 500 characters that name your comment.
4. If the server answers 422 `invalid_issue_disposition`, send the same PATCH again with `nextCheckAt` about ten hours ahead. Never set `done`.
5. **A question in the middle of the re-read.** Finish the parts that the question does not touch. Post the question with its evidence and your recommendation. Then send the PATCH of step 3 as the last action of your run. Do not open a child issue assigned to the CEO (409 `delegation_cycle`).

**Next.** On APPROVE, I merge PR #79 by the STATE block of DEC-1190. On CHANGES, a fix round 2 goes back to the Design System Engineer.

---

**Started (CEO run `9e4de761`, 2026-10-16 16:22Z), from the DEC-1190 hand-back `d79ab19a`.** `<N>` is this issue's number.

**Reviewer: the Frontend Engineer (`bc5c0753`). Tier 1, priority low. Budget: about 3 hours. Ports: `GRIMOIRE_E2E_PORT=14973` for the head tree and `14974` for the `main` tree. Web only. Do not push to the branch, and do not merge.**

## What you review
- [PR #79](https://github.com/DioPires/mtg-precon-upgrader/pull/79), branch `dec-1190-glyph-names`, head `017060e`. Base `main` `8f15c33` (PR #73 merged in). 30 files, +990 −117. The head's `web` subtree is `86121b4e`.
- The brief is the description of [DEC-1190](/DEC/issues/DEC-1190): classes C1 to C5, the C3 table of words, the tests and the pixel rule. The hand-back is comment `d79ab19a` on DEC-1190.
- The implementer (the Design System Engineer) kept its evidence in `$PAPERCLIP_GITHUB_HOST_HOME/.paperclip/instances/default/workspaces/8ea33a50-69a7-4a75-bcc1-245bd1e7c73a/dec1190/`. Its `README.md` names each folder: the census, the mutant runner and logs, the suite logs, the pixel kit (`px/`) and the control.
- CI on the head: `web-ci` run 38926608379, green (`lint-typecheck-unit` and `e2e`).

## My rulings on the hand-back (read these before the checklist)
1. **The minus sign (note 1).** The rule stands as the pull request writes it. A "−" (U+2212) directly before a digit is the sign of that number, and both checks pass it, as they pass "-1". A "−" in any other place is a glyph. Do not add "−" to R0: R0 would then pass a decorative "−" in any place. Do not add words: a screen reader says the sign of a number already. The filter also passes the Combo Lab distance chip "−1", whose words come from the C3 table, so the spec must assert those words (checklist item 3).
2. **The pixel rule.** The brief asked for 0 px and an explanation of each state that is not 0. The hand-back gives 1,795 px in 15 states and a sub-pixel cause, with a control in 3 states. I accept that cause if your control (item 5) shows it in all 15 states. I accept the 1 px growth of the "Copied" button in `deck-copied` and `shopping-copied`: that state lasts 1.6 s. A difference that the control does not explain is a B item.
3. **`lib/comboVerify.ts:517` ("mv ≤ N" in a reanimation trace).** No change in this pull request. It renders in no state that the spec reads. It is a named limit, not a B item.
4. **Notes 2 to 10 of the hand-back** stand as the implementer's decisions. Check each one against the code. A note that the code contradicts is a B item.

## Checklist
1. **Basis.** After `HOME="$PAPERCLIP_GITHUB_HOST_HOME" git fetch origin`, run `git diff --stat 8f15c33 origin/main -- web data .github`. Quote what it prints. If it prints nothing, review the head itself. If it prints files (PR #80 can merge during your leg; it changes `web/README.md`, `web/src/data/scryfallLimiter.ts` and three test files), review the merged head instead: `git merge-tree --write-tree origin/main origin/dec-1190-glyph-names`, then `git commit-tree` of that tree with both parents, and a detached tree on that commit. Name the basis in the verdict.
2. **The brief's items.** For each item, give the file and line of the change on the basis, or name the item as missing.
   - C1: the 4 spans carry `aria-hidden="true"`.
   - C2: `web/src/components/atoms/Glyph.tsx` exists. Each of the 26 sites of the census holds its glyph in `Glyph`. A space next to a glyph is inside `Glyph`, or note 2's rule covers it.
   - C3: each row of the C3 table gives the exact words of the table. Each string from a `.ts` module renders through the one helper (`GlyphText`), and `git diff --stat 8f15c33 017060e -- web/src/lib` prints nothing (the data does not change).
   - C4: `.gv1-lab-steps summary::before` in `combo-lab.css` reads `content: '▸'; content: '▸' / '';`, and the `[open]` rotation stays. `git grep -n 'gv1-loading-inline' -- web` prints nothing on the basis.
   - C5: `ManaCost` puts `role="img"` and one label on `.gv1-mv`; the pips inside it have no `aria-label` of their own; the land path and the `—` path keep `main`'s code. `GV1ManaPips` names the colours in the given order, and an empty string or ◇ alone reads "Color identity: colorless". The Combo Lab colour-identity line hides its emoji or letters and gives the words in `gv1-sr-only`.
   - `git diff --stat 8f15c33 017060e -- web/src/styles/styles.css web/src/styles/app.css` prints nothing.
3. **The spec's assertions.** For each row of the C3 table and each C5 item, name the line of `web/tests/dec1190-glyph-names.spec.ts` that asserts the words on the name that Chromium computes. A row with no such line is a B item. Check these points:
   - The spec reads CDP `Accessibility.getFullAXTree` after `document.fonts.ready`, and it skips only the nodes that Chromium ignores.
   - The distance chip: line 322 compares the spoken text with the chip's `title`. Check that the reading would fail if the words were gone (mutant R7 below).
   - The mana-cost state reads a cost in words, for example "Mana cost: 2 generic, black, black".
   - No name that held a hidden glyph starts or ends with a space, in every state.
4. **Suites.** On the basis, run lint, typecheck, Vitest and the full Playwright suite, with 3 workers at most. Quote each count line. The hand-back read: lint `✖ 10 problems (0 errors, 10 warnings)`, Vitest `Test Files 56 passed (56)` and `Tests 708 passed (708)`, Playwright `264 passed`. A difference in a count is a B item unless you name its cause (a merge from item 1).
5. **Pixels.** Run the implementer's shot spec (`px/shots.template.ts` and `px/config.template.ts`) on a `main` build and on the basis build: 23 states, each after `document.fonts.ready`, with `animations: 'disabled'`, at the viewport of each read. Compare your counts with `px/counts.txt`. Then extend the control to all 15 states that are not 0. On the `main` build, split the same text nodes with a plain `<span>` and no ARIA attribute, as `px/control/` did for three states, and count against the basis build. Keep the control as one diff file in your evidence. Expected: 0 px in each of the 15 states. For a state that is not 0, look at the crop and name the cause; ruling 2 says which causes pass. Also open the crops in `px/diff-2/` and check that no glyph, word or colour changes, and that nothing moves more than 1 px.
6. **Mutants.** A mutant that survives on a line that the pull request adds is a B item. A line that the pull request rewrote counts in full, also the words that `main` already had. A mutant that also passes on `main` is still a B item when it survives on an added line.
   - Rerun M1, M3 and M6 with the implementer's runner (`mut/run.sh`). Copy it to `/tmp/dec<N>/` first, and change `W` to your tree and `log` to `/tmp/dec<N>/mut/`. Without that change, your run writes over the implementer's logs and edits its tree.
   - Write and run your own mutants, at least these. Each must fail at least one case:
     - R1: `GlyphWords` keeps a plain space at the edge of its words (drop the `.replace`).
     - R2: `colorWords` swaps blue and black.
     - R3: the `ManaCost` label drops the generic count.
     - R4: the source check's filter `−(?=\d)` becomes `−` in every place. Run it once in the Vitest file and once in the spec.
     - R5: the Codex chip loses `aria-label="deck number"`.
     - R6: one Spellbook link loses " (opens in a new tab)".
     - R7: the distance chip loses its `GlyphWords` (the "−1" stays).
     - R8: the colour-identity line loses its `gv1-sr-only` words.
     - R9: a module that renders imports `Hero.tsx` (the guard case must fail).
     - R10: `.gv1-lab-toc-folio` loses `aria-hidden`.
     - R11: a new `::after` rule with `content: '◆'` and no `/ ''` line in a stylesheet other than `combo-lab.css` (the widened case of `dec1177-empty-sigils.spec.ts` must fail).
     - R12: `COUPLING_WORDS` in `ComboLab.tsx` loses its "↔" entry.
   - Run each mutant on the specs that it touches, not on the full suite. Save one log for each under `/tmp/dec<N>/mut/`, and restore the file after each run. Before the verdict, check that `git status --porcelain` in your tree prints nothing.
7. **The source check.** Show that `web/src/__tests__/dec1190/glyph-source.test.ts` fails on a glyph in JSX text (M7 covers this), and on a glyph in a string literal that is one branch of a ternary JSX child. Show that it passes an R0 sign and a glyph under `aria-hidden` or `Glyph`. Use a scratch `.tsx` file under `web/src/`, outside `__tests__`, and delete it after the runs.

## Not in this review
- Proposals A and B of the DEC-1182 hand-back. They wait for the owner's answer on DEC-1182.
- A pass with VoiceOver. R0 stands on the DEC-1182 reading.
- A change to the R0 list.
- The mutant rule wins over this list: a mutant that survives on an added line is a B item even when a limit here names the gap.

## Setup
1. Make the head tree: `cd /Users/dpires/Documents/Personal/code/mtg-precon-upgrader && HOME="$PAPERCLIP_GITHUB_HOST_HOME" git fetch origin && HOME="$PAPERCLIP_GITHUB_HOST_HOME" git worktree add --detach wt-dec<N> origin/dec-1190-glyph-names`. If item 1 gives a merged head, make this tree on that commit instead.
2. Make the `main` tree: `HOME="$PAPERCLIP_GITHUB_HOST_HOME" git worktree add --detach wt-dec<N>-main 8f15c33`, or `origin/main` if item 1 printed files.
3. Run `npm ci` in the `web/` of each tree.
4. Set `HOME="$PAPERCLIP_GITHUB_HOST_HOME"` for every `git` and `gh` command.
5. Set `PLAYWRIGHT_BROWSERS_PATH="$PAPERCLIP_GITHUB_HOST_HOME/Library/Caches/ms-playwright"` for every Playwright run. Set `GRIMOIRE_E2E_PORT=14973` in `wt-dec<N>` and `14974` in `wt-dec<N>-main`. Use 3 workers at most; the Mac is shared.
6. Send no request to `api.scryfall.com` or `cards.scryfall.io`. The e2e stub answers every case.
7. Keep scratch under `/tmp/dec<N>/`, and keep any scratch Playwright config outside the trees. Do not write into `/tmp/dec1190/` or into `wt-dec1190`: they belong to the implementer.

## Verdict
Post one comment on this issue. Start it with APPROVE or CHANGES. Give:
1. The basis, with the guard's output from item 1.
2. Items 2 and 3, each with its file and line.
3. The count line of each suite.
4. The pixel counts for each of the 23 states (your rerun), and for each of the 15 states under your control, with the path of the control's diff file.
5. Each mutant, its result and its log path.
6. B items (they block the merge), each with the failing case or the reading that shows it.
7. N items (they do not block), each with a proposed action.

Keep your evidence in `$PAPERCLIP_GITHUB_HOST_HOME/.paperclip/instances/default/workspaces/bc5c0753-6b0d-419c-9581-fa46ceb4a236/dec<N>/` and give that path.

## Handoff
1. Post the verdict comment.
2. Remove each of your scratch trees: `git status --porcelain` must print nothing, then `git worktree remove <path>` (never `--force`), then `git worktree prune`. Name each tree in the verdict. Do not touch `wt-dec1190`.
3. As the last action of your run, send one PATCH on this issue: `assigneeAgentId` the CEO (`f9427c33-d719-4fd5-a3c5-cd2f65dd01e8`), `status: in_review`, and `executionPolicy.monitor` with `nextCheckAt` 30 minutes ahead, `scheduledBy: "assignee"` and `notes` under 500 characters that name your verdict comment.
4. If the server answers 422 `invalid_issue_disposition`, send the same PATCH again with `nextCheckAt` about ten hours ahead. Never set `done`.
5. **A question in the middle of the leg.** Do the parts that the question does not touch first. Post the question with its evidence, the count by cause, the readings and your recommendation. Then send the PATCH of step 3 as the last action of your run. Do not open a child issue assigned to the CEO (409 `delegation_cycle`).

planned-by: CEO (run `9e4de761`). Source: DEC-1190 hand-back `d79ab19a`. Parent: DEC-1190.

