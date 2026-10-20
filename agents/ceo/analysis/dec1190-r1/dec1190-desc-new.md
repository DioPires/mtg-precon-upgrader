**STATE (CEO run `3b474ad1`, 2026-10-16 20:40Z). Read this line first.** Fix round 1 below is done: hand-back `deccb27c`, round head `69eb1f4`, `web-ci` 38958037742 green. At 20:34Z I ran `gh pr update-branch 79` after PR #80 merged. The head is now `b342ea1` (`main` `8fb404c` merged in; tree `e82dc7b5` equals the merge tree). `web-ci` run 38963214555 runs on it. Re-read 1 is with the Frontend Engineer on [DEC-1193](/DEC/issues/DEC-1193) (run `2baa11c7`, started 20:36:05Z). On APPROVE, the merge steps of the STATE block below apply, with `8fb404c` in place of `8f15c33` in step 1 and `b342ea1` as the pinned head unless `main` moves again. Fallback monitor: 23:00Z.

---

**FIX ROUND 1 (CEO run `d7ac712f`, 2026-10-16 19:50Z). Read this section first.**

**Outcome.** Review [DEC-1193](/DEC/issues/DEC-1193) returned CHANGES (verdict `9fea43e9`) on head `017060e`. The product code stands. Four mutants survive on lines that the pull request adds, so four tests are missing. Fix the tests only. Budget: about 1 hour. Priority low. Port: `GRIMOIRE_E2E_PORT=14971`.

**Do (in `wt-dec1190`, branch `dec-1190-glyph-names`):**
1. **B1 (mutant R4).** In `glyph-source.test.ts`, add `export const G = () => <p>a − b</p>;` to the fixture and expect the check to flag it. In the spec, add one plain case: `glyphsIn('a − b')` equals `['−']`, and `glyphsIn('−1')` equals `[]`.
2. **B3 (mutant R14).** After spec line 375, assert that the Type row's `.gv1-scry-delta-detail` reads `/^\S+ to \S+$/`.
3. **B2 and B4 (mutants R13 and R17).** Add a second Scrying swap that changes the land count and adds a Game Changer that is not a land. One example: cut a basic land for a Game Changer. Assert that the Lands row's detail reads `/^\d+ to \d+$/`, and that the Game Changers row's `.gv1-scry-delta-change` reads "+1". If the stub has no card that fits, a Vitest render of the delta rows with fixture data is acceptable, if R13 and R17 then fail.
4. **N1.** Add one comment at spec line 71 that says why the rule skips `RootWebArea` and `InlineTextBox`.
5. **N2.** Read the second Compare state through `state(page, 'compare-turned', …)`, so the state rules run on it too.
6. **N3: no change.** The "★ ↔" branch stays a named limit; R16 and `glyph-words.test.tsx` cover it.
7. **Mutants.** Run R4 (the Vitest file and the spec), R13, R14 and R17 again, as `mut/all.py` in the reviewer's folder defines them: `$PAPERCLIP_GITHUB_HOST_HOME/.paperclip/instances/default/workspaces/bc5c0753-6b0d-419c-9581-fa46ceb4a236/dec1193/mut/`. Each must now fail at least one case. Restore the tree after each, and check that `git status --porcelain` prints only your test edits.
8. **Suites.** Run lint, typecheck, Vitest and the full Playwright suite with 3 workers at most. Quote the count lines.
9. **No product change.** Only test files change: `git diff --stat 017060e HEAD -- web` lists only files under `web/src/__tests__/` and `web/tests/`. So the pixel counts of the verdict stand, and you take no new shots.
10. **No merge of `main`.** `main` `349e13f` has no change under `web/`, `data/` or `.github/` after `8f15c33` (the reviewer checked at 19:35Z). If `main` changes there during the round, do not merge it; I update the branch at the merge.
11. Commit and push. Wait for `web-ci` on the new head with a bounded loop in the foreground (about 10 minutes).

**Rules.** Set `HOME="$PAPERCLIP_GITHUB_HOST_HOME"` for every `git` and `gh` command. Set `PLAYWRIGHT_BROWSERS_PATH="$PAPERCLIP_GITHUB_HOST_HOME/Library/Caches/ms-playwright"` and `GRIMOIRE_E2E_PORT=14971` for every Playwright run. No request to `api.scryfall.com` or `cards.scryfall.io`. Keep `wt-dec1190` until the merge.

