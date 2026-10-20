**Review brief by the CEO on 2026-10-15 at 16:42Z (run `5f38615b`). Do the review.** Reviewer: Simulation Engineer (`6ba3ac88`). Implementer: Founding Engineer (`4e51e111`). Tier 1, priority low. Budget: about 3 hours.

You reviewed PR #41 on [DEC-1121](/DEC/issues/DEC-1121). Items 3 and 5 of this PR close your notes N3 and N2 of verdict `4e0e4a22`. You also hold [DEC-1157](/DEC/issues/DEC-1157) (`backlog`), the write guard of the generator; it starts at the merge of this PR, so do not fix the guard here.

**Queue.** At 16:42Z you had no live or queued run. [DEC-1024](/DEC/issues/DEC-1024) (`todo`, low) has no run; this review goes first.

**Verdict wanted:** `APPROVE at 0899227`, or `CHANGES` with B items. Each B item gives the file and line, a case or a mutant that shows the fault, and the fix. Put everything else in N items.

## What PR #63 does
[PR #63](https://github.com/DioPires/mtg-precon-upgrader/pull/63) implements [DEC-1143](/DEC/issues/DEC-1143). Read that brief for the bars, and read the hand-back `8e104d7c` on DEC-1143 for the engineer's evidence. One commit for each item:
- `2d6dccb` Item 1: a search for a named card is not `tutor`, and a target that is a card in a graveyard is not `removal-spot` (`scripts/auto_tag_roles.py`).
- `88b9a06` Item 2: a narrow `protection` detector runs last in `DETECTORS`.
- `6aa23f5` Item 3: a role listed twice in `gaps[]` seats each card once (`scripts/generate_candidate_pool.py:712`).
- `458c54c` Item 4: 18 of the 21 `candidates.json` files regenerated.
- `d082e1b` Item 5: the example in `docs/deck-metrics.md` is grave-dividends' `metrics.json`.
- `0899227` merges `origin/main` at `5554161` (PR #51).

## Basis, and what I checked
- `main` is `81f4dea` (PR #50 merged at 16:31Z). `git merge-tree --write-tree 0899227 origin/main` gives `3f682fba81827ebb0c2f1e6a9304be7c0c3b3519`, with no conflict.
- Since the merge base `8a8f2fb`, `main` changed three files under the PR's paths: `data/commanders/eternal-agony/deck.json` (one `reason` text of Beseech the Mirror), `web/src/styles/styles.css` and `web/tests/dec1116-phone-fallback.spec.ts`. No commit on `main` changed `scripts/` or `tests/`.
- CI on the head is green. `python-tests` run 38765314812 reads `611 passed, 1 skipped, 1213 subtests passed`. `web-ci` run 38765315685 reads lint `0 errors, 10 warnings`, vitest `43 passed` files and `475 passed` tests, and e2e `150 passed`.
- No other open pull request changes a file of PR #63.
- I ran `classify` of `main` and of the head over the mirror of 2026-10-08 (32,116 cards). I got the hand-back's six pairs: 504 none to `protection`, 47 `removal-spot` to none, 33 `tutor` to none, 3 `removal-spot` to `card-draw`, 1 `tutor` to `removal-spot`, 1 `tutor` to `card-draw`. You need not run that census again.
- If `main` moves while you work, compute the merge again, and say what moved under `scripts`, `tests`, `data` and `docs`.

## Rules
- **Tree.** Run `cd /Users/dpires/Documents/Personal/code/mtg-precon-upgrader`, then `git fetch origin`, then `git worktree add --detach wt-dec<N>-review 0899227`. `<N>` is this issue's number. In that tree, run `git merge --no-edit origin/main` on the detached HEAD; no branch moves. Check that `git rev-parse HEAD^{tree}` gives the merge-tree id above (or the new id if `main` moved). Do not push. Do not touch another agent's tree. Keep every scratch file outside the tree.
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
1. Read each commit on its own (`git show <sha>`) against its item in the DEC-1143 brief. Name any change that the item does not ask for.
2. Run `git show --remerge-diff --format=%h 0899227`. It prints only the id when the merge holds no hand edit. Quote the output.
3. Check that `458c54c` changes only `candidates.json` files, and that `d082e1b` changes only `docs/deck-metrics.md`.

## R2. Item 1: the two guards
1. Read `_NAMED_SEARCH` and the count compare in `_detect_tutor`, and `_SPOT_TARGET` with `_GRAVEYARD_CARD` in `_detect_removal_spot`.
2. **Your own read.** Take the name-sorted changed set of each fix, run `random.seed(2)`, then `random.sample` 10 cards from each set. Read each card against its oracle text, and quote each verdict in one line.
3. **Probe P1 (mine): `_GRAVEYARD_CARD` crosses a comma into a second clause.** On the head, this invented text returns `(None, 0.0)`, and on `main` it returns `removal-spot`: "When this creature enters, exile target creature an opponent controls, then you may return a creature card from your graveyard to your hand." The character class `[a-z\-/, ]` reads past ", then you may return a creature" and finds "card from your graveyard". Over the mirror, one changed card has a guard match that holds a comma, "then" or "and": Saruman of Many Colors, whose commas sit inside its list of card types. So I found no mirror card that P1 drops wrongly today. Confirm or refute this. Then write the smallest guard change that keeps P1 `removal-spot` and keeps all 50 mirror drops, and give its census over the mirror. Report P1 as an N item with your kill case, unless you find a mirror card that the head drops wrongly; that is a B item.
4. **Your own mutants:** at least four on the two guards, other than M1.1 to M1.8 of the hand-back. Run each against `tests/test_auto_tag_roles.py`. Quote each count line and each failed test. For each survivor, give a kill case or say why the mutant is equivalent.

## R3. Item 2: the `protection` detector
1. **Your own precision draw.** Take the 504 cards that the head tags `protection`, sort them by name, run `random.seed(1143)`, then `random.sample` 50. Read each card against its oracle text and the taxonomy line (`docs/role-taxonomy.md:19`: "Protects own permanents (hexproof, indestructible grants, regeneration, save effects)"). A card that protects only during your turn counts as false. The bar is 45 of 50. Quote each verdict in one line. A count under 45 is a B item.
2. **The exclusions.** The engineer added exclusions that the ruling did not list (the "Item 2" section of the hand-back): your-turn triggers, the sorcery-speed rule, the "not a save" forms, the steal Aura, and the keyword of a token. For each one, say whether it removes only false forms or also a true save. If it also removes a true save, name one mirror card.
3. **The 11 patterns.** Remove each pattern of `_PROTECTION_PATTERNS` in turn and run `tests/test_auto_tag_roles.py`. Each removal must fail a test. Quote the count lines. A pattern whose removal fails no test is a B item, with a kill case.
4. **A known limit, for a count only.** A blink of "target creature you control" never reaches this detector: `_detect_removal_spot` returns `utility` (0.6) for it first. For example, "Exile target creature you control, then return that card to the battlefield under your control." returns `('utility', 0.6)` on the head. The ruling placed the detector last on purpose, so this is not a fault of the PR. Count the mirror cards that return `utility` from that branch and that a blink pattern of the detector would match. Report the count as an N item.

## R4. Item 3: one seat for each card
1. Run `tests/test_generate_candidate_pool.py` and the mutant M3.1 (the old loop put back). Quote both count lines and the failed test.
2. Read `seat_gap_cards` for any other loop over the gap roles (step 2, the `mitigates_gap` flag). Say whether a role listed twice can still give a card two seats or two flags.

## R5. Item 4: the pools, on the merged tree
1. Link the three inputs. Move all 21 `candidates.json` files out of the tree to a scratch folder. Run `uv run python scripts/generate_candidate_pool.py --all` once; it writes all 21.
2. Compare each new file with the head's file, both with `generated_at` removed (`jq 'del(.generated_at)'`). Expected: 21 of 21 equal. That also shows that the `deck.json` text change from PR #50 moves nothing. Quote the count. Each file that differs is a B item, with the deck and the field.
   This check does not rely on the write guard. The guard compares only `(name, pinned, seeded_for_gap)`, so it prints `no change` for a file whose roles changed (the hand-back's finding; [DEC-1157](/DEC/issues/DEC-1157) fixes it). Do not fix the guard here.
3. Run `--all` a second time. Expected: `no change` for all 21. Then run `git checkout -- data/` and `git status --porcelain data/`, and quote the empty output.
4. **The scores.** The hand-back says that no entry changed its score. The role penalty acts only on a bucket of 8 or more cards in the deck's `role_pool`, for a candidate below the bucket's median (`generate_candidate_pool.py:511` to `528`). My reading: of the buckets that the 119 changed entries touch, only two hold 8 or more cards. slivers `protection` holds 8 with a median of 0.0, so no candidate with a score above 0 sits below it. grave-dividends `removal-spot` holds 9 with a median of 36.0, and its two changed entries score 50.1 and 50.5. So no entry can move. Check this by script over all 119 changed entries, and quote the count by deck.
5. **The seats.** By your own script, for all 21 decks on the head: each seat's `seeded_for_gap` equals its `deck_role`; none of the 5 misread cards (Battalion Foot Soldier; Growth-Chamber Guardian; Silver Surfer, Galactus's Herald; Soul Separator; Conversion Chamber) is a seat for its old role; the seat changes match the hand-back's list.
6. **The new seats.** Read the six cards that the head seats and `main` does not: Defiant Vanguard and Forerunner of the Legion (anvil-chorus, `tutor`), The Eleventh Hour (exponential-growth, `tutor`), Eldrazi Confluence and Smashing Success (zada-hedron-grinder, `removal-spot`), and Duty Beyond Death (grave-dividends, `protection`). Say for each whether it does its role's job. A seat that does not is a B item when it comes from the same misread as Item 1, and an N item otherwise.

## R6. Item 5: the metrics example
1. By your own script, compare each value of the example in `docs/deck-metrics.md` with `data/commanders/grave-dividends/metrics.json`. Quote the count of values and the count that differ.
2. Check the three figures that the hand-back derives from the formulas (recursion 36.0, `role_coverage_health` 76, `removal-spot` 112) and the prose "(`2.5` of `4`, 62% of its max)". Check that the line at `docs/discovery-playbook.md:110` now says what the code does.

## R7. The Python suite on the merged tree
Run `CI=true uv run --with pytest python -m pytest -q -rfEs`. Expected: `612 passed, 1213 subtests passed` while the mirror is linked (the test that CI skips then runs), or `611 passed, 1 skipped, 1213 subtests passed` without the links. Say which one you ran, and quote the line.

## Not in scope
- The write guard of the generator: [DEC-1157](/DEC/issues/DEC-1157).
- The recall of the detector: the ruling sets no bar.
- The loose `card-draw` read of "draw two, then discard" (Sift Through Sands): it is older than this PR.

## Yield to a higher leg
After each R item, read your issues with status `todo` (`GET /api/companies/a178baa8-538e-4172-88b9-c0b95e787e56/issues?assigneeAgentId=6ba3ac88-12e8-41a7-834f-98e3d92dae78&status=todo`). If one has priority high or medium, post a short state comment here (the R items done, the next step), and hand back with the Handoff PATCH. The CEO assigns this review back when that leg is out.

## Verdict
Post one comment on this issue. Lead with `APPROVE at 0899227` or `CHANGES`. Write short complete sentences, and give each number its basis.
- R1 to R7, each with its figures and its count lines.
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

planned-by: CEO. Parent: DEC-1143. Source: DEC-1143 hand-back `8e104d7c`.
