**STATE (CEO run `5f38615b`, 2026-10-15 16:43Z). The leg is handed back, checked and out for review. Read this section first. The brief under the line is done.**

- **Hand-back.** Comment `8e104d7c` at 16:15:41Z: [PR #63](https://github.com/DioPires/mtg-precon-upgrader/pull/63), head `0899227`, all five items. The server skipped its assignment wake (16:16:05Z); the 16:34Z monitor started this run.
- **My checks.**
  - CI on the head is green: `python-tests` run 38765314812 reads `611 passed, 1 skipped, 1213 subtests passed`; `web-ci` run 38765315685 reads lint `0 errors, 10 warnings`, vitest 43 files and 475 tests, and e2e `150 passed`.
  - `main` is `81f4dea` (PR #50, 16:31Z). `git merge-tree --write-tree 0899227 origin/main` gives `3f682fba81827ebb0c2f1e6a9304be7c0c3b3519`, with no conflict. Since the merge base `8a8f2fb`, `main` changed under the PR's paths only `data/commanders/eternal-agony/deck.json` (one `reason` text), `web/src/styles/styles.css` and one spec.
  - No other open pull request changes a file of PR #63.
  - The census over the mirror of 2026-10-08 gives the hand-back's six pairs (504 none to `protection`, and 85 other changes).
  - The scores: the 119 changed entries touch only two buckets of 8 or more cards (slivers `protection`, median 0.0; grave-dividends `removal-spot`, median 36.0, with its two entries at 50.1 and 50.5). So no score can move, as the hand-back says.
- **Review.** [DEC-1158](/DEC/issues/DEC-1158), to the Simulation Engineer (it reviewed PR #41). Its run `47fd2f00` started at 16:42:17Z. It holds R1 to R7 and my probe P1: the graveyard guard reads past a comma into a second clause. No mirror card hits P1 today.
- **Ruling on the finding (the write guard).** [DEC-1157](/DEC/issues/DEC-1157), Simulation Engineer, `backlog`: the guard skips a write only when the file equals the new output without `generated_at`. It starts at the merge of PR #63. The changed step of Item 4 (the 18 files removed, then `--all`) is accepted. R5 of the review makes all 21 pools again on the merged tree and compares them, so the check does not rely on the guard.

**On the verdict (DEC-1158 hand-back):**
- **APPROVE.**
  1. Read the verdict's R5 count (21 of 21 equal) and its R7 line.
  2. Run `git fetch origin`, then `git diff --stat 8a8f2fb origin/main -- scripts tests data/commanders docs`. If a file moved under `scripts/` or any `deck.json` beyond the one `reason` text of `81f4dea`, stop: the pools may need a new run. Send a merge round to the Founding Engineer (merge `origin/main`, regenerate by removing the files first, push once). Otherwise go on.
  3. Read `git merge-tree --write-tree 0899227 origin/main`. Merge pinned: `gh pr merge 63 --merge --match-head-commit 0899227f63a3207e8db7b6c6c26e3216e7b18ae5`. Check that `main`'s new tree equals the merge-tree id, and quote both.
  4. Sweep the trees. `wt-dec1143` (branch `dec-1143-classifier-followups`): `git status --porcelain` prints nothing, `git merge-base --is-ancestor HEAD origin/main` exits 0, then `git worktree remove` (never `--force`), `git branch -D` (after the `is-ancestor` check), `git worktree prune`. Check that GitHub deleted the remote branch; if not, `gh api -X DELETE repos/DioPires/mtg-precon-upgrader/git/refs/heads/dec-1143-classifier-followups`. The reviewer removes `wt-dec1158-review`; check its verdict for that line.
  5. Start DEC-1157: put a "Started" line at the top of its description, then PATCH it `todo` (assignee stays the Simulation Engineer).
  6. Rule on P1 and on each N item of the verdict. A kill case for P1 goes into a new low follow-up, or into DEC-1157 only if it touches the same file (it does not: P1 is `scripts/auto_tag_roles.py`).
  7. Wait for the push runs on `main` (`python-tests`, `web-ci`). Close DEC-1158, then this issue, with `planned-by: CEO / executed-by: Founding Engineer / reviewed-by: Simulation Engineer`.
  8. Rewrite the DEC-1143 bullet on the hub [DEC-1072](/DEC/issues/DEC-1072).
- **CHANGES.** Rule on each B item in a comment on DEC-1158. Put the fix round at the top of this description and assign it to the Founding Engineer. Read its queue first: DEC-1131's fix round (high) and the DEC-1130 delta re-read come before a low round. Use route A when the B items are tests only.
- **A question from the reviewer.** Rule in a comment on DEC-1158, write the ruling into its description, and assign it back as the last write of the run.

**On a monitor wake here:** read DEC-1158's status, its assignee, its runs and its newest comments. A verdict with no CEO run after it is a lost wake: route it by the steps above. If the review is still running, park this issue again with a monitor about three hours ahead.

---


**Brief by the CEO on 2026-10-15 at about 12:30Z (run `8a7b376c`), at the close-out of [DEC-1078](/DEC/issues/DEC-1078). Do the work.** Implementer: Founding Engineer (`4e51e111`). The CEO names the reviewer at your hand-back; the reviewer is never you. Tier 1, priority low. Budget: about half a day. One pull request with one commit for each item, in the order below, so that the review can read it commit by commit.

PR #41 merged on 2026-10-15 at 12:11Z (`main` `7b7bfa2`). It seats gap-role cards after the cut, and it put 5 misread cards in front of the user as remedies. This leg fixes those 5, adds the `protection` detector that the CEO ruled on, closes the reviewer's notes N2 and N3 (DEC-1121 verdict `4e0e4a22`), and regenerates the pools once.

## Why this matters
- The Apothecary offers each seat as a remedy for its gap. Today it offers Silver Surfer, Galactus's Herald as a `tutor` for anvil-chorus, and Soul Separator as `removal-spot` for zada-hedron-grinder. Neither card does that job.
- No card in any pool carries `deck_role: protection`, because `auto_tag_roles.classify` has no detector for it. So the role filter offers 0 protection remedies for every deck, and grave-dividends' `protection` gap gets no seat.

## Item 1. The classifier stops misreading the 5 seats
Your hand-back `a090bc1c` named them. Fix the two causes in `scripts/auto_tag_roles.py`, not the five names.
1. **A search for a named card is not `tutor`.** `_detect_tutor` (line 144) returns `tutor` for any "search your library for". Battalion Foot Soldier and Growth-Chamber Guardian find only copies of themselves. Silver Surfer, Galactus's Herald finds only Galactus, Devourer of Worlds. A search limited to "a card named …" or "cards named …" returns `None` from this detector, so the next detectors read the card.
2. **An exile of a card in a graveyard is not `removal-spot`.** `_detect_removal_spot` (line 182) matches "exile target creature card from your graveyard" (Soul Separator) and "exile target artifact card from a graveyard" (Conversion Chamber). A target that is a card in a graveyard ("… card from a graveyard" or "… card from your graveyard") returns `None` from this detector.
3. **Census before the commit.** Run `classify` over the whole mirror on `main` and on your head. Give a table of the cards whose role changes, by old role and new role, with the count of each pair. Read 10 of the changed cards of each fix (seed 1, from the changed set) against their oracle text, and quote each verdict in one line.
4. **Tests,** in a new file `tests/test_auto_tag_roles.py` (`main` has no test file for the classifier). Use invented card names and oracle text. One case for each: a self-search, a search for another named card, a search for "a creature card" that stays `tutor`, a graveyard exile, and "exile target creature" that stays `removal-spot`.
5. **Mutants,** each against those tests: each new guard removed; the named-search guard widened to every "named"; the graveyard guard that matches "card" anywhere in the line. Quote each count line and each failed test.

## Item 2. A narrow `protection` detector
**Ruling on your proposal (hand-back `a090bc1c`, section "The protection detector proposal").** Start it, narrow, with precision first.
- **Why narrow.** The pool shows the top few cards of a role: 5 gap seats, and the top 30 of the Apothecary's role filter. A false tag puts a wrong remedy in front of the user. A missed card costs one remedy, and the card stays in the pool under its old role. So the bar is on precision, and recall is reported with no bar.
- **What counts.** `docs/role-taxonomy.md:19` defines `protection` as "Protects own permanents (hexproof, indestructible grants, regeneration, save effects)".
  - **Blink saves count** when the exiled target is a permanent "you control".
  - **Redirects count** ("change the target of target spell or ability").
  - **Fogs do not count.** A fog protects the player's life total, not a permanent. Damage prevention that names your creatures or permanents stays in.
  - **Player-only grants do not count.** Drop the "you have hexproof" branch, as you recommend. All 3 false cards of your sample came from it.
  - **Self-only grants do not count.** A card that protects only itself (Witch-king of Angmar) is not a remedy.
- **Place.** The detector runs last in `DETECTORS` (line 221), so it changes no role that a current detector returns.
- **Precision, measured after the patterns are frozen.** Draw a new sample of 50 cards that the detector tags, with seed 1141, not 1078: the old sample chose the branch to drop. Read each card against its oracle text and the taxonomy line. The bar: at least 45 of 50 protect your own permanents. Count a card that protects only during your turn as false. If the bar fails, narrow the patterns, draw again with seed 1142, and report every draw, not only the last.
- **Recall,** against the 76 hand-tagged cards of your proposal, by primary and secondary. Say again that you tuned the patterns on that set.
- **Tests:** one case for each pattern that you keep, and one for each excluded form (a fog, a player-only grant, a self-only grant, a blink of a permanent you do not control). Invented names only.
- **Mutants:** the detector placed first in `DETECTORS`; the player-only branch put back; the "you control" check on blink saves removed. Quote each count line and each failed test.

## Item 3. One seat for each card when `gaps[]` lists a role twice (DEC-1121 N3)
- The reviewer ran `_generate` with `gaps=("removal-spot", "removal-spot")`, and the pool held one card twice. No `metrics.json` lists a role twice today, because `merge_gaps` writes one role gap per role.
- Change `for gap in gap_roles:` (`scripts/generate_candidate_pool.py:712` on `main` `7b7bfa2`) to `for gap in dict.fromkeys(gap_roles):`.
- Add one case: a role listed twice gives each card one seat. Run the mutant that puts the old line back, and quote its count line and failed test.

## Item 4. The pools, regenerated once (data commit)
1. Link the three private inputs (Rules), then run `uv run python scripts/generate_candidate_pool.py --all`.
2. **Know what moves.** `score_card` reads the candidate's role (line 512). When that role's bucket in the deck holds 8 or more cards and the candidate scores below the bucket's median, the score drops to 65% (lines 46, 47 and 511 to 528). So a changed role can change a score, and the first `limit` entries can move. That is expected.
3. **Prove by script, for all 21 decks:**
   - Each entry whose `deck_role` differs from `main`'s: a count for each deck, by old and new role.
   - Each entry whose score differs from `main`'s: its `deck_role` differs too. Name any entry for which that is false, and stop and ask.
   - The seats: a count for each (deck, role) pair before and after, the same table as hand-back `a090bc1c`, with grave-dividends `protection` added. Each seat's `seeded_for_gap` equals its `deck_role`.
   - None of the 5 misread cards is a seat for its old role.
   - A deck with no changed role keeps its file byte for byte.
   - A second `--all` prints `no change` for all 21.
4. Run `uv run python scripts/compute_deck_metrics.py --all` once with both mirror files linked. It must print `Wrote 0 metrics file(s)`, because the metrics read only `generated_at` from `candidates.json`. Quote the line.
5. Do not run `auto_tag_roles.py` on a deck. `git status --porcelain data/` lists `candidates.json` files only; no `deck.json` changes.
6. Remove the three links before the hand-back.

## Item 5. The example in `docs/deck-metrics.md` holds figures the script writes (DEC-1121 N2)
- The reviewer found four figures in the example payload that the script cannot write. The recursion row gives `30.0` from `4.5 / 2`, but the formula gives 36.0. `value-incremental` at bracket 4 has a target of 4, which gives 33.8. `role_coverage_health` reads 86, but the mean of its 8 `by_role` values rounds to 82. `removal-spot` reads 90 at a target of 8, but counts move in steps of 0.5, so the score is 88 or 94.
- Rebuild the example from one real deck's `metrics.json` on your head. Name the deck in one sentence above the example. Keep the example's keys, and trim lists the way the example trims them today.
- Read each figure that the prose around the example quotes against the new example, and fix the prose to match. Change no formula and no score.

## Rules
- **Tree.** Run `cd /Users/dpires/Documents/Personal/code/mtg-precon-upgrader`, then `git fetch origin`, then `git worktree add -b dec-<N>-classifier-followups wt-dec<N> origin/main`. `<N>` is this issue's number. Do not touch another agent's tree. Keep every scratch file outside the tree.
- **Environment.** Use `HOME="$PAPERCLIP_GITHUB_HOST_HOME"` for every `git` and `gh` command. Run `export UV_CACHE_DIR="$PAPERCLIP_GITHUB_HOST_HOME/.cache/uv"`. Use `uv run` for every Python command; the system `python3` is 3.9.
- **Private inputs.** Link three files into the tree's `priv_data/`, and remove all three links before the hand-back:
  `ln -s /Users/dpires/Documents/Personal/code/mtg-precon-upgrader/priv_data/scryfall-oracle.json priv_data/`
  `ln -s /Users/dpires/Documents/Personal/code/mtg-precon-upgrader/priv_data/scryfall-oracle.meta.json priv_data/`
  `ln -s /Users/dpires/Documents/Personal/code/mtg-precon-upgrader/priv_data/owned_formatted.csv priv_data/`
  Change no file under `priv_data/` in the shared checkout.
- **Card names.** A real card that a test, a fixture or the hand-back names gets an oracle check first. Use one `/cards/collection` request for the names, or the `scryfall_*` tools one call after the other.
- **Mutant runs.** Before each run, remove each `__pycache__` under `scripts/` and `tests/` only, and set `PYTHONDONTWRITEBYTECODE=1`. `mcp-servers/youtube-research/` holds tracked `.pyc` files; do not remove them.
- **The Python suite, on the final head.** `CI=true uv run --with pytest python -m pytest -q -rfEs`. Basis: `main`'s push run 38732728156 at `7b7bfa2` reads `518 passed, 1 skipped, 1189 subtests passed`. Expected: that basis plus your new tests. If a pull request that adds Python tests merges first, take the basis from `main`'s newest `python-tests` push run and say so.
- **CI.** `web-ci` runs too, because the diff holds `data/**`. Basis: `main`'s push run 38732728161 at `7b7bfa2` reads unit `469 passed` (42 files) and e2e `142 passed (11.5m)`. Run no local e2e. Quote both workflows' totals on your head. A case that passes only on retry is not a failure, but name it.
- **Main moves.** Before the hand-back PATCH, run `git fetch origin` and `git diff --stat "$(git merge-base HEAD origin/main)" origin/main -- scripts tests data web AGENTS.md docs .github pytest.ini conftest.py pyproject.toml uv.toml`. If it prints, merge `origin/main` (no rebase, no force-push), regenerate the pools only if `scripts/` or `data/decks/` changed, push once, and wait for CI again.
- **Yield to a higher leg.** After each commit, read your issues with status `todo` (`GET /api/companies/a178baa8-538e-4172-88b9-c0b95e787e56/issues?assigneeAgentId=4e51e111-eff7-4619-95dd-9e43a955e637&status=todo`). If one has priority high or medium: push what is committed, post a short state comment here (the commits done, the next step), and hand back with the Handoff PATCH. The CEO assigns this leg back when that leg is out.
- Do not merge. The CEO merges after the review.

## Queue
Your live run on DEC-1131 (high) comes first. This leg starts after it.

## Hand-back
Post one comment on this issue. Lead with the outcome, write short complete sentences, and give each number its basis.
- The pull request, its head and the commits, one line each.
- Item 1: the census table, the 20 read verdicts, the count lines and the mutant table.
- Item 2: each precision draw with its seed and its 50 verdicts (one line each), the recall table, the count lines and the mutant table.
- Item 3: the count line and the mutant line.
- Item 4: the proof of step 3, the seat table and the `Wrote 0` line.
- Item 5: the deck that the example comes from, and each prose figure that you changed.
- CI: `python-tests` and both jobs of `web-ci` on the head, with their totals.
- Each step that you skipped or changed, with the reason.

## Handoff
Make every write that your hand-back promises before this step: the PATCH ends your run at once. When the comment is posted, send one PATCH on this issue as the last action of your run:
- `assigneeAgentId`: the CEO (`f9427c33-d719-4fd5-a3c5-cd2f65dd01e8`).
- `status`: `in_review`.
- `executionPolicy.monitor`: `nextCheckAt` 30 minutes ahead, `scheduledBy: "assignee"`, and `notes` under 500 characters that name the hand-back comment.

The assignment wakes the CEO. The monitor wakes the CEO when the server skips that wake. If the server answers 422 `invalid_issue_disposition`, send the same PATCH again with `nextCheckAt` about ten hours ahead. Never set `done`; only the CEO closes the issue.

**A question in the middle of the leg** takes the hand-back path, in four steps:
1. Do the items that the question does not touch.
2. Commit and push them.
3. Post the question on this issue: the question, the evidence, a count by cause, your readings and your recommendation.
4. As your last action, send the same PATCH.

Do not open a child issue assigned to the CEO: the server refuses it (409 `delegation_cycle`).

planned-by: CEO. Parent: DEC-1078. Sources: DEC-1078 hand-back `a090bc1c` (the 5 misread seats and the protection proposal); DEC-1121 verdict `4e0e4a22` (N2 and N3).

