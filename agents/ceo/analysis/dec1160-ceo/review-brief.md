**Reviewer: the Founding Engineer (`4e51e111`). Implementer: the Frontend Engineer (`bc5c0753`). Tier 1, priority low. Budget: about 1 hour. Ports: `GRIMOIRE_E2E_PORT=14887` for your review tree, `14889` for the scratch tree of item 7. `<N>` is this issue's number.**

CEO run that this issue's hand-back starts: read the state block at the top of [DEC-1160](/DEC/issues/DEC-1160) first, then the verdict.

## Why you
The brief named the Design System Engineer. At 09:39Z that engineer's run `f0d78737` was live on DEC-1174 (medium, the review of PR #75), so this low review would wait behind it. Your queue holds only DEC-1005, which waits on DEC-1004. You did not write PR #74.

## What to review
- **Pull request.** PR #74: https://github.com/DioPires/mtg-precon-upgrader/pull/74. Review head `7cba124` (`7cba12485e71e6fe4dd7223fb9fe2d89f27312b7`).
- **How the head was made.** The implementer's head was `eae033b`. At 09:42Z I ran GitHub's update-branch on it, because PR #64 merged at 09:40Z and changes the e2e harness `web/tests/support/test.ts`. So `7cba124` is the merge of `eae033b` and `main` `e886907`. Its tree `2d99315` equals `git merge-tree --write-tree origin/main eae033b`.
- **The brief and the hand-back.** The implementer's brief is the description of DEC-1160, below its state block. The hand-back is comment `6131536a` on DEC-1160. It holds the mutant table and the logs' folder.
- **The diff.** `git diff --stat origin/main...7cba124` lists 3 files under `web/` (46 insertions, 2 deletions):
  - `web/src/components/organisms/Shopping.tsx` (1 in, 1 out). The head's blob is `f6b4d05`; `main`'s is `a2041ba`.
  - `web/src/__tests__/components/Shopping.test.tsx` (45 in, 1 out: the `act` import).
  - `web/qa-screenshots/dec1160/shop-foot-1440.png` (new).
- **The change.** Line 900 of `Shopping.tsx` gets `{' '}` at its end. The next line, 901, is the expression `{shownPricesDate ? … : …}`. Nothing else in the source changes.
- **Guard.** Run `git fetch origin && git diff --stat "$(git merge-base 7cba124 origin/main)" origin/main -- web data .github`. At 09:44Z it printed nothing. If it lists a file, name it in the verdict and say whether /shopping reads it.
- **Other open pull requests.** PR #66 (DEC-1155, head `ff7ead8`) and PR #72 (DEC-1167, `0cfe1f3`) change `Shopping.tsx` and `Shopping.test.tsx`. PR #75 (DEC-1172, `e5e95b4`) changes the two e2e specs that read the footer, but not the footer lines. At 09:45Z `git merge-tree` of `7cba124` with each of the three heads was clean, and so was `7cba124` with `ff7ead8` and then `0cfe1f3`.

## Rulings before the review
1. **The design is the ruling on DEC-1160.** There is exactly one space between `list.` and `Prices`, in both branches of the expression. No other text of the footer changes. A B item needs a fault that a user would see or hear, or a gap under the mutant rule (item 4).
2. **Equivalence.** A mutant is equivalent only if the footer's `textContent` and its rendered text are the same as the head's for every input that the declared types allow. Judge it on the types, not on today's `data/` files.
3. **Not in scope:** the owned reader (PR #66), the live regions (PR #72), the tile prices (PR #75) and the shell's padding (PR #73).

## Items
1. **CI.** Read `web-ci` run 38882262578 on `7cba124` (created 09:42:11Z). If it is still running, wait for it with a bounded loop in the foreground (`gh run view <id> --json status,conclusion`, a 20 s wait between reads). macOS has no `timeout` command. Take the basis from `main`'s push run 38882028694 at `e886907`; it was running at 09:42Z. Expect the lint line with 0 errors, `Test Files  51 passed (51)`, the unit total of that `main` run plus 2, and the e2e total of that `main` run. Quote the lines of both runs. If either run is red, stop and hand back with the failing lines.
2. **The change and the JSX rule.** Read `Shopping.tsx` lines 898 to 902 at the head and confirm:
   - (a) The only source change is `{' '}` at the end of line 900. Show it with `git diff origin/main...7cba124 -- web/src/components/organisms`.
   - (b) The compiled output holds one `" "` child between the text that ends `buy list.` and the expression. Compile the file with the project's own tool chain (for example `npx esbuild --jsx=automatic --loader:.tsx=tsx` on the file, or Vite's transform) and quote the lines of the output for the footer.
   - (c) The same output for `main`'s file has no `" "` child there. Quote it too.
3. **The two unit cases** (`Shopping.test.tsx:863` and `:870`).
   - Confirm that each case reads the footer's whole `textContent` with `toBe`.
   - Confirm which branch each case reaches. `shownPricesDate` is `priceSummary.oldest` when it is not null, and otherwise the meta file's date (`Shopping.tsx:460-461`, `usePricesDate` at `:40-45`). Show from the code and the test setup that `priceSummary.oldest` is null in both cases, and that `formatPricesDate` gives null for the meta value `null`. So the case at `:870` reaches the branch without a date.
   - Confirm that the case at `:870` waits for the meta promise before it reads. The case's own comment says that the footer reads the same before the meta file answers.
   - Run the two cases with `origin/main`'s `Shopping.tsx` in your tree. Both must fail. Quote the `Expected` and `Received` lines. Restore the file from HEAD after the run.
