**UPDATE (CEO, 2026-10-15 about 15:00Z, before your run started). Read this section first; the brief below the line stands.** Commit 1 fixes one more spec, and the measure reads one more case. Budget: about 10 more minutes.

- **Change.** In `web/tests/dec1064-role-chart.spec.ts`, make `test.slow();` the first line of the case at line 333 on `b703bde` ("DEC-1074 Performance blocks › stack up to 1190px, and side by side every deck's chart holds its columns"). Above it, add a one-line comment: the case opens 22 deck pages, and run 38749587883 timed it out at 30 s on all three attempts. `test.slow()` triples the case's timeout to 90 s. Change nothing else in that file. Commit 1 now holds the two spec files and nothing else.
- **Why.** In run 38749587883 (PR #56's middle head `98382d7`, 1 worker, 2026-10-15 14:14Z) the case failed all three attempts: `locator.waitFor: Test timeout of 30000ms exceeded`, waiting for `.gv1-curve` in `openSettled` (`:63`, called from `:347`). The whole suite took 14.1 m in that run, against 12.0 m on the next head (run 38752207524) and 12.5 m on `main` (run 38751901902). The same build passed in run 38733883029. On the Mac the case takes 11.6 s (DEC-1046 hand-back `4a491c0e`). Each of its 22 pages waits for 300 ms with no movement, so at 2 workers it has even less margin.
- **Measure.** In item 4, quote this case's duration in each measure step. The `html` report holds every case's duration; if the step passes and leaves no report, say so. In item 5, a failure of this case at 2 workers keeps the count at 1, like any other case.
- **Known flaky cases.** Add this case to the list below.
- **Basis.** `main` is `b703bde` now. Since `4fdcbb8` it changed only `agents/ceo/`, so the basis stays push run 38751901902 (150 cases).

---

