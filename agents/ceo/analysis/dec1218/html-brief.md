**Implementer: the Frontend Engineer (`bc5c0753`). Tier 1, priority high. Budget: about 5 hours. Hand back by Tuesday 3 November 12:00Z: the Star Trek sheet is due on Thursday 5 November, and the event is on Friday 6 November. One pull request; do not merge it.** `<N>` is this issue's number.

## Why
- On DEC-1218 (2 November, 10:22Z) the board asked for an HTML page of the cheat sheet that is easier to navigate and read: "lets try and see what we can come up with".
- The sheet is `analysis/prerelease/trk/cheat_sheet.md` (`main` `4f5ecdfe`), built by `scripts/prerelease/build_cheat_sheet.py`. It has an intro and six sections. Section 6, the full graded list, is 21 tables of 306 cards in six columns. The PDF (`scripts/prerelease/build_pdf.py`) is 12 A4 pages. On a phone, neither the tables nor the A4 pages fit the screen.
- The board reads the sheet on a phone at the store, for three jobs:
  1. **Deck building** (about 30 to 45 minutes): find each of the about 85 cards of the pool in the graded list, and follow the hand procedure of section 1.
  2. **During games:** look up a format rule (section 2), what a removal spell kills (section 3), or the tricks that the opponent's open mana allows (section 4).
  3. **Between rounds:** read the ten archetypes (section 5).
- You do the web app's UI work, so this leg is yours. The page is not part of the web app: it is one file that the toolkit writes beside the sheet. The web app's token rule (`var(--gv1-*)`) does not apply to it; you may copy values from the tokens.

## What to build

### Part A: the page (do this first)
1. **Tree.** Run `cd /Users/dpires/Documents/Personal/code/mtg-precon-upgrader && HOME="$PAPERCLIP_GITHUB_HOST_HOME" git fetch origin && HOME="$PAPERCLIP_GITHUB_HOST_HOME" git worktree add -b dec-<N>-html-sheet wt-dec<N> origin/main`. Work only in `wt-dec<N>`. Keep scratch under `/tmp/dec<N>/`.
2. **Builder.** Add `scripts/prerelease/build_html.py --set-dir DIR`. It writes `DIR/cheat_sheet.html`.
   - One self-contained file: inline CSS and JavaScript. It loads no font, script, style or image from the network, and it works when opened from disk (`file://`). The only network addresses in it are the Scryfall card links.
   - Intro and sections 1 to 5: convert them from `DIR/cheat_sheet.md` with python-markdown, as `build_pdf.py` does (`uv run --with markdown`). Import `markdown` inside the function that uses it, so that the tests can import the module without the package. CI has no `markdown` package.
   - Section 6: build it from `DIR/grades.json` and the card dump, with the same cards, groups, order, grades, costs, rarities, tags, notes and links as the sheet's section 6. Reuse the code of `build_cheat_sheet.py` (`mark`, `pip`, `card_urls`, the grouping and the sort) rather than copy it. A small refactor there is fine if the sheet that it writes does not change by one byte.
   - The build is deterministic: no timestamp and no random order. Two builds give the same bytes.
   - It works for any set folder with `cheat_sheet.md` and `grades.json`. Reality Fracture (`analysis/prerelease/fra/`) has other sections (a simulated ranking) and no links. Its build must not fail, but do not commit its page.
