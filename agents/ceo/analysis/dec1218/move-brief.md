**Implementer: the Simulation Engineer (`6ba3ac88`). Tier 1, priority high. Budget: about 1.5 hours. One pull request; do not merge it.**

**Start.** Nothing starts this issue yet. The CEO sets it `todo` after DEC-1221 merges and the CEO's rebuild of the Star Trek sheet and its PDF is on `main` (step 8 of DEC-1221's checks). If you find this issue `todo` with this paragraph still at the top, the owner started it: do the work. Hand back on the day you start: the Star Trek sheet is due on Thursday 5 November, and its last steps happen in the new folder.

## Why
- On DEC-1218 (2 November, 09:53Z) the board decided that the prerelease results leave `agents/ceo/` for `analysis/prerelease/<set>/` at the repository root, and that the move happens this week, right after DEC-1221 merges.
- Today the results sit in three folders under three naming schemes, beside about 1,600 files of the CEO's review records. Two test files and the `python-tests` path filter read `agents/ceo/analysis/dec925/`.
- The board left the seven older deck analyses that `data/commanders/*/deck.json` and `data/bracket-philosophy.md` cite for a later cleanup. They are not part of this leg.

## Target
```
analysis/prerelease/
  README.md      new (text in step 5)
  fra/           every file of agents/ceo/analysis/dec925/
    backtest/    every file of agents/ceo/analysis/dec1218/fra-retro/ (with review/ and review/simout/)
  trk/           every file of agents/ceo/analysis/prerelease/trk/
```
These stay where they are: the files directly in `agents/ceo/analysis/dec1218/` (the CEO's briefs and cards), and everything else under `agents/`.

## What to do
1. **Tree.** Run `cd /Users/dpires/Documents/Personal/code/mtg-precon-upgrader && HOME="$PAPERCLIP_GITHUB_HOST_HOME" git fetch origin && HOME="$PAPERCLIP_GITHUB_HOST_HOME" git worktree add -b dec-1222-prerelease-folders wt-dec1222 origin/main`. Work only in `wt-dec1222`. Keep scratch under `/tmp/dec1222/`. Check that `scripts/prerelease/build_pdf.py` exists on your base: it shows that DEC-1221 has merged. If it does not exist, stop and hand back with that finding.
2. **Count before.** Record `git ls-files <folder> | wc -l` for each of the three folders. Record the count line of `uv run --with pytest python -m pytest -q` on your base.
3. **Move with `git mv`, in a commit of its own with no content change.**
   - `mkdir -p analysis/prerelease`
   - `git mv agents/ceo/analysis/dec925 analysis/prerelease/fra`
   - `git mv agents/ceo/analysis/dec1218/fra-retro analysis/prerelease/fra/backtest`
   - `git mv agents/ceo/analysis/prerelease/trk analysis/prerelease/trk`
   - Commit with the message `chore(prerelease): move the prerelease folders to analysis/prerelease/ (DEC-1218)`. In this commit every file is a 100% rename, so `git log --follow` finds each file's history.
4. **Path edits, in a second commit** with the message `fix(prerelease): point tests, CI, scripts and documents at analysis/prerelease/ (DEC-1218)`. Line numbers are from `main` `6c3604f7`; DEC-1221 can move them.
   - `tests/test_prerelease_tools.py`: `DEC925 = ROOT / "analysis" / "prerelease" / "fra"` and `TRK = ROOT / "analysis" / "prerelease" / "trk"`. Keep the constant names.
   - `tests/test_sealed_sim.py`: `DATA = ROOT / "analysis" / "prerelease" / "fra"`.
   - `.github/workflows/python-tests.yml`: in both path lists, replace `'agents/ceo/analysis/dec925/**'` with `'analysis/prerelease/**'`. The suite then also starts on a change under `trk/`, which `tests/test_prerelease_tools.py` reads since DEC-1220.
   - `scripts/sealed_sim.py`: the five paths in the docstring's example command (lines 10 to 15).
   - `scripts/prerelease/README.md`: the worked example becomes `analysis/prerelease/fra/` (Reality Fracture), and `DIR` is normally `analysis/prerelease/CODE`. Change also each path that DEC-1221 added.
   - `scripts/prerelease/build_pdf.py`: each old path in its docstring, if any.
   - `docs/prerelease-playbook.md`: the worked example (line 3), `DIR` (line 24), the path of `retro.py` in step 10 (it becomes `analysis/prerelease/fra/backtest/retro.py`), the deliverables path in the issue template (line 114), and each path that DEC-1221 added.
   - Root `AGENTS.md`, section "Prepare for a Sealed prerelease" (line 237): the worked example becomes `analysis/prerelease/fra/`. Add this sentence after it: "Each set's files go in `analysis/prerelease/<code>/` (index: `analysis/prerelease/README.md`)."
   - The moved one-off scripts, so that they still run from their new place:
     - `analysis/prerelease/fra/backtest/retro.py`: `DEC925 = os.path.join(HERE, "..")`. In the docstring, `../../dec925/` becomes `../`.
     - `analysis/prerelease/fra/backtest/review/ceo_verify.py`: `DEC925 = os.path.join(D, "..")`.
     - `analysis/prerelease/fra/backtest/review/common.py`: `R = REPO + "/analysis/prerelease/fra/backtest"` and `D = REPO + "/analysis/prerelease/fra"`.
     - `analysis/prerelease/fra/build_echoed_pairs.py`: the `Run:` line of the docstring (line 30). Do not change line 101. It is the source text that the script writes into `echoed_pairs.json`, and the committed file must stay reproducible.
   - **Do not edit records.** Reports, comments, logs, briefs, sim outputs and data files keep the paths of the day they were written: every `*.json` and `*.txt` file, and every `*.md` file under `analysis/prerelease/` other than the new README. The README says so.
5. **New file `analysis/prerelease/README.md`**, with this text. Replace `<date>` (the day of your move commit, written as "2 November 2026").

````markdown
# Prerelease analyses

One folder per set, named by its Scryfall set code. The tools are in
[`scripts/prerelease/`](../../scripts/prerelease/README.md), and the process is in
[`docs/prerelease-playbook.md`](../../docs/prerelease-playbook.md).

| Set | Folder | Event | Cheat sheet | Back-test |
|---|---|---|---|---|
| Reality Fracture | [`fra/`](fra/) | 25 or 26 September 2026 | [`cheat_sheet.md`](fra/cheat_sheet.md), [`cheat_sheet.pdf`](fra/cheat_sheet.pdf) | Done on 1 November 2026: [`backtest/retro.md`](fra/backtest/retro.md) and [`backtest/adversarial-review.md`](fra/backtest/adversarial-review.md) |
| Star Trek | [`trk/`](trk/) | 6 November 2026 | [`cheat_sheet.md`](trk/cheat_sheet.md), [`cheat_sheet.pdf`](trk/cheat_sheet.pdf) | Due about 1 December 2026 |

## Where the folders came from

DEC-1222 moved them here on <date>:

- `fra/` was `agents/ceo/analysis/dec925/` (issue DEC-925).
- `fra/backtest/` was `agents/ceo/analysis/dec1218/fra-retro/` (issue DEC-1218).
- `trk/` was `agents/ceo/analysis/prerelease/trk/` (issue DEC-1218).

Files written before the move, such as reports, sim outputs and logs, still
quote the old paths. `git log --follow <file>` shows a file's history from
before the move.
````

6. **Checks on your head.** Quote each result in the hand-back.
   - a. `git ls-files agents/ceo/analysis/dec925 agents/ceo/analysis/dec1218/fra-retro agents/ceo/analysis/prerelease | wc -l` prints 0. `git ls-files analysis/prerelease | wc -l` equals the sum of step 2 plus 1 (the README).
   - b. `git diff -M --name-status origin/main...HEAD | grep -v '^R100'` lists only the files of step 4 and the README.
   - c. `git grep -n -E 'agents/ceo/analysis/(dec925|prerelease|dec1218/fra-retro)|"ceo"' -- . ':!agents/'` names no file in `tests/`, `scripts/`, `docs/`, `.github/` or the root `AGENTS.md`, and no moved `.py` file except line 101 of `build_echoed_pairs.py`. Quote the number of lines and the files that it names.
   - d. `uv run --with pytest python -m pytest -q` passes, and its count line equals the one of step 2.
   - e. `python3 -I analysis/prerelease/fra/backtest/retro.py > /tmp/dec1222/retro.out` exits 0, and `git status --porcelain` then prints nothing. The script rewrites `retro.md` beside itself; on `main` `6c3604f7` it writes the committed file byte for byte.
   - f. Copy `analysis/prerelease/trk/` to `/tmp/dec1222/trk/`. Run `uv run python scripts/prerelease/build_grades.py --set-dir /tmp/dec1222/trk` and then `uv run python scripts/prerelease/build_cheat_sheet.py --set-dir /tmp/dec1222/trk`. `cmp` shows that `grades.json` and `cheat_sheet.md` equal the committed files.
   - g. `git log --follow --oneline analysis/prerelease/trk/grades_src.py` lists the commits from before the move.
7. **Pull request.** Push the branch and open the pull request against `main`, titled `Move the prerelease folders to analysis/prerelease/ (DEC-1218)`. Keep the two commits. Wait for `python-tests` on the head and quote its result.

## Rules
- Set `HOME="$PAPERCLIP_GITHUB_HOST_HOME"` for every `git` and `gh` command.
- Change only the three moves, the new README and the edits of step 4. Touch nothing else under `agents/`, and nothing under `data/` or `web/`.
- Rebuild no output and edit no record (the last bullet of step 4).
- The CEO commits nothing under the three old folders from the moment this issue is `todo` until the merge. If `main` changes a file there after your branch point anyway, merge `origin/main` into your branch (git follows the renames), repeat checks a to f, and say so in the hand-back.
- Send no request to Scryfall or any other network service.
- Keep `wt-dec1222` until the merge; the CEO removes it at the merge. Remove any scratch tree that you add with `git worktree remove` (never `--force`), and name it in your hand-back.

## Handoff
1. Post one comment: the pull request number and head, `git diff --stat -M origin/main...HEAD | tail -1`, the counts of step 2, the results of checks a to g, and the `python-tests` result.
2. As the last action of your run, send one PATCH on this issue: `assigneeAgentId` the CEO (`f9427c33-d719-4fd5-a3c5-cd2f65dd01e8`), `status: in_review`, and `executionPolicy.monitor` with `nextCheckAt` 30 minutes ahead, `scheduledBy: "assignee"` and `notes` under 500 characters that name your comment.
3. If the server answers 422 `invalid_issue_disposition`, send the same PATCH again with `nextCheckAt` about ten hours ahead. Never set `done`.
4. **A question in the middle of the leg.** Finish the parts that the question does not touch, commit and push them. Post the question with its evidence and your recommendation. Then send the PATCH of step 2 as the last action of your run. Do not open a child issue assigned to the CEO (the server refuses it with 409 `delegation_cycle`).

## CEO: checks at the hand-back
Review: a CEO checklist pass, as on DEC-1221. I am the only user of these folders.
1. `git diff -M --name-status origin/main...origin/dec-1222-prerelease-folders`: every line that is not `R100` is a file of step 4 or the README.
2. `python-tests` is green on the head, and the pytest count line equals `main`'s.
3. On the head, I run checks c and e again.
4. Merge pinned, as a merge commit so that the move commit stays apart: `gh pr merge <PR> -R DioPires/mtg-precon-upgrader --merge --match-head-commit <head>`.
5. Delete the remote branch (`gh api -X DELETE repos/DioPires/mtg-precon-upgrader/git/refs/heads/dec-1222-prerelease-folders`). Sweep `wt-dec1222`: `git status --porcelain` prints nothing, `git merge-base --is-ancestor HEAD origin/main` exits 0, then `git worktree remove wt-dec1222`, `git branch -D dec-1222-prerelease-folders` and `git worktree prune`. Fast-forward the shared checkout.
6. Update my records: the `python-tests` filter line in `agents/ceo/TOOLS.md`, and the paths in DEC-1218's monitor notes. The hold on writes ends: from now on the Star Trek work goes into `analysis/prerelease/trk/`.
7. Close with the audit line `planned-by: CEO / executed-by: Simulation Engineer / reviewed-by: CEO (checklist)`.

planned-by: CEO (run `3d708c0e`). Source: the board's answer of 2 November 09:53Z on DEC-1218 (card `48181f5a`: layout `analysis/prerelease/<set>/`, timing "right after DEC-1221 merges", deck analyses later), and `main` `6c3604f7`. Parent: DEC-1218.
