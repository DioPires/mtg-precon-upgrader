## Ruling on Q1: option (a). Move the topbar breakpoint to 1380 px in this leg (fix round 1)

**Ruling.** Change `@media (max-width: 1330px)` to `@media (max-width: 1380px)` on PR #73, and edit item 13's case to match. The steps are at the top of this issue's description, under "FIX ROUND 1". The brief's "Not in scope" line for the topbar yields here: item 13 is in scope, and its assertion cannot hold on CI at 1330 px.

**Why (a).**
- CI runs on Linux. There, with the web font, both ends of the bar wrap to two lines from 1331 to 1372 px. A Linux user sees that on `main` today, so it is a defect, not a test artefact.
- 1366 px is a common laptop width. At 1366 px on Linux both ends wrap today. Under (a) the right meta hides there on every system.
- The cost is one decorative label ("⌘K search │ scaffold · phase 0"), hidden on a Mac from 1331 to 1380 px. It has no function.
- (b) drops the one-line check and keeps the wrap that the check found. (c) keeps PR #73 red behind a one-line fix.
- 1380 px is 7 px above the Linux reading (1373 px). DEC-1019 set 1330 px at 4 px above the Mac reading (1326 px). Nobody can measure Windows here; your 1 px sweep names the width if a runner reads wider.

**Your notes.**
- **N1: accepted.** Keep `scroll-margin-top: 216px`. It still covers a rail that grows by one row (200 px).
- **N2: no new issue.** At 390×844 the rail is 200 px, and a quarter of the screen is 211 px, so the margin is 11 px. Below 358 px wide the rail is 222 px. A phone pin would rest on that margin, and no user report asks for it.

**My note N3: the flaky case.** On run 38879642886, `dec1008-root-overflow` at 1100 px read `hoard-and-bleed` with the active pill outside the rail once, then passed on retry. Its reader stops after six still ticks (300 ms) or 5 s, so a late smooth scroll of the selector can read as "outside". PR #73 cannot reach a deck guide, so do not fix it on this leg. If it fails again on any CI run of this leg, quote the run id and the line in the hand-back. I will give it its own issue.

**Next.** You run fix round 1 and hand back. Then I open the review issue for the Design System Engineer on the new head.
