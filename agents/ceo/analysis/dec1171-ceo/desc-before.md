**Restart of [DEC-1024](/DEC/issues/DEC-1024) (CEO merge run `d944cad2` on DEC-1154, 2026-10-15 23:07Z). The server stopped DEC-1024 on 2026-10-13 (`recovery_needed`), so no run can start there. This issue carries its work. Read this section first: where it differs from the original brief below the line, this section wins.**

Implementer: the Simulation Engineer (`6ba3ac88`), the board's choice on 2026-10-14. Reviewer at the hand-back: the Design System Engineer (`8ea33a50`), who owns the shell and found the three notes. Tier 1, priority low. Budget: about 3 hours. Port: `GRIMOIRE_E2E_PORT=14897`. Your queue at 2026-10-15 23:07Z: your DEC-1161 run `a1849fc5` (low) is live. Finish DEC-1161 first; this issue's run queues after it.

**The work in one line.** Give the shell's `main` a phone side padding at 768 px and below (`app.css`), because its 64 px gutter leaves the Shopping and Compare sections a 160 px content column on a 320 px screen. Items 1 to 7 and 10 to 14 of the original brief stand, with the changes below.

## What changed since the original brief
1. **PR #65 (DEC-1154) merged at 22:53:37Z as `904c74d`.** It adds a `@media (max-width: 480px)` block for the /shopping summary (`styles.css:3384-3390`). The stats wrap in a flex row (`flex: 1 1 0`), the figures are 28 px, the action row takes a line of its own, and its buttons keep each label on one line. PR #65 also removed the dead `.gv1-shop-summary-stat` line.
   - **Run PR #65's two specs before and after your rule.** `dec1154-shop-summary.spec.ts` and `dec1154-shop-summary-rule.spec.ts` read the summary box's width, and a wider `main` changes how the stats wrap. Each spec runs with the fonts live and blocked. Quote both count lines on `main` and on your branch.
   - **Item 8 is done.** Strike it.
   - **Items 4 and 9 become checks.** On `main` no stat passes the summary's box at 320, 360, 390, 430 or 480 px. After your rule, quote each stat's right edge against the summary's content edge at 320 px, with the fonts live and blocked, for the first deck and for every deck with the brewing decks.
2. **PR #19 (DEC-1045) merged on 2026-10-13.** The e2e suite answers Scryfall from repository data (`web/tests/support/`). Use `GRIMOIRE_E2E_PORT`; no scratch config. A new spec imports `test` and `expect` from `./support/test`, and `test.use({ fonts: 'blocked' })` blocks the web fonts. The Setup lines about port 4173, a scratch config, `page.route` and the live API no longer apply. Item 9's "every card answer in and none" becomes the stub's prices (the default selection) and every deck selected.
3. **Line numbers on `main` at `904c74d`.** They replace the table "Basis after the PR #11 merge".

| Rule | Line |
|---|---|
| `.gv1-app > main` padding, 48 px by 64 px at every width (N1) | `app.css:7` |
| The deck guide's opt-out | `app.css:12` |
| The Combo Lab's opt-out | `combo-lab.css:228` |
| The phone summary rules in `@media (max-width: 768px)` from line 2155 | `styles.css:2157-2166`; the action row's `justify-self` at 2164 and `justify-content` at 2165 |
| PR #11's summary rule, `@media (max-width: 1080px)` | `styles.css:3119-3126`; `justify-self` at 3123 and `justify-content` at 3124 |
| The topbar's first breakpoint, 1330 px (item 13) | `styles.css:3066` |
| The 768 px block | starts at `styles.css:3162` |
| `.gv1-shop-section { padding-top: 16px }`, still dead (N6, item 5) | `styles.css:3212` |
| The rail's focus margin: comment at 3229-3231, `scroll-margin-top: 216px` at 3233 (item 11) | `styles.css:3229-3234` |
| The 768 px block's summary rules | `styles.css:3262-3270` |
| `.gv1-section { padding: 32px 16px }` | `styles.css:3278` |
| PR #65's phone rule, `@media (max-width: 480px)` | `styles.css:3384-3390` |

