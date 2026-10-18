**CHANGES. PR #81 at `699cb7e` has 4 B items.** B1 to B3 are surviving mutants on lines that PR #81 adds or rewrites (ruling 5). None of them is equivalent, and each one now has a kill case. B4 is probe P2: through P2, the head reads Campus Crier wrongly in two pools (ruling 2). The fix round needs 13 new tests and a change to one line of code. The kill cases are written and run. All the bars of the brief hold, and R1, R2, R5 and R6 match the hand-back exactly.

- **Kill file:** `/tmp/dec1198/kill/test_dec1198_kill.py`. It holds 4 classes in the style of `tests/test_auto_tag_roles.py`, with invented names only. Paste the classes into that file. Drop the file's `ATR_ROOT` lines, which let the file import from any tree.
- **Its log:** `/tmp/dec1198/kill/kill_run.log`. On the head, the kill file reads `1 failed, 12 passed, 14 subtests passed`. The 1 failure is B4's fault case. Under each surviving mutant, that mutant's own kill test fails. With the B4 fix, the suite's test file plus the kill file read `94 passed, 39 subtests passed`.
- After the fix round, CI's `python-tests` should read `712 passed, 1 skipped, 1256 subtests passed` (699 + 13 tests, 1,242 + 14 subtests).

## B items

**B1. `scripts/auto_tag_roles.py:274` to `289` (`_REPEATABLE_DRAW`, `_is_cantrip`). Six mutants survive.** For each one, the mirror figure is the change against the head's census.
- X1: drop `(?! for each)`. 72 cards go from `card-draw` to none.
- X3: drop `\bat the beginning of (?!the next)`. 129 cards leave `card-draw` (128 to none, 1 to `protection`).
- X4: the cantrip read `draws? (?:a|one) card\b` becomes `draws? a card\b`. No mirror card moves, but the invented text "Draw one card." moves. By ruling 6, that makes X4 not equivalent.
- X6: drop `discard this` from the cost lookahead. 3 cards go from none to `card-draw`: Reinforced Ronin, Action News Crew and Kogla and Yidaro. Each is a channel ability that draws once, outside reminder text.
- X7: `(?!the next)` becomes `(?!the next end step)`. 46 cards go from none to `card-draw`.
- X9: the cantrip read takes "draw" only, not "draws". 27 cards go to `card-draw` (26 from none, 1 from `protection`).
- **Fix:** add the class `CantripKillTests` (6 tests). Its texts, where " / " stands for a line break:
  - X1: Tallyhorn Census, Sorcery, "Draw a card for each creature you control." It reads `('card-draw', 0.85)`.
  - X3: Dawnquill Almanac, Enchantment, "At the beginning of your upkeep, draw a card." It reads `('card-draw', 0.85)`.
  - X4: Mistveil Nudge, Instant, "Tap target creature. / Draw one card." It does not read `card-draw`.
  - X6: Tidewhisper Skiff, Creature, "Flying / {1}{U}, Discard this card: Draw a card." It does not read `card-draw`.
  - X7: Lantern of Tomorrow, Instant, "Tap target creature. / Draw a card at the beginning of the next turn's upkeep." It does not read `card-draw`.
  - X9: Quillfeather Gift, Instant, "You gain 2 life. Target player draws a card." It does not read `card-draw`.

**B2. `scripts/auto_tag_roles.py:268` to `271` (`_DRAW`). Fourteen mutants survive.** `_DRAW` rewrites the first lines of `main`'s `_detect_card_draw`, so all of its words count (ruling 5). The suite has a case only for "a" and "two". Each mutant moves cards from `card-draw` to none. The mirror counts are:
- "draws?" read as "draw": 192.
- One word dropped: "one" 0, "three" 156, "four" 32, "five" 6, "six" 0, "seven" 40, "eight" 1, "nine" 1, "ten" 0, "x" 98, "that many" 91 and `\d+` 0.
- "draw cards equal to" dropped: 72.
- **Fix:** add the class `DrawCountKillTests`. It is one test with 14 subtests, and each subtest reads `('card-draw', 0.85)`:
  - "Target player draws two cards."
  - "Whenever a creature you control dies, draw one card." (an Enchantment)
  - "Draw three cards." through "Draw ten cards.", "Draw X cards." and "Draw 3 cards."
  - "Sacrifice any number of artifacts, then draw that many cards."
  - "Draw cards equal to the number of creatures you control."

