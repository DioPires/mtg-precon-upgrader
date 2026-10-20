**GitHub refuses every Actions job in the private repository `mtg-precon-upgrader` since 2026-10-16 10:01Z. No agent can change billing. The board question is the card on [DEC-1155](/DEC/issues/DEC-1155). Until the block ends, no pull request here gets a CI reading, and a merge does not reach production by itself.**

## Readings
- GitHub's annotation, on each refused job: "The job was not started because recent account payments have failed or your spending limit needs to be increased. Please check the 'Billing & plans' section in your settings".
- The last job that got a runner: `lint-typecheck-unit` of run 38884232804 (PR #66), 09:59:45Z to 10:01:26Z.
- Refused: `e2e` of run 38884232804, attempt 1 at 10:01:26Z and attempt 2 at 10:02:58Z (3 s each). `lint-typecheck-unit` of run 38885108440 (PR #73) at 10:07:21Z (3 s). A refused job costs 0 minutes.
- The repository is private, so every hosted minute draws on the account's monthly quota. GitHub's docs give 2,000 minutes a month for GitHub Free and 3,000 for GitHub Pro. The quota resets on 1 November. My token cannot read the account's usage (404, `user` scope).
- `eternities-mtg-app` is public since DEC-880 (2026-09-21) and is not affected. Its last run, 38875899855 at 08:46Z, passed.
- Precedent: [DEC-880](/DEC/issues/DEC-880). The same block hit `eternities-mtg-app` on 2026-09-20. The board made that repository public the next morning.

## What it blocks (at 10:15Z)
| PR | Issue | Head | Last CI |
|---|---|---|---|
| #66 | [DEC-1155](/DEC/issues/DEC-1155) | `3c3a151` | unit green (657), `e2e` refused |
| #70 | [DEC-1153](/DEC/issues/DEC-1153) | `a75bcc2` | green, but its basis is before `e886907` |
| #71 | [DEC-1161](/DEC/issues/DEC-1161) | `5874fd4` | green on a merge with `e886907`; review DEC-1176 open |
| #72 | [DEC-1167](/DEC/issues/DEC-1167) | `0cfe1f3` | green; fix round 1 open |
| #73 | [DEC-1171](/DEC/issues/DEC-1171) | `01f3395` | refused (run 38885108440) |
| #74 | [DEC-1160](/DEC/issues/DEC-1160) | `7cba124` | green on a merge with `e886907`; review DEC-1175 |
| #75 | [DEC-1172](/DEC/issues/DEC-1172) | `e5e95b4` | green, but its basis is before `e886907` |

- The push run on `main` (`web-ci`) and `deploy-branch` are hosted jobs too. Production follows the `deploy` branch, which is at `e886907`. `main` (`cffaa03`) has the same build inputs.

## Rules for every CEO run while the block lasts
1. Merge a pull request only on a green `e2e` reading of its head, and only when `git diff --stat "$(git merge-base <head> origin/main)" origin/main -- web data .github vercel.json` prints nothing. A unit job alone is not a pass.
2. Run no `gh pr update-branch` and ask no engineer for a push whose only purpose is CI: the new head cannot get a reading.
3. After a merge that changes `web/`, `data/` or `vercel.json`, fast-forward `deploy` by hand, as the workflow does: `gh api -X PATCH repos/DioPires/mtg-precon-upgrader/git/refs/heads/deploy -f sha=<main sha> -F force=false`. Then read the newest Vercel deployment record.
4. Rerun at most one refused job for each wake, to test the block. Use `gh run rerun 38884232804 --failed` (PR #66's `e2e`, a reading we need anyway).
5. When an engineer's hand-back hits the block, park its issue on this hub and do not open a second board card. The card lives on DEC-1155.
6. When the block ends, rerun the refused runs, then route each pull request by its own state block. Close this hub when every refused run has a reading.

## Handoff
This hub is the CEO's own. It stays `in_review` with a fallback monitor. The board's answer on the DEC-1155 card wakes the CEO on DEC-1155, and that run updates this hub.

planned-by: CEO (run `a9b35256`, 2026-10-16). Source: DEC-1155 fix round 1 hand-back `f9b314c7`.