4. **Item 10's caution now covers four rules.** The summary's action row takes its values from `styles.css:2162-2166`, `3121-3126` and `3266-3270`, and at 480 px and below from `3388-3389`. An edit to any of them changes phones.
5. **Totals on `main` at `904c74d`** (push run 38820146768): lint `✖ 10 problems (0 errors, 10 warnings)`, `Test Files  51 passed (51)`, `Tests  612 passed (612)`, and Playwright `205 passed (10.7m)`. Quote the totals of the `main` that you branch from.

## Open work that touches the same files
- **PR #68** (DEC-1156, the engine panel's role title) changes `styles.css`. Its review is out.
- **[DEC-1167](/DEC/issues/DEC-1167)** (Frontend Engineer, started at 2026-10-15 23:07Z) keeps the /shopping summary section in the page with no deck selected. It changes `Shopping.tsx`, not the stylesheet. That section has no class while no deck is selected, so read the Shopping `.gv1-section` widths with a deck selected (the default).
- If either merges before your hand-back, merge `origin/main` (the guard in the Rules) and run the suites again.

## Rules (they replace the Setup section of the original brief)
- **Environment.** Set `HOME="$PAPERCLIP_GITHUB_HOST_HOME"` for every `git` and `gh` command. Set `PLAYWRIGHT_BROWSERS_PATH="$PAPERCLIP_GITHUB_HOST_HOME/Library/Caches/ms-playwright"` for every Playwright run; without it every case fails at launch.
- **Tree.** Run `cd /Users/dpires/Documents/Personal/code/mtg-precon-upgrader && git fetch origin && git worktree add wt-dec<N> -b dec-<N>-shell-phone-padding origin/main`, then `npm ci` in its `web/`. `<N>` is this issue's number. Screenshots go under `web/qa-screenshots/dec<N>/` (force-add). Touch no other tree. Keep scratch files under `/tmp/dec<N>/`. Never use `git worktree remove --force`.
- **No live request.** Send no request to `api.scryfall.com` or `cards.scryfall.io` from a script, a test, a browser or `curl`.
- **Workers.** Run Playwright with 3 workers at most; the Mac is shared.
- **Fonts and shots.** Read every width and height after `document.fonts.ready`, once with the fonts live and once with them blocked. Take each screenshot with `animations: 'disabled'`.
- **Mutants.** For each CSS line that you add or rewrite, run at least one mutant and name the case that kills it.
- **Before the hand-back PATCH.** Run `git fetch origin` and `git diff --stat "$(git merge-base HEAD origin/main)" origin/main -- web data .github`. If it lists a file, merge `origin/main`. Then run `cd web && npm run lint && npm run typecheck && npm test -- --run && GRIMOIRE_E2E_PORT=14897 npm run test:e2e -- --workers 3`, quote the four count lines, and wait for `web-ci` on your last push.
- Open one pull request against `main`. Its description names this issue and DEC-1024. Do not merge.

## Handoff (it replaces the Handoff section of the original brief)
1. Post your evidence as one comment on this issue: the pull request, its head, the four count lines, CI's run id and totals, the readings that the Acceptance sections ask for, the mutant table, and each departure from this brief with its reason.
2. As the last action of your run, send one PATCH on this issue: `assigneeAgentId` the CEO (`f9427c33-d719-4fd5-a3c5-cd2f65dd01e8`), `status: in_review`, and `executionPolicy.monitor` with `nextCheckAt` 30 minutes ahead, `scheduledBy: "assignee"` and `notes` under 500 characters that name your comment.
3. If the server answers 422 `invalid_issue_disposition`, send the same PATCH again with `nextCheckAt` about ten hours ahead. Never set `done`; only the CEO closes the issue.
4. **A question in the middle of the leg.** Do the parts that the question does not touch, then commit and push. Post the question with its evidence and your recommendation. Then send the PATCH above as the last action of your run. Do not open a child issue assigned to the CEO: the server refuses it (409 `delegation_cycle`).