**B3. `scripts/auto_tag_roles.py:231` and `237` to `240` (`_TARGET_CREATURE_GETS`, `_POWER_CUT_KILL`). Five mutants survive.**
- Y1: `{1,40}?` becomes `{1,20}?`. 3 cards go from `removal-spot` to none: Weed-Pruner Poplar; Armix, Filigree Thrasher; and Executioner's Swing. Their qualifiers have 24 to 27 characters.
- Y2: drop `;` from the qualifier's character class. No mirror card moves.
- Y4: `destroy (?:it|that creature)` becomes `destroy it`. No mirror card moves.
- Y6: drop the `x` of the guard's `-(?:\d+|x)/-0`. No mirror card moves.
- Y7: the guard reads plain "target creature gets? " and drops the qualifier. No mirror card moves.
- **Fix:** add the class `ToughnessCutKillTests` (5 tests):
  - Y1: Skybane Hex, "Target creature an opponent controls with flying gets -3/-3 until end of turn." It reads `('removal-spot', 0.65)`.
  - Y2: Gloomtether Brute, Creature, "{2}: Tap target creature an opponent controls; this creature gets +2/-2 until end of turn." It does not read `removal-spot`.
  - Y4: Crushing Tide, "Target creature gets -3/-0 until end of turn. Then if that creature's power is 0 or less, destroy that creature." It reads `('removal-spot', 0.65)`.
  - Y6: Wilting Undertow, "Target creature gets -X/-0 until end of turn, where X is the number of cards in your hand. Then if that creature's power is 0 or less, destroy it." It reads `('removal-spot', 0.65)`.
  - Y7: Brineclutch Horror, Creature, "When this creature enters, target creature an opponent controls gets -3/-0 until end of turn. Then if that creature's power is 0 or less, destroy it." It reads `('removal-spot', 0.65)`.

**B4. `scripts/auto_tag_roles.py:275`: probe P2 reads a card in a pool wrongly (ruling 2).**
- **The fault.** Campus Crier reads `card-draw` on the head in anvil-chorus (score 50.4) and stampede-acres (score 49.9). Its text is "{1}, Exile this card from your graveyard: Empower Jace 2. (…"[−3]: Draw a card.")". Its only draw is the Jace token's −3, in reminder text. Two loyalty counters cannot pay −3, so the card nets 0. In item 1, 21 other "empower Jace" cards leave `card-draw`. Campus Crier stays only because the cost "exile this card from your graveyard" looks like a repeatable cost. This is not a regression: it read `card-draw` on `607dd65` too.
- **Fix (exact text).** In `_REPEATABLE_DRAW`, replace `(?!sacrifice this|discard this)` with `(?!sacrifice this|discard this|exile this card from your graveyard)`. The candidate file is `/tmp/dec1198/snap/atr_fix_p2.py`.
- **Census against the head.** 10 cards go from `card-draw` to none: Campus Crier, Cobbled Lancer, Faerie Dreamthief, Glitch Ghost Surveyor, Goblin Surveyor, Leonin Surveyor, Loxodon Surveyor, Mutant Surveyor, Unwilling Ingredient and White Tiger, Amulet Keeper. I read all 10. Each draws one card, once, from the graveyard, so 0 are false.
- **Pools.** I built the pools in memory with the implementer's `pooldiff.py`. 2 entries change (Campus Crier goes to none in both pools), and 0 seats move. The fix round regenerates those 2 `candidates.json` files.
- **Fault case.** Ashveil Courier, Creature, "Menace / {2}{B}, Exile this card from your graveyard: Draw a card." It does not read `card-draw` (`GraveyardCostFaultTests`). It fails on the head and passes with the fix.
- The name form ("sacrifice <the card's name>": Stone of Erech, ED-E) needs the card's name, and no pool holds such a card. It stays item 3 of DEC-1197.

## R1. CI on the head
Both runs are `completed`/`success` on `headSha` `699cb7e04a89…`.
- `python-tests` 38965910668: `699 passed, 1 skipped, 1242 subtests passed`.
- `web-ci` 38965910747: lint `✖ 10 problems (0 errors, 10 warnings)`, `Test Files  57 passed (57)`, `Tests  719 passed (719)` and e2e `266 passed`.
- All four totals are as expected.

## R2. The commits
1. Each commit holds only its item:
   - `b125c8f` changes 3 files: docs, scripts and tests. Its departures are the ones ruled to stand.
   - `81368f9` changes 2 files: scripts and tests. Its departure, the comma rule with Giantsbane Fury, was ruled to stand. The qualifier also stops at `;`. The hand-back names this, but no ruling covers it. B3's case Y2 now pins it.
   - `a857950` changes the `candidates.json` files only.
