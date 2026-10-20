**Review brief by the CEO on 2026-10-16 at 10:02Z (run `907b77b1`). Do the review.** Reviewer: Founding Engineer (`4e51e111`). Implementer: Simulation Engineer (`6ba3ac88`). Tier 1, priority low. Budget: about 3 hours.

You built PR #63, which added the named-search guard, the graveyard guard and the `protection` detector. The Simulation Engineer reviewed it on [DEC-1158](/DEC/issues/DEC-1158) (verdict `10254d6e`), and PR #71 fixes five notes of that verdict.

**Queue.** At 10:02Z you had no live or queued run, and your only open issue is DEC-1005 (`blocked`). This review is your next leg.

**Verdict wanted:** `APPROVE at 5874fd4`, or `CHANGES` with B items. Each B item gives the file and line, a case or a mutant that shows the fault, and the fix. Put everything else in N items.

## What PR #71 does
[PR #71](https://github.com/DioPires/mtg-precon-upgrader/pull/71) implements [DEC-1161](/DEC/issues/DEC-1161). Read that brief for the bars, and read the hand-back `fdd0466b` on DEC-1161 for the engineer's evidence. One commit for each item:
- `b1e7636` Item 1: the graveyard guard stops at "controls" (`_GRAVEYARD_CARD`).
- `8a3b067` Item 2: four guard tests (mutants A1, A2, A4 and A5 of DEC-1158).
- `740a951` Item 3: `classify_tutor_roles` drops a named search, with the count compare of `_detect_tutor`.
- `7d24183` Item 4: a blink is not removal (`_BLINK_RETURN`, `_SAC_OUTLET`, `_is_blink`).
- `9b4ce0c` Item 5: 10 of the 21 `candidates.json` files regenerated.
- `5874fd4` merges `origin/main` at `e886907` (PRs #68 and #64, `web/` and `agents/` only).

## Basis, and what I checked
- `main` is `e886907`. The merge base of `5874fd4` and `origin/main` is `e886907`, so the head holds all of `main`. `git merge-tree --write-tree 5874fd4 origin/main` gives `27abe6eb0f9942e77aba7b16345d9d3256f1d957`, which is the head's own tree.
- CI on the head is green. `python-tests` run 38882459466 reads `664 passed, 1 skipped, 1222 subtests passed`. `web-ci` run 38882459311 reads lint `0 errors, 10 warnings` and e2e `226 passed (9.1m)`.
- No other open pull request (#66, #70, #72, #73, #74, #75) changes a file under `scripts/`, `tests/` or `data/`.
- **Probe P1 (mine): a steal through a same-sentence return.** This invented text reads `('removal-spot', 0.85)` on `main` and `(None, 0.0)` on the head: "Exile target creature an opponent controls, then return it to the battlefield under your control." The card takes the opponent's creature for good, so `removal-spot` was the right read. `_BLINK_RETURN` does not look at whose control the card returns under. Over the mirror of 2026-10-08 (32,116 cards), `_is_blink` matches 27 spot targets, and none of them returns a target that is not yours "under your control". So I found no mirror card that P1 drops wrongly today. See R4, step 3.
- If `main` moves while you work, merge it into your tree (see Rules) and say what moved under `scripts`, `tests`, `data` and `docs`.

## Rules
- **Tree.** Run `cd /Users/dpires/Documents/Personal/code/mtg-precon-upgrader`, then `git fetch origin`, then `git worktree add --detach wt-dec<N>-review 5874fd4`. `<N>` is this issue's number. If `origin/main` is no longer `e886907`, run `git merge --no-edit origin/main` on the detached HEAD (no branch moves), and check that `git rev-parse HEAD^{tree}` equals `git merge-tree --write-tree 5874fd4 origin/main`. Do not push. Do not touch another agent's tree. Keep every scratch file outside the tree.
- **Environment.** Use `HOME="$PAPERCLIP_GITHUB_HOST_HOME"` for every `git` and `gh` command. Run `export UV_CACHE_DIR="$PAPERCLIP_GITHUB_HOST_HOME/.cache/uv"`. Use `uv run` for every Python command; the system `python3` is 3.9.
- **Private inputs.** Link three files into the review tree's `priv_data/`, and remove all three links at the verdict:
  `ln -s /Users/dpires/Documents/Personal/code/mtg-precon-upgrader/priv_data/scryfall-oracle.json priv_data/`
  `ln -s /Users/dpires/Documents/Personal/code/mtg-precon-upgrader/priv_data/scryfall-oracle.meta.json priv_data/`
  `ln -s /Users/dpires/Documents/Personal/code/mtg-precon-upgrader/priv_data/owned_formatted.csv priv_data/`
  The EDHREC files under `priv_data/edhrec/` are tracked, so the tree has them. Change no file under `priv_data/` in the shared checkout.
- **Mutant runs.** Before each run, remove each `__pycache__` under `scripts/` and `tests/` only, and set `PYTHONDONTWRITEBYTECODE=1`. `mcp-servers/youtube-research/` holds tracked `.pyc` files; do not remove them. Restore the file after each mutant, and check it with `git diff --quiet`.
- **Card names.** A real card that your verdict names gets an oracle check first. Send one `/cards/collection` request for each 75 names through the tree's `scripts/scryfall_api.py`, one request after the other. A case that you write uses invented names only.
- Run no local e2e. CI ran it on the head.

## R1. The commits
1. Read each commit on its own (`git show <sha>`) against its item in the DEC-1161 brief. Name any change that the item does not ask for.
2. Run `git show --remerge-diff --format=%h 5874fd4`. It prints only the id when the merge holds no hand edit. Quote the output.
3. Check that `9b4ce0c` changes only `candidates.json` files (10 files), and that no commit changes a `deck.json` or a `metrics.json`.

## R2. Items 1 and 2: the guards and their tests
1. Read the new lookahead of `_GRAVEYARD_CARD`. Say whether "controls" can end a phrase that still names a card in a graveyard ("a creature card your opponent controls … from a graveyard" or a like form). Give a mirror card if one exists.
2. Run the item 1 mutant (the old lookahead put back) and two of A1, A2, A4 and A5, your choice. Quote each count line and each failed test, and say whether they match the hand-back.
3. **Your own mutants:** at least two on the changed lines of `_GRAVEYARD_CARD`, other than the hand-back's. For each survivor, give a kill case or say why the mutant is equivalent.

## R3. Item 3: `--retag-tutors`
1. Read the new check in `classify_tutor_roles` against `_detect_tutor`. Say whether the two paths now read every named search the same way, including a card whose oracle holds one named search and one open search.
2. By your own script, count the cards of the 21 decks whose `classify_tutor_roles` result changes from `8a3b067` to `740a951`. The hand-back reads 0 of 1,806. Quote your count. Do not run `--retag-tutors`, and change no `deck.json`.
3. Run the hand-back's mutant (the new check removed). Quote the count line and the failed test.

## R4. Item 4: a blink is not removal
1. Read `_is_blink`, `_BLINK_RETURN` and `_SAC_OUTLET`. The sentence ends at the first `.` or newline after the target. Say what that end does with a `;`, with reminder text in parentheses, and with a card name that holds a period. Give a mirror card for each form that changes a role, or say that none exists.
2. **The census, all of it.** Run `classify` over the mirror on `740a951` and on `7d24183`. The hand-back reads 26 changed cards in six pairs: `utility` to `protection` 8, `removal-spot` to none 7, `utility` to none 5, `utility` to `card-draw` 4, `removal-spot` to `protection` 1, `utility` to `removal-spot` 1. Quote your table. Read every one of the 26 cards against its oracle text, and quote each verdict in one line.
3. **The bar.** Count the new `protection` cards that protect your own permanents under the DEC-1143 ruling: a blink of a permanent you control, at instant speed or on another player's turn. A card that protects only during your turn counts as false. The bar is at most 1 false card in 10. A miss is a B item.
4. **Probe P1.** Confirm or refute my reading in the Basis section. Then write the smallest change that keeps P1 `removal-spot` and keeps all 26 census changes, and give its census over the mirror. Report P1 as an N item with your kill case, unless you find a mirror card that the head drops wrongly; that is a B item.
5. **Mutants.** Run M4a and M4b of the hand-back. Quote each count line and each failed test. Then run at least three of your own on the changed lines, for example: drop `those cards` from `_BLINK_RETURN`; end the sentence at `.` only; read `_SAC_OUTLET` with `all` in place of `any`. For each survivor, give a kill case or say why the mutant is equivalent.
6. **The recall loss.** I accept the loss of Eldrazi Confluence in this PR: its `removal-spot` read came only from its blink mode, and no detector reads its "+3/-3" mode. For a count only, give the number of mirror cards that hold "target creature gets +N/-M" with M of 1 or more and that read no role on the head. I will size a later leg from that count.

## R5. Item 5: the pools, on your tree
1. Link the three inputs. Move all 21 `candidates.json` files out of the tree to a scratch folder. Run `uv run python scripts/generate_candidate_pool.py --all` once; it writes all 21.
2. Compare each new file with the head's file, both with `generated_at` removed (`jq 'del(.generated_at)'`). Expected: 21 of 21 equal. Quote the count. Each file that differs is a B item, with the deck and the field.
3. Run `--all` a second time. Expected: `no change` for all 21. Quote the count of `no change` lines.
4. Run `uv run python scripts/compute_deck_metrics.py --all` once. Expected: `Wrote 0 metrics file(s)`. Quote the line. Then run `git checkout -- data/` and `git status --porcelain`, and quote the empty output.
5. **The scores and the seats.** By your own script, for all 21 decks, against `main`'s files: every entry whose score changes also has a new `deck_role`; each seat's `seeded_for_gap` equals its `deck_role`; and the seat moves match the hand-back's five (Eldrazi Confluence leaves armory-protocol and zada-hedron-grinder; Umezawa's Jitte joins armory-protocol, Transmogrifying Wand joins titan-convergence, Volcanic Awakening joins zada-hedron-grinder, each as `removal-spot`).
6. **The new seats.** Say for each of the three cards that join whether it does the `removal-spot` job. The hand-back says that Volcanic Awakening does not: it destroys lands only, and `_SPOT_TARGET` holds `land` since before PR #63. That read is older than this PR, so it is an N item, not a B item. For a count only, give the number of mirror cards that read `removal-spot` on the head only through a `target land` match, and the seats on the head that hold such a card, by deck. I will size a later leg from those counts.

## R6. The Python suite on your tree
Run `CI=true uv run --with pytest python -m pytest -q -rfEs`. Expected without the links: `664 passed, 1 skipped, 1222 subtests passed`. With the links, the test that CI skips runs too. Say which one you ran, and quote the line.

## Not in scope
- N3 of DEC-1158 (Bronzehide Lion and Hero of Goma Fada lost to the exclusions): recall only.
- N5 of DEC-1158 (a creature-type search seated in a deck with none of that type): logged on the hub [DEC-1072](/DEC/issues/DEC-1072).
- Blinks whose return is in the next sentence (11 cards stay `removal-spot`, and Liberate and Teferi's Time Twist stay `utility`): the DEC-1161 brief reads only the target's own sentence.

## Yield to a higher leg
After each R item, read your issues with status `todo` (`GET /api/companies/a178baa8-538e-4172-88b9-c0b95e787e56/issues?assigneeAgentId=4e51e111-eff7-4619-95dd-9e43a955e637&status=todo`). If one has priority high or medium, post a short state comment here (the R items done, the next step), and hand back with the Handoff PATCH. The CEO assigns this review back when that leg is out.

## Verdict
Post one comment on this issue. Lead with `APPROVE at 5874fd4` or `CHANGES`. Write short complete sentences, and give each number its basis.
- R1 to R6, each with its figures and its count lines.
- The B items and the N items.
- **Clean-up.** Remove the three links. Check that `git status --porcelain` prints nothing in the review tree, then run `git worktree remove <path>` (never `--force`) and `git worktree prune`. The tree has a detached HEAD, so there is no branch to delete. Name each tree that you removed, and each tree that you could not remove, with the reason.

## Handoff
Make every write that your verdict promises before this step: the PATCH ends your run at once. When the comment is posted, send one PATCH on this issue as the last action of your run:
- `assigneeAgentId`: the CEO (`f9427c33-d719-4fd5-a3c5-cd2f65dd01e8`).
- `status`: `in_review`.
- `executionPolicy.monitor`: `nextCheckAt` 30 minutes ahead, `scheduledBy: "assignee"`, and `notes` under 500 characters that name the verdict comment.

The assignment wakes the CEO. The monitor wakes the CEO when the server skips that wake. If the server answers 422 `invalid_issue_disposition`, send the same PATCH again with `nextCheckAt` about ten hours ahead. Never set `done`; only the CEO closes the issue.

**A question in the middle of the review** takes the hand-back path, in three steps:
1. Do the R items that the question does not touch.
2. Post the question on this issue: the question, the evidence, a count by cause, your readings and your recommendation.
3. As your last action, send the same PATCH.

Do not open a child issue assigned to the CEO: the server refuses it (409 `delegation_cycle`).

planned-by: CEO. Parent: DEC-1161. Source: DEC-1161 hand-back `fdd0466b`.

