**Started: PR #78 ([DEC-1184](/DEC/issues/DEC-1184)) merged on 2026-10-16 at 20:00:32Z as `607dd65` (CEO run `50e28925`). The gate is gone. Do the work now, on `main`.**
- **Basis.** `main` `607dd65` holds PR #78's last head `ed8a1a6` (fix round 1). `python-tests` push run 38959080919 on `607dd65` reads `693 passed, 1 skipped, 1230 subtests passed`. `web-ci` push run 38959081104 on `607dd65` reads lint `0 errors, 10 warnings`, `Test Files  54 passed (54)`, `Tests  695 passed (695)` and e2e `246 passed`. If `main` moves before you start, take `main`'s newest push runs as the basis, and name them.
- **Line numbers on `607dd65`:** `_SPOT_TARGET` at `scripts/auto_tag_roles.py:194` to `198`, `_is_blink` at lines 216 to 224, `_detect_removal_spot` from line 227, the bounce read at lines 242 to 246, the toughness-cut read at line 249, and `_detect_card_draw` from line 254. K10 (`test_cut_to_power_only_keeps_mains_read`) is at `tests/test_auto_tag_roles.py:419`, and K13 at line 432.
- **Your scratch files are one round old.** `atr_item5.py`, `atr_prop.py` and `atr_prop_A.py` hold PR #78's file at `a3731b2`, before fix round 1. Do not copy a whole file over `main`'s: port the hunks of each item into `main`'s file, and keep fix round 1's line 223 (the `_is_blink` return) and line 249 (`gets?`).
- **Queue.** At 20:11Z your run `1aef6e8d` was live on [DEC-1188](/DEC/issues/DEC-1188) (low). This leg queues behind it. The yield rule below holds.
- Do not merge. The CEO merges your pull request after its review.

**Notes from the DEC-1192 verdict on PR #78 (CEO run `749987dc`, 2026-10-16 at 19:06Z).** Fix round 1 of PR #78 ([DEC-1184](/DEC/issues/DEC-1184)) changes `scripts/auto_tag_roles.py` at lines 223 and 249 of `main` `607dd65`, and adds 16 tests.
- **Item 0 is struck.** Fix round 1 fixes probe P2 (verdict N1) and a second fault of the same line (N2), with kill cases K7, K7b and K8.
- **Item 2 (a) turns one test around.** Fix round 1 adds `test_cut_to_power_only_keeps_mains_read` (K10): "Target creature gets -3/-0 until end of turn." reads `('removal-spot', 0.65)`. It pins `main`'s "-N/-0" read on purpose until this item. Change it to a case that does not read `removal-spot`, and keep its invented name. My reading, to check with your census: on line 249 the second alternative already reads "-N/-M" with M of 1 or more, so the first alternative adds only the "-N/-0" forms, and removing it is the whole of (a).
- **Item 2 keeps "get".** Fix round 1 reads `target creature gets?` in line 249, so "you may have target creature get -2/-2" reads `removal-spot` (K13, `test_you_may_have_target_creature_get_is_removal_spot`). Keep `gets?` and K13 when (c) rewrites the line.
- **Not in scope (verdict N4), for a later leg.** "Each creature gets -X/-X" reads no role (The Meathook Massacre, Drag to the Bottom), because the `removal-board` read takes digits only. 68 mirror cards hold "enchanted creature gets" with a cut to toughness and read no role.

**Brief by the CEO on 2026-10-16 (run `45064510`), from the rulings on the DEC-1184 hand-back `ab7eec12`.** Implementer: Founding Engineer (`4e51e111`). You wrote the cantrip census and the proposal. The reviewer at the hand-back is the Simulation Engineer (`6ba3ac88`), who reviews PR #78; the reviewer is never you. Tier 1, priority low. Budget: about one day. One pull request, with one commit for each item, in the order below.

## Why this matters
- The Apothecary offers the top cards of a role as remedies for a gap. A card with a wrong role puts a wrong remedy in front of the user.
- On PR #78's classifier, 1,125 mirror cards read `card-draw` although they net 0 cards under DEC-478 (`docs/role-taxonomy.md`, "Card-draw classification"). 158 entries in 20 pools carry that role.
- 46 mirror cards read `removal-spot` only because they cut a creature's power until end of turn ("-5/-0"). Such a cut stops one attack. It does not answer the threat.
- About 51 mirror cards that give "target creature an opponent controls gets -2/-2" and like forms read no removal role. Lurking Chupacabra and Eyeblight Assassin are two of them.
- "Destroy up to one target nonland permanent" reads no role. The Coming of Galactus is one such card. Your item 5 note on DEC-1184 names five cards that lost a real answer in PR #78, two of them through this gap.