2. `diff atr_prop.py` against `b125c8f`'s file shows two hunks only:
   - Lines 221 to 223: the `_is_blink` return now reads `re.match(r"(?:[^,]|,(?! then\b))*? you (?:control|own)\b", oracle[t.start():r.start()])`. `atr_prop.py` read `re.match(r"[^,]*? you (?:control|own)\b", oracle[t.end():r.start()])`.
   - Lines 248 and 249: `target creature gets? (` against `target creature gets (`, with one comment line.
   - Both are fix round 1's lines, as the hand-back says.
3. `git show --remerge-diff --format=%h 699cb7e` printed `699cb7e` only. The head's tree is `3797082a`, which equals `git merge-tree --write-tree e6d472e a857950`.
4. These checks hold:
   - `a857950` changes 20 files, all `candidates.json`.
   - From `607dd65` to `a857950`, the only other files are `docs/role-taxonomy.md`, `scripts/auto_tag_roles.py` and `tests/test_auto_tag_roles.py`. No `deck.json` and no `metrics.json` changes.
   - The scripts diff holds no "up to". `_SPOT_TARGET` (lines 194 to 198) and the bounce read (line 259) hold no "up to" either.
   - From `607dd65` to `e6d472e`, `main` changed 35 files, all under `web/`.
5. `docs/role-taxonomy.md:50` ends with the sentence byte for byte. A Python `bytes.endswith` check returned `True`.

## R3. Item 1
1. **Census, `607dd65` to `b125c8f`.** `cards 32116 changed 1125`: `card-draw -> None: 1099` and `card-draw -> protection: 26`. My list equals `census_item1.txt` (`diff` printed nothing).
   - **By cause.** I ran a copy of the implementer's `causes.py`. Its JSON equals the implementer's byte for byte. The table equals the hand-back's:
     - Cause 1: 322 to none and 13 to `protection`.
     - Cause 2: 413 and 5, and 4 stay.
     - Cause 3: 1,625 stay (962 "whenever", 170 "at the beginning of" and 493 activated).
     - Cause 4: 669 stay.
     - Cause 5: cycling 182 and 5; reminder text 170 and 3; another player 12, with 69 staying; two or more one-card draws, 24 stay.
   - The whole head against `607dd65` reads 1,217 changes, the same as your census (1,098 / 26 / 1 / 39 / 5 / 1 / 47).
2. **Readings, seed 1198.**
   - 10 of the implementer's 20, drawn with `random.Random(1198).sample` over the sorted 20: Primoc Escapee, Revel Ruiner, Imaginary Threats, Revitalize, The Sackville-Bagginses, Intimidation Tactics, Mezzio Mugger, Skyscanner, Crash Through and Ray of Erasure. All 10 are right. Mezzio Mugger is a near case: its attack trigger gives card access, not a draw.
   - 10 others, drawn with the same seed over the sorted 1,105 names that leave out the 20:
     - Right: Oracle of Tragedy (a loot that nets 0), Rhox Oracle, Fleeting Memories (one Clue), Gempalm Strider (cycling), Selvala's Charge (each player draws once), That's Rough Buddy, Reality Anchor, Dazzling Beauty (a delayed draw, once) and Courageous Resolve (to `protection`).
     - **False: Secrets of the Key.** Its flashback investigates twice. The card gives 3 Clues in all and nets +2.
   - **Bar: 1 false card in 20 (0.5 in 10), so the bar holds.** The 10 others alone sit at the bar (1 in 10).
   - Acrobatic Maneuver, Blur and Siren's Ruse go to `protection`, and Splash Portal goes to none. All four are right.
3. **The 27 modal draws:** all 27 read `card-draw` on `b125c8f` (27 on `607dd65` too).
4. **Probes P1 and P2:** my counts confirm yours; see N-a and N-b.
5. **Mutants.**
   - I ran M1 to M5 on the head. Each fails the same subtest as in the hand-back, and the mirror counts are the same:
     - M1: Skyrider Courier, 27 cards.
     - M2: Dusktide Stall, 64.
     - M3: Brassleaf Trinket, 70 (69 + 1).
     - M4: Tomeshade Heron, 22.
     - M5: Echoing Augury, 65.
   - Each count line reads `1 failed, 81 passed, 24 subtests passed`, where the hand-back reads `77 passed`. The difference is item 2's 4 tests, which the head's file holds.
   - Mine: X2 (drop `\bwhenever\b`) fails 2 subtests and moves 795 cards. X11 (drop the `^` of the cost alternative) fails 4 subtests and moves 352. X8 is equivalent; see N-g. The survivors are B1 and B2.

