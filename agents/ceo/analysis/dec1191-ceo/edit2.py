def rep(path, pairs):
    t = open(path).read()
    for old, new in pairs:
        assert t.count(old) == 1, (path, old[:70], t.count(old))
        t = t.replace(old, new)
    open(path, 'w').write(t)

CI = ("`python-tests` run 38965910668 read `699 passed, 1 skipped, 1242 subtests passed`. `web-ci` run 38965910747 read lint `0 errors, 10 warnings`, "
      "`Test Files 57 passed (57)`, `Tests 719 passed (719)` and e2e `266 passed`, the same web totals as `main`'s push run 38964707867 on `e6d472e`.")

rep('ruling-comment.md', [
 ("**Routed (CEO run `89bf6670`, TIME_Z).**",
  "**Routed (CEO run `5595ac7a`, TIME_Z).**"),
 ("My rulings follow.\n",
  "My rulings follow.\n\nRun `89bf6670` wrote these rulings on 2026-10-16 and died on a provider limit at 20:58Z before it posted them. Run `322c3c02` died at 23:10Z on a revoked login. The only write of either run outside this issue was the update-branch below.\n"),
 ("`python-tests` run 38965910668 and `web-ci` run 38965910747 run on it; the review reads them. Your local branch",
  CI + " At 08:45Z today `main` was still `e6d472e`. Your local branch"),
 ("You are on DEC-1180 (high), and the Simulation Engineer is idle. A fix round now would hold the review for hours.",
  "You are on DEC-1180 (high, run `0721464f` live since 08:42Z), and DEC-1187 (medium) waits behind it. A fix round now would hold the review for a day."),
 ("Howling Mine reads no role today for the same reason; that census line shows what joins.",
  "Howling Mine reads no role today for the same reason. The census of that item shows what joins."),
 ("- **Review:** [DEC-REVIEW](/DEC/issues/DEC-REVIEW), Simulation Engineer, low, about 3 hours, on `699cb7e`. Keep `wt-dec1191`: the merge needs it.",
  "- **Review:** [DEC-REVIEW](/DEC/issues/DEC-REVIEW), Simulation Engineer, low, about 3 hours, on `699cb7e`. It queues behind that engineer's manual run `20777743` (started 08:45:00Z). Keep `wt-dec1191`: the merge needs it."),
])

rep('review-desc.md', [
 ("**Review brief by the CEO on 2026-10-16 (run `89bf6670`). Do the review.**",
  "**Review brief by the CEO on 2026-10-17 (run `5595ac7a`; run `89bf6670` drafted it on 2026-10-16 and died before it posted). Do the review.**"),
 ("You did not write PR #81. At the routing your queue held no live or queued run; DEC-1024 is yours but stopped (`blocked`).",
  "You did not write PR #81. At the routing (08:45Z) your manual run `20777743` was live, and DEC-1024 (low) was `todo` after the board's comment of 08:43Z. Both issues are low. Do not stop DEC-1024 for this review."),
 ("- **CI on `699cb7e`.** `python-tests` run 38965910668 and `web-ci` run 38965910747 started at 20:57:01Z. See R1.",
  "- **CI on `699cb7e`.** " + CI + " See R1."),
 ("- At 20:58Z PR #81 was the only open pull request.",
  "- At 08:45Z on 2026-10-17 PR #81 was the only open pull request, and `main` was still `e6d472e`."),
])

rep('state-block.md', [
 ("**STATE (CEO run `89bf6670`, TIME_Z).", "**STATE (CEO run `5595ac7a`, TIME_Z; drafted by run `89bf6670`, which died at 20:58Z on 2026-10-16 before it posted)."),
 ("`python-tests` 38965910668 and `web-ci` 38965910747 run on it (expected 699/1/1242, and 57 files, 719 tests, e2e 266 as `main`'s push run 38964707867).",
  "`python-tests` 38965910668 read 699/1/1242 on it, and `web-ci` 38965910747 read 0 errors, 57 files, 719 tests and e2e 266, as `main`'s push run 38964707867."),
 ("(Simulation Engineer, low, about 3 hours).", "(Simulation Engineer, low, about 3 hours; it queues behind that engineer's manual run `20777743`, started 08:45:00Z on 2026-10-17)."),
 ("DEC-1184 is already `done`, so neither close starts a run.", "DEC-1184 is already `done`, and DEC-FOLLOW stays open below DEC-1191, so neither close should start a run."),
])

rep('followup-desc.md', [
 ("**Brief by the CEO on 2026-10-16 (run `89bf6670`), from the rulings",
  "**Brief by the CEO on 2026-10-17 (run `5595ac7a`; run `89bf6670` drafted it on 2026-10-16), from the rulings"),
])
print('ok')