3. **Layout: a phone first.**
   - At 360 px wide, no part of the page scrolls sideways, except a wide table inside its own box (section 3's table).
   - Body text is at least 16 px. Light and dark themes follow `prefers-color-scheme`. Text contrast meets WCAG AA in both.
   - Mana costs show as small coloured symbols drawn with CSS, not images. Each symbol keeps its source text (`{2}`, `{W}`, `{X}`, a hybrid `{W/U}`) in an attribute and has an accessible name.
4. **Navigation.**
   - A bar that stays on screen holds one link per section, with short labels (for example: Build, Rules, Removal, Tricks, Archetypes, Cards). You choose top or bottom; say why in the hand-back.
   - The links work without JavaScript (anchor links). With JavaScript, the bar marks the section on screen. A heading never hides under the bar.
   - The card search (point 5) is one tap away from any section.
5. **Section 6: the card list.**
   - Each card is one block, not a table row. Line 1: the grade as a badge (one colour per band: 8+, 6 to 7.5, 4 to 5.5, under 4), the name as its Scryfall link, the mana cost, the rarity and the tags. Line 2: the note.
   - A legend of the tag symbols sits at the top of the section: ★ bomb, ✕ removal, ⚡ instant speed, ◆ fixing, ✚ card advantage.
   - **Search.** A text field filters the list as you type. Normalise the name and the query the same way: lower case, accents removed, apostrophes and full stops removed, other punctuation turned into spaces. A card matches when each word of the query appears in its name. These must work: `obrien` finds Miles O'Brien, Transporter Ops; `uss ent` finds U.S.S. Enterprise-A, Free Spirit; `spock` finds each card with Spock in its name; `khaan` finds Khaaaaaaaaaaaannn!.
   - **Filters.** Toggle chips for colour (W, U, B, R, G, gold, colourless), rarity (C, U, R, M) and tag (★ ✕ ⚡ ◆ ✚), and a minimum grade (4+, 6+). A hybrid card shows under each of its colours. Chips of one kind combine with OR, kinds combine with AND, and the search combines with the chips with AND.
   - The list keeps the sheet's groups and order. A group with no card shown hides. The section shows how many cards it shows, for example "12 of 306".
   - Without JavaScript, the full list shows, grouped as in the sheet, and the search field and the chips do not show.
6. **Sections 1 to 5.** Keep every word and every link of the sheet. Make them easier to read:
   - Section 5: one block per archetype. The ten names and plan sentences fit on few screens; the signposts and the "Look for" list open on a tap (`<details>` works without JavaScript).
   - Section 4: the tricks by colour, with their mana costs as symbols.
   - Card links open in a new tab, so that the page keeps its place and its search.

### Part B: the pool counter (after Part A passes its checks)
The hand procedure (section 1) takes about 10 minutes with pen and paper. Part B does steps 2, 3, 4 and 7 from the cards that the board counts. The board will type a few letters of each card and tap `+` on it, about 85 times: make that loop fast (for example, a clear button on the search field, and the field stays in reach after a tap).
1. Each card block gets a counter: `−`, the number of copies, `+`. The counts persist in the browser (`localStorage`, one key per set code). A "Clear pool" button asks before it clears. A chip "In my pool" shows only the counted cards.
2. A "Pool" view, with its own entry in the bar, shows:
   - The number of cards counted.
   - **Step 2**, for each colour W, U, B, R and G: the cards graded 6+, the cards graded 4+, and the ★ cards. A hybrid card counts for each of its colours. Gold cards, three-colour cards, colourless cards and lands do not count here.
   - **Step 3**: the ten pairs, ranked by score. The score is the number of the pair's cards graded 6+, with a ★ counted twice. A pair's cards here are the mono-coloured cards of its two colours and the hybrid cards with at least one of its colours, each card counted once.
   - **Step 4**, for the top three pairs: the cards graded 4+ and the creatures among them, beside the targets 22 to 23 and 15+. The cards here are step 3's cards, plus the pair's gold cards (exactly the pair's two colours), plus the colourless non-land cards. A card is a creature when its front face's type line holds "Creature"; a Spacecraft is not a creature. Section 1, step 4, of the sheet says the same since `4f5ecdfe`.
   - **Step 7**: a tie in the step 3 score breaks by more ★, then more ✚, then more ✕, then more two-drops (mana value 2), each counted over the step 4 cards graded 4+. A tie after that keeps the order WU, WB, WR, WG, UB, UR, UG, BR, BG, RG (`PAIRS` in `build_cheat_sheet.py`).
   - One line that says that the splash (step 5) and the build (step 6) stay by hand.
   - A grade of 5.5 is not 6+: compare with `>=`. Two copies of a card count twice.
3. **One rule, two implementations.** Write the counts once in Python, as `pool_summary(pool, grades)` in `build_html.py`, and once in the page's JavaScript. The Python function is the reference for the tests, and the browser check (Checks, point 3) shows that the page gives the same numbers.
4. Without JavaScript, the counters and the Pool view do not show.

## Tests (`tests/test_prerelease_tools.py`)
CI runs `uv run --with pytest python -m pytest` with no `markdown` package. Every new test must pass there. Add no skip: a skip changes the suite's count.
- `pool_summary` on a small hand-made pool from the Star Trek grades, with the expected numbers written by hand in the test. The pool holds a hybrid card, a gold card, a ★, a Spacecraft, a colourless creature, a land, a three-colour card, a card graded 5.5 and two copies of one card.
- The search normalisation: the four examples of Part A, point 5. If the normalisation lives only in JavaScript, keep its examples in one list that both the test and the browser check read.
- The committed Star Trek page (`analysis/prerelease/trk/cheat_sheet.html`), read with the standard library's `html.parser`:
  - Each card of `grades.json` has exactly one block, and its name, grade, cost, rarity, tags, note and link equal the sheet's section 6 row.
  - The links of the intro and sections 1 to 5 of `cheat_sheet.md`, in order, equal the links of the same part of the page (text and address).
  - The page holds no `src` or `href` to any address other than `https://scryfall.com/card/` pages and anchors in the page.
- These tests fail when someone changes the sheet and does not rebuild the page. That is wanted.

## Checks before the hand-back
1. Run `uv run --with pytest python -m pytest tests/test_prerelease_tools.py -q`, then the whole suite with `uv run --with pytest python -m pytest -q`. Quote both count lines. On `main` the whole suite reads 772 passed and 1 skipped; your new tests raise only the passed count.
2. Build the Star Trek page twice and compare the bytes (`cmp`). Copy `analysis/prerelease/fra/` to `/tmp/dec<N>/fra/`, build its page there and quote its size.
3. **Text check.** Compare the text of the intro and sections 1 to 5 of the page with the text of python-markdown's render of the same part of the sheet: tags removed, white space joined, each mana symbol turned back into its source text. The two must be equal. Quote the result.
4. **Browser check.** Write it as a script that you commit, `scripts/prerelease/check_html.mjs`. It drives the page with Playwright from `web/node_modules` (no new dependency), opened from disk. It prints a summary:
   - no sideways scroll (`document.documentElement.scrollWidth <= innerWidth`) at 360 and 390 px wide, in light and in dark;
   - each search of Part A, point 5, with the cards it shows;
   - one chip of each kind turned on, with the count it shows;
   - with JavaScript off (`javaScriptEnabled: false`): all six sections and 306 card blocks;
   - Part B: `+` tapped on five cards, then the Pool view read. Then three more pools loaded through `localStorage`, one of them 85 cards drawn from the graded cards with a fixed seed. For each pool, every number of the Pool view equals `pool_summary`'s number for the same pool. Print "pool check: N numbers, 0 differ", or the differences.
5. **Screenshots** at 390 × 844, light and dark, into `/tmp/dec<N>/shots/`: the top of the page, section 1, section 3, section 5 with one archetype open, section 6 with the search `spock`, and the Pool view with the 85-card pool.
6. Quote the page's size in bytes. Keep it under 500 KB.

## Documents
- `scripts/prerelease/README.md`: a run-order step and a "What each command does" entry for `build_html.py`, and the browser check's command line.
- `docs/prerelease-playbook.md`: in the step that builds the sheet and the PDF, add the page's command and one line that says to rebuild the page each time the sheet changes (the tests check that the two agree). Change no other line.

## Pull request
- Build the Star Trek page from `analysis/prerelease/trk/` on your head, and commit `analysis/prerelease/trk/cheat_sheet.html` in the pull request: the tests read it. If `main` changes the Star Trek files during your leg, merge `origin/main` and rebuild the page before the hand-back.
- Commit with a conventional message, for example `feat(prerelease): an HTML page of the cheat sheet for a phone (DEC-1218)`. Push the branch and open the pull request against `main`. Wait for `python-tests` on the head and quote its result.

## Rules
- Set `HOME="$PAPERCLIP_GITHUB_HOST_HOME"` for every `git` and `gh` command, and `PLAYWRIGHT_BROWSERS_PATH="$PAPERCLIP_GITHUB_HOST_HOME/Library/Caches/ms-playwright"` for each Playwright run.
- Change only these files: `scripts/prerelease/build_html.py` (new), `scripts/prerelease/check_html.mjs` (new), `scripts/prerelease/build_cheat_sheet.py` (only a refactor that keeps the sheet byte for byte), `scripts/prerelease/README.md`, `tests/test_prerelease_tools.py`, the one step of `docs/prerelease-playbook.md`, and `analysis/prerelease/trk/cheat_sheet.html` (new, built). Touch nothing under `web/**`, `data/**` or `agents/**`, and no other file under `analysis/**`. A change under `web/**` or `data/**` deploys the public site when it merges.
- Do not change the sheet's words, grades or tags. If a text of the sheet reads badly on the page, say so in the hand-back: the sheet's text is mine.
- Send no request to Scryfall or to any other network service, from the builder, the check or the page.
- No new project dependency. python-markdown runs only through `uv run --with markdown`, as for the PDF.
- Design choices beyond this brief (colours, type, spacing, the bar's place) are yours. Keep the page plain and easy to read: it is a reference page.
- Keep `wt-dec<N>` until the merge; I remove it at the merge. Remove any scratch tree that you add with `git worktree remove` (never `--force`), and name it in your hand-back.

## Handoff
1. Post one comment: the pull request number and head; `git diff --stat -M origin/main...HEAD`; the two pytest count lines; the `python-tests` result; the page's size and the `cmp` result; the text check's result; the browser check's summary; the screenshot paths; where you put the bar and why; and any text of the sheet that reads badly on the page.
2. As the last action of your run, send one PATCH on this issue: `assigneeAgentId` the CEO (`f9427c33-d719-4fd5-a3c5-cd2f65dd01e8`), `status: in_review`, and `executionPolicy.monitor` with `nextCheckAt` 30 minutes ahead, `scheduledBy: "assignee"` and `notes` under 500 characters that name your comment.
3. If the server answers 422 `invalid_issue_disposition`, send the same PATCH again with `nextCheckAt` about ten hours ahead. Never set `done`.
4. **A question in the middle of the leg.** Finish the parts that the question does not touch, commit and push them. Post the question with its evidence and your recommendation. Then send the PATCH of step 2 as the last action of your run. Do not open a child issue assigned to the CEO (the server refuses it with 409 `delegation_cycle`).
5. If Part A is done and Part B cannot be done by Tuesday 12:00Z, hand back Part A on time and say what Part B still needs.

## CEO: checks at the hand-back
Review: a CEO checklist pass, as on DEC-1221, plus the screenshots. The board sees the page after the merge.
1. `git diff --stat -M origin/main...origin/dec-<N>-html-sheet` lists the Rules' files only.
2. `python-tests` is green on the head. On the head, `build_cheat_sheet.py` writes the Star Trek and the Reality Fracture sheets byte for byte as on `main`.
3. I build the Star Trek page on the head twice and compare both builds with the committed file (`cmp`).
4. I run `check_html.mjs` myself and read its summary.
5. I read the screenshots, light and dark.
6. I count one pool of 10 cards by hand with the sheet's procedure and compare it with the Pool view.
7. Merge pinned: `gh pr merge <PR> -R DioPires/mtg-precon-upgrader --merge --match-head-commit <head>`. If `main`'s Star Trek files changed after the head's build, I first merge `main` into the branch, rebuild the page, push and wait for `python-tests`.
8. Delete the remote branch (`gh api -X DELETE repos/DioPires/mtg-precon-upgrader/git/refs/heads/dec-<N>-html-sheet`; `delete_branch_on_merge` is off on this repository). Then sweep `wt-dec<N>`: `git status --porcelain` prints nothing, `git merge-base --is-ancestor HEAD origin/main` exits 0, `git worktree remove wt-dec<N>`, `git branch -D dec-<N>-html-sheet`, `git worktree prune`.
9. Tell the board on DEC-1218 how to open the page, as their answer to the delivery card on DEC-1218 says. A copy to the public site is a separate step, only if the board chose it.
10. Close with the audit line `planned-by: CEO / executed-by: Frontend Engineer / reviewed-by: CEO (checklist)`.

planned-by: CEO (run `20515f00`). Source: the board's comment of 2 November 10:22Z on DEC-1218 (`eb97abc0`), and the Star Trek sheet on `main` `4f5ecdfe`. Parent: DEC-1218.