## R4. Item 2
1. **Census, `b125c8f` to `81368f9`.** `cards 32116 changed 93`: 48 none to `removal-spot`; 39 `removal-spot` to none; 5 to `card-draw`; 1 to `protection`.
   - By part, from two files that I built between the commits:
     - (a) 46 cards leave: 40 to none, 5 to `card-draw` and 1 to `protection`.
     - (b) 1 card comes back: Depressurize.
     - (c) 48 cards join.
   - My lists equal `item2_join.txt` and `item2_leave.txt`.
2. **Readings, seed 1198.**
   - Cards that leave: Hydrosurge, Take the Fall, Lost in a Labyrinth, Code of Constraint, Shrink, Startle, Constricting Tendrils, Stream of Unconsciousness, Protect // Serve and Mu Yanling, Celestial Wind. **0 misses in 10.** Mu Yanling is a near case and a named limit: its −3 is a bounce of two creatures.
   - Cards that join: Grim Physician, Splatter Goblin, Invasion of Innistrad // Deluge of the Dead, Shambling Goblin, Skulking Killer, Lurking Chupacabra, Drana's Silencer, Tooth Collector, Orc Sureshot and Death Match. **0 false in 10.** Death Match is a near case: each player can use it.
   - The named cards:
     - Twisted Reflection is a miss and a named limit.
     - Harald Unites the Elves is false and a named limit.
     - Depressurize stays `removal-spot`.
     - Defiling Tears and Blood Lust read none, which is right.
3. **Mutants.**
   - N1 to N6 match the hand-back: the same count line `1 failed, 80 passed, 25 subtests passed`, the same failed tests, and the same mirror counts (62, 1, 1, 48, 1 and 2).
   - Mine: Y3 (drop `(?:\. ?)?`), Y5 (drop the `x` of the toughness cut), Y12 (the guard's power cut reads `-X` only) and Y13 (drop the guard's first character class) are killed. Y8 to Y11 are equivalent; see N-g. The survivors are B3.
   - Logs: `/tmp/dec1198/mut_item1_head.log`, `mut_item1b_head.log` and `mut_item2_head.log`.

## R5. Item 5: the pools, on my tree
1. I moved all 21 files out of the tree. `--all` then printed 21 `wrote` lines.
2. **21 of 21 files equal** the head's with `generated_at` removed (`jq -S 'del(.generated_at)'` and `cmp`).
3. The second `--all` printed **21 `no change` lines** and 0 `wrote` lines.
4. Metrics printed `Wrote 0 metrics file(s) (weights=A).` After `git checkout -- data/`, `git status --porcelain` printed nothing.
5. **My script** (`/tmp/dec1198/pools.py`) compared the regenerated files with `607dd65`'s. It gives the same output for the committed files, and `git diff --stat 607dd65 e6d472e -- data` printed nothing.
   - 4,104 entries are in both files, and 0 scores change.
   - 162 entries change `deck_role`: 158 `card-draw` to none and 4 `removal-spot` to none (Deceive the Messenger).
   - 1 card joins a pool, and 0 leave.
   - Of 36 seats, 0 have `seeded_for_gap` different from `deck_role`.
   - 1 seat moves: Cankerbloom joins exponential-growth as `removal-spot`.
   - All of this matches the hand-back.
   - **Cankerbloom does the job.** "{1}, Sacrifice this creature: Choose one — Destroy target artifact; destroy target enchantment; proliferate." It is a targeted answer to one permanent, and its proliferate mode fits the deck.
6. **Beyond the brief, I read all 70 names behind the 162 entries.** See N-c and N-d.

## R6. The suite on my tree
- With the links: `700 passed, 1242 subtests passed in 19.35s`.
- Without them: `699 passed, 1 skipped, 1242 subtests passed in 19.91s`. The skip is `tests/test_validate_deck_card_names.py:124: local Scryfall mirror is generated by scripts/refresh_scryfall_mirror.py`.

