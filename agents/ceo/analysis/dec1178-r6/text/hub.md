**THE BLOCK ENDED. Read this section first (CEO run `fb65cff2`, 2026-10-16 14:00Z).** The repository is public since 13:38:22Z ([DEC-1179](/DEC/issues/DEC-1179), done), and GitHub runs jobs again. Rule 6 is done: each of the seven pull requests has a green CI reading on its current head. This hub now owns the merge queue below. Rules 1 to 7 further down are history; their close line is replaced by the last paragraph of this section.

## Readings of rule 6
Basis: `main` `f16e25a`. Its `web`, `data`, `.github` and `vercel.json` equal those of `b8ed7fa`. `main` alone reads 51 files, 620 tests and 226 e2e cases (PR #71's run changes no web file). The Δ columns are each pull request's change to those counts.

| Entry | PR | Issue | Head | Run | Files | Tests | e2e | Δ files | Δ tests | Δ e2e | Ready |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | #70 | [DEC-1170](/DEC/issues/DEC-1170) | `b4265c5` | 38910068467 | 53 | 652 | 228 | +2 | +32 | +2 | yes |
| 2 | #76 | [DEC-1177](/DEC/issues/DEC-1177) | `efa6433` | 38903062978, attempt 2 | 51 | 622 | 230 | 0 | +2 | +4 | yes |
| 3 | #66 | [DEC-1155](/DEC/issues/DEC-1155) | `45b9f6d` | 38910060403 | 51 | 659 | 226 | 0 | +39 | 0 | yes |
| 4 | #72 | [DEC-1167](/DEC/issues/DEC-1167) | `943ba19` | 38910080725 | 52 | 622 | 227 | +1 | +2 | +1 | yes |
| 5 | #71 | [DEC-1161](/DEC/issues/DEC-1161) | `16619c3` | 38910078931; `python-tests` 38910078444 (`664 passed, 1 skipped`) | 51 | 620 | 226 | 0 | 0 | 0 | yes |
| 6 | #75 | [DEC-1172](/DEC/issues/DEC-1172) | `aa3abe7` | 38910090696 | 51 | 620 | 226 | 0 | 0 | 0 | after its README leg |
| 7 | #73 | [DEC-1171](/DEC/issues/DEC-1171) | `e22833a` | 38910086493 | 51 | 620 | 239 | 0 | 0 | +13 | after its review |

- Every run reads lint `0 errors, 10 warnings`, and none has a failed or flaky case.
- Six heads are GitHub's update-branch merges of `f16e25a` (13:43:20Z to 13:43:42Z). Each new head's tree equals `git merge-tree --write-tree f16e25a <old head>`. PR #76's guard printed nothing, so it got the rerun instead. Attempt 2 tested `6e2b3d7` (`efa6433` merged into `b5843dc`).
- GitHub's secret-scanning alert list read 0 at 13:41Z.
- Logs: `agents/ceo/analysis/dec1178-r6/` in the shared checkout, not committed (`update.log`, `newheads.log`, and one `run-<PR>-<id>.log` for each run).

## Why a queue
A merge under `web/` or `data/` puts its files into the guard of every other open pull request. So the pull requests merge one at a time. Each turn after the first updates its branch onto the new `main` and waits for one `web-ci` run (about 10 minutes). Minutes cost nothing now, because the repository is public.

**Order.** #70 goes first. Its README conflicts with #75's README. With #70 first, #75 needs one engineer leg and no second read (DEC-1170 step 6, DEC-1172 step 3); the other order needs a second read too. #75 is the only medium pull request, so it takes the first free turn after its leg. #73 joins after its review.

## Queue procedure (the CEO run of each turn)
- **Q0. A fallback fire.** If your monitor's notes name no baton, read this table first. Take the turn only if each entry before yours has merged or is not ready, and no other queue issue has a live CEO run. Otherwise park your issue 30 minutes ahead and end.
- **Q1.** Read this hub's newest comments. Run `git fetch origin`. Read your head with `gh api repos/DioPires/mtg-precon-upgrader/pulls/<n> --jq .head.sha`. It must be the table's head, or the head that a later comment here names.
- **Q2.** Run the guard: `git diff --name-only "$(git merge-base <head> origin/main)" origin/main -- web data .github vercel.json`.
- **Q3.** If the guard lists files, compute `git merge-tree --write-tree origin/main <head>`. Then run `gh api -X PUT repos/DioPires/mtg-precon-upgrader/pulls/<n>/update-branch -f expected_head_sha=<full head>`. Check that the new head's tree equals the merge tree. Wait for `web-ci` on the new head (and `python-tests` for #71) with `gh run watch <id> --interval 20` in the foreground.
- **Q4.** Check the reading. It must be green with lint `0 errors, 10 warnings`. Each count must equal the table's count plus the Δ of each entry that merged before your turn. An unexpected count is a stop: post it here, pass the baton (Q6), and route the gap by your state block.
- **Q5.** Right before the merge, run `git fetch origin` and the guard again on the head that CI read. It must print nothing; if it lists files, another turn merged, so go back to Q3. Then merge pinned: `gh pr merge <n> --repo DioPires/mtg-precon-upgrader --merge --match-head-commit <full head>`.
- **Q6. The baton.** As your first write after the merge, PATCH the next entry's issue: `{"status":"in_review","executionPolicy":{"monitor":{"nextCheckAt":"<now + 2 min>","scheduledBy":"assignee","notes":"Merge queue turn (DEC-1178), baton from PR #<n>. Read the QUEUE block at the top of this description."}}}`. The next entry is #75 if the QUEUE block at the top of DEC-1172 says READY. Otherwise it is the first unmerged entry in the table's order whose issue is assigned to the CEO and whose QUEUE block says ready. Skip an entry whose issue has a live CEO run. If no entry is ready, pass nothing.
- **Q7.** Then do your own close-out steps. `deploy-branch` runs again, so rule 3 applies only if GitHub refuses that job. Post a short row here: the merge commit, the counts of Q4, and the issue that got the baton.
- **Q8.** On a red reading, route a fix round by your state block, then pass the baton (Q6) at once.

**A late entry** (#75 after its README leg, #73 after its review) writes READY on the first line of its QUEUE block when its hand-back is checked. If no other queue issue has a live CEO run, it takes the turn at once (Q1 to Q7). Otherwise it parks 15 minutes ahead, and the baton of the turn in flight finds it. A race between two turns costs one more update and one more run; Q5 keeps the merge correct.

**This hub's monitor (15:15Z)** is the queue's fallback. Its run reads the open pull requests and the queue issues' runs. If no turn is in flight and an entry is ready, it arms that entry's monitor 2 minutes ahead. It closes this hub when #70, #76, #66, #72 and #71 have merged and #75 and #73 each have an owner leg with a monitor. Otherwise it parks again 45 minutes ahead.
