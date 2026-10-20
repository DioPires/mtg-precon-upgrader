def rep(path, pairs):
    t = open(path).read()
    for old, new in pairs:
        assert t.count(old) == 1, (path, old[:60], t.count(old))
        t = t.replace(old, new)
    open(path, 'w').write(t)
rep('review-desc.md', [
 ("**Verdict wanted:** `APPROVE at a857950`", "**Verdict wanted:** `APPROVE at 699cb7e`"),
 ("- `a857950` Item 5: 20 of the 21 `candidates.json` files regenerated.\n",
  "- `a857950` Item 5: 20 of the 21 `candidates.json` files regenerated.\n- `699cb7e` merges `main` `e6d472e` (see Basis).\n"),
 ("- **The head** is `a857950`, branched from `main` `607dd65`. `main` is now `8fb404c` (PR #80). From `607dd65` to `8fb404c`, `main` changed files under `web/` only, and none under `scripts`, `tests`, `data`, `docs` or `.github`.\n- **CI on the head.** `python-tests` run 38963263988: `699 passed, 1 skipped, 1242 subtests passed`. That is `main`'s push run 38959080919 on `607dd65` (`693 passed, 1 skipped, 1230 subtests passed`) plus the PR's 6 tests and 12 subtests. `web-ci` run 38963263746: lint `0 errors, 10 warnings`, `Test Files 55 passed (55)`, `Tests 706 passed (706)` and e2e `246 passed`. That is `main`'s push run 38961819328 on `8fb404c`; PR #81 adds no web test.\n",
  "- **The head.** The implementer's head was `a857950`, branched from `main` `607dd65`. PR #79 ([DEC-1190](/DEC/issues/DEC-1190)) merged at 20:46:53Z as `e6d472e`. At 20:56:55Z I ran GitHub's update-branch, pinned to `a857950`. The head is now `699cb7e` (parents `a857950` and `e6d472e`). Its tree `3797082a` equals `git merge-tree --write-tree e6d472e a857950`.\n- **What `main` brought.** From `607dd65` to `e6d472e`, `main` changed 35 files under `web/` (PR #80 and PR #79) and none under `scripts`, `tests`, `data`, `docs` or `.github`. PR #79 shares no file with PR #81.\n- **CI on `a857950`** (merged with `8fb404c`): `python-tests` run 38963263988 read `699 passed, 1 skipped, 1242 subtests passed`, and `web-ci` run 38963263746 read lint `0 errors, 10 warnings`, `Test Files 55 passed (55)`, `Tests 706 passed (706)` and e2e `246 passed`.\n- **CI on `699cb7e`.** `python-tests` run 38965910668 and `web-ci` run 38965910747 started at 20:57:01Z. See R1.\n"),
 ("- At 20:45Z PR #79 ([DEC-1190](/DEC/issues/DEC-1190), `web/` only) was the only other open pull request.\n",
  "- At 20:58Z PR #81 was the only open pull request.\n- If `main` moves while you work, merge it into your tree (see Rules) and say what moved under `scripts`, `tests`, `data` and `docs`.\n"),
 ("`git worktree add --detach wt-dec<N>-review a857950`. Run `git merge --no-edit origin/main` on the detached HEAD (no branch moves), and check that `git rev-parse HEAD^{tree}` equals `git merge-tree --write-tree a857950 origin/main`.",
  "`git worktree add --detach wt-dec<N>-review 699cb7e`. If `origin/main` is no longer `e6d472e`, run `git merge --no-edit origin/main` on the detached HEAD (no branch moves), and check that `git rev-parse HEAD^{tree}` equals `git merge-tree --write-tree 699cb7e origin/main`."),
 ("## R1. CI on the head\n- Read `python-tests` run 38963263988 and `web-ci` run 38963263746 on `a857950`. Quote the count lines. They must match the Basis.\n",
  "## R1. CI on the head\n- Read `python-tests` run 38965910668 and `web-ci` run 38965910747 on `699cb7e`. If either is still running, wait with a bounded loop in the foreground (`gh run view <id> --json status,conclusion`, a 20 s wait between reads). macOS has no `timeout` command.\n- Expected for `python-tests`: `699 passed, 1 skipped, 1242 subtests passed`. That is `main`'s push run 38959080919 on `607dd65` (`693 passed, 1 skipped, 1230 subtests passed`) plus the PR's 6 tests and 12 subtests. PR #79 changed no Python file.\n- Expected for `web-ci`: lint `0 errors, 10 warnings`, `Test Files 57 passed (57)`, `Tests 719 passed (719)` and e2e `266 passed`. That is `main`'s push run 38964707867 on `e6d472e`; PR #81 adds no web test.\n- Quote the lines. If either run is red, stop and hand back with the failing lines.\n"),
 ("3. Check that `a857950` changes only `candidates.json` files (20 files)",
  "3. Run `git show --remerge-diff --format=%h 699cb7e`. It prints only the id when the merge holds no hand edit. Quote the output.\n4. Check that `a857950` changes only `candidates.json` files (20 files)"),
 ("4. Check that the first bullet of", "5. Check that the first bullet of"),
 ("against `607dd65`'s files (`8fb404c` holds the same data files)", "against `607dd65`'s files (`e6d472e` holds the same data files)"),
 ("Lead with `APPROVE at a857950` or `CHANGES`.", "Lead with `APPROVE at 699cb7e` or `CHANGES`."),
])
rep('ruling-comment.md', [
 ("## What I checked\n- PR #81 head `a857950`:",
  "## What I checked\n- **`main` moved.** PR #79 merged at 20:46:53Z as `e6d472e` (`web/` only; it shares no file with PR #81; note `3828e432`). At 20:56:55Z I ran update-branch on PR #81, pinned to `a857950`. The head is now `699cb7e`, and its tree `3797082a` equals `git merge-tree --write-tree e6d472e a857950`. `python-tests` run 38965910668 and `web-ci` run 38965910747 run on it; the review reads them. Your local branch in `wt-dec1191` stays at `a857950`; leave it as it is.\n- PR #81 at `a857950`:"),
 ("Simulation Engineer, low, about 3 hours, on `a857950` merged with `main`.", "Simulation Engineer, low, about 3 hours, on `699cb7e`."),
])
rep('state-block.md', [
 ("- **Done.** PR #81 holds items 1, 2 and 5: head `a857950` (commits `b125c8f`, `81368f9`, `a857950`), branched from `607dd65`. `python-tests` 38963263988 reads `699 passed, 1 skipped, 1242 subtests passed`; `web-ci` 38963263746 reads 55 files, 706 tests, e2e 246.",
  "- **Done.** PR #81 holds items 1, 2 and 5: commits `b125c8f`, `81368f9` and `a857950`, branched from `607dd65`. On `a857950`, `python-tests` 38963263988 read `699 passed, 1 skipped, 1242 subtests passed` and `web-ci` 38963263746 read 55 files, 706 tests, e2e 246.\n- **Head `699cb7e`.** PR #79 merged at 20:46:53Z as `e6d472e` (`web/` only). My update-branch at 20:56:55Z (pinned to `a857950`) made the head `699cb7e`, tree `3797082a` = `git merge-tree --write-tree e6d472e a857950`. `python-tests` 38965910668 and `web-ci` 38965910747 run on it (expected 699/1/1242, and 57 files, 719 tests, e2e 266 as `main`'s push run 38964707867). `wt-dec1191` stays at `a857950`."),
 ("Check that `gh pr view 81 --json headRefOid` gives `a857950`.", "Check that `gh pr view 81 --json headRefOid` gives `699cb7e`."),
 ("If `origin/main` changed `web/` or `.github` since `8fb404c` (PR #79 is open), run update-branch", "If `origin/main` changed `web/`, `data/` or `.github` since `e6d472e`, run update-branch"),
])
print('ok')
