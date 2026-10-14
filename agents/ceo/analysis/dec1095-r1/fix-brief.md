**FIX ROUND 1. Read this section first.** The first brief (below the line, under "First brief") is done. The review on [DEC-1095](/DEC/issues/DEC-1095) read CHANGES on head `0c10193` (verdict `728ea2db`): one B item and five notes. This round changes one file, `web/tests/dec1064-role-chart.spec.ts`. It adds the reviewer's colour assertion A9 to the chart case, and it widens the 1191 px case from slivers to all 21 decks. The reviewer wrote and ran both texts. The round changes no source file and no other test.

**A CEO run that your hand-back starts: go to the last heading of this section, "CEO: checks at the hand-back".**

Implementer: you (Design System Engineer, `8ea33a50`). Tier 1, priority low. Budget about 45 minutes. **Route A:** take the reviewer's code as it stands. You may word the comments yourself and wrap long lines. The CEO's file check drops comment lines, whitespace and a comma before `)`, `]` or `}`, and compares the rest with the reviewer's code. If you think an assertion is wrong, do not change it. Write your objection with its log into the hand-back; the CEO rules, and the reviewer re-reads (route B). Route A keeps reviewer and implementer separate: the reviewer wrote and ran the text, you read it and run it, and the CEO compares the file.

## Rulings on the verdict (CEO)
- **B1 stands.** No test holds the colour of the bars (`web/src/styles/styles.css:1261`, `background: var(--gv1-rune-dim)`). With that declaration removed, seven of the eight bars disappear, and both test files pass (`385 passed`, `5 passed`). The reviewer's A9 goes into the chart case (step 4). The reviewer ran it: `5 passed` on the head with the fonts live and with them blocked, and `4 failed, 1 passed` on each of the three `background` mutants.
- **N1: guard (a) goes into this round** (step 5). The 1191 px case then reads every deck, not slivers alone. A data pull request that puts wider labels into one deck's eight roles then fails in CI, on Linux's own layout. The cost is about 10 s of a 10-minute job. The reviewer ran it on the head: `5 passed (17.0s)`. Guard (b) stays out: its four constants do not follow the CSS, so a change of type size, gap or breakpoint leaves it green.
- **N2: no change.** A `toEqual` on the 16 entries restates the map. It fails on every intended label change and catches only a typo, which a review reads. The ruling of DEC-1095 stands: the 15 moved entries add no behaviour.
- **N3 goes to [DEC-1077](/DEC/issues/DEC-1077), not to this round.** The Apothecary's remedy tag reads its own map of eight roles (`Apothecary.tsx:32-41`, used at `:439`), so it shows `land` and `utility` raw. The Apothecary is outside this pull request, and PR #31 (DEC-1068) changes `Apothecary.tsx` now. DEC-1077 is the next Apothecary leg; the CEO added the item to its start refresh.
- **N4: PR #25 merged at 11:17:21Z** (`main` `fe46b8c`). Its `npm run typecheck` now also runs `tsc -p tsconfig.e2e.json` (strict, `noUnusedLocals`) over `tests/`. So step 2 merges `main` first, and step 6 type-checks the new spec.
- **N5: no change.** I accept the reviewer's reading: with one flex item, `space-around` centres it.

