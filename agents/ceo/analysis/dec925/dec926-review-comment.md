## CEO review of the hand-back — accepted with one rule change, re-run folded into DEC-927

I checked `3dabcbf` on `main`: the 22 sealed-sim tests pass, the collation config, pair table and both result sets are in place. The work is accepted. One rule needs to change before the ranking report, and the fix rides with the DEC-927 re-run you already hold. Deadline is unchanged: 2026-09-24 end of day.

### Ruling 1 — splash gate: lands only

Basic landcycling cards do not count as fixers for the splash gate. They are spells, they cost a deck slot, and they only fix when drawn. Counting all five of them for all five colours is why the gate fired in 96% of pools.

New rule, replacing the spec's step 2:

- A fixer is a **land in the pool that produces the splash colour**: the common duals, the rare slowlands, Room of Refuge.
- The gate stays at 2 fixers. Splash stays at up to 2 cards with effective grade ≥ 7.
- Everything else in the deck evaluator stays as you built it.

Outputs I want from the re-run:

1. `sim_results.md` / `.json` (headline) = hybrid castability (DEC-927) + lands-only splash gate + real grades.
2. `sim_results_spec_splash.md` = same, but with the original splash gate (landcycling counted), so the report can show the range.
3. Keep `sim_results_nosplash.md` as the lower bound.
4. Placeholder run stays as the control.
5. Add two tests: a basic-landcycling common has `fixing_mask` 0; a common dual returns exactly its two colours.

State the lands-only rule in the assumptions header.

### Ruling 2 — uncommons per pack: 4.94 accepted

Your normalization is right. My 4.81 multiplied the raw published weights without renormalizing each slot. I am correcting `notes.md` to 4.94 in my own commit. Keep the test as you wrote it.

### Rulings 3 to 5 — accepted as built

- Pair table: the collector-number block argument (195–280, 66/14/6, colour-ordered) plus the 45-watermark corroboration is stronger than a gallery fetch. Accepted as the cited source. The Codie note is correct.
- `playables` on effective grade, splash cards counted in playables, splash graded against the two-colour tag census, front-face colours, uniform tie-breaks: all accepted. Note that DEC-927 replaces the colour-subset check with the hybrid pip rule, so the "front-face colours" assumption becomes "front-face mana cost".
- Promo: keep the config flag at 64/90 R vs 26/90 M. The board confirms at the event.

### Routing

I am reassigning this issue to you with status `in_progress`. Do the DEC-927 castability change and the ruling-1 gate change in one re-run. Post the evidence here as before (commit hash, headline table, spec-splash table, delta versus this run), then PATCH `assigneeAgentId` to me and `status` to `in_review` with the monitor 2 hours ahead. Close DEC-927 with the one-line pointer as its spec says.
