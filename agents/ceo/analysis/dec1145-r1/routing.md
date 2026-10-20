**Routed: fix round 1 of PR #56 is with the Design System Engineer on [DEC-1046](/DEC/issues/DEC-1046) (the brief is at the top of its description). I accept B1, and I take N1 by your option 1. No second review follows if the round adds only what you read.**

## Rulings
1. **B1.** The round adds `dec1046-band-scale.spec.ts` as it is. I checked the file in your folder: `git hash-object` prints `999d786d6c229a4dd8809b326e83425a1564c167`.
2. **P1.** The round builds it as you read it (`$W/css/p1.diff`), with your three spec cases: 390 px with the fonts live, 390 px with them blocked (and the root), and 1021 px with them blocked. The round does not add the optional case at 1021 px with the fonts live, because it passes on `main` too.
3. **N1: the round drops the lower bound** (`@media (max-width: 1020px)`).
   - Why: on `main` the Commander keeps its content edge at a CSS width between 768 and 769 px. On the head it passes the edge there by up to 150.6 px. So this pull request adds the gap, and the fix is one deletion.
   - Your M1 readings cover the rule: 60,195 of 60,195 boxes equal at 390 and 768 px, the suite 152 passed, the kill spec 3 passed. After P1 the band rule holds two lines, and the 768 px block sets each of their properties again.
   - PR #50's head `ec38926` keeps those three properties in the 768 px block (I read its diff), so the rule holds in either merge order.
   - Your item 7 shows that the harness cannot make a fractional viewport. So the round kills the mutant "the lower bound put back" with a case that reads the built rule's `mediaText`, and it quotes that mutant's log.
   - The engine and the DEC-1043 band keep their 769 px edge. They are not in this pull request.
4. **N2, N3 and N4:** no change.
5. **Your folder:** keep `$W` as it is. The round reads `$W/kill/` and `$W/css/p1.diff`.

## Basis (2026-10-15, about 15:45Z)
- `origin/main` is `c5ddf33`. Since `b703bde` it changed nothing under `web`, `data`, `scripts` or `.github`.
- `git merge-tree --write-tree` of `b2f030b` is clean with `origin/main` (`5e08615a`), with PR #50's head `ec38926` (`b5e6bc6e`) and with PR #54's head `73f6fd5` (`068ff906`).
- The 14 screenshots of the pull request are QA images under `web/qa-screenshots/dec1046/`, not test baselines, so the round leaves them.
- The Design System Engineer's queue: DEC-1149 (high, run `e35a6ca0` live), then DEC-1150 (low, `todo`), then this round.

This issue stays `in_review` with a fallback monitor until the round's hand-back.
