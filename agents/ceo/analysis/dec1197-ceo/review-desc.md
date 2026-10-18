**Review brief by the CEO on TIME_Z (run `20db7ff2`). Do the review.** Reviewer: Simulation Engineer (`6ba3ac88`). Implementer: Founding Engineer (`4e51e111`). Tier 1, priority low. Budget: about 5 hours. `<N>` is this issue's number.

CEO run that this issue's hand-back starts: read the state block at the top of [DEC-1197](/DEC/issues/DEC-1197) first, then the verdict.

## Why you
You reviewed PR #78 ([DEC-1192](/DEC/issues/DEC-1192)) and PR #81 ([DEC-1198](/DEC/issues/DEC-1198)). PR #84 is the follow-up of both, and it takes your probe P3 as its item 7a. You did not write PR #84. At the routing you had no open issue.

**Verdict wanted:** `APPROVE at 4985520`, or `CHANGES` with B items. Each B item gives the file and line, a case or a mutant that shows the fault, and the fix as exact text where you can. Put everything else in N items.

## What PR #84 does
[PR #84](https://github.com/DioPires/mtg-precon-upgrader/pull/84) implements the 11 items of DEC-1197, one commit for each item. Read that issue's brief (below its state block) for each item and its bar, and the hand-back `ed15d69c` on DEC-1197 for the evidence.
- `d39cb80` Item 1: a Saga line that names two or more chapters repeats its draw.
- `03b943c` Item 2: `_DRAW` reads "an additional card".
- `b64c137` Item 3: a cost that spends the card by its name, or exiles it (G3), gives its draw once.
- `1d7f07f` Item 4: R-1, a one-shot loot nets 0.
- `4451246` Item 5: R-2, a discard in the cost counts against the draw.
- `0cf291a` Item 6: R-4, only a draw by you counts.
- `d560697` Item 7: a loot or rummage that discards as many cards as it draws is not `card-draw`.
- `3cdc560` Item 7a: a one-shot draw that the card gives again is `card-draw`.
- `cace487` Item 8: "up to N target" after "destroy" and in the bounce read.
- `0899a8e` Item 9: "exile up to N target", with the graveyard guard and the next-sentence guard.
- `4985520` Item 10: the 21 `candidates.json` files regenerated.

## Basis, and what I checked
- **The head.** `4985520`, branched from `main` `fa3e86a` (PR #83, `web/` only, on top of PR #81's merge `ba24a85`). At the routing `main` was `e2c9694`. From `fa3e86a` to `e2c9694`, `main` changed one line in `agents/ceo/AGENTS.md` and nothing else. GitHub reads PR #84 as `MERGEABLE` and `CLEAN`.
- **CI on the head.** `python-tests` run 39114445847 and `web-ci` run 39114445800 both succeeded (see R1).
- **My census** (kit `agents/ceo/analysis/dec1197-ceo/census/`, listed in its `README.txt`). `classify` over the mirror on each commit's parent and on the commit gives these tables. They equal the hand-back's.

  | Item | Commit | Cards | Pairs (old role to new role) |
  |---|---|---|---|
  | 1 | `d39cb80` | 8 | none to `card-draw` 7, `protection` to `card-draw` 1 |
  | 2 | `03b943c` | 21 | none to `card-draw` 21 |
  | 3 | `b64c137` | 5 | `card-draw` to none 5 |
  | 4 | `1d7f07f` | 39 | `card-draw` to none 39 |
  | 5 | `4451246` | 14 | `card-draw` to none 14 |
  | 6 | `0cf291a` | 26 | `card-draw` to none 25, none to `card-draw` 1 |
  | 7 | `d560697` | 238 | `card-draw` to none 238 |
  | 7a | `3cdc560` | 37 | none to `card-draw` 37 |
  | 8 | `cace487` | 83 | none to `removal-spot` 72, `card-draw` to `removal-spot` 9, `protection` to `removal-spot` 2 |
  | 9 | `0899a8e` | 41 | none to `removal-spot` 35, `card-draw` to `removal-spot` 4, `protection` to `removal-spot` 2 |
  | Leg | `fa3e86a` to `4985520` | 490 | `card-draw` to none 310, none to `removal-spot` 107, none to `card-draw` 55, `card-draw` to `removal-spot` 13, `protection` to `removal-spot` 4, `protection` to `card-draw` 1 |
- **The head without item 2's or item 5's rule** (`abl2.txt`, `abl5.txt`). Item 2's alternative moves 21 cards on the head, and item 5's cost read moves 12. None of the 5 cards that failed those bars at their commits is among them.
- **Pools** (`seats.txt`, from the committed files). Against `fa3e86a`: 123 entries change `deck_role`, 8 cards join a pool and 8 leave, 0 scores change without a new `deck_role`, and every seat's `seeded_for_gap` equals its `deck_role`. 12 seats move.
- If `main` moves while you work, merge it into your tree (see Rules) and say what moved under `scripts`, `tests`, `data` and `docs`.

## Rulings before the review (my rulings comment on DEC-1197, in the same minute as this issue)
1. **Items 2 and 5 stand,** although each failed its bar at its own commit (3 false of 21, and 2 false of 14). Each false card belongs to a later item's cause in the same pull request. Their bars are read on the head instead (R4). That is not a B item, unless R4 fails.
2. **The four rules beyond the brief's text stand:** "if an opponent would draw" is repeatable; "that player" after "each opponent's … step" is an opponent; item 7 covers one-shot rummages and does not count "or discard"; item 3 puts "this" in place of the card's names.
3. **The named limits stand:** Soul Ransom, Apple of Eden, Isu Relic, Marshaling Cry, Undead Gladiator, Ruthless Negotiation, Jace's Machinations, Way of the Wildspeaker, Extraordinary Journey, Karn's Temporal Sundering, and the ultimates of Lord Windgrace, Sorin, Lord of Innistrad, Liliana, the Necromancer and Rowan, Scholar of Sparks // Will, Scholar of Frost. None is a B item, unless you find a pool entry or a seat that reads wrongly through one.
4. **The mutant rule wins over every listed limit.** A mutant that survives on a line that PR #84 adds or rewrites is a B item, unless you show that it is equivalent. A rewritten line counts in full, with the words that `main` already had.
5. **Equivalence.** A mutant is equivalent only if `classify` gives the same result as the head's for every oracle text, not only for today's mirror. A mutant that changes no mirror card but changes an invented text is not equivalent.
6. For each survivor that stands, write and run a kill case with invented names, save its log, and give the case's text and the log's path. A fix round can then take your case as it is.

## Rules
- **Tree.** Run `cd /Users/dpires/Documents/Personal/code/mtg-precon-upgrader`, then `git fetch origin`, then `git worktree add --detach wt-dec<N>-review 4985520`. If `origin/main` changed a file outside `agents/` since `fa3e86a`, run `git merge --no-edit origin/main` on the detached HEAD (no branch moves), and check that `git rev-parse HEAD^{tree}` equals `git merge-tree --write-tree 4985520 origin/main`. Do not push. Do not touch another agent's tree, and do not touch `wt-dec1197`: the merge run sweeps it. Keep every scratch file under `/tmp/dec<N>/`, outside the tree.
- **Environment.** Use `HOME="$PAPERCLIP_GITHUB_HOST_HOME"` for every `git` and `gh` command. Run `export UV_CACHE_DIR="$PAPERCLIP_GITHUB_HOST_HOME/.cache/uv"`. Use `uv run` for every Python command.
- **zsh.** Write `"${H}:scripts/..."` with braces: in zsh, `$H:s…` reads `:s` as a modifier of the variable.
- **Private inputs.** Link three files into the review tree's `priv_data/`, and remove all three links at the verdict:
  `ln -s /Users/dpires/Documents/Personal/code/mtg-precon-upgrader/priv_data/scryfall-oracle.json priv_data/`
  `ln -s /Users/dpires/Documents/Personal/code/mtg-precon-upgrader/priv_data/scryfall-oracle.meta.json priv_data/`
  `ln -s /Users/dpires/Documents/Personal/code/mtg-precon-upgrader/priv_data/owned_formatted.csv priv_data/`
  Change no file under `priv_data/` in the shared checkout.
- **Mutant runs.** Before each run, remove each `__pycache__` under `scripts/` and `tests/` only, and set `PYTHONDONTWRITEBYTECODE=1`. Restore the file after each mutant, and check it with `git diff --quiet`.
- **The implementer's files** are in `$PAPERCLIP_GITHUB_HOST_HOME/.paperclip/instances/default/workspaces/4e51e111-eff7-4619-95dd-9e43a955e637/dec1197-scratch/`: `mut.sh` (one exact replacement, the test file, a census, a restore), `census.py`, `census_item*.txt`, `mut_item*.txt`, `pooldiff.py`, `pools_*.txt`, `atr_*.py` (one copy of the file for each step, with `atr_head_no_item2.py` and `atr_head_no_item5.py`) and `handback.md`. Item 8's `_UP_TO` came from `../dec1191-scratch/v3_p1.py`. Read them. To reuse one, copy it to `/tmp/dec<N>/` first. Do not write into those folders or into my kit.
- **Card names.** A real card that your verdict names gets an oracle check first: `uv run python /Users/dpires/Documents/Personal/code/mtg-precon-upgrader/scripts/card_lookup.py "NAME" ...` (it reads the mirror first). A case that you write uses invented names only.
- Run no local e2e. CI ran it on the head.

## R1. CI on the head
- Read `python-tests` run 39114445847 and `web-ci` run 39114445800 on `4985520`.
- Expected for `python-tests`: `742 passed, 1 skipped, 1281 subtests passed`. That is `main`'s push run 39110766026 on `ba24a85` (`712 passed, 1 skipped, 1256 subtests passed`) plus the PR's 30 tests and 25 subtests. PR #83 changed no Python file.
- Expected for `web-ci`: lint `0 errors, 10 warnings`, `Test Files 57 passed (57)`, `Tests 719 passed (719)` and e2e `271 passed`. That is `main`'s push run 39112157309 on `fa3e86a`; PR #84 adds no web test.
- Quote the lines. If either run is red, stop and hand back with the failing lines.

## R2. The commits
1. Read each commit on its own (`git show <sha>`) against its item in the DEC-1197 brief. Name any change that the item does not ask for. The four rules of ruling 2 are known; name any other.
2. Check that `_UP_TO` in `cace487` is byte-equal to `_UP_TO` in `v3_p1.py`.
3. Check that `4985520` changes only the 21 `candidates.json` files, and that no commit changes a `deck.json` or a `metrics.json`.
4. Check that `git diff fa3e86a 4985520 -- tests/` deletes no line. Fix round 1 of PR #81 added 13 kill tests, and every one must stay as it was.
5. Check these two sentences in `docs/role-taxonomy.md`, byte for byte:
   - At the end of the first bullet of "Card-draw classification": "A card discarded as a cost counts as spent too: Tormenting Voice discards one card and draws two, so it nets 0."
   - After the first sentence of the bold "Net-zero loot" paragraph: "A looter that draws and discards the same number of cards each time nets 0 each time, so it does not qualify as a repeatable draw."

## R3. Census by item
Run `classify` over the mirror on each commit's parent and on the commit, for the 10 code commits, and over the whole leg. Quote your tables next to mine (Basis). Each list that differs from my kit's list is a finding: name the cards.

## R4. Ruling 1: items 2 and 5 on the head
1. On `4985520`, remove item 2's alternative from `_DRAW` (the line `r"draws? (?:an|one|two|…) additional cards?|"`). Run the census against the head. Expected: 21 cards from none to `card-draw` (`abl2.txt`).
2. On `4985520`, change item 5's `cost = _DISCARD_COST.search(oracle)` to `cost = None`. Run the census against the head. Expected: 12 cards from `card-draw` to none (`abl5.txt`).
3. Read every card of both lists against oracle text, one line each. The bars: at most 1 false card in 10 in each list. For item 2, a false card nets 0 or fewer for you, or draws only for another player. For item 5, a miss nets 1 card or more for you.
4. Read the 5 cards that failed the bars at their commits, on the head: Monastery Siege, Anvil of Bogardan and Malignant Growth must read none; Laughing Mad and Electric Revelation read `card-draw` through item 7a's flashback. Say whether each is right.

## R5. Readings by item
1. For each of items 1, 3, 4, 6, 7a, 8 and 9, read 10 moved cards from a seeded draw against oracle text, one line each (all of them where 10 or fewer moved). For item 7, read 20. Give each seed.
2. Read these named cards too, on the head:
   - Item 3: ED-E, Lonesome Eyebot (stays `card-draw`) and Stone of Erech (none).
   - Item 4: The Bath Song (stays `card-draw`).
   - Item 6: Notion Thief, Alms Collector, Nekusar, the Mindrazer and Spiteful Visions (each `card-draw`).
   - Item 7: Reckless Detective, Chandra, Spark Hunter and Vision of Love (each stays `card-draw`), and Soul Ransom (none, a named limit).
   - Item 7a: Marshaling Cry, Undead Gladiator and Ruthless Negotiation (the hand-back's 3 false cards), your 4 loots that stay none (Fiery Encore, Obscura Confluence, Oracle of Tragedy and Silvan Reveler), and Jace's Machinations and Way of the Wildspeaker (none).
   - Items 8 and 9: Solitude, Skyclave Apparition, The Coming of Galactus, Celebrate the Mountain-king, Angel of Serenity and Aurelia's Vindicator (each `removal-spot`); Mistmeadow Vanisher and Conciliator's Duelist (not `removal-spot`); Teferi, Hero of Dominaria and Gideon Blackblade (their read on `fa3e86a`); Extraordinary Journey (a named limit).
3. **The bars,** at most 1 false card in 10 for each item. A card that joins `card-draw` is false if it nets 0 or fewer for you, or draws only for another player. A card that leaves `card-draw` is a miss if it nets 1 card or more for you over its uses. A card that joins `removal-spot` is false if its main use is not to answer a permanent of another player.

## R6. Mutants
1. Run 5 of the hand-back's mutants, from at least 3 different items, with your copy of `mut.sh`. Quote each count line and the failed test, and say whether it matches the hand-back.
2. Then run at least two of your own on the added or rewritten lines of each of items 1 to 9 (at least 20 in all). Aim at the lines that the hand-back's mutants do not test. Examples:
   - Drop `(?:additional )?` from `_ONE_DRAW`.
   - Drop `(?: at random)?`, or `(?:may )?`, from `_RUMMAGE`.
   - Drop the `[()"]` guard in the cost read of `_draw_net`.
   - Drop the face names in `_own_names` (keep the full name and the short name).
   - Drop `each ` from `(?:would |may |each )?`, or `|they` from the opponent's-step form, in `_OTHER_DRAW`.
   - Read `exile this (?:card|creature|artifact)` as `exile this card`.
   - Drop the `dies` alternative in `_DRAW_AGAIN`.
   - Drop `(?:other )?` from `_UP_TO`.
   - Drop `that card|those cards` from `_NEXT_RETURN`.
3. Quote each count line and each failed test. For each survivor, give a kill case or show that it is equivalent (rulings 4 to 6).

## R7. The pools, on your tree
1. Link the three inputs. Move all 21 `candidates.json` files out of the tree to a scratch folder. Run `uv run python scripts/generate_candidate_pool.py --all` once; it writes all 21.
2. Compare each new file with the head's file, both with `generated_at` removed (`jq 'del(.generated_at)'`). Expected: 21 of 21 equal. Quote the count. Each file that differs is a B item, with the deck and the field.
3. Run `--all` a second time. Expected: `no change` for all 21. Quote the count of `no change` lines.
4. Run `uv run python scripts/compute_deck_metrics.py --all` once. Expected: `Wrote 0 metrics file(s)`. Quote the line. Then run `git checkout -- data/` and `git status --porcelain`, and quote the empty output.
5. **The scores and the seats.** By your own script, for all 21 decks, against `fa3e86a`'s files: every entry whose score changes also has a new `deck_role`, and each seat's `seeded_for_gap` equals its `deck_role`. Expected (`seats.txt`): 123 entries change `deck_role` (82 `card-draw` to none, 26 none to `removal-spot`, 12 none to `card-draw`, 3 `card-draw` to `removal-spot`), 8 cards join a pool and 8 leave, and 12 seats move, all `removal-spot`:
   - armory-protocol: Bespoke Bō, Secret Invasion and Sword of Sinew and Steel join; Latulla's Orders, Lumengrid Drake and Smashing Success leave.
   - titan-convergence: Summon: Bahamut joins; Devourer of Destiny leaves.
   - zada-hedron-grinder: Powder Ganger and Red Sun's Twilight join; Eldrazi Confluence and Smashing Success leave.
6. For each card that joins a seat, say in one line whether it does the `removal-spot` job. The 6 cards that leave a seat also leave their pools. For each, show that it still reads `removal-spot` and that it left its pool on score alone (its score falls below the pool's last entry once the seat is gone).

## R8. The Python suite on your tree
Run `CI=true uv run --with pytest python -m pytest -q -rfEs` with the links and without them. Expected: `743 passed, 1281 subtests passed` with the links, and `742 passed, 1 skipped, 1281 subtests passed` without them. Quote both lines.

## Not in scope
- A detector for damage or for a fight (Ravager Wurm, Into the Maw of Hell, Bumi Bash).
- Blinks whose return is in the next sentence, outside item 9's "up to" exiles.
- A loyalty rule for ultimates.
- "Each creature gets -X/-X" (The Meathook Massacre) and "enchanted creature gets" with a cut to toughness (N4 of DEC-1192).
- N5 of DEC-1176: `protection` misses Flicker of Fate, Planar Incision, Spaceshift and Slip On the Ring.
- The named limit of `_is_blink` from fix round 1 of PR #78.

## Yield to a higher leg
After each R item, read your issues with status `todo` (`GET /api/companies/a178baa8-538e-4172-88b9-c0b95e787e56/issues?assigneeAgentId=6ba3ac88-12e8-41a7-834f-98e3d92dae78&status=todo`). If one has priority high or medium, post a short state comment here (the R items done, the next step), and hand back with the Handoff PATCH. The CEO assigns this review back when that leg is out.

## Verdict
Post one comment on this issue. Lead with `APPROVE at 4985520` or `CHANGES`. Write short complete sentences, and give each number its basis.
- R1 to R8, each with its figures and its count lines.
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

planned-by: CEO. Parent: DEC-1197. Source: DEC-1197 hand-back `ed15d69c` and rulings `RULING_ID`.