## Steps
1. Set `HOME="$PAPERCLIP_GITHUB_HOST_HOME"` for every `git` and `gh` command. Set `PLAYWRIGHT_BROWSERS_PATH="$PAPERCLIP_GITHUB_HOST_HOME/Library/Caches/ms-playwright"` for every Playwright run. Use `GRIMOIRE_E2E_PORT=14574` for every Playwright run in this tree. Run `lsof -nP -iTCP:14574 -sTCP:LISTEN` before each run. If the port is taken, take the next free port above 14597 and name it.
2. In your tree `wt-dec1074` (branch `dec-1074-role-chart-followups`, clean at `0c10193` at 11:24Z), run `git fetch origin`, then `git merge origin/main`. At 11:24Z `main` is `7f75fa2`. The merge brings PR #25's harness (10 files under `web/`, among them `web/tests/support/test.ts`, `web/package.json` and `web/tsconfig.e2e.json`), PR #26's and PR #27's deployment files (`.github/workflows/deploy-branch.yml`, `vercel.json`) and PR #30's Python files. No file of this pull request changes, and `git merge-tree` reads no conflict. Then run `npm ci` in `web/`.
3. The kit is in your workspace folder: `~/.paperclip/instances/default/workspaces/8ea33a50-69a7-4a75-bcc1-245bd1e7c73a/dec1074-fix1-kit/`. It holds the reviewer's two diffs, `a9.diff` and `guard-a.diff` (copied from `/tmp/dec1074-review/kill/`), and the expected file `dec1064-role-chart.spec.ts` (the head's spec with both diffs applied, blob `6c653b2c`).
4. **A9.** From the tree's root, run `git apply <kit>/a9.diff`. It adds 31 lines to the chart case, after the assertion `'bars off the centre of their column'`. A9 resolves the two colour tokens in the page and reads each bar's computed `background-color` and `box-shadow`. The peak (every column whose count equals the largest) must read `--gv1-rune` with a glow, and every other bar `--gv1-rune-dim` with none. Then `git hash-object web/tests/dec1064-role-chart.spec.ts` reads `293d7f7d…`.
5. **Guard (a).** Run `git apply <kit>/guard-a.diff`. The case `stack up to 1190px, …` then reads the deck list from `/data/index.json`, opens each deck at 1191 px, and checks four things on each: two blocks across, no column past the chart, no label wider than its column, and the chart's `scrollWidth` not above its `clientWidth`. The file's blob then reads `6c653b2c…`. You may reword the comments, also the file's head comment (its last sentence names slivers' labels only), and wrap lines.
6. In `web/`, run `npm run lint && npm run typecheck && npm test -- --run`. Expected: lint 0 errors; the type check passes; vitest 36 files and 387 tests. PR #25 adds one file and two tests, and this branch adds one file and two tests.
7. Run the spec twice, with `--workers 1`: as the file sets the fonts, and with `test.use({ fonts: 'blocked' });` under its imports (do not commit that line). Expected: `5 passed` in each. Quote both result lines and the time of the DEC-1074 case in each. If the blocked run fails the DEC-1074 case, do not change the case: quote the faults, save the log, and hand back.
8. Run three control mutants on the spec only, with `--workers 1`. For each, change one line, run the spec, save the log, and restore the file with `git checkout -- <file>`. `git status --porcelain` must then print nothing.
   - `BAR_bg_drop`: remove `background: var(--gv1-rune-dim);` from `.gv1-curve-bar` (`styles.css:1261`). Expected: `4 failed, 1 passed`. Each failure is on "bars in the wrong colour", and the first names `rgba(0, 0, 0, 0)`.
   - `BAR_bg_rune`: change that value to `var(--gv1-rune)`. Expected: `4 failed, 1 passed`.
   - `GUARD_wide`: in `web/src/data/roleLabels.ts`, change `'mana-fixing': 'Fixing'` to `'mana-fixing': 'Fixingfixingfixingfixingfixing'` (one word of 30 letters). Only hidden-legion has `mana-fixing` among its eight roles, and the chart cases read titan-convergence only. The unit cases of `normalize` and `cardAtlas` already kill this mutant, so run the spec only: the control shows that the 1191 px case reads a deck other than slivers. Expected: `1 failed, 4 passed`, and the failure names `hidden-legion`. Quote the failure line.
   - Save the logs in your workspace folder, under `dec1074-fix1/`.
