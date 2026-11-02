**Implementer: the Simulation Engineer (`6ba3ac88`). Tier 1, priority high. Budget: about 2 hours. Hand back by Tuesday 3 November 18:00Z: the Star Trek sheet is due on Thursday 5 November, and the event is on Friday 6 November. One pull request; do not merge it.** `<N>` is this issue's number.

## Why
- On DEC-1218 (2 November, 09:42Z) the board asked for a link to Scryfall on every card in the cheat sheet, and for a PDF of the sheet.
- The Star Trek sheet (`agents/ceo/analysis/prerelease/trk/cheat_sheet.md`, `main` `fecff218`) names cards in every section: the intro and the procedure (from `prose.json`), the format rules (copied from `format_rules.md`), the removal list (section 3), the tricks (section 4), the archetypes (section 5) and the full list (section 6). That is about 470 name mentions, none of them a link today.
- The PDF builder is `agents/ceo/analysis/dec925/build_pdf.py`. It reads and writes beside itself, so it cannot build another set's PDF without a copy.
- Each card in the dump (`DIR/<code>_all_cards.json`) holds its Scryfall page in `scryfall_uri`, for example `https://scryfall.com/card/trk/1/70000-light-years-from-home?utm_source=api`.

## What to do
1. **Tree.** Run `cd /Users/dpires/Documents/Personal/code/mtg-precon-upgrader && HOME="$PAPERCLIP_GITHUB_HOST_HOME" git fetch origin && HOME="$PAPERCLIP_GITHUB_HOST_HOME" git worktree add -b dec-<N>-scryfall-links wt-dec<N> origin/main`. Work only in `wt-dec<N>`. Keep scratch under `/tmp/dec<N>/`.
2. **Links: one pass after the build.** Add `link_cards(text, cards)` to `scripts/prerelease/build_cheat_sheet.py`. `main()` applies it to the text that `build()` returns, before it writes the file. `build()` does not change.
   - The URL is the card's `scryfall_uri` with the query string removed. Take it from the card dump; hard-code no URL.
   - On every line except headings (lines that start with `#`), replace each exact, case-sensitive occurrence of a card name from the dump with `[name](url)`. A match must not touch a letter or a digit on either side.
   - Match longer names first, and never link text that is already inside a link. Star Trek's test case: "Eject the Warp Core" gets one link to its own page, and the card "Warp Core" inside it gets no second link.
   - For a two-faced card (its `name` holds ` // `), link the full name and also the front face's name alone: the signposts print the front face.
   - Text that is not a full card name stays plain, for example "Hemmer" for "Hemmer, Fixing What Is Broken".
   - Add `--no-scryfall-links`: with it, `main()` writes the sheet exactly as today.
   - The DEC-925 regression tests call `build()` and must pass unchanged. Do not edit them or their files.
3. **PDF builder into the toolkit.** Move `agents/ceo/analysis/dec925/build_pdf.py` to `scripts/prerelease/build_pdf.py` with `git mv`.
   - Add `--set-dir DIR` (required). Read `DIR/cheat_sheet.md`, write `DIR/cheat_sheet.pdf`, and remove the temporary HTML file, as today.
   - Keep the CSS. Add one rule so that links show on a phone without underlining every row: `a { color: #1a4fa0; text-decoration: none; }`.
   - Keep python-markdown through `uv run --with markdown`. Add no project dependency. Update the docstring's command line.
   - If Chrome is not at its path, exit non-zero with a message that names the path.
4. **Tests** (`tests/test_prerelease_tools.py`). Read the Star Trek folder `agents/ceo/analysis/prerelease/trk/` in place (do not copy it), as the DEC-1220 test does.
   - Remove every link from the linked sheet (`[X](url)` becomes `X`): the result is byte for byte the text that `build()` returns.
   - Every card in `grades.json` has at least one link. Every link's URL is the `scryfall_uri`, without its query, of the card that the link text names.
   - "Eject the Warp Core" has exactly one link, to its own page, and no link sits inside another.
   - No heading line holds a link.
   - Add no test that imports `build_pdf.py`. CI has no `markdown` package, and a skip would change the suite's count.
5. **Documents.**
   - `scripts/prerelease/README.md`: describe the links and `--no-scryfall-links` under `build_cheat_sheet.py`. Add a run-order step and a "What each command does" entry for `build_pdf.py`. The worked-example line keeps `dec925/`.
   - `docs/prerelease-playbook.md`: in the step that builds the cheat sheet, add the PDF command. Change no other line.
