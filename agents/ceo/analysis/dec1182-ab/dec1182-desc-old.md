**STATE (CEO run `c08f3a43`, 2026-10-16 20:57Z). Read this line first; it replaces the "Out" line below.** PR #79 ([DEC-1190](/DEC/issues/DEC-1190)) merged at 20:46:53Z as `e6d472e`, and DEC-1190 is closed. PR #73 merged at 15:19:45Z as `8f15c33`. So the only open item is the owner card `345bc3b0` (proposals A and B), still pending at 20:57Z. A run that the close of DEC-1190 starts here (`issue_children_completed`) does one thing: it reads the card. If the card is still pending, it re-parks this issue `in_review` with a fallback monitor and ends. If the card has an answer, the card rules below apply. Both gates of the A/B leg are now open.

---

**STATE (CEO run `d7ac712f`, 2026-10-16 19:43Z). Read this section first.**
- **Done:** the census leg (hand-back `12805aca`) and my ruling `db9cd4c5`.
- **Out:** PR #79 on [DEC-1190](/DEC/issues/DEC-1190) (head `017060e`). Review [DEC-1193](/DEC/issues/DEC-1193) (Frontend Engineer) returned CHANGES `9fea43e9`: four mutants survive, and each fix is a test change. Fix round 1 is with the Design System Engineer on DEC-1190. Its hand-back comes to DEC-1190; the re-read goes back to the Frontend Engineer on DEC-1193. Route both there, not here.
- **Owner card `345bc3b0`** (proposals A and B). The answer wakes a CEO run here.
  - If any option other than "keep both" is chosen, open one small leg after DEC-1190's pull request merges (it changes `ComboLab.tsx`) and after PR #73 merges (it changes `styles.css`). Proposal A is 4 container classes and 1 CSS rule; B is 2 text edits. Ask for shots before and after.
  - If "keep both" is chosen twice, record it and open no leg.
- **Close:** DEC-1182 closes when DEC-1190 has merged and the card has an answer and, if needed, its own leg.
- **Monitor:** a fallback only (22:45Z); re-arm it while DEC-1190 is out. DEC-1193 holds its own at 23:15Z.

---

**Started (CEO run `a6f09ddb`, 2026-10-16 14:18Z), at the close-out of [DEC-1177](/DEC/issues/DEC-1177).** PR #76 merged as `ec931c4` at 14:16:38Z: screen readers now skip the sigil spans of the /shopping and Compare empty states and the `.gv1-empty::before` glyph. I read the 22 sites listed below on `main` `ec931c4`, and each line number still holds. Your review of PR #73 ([DEC-1189](/DEC/issues/DEC-1189)) is live, so this leg starts after it. PR #72 ([DEC-1167](/DEC/issues/DEC-1167)) and PR #66 ([DEC-1155](/DEC/issues/DEC-1155)) are in the merge queue on [DEC-1178](/DEC/issues/DEC-1178) and change `Shopping.tsx`. Read the line numbers again on your tree.

**Implementer: the Design System Engineer (`8ea33a50`). Tier 1, priority low. Budget: about 1 hour. Port: `GRIMOIRE_E2E_PORT=14907`. Web only. This leg measures and proposes. It changes no file and opens no pull request.**

## The fault
- PR #76 (DEC-1177) hides the sigil of every empty state from screen readers. Many other text glyphs still reach Chromium's tree. Your DEC-1177 note 2 named `Hero.tsx:46`.
- My `git grep` on `main` `1433536` found the sites below (each line number checked again on `ec931c4`): JSX text that holds a glyph from U+2190 to U+2BFF, on a line with no `aria-hidden`. The list is a start, not the census.
  - **A decorative span alone:** `components/organisms/Hero.tsx:46` (◆, the eyebrow), `components/organisms/Scrying.tsx:768` (⚠) and `:787` (✓), `routes/ComboLab.tsx:1499` (⟶).
  - **A glyph inside a text string:** `components/global/GV1CardHoverLayer.tsx:163` ("◆ scrying scryfall ◆") and `:169`, `components/molecules/CardTile.tsx:132` ("hover ◇"), `components/organisms/Performance.tsx:109` ("open →"), `components/organisms/Tokens.tsx:39`, the loading lines `routes/CardAtlas.tsx:10`, `routes/Codex.tsx:10`, `routes/Compare.tsx:10`, `routes/Shopping.tsx:10`, `routes/ComboLab.tsx:606` and `:620`, and the mode tags `routes/ComboLab.tsx:703` and `:712` ("◈ mode i").
  - **A glyph that carries meaning:** the Game Changer star at `components/molecules/CardTile.tsx:124` and `components/organisms/Decklist.tsx:284` (★, with no text alternative), and the legend `components/organisms/Compare.tsx:224` (≥75).
  - Not in this leg: PR #72 (DEC-1167) covers `Shopping.tsx:733` and `:741`, and PR #76 covers the empty states.
  - **From the review of PR #76 ([DEC-1185](/DEC/issues/DEC-1185) N2, verdict `c122f884`):** the loading lines `routes/ComboLab.tsx:606` and `:620` are the `aria-busy` states inside `.gv1-empty gv1-lab-unscribed`. Their "◇" is part of the text node, with no `aria-hidden`, and the `::before` ◇ shows too, so these states show two glyphs. The reviewer read the markup of every other `.gv1-empty` (Apothecary, Combos, Compare, Engine, Shopping, WinCons and the Combo Lab route) at `3a3b8fc` and found no other glyph.

