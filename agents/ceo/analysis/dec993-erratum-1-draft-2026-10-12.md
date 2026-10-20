# PRD v4 Amendment 4, erratum 1: owner walks on a built player (draft, CEO, 2026-10-12 19:5xZ)

Source: the owner's answer on DEC-993's card of 2026-10-12 19:25Z, question "walks": "Row G on a
built player, and a ten-minute walk after each merged leg-2 look pull request." The reason is on
the record (DEC-993 triage, finding 6): the owner does not use the editor, so the first slice's
greybox walk never happened, and the owner's first look at the slice came with the scope already
complete. Feedback latency is the thing the post of DEC-993 had that we lacked.

This erratum is drafted after Amendment 4 is confirmed and PR #124 is merged (DEC-994), as a
documents-only pull request by the CEO, reviewed by an engineer who did not write it. It changes
`prd_v4.md` section 9.6 and the plan's section 14.4. No code, no Unity job, no renderer path.

## E1. 9.6, opening paragraph, last sentence

Replace:

> The owner is in the editor for at most one day across both legs, plus two walks: twenty minutes
> on leg 1's greybox and the judging walk at the end of leg 2.

with:

> The owner is in the editor for at most one day across both legs, plus the walks of this
> subsection: twenty minutes on leg 1's greybox, ten minutes after each of leg 2's merged pull
> requests, and the judging walk at the end of leg 2. Every walk is on a built player placed in
> the owner's folder; no walk needs the editor. *(Erratum 1, 2026-10-12: the owner does not use
> the editor, and the first slice's greybox walk never happened for that reason.)*

## E2. 9.6, leg 1, pull request 2, the greybox clause

Replace:

> **the greybox**: the layout rendered on flat ground as plinths, paths, approaches and the
> trail, no dressing, no images, playable in the editor; the owner walks it for twenty minutes
> (row G).

with:

> **the greybox**: the layout rendered on flat ground as plinths, paths, approaches and the
> trail, no dressing, no images, playable in the editor and delivered as a built player in the
> owner's folder (built and placed by leg 1's engineer, about half an hour inside leg 1's budget;
> through `Build.Dirty` once DEC-979's PR #123 is merged, by hand before that as DEC-978 did); the
> owner walks the player for twenty minutes (row G); the reviewer reproduces the greybox in the
> editor through the scene generation entry point (8.2.5).

## E3. 9.6, leg 2, heading line

Replace:

> **Leg 2, the walkable Dominaria (about ten engineer-days):**

with:

> **Leg 2, the walkable Dominaria (about ten engineer-days, in two or three pull requests, each
> reviewed and merged on its own: dressing, blend and water; stands, HUD and map; stones, travel
> and the bench):** after each merge the engineer builds a player into the owner's folder and the
> owner walks it for ten minutes and answers in one line; the answer feeds the next pull request.
> The walk is not a merge gate: the merge stays on the reviewer's verdict. Pushes are held while
> the owner's screen is unlocked, as the first slice did. The split and the walks cost about half
> an hour of engineer time per build and ten minutes of the owner's per walk.

## E4. 9.6, acceptance matrix, row G, the Check cell

Replace:

> Greybox: the owner walks leg 1's greybox for twenty minutes and gives a first answer to
> question 1

with:

> Greybox: the owner walks leg 1's greybox as a built player for twenty minutes and gives a first
> answer to question 1

The Machine, Run, Pass and On-miss cells are unchanged.

## E5. Section 11, the decision record

Add one line after the last numbered decision of Amendment 4 (11.21 in draft 6; the number is
set at drafting): the owner's decision of 2026-10-12 19:25Z that every walk of the second slice
is on a built player and that leg 2 is merged in two or three pull requests, each followed by a
ten-minute owner walk that is not a merge gate.

## E6. Plan, section 14.4, the cost paragraph

In the owner-days sentence, replace "the greybox walk and the judging walk of 9.6" with "the
greybox walk, two or three ten-minute walks after leg 2's merged pull requests, and the judging
walk of 9.6". In leg 2's description add "in two or three pull requests, each followed by a build
into the owner's folder (about half an hour each)".

## Not changed

Row D's "owner editor time ≤ 1 day across both legs" stands: walks on a built player are not
editor time. Row A stays the judging walk at the end of leg 2. The leg 2 split is written into
leg 2's issues when they open; this erratum is the contract they cite.

## Correction after the DEC-1006 review (2026-10-12 20:2xZ, PR #127 head `5b0c1d7`)

B1 from the Design System Engineer's verdict (DEC-1006 comment `2805f046`): E2's parenthesis named `Build.Dirty` as the build. `Build.Dirty` is PR #123's dirty-stamp check (`git status --porcelain -- .` in `unity/Eternities/`); `Build.Run` on `main` builds the player, and DEC-978's copies came from it. The parenthesis in E2 now reads:

> (built with `Build.Run` and placed by leg 1's engineer, as DEC-978's copies were, about half an hour inside leg 1's budget; once DEC-979's PR #123 is merged, the player's dirty stamp reads the project folder only)

and the reviewer's sentence ends "the reviewer reproduces the greybox through the scene generation entry point (8.2.5)" (N4: 8.2.5 runs without the editor open). N5: the §12 erratum row cites plan §14.5 beside §14.4 and §14.7. The same E2 wording is in the plan's 14.5 paragraph. The text above this section is the draft as submitted at `585ad15`.
