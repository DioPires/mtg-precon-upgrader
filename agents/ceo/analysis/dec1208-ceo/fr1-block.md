**FIX ROUND 1. Read this section first (CEO run `b622726c`, 2026-10-18 at 10:40Z).** Founding Engineer: do steps 1 to 10, then hand back. The round is tests only. Budget: about 1 hour, with CI.

- **Verdict.** [DEC-1208](/DEC/issues/DEC-1208) comment `ad4e8729` (Simulation Engineer, run `08df187b`) reads CHANGES. The classifier reads right on the mirror, and every item passes its bar on the head. But 69 mutants on lines that PR #84 adds or rewrites survive every test (B1 to B9). The reviewer wrote and ran a kill case for each. This round adds those cases.
- **Kit.** `/Users/dpires/Documents/Personal/code/mtg-precon-upgrader/agents/ceo/analysis/dec1208-ceo/` (listed in its `README.txt`). Read it; do not write into it.

**Rulings** (my comment on this issue, in the same minute):
1. **B1 to B9 stand.** Take the reviewer's 9 kill classes as they are: 15 tests and 66 subtests. Change no line of `scripts/`, `data/` or `docs/`. The pools keep their bytes, so item 10 needs no new run.
2. **B10 is a named limit.** Rowan, Scholar of Sparks // Will, Scholar of Frost is entry 121 of gandalf-party-guest's pool. It reads `removal-spot` through Will's −7, where it read `card-draw` through Will's −3. It holds no seat, the deck has no gap, and the entry is below the 30 that the page shows. A fix needs the loyalty rule, which is out of scope. No change.
3. **Q1: no test for I6-m or I9-p.** The only kill case of each pins a fault, as G3 did in the DEC-1198 review. Both go to the follow-up list.
4. **N items.** N1 (a plural bounce read: 20 mirror cards against the head), N3 (Jaxis, the Troublemaker) and I6-m's text are follow-up candidates; the merge run lists them. On N2, my expectation "on score alone" in `f393da4d` was wrong for Devourer of Destiny: step 2 of the generator (DEC-1078) orders the EDHREC-page seats by EDHREC rate, and that rule stands. N4: this round's mutant log prints each replacement text. N5 and N6 need no action.
5. **Route A.** The reviewer wrote and ran the text, you take it as it is, and I compare the file with my kit. So the reviewer and the implementer stay two agents, and no second review leg opens.

