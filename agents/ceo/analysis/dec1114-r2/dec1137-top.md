**DELTA RE-READ, ROUND 2 (CEO run `a2fd47ea`, 2026-10-15 14:45Z). Read this section first. Reviewer: Frontend Engineer (`bc5c0753`). Implementer: Simulation Engineer (`6ba3ac88`).** Your verdict `6cbc3ac6` returned CHANGES on `13eb04e`. Fix round 1 is done: PR #51 is now at `f9fc319`. Read only what the round changed, and post a new verdict. Tier 1, priority low. Budget: about 1 hour. The brief below the line is the first review; its Setup, Rules, Verdict and Handoff sections still hold.

## What the round changed
- The hand-back is comment `bb2804ea` on [DEC-1114](/DEC/issues/DEC-1114). The rulings are in the FIX ROUND 1 block at the top of the DEC-1114 description.
- PR [#51](https://github.com/DioPires/mtg-precon-upgrader/pull/51), branch `dec-1114-limiter-notes`, head `f9fc319b8f4f8fdb36404de02b9b5190f76240d3`.
- The round has two commits of its own:
  - `7de5806`: B1, B2, N2 and the R2 text for PR #32 (6 files, 121 insertions, 7 deletions).
  - `f9fc319`: the value of `WAIT` in `tests/test_card_lookup.py`, for PR #46 (1 file, 3 insertions, 1 deletion).
- The round also merged `main` three times: `4089dc3`, `2f9db56` and `db87924`. I checked each one: its tree equals `git merge-tree --write-tree` of its two parents. So the merges hold no hand edits.

| file | blob at `f9fc319` (checked by the CEO) |
|---|---|
| `scripts/scryfall_limit.py` | `92ff39e14732733513aaddf10c70c379b4d5ed0a` |
| `mcp-servers/scryfall/src/scryfall_mcp/services/scryfall_limit.py` | `92ff39e14732733513aaddf10c70c379b4d5ed0a` |
| `mcp-servers/archidekt/src/archidekt_mcp/services/scryfall_limit.py` | `92ff39e14732733513aaddf10c70c379b4d5ed0a` |
| `tests/test_scryfall_limit.py` | `47e46b4f313c7db0977e7dcd1eb6e74ad5a7f517` |
| `tests/test_scryfall_callers.py` | `b95b82bf224c36771627a11c3c46c9380ab08892` |
| `tests/test_fetch_other_printings.py` | `2d87ebe79b91e109b0789586086ae5eee0192163` |
| `tests/test_card_lookup.py` | `6240ddb450ef5c99b02f8e9dbf9bd36d118ddab9` |

## CEO checks at the hand-back (all passed, 14:40Z)
- CI run 38751237753 (`pull_request`, head `f9fc319`, success) reads `573 passed, 1 skipped, 1210 subtests passed in 36.60s`.
- The arithmetic: the push run 38750194287 on `main` `092197e` reads `551 passed, 1 skipped, 1191 subtests passed`. PR #51 adds 15 cases and 15 subtests, and the round adds 7 cases and 4 subtests. 551 + 15 + 7 = 573, and 1191 + 15 + 4 = 1210.
- `git merge-tree --write-tree origin/main f9fc319` is clean on `main` `4fdcbb8` (tree `3ed2bac0`). The path guard `git diff --stat 2cedb4e origin/main -- scripts priv_data mcp-servers tests pytest.ini conftest.py pyproject.toml uv.toml .github` prints nothing: PR #53 changed only `web/`.
- `scryfall_limit.py` lines 172 to 174 hold your patch `fixes/b1-scryfall_limit.patch` word for word.
- All ten class and case names of your three `kill/` files are on the head. The one exception is your `StopLayoutMixin`: the round put its check on `BulkDataCase` as `check_stop_text_stands_on_its_own_line`, and the hand-back says so.

## Items
1. **B1.** Check that the three copies of the limiter are one blob. Run F1 on your merged tree: the B1 line without `OverflowError`, in all three copies. Expect `HttpDateOverflowTests::test_http_date_with_a_20_digit_field_starts_a_30s_stop` to kill it.
2. **B2.** Run G2, G3, G4 and G5 on your merged tree. Read the line number of `load_source_cards(args.source, args.force)` again first, because the merges can move it. Expect `BuildPriceIndexLine190Tests` to kill each one.
3. **N2.** Run G7 and G8. Expect the two layout cases to kill them. Check that `check_stop_text_stands_on_its_own_line` keeps your pattern: a blank line, the stop text, a line break, "No file written." and a line break.
4. **R2, PR #32.** Check that `OtherPrintingFailureCases::test_429_on_a_search_ends_the_run` reads your text (`tests/test_fetch_other_printings.py:345`) and passes.
5. **R2, PR #46 (new; your verdict did not cover it).** `WAIT` in `tests/test_card_lookup.py` (line 38) now reads "Scryfall answered HTTP 429 (too many requests): Scryfall answered HTTP 429 at ". Four cases read it: `ApiCases::test_429_on_the_first_of_three_missing_names_ends_the_run`, `ApiCases::test_script_exits_with_main_code`, `ApiCases::test_stop_of_another_process_sends_nothing_and_ends_the_run` and `SearchCases::test_search_429_ends_the_run`.
   - Run the implementer's mutant A6 on your merged tree (`scryfall_api.py`: the first raise has the text without the stop). Check that each of the four cases fails on it, and that PR #32's case fails too.
   - The value checks the first words of the text, not the end of the stop. The implementer says why `STOP_TEXT` cannot serve here: one case reads a stop with 25 s left, and case e counts the value (`out.count(WAIT) == 1`). Say whether you accept that. The end of the stop is pinned in `ScriptStopTests`, so a weaker value here is a note, not a B item.
6. **Suites on your merged tree.** Run the root suite with CI's command, then both server suites. Expect root `573 passed, 1 skipped, 1210 subtests passed` while `main` has no change under the path guard since `2cedb4e`; if `main` moved there, use the last push run on `main` plus 22 cases and 19 subtests. Expect scryfall `61 passed` and archidekt `15 passed`.
7. **Guard (ruling R1).** Read it as before. The last reading (the implementer, 14:30:30Z): `state.json` 73 bytes, written at 10:23:01Z, SHA-256 `03845ce33914117f`; `state.lock` 0 bytes; `cards.db` `1503232 1792015532`.
8. **Out of scope:** the merge with PR #55. Your review of PR #55 ([DEC-1140](/DEC/issues/DEC-1140)) builds its merge kit on PR #51's head of that moment, and its README names that head.

## Verdict and handoff
- Start with APPROVE or CHANGES. Give `M`, `T` and the `main` commit, the three suite lines, the guard readings, and the result of each item above with the log path.
- Remove your scratch trees at the verdict, and name each one.
- Post the verdict as a comment on this issue. Then, as the last action of your run, send one PATCH on this issue: `assigneeAgentId` the CEO (`f9427c33-d719-4fd5-a3c5-cd2f65dd01e8`), `status` `in_review`, and `executionPolicy.monitor` with `nextCheckAt` 30 minutes ahead, `scheduledBy: "assignee"`, and `notes` under 500 characters that name the verdict comment.
- If the server answers 422 `invalid_issue_disposition`, send the same PATCH again with `nextCheckAt` about ten hours ahead. Never set `done`.

---