6. **Build on your head, in a scratch copy.** Copy `agents/ceo/analysis/prerelease/trk/` to `/tmp/dec<N>/trk/`. Build the sheet with links and then the PDF there. Do not commit rebuilt Star Trek files; I rebuild them on `main` after the merge.
   - Count the links in the sheet, and the distinct cards they name.
   - Count the link annotations in the PDF with `uv run --with pypdf python ...`: each page's `/Annots` entries that hold a `/URI`. The PDF count may be higher than the sheet's when a link breaks over two lines. It must not be lower.
7. **Run** `uv run --with pytest python -m pytest tests/test_prerelease_tools.py -q`, then the whole suite with `uv run --with pytest python -m pytest -q`. Quote both count lines.
8. **Pull request.** Commit with the message `feat(prerelease): a Scryfall link on every card name; PDF builder in the toolkit (DEC-1218)`. Push the branch and open the pull request against `main`. Wait for `python-tests` on the head and quote its result.

## Rules
- Set `HOME="$PAPERCLIP_GITHUB_HOST_HOME"` for every `git` and `gh` command.
- Change only `scripts/prerelease/build_cheat_sheet.py`, `scripts/prerelease/build_pdf.py` (moved from `agents/ceo/analysis/dec925/build_pdf.py`), `scripts/prerelease/README.md`, `tests/test_prerelease_tools.py` and the one step of `docs/prerelease-playbook.md`. Touch nothing else under `agents/ceo/analysis/**`, and nothing under `data/**` or `web/**`.
- The board is deciding whether the prerelease folders move out of `agents/ceo/analysis/`. Move no other file in this leg. Keep every set path a `--set-dir` argument, so that a later move changes only paths.
- Send no request to Scryfall or any other network service. Both builders work from the files in the repository.
- No new project dependencies.
- Keep `wt-dec<N>` until the merge; I remove it at the merge. Remove any scratch tree that you add with `git worktree remove` (never `--force`), and name it in your hand-back.

## Handoff
1. Post one comment: the pull request number and head, `git diff --stat -M origin/main...HEAD`, the two pytest count lines, the `python-tests` result, the counts of step 6, and the first five lines of the Star Trek removal list as built with links.
2. As the last action of your run, send one PATCH on this issue: `assigneeAgentId` the CEO (`f9427c33-d719-4fd5-a3c5-cd2f65dd01e8`), `status: in_review`, and `executionPolicy.monitor` with `nextCheckAt` 30 minutes ahead, `scheduledBy: "assignee"` and `notes` under 500 characters that name your comment.
3. If the server answers 422 `invalid_issue_disposition`, send the same PATCH again with `nextCheckAt` about ten hours ahead. Never set `done`.
4. **A question in the middle of the leg.** Finish the parts that the question does not touch, commit and push them. Post the question with its evidence and your recommendation. Then send the PATCH of step 2 as the last action of your run. Do not open a child issue assigned to the CEO (the server refuses it with 409 `delegation_cycle`).

## CEO: checks at the hand-back
Review: a CEO checklist pass, as on DEC-1220. I am the only user of this output.
1. `git diff --stat -M origin/main...origin/dec-<N>-scryfall-links` lists the Rules' files only and shows `build_pdf.py` as a rename.
2. `python-tests` is green on the head, and the DEC-925 regression tests are unchanged in the diff.
3. On the head, I build the Star Trek sheet from `agents/ceo/analysis/prerelease/trk/` twice. With `--no-scryfall-links` it is byte-identical to the build on `main`. With links, five links picked at random each point to the card they name.
4. I build the PDF and click five of its links.
5. Merge pinned: `gh pr merge <PR> -R DioPires/mtg-precon-upgrader --merge --match-head-commit <head>`.
6. Delete the remote branch (`gh api -X DELETE repos/DioPires/mtg-precon-upgrader/git/refs/heads/dec-<N>-scryfall-links`; `delete_branch_on_merge` is off on this repository). Then sweep `wt-dec<N>`: `git status --porcelain` prints nothing, `git merge-base --is-ancestor HEAD origin/main` exits 0, `git worktree remove wt-dec<N>`, `git branch -D dec-<N>-scryfall-links`, `git worktree prune`.
7. On `main`, rebuild the Star Trek sheet and its PDF, and commit both.
8. Close with the audit line `planned-by: CEO / executed-by: Simulation Engineer / reviewed-by: CEO (checklist)`.

planned-by: CEO (run `d5d55166`). Source: the board's comment of 2 November 09:42Z on DEC-1218, and the Star Trek sheet on `main` `fecff218`. Parent: DEC-1218.
