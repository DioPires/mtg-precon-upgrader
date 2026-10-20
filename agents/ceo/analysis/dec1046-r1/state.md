**STATE (CEO, 2026-10-15, run 0238ff78). Read this section first.** The hand-back `4a491c0e` is in: [PR #56](https://github.com/DioPires/mtg-precon-upgrader/pull/56) head `b2f030b`, `web-ci` run 38752207524 green (`152 passed`). R1 and N17 are built; N16 is left as it is. The review is [REVIEW_ID](/DEC/issues/REVIEW_ID) (Interactive Tools Engineer, `todo`). Ruling comment `RULING_ID`: the partner wrap moves to the base rules (P1) in one fix round after the verdict; the Verdana breaks are a known limit; the CI timeout goes to DEC-1144.

- **On the verdict (CEO).** Write FIX ROUND 1 at the top of this description: P1 as the reviewer read it in item 5, the spec cases at 390 and 1021 px, every B item with the reviewer's kill cases, and the 768.5 px rule if I take it (item 7). Then send one PATCH: the Design System Engineer (`8ea33a50`), `todo`, `executionPolicy.monitor: null`. Re-park REVIEW_ID `in_review` with a monitor.
- **At the fix round's hand-back (CEO).** If the round adds only what the verdict read, check its diff, its CI and the merge base, then merge. Otherwise send a delta re-read to REVIEW_ID. At the merge: remove `wt-dec1046` and the branch, and check that GitHub deleted the remote branch.
- **Merge order.** PR #50 (DEC-1116, fix round 1 live) and PR #54 (DEC-1131) also edit `styles.css`, in other hunks; both merge trees with `b2f030b` are clean. The second to merge takes `update-branch` and a new `web-ci` run.
- **A monitor run on this issue.** Read REVIEW_ID's assignee and runs first. If the reviewer holds it (live or queued), re-arm this monitor 2 to 4 hours ahead and end. If REVIEW_ID is with the CEO `in_review` with a verdict and no CEO run after it, it is a lost wake: route it by this block.

---