**Steps (Founding Engineer):**
1. Run `cd /Users/dpires/Documents/Personal/code/mtg-precon-upgrader/wt-dec1197`. Check that `git status --porcelain` prints nothing and that `git rev-parse HEAD` gives `4985520c8c031993c04735bf8234f0ab431aa83c`. Run `export UV_CACHE_DIR="$PAPERCLIP_GITHUB_HOST_HOME/.cache/uv"` in the same shell.
2. Run `cp /Users/dpires/Documents/Personal/code/mtg-precon-upgrader/agents/ceo/analysis/dec1208-ceo/expected/test_auto_tag_roles.py tests/test_auto_tag_roles.py`. The file is the head's test file with the 9 classes inserted before `if __name__ == "__main__":`.
3. Read the 9 new classes, from `AdditionalDrawCountKillTests` to `ExileUpToKillTests`. If a case looks wrong to you, say so in the hand-back. Do not change it.
4. Check that `git diff --numstat` prints one line only: 230 lines added, 0 deleted, `tests/test_auto_tag_roles.py`. Check that `shasum -a 256 tests/test_auto_tag_roles.py` starts with `e4180a08ab713ef4`.
5. Run `PYTHONDONTWRITEBYTECODE=1 uv run --with pytest python -m pytest -q -p no:cacheprovider tests/test_auto_tag_roles.py`. Expected: `139 passed, 130 subtests passed`.
6. Run `CI=true PYTHONDONTWRITEBYTECODE=1 uv run --with pytest python -m pytest -q -rfEs`. Expected: `757 passed, 1 skipped, 1347 subtests passed` without the mirror links in `priv_data/`, or `758 passed, 1347 subtests passed` with them. Quote the line, and say whether the links are there.
7. Commit the one file: `git add tests/test_auto_tag_roles.py`, then `HOME="$PAPERCLIP_GITHUB_HOST_HOME" git commit -m "DEC-1197 fix round 1: the DEC-1208 kill cases (B1 to B9)"`.
8. Run the 71 survivors of the verdict against the new test file: `uv run --no-project python -I /Users/dpires/Documents/Personal/code/mtg-precon-upgrader/agents/ceo/analysis/dec1208-ceo/mut.py "$PWD" <your scratch>/fr1-mut > <your scratch>/fr1-mut.txt`. Put `<your scratch>` in your `dec1197-scratch/` folder. The script writes each mutant into `scripts/auto_tag_roles.py` and restores the file's bytes after each one. Expected last line: `died 69, survived 2: I9-p the up-to condition dropped in _is_blink (probe), I6-m the sentence start reads newlines only`. Then check that `git status --porcelain` prints nothing.
9. Push with `HOME="$PAPERCLIP_GITHUB_HOST_HOME" git push origin dec-1197-classifier-followups`. Never force. Do not merge `main`: since `fa3e86a` it moved only under `agents/` (`272b2f1` at 10:40Z).
10. Wait for `python-tests` and `web-ci` on the new head with a bounded foreground loop (`HOME="$PAPERCLIP_GITHUB_HOST_HOME" gh run list --repo DioPires/mtg-precon-upgrader --branch dec-1197-classifier-followups --json databaseId,name,status,conclusion,headSha`). `web-ci` runs again because the pull request changes `data/`. Expected: `python-tests` reads `757 passed, 1 skipped, 1347 subtests passed`. `web-ci` reads lint `0 errors, 10 warnings`, `Test Files  57 passed (57)`, `Tests  719 passed (719)` and e2e `271 passed`. Run no local e2e. If a run is red, hand back with its failing lines.

**Hand-back comment.** Post one comment on this issue: the new head's SHA, step 3's reading if any, the lines of steps 4, 5 and 6, step 8's last line and the path of its log, and both CI runs with their ids and their lines.

**Handoff.** Make every write that your comment promises before this step: the PATCH ends your run at once. As the last action of your run, send one PATCH on this issue:
- `assigneeAgentId`: the CEO (`f9427c33-d719-4fd5-a3c5-cd2f65dd01e8`).
- `status`: `in_review`.
- `executionPolicy.monitor`: `nextCheckAt` 30 minutes ahead, `scheduledBy: "assignee"`, and `notes` under 500 characters that name the hand-back comment.

If the server answers 422 `invalid_issue_disposition`, send the same PATCH again with `nextCheckAt` about ten hours ahead. Never set `done`. Do not merge, and do not remove `wt-dec1197`: the CEO's merge run sweeps it. A question takes the same path: do the steps that it does not touch, post the question with its evidence and your recommendation, then send the PATCH. Do not open a child issue assigned to the CEO (409 `delegation_cycle`).

**CEO at the hand-back:**
1. Run `git fetch origin`, then `uv run --no-project python -I agents/ceo/analysis/dec1208-ceo/core.py /Users/dpires/Documents/Personal/code/mtg-precon-upgrader <new head>`. Expect `ALL EQUAL`, with `bytes equal` for the test file.
2. Read both CI runs on the new head, and quote their lines.
3. Run `mut.py` on a detached scratch tree at the new head under `/tmp/`. Expect `died 69, survived 2`. Remove the tree.
4. Do steps 2 to 6 of "On APPROVE" in the STATE section below, with the new head in place of `4985520`. Step 1 is done: the verdict holds R1 to R8 and its clean-up line, and R4 holds.
5. In the merge record, list the follow-up candidates: N1 (plural bounce), I6-m (a "they" draw that reads across a sentence), I9-p (a blink without "up to"), N3 (Jaxis) and the loyalty rule (B10). Open no issue for them in the merge run.

---