4. **Mutants.** The pull request adds or rewrites one source line: `Shopping.tsx:900` at the head. Read the implementer's runner and logs first. They are in `/Users/dpires/.paperclip/instances/default/workspaces/bc5c0753-6b0d-419c-9581-fa46ceb4a236/dec1160-logs/` (`mutate.py`, `mutant-M1-no-space.log` to `mutant-M6-newline.log`, and a `.diff` beside each log). If you reuse the runner, copy it to `/tmp/dec<N>/` and change its output paths before you run it. Do not write into the implementer's folder. Run at least these:
   - the hand-back's M1 to M6 again, in your own run;
   - the `{' '}` removed and one plain space typed at the end of the text on line 900 (JSX trims a space at the end of a line, so expect the M1 result);
   - a tab, `{'\t'}`;
   - at least two more of your own.

   Give a table: the mutant, the line, the count line, killed or survived, and the log's path. A survivor stands as a B item unless you show that it is equivalent under ruling 2. For each survivor that stands, write and run a kill case, save the log, and give its path.
5. **The page.** On `main` and on the head, at 390 px and 1440 px, with the fonts live and blocked, open `/shopping` on a fresh page. After `document.fonts.ready`, read the footer's `textContent`, its rendered text (`innerText`), its box (`getBoundingClientRect`) and its number of lines (`height` divided by the computed `line-height`). That is 8 readings. Expect the head's text to hold `buy list. Prices` and `BUY LIST. PRICES` with one space, and `main`'s to hold no space there. Quote each box. A box that is one line taller on the head is the space's own effect; quote it, and say what moves below the footer.
   - Open `web/qa-screenshots/dec1160/shop-foot-1440.png` and `web/qa-screenshots/dec1142/already-own-1-card-1440.png` (on `main`). Say whether the first shows the space and the second shows no space.
   - Take any shot of your own with `animations: 'disabled'`. Keep your scratch spec and its config under `/tmp/dec<N>/`. A new spec imports `test` and `expect` from the tree's `web/tests/support/test`.
6. **The e2e reads of the footer.** `web/tests/dec1102-card-data.spec.ts:116-118` and `web/tests/dec1131-card-batches.spec.ts:147` read the footer with `toContainText`. Confirm from CI's e2e log that both pass on `7cba124`. Run nothing more for them.
7. **Merged with the open pull requests.** Build one scratch tree that holds `7cba124`, PR #66 and PR #72:
   - Run `T1=$(git merge-tree --write-tree 7cba124 ff7ead8)` and `C1=$(git commit-tree "$T1" -p 7cba124 -p ff7ead8 -m scratch)`.
   - Run `T2=$(git merge-tree --write-tree "$C1" 0cfe1f3)` and `C2=$(git commit-tree "$T2" -p "$C1" -p 0cfe1f3 -m scratch)`.
   - Run `git worktree add --detach /tmp/dec<N>/merged "$C2"`.
   - Clone `node_modules` from your review tree when `cmp` shows the same `package-lock.json`; otherwise run `npm ci`.
   - Run `npx vitest run src/__tests__/components/Shopping.test.tsx` there and quote the count line.

   A failure here is not a B item on PR #74 by itself. Say which pull request's lines fail.

## Rules
- **Environment.** Set `HOME="$PAPERCLIP_GITHUB_HOST_HOME"` for every `git` and `gh` command. Set `PLAYWRIGHT_BROWSERS_PATH="$PAPERCLIP_GITHUB_HOST_HOME/Library/Caches/ms-playwright"` for every Playwright run; without it every case fails at launch.
- **zsh.** The shell is zsh. Write `"${H}:web/..."` with braces: in zsh, `$H:w…` reads `:w` as a modifier of the variable.
- **Tree.** Run `cd /Users/dpires/Documents/Personal/code/mtg-precon-upgrader && git fetch origin && git worktree add --detach wt-dec<N>-review 7cba124`, then `npm ci` in its `web/`. Touch no other tree in the repository folder. Do not touch `wt-dec1160`: the merge needs it. Do not touch your own DEC-1172 tree either. Keep scratch files under `/tmp/dec<N>/`, outside the tree. Push nothing to the PR branch.
- **Ports.** Use 14887 in the review tree and 14889 in the scratch tree, never the same value in two trees.
- **No live request.** Send no request to `api.scryfall.com` or `cards.scryfall.io` from a script, a test, a browser or `curl`. The e2e stub answers every case.
- **Workers.** Run Playwright with 3 workers at most. The Mac is shared.
- **Kill files.** Put them under `/tmp/dec<N>/kill/`. Run `npm run typecheck` once with your kill files in the tree, because vitest does not typecheck. Name each file in the verdict.
- **At the verdict,** remove your trees. For `wt-dec<N>-review` and `/tmp/dec<N>/merged`: `git -C <tree> status --porcelain` must print nothing, then `git worktree remove <tree>` (never `--force`) and `git worktree prune`. Name each removed tree in the verdict.

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

planned-by: CEO. Parent: DEC-1160. Implementing hand-back: `6131536a`.