---

## The original brief (DEC-1024, copied at 2026-10-15 23:07Z)

Give the shell's `main` a phone-width side padding, because its 64 px gutter at every width leaves a 160 px content column on a 320 px screen. Web only. Shell owner: Design System Engineer (`8ea33a50`). Tier 1.

**Why.** Three notes from the DEC-1019 hand-back (Design System Engineer, comment `c24c6f61`, 2026-10-13 01:47Z), measured on PR #8 at `ced47d5` and the same on `main` at `e0d7d5f`.

1. **N1.** `web/src/styles/app.css:7` sets `.gv1-app > main { padding: var(--gv1-space-12) var(--gv1-space-16) }`, that is 48 px by 64 px, at every width. `.gv1-section` adds `32px 16px` at 768 px and below (`styles.css:3141` on `main` at `cb33744`; 72 px at desktop). So at 320 px the content column is 320 − 128 − 32 = 160 px. The Shopping rail's head wraps to three rows because of it. Three surfaces opt out: the deck guide (`app.css:12`), the Combo Lab (`combo-lab.css:227`) and Scrying. Shopping, Codex, Compare and Atlas do not. (Corrected by the DEC-1026 review, round one N14a: the Apothecary is part of the guide, and Scrying also opts out.)
2. **N5.** At 320 px the third Shopping summary stat ends 2.8 px past its column (right edge 258.8 against 256).
3. **N6.** `.gv1-shop-section { padding-top: 16px }` (`styles.css:3074` on `main` at `cb33744`, inside the 768 px block) never applies. `.gv1-section { padding: 32px 16px }` at `:3141` comes later with the same specificity, so the rail's computed `padding-top` reads 32 px.

The DEC-1019 review (DEC-1026, Frontend Engineer) swept the widths. Its figures are in the section "Added at the PR #8 merge" below, and that section overrides the text above where they differ.

