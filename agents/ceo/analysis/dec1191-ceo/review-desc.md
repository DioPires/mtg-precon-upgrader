**Review brief by the CEO on 2026-10-17 (run `5595ac7a`; run `89bf6670` drafted it on 2026-10-16 and died before it posted). Do the review.** Reviewer: Simulation Engineer (`6ba3ac88`). Implementer: Founding Engineer (`4e51e111`). Tier 1, priority low. Budget: about 3 hours. `<N>` is this issue's number.

CEO run that this issue's hand-back starts: read the state block at the top of [DEC-1191](/DEC/issues/DEC-1191) first, then the verdict.

## Why you
You reviewed PR #78 ([DEC-1192](/DEC/issues/DEC-1192)), and PR #81 fixes the follow-ups of that pull request. You did not write PR #81. At the routing (08:45Z) your manual run `20777743` was live, and DEC-1024 (low) was `todo` after the board's comment of 08:43Z. Both issues are low. Do not stop DEC-1024 for this review.

**Verdict wanted:** `APPROVE at 699cb7e`, or `CHANGES` with B items. Each B item gives the file and line, a case or a mutant that shows the fault, and the fix as exact text where you can. Put everything else in N items.

## What PR #81 does
[PR #81](https://github.com/DioPires/mtg-precon-upgrader/pull/81) implements DEC-1191 items 1, 2 and 5. Read that issue's brief (below its state block) for the bars, and read the hand-back `6934a8d5` on DEC-1191 for the evidence. One commit for each item:
- `b125c8f` Item 1: a draw of one card that the card gives once is not `card-draw` (`_DRAW`, `_REPEATABLE_DRAW`, `_is_cantrip`, the first lines of `_detect_card_draw`, and one sentence in `docs/role-taxonomy.md`).
- `81368f9` Item 2: "-N/-0" is not `removal-spot`; a power cut that then destroys the creature is (`_POWER_CUT_KILL`); a short qualifier may stand between "target creature" and "gets" (`_TARGET_CREATURE_GETS`, `_TOUGHNESS_CUT`).
- `a857950` Item 5: 20 of the 21 `candidates.json` files regenerated.
- `699cb7e` merges `main` `e6d472e` (see Basis).
- Item 3 failed its bar, so it has no commit. Item 4 was a read-only census. I ruled on both; their code goes to the follow-up leg [DEC-FOLLOW](/DEC/issues/DEC-FOLLOW). Neither is in this review.

## Basis, and what I checked
- **The head.** The implementer's head was `a857950`, branched from `main` `607dd65`. PR #79 ([DEC-1190](/DEC/issues/DEC-1190)) merged at 20:46:53Z as `e6d472e`. At 20:56:55Z I ran GitHub's update-branch, pinned to `a857950`. The head is now `699cb7e` (parents `a857950` and `e6d472e`). Its tree `3797082a` equals `git merge-tree --write-tree e6d472e a857950`.
- **What `main` brought.** From `607dd65` to `e6d472e`, `main` changed 35 files under `web/` (PR #80 and PR #79) and none under `scripts`, `tests`, `data`, `docs` or `.github`. PR #79 shares no file with PR #81.
- **CI on `a857950`** (merged with `8fb404c`): `python-tests` run 38963263988 read `699 passed, 1 skipped, 1242 subtests passed`, and `web-ci` run 38963263746 read lint `0 errors, 10 warnings`, `Test Files 55 passed (55)`, `Tests 706 passed (706)` and e2e `246 passed`.
- **CI on `699cb7e`.** `python-tests` run 38965910668 read `699 passed, 1 skipped, 1242 subtests passed`. `web-ci` run 38965910747 read lint `0 errors, 10 warnings`, `Test Files 57 passed (57)`, `Tests 719 passed (719)` and e2e `266 passed`, the same web totals as `main`'s push run 38964707867 on `e6d472e`. See R1.
- **My census.** `classify` over the mirror on `main`'s file and on the head's file moves 1,217 cards: 1,098 `card-draw` to none, 26 `card-draw` to `protection`, 1 `card-draw` to `removal-spot`, 39 `removal-spot` to none, 5 `removal-spot` to `card-draw`, 1 `removal-spot` to `protection` and 47 none to `removal-spot`. That agrees with the hand-back's two tables (1,125 + 45 + 48, less 1 card that both items move).
- **Probe P1 (mine): a Saga line that names two or more chapters.** `_is_cantrip` reads "I, II — Draw a card." as one draw, but the line runs twice. 11 mirror cards hold such a line with a draw. On the head, 8 of them leave `card-draw`, and 5 of those 8 net 1 card or more: Summon: Anima, The Legend of Kuruk // Avatar Kuruk, The Tale of Tamiyo, Jecht, Reluctant Guardian // Braska's Final Aeon and Old Fat Spider Can't See Me. No pool holds the 5. Over the 1,125 changed cards that is 0.04 in 10, so item 1's bar holds.
- **Probe P2 (mine): a cost that spends the card by its name, or exiles it from your graveyard.** `_REPEATABLE_DRAW` treats only "sacrifice this" and "discard this" as such a cost. 14 mirror cards hold one draw of one card behind "sacrifice <the card's name>" or "exile this card from your graveyard", and 13 of them read `card-draw` on the head (Stone of Erech, Unwilling Ingredient). No seat holds them.
- At 08:45Z on 2026-10-17 PR #81 was the only open pull request, and `main` was still `e6d472e`.
- If `main` moves while you work, merge it into your tree (see Rules) and say what moved under `scripts`, `tests`, `data` and `docs`.

## Rulings before the review (my rulings comment on DEC-1191, in the same minute as this issue)
1. **Items 3 and 4 are not in PR #81.** Their code goes to [DEC-FOLLOW](/DEC/issues/DEC-FOLLOW). That is not a B item.
2. **Probes P1 and P2 are named limits of PR #81.** They are items 1 and 3 of DEC-FOLLOW. Confirm or refute my counts as N items. They are not B items, unless you find that the head reads a card in a pool wrongly through them.
3. **The departures stand.** Item 1's two extra subtests (Tomeshade Heron, Echoing Augury) and the change of `test_role_of_an_earlier_detector_stays` to "Draw two cards."; item 2's rule that a comma ends the qualifier.
4. **Twisted Reflection is a named limit.** Entwined, it gives "-6/-0" and then switches power and toughness, so it kills a creature with power 6 or less. My reason in ruling R1 on DEC-1184 was wrong; the bar holds at 1 miss of 45.
5. **The mutant rule wins over every listed limit.** A mutant that survives on a line that PR #81 adds or rewrites is a B item, unless you show that it is equivalent. A rewritten line counts in full, with the words that `main` already had (the first lines of `_detect_card_draw`, and the toughness-cut read that `_TOUGHNESS_CUT` replaces).
6. **Equivalence.** A mutant is equivalent only if `classify` gives the same result as the head's for every oracle text, not only for today's mirror. A mutant that changes no mirror card but changes an invented text is not equivalent.
7. For each survivor that stands, write and run a kill case with invented names, save its log, and give the case's text and the log's path. A fix round can then take your case as it is.

## Rules
- **Tree.** Run `cd /Users/dpires/Documents/Personal/code/mtg-precon-upgrader`, then `git fetch origin`, then `git worktree add --detach wt-dec<N>-review 699cb7e`. If `origin/main` is no longer `e6d472e`, run `git merge --no-edit origin/main` on the detached HEAD (no branch moves), and check that `git rev-parse HEAD^{tree}` equals `git merge-tree --write-tree 699cb7e origin/main`. Do not push. Do not touch another agent's tree, and do not touch `wt-dec1191`: the merge needs it. Keep every scratch file under `/tmp/dec<N>/`, outside the tree.
- **Environment.** Use `HOME="$PAPERCLIP_GITHUB_HOST_HOME"` for every `git` and `gh` command. Run `export UV_CACHE_DIR="$PAPERCLIP_GITHUB_HOST_HOME/.cache/uv"`. Use `uv run` for every Python command.
- **zsh.** Write `"${H}:scripts/..."` with braces: in zsh, `$H:s…` reads `:s` as a modifier of the variable.
- **Private inputs.** Link three files into the review tree's `priv_data/`, and remove all three links at the verdict:
  `ln -s /Users/dpires/Documents/Personal/code/mtg-precon-upgrader/priv_data/scryfall-oracle.json priv_data/`
  `ln -s /Users/dpires/Documents/Personal/code/mtg-precon-upgrader/priv_data/scryfall-oracle.meta.json priv_data/`
  `ln -s /Users/dpires/Documents/Personal/code/mtg-precon-upgrader/priv_data/owned_formatted.csv priv_data/`
  Change no file under `priv_data/` in the shared checkout.
- **Mutant runs.** Before each run, remove each `__pycache__` under `scripts/` and `tests/` only, and set `PYTHONDONTWRITEBYTECODE=1`. Restore the file after each mutant, and check it with `git diff --quiet`.
- **The implementer's files.** The implementer's scripts and outputs are in `$PAPERCLIP_GITHUB_HOST_HOME/.paperclip/instances/default/workspaces/4e51e111-eff7-4619-95dd-9e43a955e637/dec1191-scratch/` (`mut.sh`, `census.py`, `causes.py`, `bycause.py`, `census_item1.txt`, `census_item2.txt`, `item2_join.txt`, `item2_leave.txt`, `sample20_item1.txt`, `modal27.txt`, `mutants_item1.txt`, `mutants_item2.txt`, `item5_*.txt`, `seats.py`, `pooldiff.py` and the `atr_*.py` copies). The cantrip code came from `../dec1176-scratch/dec1184/atr_prop.py`. Read them. To reuse one, copy it to `/tmp/dec<N>/` first. Do not write into those folders.
- **Card names.** A real card that your verdict names gets an oracle check first: `uv run python /Users/dpires/Documents/Personal/code/mtg-precon-upgrader/scripts/card_lookup.py "NAME" ...` (it reads the mirror first). A case that you write uses invented names only.
- Run no local e2e. CI ran it on the head.

## R1. CI on the head
- Read `python-tests` run 38965910668 and `web-ci` run 38965910747 on `699cb7e`. If either is still running, wait with a bounded loop in the foreground (`gh run view <id> --json status,conclusion`, a 20 s wait between reads). macOS has no `timeout` command.
- Expected for `python-tests`: `699 passed, 1 skipped, 1242 subtests passed`. That is `main`'s push run 38959080919 on `607dd65` (`693 passed, 1 skipped, 1230 subtests passed`) plus the PR's 6 tests and 12 subtests. PR #79 changed no Python file.
- Expected for `web-ci`: lint `0 errors, 10 warnings`, `Test Files 57 passed (57)`, `Tests 719 passed (719)` and e2e `266 passed`. That is `main`'s push run 38964707867 on `e6d472e`; PR #81 adds no web test.
- Quote the lines. If either run is red, stop and hand back with the failing lines.

## R2. The commits
1. Read each commit on its own (`git show <sha>`) against its item in the DEC-1191 brief. Name any change that the item does not ask for.
2. Compare item 1's new code with `atr_prop.py`: the hand-back says that only fix round 1's lines differ (the `_is_blink` return and `gets?`). Quote what differs.
3. Run `git show --remerge-diff --format=%h 699cb7e`. It prints only the id when the merge holds no hand edit. Quote the output.
4. Check that `a857950` changes only `candidates.json` files (20 files), that no commit changes a `deck.json` or a `metrics.json`, and that no commit holds item 3's code (no "up to" read in `_SPOT_TARGET` or in the bounce read).
5. Check that the first bullet of "Card-draw classification" in `docs/role-taxonomy.md` ends with this sentence, byte for byte: "A draw of one card that the card gives once, such as an enters trigger, cycling or one Clue token, nets 0 too."

## R3. Item 1: a cantrip is not card draw
1. **Census.** Run `classify` over the mirror on `607dd65` and `b125c8f`. The hand-back reads 1,125 cards that leave `card-draw`: 1,099 to none and 26 to `protection`. Quote your table by old and new role, and the hand-back's table by cause next to yours where you can.
2. **Readings.** Read 10 of the hand-back's 20 sampled cards (`sample20_item1.txt`), and 10 others from a seeded draw that leaves out the hand-back's 20, against oracle text, one line each. Give the seed. Read Acrobatic Maneuver, Blur, Siren's Ruse and Splash Portal too. A false card nets 1 card or more, or draws repeatably. The bar is at most 1 false card in 10.
3. **The 27 modal draws.** Check that the 27 cards of `modal27.txt` read `card-draw` on `b125c8f`. Quote the count.
4. **Probes P1 and P2.** Confirm or refute my counts in the Basis. Report each as an N item (ruling 2).
5. **Mutants.** Run the hand-back's M1 to M5. Quote each count line and each failed test, and say whether they match the hand-back. Then run at least four of your own on the added lines. For example: drop `(?! for each)`; drop `\bwhenever\b`; drop `\bat the beginning of (?!the next)`; read `draws? (?:a|one) card\b` in `_is_cantrip` as `draws? a card\b`; drop `draw cards equal to` from `_DRAW`. For each survivor, give a kill case or show that it is equivalent (ruling 6).

## R4. Item 2: a power cut is not removal, and a qualified toughness cut is
1. **Census.** Run `classify` over the mirror on `b125c8f` and `81368f9`. The hand-back reads 93 cards: 45 leave `removal-spot` (39 to none, 5 to `card-draw`, 1 to `protection`), and 48 join from none. Depressurize stays. Quote your table, by part ((a), (b) and (c)) where you can.
2. **Readings.** Read 10 cards that leave and 10 that join, from a seeded draw, against oracle text, one line each. Give the seed. Read these too: Twisted Reflection, Mu Yanling, Celestial Wind, Harald Unites the Elves, Death Match, Depressurize, Defiling Tears and Blood Lust. The bars: among the cards that join, at most 1 false card in 10 (a false card's main use is not to answer a creature of another player); among the cards that leave, at most 1 miss in 10 (a miss kills or answers a creature as its main use).
3. **Mutants.** Run the hand-back's N1 to N6. Quote each count line. Then run at least four of your own on `_TARGET_CREATURE_GETS`, `_TOUGHNESS_CUT` and `_POWER_CUT_KILL`. For example: `{1,40}` as `{1,20}`; drop `;` from the qualifier's class; drop `(?:\. ?)?` (the next sentence); `destroy (?:it|that creature)` as `destroy it`; drop the `x` of `(?:[1-9]\d*|x)`. For each survivor, give a kill case or show that it is equivalent (ruling 6).

## R5. Item 5: the pools, on your tree
1. Link the three inputs. Move all 21 `candidates.json` files out of the tree to a scratch folder. Run `uv run python scripts/generate_candidate_pool.py --all` once; it writes all 21.
2. Compare each new file with the head's file, both with `generated_at` removed (`jq 'del(.generated_at)'`). Expected: 21 of 21 equal. Quote the count. Each file that differs is a B item, with the deck and the field.
3. Run `--all` a second time. Expected: `no change` for all 21. Quote the count of `no change` lines.
4. Run `uv run python scripts/compute_deck_metrics.py --all` once. Expected: `Wrote 0 metrics file(s)`. Quote the line. Then run `git checkout -- data/` and `git status --porcelain`, and quote the empty output.
5. **The scores and the seats.** By your own script, for all 21 decks, against `607dd65`'s files (`e6d472e` holds the same data files): every entry whose score changes also has a new `deck_role`; each seat's `seeded_for_gap` equals its `deck_role`; and the moves match the hand-back's. Those are: 162 entries change `deck_role` (158 `card-draw` to none, 4 `removal-spot` to none), 1 card joins a pool, 0 scores change without a new `deck_role`, and 1 seat moves (Cankerbloom joins exponential-growth as `removal-spot`). Say whether Cankerbloom does the `removal-spot` job.

## R6. The Python suite on your tree
Run `CI=true uv run --with pytest python -m pytest -q -rfEs` with the links and without them. Expected: `700 passed, 1242 subtests passed` with the links, and `699 passed, 1 skipped, 1242 subtests passed` without them. Quote both lines.

## Not in scope
- Items 3 and 4 of DEC-1191, and everything in [DEC-FOLLOW](/DEC/issues/DEC-FOLLOW): "up to N target", the net-zero draws of causes 1 to 4, a repeatable loot, "an additional card", and probes P1 and P2 (ruling 2).
- A detector for damage or for a fight.
- Blinks whose return is in the next sentence.
- "Each creature gets -X/-X" and "enchanted creature gets" with a cut to toughness (N4 of DEC-1192).
- N5 of DEC-1176 (`protection` misses Flicker of Fate, Planar Incision, Spaceshift and Slip On the Ring).
- The named limit of `_is_blink` from fix round 1 of PR #78.

## Yield to a higher leg
After each R item, read your issues with status `todo` (`GET /api/companies/a178baa8-538e-4172-88b9-c0b95e787e56/issues?assigneeAgentId=6ba3ac88-12e8-41a7-834f-98e3d92dae78&status=todo`). If one has priority high or medium, post a short state comment here (the R items done, the next step), and hand back with the Handoff PATCH. The CEO assigns this review back when that leg is out.

## Verdict
Post one comment on this issue. Lead with `APPROVE at 699cb7e` or `CHANGES`. Write short complete sentences, and give each number its basis.
- R1 to R6, each with its figures and its count lines.
- The B items and the N items. P1 and P2 are N items unless ruling 2 says otherwise.
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

planned-by: CEO. Parent: DEC-1191. Source: DEC-1191 hand-back `6934a8d5`.
