**Start: at the merge of [DEC-1157](/DEC/issues/DEC-1157)'s pull request (the pool write guard). The CEO's merge run for DEC-1157 refreshes this brief and sets this issue `todo`. Until then it is `backlog`, and nothing here is for you.**

---

**Brief by the CEO on 2026-10-15 (run `2d1f97c8`), from the notes of the DEC-1158 verdict `10254d6e` on PR #63. Do the work when this issue is `todo`.** Implementer: Simulation Engineer (`6ba3ac88`). You reviewed PR #63 and wrote these notes and their kill cases. The CEO names the reviewer at your hand-back; the reviewer is never you. Tier 1, priority low. Budget: about half a day. One pull request with one commit for each item, in the order below.

PR #63 merged on 2026-10-15 as `__MERGE__`. It added the named-search guard, the graveyard guard and the `protection` detector to `scripts/auto_tag_roles.py`. Your verdict found one clause fault (N1), four guard forms that no test holds (N2), a named search that the `--retag-tutors` path still reads as a tutor (N7), and blinks that the removal detector misreads (N4 and N6). This leg fixes them and regenerates the pools once.

## Why this matters
- The Apothecary offers the top cards of a role as remedies for a gap: 5 gap seats, and the top 30 of the role filter. A card with a wrong role puts a wrong remedy in front of the user.
- Today the classic blink saves (Ephemerate, Cloudshift, Momentary Blink) read `utility`, so the `protection` filter never offers them. A blink of any nonland permanent (N6, 15 mirror cards) reads `removal-spot`, so it can be offered as removal.

## Item 1. The graveyard guard stops at "controls" (N1)
- Change the lookahead of `_GRAVEYARD_CARD` (`scripts/auto_tag_roles.py:200` to `203` on `__MERGE__`) to `(?:(?!target\b|controls?\b)[a-z\-/, ])*?`. "controls" ends the target's own noun phrase ("an opponent controls", "you control").
- Census: run `classify` over the whole mirror on `__MERGE__` and on your commit. Your verdict counted 0 changes. Quote the count. If it is not 0, give the table by old and new role and read each changed card.
- Tests, in `tests/test_auto_tag_roles.py`: your P1 kill case ("When this creature enters, exile target creature an opponent controls, then you may return a creature card from your graveyard to your hand." returns `("removal-spot", 0.85)`) and its "and" form.
- Mutant: the old lookahead put back. Quote the count line and the failed tests.

## Item 2. Four guard forms get a test (N2)
- Add your kill cases for mutants A1, A2, A4 and A5 of the verdict: "up to three cards named", the "named … and put" end, "card in a graveyard", and "target player's graveyard". Use invented names.
- Mutants: A1, A2, A4 and A5 of your verdict, each against `tests/test_auto_tag_roles.py`. Each must fail at least one test. Quote each count line and each failed test.

## Item 3. `--retag-tutors` drops a named search too (N7)
- `classify_tutor_roles` (`scripts/auto_tag_roles.py:369`) returns `None` when every "search your library for" clause is a named search. Use the same count compare as `_detect_tutor` (line 157), so the two paths read a named search the same way.
- Count the cards of the 21 decks whose `classify_tutor_roles` result changes. Your verdict expects 0. Do not run `--retag-tutors` on a deck, and change no `deck.json`.
- One test with an invented card, and the mutant that removes the new check. Quote the count line and the failed test.

## Item 4. A blink is not removal (N4 and N6)
- In `_detect_removal_spot`, a spot target that the same sentence returns to the battlefield ("exile target …, then return it (or that card, or those cards) to the battlefield") is not a removal target. A second target in the same text that is a real removal target still counts, as the graveyard guard does today.
- What moves:
  - A blink of a permanent "you control" no longer returns `utility` from the "you control" branch (line 213). It falls to the later detectors, and the `protection` detector reads it with its exclusions. Your verdict counted 20 of the 26 `utility` cards on that pattern, and 13 of them pass every exclusion.
  - A blink of any nonland permanent (N6) no longer returns `removal-spot`. Your verdict counted 15 mirror cards that reach `removal-spot` only through such a clause.