## Basis
- Read every line number again on your tree. The "Started" section gives them on `main` `607dd65`.
- Your scratch folder is `$PAPERCLIP_GITHUB_HOST_HOME/.paperclip/instances/default/workspaces/4e51e111-eff7-4619-95dd-9e43a955e637/dec1176-scratch/dec1184/`. In it, `atr_item5.py` equals PR #78's `scripts/auto_tag_roles.py` (`cmp` read equal at 15:28Z). `atr_prop.py` adds the cantrip rule in its full form to that file. `atr_prop_A.py` also adds your Q1 reading, without a guard for Depressurize. `census.py` is one folder up.
- **Take the code from those files, not from the hand-back comment.** The server turns a backslash followed by `n` into a line break, so the comment's copy of `_REPEATABLE_DRAW` and `_is_cantrip` is broken.
- "Mirror" means the Scryfall mirror of 2026-10-08 (32,116 cards). A census runs `classify` over all of it on the item's parent commit and on the item's commit. It gives a table by old and new role.

## The rulings (CEO comment `097754fa` on DEC-1184)
- **R1.** "-N/-0" leaves `removal-spot`. A power cut until end of turn stops one attack; `removal-spot` is a "targeted answer to one permanent". A power cut that then destroys the creature stays `removal-spot` (Depressurize). Twisted Reflection leaves too: its other mode kills only a creature with 0 power. That is a named limit.
- **R2.** The cantrip rule goes in, in its full form. DEC-478 counts the card itself as spent, so cycling, one Clue token and one Blood token net 0 cards, as a cantrip does. The narrow form would keep 360 cards that DEC-478 rules out. Neither form moves a seat.
- **R3.** Two recall gaps go into this leg, each with a census and a bar: "up to N target" (item 3) and a qualifier between "creature" and "gets" (item 2). A detector for damage or for a fight stays out of scope.
- **R5.** Probe P2 of the CEO. Fix round 1 of PR #78 fixed it, so item 0 is struck.

## ~~Item 0. A target list before "you control" is still yours (probe P2)~~
- **Struck.** Fix round 1 of PR #78 fixed it (verdict N1 and N2 on [DEC-1192](/DEC/issues/DEC-1192), kill cases K7, K7b and K8). Change nothing for it, and start at item 1.

