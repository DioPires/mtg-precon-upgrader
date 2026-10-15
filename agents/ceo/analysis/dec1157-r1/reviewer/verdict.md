**CHANGES.** One B item blocks the merge. No test covers the corrupt-file path, so two mutants of that path survive the full suite. The guard itself is right: items 1, 2, 3, 5 and 6 give the results that the brief expects. The fix is one test, and my kill case K1 is ready to copy.

Basis: PR #67 head `f5eda73`, merged with `origin/main` `822f2da` into the detached commit `b3ab5db` (tree `782416d`, no conflict). `main` has since moved to `32e1057`. Its two new commits are CEO notes and touch no `scripts`, `tests`, `data` or Python root file.

## B items
**B1. The corrupt-file path has no test.** `write_candidates` catches `json.JSONDecodeError` at lines 943 and 944, and line 945 writes the file. The hand-back calls this change on purpose, but no test writes a file that is not valid JSON. So two mutants of the path survive with `652 passed, 1 skipped, 1220 subtests passed`:
- R1: `pass` becomes `return False`, so a corrupt file is never written.
- X4: `pass` becomes `raise`, so a corrupt file crashes the run again (the behaviour of `main`).

Under your ruling, a survivor on the corrupt-file path is a B item.
- Kill case K1, `test_file_that_is_not_valid_json_is_rewritten`. It runs once, writes `{"candidates": [` and a newline over the file, and runs again. It expects `wrote 8 candidates` and a file that parses with 8 candidates.
- On the head: `3 passed`. On R1: `1 failed, 2 passed` (K1 finds `no change`, not `wrote 8 candidates`). On X4: `1 failed, 2 passed` (K1 raises `JSONDecodeError: Expecting value: line 2 column 1 (char 17)`).
- Fix: add K1 to `GapSeatWriteTests` in `tests/test_generate_candidate_pool.py`. With K1 alone, the test file gives `60 passed, 4 subtests passed` and the suite gives `653 passed` (59 and 652, plus 1).

Kill file for every item: `/Users/dpires/.paperclip/instances/default/workspaces/8ea33a50-69a7-4a75-bcc1-245bd1e7c73a/dec1165-review/test_dec1165_kill_cases.py`, blob `d04d750ae358edca6a5c2d4937dff8d35a96d227`. It holds K1, K2 and K3. Its class reuses `GapSeatWriteTests.setUp`, `tearDown`, `_run` and `_edit_pool`, so it runs on the class's invented cards. Each kill run copied the file into `tests/` and ran it alone.

## N items
**N1. No test checks the text format (R5, R6, R7).** The three mutants survive on the head (`652 passed, 1 skipped, 1220 subtests passed` each). The same three mutants of `main`'s write line (`scripts/generate_candidate_pool.py:995` on `origin/main`) survive on a second tree at `822f2da` (`648 passed, 1 skipped, 1220 subtests passed` each). So the gap is not new.
- Kill case K3, `test_written_text_has_two_space_indent_utf8_and_final_newline`. It gives the EDHREC rate file an invented `source` with `—` and `ë`, runs once, and checks that the file text equals `json.dumps(pool, indent=2, ensure_ascii=False) + "\n"`.
- On the head: passes. On R5, R6 and R7: `1 failed, 2 passed` each.
- Under your ruling, K3 goes to DEC-1161.

**N2. A skip can print a false `wrote` line (X2).** X2 removes the `continue` at line 999. The guard still skips the write, so the file stays right. But the run then prints `no change (8 candidates)` and also `wrote 8 candidates`. The tests check only that the `no change` line is present, so X2 gives `652 passed`. Your ruling does not name a survivor on a log line. I class it N because the file and the Apothecary's data stay right.
- Kill case K2, `test_run_that_writes_nothing_prints_no_wrote_line`. `_edit_pool` changes only `generated_at`, and the next run must print `no change (8 candidates)` and no `wrote` line.
- On the head: passes. On X2: `1 failed, 2 passed`. It is cheap to add with the fix of B1.