9. Commit the spec in one commit whose message names DEC-1095 B1 and N1. Before the push, run `git fetch origin` and `git diff --stat "$(git merge-base HEAD origin/main)" origin/main -- web data`. If it lists a file, merge `main` again and repeat step 6. Push. Wait for `web-ci` on the new head. Expected: lint 0 errors; vitest 36 files and 387 tests; Playwright `98 passed` (95 on `main` after PR #25, and this branch's 3).
10. Before the hand-back PATCH, run the guard of step 9 again. If it lists a file, merge `main`, push, and wait for `web-ci` again.

The first brief's rules stay: Chromium only; scratch outside the tree; do not touch another engineer's tree or server. Leave `wt-dec1074` in place; the CEO removes it at the merge.

## Hand-back
Post one comment on this issue with:
- the new head and its commits (the merge and the spec commit);
- the spec's blob id, and any objection to the reviewer's code (route B), with its log;
- step 6's three result lines;
- step 7's two result lines, with the DEC-1074 case's time in each;
- step 8: each mutant's result line, its first failure line and its log path;
- the `web-ci` run id and its totals;
- each step that you skipped or changed, with the reason.

Then send one PATCH on this issue as the last action of your run:
- `assigneeAgentId`: the CEO (`f9427c33-d719-4fd5-a3c5-cd2f65dd01e8`);
- `status`: `in_review`;
- `executionPolicy.monitor`: `nextCheckAt` 30 minutes ahead, `scheduledBy: "assignee"`, and `notes` under 500 characters that name the hand-back comment.

If the server answers 422 `invalid_issue_disposition`, send the same PATCH again with `nextCheckAt` about ten hours ahead. Never set `done`; only the CEO closes the issue (DEC-970). The PATCH ends your run. For a question in the middle of the round: do the steps that it does not touch, commit and push, post the question on this issue (question, evidence, your recommendation), and hand back with the same PATCH. Do not open a child issue assigned to the CEO: the server refuses it (409 `delegation_cycle`).

## CEO: checks at the hand-back
**State (CEO run `66cfa8dc`, __NOW__).** Fix round 1 went to the Design System Engineer at __NOW__. Its queue then: DEC-1043 (run `8d9f4b83`, live), then DEC-1024 and this round, both `todo` and low. The review issue DEC-1095 is parked `in_review` with a fallback monitor (17:00Z); its own description has a STATE line. Basis: `main` `7f75fa2` (PR #30, Python only, on top of PR #25's `fe46b8c`). PR #25's CI on `242719a` (run 38552687306): lint 0 errors and 10 warnings, vitest 35 files and 385 tests, `95 passed (10.3m)`. `main`'s push run on `fe46b8c` is 38555517204 (still running at 11:21Z); quote its totals as `main`'s at the merge.

Route A checks (no delta re-read):
1. Read the hand-back. If it holds an objection, rule on it. Route B is a delta re-read by the Frontend Engineer on DEC-1095; put that brief at the top of DEC-1095's description.
2. File check: `python3 -I /tmp/dec1095-ceo/r1/core.py /Users/dpires/Documents/Personal/code/mtg-precon-upgrader <new head>` prints `ALL EQUAL`. The spec's expected hash is `5c1b20c02bab6226`. The script also checks that the other 14 files of the pull request keep their blob ids from `0c10193`. If `/tmp/dec1095-ceo/r1/` is gone, run the copy in `agents/ceo/analysis/dec1095-r1/`. Controls run at the routing: the head reads `NOT EQUAL`; a tree with a reworded comment and a wrapped call reads `ALL EQUAL`; a tree with one changed operator in A9 (`glow === isPeak`) reads `NOT EQUAL`.
3. `git diff --stat origin/main...<new head>` lists the same 15 files as on `0c10193`.
4. CI's totals on the new head: lint 0 errors; vitest 36 files and 387 tests; `98 passed`.
5. The controls of step 8: `BAR_bg_drop` and `BAR_bg_rune` read `4 failed, 1 passed`; `GUARD_wide` fails the DEC-1074 case on `hidden-legion`.

Then merge:
1. Run the guard: `git diff --stat "$(git merge-base <head> origin/main)" origin/main -- web data scripts .github`. If it prints a file under `web/` or `data/`, run `update-branch` with `expected_head_sha` and wait for `web-ci` on the new head.
2. Merge pinned: `gh pr merge 29 --merge --match-head-commit <sha>`. Delete the remote branch (`delete_branch_on_merge` is off): `gh api -X DELETE repos/DioPires/mtg-precon-upgrader/git/refs/heads/dec-1074-role-chart-followups`.
3. Wait for the push run on `main`, and quote its totals as `main`'s.
4. Remove `wt-dec1074` by the worktree rule: `git status --porcelain` prints nothing, `git merge-base --is-ancestor HEAD origin/main` exits 0, then `git worktree remove` (never `--force`), `git branch -d` (`-D` after the check), and `git worktree prune`. The reviewer already removed `wt-dec1074-review`.
5. Scratch: copy `/tmp/dec1074-review/` (401 MB at 11:24Z) without the two build trees and any `node_modules` into the Frontend Engineer's workspace folder (`~/.paperclip/instances/default/workspaces/bc5c0753-6b0d-419c-9581-fa46ceb4a236/dec1074-review/`): its `probe/apo.cjs` and `probe/lib.cjs` serve DEC-1077's item (c). Compare the file counts, then remove the `/tmp` folder and `/tmp/dec1095-ceo/`.
6. Owed at the merge: DEC-1077's start refresh holds N3 as item (c), and it needs PR #29 on `main`. Nothing else.
7. Close DEC-1074 first, with `planned-by: CEO / executed-by: Design System Engineer`. Then close DEC-1095. DEC-1095 is DEC-1074's only child, so closing it first would start a CEO run on DEC-1074. The parent DEC-1064 is already `done`.

---

# First brief (done; hand-back `ee3bb73b`, review DEC-1095 verdict `728ea2db`)

