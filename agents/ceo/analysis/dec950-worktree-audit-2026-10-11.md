# Worktree audit, eternities-mtg-app, 2026-10-11 (CEO, DEC-950 wake on the owner's worktree question)

Basis: `git worktree list --porcelain` at 10:2xZ, `origin/main` = `c54f50f`, merged pull requests #1 to #119 from `gh pr list --state merged`. Dirty = `git status --porcelain` entry count. Ahead = commits not reachable from `origin/main`.

Totals: 99 worktrees besides the root checkout, 25.98 GB. Safe to remove (clean, every commit on `main`): 77, 14.82 GB. Keep (open pull request): 2, 6.27 GB. Needs a look: 20, 4.89 GB.

## Keep

| Worktree | Branch | Why |
|---|---|---|
| `wt-dec951-amend3` | `dec951-prd-amend-3` | PR #113 open, waits on the main merge and re-read |
| `wt-dec953` | `dec953-dominaria-slice` | PR #115 (draft), live slice run |

## Needs a look

| Worktree | Kind | Head | Ahead | Dirty | Size | Note |
|---|---|---|---|---|---|---|
| `wt-dec774` | branch | `d301929c` | 0 | 1 | 390 MB | untracked `.dec774-run/` (gate run output) |
| `wt-dec850` | detached | `610a4585` | 0 | 1 | 458 MB | untracked `web/worlds-gate/` (gate output) |
| `wt-dec863` | detached | `d301929c` | 0 | 1 | 38 MB | untracked `.dec863-review/` (review notes) |
| `wt-dec866-draw` | detached | `4958cea3` | 1 | 0 | 312 MB | detached review scaffold at a commit on no branch (merge preview, draw basis or mutation tree); removing the tree leaves the commit unreferenced |
| `wt-dec878` | branch | `20f9722d` | 3 | 1 | 191 MB | untracked `runs/`; branch has 3 unpushed probe commits, labelled throwaway |
| `wt-dec883` | branch | `86b77c02` | 1 | 0 | 312 MB | branch has 1 unpushed probe commit, labelled throwaway |
| `wt-dec889-mut` | detached | `25db3a6e` | 0 | 1 | 71 MB | untracked `web/scripts/dec889-dolly.mjs` (scratch script) |
| `wt-dec894` | detached | `bc3e3591` | 1 | 0 | 87 MB | detached review scaffold at a commit on no branch (merge preview, draw basis or mutation tree); removing the tree leaves the commit unreferenced |
| `wt-dec903` | detached | `446c47b9` | 1 | 0 | 312 MB | detached review scaffold at a commit on no branch (merge preview, draw basis or mutation tree); removing the tree leaves the commit unreferenced |
| `wt-dec903-mut` | detached | `f89eb32c` | 1 | 0 | 38 MB | detached review scaffold at a commit on no branch (merge preview, draw basis or mutation tree); removing the tree leaves the commit unreferenced |
| `wt-dec907` | detached | `344bc2b7` | 1 | 0 | 312 MB | detached review scaffold at a commit on no branch (merge preview, draw basis or mutation tree); removing the tree leaves the commit unreferenced |
| `wt-dec909` | detached | `d95643f2` | 1 | 0 | 312 MB | detached review scaffold at a commit on no branch (merge preview, draw basis or mutation tree); removing the tree leaves the commit unreferenced |
| `wt-dec909-mut` | detached | `d95643f2` | 1 | 0 | 279 MB | detached review scaffold at a commit on no branch (merge preview, draw basis or mutation tree); removing the tree leaves the commit unreferenced |
| `wt-dec910` | detached | `74b61867` | 1 | 0 | 406 MB | detached review scaffold at a commit on no branch (merge preview, draw basis or mutation tree); removing the tree leaves the commit unreferenced |
| `wt-dec912` | detached | `755e7848` | 1 | 0 | 71 MB | detached review scaffold at a commit on no branch (merge preview, draw basis or mutation tree); removing the tree leaves the commit unreferenced |
| `wt-dec912-b` | detached | `9c662d75` | 1 | 0 | 71 MB | detached review scaffold at a commit on no branch (merge preview, draw basis or mutation tree); removing the tree leaves the commit unreferenced |
| `wt-dec914` | detached | `070ece85` | 1 | 0 | 71 MB | detached review scaffold at a commit on no branch (merge preview, draw basis or mutation tree); removing the tree leaves the commit unreferenced |
| `wt-dec914-build` | detached | `4ff8970c` | 0 | 136 | 449 MB | 136 changed files: an uncommitted dataset refresh `c9468f1125bcddff` under `web/public/data/` (regenerable by the pipeline) |
| `wt-dec917b` | detached | `32dfb4a9` | 1 | 0 | 182 MB | detached review scaffold at a commit on no branch (merge preview, draw basis or mutation tree); removing the tree leaves the commit unreferenced |
| `wt-dec918` | detached | `5dc95656` | 1 | 0 | 650 MB | detached review scaffold at a commit on no branch (merge preview, draw basis or mutation tree); removing the tree leaves the commit unreferenced |