**N3. A file that is valid JSON but not an object crashes the run.** For `null`, `[]` and `0`, line 940 calls `.pop` on a value that is not a dict. The three errors are `AttributeError: 'NoneType' object has no attribute 'pop'`, `TypeError: pop expected at most 1 argument, got 2` and `AttributeError: 'int' object has no attribute 'pop'`. On `main`, the old guard wrote these three files, because each value is falsy.
- `write_metrics` (`scripts/compute_deck_metrics.py:1264` and `1265`) has the same shape and the same crash.
- Only a hand edit makes such a file. The crash is loud, so no stale data reaches the user. The brief's item 1 names a file that is not valid JSON, and these three files are valid JSON.
- I recommend no change in this pull request. A later leg can check `isinstance(old, dict)` in both writers.
- Demo file (not a kill case): `demo_dec1165_non_object.py` in the same folder, blob `33668838a4bc9353d839b574a0bf39394216bba9`. On the head: `3 failed, 1 passed` (the 3 subtests fail). On `main`: `1 passed, 3 subtests passed`.

## Items
1. **The guard: confirmed.** Line numbers are on the merge tree.
   - The skip: line 937 parses the file, line 938 parses the new text, lines 939 and 940 drop `generated_at` from both, and lines 941 and 942 return False only when the two are equal. No other line returns False.
   - Line 997 calls `write_candidates`. On a skip, line 998 prints `[<deck>] no change (N candidates).` with N from `len(out['candidates'])`, and line 999 goes to the next deck. On a write, lines 1000 to 1002 print the `wrote` line, the same text as on `main`. Control A printed `[anvil-chorus] wrote 205 candidates, top score 71.8.`
   - A file that is not valid JSON: lines 943 and 944 catch `json.JSONDecodeError`, and line 945 writes the file. K1 shows it on the head. B1 covers the missing test, and N3 covers valid JSON that is not an object.
2. **The clock field: confirmed.** `git grep -n -E 'datetime|time[.]|date[.]today' HEAD -- scripts/generate_candidate_pool.py scripts/auto_tag_roles.py` printed 2 lines: line 24 (`from datetime import datetime, timezone`) and line 895 (`"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),`). `scripts/auto_tag_roles.py` gave 0 lines.
   - `generate_candidate_pool.py` imports `argparse`, `csv`, `json`, `re`, `statistics`, `sys`, `datetime`, `pathlib` and `classify` from `auto_tag_roles`. `auto_tag_roles.py` imports `argparse`, `json`, `re`, `sys` and `pathlib`.
   - `scryfall_mirror_updated_at` comes from the mirror meta file (lines 966 and 967). `edhrec_rates.recorded_at` comes from the EDHREC rate file (line 145).
   - So no second field reads the clock. The two `--all` runs of item 5 ran in two processes, each with its own string hash seed, and gave 21 of 21 `no change`. So no other field changes from run to run.
3. **The suite: as expected.** `CI=true uv run --with pytest python -m pytest -q -rfEs` gave `652 passed, 1 skipped, 1220 subtests passed`. The skip is `tests/test_validate_deck_card_names.py:124` (no local mirror). The test file alone gave `59 passed, 4 subtests passed`.
4. **Mutants: see the table.** R1 and X4 are B1. R5, R6 and R7 are N1. X2 is N2. X3 is equivalent.
5. **The proof on the data: as expected.** I linked the 3 private inputs into the tree's `priv_data/`.
   - `--all` run 1: 21 `no change` lines and 0 `wrote` lines. Run 2: the same. `git status --porcelain data/` printed nothing after each run. Each run has 16 other lines, the same in both: the 2 header lines (`Loading mirror...` and `Mirror: 32,116 cards | Owned: 3,522 | GC: 53`), 1 `candidate-pin` line and 13 `gap-seat` lines.
   - Control A: I set the first candidate's `deck_role` (Dwarven Mattock) from `protection` to `stale-role`. `--deck anvil-chorus` printed `[anvil-chorus] wrote 205 candidates, top score 71.8.` `git diff data/` showed one changed line:
     ```
     -  "generated_at": "2026-10-15T15:56:20+00:00",
     +  "generated_at": "2026-10-15T22:12:50+00:00",
     ```
   - Control B: with `main`'s file and the same edit, `--deck anvil-chorus` printed `[anvil-chorus] no change (205 candidates).` The file kept `"deck_role": "stale-role"`. That is the fault that this pull request fixes.
   - After each control I ran `git checkout -- scripts/ data/`, and `git status --porcelain` printed nothing.
   - I removed the 3 links. `find priv_data -type l` counts 0. The 3 files in the shared checkout keep their sizes and dates.
