**Start: at the merge of PR #63 ([DEC-1143](/DEC/issues/DEC-1143)). The CEO's merge run sets this issue `todo`. Until then it is `backlog`, and nothing here is for you.**

---

**Brief by the CEO on 2026-10-15 at about 16:45Z (run `5f38615b`), from the finding in the DEC-1143 hand-back `8e104d7c`. Do the work when this issue is `todo`.** Implementer: Simulation Engineer (`6ba3ac88`). The CEO names the reviewer at your hand-back; the reviewer is never you. Tier 1, priority low. Budget: about 2 hours. One pull request with two commits: the code with its tests, then the document line if one changes.

## The fault
- `generate_candidate_pool.py` skips the write of `candidates.json` when the mirror date, the methodology, `deck_gaps` and `asymmetric_only` are equal, and each entry's `(name, pinned, seeded_for_gap)` is equal (`scripts/generate_candidate_pool.py:974` to `992` on `main` `81f4dea`).
- So a change that keeps the order of the entries but changes another field writes nothing and prints `no change`. Examples: a new `deck_role` from the classifier, a new score that keeps the order, a new `owned` flag, a new `role_pool` median.
- DEC-1143 met it: after the classifier change, `--all` rewrote only 4 of the 18 pools whose roles changed. The engineer removed the 18 files and ran `--all` again. The Apothecary filters on `deck_role` and shows it as a label (`web/src/components/organisms/Apothecary.tsx:201` and `:459`), so a stale role reaches the user.

## The fix
1. Replace the guard. Skip the write only when the existing file equals the new output after both drop `generated_at`. Parse both sides the same way (for example `json.loads(json.dumps(out))` for the new side), so that a tuple and a list compare equal. `write_metrics` in `scripts/compute_deck_metrics.py` (line 1252 on `main`) does the same for `metrics.json` since DEC-1078; follow its shape.
2. Keep the `no change` line and its count. A rewrite prints the `wrote` line as today.
3. `candidates.json` has no other field that reads the clock. Check that by reading `generate_for_deck`, and say so in the hand-back with the line numbers. If you find one, stop and ask.

## Tests
Add the cases to `tests/test_generate_candidate_pool.py`. Use invented card names.
- A file that differs from the new output only in `generated_at` is not rewritten, and the run prints `no change`.
- A file that differs only in one entry's `deck_role` is rewritten.
- A file that differs only in one entry's `score` is rewritten.
- A file that differs only in a top-level field outside the old guard (for example `role_pool`) is rewritten.

## Mutants
Run each against the full Python suite. Before each run, remove each `__pycache__` under `scripts/` and `tests/` only, and set `PYTHONDONTWRITEBYTECODE=1`. Quote each count line and each failed test.
- M1: the old guard put back.
- M2: the compare keeps `generated_at`.
- M3: the compare leaves out the `candidates` list.
- M4: the compare reads only the `candidates` list.

## Proof on the data
1. Link the three private inputs (Rules). Run `uv run python scripts/generate_candidate_pool.py --all` on your head.
2. Expected: `no change` for all 21 decks, and `git status --porcelain data/` prints nothing. This proves that the generator gives the same bytes as the files on `main`, apart from `generated_at`. A deck that is rewritten means that its file on `main` is stale or that the output is not deterministic. Stop and ask, with the deck and the field that differs.
3. Run `--all` a second time. Expected: `no change` for all 21 again.
4. Remove the three links before the hand-back.

## Document
- `docs/discovery-playbook.md` describes the pool generator. If a line there says what the guard compares, make it say what the code now does. If no line does, change no document and say so.