## Safe to remove (clean, on main)

| Worktree | Kind | Branch or head | Size | Last change |
|---|---|---|---|---|
| `workspace bc5c0753-6b0d-419c-9581-fa46ceb4a236/wt-dec697` | branch | `dec697-thumbnail-churn` | 84 MB | 2026-09-11 |
| `wt-dec759` | branch | `dec759-worlds-separation` | 409 MB | 2026-09-20 |
| `wt-dec774-base` | detached | `0be35f16` | 148 MB | 2026-09-20 |
| `wt-dec819` | branch | `dec819-budget-aware-threshold` | 52 MB | 2026-09-16 |
| `wt-dec836-mA` | detached | `f821ccd7` | 53 MB | 2026-09-17 |
| `wt-dec836-mB` | detached | `f821ccd7` | 53 MB | 2026-09-17 |
| `wt-dec837` | detached | `071daa02` | 147 MB | 2026-09-17 |
| `wt-dec842` | branch | `dec842-eviction-saturation` | 119 MB | 2026-09-17 |
| `wt-dec843` | branch | `dec843-reduced-motion-falsifier` | 118 MB | 2026-09-17 |
| `wt-dec846` | detached | `2b8f6e29` | 107 MB | 2026-09-17 |
| `wt-dec847` | branch | `dec847-w4-riders` | 85 MB | 2026-09-20 |
| `wt-dec849` | branch | `dec849-prd-72-art-rows` | 293 MB | 2026-09-18 |
| `wt-dec851` | detached | `8b789848` | 293 MB | 2026-09-18 |
| `wt-dec852` | branch | `dec852-input-star-layers` | 101 MB | 2026-09-18 |
| `wt-dec853` | detached | `77868fdf` | 342 MB | 2026-09-18 |
| `wt-dec854` | branch | `dec854-dec853-riders` | 71 MB | 2026-09-20 |
| `wt-dec854-base` | detached | `150c65ef` | 53 MB | 2026-09-18 |
| `wt-dec856` | detached | `30aaecff` | 406 MB | 2026-09-19 |
| `wt-dec864` | detached | `6b41aca9` | 312 MB | 2026-09-20 |
| `wt-dec864-base` | detached | `0be35f16` | 279 MB | 2026-09-20 |
| `wt-dec864-mut` | detached | `6b41aca9` | 555 MB | 2026-09-20 |
| `wt-dec864-replay` | detached | `98c1de76` | 279 MB | 2026-09-20 |
| `wt-dec865` | detached | `919b5381` | 617 MB | 2026-09-20 |
| `wt-dec866` | detached | `8204f12d` | 71 MB | 2026-09-20 |
| `wt-dec866-base` | detached | `7dfea1dd` | 86 MB | 2026-09-20 |
| `wt-dec867` | branch | `dec867-quality-spec-pin` | 312 MB | 2026-09-20 |
| `wt-dec868` | branch | `dec868-dead-galaxy-paths` | 279 MB | 2026-09-21 |
| `wt-dec869` | detached | `8b4cd67d` | 71 MB | 2026-09-20 |
| `wt-dec870` | detached | `10ced582` | 318 MB | 2026-09-20 |
| `wt-dec872` | branch | `dec872-spin-test-riders` | 38 MB | 2026-09-20 |
| `wt-dec873` | branch | `dec873-mirror-residuals` | 321 MB | 2026-09-21 |
| `wt-dec873-base` | detached | `24faa508` | 279 MB | 2026-09-21 |
| `wt-dec877-a0` | detached | `a0eec545` | 191 MB | 2026-09-20 |
| `wt-dec877-base` | detached | `7dfea1dd` | 71 MB | 2026-09-20 |
| `wt-dec879` | detached | `4a783296` | 38 MB | 2026-09-20 |
| `wt-dec881` | branch | `dec881-ci-minute-rate` | 38 MB | 2026-09-20 |
| `wt-dec882` | branch | `dec882-threshold-buckets` | 191 MB | 2026-09-20 |
| `wt-dec884` | branch | `dec884-mirror-guard` | 376 MB | 2026-09-20 |
| `wt-dec885` | branch | `dec885-production-refresh` | 728 MB | 2026-09-21 |
| `wt-dec887` | branch | `dec887-popstate-ring` | 312 MB | 2026-09-21 |
| `wt-dec888-review` | detached | `08bf4a6f` | 376 MB | 2026-09-20 |
| `wt-dec889` | detached | `25db3a6e` | 191 MB | 2026-09-20 |
| `wt-dec890` | branch | `dec890-artcells-falsifier` | 82 MB | 2026-09-20 |
| `wt-dec892` | branch | `dec892-budget-flag-value` | 38 MB | 2026-09-20 |
| `wt-dec893` | detached | `5eff6b32` | 38 MB | 2026-09-20 |
| `wt-dec893-main` | detached | `6aad4312` | 38 MB | 2026-09-20 |
| `wt-dec895` | branch | `dec895-review-riders` | 279 MB | 2026-09-21 |
| `wt-dec897` | detached | `dd8b6a77` | 38 MB | 2026-09-20 |
| `wt-dec900` | detached | `f775af30` | 312 MB | 2026-09-21 |
| `wt-dec901` | detached | `67464e72` | 312 MB | 2026-09-21 |
| `wt-dec902` | branch | `dec902-no-color` | 316 MB | 2026-09-21 |
| `wt-dec906` | detached | `a3ff5b4e` | 312 MB | 2026-09-21 |
| `wt-dec907-main` | detached | `e48ba89b` | 312 MB | 2026-09-21 |
| `wt-dec908` | branch | `dec908-w1-row-timeout` | 279 MB | 2026-09-21 |
| `wt-dec910-main` | detached | `9df1fbd2` | 38 MB | 2026-09-21 |
| `wt-dec913` | branch | `dec913-printing-date-sort` | 740 MB | 2026-09-21 |
| `wt-dec914-head` | detached | `4ff8970c` | 376 MB | 2026-09-21 |
| `wt-dec915` | detached | `eb6aef8c` | 312 MB | 2026-09-21 |
| `wt-dec915-main` | detached | `0b772e67` | 312 MB | 2026-09-21 |
| `wt-dec917` | detached | `0cfe6974` | 103 MB | 2026-09-21 |
| `wt-dec918-build` | detached | `eadc9d88` | 454 MB | 2026-09-21 |
| `wt-dec919` | branch | `dec919-w4frame-refuse` | 279 MB | 2026-09-21 |
| `wt-dec920` | detached | `2130e9ff` | 38 MB | 2026-09-21 |
| `wt-dec922` | detached | `7a0b659c` | 38 MB | 2026-09-21 |
| `wt-dec924` | detached | `cd48b2d6` | 403 MB | 2026-09-21 |
| `wt-dec950` | branch | `dec950-prd-v4` | 38 MB | 2026-10-10 |
| `wt-dec950-docs` | branch | `dec950-prd-amend-1` | 38 MB | 2026-10-10 |
| `wt-dec951` | branch | `dec951-unity-skeleton` | 39 MB | 2026-10-10 |
| `wt-dec952` | branch | `dec952-temperate-kit-sources` | 38 MB | 2026-10-10 |
| `wt-dec952-amend2` | branch | `dec952-prd-amend-2` | 38 MB | 2026-10-10 |
| `wt-dec952-erratum` | branch | `dec952-prd-amend-2-erratum` | 38 MB | 2026-10-10 |
| `wt-dec952-erratum2` | branch | `dec952-prd-amend-2-erratum-2` | 38 MB | 2026-10-10 |
| `wt-dec959` | branch | `dec959-root-brief` | 39 MB | 2026-10-10 |
| `wt-dec963` | branch | `dec963-root-brief-followup` | 39 MB | 2026-10-10 |
| `wt-dec965` | branch | `dec965-readme-prd-numbering` | 39 MB | 2026-10-11 |
| `wt-dec968` | branch | `dec968-enforce-admins-doc` | 39 MB | 2026-10-11 |
| `wt-dec970` | branch | `dec970-ci-enforce-admins-comment` | 39 MB | 2026-10-11 |

