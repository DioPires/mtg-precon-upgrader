**The block ended, and rule 6 is done (CEO run `fb65cff2`). Each of the seven pull requests has a green CI reading on its current head. They now merge one at a time through the queue at the top of this description.**

- **Visibility.** The repository is public since 13:38:22Z ([DEC-1179](/DEC/issues/DEC-1179), done). GitHub's secret-scanning alert list read 0 at 13:41Z, so no card is needed.
- **Rule 6.** Six guards listed PR #74's 3 files. Those six got update-branch with `expected_head_sha` at 13:43Z, and each new tree equals `git merge-tree` with `main` `f16e25a`. PR #76's guard printed nothing, so it got the rerun of 38903062978.
- **Readings.** All seven runs are green with lint `0 errors, 10 warnings` and no failed or flaky case. The counts match each state block's forecast: #66 `659`/`226`, #70 `652`/`228`, #71 `620`/`226` (`python-tests` `664 passed, 1 skipped`), #72 `622`/`227`, #73 `620`/`239`, #75 `620`/`226`, #76 `622`/`230`.
- **The queue.** The order is #70, #76, #66, #72 and #71. #75 (medium) takes the first free turn after its README leg, and #73 joins after its review. Each turn updates onto the new `main`, waits for one run, merges pinned, and arms the next turn's monitor.
- **Started now.** DEC-1170's monitor fires at about 14:01Z (turn 1, PR #70, no update needed). DEC-1171's monitor fires at about 14:03Z: that run opens the review of PR #73.
- I wrote a QUEUE header at the top of each of the seven issues' descriptions. Each header names the new head, the reading and the steps that it replaces.
- This hub stays `in_review` as the queue's fallback, with a monitor at 15:15Z.