## What to do
1. **Census.** Write a script that lists every text glyph outside letters, digits and common punctuation in `web/src/**/*.tsx` (tests excluded), and every CSS `content:` value under `web/src/styles/`. For each site, give the file and line, the glyph, and what covers it (`aria-hidden`, an alternative text, or nothing). Count the sites.
2. **Chromium's tree.** For each route that shows a site, read CDP `Accessibility.getFullAXTree` on `main` and quote what Chromium reads for each glyph. Read after `document.fonts.ready`.
3. **Classes and a rule.** Sort the sites into four classes: a decorative span alone, a decorative glyph inside a text string, a glyph that carries meaning (★, ✓, ⚠, ≥, →), and a CSS `content:`. Propose one rule for each class: for example `aria-hidden`, a split of the string into a hidden span and the text, a text alternative in `gv1-sr-only`, or CSS alternative text. For each rule, give the count of sites and files it touches and the test that would check it.
4. **Two glyphs in one empty state.** Each empty state on /shopping and on Compare shows two glyphs (the `::before` and the span). Apothecary and Combo Lab show one, except the Combo Lab loading states at `ComboLab.tsx:606` and `:620`, which show two (DEC-1185 N2). Read the design handoff and the git history of those spans, and say which the design intends. Propose a change if one is needed; do not make it. A change to what users see goes to the owner.
5. **Size the fix.** Say whether the fix fits one pull request, and give its budget.

## Rules
- Tree: `cd /Users/dpires/Documents/Personal/code/mtg-precon-upgrader && git fetch origin && git worktree add --detach wt-dec<N> origin/main`, then `npm ci` in its `web/`. `<N>` is this issue's number. Keep scratch under `/tmp/dec<N>/`. At the hand-back, remove the tree with `git worktree remove` (never `--force`) and say so.
- Set `HOME="$PAPERCLIP_GITHUB_HOST_HOME"` for every `git` and `gh` command. Set `PLAYWRIGHT_BROWSERS_PATH="$PAPERCLIP_GITHUB_HOST_HOME/Library/Caches/ms-playwright"` for every Playwright run.
- No request to `api.scryfall.com` or `cards.scryfall.io`. The e2e stub answers every case.
- Run Playwright with 3 workers at most; the Mac is shared.

## Handoff
1. Post the census, the reads and the proposal as one comment. Keep the script and the reads in `$PAPERCLIP_GITHUB_HOST_HOME/.paperclip/instances/default/workspaces/8ea33a50-69a7-4a75-bcc1-245bd1e7c73a/dec<N>/`, and give that path.
2. As the last action of your run, send one PATCH on this issue: `assigneeAgentId` the CEO (`f9427c33-d719-4fd5-a3c5-cd2f65dd01e8`), `status: in_review`, and `executionPolicy.monitor` with `nextCheckAt` 30 minutes ahead, `scheduledBy: "assignee"` and `notes` under 500 characters that name your comment.
3. If the server answers 422 `invalid_issue_disposition`, send the same PATCH again with `nextCheckAt` about ten hours ahead. Never set `done`.
4. **A question in the middle of the leg.** Post the question with its evidence and your recommendation. Then send the PATCH above as the last action of your run. Do not open a child issue assigned to the CEO (409 `delegation_cycle`).

planned-by: CEO (run `cc3c9de1`). Source: DEC-1177 hand-back `4b4051bb`, notes 1 and 2. Parent: DEC-1177.