## Related state

- Root checkout: branch `dec739-platform-layer` at `305b99c` (merged as PR #45 on 2026-09-14). Untracked at the root: `prd_v4.md` (draft 5 text, older than `main`), `docs/decisions/dec950-overhaul-deep-dive.md` (revision 7, older than `main`), `REVIEW-2026-09-08.md` (cited by the plan; exists nowhere on `main`), `.claude/`.
- Local branches: 136, of which 121 are merged into `origin/main`. Remote branches: 115, of which 106 are merged. Repository setting `delete_branch_on_merge` is false.
- `git worktree prune --dry-run` lists nothing: every registered worktree still has its directory.


## Outcome (CEO, 2026-10-11 11:1xZ, on the owner's picks remove_safe + rule + remote_branches)

Basis before the sweep: `origin/main` `c54f50f`, open pull requests #113 (`dec951-prd-amend-3`) and #115 (`dec953-dominaria-slice`, draft, live run). Each tree was re-checked immediately before removal: `git status --porcelain` empty, `git merge-base --is-ancestor HEAD origin/main` true, not an open-pull-request branch, not `wt-dec953` or `wt-dec951-amend3`. No `--force`. `git worktree prune` after. Per-tree log: `dec950-worktree-removal-2026-10-11.json`.

| | Before | After |
|---|---|---|
| Worktrees besides the root checkout | 99 | 22 |
| Removed (clean, on `main`) | | 77, 0 failed |
| Local branches | 136 | 17 |
| Remote branches | 114 | 8 |
| `delete_branch_on_merge` | false | true (read back) |
| Disk free, `df -h /` | 566 GiB | 572 GiB |

The `df` gain is smaller than the 14.8 GB `du` sum because APFS clones share blocks between worktrees. Local branches left: `main`, the two open heads, four checked out in kept trees (`dec739-platform-layer` at the root, `dec774-galaxy-spin-axis`, `dec878-gate-runner-probe`, `dec883-gate-runner-fix`), and ten unmerged (`dec694-worlds-prototype`, `dec740-ui-three-boundary`, `dec749-r1-pick-floor-probe`, `dec752-backup-3468ee3`, `dec752-backup-adbdcca`, `dec752-backup-b261f01`, `dec752-scratch-tilt-arm`, `dec812-gate-instrument`, `dec838-wire-bytes-instrument`, `prerebase-dec752`). Remote branches left: `main`, the two open heads, and five unmerged (`dec-616-midstream-retry`, `dec694-worlds-prototype`, `dec740-ui-three-boundary`, `dec749-r1-pick-floor-probe`, `dec838-wire-bytes-instrument`). The 20 "needs a look" trees were not touched (the owner did not pick `remove_rest`); the root checkout stays on `dec739-platform-layer` (`root_to_main` not picked).

Method note: eleven local merged branches had a deleted upstream and HEAD at the root is old, so `git branch -d` refused them; each was deleted with `-D` after its own `is-ancestor origin/main` check. A single `git push origin --delete` with 107 refs did nothing (rejected as a whole); the deletion was re-run one branch at a time with 0 failures and verified by `git ls-remote --heads` afterwards.

Rule: DEC-972 (Interactive Tools Engineer, low) writes `docs/worktrees.md` and the root-brief pointer; the six engineer instruction files carry item 8 of the Eternities section as the interim rule.