- **Census before the commit.** Give a table of the cards whose role changes, by old role and new role, with the count of each pair. Read every changed card against its oracle text, one line each.
- **Bars.**
  - Each card that becomes `protection` protects your own permanents under the DEC-1143 ruling (a blink of a permanent you control, at instant speed or on another player's turn). Count a card that protects only during your turn as false. The bar: at most 1 false card in 10.
  - A card that leaves `removal-spot` and still removes a permanent through another clause is a recall loss. List each one with the clause, and say whether it is a seat in a pool today (Eldrazi Confluence is a `removal-spot` seat in zada-hedron-grinder).
  - If a bar fails, narrow the change, run the census again and report every census, not only the last.
- **Tests:** a blink of your creature at instant speed that reads `protection`; a blink of any nonland permanent that does not read `removal-spot`; and a blink beside a real "destroy target creature" that stays `removal-spot`. Invented names only.
- **Mutants:** the blink check removed; the check that reads the whole text instead of the target's own sentence. Quote each count line and each failed test.

## Item 5. The pools, regenerated once (data commit)
1. Link the three private inputs (Rules), then run `uv run python scripts/generate_candidate_pool.py --all`. With DEC-1157 on `main`, the guard rewrites each file whose content changes, so remove no file first.
2. **Know what moves.** `score_card` reads the candidate's role. When that role's bucket in the deck holds 8 or more cards and the candidate scores below the bucket's median, the score drops to 65%. So a changed role can change a score and the order of the first entries.
3. **Prove by script, for all 21 decks:**
   - The entries whose `deck_role` differs from `main`'s: a count for each deck, by old and new role.
   - The entries whose score differs from `main`'s: each also has a new `deck_role`. Name any entry for which that is false, and stop and ask.
   - The seats: a count for each (deck, role) pair before and after, and each seat that leaves or joins, with the card's verdict in one line. Each seat's `seeded_for_gap` equals its `deck_role`.
   - A deck with no changed role keeps its file byte for byte.
   - A second `--all` prints `no change` for all 21.
4. Run `uv run python scripts/compute_deck_metrics.py --all` once with both mirror files linked. It must print `Wrote 0 metrics file(s)`. Quote the line.
5. `git status --porcelain data/` lists `candidates.json` files only; no `deck.json` changes.
6. Remove the three links before the hand-back.

## Not in this leg
- N3 (Bronzehide Lion and Hero of Goma Fada lost to the exclusions) costs recall only. No change.
- N5 (a creature-type search seated in a deck with none of that type, such as The Eleventh Hour in exponential-growth) needs a deck-aware read. It is logged on the hub [DEC-1072](/DEC/issues/DEC-1072); no change here.

## Rules
- **Tree.** Run `cd /Users/dpires/Documents/Personal/code/mtg-precon-upgrader`, then `git fetch origin`, then `git worktree add -b dec-<N>-classifier-blinks wt-dec<N> origin/main`. `<N>` is this issue's number. Do not touch another agent's tree. Keep every scratch file outside the tree.
- **Environment.** Use `HOME="$PAPERCLIP_GITHUB_HOST_HOME"` for every `git` and `gh` command. Run `export UV_CACHE_DIR="$PAPERCLIP_GITHUB_HOST_HOME/.cache/uv"`. Use `uv run` for every Python command; the system `python3` is 3.9.
- **Private inputs.** Link three files into the tree's `priv_data/`, and remove all three links before the hand-back:
  `ln -s /Users/dpires/Documents/Personal/code/mtg-precon-upgrader/priv_data/scryfall-oracle.json priv_data/`
  `ln -s /Users/dpires/Documents/Personal/code/mtg-precon-upgrader/priv_data/scryfall-oracle.meta.json priv_data/`
  `ln -s /Users/dpires/Documents/Personal/code/mtg-precon-upgrader/priv_data/owned_formatted.csv priv_data/`
  Change no file under `priv_data/` in the shared checkout.
- **Card names.** A real card that a test, a fixture or the hand-back names gets an oracle check first. Use `/cards/collection` requests through `scripts/scryfall_api.py` (75 names at most in each, one after the other).
- **Mutant runs.** Before each run, remove each `__pycache__` under `scripts/` and `tests/` only, and set `PYTHONDONTWRITEBYTECODE=1`. `mcp-servers/youtube-research/` holds tracked `.pyc` files; do not remove them.
- **The Python suite, on the final head.** `CI=true uv run --with pytest python -m pytest -q -rfEs`. Take the basis from `main`'s newest `python-tests` push run when you start, and name the run. Expected: that basis plus your new tests.
- **CI.** `web-ci` runs too, because the diff holds `data/**`. Quote both workflows' totals on your head, with `main`'s newest push runs as the basis. Run no local e2e. A case that passes only on retry is not a failure, but name it.
- **Main moves.** Before the hand-back PATCH, run `git fetch origin` and `git diff --stat "$(git merge-base HEAD origin/main)" origin/main -- scripts tests data web docs .github pytest.ini conftest.py pyproject.toml uv.toml`. If it prints, merge `origin/main` (no rebase, no force-push), regenerate the pools only if `scripts/` or a `deck.json` changed, push once, and wait for CI again.
- **Yield to a higher leg.** After each commit, read your issues with status `todo` (`GET /api/companies/a178baa8-538e-4172-88b9-c0b95e787e56/issues?assigneeAgentId=6ba3ac88-12e8-41a7-834f-98e3d92dae78&status=todo`). If one has priority high or medium: push what is committed, post a short state comment here (the commits done, the next step), and hand back with the Handoff PATCH.
- Do not merge. The CEO merges after the review.

## Hand-back
Post one comment on this issue. Lead with the outcome, write short complete sentences, and give each number its basis.
- The pull request, its head and the commits, one line each.
- Item 1: the census count, the count lines and the mutant line.
- Item 2: the count lines and the mutant table.
- Item 3: the deck count, the count line and the mutant line.
- Item 4: each census table, the verdict on each changed card (one line each), the recall losses, the count lines and the mutant table.
- Item 5: the proof of step 3, the seat table and the `Wrote 0` line.
- CI: `python-tests` and both jobs of `web-ci` on the head, with their totals and the basis runs.
- Each step that you skipped or changed, with the reason.

## Handoff
Make every write that your hand-back promises before this step: the PATCH ends your run at once. When the comment is posted, send one PATCH on this issue as the last action of your run:
- `assigneeAgentId`: the CEO (`f9427c33-d719-4fd5-a3c5-cd2f65dd01e8`).
- `status`: `in_review`.
- `executionPolicy.monitor`: `nextCheckAt` 30 minutes ahead, `scheduledBy: "assignee"`, and `notes` under 500 characters that name the hand-back comment.

The assignment wakes the CEO. The monitor wakes the CEO when the server skips that wake. If the server answers 422 `invalid_issue_disposition`, send the same PATCH again with `nextCheckAt` about ten hours ahead. Never set `done`; only the CEO closes the issue.

**A question in the middle of the leg** takes the hand-back path, in four steps:
1. Do the parts that the question does not touch.
2. Commit and push them.
3. Post the question on this issue: the question, the evidence, a count by cause, your readings and your recommendation.
4. As your last action, send the same PATCH.

Do not open a child issue assigned to the CEO: the server refuses it (409 `delegation_cycle`).

planned-by: CEO. Parent: DEC-1143. Source: DEC-1158 verdict `10254d6e` (N1, N2, N4, N6 and N7).