## N items
- **N-a. P1 is confirmed.**
  - My pattern finds 12 mirror cards with a line that names two or more chapters and holds a draw. 11 of them read `card-draw` on `607dd65`. The 12th, Vault 11: Voter's Dilemma, reads `removal-board` on both commits.
  - 8 of the 11 leave `card-draw` on the head. 5 of the 8 net +1 card or more: your five.
  - None of the 5 is in a pool. The Modern Age // Vector Glider is in 2 pools and leaves `card-draw`; that is right, because it loots.
- **N-b. P2 is confirmed.** 14 cards match, and 13 read `card-draw` on the head; Five Hundred Year Diary reads `ramp`. Its graveyard form goes to B4. Its name form stays in DEC-1197.
- **N-c. P3 (my probe): a draw that the card gives more than once, through a word that `_is_cantrip` does not read.**
  - 5 pool cards (7 entries) leave `card-draw` wrongly on the head, and 0 seats move:
    - Season of Weaving (tidal-legion): "You may choose the same mode more than once."
    - Ominous Harvest (witherbloom-the-balancer): gravestorm.
    - Striding Shotcaller // Run the Play (creeping-corruption and exponential-growth): it becomes prepared on each combat damage.
    - Killian's Confidence (creeping-corruption): it returns to your hand.
    - Ichor Wellspring (anvil-chorus and grave-dividends): "enters or is put into a graveyard".
  - Mirror cards outside the pools: Secrets of the Key and Think Twice (flashback), Whispers of the Muse (buyback), Last Thoughts (cipher) and Detective's Satchel (investigate twice).
  - **I list P3 as N, not B, for this reason.** A narrow rule (`_DRAW_AGAIN` in `/tmp/dec1198/snap/atr_fix_p3.py`) moves 20 cards from none to `card-draw`. Of those, 13 are right and 2 are near cases (Eldrazi Ravager and Hormagaunt Horde). **5 are false, and all 5 are loots or rummages:** Fiery Encore, Obscura Confluence, Oracle of Tragedy, Silvan Reveler and Undead Gladiator. That is 2.5 in 10, so the rule fails the bar until DEC-1197's loot rules land. In memory, the rule restores the 7 entries, also moves Eldrazi Ravager in titan-convergence, and moves 0 seats.
  - **Recommendation:** make P3 a DEC-1197 item after its loot items, and add flashback, buyback, cipher, escape, harmonize and "investigate twice" to it. By the test of ruling 2 it would be a B item; rule it into this fix round if you want it there.
- **N-d. Pool reading.** Of the 69 names that lose `card-draw` in a pool, 5 are false (N-c) and 2 are near cases. The near cases are Jace's Machinations (3 pools; Empower Jace 8) and Way of the Wildspeaker (1 pool; Empower Jace 7). Each lets the Jace token use −3 twice, so each nets +1. The other 62 are right.
- **N-e. Named limits, as ruled:** Twisted Reflection (entwined), Mu Yanling, Celestial Wind, Harald Unites the Elves and Death Match.
- **N-f. `main` and the other open pull request.** At the verdict, `origin/main` is still `e6d472e`, and PR #81's head is `699cb7e` (`MERGEABLE`). PR #82 (DEC-1199) opened at 08:56:51Z. It changes 8 files, all under `web/`, so it shares no file with PR #81.
- **N-g. The equivalent mutants.** Each is equivalent for every text, not only for the mirror.
  - X8 (`len(draws) != 1` read as `> 1`): `_is_cantrip` is called only at line 293, after `_DRAW.search` matched, so `len(draws)` is at least 1.
  - Y8 (`[1-9]\d*` read as `[1-9]`): the group ends `_TOUGHNESS_CUT`, which is used only for `.search()` truth at line 263. A match of either form gives a match of the other at the same start.
  - Y9 (lazy `{1,40}?` read as greedy) and Y11 (the guard's lazy class read as greedy): greediness changes which match is found, not whether one exists. Both patterns are used only for `.search()` truth.
  - Y10 (`(?:\. ?)?` read as `(?:\.)?`): the next class takes the space.

## Clean-up
- I removed the three links, `.pytest_cache` and each `__pycache__`. `git status --porcelain --ignored` printed nothing.
- I ran `git worktree remove …/wt-dec1198-review` (exit 0, without `--force`) and `git worktree prune`. The tree had a detached HEAD, so there was no branch to delete.
- **Removed:** `wt-dec1198-review`. **Not touched:** `wt-dec1191` (the merge needs it) and `wt-dec1199` (another agent's).
- `/tmp/dec1198/` stays, for the fix round: the kill file, its log, the mutant logs, the censuses and the two candidate fix files.
