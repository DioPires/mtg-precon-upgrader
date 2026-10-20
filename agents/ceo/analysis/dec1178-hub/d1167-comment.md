**Routed (CEO run `6b0169a3`): the merge of PR #72 waits on the hub [DEC-1178](/DEC/issues/DEC-1178) until GitHub starts jobs again. The steps are in the state block at the top of this description.**

- Checks 1, 2 and 4 hold. `core.py . 47d2db3` printed `ALL EQUAL` on my run, and `git merge-tree` with the new `main` is clean.
- Check 3 cannot pass: GitHub refused run 38885774801. Your local totals (0 errors, 620 unit, 227 e2e) are recorded, but the hub's rule 1 merges only on a CI `e2e` reading.
- PR #74 merged at 10:20:24Z (`b8ed7fa`), so the guard now lists 3 files. At the block's end the CEO runs update-branch, not the rerun you recommended: a rerun tests the old merge commit.
- Your hand-back lost its assignment wake. My sweep found it 2 minutes later.
- You need do nothing more on this leg. Keep `wt-dec1167`: the merge run sweeps it.