**Handoff.**
1. Post one comment on this issue with: the new head, `git diff --stat 017060e HEAD`, each mutant's result with its log path, the count lines of each suite, and the `web-ci` run id and result. Keep the logs in `$PAPERCLIP_GITHUB_HOST_HOME/.paperclip/instances/default/workspaces/8ea33a50-69a7-4a75-bcc1-245bd1e7c73a/dec1190/fix1/`.
2. As the last action of your run, send one PATCH on this issue: `assigneeAgentId` the CEO (`f9427c33-d719-4fd5-a3c5-cd2f65dd01e8`), `status: in_review`, and `executionPolicy.monitor` with `nextCheckAt` 30 minutes ahead, `scheduledBy: "assignee"` and `notes` under 500 characters that name your comment.
3. If the server answers 422 `invalid_issue_disposition`, send the same PATCH again with `nextCheckAt` about ten hours ahead. Never set `done`.
4. **A question in the middle of the round.** Do the parts that the question does not touch first, then commit and push. Post the question with its evidence and your recommendation. Then send the PATCH of step 2 as the last action of your run. Do not open a child issue assigned to the CEO (409 `delegation_cycle`).

**Next.** At your hand-back, the Frontend Engineer re-reads the round on DEC-1193. On APPROVE, the merge steps of the STATE block below apply.

---

**STATE (CEO run `9e4de761`, 2026-10-16 16:23Z). Fix round 1 above comes first. The "On APPROVE" merge steps here still apply after the re-read. The build brief below is done; do not start it again.**

- **Done.** PR #79 is open, head `017060e`, base `main` `8f15c33`, `web-ci` run 38926608379 green. Hand-back `d79ab19a`. My rulings are in comment `cf646682`: the minus-sign rule stands; the pixel cause stands if the reviewer's control shows it in all 15 states; `lib/comboVerify.ts:517` is a named limit.
- **Where the leg is.** Review [DEC-1193](/DEC/issues/DEC-1193) (the Frontend Engineer, low). Its hand-back comes to me on DEC-1193, with its own 30-minute monitor.
- **On APPROVE.**
  1. Run `HOME="$PAPERCLIP_GITHUB_HOST_HOME" git fetch origin`, then `git diff --stat 8f15c33 origin/main -- web data .github`.
  2. If step 1 prints files, run `HOME="$PAPERCLIP_GITHUB_HOST_HOME" gh pr update-branch 79` and wait for `web-ci` on the new head (about 10 minutes) with a bounded loop.
  3. Merge pinned: `gh pr merge 79 --merge --match-head-commit <head>`.
  4. Wait for the push run on `main` and the Vercel deploy. Quote the count lines.
  5. Remove `wt-dec1190`: `git status --porcelain` prints nothing, `git merge-base --is-ancestor HEAD origin/main` exits 0, then `git worktree remove` (never `--force`), `git branch -D dec-1190-glyph-names`, `git worktree prune`, and delete the remote branch if GitHub kept it.
  6. Close DEC-1193, then this issue. The A/B leg on DEC-1182 waits for the owner's card `345bc3b0`; see the DEC-1182 state block.
- **On CHANGES.** Write a fix round for the Design System Engineer at the top of this description ("FIX ROUND 1. Read this section first"). The re-read goes back to the Frontend Engineer on DEC-1193.
- **Known limits.** R0 and the middle dot rest on the DEC-1182 reading (no VoiceOver pass). `lib/comboVerify.ts:517` keeps "≤". `Hero.tsx` is imported by no module.
- **Fallback monitor:** 20:50Z.

---

## Build brief (done)

**Started (CEO run `370ec983`, 2026-10-16 15:11Z), from the DEC-1182 hand-back `12805aca`.** I ruled on every class and on the words in the comment that follows the hand-back on [DEC-1182](/DEC/issues/DEC-1182). This leg builds the whole fix as one pull request. `<N>` is this issue's number.

**Implementer: the Design System Engineer (`8ea33a50`). Tier 1, priority low. Budget: about 6 hours. Port: `GRIMOIRE_E2E_PORT=14971`. Web only. One pull request; do not merge it.**

## Why one pull request
Your hand-back split the fix in two only because class C3 waited for my words. The words are below, so one review covers the whole fix.

## What the pull request does
Your census is the list of sites. `main` moved after `08d741e`: PRs #72, #71 and #75 merged and changed `Shopping.tsx` and three other files. Run `census.mjs` again on your tree first, and work from the new line numbers.

1. **C1, a decorative span alone (4 sites).** Put `aria-hidden="true"` on the span: `Scrying.tsx` ⚠ and ✓, the rail folio "§ XII" and the TOC folio ◈ in `ComboLab.tsx`.
2. **C2, a decorative glyph inside a text string (26 sites).** Add the atom `web/src/components/atoms/Glyph.tsx`. It renders `<span aria-hidden="true">{children}</span>`. Split each string: the glyph goes in `Glyph` and the words stay as text. Where a ternary picks a string, make the chosen branch JSX. A space next to the glyph goes inside `Glyph`, not outside it. Chromium keeps a space that sits outside a hidden span, so `Copied <span aria-hidden="true">◆</span>` reads "COPIED " with a trailing space.
3. **C3, a glyph that carries meaning.** Hide the glyph and add the words in a `gv1-sr-only` span. For a control whose whole name is the glyph, use `aria-label`. For strings from `.ts` modules, split them where they render, with one helper. Do not change the data. The words are fixed:

| Glyph | Sites | Words that the reader hears |
|---|---|---|
| ★ | `CardTile.tsx` (the tile star), `Decklist.tsx` (the row star) | " (Game Changer)", after the card name in reading order. Keep the text of each element that a test or a feature reads as the card's name unchanged; put the words in a sibling span if needed. |
| ★ and ↔ | `Scrying.tsx` ("★ +1", "★ −1", "★ ↔") | Hide both glyphs. The row label says "Game Changers", and the detail cell says "GC for GC — count unchanged". |
| → | `Scrying.tsx` (mana value, average mana value, lands, type) and the `gcDetail` strings of `lib/scrying.ts` | "to" |
| ▲ ▼ | `Compare.tsx`, Sorted by | ▲ (`asc` true) is "ascending"; ▼ is "descending". |
| ≥75, 50–74, &lt;50 | `Compare.tsx`, the Scale legend | "75 or more", "50 to 74", "under 50". All three pills, so the legend reads as one set. |
| № | `Codex.tsx`, the sort chip whose whole name is "№" | `aria-label="deck number"` |
| ⇣ | `ComboLab.tsx`, the two export buttons | "Download". The buttons read "Download .txt" and "Download .md". |
| ↗ | `ComboLab.tsx`, the two Spellbook links with `target="_blank"` | " (opens in a new tab)" |
| → | `ComboLab.tsx`, before the produces list of a near miss | "produces" |
| ⟶ | `ComboLab.tsx`, a synergy edge | "to" |
| −n | `ComboLab.tsx`, the distance chip | The `title`'s words: "1 piece short", "2 pieces short". |
| ↔ | the coupling labels of `lib/synergyMatch.ts` and `lib/nearMissComplete.ts`, where `ComboLab.tsx` renders them | "pairs with" |
| → | the trace strings of `lib/comboVerify.ts`, rendered by `Steps` | "then" |

4. **C4, CSS `content:` (1 rule).** `combo-lab.css`: `.gv1-lab-steps summary::before` gets `content: '▸'; content: '▸' / '';`. The `[open]` rotation stays. In `states.css`, delete the `.gv1-loading-inline` rules if `git grep -n 'gv1-loading-inline' -- web` lists only `states.css`; otherwise give its `::before` the same `/ ''` form.
5. **C5, mana symbols (from your notes outside the leg).**
   - `ManaCost.tsx`: the `.gv1-mv` wrapper gets `role="img"` and one label built from the pips, for example "Mana cost: 2 generic, blue, blue". Name the colours as words: W white, U blue, B black, R red, G green, in every kind of pip (hybrid "white or blue hybrid", phyrexian "white or 2 life phyrexian"). The pips inside an image are not read, so drop their own `aria-label`. The land and `—` paths stay as they are.
   - `GV1ManaPips.tsx`: the label names the colours in the given order, for example "Color identity: blue, red". An empty string or ◇ alone reads "Color identity: colorless". Export one helper for the colour words.
   - `ComboLab.tsx`, the line "Color identity 🔴⚫ · legal in Commander": hide the emoji span and add the same words in `gv1-sr-only`.
6. **Any other glyph that the new spec finds** in a state it reads (a glyph that comes from data, not from a literal) takes the rule of its class. List each one in the hand-back with the class you gave it.
7. **No pixel changes.** Do not touch `styles.css` or `app.css`: PR #73 changes both and waits in the merge queue. If a change there seems needed, ask (Handoff step 4).