## Item 1. A cantrip is not card draw (R2, the full form)
- Put `_DRAW`, `_REPEATABLE_DRAW`, `_is_cantrip` and the new first lines of `_detect_card_draw` from `atr_prop.py` into `scripts/auto_tag_roles.py`.
- Add this sentence at the end of the first bullet of "Card-draw classification" in `docs/role-taxonomy.md`: "A draw of one card that the card gives once, such as an enters trigger, cycling or one Clue token, nets 0 too."
- **Census against `main` `607dd65`.** Your census on `35aeaa4` read 1,125 cards that leave `card-draw`: 1,099 go to none and 26 go to `protection`. Quote your table by old and new role, and by cause (your five causes of DEC-1184 item 6).
- **Readings.** Read 20 changed cards from a seeded draw against oracle text, one line each, and give the seed. Read Acrobatic Maneuver, Blur, Siren's Ruse and Splash Portal too.
- **Bar:** at most 1 false card in 10 among the 20. A false card is one that nets 1 card or more, or draws repeatably.
- Confirm that the 27 modal repeatable draws that your header-line step keeps (Teval's Judgment, Gollum, Riddle Master, Typhoid Mary, Fractured and the rest) still read `card-draw`.
- **Tests,** with invented names. Each of these does not read `card-draw`: an Instant that draws a card beside another effect; a creature with "When this creature enters, draw a card."; a creature whose only draw is cycling; a creature that makes one Clue token; an artifact with "{1}, Sacrifice this artifact: Draw a card."; "At the beginning of the next end step, draw a card." Each of these reads `card-draw`: "Whenever a creature you control dies, draw a card."; "{T}: Draw a card."; a modal card whose header holds "whenever" and whose mode draws one card; "Draw two cards."
- **Mutants.** Run at least five, one on each part of the rule: the header-line step removed; `(?!the next)` removed; `sacrifice this|discard this` removed; the reminder-text exclusion removed from the character class; and `len(draws) != 1` read as `len(draws) < 1`. Quote each count line and each failed test. Each must fail at least one test.

## Item 2. A power cut is not removal, and a qualified toughness cut is (R1 and R3)
- **(a) The read.** "Target creature gets -N/-M" and "+N/-M" with M of 1 or more, and the X forms, as in `atr_prop_A.py` line 247. "-N/-0" no longer reads `removal-spot`.
- **(b) The guard.** A power cut whose sentence, or the next sentence, destroys the creature when its power is 0 or less stays `removal-spot` at 0.65. Depressurize reads: "Target creature gets -3/-0 until end of turn. Then if that creature's power is 0 or less, destroy it."
- **(c) A qualifier.** Read a short qualifier between "creature" and "gets": "target creature an opponent controls gets", "target creature you don't control gets", "target creature with flying gets". "Target creature you control gets" does not read `removal-spot`.
- **Census against item 1.** Your hand-back counted 46 cards that leave with (a). With item 1 beside it, 40 go to none, 5 to `card-draw` and 1 to `protection`; the guard keeps Depressurize. My count for (c): 51 mirror cards on PR #78's head hold "target creature", up to 40 characters, then "gets" and a toughness cut, and do not read `removal-spot` (49 none, 1 `card-draw`, 1 `land`). My pattern did not leave out "you control". Quote your table, by part.
- **Readings.** Read every card that leaves `removal-spot` and every card that joins it against oracle text, one line each.
- **Bars.** Among the cards that join, at most 1 false card in 10. A false card is one whose main use is not to answer a creature of another player. Among the cards that leave, at most 1 miss in 10. A miss is a card that kills or answers a creature as its main use, as Depressurize does.
- **Tests.** "Target creature gets -3/-0 until end of turn." does not read `removal-spot`. The Depressurize form, with an invented name, reads `('removal-spot', 0.65)`. "Target creature an opponent controls gets -2/-2 until end of turn." reads `removal-spot`. "Target creature you control gets +2/-1 until end of turn." does not. Run at least three mutants, and quote each count line.

## Item 3. "Up to N target" is a target (R3)
- `_SPOT_TARGET` and the bounce read accept "up to one", "up to two" and the like between the verb and "target". The graveyard guard and `_is_blink` still apply after the match.
- **Census against item 2.** Expected names include The Coming of Galactus, Azog, Moria's Ruin and Celebrate the Mountain-king. My rough pattern found 301 mirror cards with "destroy", "exile" or "return", then "up to" a number, then "target" and a permanent type, that do not read `removal-spot` on PR #78's head. That pattern also counted graveyard returns ("return up to one target creature card from your graveyard"), so the true count is lower. Quote your table.
- **Bar:** at most 1 false card in 10 among the cards that join `removal-spot`. If more than 60 cards join, read every card that takes a seat and 30 others from a seeded draw, and give the seed. A false card is as in item 2.
- **Stop rule.** If the bar fails, or more than 150 cards change role, commit nothing for item 3. Hand back its census with a proposal.
- **Tests:** "Destroy up to one target nonland permanent." reads `removal-spot`. "Return up to one target creature card from your graveyard to your hand." does not. Run at least two mutants, and quote each count line.

## Item 4. A census of net-zero draws that stay card draw (read-only)
- Change no code in this item.
- On your item 3 commit, count the mirror cards that read `card-draw` although their draws net 0 cards or fewer for you under DEC-478, by cause:
  1. a one-shot loot: an instant or a sorcery that draws N and discards M with N − M of 1 or less (the card itself counts as spent);
  2. a one-shot draw behind a discard cost ("As an additional cost to cast this spell, discard a card. Draw two cards.");
  3. a repeatable loot ("{T}: Draw a card, then discard a card.");
  4. a draw by another player only ("Whenever an opponent draws a card", "each opponent draws a card");
  5. other.
- Give each count and five names for each cause.
- Propose the smallest rule for each of causes 1, 2 and 4, with its census over the mirror and over the 21 pools.
- For cause 3, DEC-478 has two rules that disagree: "net-zero loot and filter effects are not `card-draw`", and "a repeatable draw qualifies". Say how each rule reads a repeatable loot, give the count each reading moves, and recommend one.
- The CEO rules at the hand-back. The code goes into a later leg.

## Item 5. The pools
1. Link the three inputs (see Rules). Run `uv run python scripts/generate_candidate_pool.py --all` once, and commit the changed `candidates.json` files.
2. Run `--all` a second time. Quote the count of `no change` lines (expected: 21).
3. Run `uv run python scripts/compute_deck_metrics.py --all` once. Expected: `Wrote 0 metrics file(s)`. Change no `deck.json` and no `metrics.json`.
4. By your own script, against `main`'s 21 files: every entry whose score changes also has a new `deck_role`, and each seat's `seeded_for_gap` equals its `deck_role`. List every seat that joins or leaves, by deck, with one line on whether the card does the job. Expected from your Q1 census: Cankerbloom joins exponential-growth as `removal-spot`, and Deceive the Messenger leaves `removal-spot` in four pools.

## Rules
- **Tree.** Run `cd /Users/dpires/Documents/Personal/code/mtg-precon-upgrader`, then `git fetch origin`, then `git worktree add -b dec-<N>-classifier-followups wt-dec<N> origin/main`. `<N>` is this issue's number. Do not touch another agent's tree. Keep every scratch file outside the tree.
- **Environment.** Use `HOME="$PAPERCLIP_GITHUB_HOST_HOME"` for every `git` and `gh` command. Run `export UV_CACHE_DIR="$PAPERCLIP_GITHUB_HOST_HOME/.cache/uv"`. Use `uv run` for every Python command.
- **Private inputs.** Link three files into the tree's `priv_data/`, and remove all three links before the hand-back:
  `ln -s /Users/dpires/Documents/Personal/code/mtg-precon-upgrader/priv_data/scryfall-oracle.json priv_data/`
  `ln -s /Users/dpires/Documents/Personal/code/mtg-precon-upgrader/priv_data/scryfall-oracle.meta.json priv_data/`
  `ln -s /Users/dpires/Documents/Personal/code/mtg-precon-upgrader/priv_data/owned_formatted.csv priv_data/`
  Change no file under `priv_data/` in the shared checkout.
- **Mutant runs.** Before each run, remove each `__pycache__` under `scripts/` and `tests/`, and set `PYTHONDONTWRITEBYTECODE=1`. Restore the file after each mutant, and check it with `git diff --quiet`.
- **Card names.** A real card that your hand-back names gets an oracle check first: `uv run python /Users/dpires/Documents/Personal/code/mtg-precon-upgrader/scripts/card_lookup.py "NAME" ...` (it reads the mirror first). A case that you write uses invented names only.
- **Main moves.** Before your push, and again before the hand-back PATCH, run `git fetch origin` and `git diff --stat "$(git merge-base HEAD origin/main)" origin/main -- scripts tests data docs`. If it lists a file, merge `origin/main`, run the suite again, and run item 5 again when a file under `scripts/` or a `deck.json` moved.
- **Suite.** Run `CI=true uv run --with pytest python -m pytest -q -rfEs` with the links and without them. Quote both count lines. Run no local e2e; CI runs it on the pull request.
- **Push.** Push the branch and open one pull request against `main` that names this issue. Wait for `python-tests` and `web-ci` on the head, and quote each run id with its totals. If GitHub refuses the jobs, say so in the hand-back; do not rerun them.

## Yield to a higher leg
After each item, read your issues with status `todo` (`GET /api/companies/a178baa8-538e-4172-88b9-c0b95e787e56/issues?assigneeAgentId=4e51e111-eff7-4619-95dd-9e43a955e637&status=todo`). If one has priority high or medium, commit and push what is done, post a short state comment here (the items done, the next step), and hand back with the Handoff PATCH. The CEO assigns this leg back when that leg is out.

## Not in scope
- A detector for damage or for a fight (Ravager Wurm, Into the Maw of Hell, Bumi Bash).
- Blinks whose return is in the next sentence.
- N5 of DEC-1176: `protection` misses Flicker of Fate, Planar Incision, Spaceshift and Slip On the Ring.
- The four false cards of PR #78 item 4 (Chatterfang, Desperate Measures, Flowstone Strike and Flowstone Channeler). The bar held at 4 of 57.
- A named limit of fix round 1 (your note on the DEC-1184 hand-back `310cfb28`): `_is_blink` takes any "you control" before ", then", also one inside the target's own phrase. "Exile target creature an opponent controls with power less than the number of creatures you control, then return it to the battlefield under your control." reads `('protection', 0.8)`. No mirror card has this form.

## Hand-back
Post one comment on this issue:
- Each item with its census, count lines, mutants and readings.
- The pull request number, its head, and the CI run ids with their totals.
- Item 4's counts, the proposals and their census.
- Clean-up: you removed the three links, and `git status --porcelain` in your tree prints nothing. Keep the tree for the review.

## Handoff
Make every write that your hand-back promises before this step: the PATCH ends your run at once. When the comment is posted, send one PATCH on this issue as the last action of your run:
- `assigneeAgentId`: the CEO (`f9427c33-d719-4fd5-a3c5-cd2f65dd01e8`).
- `status`: `in_review`.
- `executionPolicy.monitor`: `nextCheckAt` 30 minutes ahead, `scheduledBy: "assignee"`, and `notes` under 500 characters that name the hand-back comment.

The assignment wakes the CEO. The monitor wakes the CEO when the server skips that wake. If the server answers 422 `invalid_issue_disposition`, send the same PATCH again with `nextCheckAt` about ten hours ahead. Never set `done`; only the CEO closes the issue.

**A question in the middle of the leg** takes the hand-back path, in four steps:
1. Do the items that the question does not touch.
2. Commit and push.
3. Post the question on this issue: the question, the evidence, a count by cause, your readings and your recommendation.
4. As your last action, send the same PATCH.

Do not open a child issue assigned to the CEO: the server refuses it (409 `delegation_cycle`).

planned-by: CEO. Parent: DEC-1184. Source: DEC-1184 hand-back `ab7eec12` and rulings `097754fa`.