6. **Documents: no line to change.** `git grep -n -i -E 'no change|idempot|write guard|skip.{0,20}write' HEAD -- docs AGENTS.md CLAUDE.md` printed nothing (exit 1, over 12 files). A wider search for `candidates.json` near `unchanged`, `rewrit` or `skip` printed nothing too. No line says what the guard compares.

## Mutant table
Each run used the full suite, after I removed every `__pycache__` under `scripts/` and `tests/`, with `PYTHONDONTWRITEBYTECODE=1`. `git status --porcelain` printed nothing after each restore. Every failed test is in `GapSeatWriteTests`. Each count line ends in `1 skipped, 1220 subtests passed`.

| Mutant | Count line | Failed tests | Class |
|---|---|---|---|
| M1: `main`'s file (the old guard) | `3 failed, 649 passed` | `..._one_deck_role_is_rewritten`, `..._one_score_is_rewritten`, `..._role_pool_is_rewritten` | killed, same as the hand-back |
| M3: the compare leaves out `candidates` | `4 failed, 648 passed` | `..._one_deck_role_...`, `..._one_score_...`, `..._only_in_the_flag_...`, `..._flag_names_another_role_...` | killed, same as the hand-back |
| R1: `pass` becomes `return False` | `652 passed` | none | B1 |
| R2: `if True:` | `7 failed, 645 passed` | all 7 tests of the class (`FileNotFoundError`) | killed |
| R3: `for doc in (old,):` | `2 failed, 650 passed` | `..._only_in_generated_at_...`, `test_second_run_writes_no_file` | killed |
| R4: the last `return True` becomes `return False` | `6 failed, 646 passed` | all but `..._only_in_generated_at_...` | killed |
| R5: no final newline | `652 passed` | none | N1 (survives on `main` too) |
| R6: `indent=1` | `652 passed` | none | N1 (survives on `main` too) |
| R7: `ensure_ascii=True` | `652 passed` | none | N1 (survives on `main` too) |
| R8: the count is `len(out['candidates']) - 1` | `2 failed, 650 passed` | `..._only_in_generated_at_...`, `test_second_run_writes_no_file` | killed |
| X1: `for doc in (new,):` | `2 failed, 650 passed` | `..._only_in_generated_at_...`, `test_second_run_writes_no_file` | killed |
| X2: no `continue` after the `no change` line | `652 passed` | none | N2 |
| X3: `new = out` (no parse of the new text) | `652 passed` | none | equivalent |
| X4: `pass` becomes `raise` | `652 passed` | none | B1 |

The second tree at `origin/main` `822f2da`: no mutant `648 passed`; R5m, R6m and R7m each `648 passed`.

X3 is equivalent. The generator builds the pool from JSON input, with lists, dicts with string keys, strings, numbers, booleans and None. It makes no tuple, no set and no other key type: I read the output dict (lines 885 to 921) and `trim_card` (lines 747 to 774). So `json.loads(json.dumps(out)) == out`, and the parse at line 938 changes no result. X3 also drops `generated_at` from `out` itself, but `new_text` is already built and nothing reads the field later. On the real data, X3 gave 21 of 21 `no change` too.

## Files
All in `/Users/dpires/.paperclip/instances/default/workspaces/8ea33a50-69a7-4a75-bcc1-245bd1e7c73a/dec1165-review/`:
- `test_dec1165_kill_cases.py` (blob `d04d750a`): K1, K2 and K3.
- `demo_dec1165_non_object.py` (blob `33668838`): the demo of N3.
- `kills/` (9 logs: the kill file on the head and on R1, X4, X2, R5, R6, R7; the demo on the head and on `main`) and `kills-summary.txt`.
- `mutants/` (18 logs) with `mutants-head-summary.txt` and `mutants-main-summary.txt`.
- `mutate.py`, `run_mutant.sh`, `run_kill.sh`, `item3-*.log`, `item5-*.log`, `item5-controlA.diff`, `item5-controlB.diff`, `item6-grep.txt`.

## Trees
I removed both scratch trees with `git worktree remove` (no `--force`): `wt-dec1165-review` (the merge `b3ab5db`) and `wt-dec1165-main` (`origin/main` `822f2da`). I did not touch `wt-dec1157`, and I pushed nothing.