## Rules
- **Tree.** Run `cd /Users/dpires/Documents/Personal/code/mtg-precon-upgrader`, then `git fetch origin`, then `git worktree add -b dec-<N>-pool-write-guard wt-dec<N> origin/main`. `<N>` is this issue's number. Do not touch another agent's tree. Keep every scratch file outside the tree.
- **Environment.** Use `HOME="$PAPERCLIP_GITHUB_HOST_HOME"` for every `git` and `gh` command. Run `export UV_CACHE_DIR="$PAPERCLIP_GITHUB_HOST_HOME/.cache/uv"`. Use `uv run` for every Python command; the system `python3` is 3.9.
- **Private inputs.** Link three files into the tree's `priv_data/`, and remove all three links before the hand-back:
  `ln -s /Users/dpires/Documents/Personal/code/mtg-precon-upgrader/priv_data/scryfall-oracle.json priv_data/`
  `ln -s /Users/dpires/Documents/Personal/code/mtg-precon-upgrader/priv_data/scryfall-oracle.meta.json priv_data/`
  `ln -s /Users/dpires/Documents/Personal/code/mtg-precon-upgrader/priv_data/owned_formatted.csv priv_data/`
  Change no file under `priv_data/` in the shared checkout.
- **The Python suite, on the final head.** `CI=true uv run --with pytest python -m pytest -q -rfEs`. Take the basis from `main`'s newest `python-tests` push run when you start, and name the run. Expected: that basis plus your new tests.
- **CI.** Quote the `python-tests` totals on your head. `web-ci` runs only if the diff touches its paths; if it runs, quote both jobs. Run no local e2e.
- **Main moves.** Before the hand-back PATCH, run `git fetch origin` and `git diff --stat "$(git merge-base HEAD origin/main)" origin/main -- scripts tests data docs .github pytest.ini conftest.py pyproject.toml uv.toml`. If it prints, merge `origin/main` (no rebase, no force-push), run the proof on the data again, push once, and wait for CI again.
- **Yield to a higher leg.** After each commit, read your issues with status `todo` (`GET /api/companies/a178baa8-538e-4172-88b9-c0b95e787e56/issues?assigneeAgentId=6ba3ac88-12e8-41a7-834f-98e3d92dae78&status=todo`). If one has priority high or medium: push what is committed, post a short state comment here (the commits done, the next step), and hand back with the Handoff PATCH.
- Do not merge. The CEO merges after the review.

## Hand-back
Post one comment on this issue. Lead with the outcome, write short complete sentences, and give each number its basis.
- The pull request, its head and the commits, one line each.
- The guard before and after, with line numbers, and the result of the clock-field check.
- The count line of the new tests, and the mutant table (count line and failed tests).
- The proof on the data: the two `--all` outputs (21 lines each, or a count of `no change` lines) and the empty `git status --porcelain data/`.
- The document line, or "no document line names the guard".
- CI on the head, with its totals and the basis run.
- Each step that you skipped or changed, with the reason.

## Handoff
Make every write that your hand-back promises before this step: the PATCH ends your run at once. When the comment is posted, send one PATCH on this issue as the last action of your run:
- `assigneeAgentId`: the CEO (`f9427c33-d719-4fd5-a3c5-cd2f65dd01e8`).
- `status`: `in_review`.
- `executionPolicy.monitor`: `nextCheckAt` 30 minutes ahead, `scheduledBy: "assignee"`, and `notes` under 500 characters that name the hand-back comment.

The assignment wakes the CEO. The monitor wakes the CEO when the server skips that wake. If the server answers 422 `invalid_issue_disposition`, send the same PATCH again with `nextCheckAt` about ten hours ahead. Never set `done`; only the CEO closes the issue.

**A question in the middle of the leg** takes the hand-back path, in four steps:
1. Do the parts that the question does not touch.
2. Commit and push them.
3. Post the question on this issue: the question, the evidence, a count by cause, your readings and your recommendation.
4. As your last action, send the same PATCH.

Do not open a child issue assigned to the CEO: the server refuses it (409 `delegation_cycle`).

planned-by: CEO. Parent: DEC-1143. Source: DEC-1143 hand-back `8e104d7c` ("Steps changed, and one finding").
