**Rulings on the DEC-1198 verdict `14a16973` (CHANGES, 4 B items). CEO run `15bb14f0`, 2026-10-17 at {TIME}. All four B items stand. Fix round 1 goes to the Design System Engineer by route A.**

PR #81 needs 13 tests, one source line and 2 regenerated pools. The reviewer wrote and ran every case. I built the round from the reviewer's text in a scratch tree at `699cb7e`, and it reads the reviewer's figures. The account outage delayed this routing: run `8873c35b` (09:41Z) died in 2 s on `configuration_incomplete`, and the board reconnected at 11:45Z.

## Rulings
1. **B1, B2 and B3 stand.** 25 mutants survive on lines that PR #81 adds or rewrites (ruling 5), and none is equivalent (ruling 6). The reviewer's kill classes go in byte for byte: `CantripKillTests` (6 tests), `DrawCountKillTests` (1 test, 14 subtests) and `ToughnessCutKillTests` (5 tests).
2. **B4 stands, by ruling 2.** Through probe P2, the head reads Campus Crier as `card-draw` in anvil-chorus and stampede-acres. Its only draw is the Jace token's −3, and the card nets 0. The fix is the reviewer's text: `_REPEATABLE_DRAW` also treats "exile this card from your graveyard" as a cost that spends the card. It moves 10 mirror cards from `card-draw` to none, and the reviewer read all 10 as right. In the pools, 2 entries change and 0 seats move. The fault case `GraveyardCostFaultTests` goes in with it.
3. **My mutant G3 survives the round, and it is not a B item.** G3 reads "exile this card" for "exile this card from your graveyard". Its only kill case would assert `card-draw` for a draw behind "Exile this card from your hand:". That draw happens once, so the case would pin a fault that the head shares. The mutant rule yields here, as it did for M05 on DEC-1101. G3 goes to [DEC-1197](/DEC/issues/DEC-1197) item 3 as a candidate rule, with the forms "exile this creature" and "exile this artifact".
4. **N-c (probe P3) stays a named limit of PR #81. It becomes item 7a of DEC-1197, after the loot items (items 4 and 7).** It differs from B4 in one point: no rule passes the bar today. The reviewer's narrow rule (`_DRAW_AGAIN`) moves 20 cards, and 5 of them are false, all loots or rummages (2.5 in 10). The right rule needs DEC-1197's loot rules first. Through P3, 7 pool entries lose `card-draw` wrongly, and 0 seats move. Item 6 also reads flashback, buyback, cipher, escape, harmonize and "investigate twice".
5. **N-d.** Jace's Machinations (3 pools) and Way of the Wildspeaker (1 pool) are near cases: with Empower Jace 7 or more, the token can use −3 twice, so each card nets +1. They go to DEC-1197 item 7a as cards to read. They do not block this pull request.
6. **The other N items.** N-a and N-b confirm my counts for P1 and P2. N-e lists the named limits as ruled. N-f needs no action. I accept the proofs of N-g: X8, Y8, Y9, Y10 and Y11 are equivalent. Secrets of the Key, the one false card of item 1's sample (1 in 20), belongs to P3 (flashback), and item 1's bar holds.

## Route
- **Implementer: Design System Engineer** (`8ea33a50`). It was idle with no open issue at {TIME}. The Founding Engineer's run `ea773a04` is live on [DEC-1187](/DEC/issues/DEC-1187) (medium), and its next queued run (`83bebd7f`) is DEC-1197, which the board set `todo` at 11:46:27Z.
- **Route A keeps reviewer and implementer apart.** The reviewer wrote and ran the text. The Design System Engineer applies it and reads it. I compare the files at the hand-back. The Founding Engineer wrote PR #81 and does not touch the round.
- **No delta re-read.** The round's one source line is the reviewer's own. I ran the mutants of that line, and the kit's `mut.py` runs them again on the round's tree.

## What I checked
Kit: `/Users/dpires/Documents/Personal/code/mtg-precon-upgrader/agents/ceo/analysis/dec1198-r1/` (`README.txt` lists each file). I ran everything in a detached scratch tree at `699cb7e` and removed the tree after.
- `apply.py` made 3 edits, and a second run printed `already` 3 times. The B4 file and the reviewer's run file have the same syntax tree (`compare.py`, digest `4258a3f7bf19205d`).
- The suite with the links read `713 passed, 1256 subtests passed`. Without them it read `712 passed, 1 skipped, 1256 subtests passed`. These are the reviewer's figures.
- The first pool run wrote anvil-chorus and stampede-acres and printed `no change` for the other 19. In each written file, Campus Crier's `deck_role` goes from `card-draw` to `null`, and no other field changes but `generated_at`. The second run printed `no change` 21 times. Metrics printed `Wrote 0 metrics file(s) (weights=A).`
- `mut.py` on the round's tree: the baseline reads `94 passed, 39 subtests passed`. Each of the 25 survivors fails its own kill case. G1 (the head's lookahead), G2 ("from your hand") and G4 ("from a graveyard") fail the B4 case. G3 survives (ruling 3).
- `core.py`, my check for the hand-back, read as expected on six local commits: `699cb7e` NOT EQUAL; the round ALL EQUAL; the round with a reworded docstring, a reworded comment and a wrapped call ALL EQUAL; the round with G3, with a stale pool, or with one more line in `docs/role-taxonomy.md` NOT EQUAL.

## DEC-1197
The board set DEC-1197 `todo` at 11:46:27Z. Its gate is real: its items edit `_REPEATABLE_DRAW` and `_is_cantrip`, which exist only on PR #81's branch, and B4 changes the same lookahead as its item 3. I wrote a paragraph at the top of its description: if PR #81 has merged when its run starts, do the work on `main`; if not, post one line and hand back, and the merge run assigns it back. Item 3 now holds ruling 3, and a new item 7a holds rulings 4 and 5.

planned-by: CEO. Source: DEC-1198 verdict `14a16973`.
