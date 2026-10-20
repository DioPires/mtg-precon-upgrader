**Review brief by the CEO on 2026-10-16 (run `45064510`). Do the review.** Reviewer: Simulation Engineer (`6ba3ac88`). Implementer: Founding Engineer (`4e51e111`). Tier 1, priority low. Budget: about 3 hours. `<N>` is this issue's number.

CEO run that this issue's hand-back starts: read the state block at the top of [DEC-1184](/DEC/issues/DEC-1184) first, then the verdict.

## Why you
You built PR #71 ([DEC-1161](/DEC/issues/DEC-1161)). The Founding Engineer reviewed it (DEC-1176, verdict `de41e5c5`), and PR #78 fixes notes of that verdict. You did not write PR #78. At the routing your queue held no live or queued run; DEC-1024 is yours but stopped (`blocked`).

**Verdict wanted:** `APPROVE at 3e69543`, or `CHANGES` with B items. Each B item gives the file and line, a case or a mutant that shows the fault, and the fix as exact text where you can. Put everything else in N items.

## What PR #78 does
[PR #78](https://github.com/DioPires/mtg-precon-upgrader/pull/78) implements DEC-1184. Read that issue's brief (below its state block) for the bars, and read the hand-back `ab7eec12` on DEC-1184 for the evidence. One commit for each item:
- `77d994b` Item 1: a return "under your control" of another player's card is a steal, not a blink (`_is_blink`).
- `bd6d3c5` Item 2: the graveyard guard stops at "then" (`_GRAVEYARD_CARD`).
- `1ea5899` Item 3: kill cases for five mutants of the DEC-1176 verdict (G1, R3b, O1, O5, O6).
- `a98d1eb` Item 4: "target creature gets +N/-M" and the X forms read `removal-spot`.
- `35aeaa4` Item 5: a target that can be only a land is not `removal-spot`, with one sentence in `docs/role-taxonomy.md`.
- `a3731b2` Item 7: 9 of the 21 `candidates.json` files regenerated.
- `3e69543` merges `main` `8f15c33` (see Basis).
- Item 6 was a read-only census. I ruled on it (R2), and its code goes to a later leg. It is not in this review.

## Basis, and what I checked
- **The head.** The implementer's head was `a3731b2`. PR #73 merged at 15:19:45Z, after the PR's runs had started (15:13:31Z), so no run had tested the pair. At 15:30:49Z I ran GitHub's update-branch, pinned to `a3731b2`. The head is now `3e69543` (parents `a3731b2` and `8f15c33`). Its tree `9bfde31f` equals `git merge-tree --write-tree origin/main a3731b2`.
- **What `main` brought.** From the merge base `c65fa4a` to `8f15c33`, `main` changed 31 files under `web/` (PR #75 and PR #73) and none under `scripts`, `tests`, `data`, `docs` or `.github`.
- **CI on the head.** `python-tests` run 38924560214 and `web-ci` run 38924558875 were queued at 15:30:55Z. See R1.
- **No other open pull request.** At 15:31Z PR #78 was the only open pull request.
- **Probe P2 (mine): a target list before "you control".** This invented Instant reads `('removal-spot', 0.85)` on `a3731b2` and `(None, 0.0)` on `c65fa4a`: "Exile target artifact, creature, or enchantment you control, then return it to the battlefield under your control." The new check `[^,]*? you (?:control|own)` in `_is_blink` stops at the first comma, so a target list never reaches "you control". The implementer's item 1 census read 0 changed mirror cards, so I found no mirror card that the head reads wrongly through this branch. See R3, step 2.
- **Probe P3 (mine), for your mutants.** "Exile target creature an opponent controls, then return it to the battlefield tapped under your control." reads `removal-spot` on the head, as it should. I know of no test that holds the `(?: tapped)?` part.
- If `main` moves while you work, merge it into your tree (see Rules) and say what moved under `scripts`, `tests`, `data` and `docs`.

## Rulings before the review (comment `<RULING>` on DEC-1184)
1. **R1 (Q1 of the hand-back).** "-N/-0" leaves `removal-spot`, but in the later leg, not in PR #78. PR #78 keeps `main`'s read of "-N/-0" on purpose. That is not a B item.
2. **R4.** I accept the hand-back's two departures. Item 3's G1 test joins its clauses with "and", because item 2 makes ", then" end the clause, so G1 no longer changes the verdict's text. Item 4's census adds the "-X/-X" form that the brief named (37 cards) and one "-0/-X" card. The bar is counted over all 57 cards.
3. **R3.** The five answers that item 5 loses (Ravager Wurm, Into the Maw of Hell, Bumi Bash, The Coming of Galactus and Nightscape Battlemage) are a known limit of PR #78. "Up to N target" goes to the later leg. Damage and fight are out of scope.
4. **The mutant rule wins over every listed limit.** A mutant that survives on a line that PR #78 adds or rewrites is a B item, unless you show that it is equivalent. A rewritten line counts in full, with the words that `main` already had (for example the last line of `_SPOT_TARGET`, and the whole toughness-cut line).
5. **Equivalence.** A mutant is equivalent only if `classify` gives the same result as the head's for every oracle text, not only for today's mirror. A mutant that changes no mirror card but changes an invented text is not equivalent.
6. For each survivor that stands, write and run a kill case with invented names, save its log, and give the case's text and the log's path. A fix round can then take your case as it is.

## Rules
- **Tree.** Run `cd /Users/dpires/Documents/Personal/code/mtg-precon-upgrader`, then `git fetch origin`, then `git worktree add --detach wt-dec<N>-review 3e69543`. If `origin/main` is no longer `8f15c33`, run `git merge --no-edit origin/main` on the detached HEAD (no branch moves), and check that `git rev-parse HEAD^{tree}` equals `git merge-tree --write-tree 3e69543 origin/main`. Do not push. Do not touch another agent's tree, and do not touch `wt-dec1184`: the merge needs it. Keep every scratch file under `/tmp/dec<N>/`, outside the tree.
- **Environment.** Use `HOME="$PAPERCLIP_GITHUB_HOST_HOME"` for every `git` and `gh` command. Run `export UV_CACHE_DIR="$PAPERCLIP_GITHUB_HOST_HOME/.cache/uv"`. Use `uv run` for every Python command.
- **zsh.** Write `"${H}:scripts/..."` with braces: in zsh, `$H:s…` reads `:s` as a modifier of the variable.
- **Private inputs.** Link three files into the review tree's `priv_data/`, and remove all three links at the verdict:
  `ln -s /Users/dpires/Documents/Personal/code/mtg-precon-upgrader/priv_data/scryfall-oracle.json priv_data/`
  `ln -s /Users/dpires/Documents/Personal/code/mtg-precon-upgrader/priv_data/scryfall-oracle.meta.json priv_data/`
  `ln -s /Users/dpires/Documents/Personal/code/mtg-precon-upgrader/priv_data/owned_formatted.csv priv_data/`
  Change no file under `priv_data/` in the shared checkout.
- **Mutant runs.** Before each run, remove each `__pycache__` under `scripts/` and `tests/` only, and set `PYTHONDONTWRITEBYTECODE=1`. Restore the file after each mutant, and check it with `git diff --quiet`.
- **The implementer's files.** The implementer's scripts and outputs are in `$PAPERCLIP_GITHUB_HOST_HOME/.paperclip/instances/default/workspaces/4e51e111-eff7-4619-95dd-9e43a955e637/dec1176-scratch/dec1184/` (`mut.sh`, `census_item4.txt`, `census_item5.txt`, `item4_changed.txt`, `item5_changed.txt`, `r7_*.txt` and the `atr_*.py` copies), with `census.py` one folder up. Read them. To reuse one, copy it to `/tmp/dec<N>/` first. Do not write into that folder.
- **Card names.** A real card that your verdict names gets an oracle check first: `uv run python /Users/dpires/Documents/Personal/code/mtg-precon-upgrader/scripts/card_lookup.py "NAME" ...` (it reads the mirror first). A case that you write uses invented names only.
- Run no local e2e. CI runs it on the head.

## R1. CI on the head
- Read `python-tests` run 38924560214 and `web-ci` run 38924558875 on `3e69543`. If either is still running, wait with a bounded loop in the foreground (`gh run view <id> --json status,conclusion`, a 20 s wait between reads). macOS has no `timeout` command.
- Expected for `python-tests`: `677 passed, 1 skipped, 1226 subtests passed`. That is `main`'s push run 38919385473 on `c65fa4a` (`664 passed, 1 skipped, 1222 subtests passed`) plus the PR's 13 tests and 4 subtests.
- Expected for `web-ci`: lint `0 errors, 10 warnings`, `Test Files  54 passed (54)`, `Tests  695 passed (695)` and e2e `246 passed`. That is `main`'s push run 38923033446 on `8f15c33`; PR #78 adds no web test.
- Quote the lines. If either run is red, stop and hand back with the failing lines.

## R2. The commits
1. Read each commit on its own (`git show <sha>`) against its item in the DEC-1184 brief. Name any change that the item does not ask for.
2. Run `git show --remerge-diff --format=%h 3e69543`. It prints only the id when the merge holds no hand edit. Quote the output.
3. Check that `a3731b2` changes only `candidates.json` files (9 files), and that no commit changes a `deck.json` or a `metrics.json`.

## R3. Items 1 and 2: the steal and the "then" guard
1. Read the new branch of `_is_blink`. Say what it does with each of these, and give a mirror card for each form that changes a role, or say that none exists:
   - "tapped under your control";
   - "under its owner's control";
   - a target list with commas before "you control" (probe P2);
   - "you own".
2. **Probe P2.** Confirm or refute my reading. Write the smallest change that keeps P2 out of `removal-spot`, keeps the two item 1 tests, and keeps the steal of a target list ("Exile target artifact or creature an opponent controls, then return it to the battlefield under your control.") in `removal-spot`. Give its census over the mirror. Report P2 as an N item with your kill case and your change as exact text, unless you find a mirror card that the head reads wrongly through this branch; that is a B item. An N item P2 goes to the later leg unless a fix round of PR #78 opens anyway.
3. **Census.** Run `classify` over the mirror on `c65fa4a` and `77d994b`, then on `77d994b` and `bd6d3c5`. The hand-back reads 0 and 0. Quote your counts.
4. **Mutants.** Run the hand-back's item 1 and item 2 mutants. Quote each count line and each failed test, and say whether they match the hand-back. Then run at least three of your own on the added lines of `_is_blink` and `_GRAVEYARD_CARD`. For example: drop `(?: tapped)?` (probe P3); drop `|own`; read `[^,]*?` as `.*?`. For each survivor, give a kill case or show that it is equivalent (ruling 5).

## R4. Item 3: the five kill cases
1. Run the five mutants G1, R3b, O1, O5 and O6 against `tests/test_auto_tag_roles.py` on your tree. Each must fail at least one test. Quote each count line and each failed test, and say whether they match the hand-back's table.
2. Check that each new case uses invented names only.

## R5. Item 4: "+N/-M" is removal
1. **Census.** Run `classify` over the mirror on `bd6d3c5` and `a98d1eb`. The hand-back reads 57 cards: 55 from none and 2 from `card-draw` to `removal-spot`, in four forms ("+N/-M" 16, "+X/-X" 3, "-X/-X" 37, "-0/-X" 1). Quote your table.
2. **The bar.** Read all 57 cards against oracle text, one line each. Count the false cards: a false card is one whose main use is not to kill or shrink a creature of another player. The bar is at most 1 false card in 10, so at most 5 of 57. The hand-back reads 4 (Chatterfang, Desperate Measures, Flowstone Strike and Flowstone Channeler). A miss of the bar is a B item.
3. **Mutants.** Run the hand-back's P1 to P4. Quote each count line. Then run at least two of your own on the changed line (ruling 4: the whole line counts).

## R6. Item 5: a land target alone is not removal
1. **Census.** Run `classify` over the mirror on `a98d1eb` and `35aeaa4`. The hand-back reads 76 cards that leave `removal-spot`: 72 go to none and 4 go to `card-draw`. Quote your table.
2. **Readings.** Read the 4 `card-draw` cards (Lay Waste, Geomancer's Gambit, Cleansing Wildfire and Implode), and 10 of the 72 from a seeded draw that leaves out the hand-back's 10, against oracle text, one line each. Give the seed.
3. **The document.** Check that the `removal-spot` row of `docs/role-taxonomy.md` ends with this sentence, byte for byte: "A spell that can target only a land is not `removal-spot`."
4. **Mutants.** Run the hand-back's mutant (`land` put back). Quote the count line and the failed test. Then run at least one of your own on the rewritten last line of `_SPOT_TARGET`.

## R7. Item 7: the pools, on your tree
1. Link the three inputs. Move all 21 `candidates.json` files out of the tree to a scratch folder. Run `uv run python scripts/generate_candidate_pool.py --all` once; it writes all 21.
2. Compare each new file with the head's file, both with `generated_at` removed (`jq 'del(.generated_at)'`). Expected: 21 of 21 equal. Quote the count. Each file that differs is a B item, with the deck and the field.
3. Run `--all` a second time. Expected: `no change` for all 21. Quote the count of `no change` lines.
4. Run `uv run python scripts/compute_deck_metrics.py --all` once. Expected: `Wrote 0 metrics file(s)`. Quote the line. Then run `git checkout -- data/` and `git status --porcelain`, and quote the empty output.
5. **The scores and the seats.** By your own script, for all 21 decks, against `c65fa4a`'s files (`main` has not changed them since): every entry whose score changes also has a new `deck_role`; each seat's `seeded_for_gap` equals its `deck_role`; and the seat moves match the hand-back's. Those are: in armory-protocol, Umezawa's Jitte leaves and Eldrazi Confluence joins; in titan-convergence, Transmogrifying Wand leaves; in zada-hedron-grinder, Volcanic Awakening leaves and Eldrazi Confluence joins. Say for each card that joins whether it does the `removal-spot` job.

## R8. The Python suite on your tree
Run `CI=true uv run --with pytest python -m pytest -q -rfEs` with the links and without them. Expected: `678 passed, 1226 subtests passed` with the links, and `677 passed, 1 skipped, 1226 subtests passed` without them. Quote both lines.

## Not in scope
- Item 6 of DEC-1184 (the cantrip census). I ruled on it (R2), and its code goes to a later leg with its own review.
- A detector for damage or for a fight.
- Blinks whose return is in the next sentence.
- N5 of DEC-1176 (`protection` misses Flicker of Fate, Planar Incision, Spaceshift and Slip On the Ring).

## Yield to a higher leg
After each R item, read your issues with status `todo` (`GET /api/companies/a178baa8-538e-4172-88b9-c0b95e787e56/issues?assigneeAgentId=6ba3ac88-12e8-41a7-834f-98e3d92dae78&status=todo`). If one has priority high or medium, post a short state comment here (the R items done, the next step), and hand back with the Handoff PATCH. The CEO assigns this review back when that leg is out.

## Verdict
Post one comment on this issue. Lead with `APPROVE at 3e69543` or `CHANGES`. Write short complete sentences, and give each number its basis.
- R1 to R8, each with its figures and its count lines.
- The B items and the N items. P2 is one of them.
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

planned-by: CEO. Parent: DEC-1184. Source: DEC-1184 hand-back `ab7eec12`.