## Ask
1. **Before.** Measure the content-box width at 320, 390, 768 and 1024 px: the `.gv1-section` on Shopping and Compare, and `main` on Codex and Atlas (they have no `.gv1-section`). Quote the sixteen figures.
2. **Rule.** Set a phone-width side padding for `main` in `app.css`, beside the guide's opt-out, at 768 px and below. You pick the value; the guide's 0 and the section's 16 px are the two references in the shell. Do not do it per surface. Say why you picked the value.
3. **After.** Repeat item 1 and quote the sixteen figures. The 769 to 978 px band is DEC-1017's (Frontend Engineer); your rule must not change widths above 768 px.
4. **N5.** Fix the 2.8 px overrun, or show that the padding change removes it (quote the stat's right edge against the column at 320 px).
5. **N6.** Remove the dead `padding-top: 16px` rule, or move it after `.gv1-section { padding: 32px 16px }` if the 16 px was intended. Quote the rail's computed `padding-top` at 390 px after.
6. **Overflow checks.** `dec181-qa.spec.ts`, `dec184-visual-qa.spec.ts`, `dec1008-root-overflow.spec.ts` and `dec1019-root-clip.spec.ts` must still pass. Add one e2e case only if it is cheap: the Shopping `.gv1-section` content box reads at least a floor you name at 320 px, failing on `main` (160 px) and passing on the fix.
7. **Screenshots** under `web/qa-screenshots/dec<this issue>/` (force-add): Shopping and Codex at 320 px and 390 px, before and after.

## Acceptance (quote the figures in the hand-back comment)
- The readings from items 1, 3, 4 and 5.
- `cd web && npm run lint && npm run typecheck && npm test -- --run && npm run test:e2e` exit 0; quote the vitest and Playwright totals (on `main` at `cb33744`, after PR #8: 33 files, 362 tests; 50 Playwright; PR #9 and PR #11 add cases, so quote the totals of the `main` you branch from). CI `web-ci` green on the PR.
- `git diff --stat origin/main...HEAD` touches only `web/`.
- PR against `main`, one or two commits, description names this issue. Do not merge; the CEO merges after the review.

## Setup
- Both pull requests that this issue waited for are merged: PR #9 (DEC-1021) at `366518d` and PR #11 (DEC-1017) at `090a151` (2026-10-13 15:17Z). PR #8 (DEC-1019) merged at `cb33744`. Branch from `origin/main` at `090a151` or later. Scratch tree `wt-dec1024` under the repository root. Do not touch another agent's `wt-dec*` tree.
- `gh`, `git push` and `git commit` need `HOME="$PAPERCLIP_GITHUB_HOST_HOME"` in agent runs. Playwright needs `PLAYWRIGHT_BROWSERS_PATH="$PAPERCLIP_GITHUB_HOST_HOME/Library/Caches/ms-playwright"`, or the browsers fail to launch (DEC-1018 N2).
- Playwright reuses a server already on port 4173 (`playwright.config.ts`, `reuseExistingServer`), and the `lsof` check is racy (DEC-1026 N16). Run the e2e suite through a scratch config that imports `web/playwright.config.ts`, on a private port, with `reuseExistingServer: false`, and name the port. If DEC-1045 has merged, use its port variable instead.
- `web/qa-screenshots/dec-184/findings.json` is no longer tracked (PR #11), so `npm run test:e2e` leaves the checkout clean.
- Keep the legacy root app untouched.

## Added 2026-10-13 from the DEC-1044 review of PR #11 (your note N13)
8. **Correct the dead selector; do not delete the rule.** Inside the 768 px block, `.gv1-shop-summary-stat .gv1-serif-xl { font-size: 28px; }` has never applied (`styles.css:3162` on PR #11 at `7b4e765`; `styles.css:3128` on `main` at `cb33744`; the line moves again when PR #11 merges). The markup uses `.gv1-shop-stat` (`Shopping.tsx:650-662`), and nothing else under `web/src` names `.gv1-shop-summary-stat`. Change the selector to `.gv1-shop-stat .gv1-serif-xl`. This is your ruling on DEC-1044 (verdict `ba06cc6d`, N13), and the CEO accepts it.
   - **Your readings at 320 px on PR #11's head, no prices in.** The third stat is 216.5 to 258.8 against 256. With the selector corrected it stays at 258.8, because the column is as wide as the word "UNIQUE" (42.2 px), not the value. So the selector is not the cause of item 4's 2.8 px.
   - **Prices in.** The first column is 86.3 px (`$1191` at 42 px) and the third stat ends at 302.8. With the selector corrected the first column is 57.5 px and the third stat ends at 274.0. The correction removes 28.8 px.
   - With no prices the three columns need 161.8 px in a 126 px content box (97 to 223). The padding rule in item 2 must supply the rest.
9. **Item 4 now has two card states.** Read the third stat's right edge against its column at 320 px with every card answer in and with none, before and after. The 258.8 in N5 above is the state with no prices; with the prices in the stat ends at 302.8.
   - Scryfall answered 429 to this Mac during DEC-1044 (N15). If DEC-1045 has merged, use its stub. If not, serve the card answers by `page.route` from `data/card-metadata.json` and `data/spellbook/price-index.json`, as you did on DEC-1044. Do not loop the live API.
10. **One caution from the same review (N5a).** After PR #11, `.gv1-shop-summary-actions` takes `justify-self: stretch` and `justify-content: space-between` on phones from PR #11's Shopping summary rule (ahead of the 768 px block), and no longer from the phone rule at `styles.css:2109-2110`. Both rules give the same values today. An edit to either rule changes phones.

Acceptance adds the readings from items 8 and 9.


## Added at the PR #8 merge (2026-10-13, DEC-1026 review)
PR #8 (DEC-1019) merged at 13:11:59Z; `main` is `cb33744`. The review on DEC-1026 (Frontend Engineer, round one verdict `8e365265`, round two verdict `a1116f2b`) gives the figures below. This section overrides the text above where they differ.

**Widths on `main` before your change** (round one N14a), at 320, 390 and 768 px:
- Shopping `.gv1-section` content box: 160, 230 and 608 px (six sections).
- Compare `.gv1-section` content box: 160, 230 and 608 px (two sections).
- Codex and Atlas have no `.gv1-section`. Their `main` content box reads 192, 262 and 640 px.
- The opted-out surfaces are the reference. Guide sections (the Apothecary among them) and Scrying sections read 288, 358 and 736 px.

**N5, item 4** (round one N14c). Confirmed, and worse against the summary's own box. At 320 px with no prices, the three stats end at 139.3, 202.5 and 258.8 px. The section ends at 256 px and the summary at 240 px. So the third stat runs 2.8 px past the section and 18.8 px past the summary. Quote both edges in item 4.

**N6, item 5** (round one N14d). Confirmed. The rail and every `.gv1-shop-section` compute `padding-top: 32px` at 320, 390 and 768 px, and 20 px at 1280 px.

11. **The rail's focus margin (round two R1).** PR #8 gives every control after the Shopping rail `scroll-margin-top: 216px` where the rail pins (`styles.css:3085-3096`, inside `@media (min-width: 600px) and (min-height: 800px)`). The rule's comment says "216px is the rail at its tallest (200px, 600–625px wide) plus 16px". The reviewer measured the 200 px band up to 632 px wide with two-digit counts (`· 12 of 12`, `· 21 of 21`) in Chromium and WebKit, and up to 642 px under WebKit's fallback font. No state read above 200 px. Your padding rule changes where the rail's head wraps, so measure again after it:
    - Read the rail's height at every width from 600 to 768 px, at 1024 px tall.
    - Use the five head states: default, all selected, none selected, brewing with none, and brewing with all.
    - Read with JetBrains Mono loaded and with `fonts.gstatic.com` blocked.
    - If no reading is above 200 px, correct the comment's width range with your figures. The reviewer's text is "216px is the rail at its tallest (200px, up to about 640px wide) plus 16px".
    - If any reading is above 200 px, set the margin to that height plus 16 px and quote the reading.
12. **The keyboard case at both pinned viewports (round two R2).** `web/tests/dec1019-root-clip.spec.ts` checks focus against the rail at 768×1024 only, where the rail is 148 px. Run the same `describe` at 600×960 too, where the rail is 200 px. The reviewer's form, with the body unchanged:
```ts
for (const { width, height } of [{ width: 768, height: 1024 }, { width: 600, height: 960 }]) {
  test.describe(`DEC-1019 Shopping rail, keyboard @ ${width}×${height}`, () => {
    test.use({ viewport: { width, height } });
    // body of 'focus does not land under the pinned rail', unchanged
  });
}
```
    At 600×960 it reads 216 against 200 today, and it fails if the rail grows past 216 px.
13. **A topbar breakpoint case (round one N10).** No e2e case covers the topbar's first breakpoint at 1330 px (`styles.css:3015`); the old 1240 px passes every DEC-1019 case. Add one case:
    - At 1241, 1280 and 1325 px, no end of the bar is taller than one line.
    - At 1331 px, `.gv1-topbar-right` shows and each end is one line.
    - The reviewer's heights with JetBrains Mono: an end reads 18 px or 14 px on one line and 28 px on two; the bar reads 53 px at every width. With the font blocked, the bar reads 52 px, the left end 17 px and the right meta 13 px at 1331 px.
    - For the negative control, set the line back to `@media (max-width: 1240px)` by hand, run the case, quote the failure and restore the line.
14. **Scripted clicks in the pin band (round two N9).** `locator.click()` scrolls its target into view before it clicks, and that scroll honours the 216 px margin. A user's click does not. In Chromium, on `Type` 12 px below the pinned rail, it moves the page 56 px at 768×1024 and 4 px at 600×960. In a case that reads positions after a `locator.click()` on a control after the rail, read them after that scroll, or press keys instead.

Acceptance adds the readings from items 11 to 13.

## Not in scope
- The 769 to 978 px band (DEC-1017, Frontend Engineer).
- The Shopping import control's keyboard access (its own issue, Frontend Engineer).
- The topbar, the deck guide and the Combo Lab, which already opt out.
- Any change to `scripts/` or `data/`.

## Handoff
When the evidence and the PR are in your comment, PATCH this issue: set `assigneeAgentId` to the CEO (`f9427c33-d719-4fd5-a3c5-cd2f65dd01e8`) and `status` to `in_review`. That assignment wakes the CEO, who opens the review issue (Frontend Engineer reviews) or routes fixes back to you. If the server answers 422 `invalid_issue_disposition`, send the same PATCH again with an `executionPolicy.monitor` block: `nextCheckAt` about ten hours ahead, `scheduledBy: "assignee"`, and `notes` under 500 characters that name the hand-back. Never set `done`; only the CEO closes the issue (DEC-970).

## Basis after the PR #11 merge (added 2026-10-13)
The line numbers above are from `cb33744` or from PR #11 at `7b4e765`. On `main` at `090a151`:

| Rule | Line on `main` at `090a151` |
|---|---|
| `.gv1-app > main` padding | `app.css:7` (unchanged) |
| `.gv1-shop-section { padding-top: 16px }`, inside the 768 px block (item N6) | `styles.css:3136` |
| `.gv1-section { padding: 32px 16px }`, inside the 768 px block | `styles.css:3203` |
| The dead selector `.gv1-shop-summary-stat .gv1-serif-xl` (item 8) | `styles.css:3190` |
| The phone rule for `.gv1-shop-summary-actions` (item 10) | `styles.css:2116-2120`; `justify-self` at 2118 and `justify-content` at 2119 |
| PR #11's Shopping summary rule, `@media (max-width: 1080px)` (item 10) | `styles.css:3067-3075`; `justify-self` at 3071 and `justify-content` at 3072 |
| The 768 px block's summary rules | `styles.css:3186-3195`; the block starts at 3086 |
| The rail's `scroll-margin-top: 216px` (item 11) | `styles.css:3156-3158` |
| The topbar's first breakpoint, 1330 px (item 13) | `styles.css:3020` |

- **The review changed PR #11's Shopping rule after items 8 to 10 were written.** The rule now applies at 1080 px and below (it was 980 px), and its stat columns are `repeat(4, auto)` (they were `repeat(4, minmax(0, 1fr))`). The 768 px block sets `grid-template-columns` and `gap` again at 3186-3189, so phones did not change: at 360, 375, 390 and 768 px every box on /shopping equals the `main` before the merge (DEC-1044 delta verdict `836929ea`, N2 and N5). Item 10's caution stands as written.
- Totals on `main` at `090a151` (push run 38420852874): vitest 33 files and 365 tests, Playwright `62 passed`, lint 0 errors and 10 warnings.
- Until DEC-1045 merges, every page in the e2e suite calls the live Scryfall API, and a slow answer timed out one hosted case (run 38413091908, attempt 1). Run the full suite once, and do not loop it.
- Read every height after `document.fonts.ready`. Take each screenshot after it, with `animations: 'disabled'`.

planned-by: CEO. Found on DEC-1019 (Design System Engineer hand-back, N1, N5, N6). Blocked by DEC-1021 and DEC-1017 (both change the 768 px block of `styles.css`, and items 8 and 10 are written against PR #11). Priority low: after DEC-1045 in your queue.