## Tests
1. **Chromium's tree.** Turn `ax-reads.spec.ts` into `web/tests/dec<N>-glyph-names.spec.ts`. Import `test` and `expect` from `./support/test`. Keep the 23 states, and read CDP `Accessibility.getFullAXTree` after `document.fonts.ready`. In each state, no node that Chromium does not ignore may have a name that holds a glyph outside R0 and `·`. Add one assertion for each row of the table above on the name that Chromium computes, for example: a Game Changer tile holds "Game Changer", the export buttons are named "Download .txt" and "Download .md", each Spellbook link's name ends in "(opens in a new tab)", and "Sorted by" reads "ascending". No name that held a hidden glyph starts or ends with a space. Add one state for a card's mana cost that reads, for example, "Mana cost: 2 generic, blue, blue".
2. **Stylesheets.** Widen the third case of `web/tests/dec1177-empty-sigils.spec.ts` from `.gv1-empty::before` to every `::before` and `::after` rule whose content is not `''` or `none`. Each such rule must have a plain declaration followed by one with `/ ''`.
3. **Source check.** Add a Vitest file under `web/src/__tests__/dec<N>/`, built from `census.mjs`. It fails when JSX text, or a string literal that is a JSX child, holds a glyph outside R0 and `·` with no `aria-hidden` ancestor (`Glyph` counts as one). Keep the R0 list in the file: № × ± € © § ∞. Name its limit in a comment: an R0 sign in a decorative place passes.
4. **Mutants.** Run each of these on the branch and save one log for each under `/tmp/dec<N>/mut/`. Each must fail at least one case:
   - M1: `Glyph` without `aria-hidden`.
   - M2: no "Game Changer" words on the tile.
   - M3: `combo-lab.css` without the `/ ''` line.
   - M4: "ascending" and "descending" swapped.
   - M5: `ManaCost` without `role="img"`.
   - M6: the arrow helper renders → with no words.
   - M7: a new literal "◇ test" in a rendered JSX text (the source check must fail).
5. **Pixels.** Shoot the 23 states on a `main` build and on the branch build. Read after `document.fonts.ready`, take each shot with `animations: 'disabled'`, and use the viewport of each read. Count the pixels that differ for each state. Expect 0, and explain any state that is not 0.
6. **Suites.** Run lint, typecheck, Vitest and the full Playwright suite with 3 workers at most. Quote the count lines.

## Setup
1. Make the tree: `cd /Users/dpires/Documents/Personal/code/mtg-precon-upgrader && HOME="$PAPERCLIP_GITHUB_HOST_HOME" git fetch origin && HOME="$PAPERCLIP_GITHUB_HOST_HOME" git worktree add -b dec-<N>-glyph-names wt-dec<N> origin/main`. Then run `npm ci` in its `web/`.
2. Set `HOME="$PAPERCLIP_GITHUB_HOST_HOME"` for every `git` and `gh` command.
3. Set `PLAYWRIGHT_BROWSERS_PATH="$PAPERCLIP_GITHUB_HOST_HOME/Library/Caches/ms-playwright"` and `GRIMOIRE_E2E_PORT=14971` for every Playwright run. Use 3 workers at most; the Mac is shared.
4. Send no request to `api.scryfall.com` or `cards.scryfall.io`. The e2e stub answers every case.
5. Copy your census kit from `$PAPERCLIP_GITHUB_HOST_HOME/.paperclip/instances/default/workspaces/8ea33a50-69a7-4a75-bcc1-245bd1e7c73a/dec1182/`. Keep scratch under `/tmp/dec<N>/`, and keep any scratch Playwright config outside the tree.
6. Before your push and again before the hand-back PATCH, run `git diff --stat "$(git merge-base HEAD origin/main)" origin/main -- web data .github` after a `git fetch`. If it prints anything, merge `origin/main`, run the suites again, and push.

## Not in this leg
- Proposals A and B of your hand-back (one glyph in the /shopping, Compare and Combo Lab loading states). They change what users see, so they went to the owner on a card on DEC-1182. They come as their own small leg after the answer.
- A screen-reader pass with VoiceOver. R0 stands on the reading in your hand-back.

## Handoff
1. Open the pull request against `main`. Its body holds the new census table, the C3 table, the mutant results and the pixel counts.
2. Post one comment on this issue with: the pull request's number and head, the new census lines, the count lines of each suite, each mutant's result with its log path, the pixel count for each state, and any site from step 6 of the work. Keep the evidence in `$PAPERCLIP_GITHUB_HOST_HOME/.paperclip/instances/default/workspaces/8ea33a50-69a7-4a75-bcc1-245bd1e7c73a/dec<N>/` and give that path.
3. Keep `wt-dec<N>` until the merge. Remove every other scratch tree with `git worktree remove` (never `--force`), and name the trees in the comment.
4. As the last action of your run, send one PATCH on this issue: `assigneeAgentId` the CEO (`f9427c33-d719-4fd5-a3c5-cd2f65dd01e8`), `status: in_review`, and `executionPolicy.monitor` with `nextCheckAt` 30 minutes ahead, `scheduledBy: "assignee"` and `notes` under 500 characters that name your comment.
5. If the server answers 422 `invalid_issue_disposition`, send the same PATCH again with `nextCheckAt` about ten hours ahead. Never set `done`.
6. **A question in the middle of the leg.** Do the parts that the question does not touch first, then commit and push. Post the question with its evidence and your recommendation. Then send the PATCH of step 4 as the last action of your run. Do not open a child issue assigned to the CEO (409 `delegation_cycle`).

planned-by: CEO (run `370ec983`). Source: DEC-1182 hand-back `12805aca` and the ruling after it. Parent: DEC-1182.


