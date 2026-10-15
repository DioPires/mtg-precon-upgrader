## 1. CHANGES

PR #46 at `7ca7e9a` meets every bullet of Ask 1 and Ask 2. Fourteen of my 37 mutants survive the PR's 21 cases. Four of them are on the brief's own list. None is equivalent, so each one is a B item by the mutant rule.

**The script needs no change.** I wrote a kill case for each survivor. All kill cases pass on `7ca7e9a`, and each one fails on its mutant. The fix is one commit: the kill file in place of `tests/test_card_lookup.py`.

- Kill file: `/Users/dpires/.paperclip/instances/default/workspaces/8ea33a50-69a7-4a75-bcc1-245bd1e7c73a/dec1126-review/kill/test_card_lookup.py`
- Blob `43579aa1dd7e8a57bdf9479bfda0ec384c251700`. The PR's file is blob `8cfd61d14f672024ad477fc1c6d7edabc35f82ed`.
- The kill file adds the class `ReviewCases` (10 cases), the imports `sys` and `urllib.error`, and one docstring line. It changes no case of the PR.
- Every path below is under `/Users/dpires/.paperclip/instances/default/workspaces/8ea33a50-69a7-4a75-bcc1-245bd1e7c73a/dec1126-review/` (I write it as `W/`).

## 2. B items

All kill cases are in `W/kill/test_card_lookup.py`, class `ReviewCases`. Most-felt first.

| # | Line(s) | Mutant(s) | Input that a user meets | Kill case |
|---|---|---|---|---|
| B1 | 134, 66 | `sum-faces-untrimmed`, `face-fields-drop-colors`, `face-fields-drop-defense` | `--api` on a two-faced card, or a two-faced card newer than the mirror, prints `image_uris` and `artist` in `card_faces`. That breaks choice 4 ("for both sources"). A field that FACE_FIELDS drops goes unseen. | `test_card_faces_keep_the_mirror_face_fields_for_both_sources` |
| B2 | 99-105 | `find-main-first` | A worktree that holds its own, newer mirror reads the main worktree's older copy. | `test_worktree_with_its_own_mirror_reads_its_own_copy` |
| B3 | 202-206 | `main-error-text-no-details`, `error-text-details-none` | A bad `--search` query prints `HTTP Error 400` without Scryfall's `details` (choice 2 promises them), or appends `: None`. | `test_failed_request_prints_scryfall_details_when_the_answer_has_them` |
| B4 | 115 | `load-front-overwrites` | A mirror where a front face has the spelling of another card's full name. That name then prints the two-part card. Today's mirror has 0 such pairs in 32,116 cards, so nobody meets it today. | `test_full_name_answers_before_a_front_face_of_the_same_spelling` |
| B5 | 71, 165 | `fold-no-strip`, `lookup-no-strip` | `" Sol Ring "` sends a request in place of a mirror hit. `" Brand New Card "` goes out as `exact=%20Brand%20New%20Card%20`. | `test_spaces_around_a_name_do_not_count` |
| B6 | 220 | `main-no-args-accepted` | No name and no `--search` (an empty shell list) exits with 0 and prints nothing, so the caller reads a success. | `test_no_name_and_no_search_are_refused` |
| B7 | 89 | `mw-no-check` | A script outside any repository reads `priv_data/` of its parent folder. | `test_folder_outside_a_repository_does_not_read_the_mirror_of_its_parent` |
| B8 | 91 | `mw-no-oserror` | With no `git` on the PATH, the script stops with a traceback, not the warning. | `test_no_git_on_the_path_goes_to_scryfall` |
| B9 | 124 | `ms-narrow-except` | A meta file that is not JSON, or not an object, stops the script with a traceback, not `mirror unknown`. | `test_meta_file_that_is_not_an_object_prints_mirror_unknown` |
| B10 | 52 | `no-sys-path` | `python -I`, `-P` or `PYTHONSAFEPATH=1` gives `ModuleNotFoundError: scryfall_api`. Under the seven lines' command, Python puts the script's folder on `sys.path` itself, so only these inputs differ. This is also the only case that runs the script as its own process from another folder. | `test_script_runs_by_its_absolute_path_from_another_folder` |

Kill runs: `W/logs/kill-<mutant>.log`. Each one reads `1 failed, 30 passed, 2 subtests passed`. For `ms-narrow-except`, both subtests fail (`2 failed, 31 passed`).

## 3. N items

- **N1.** The `AGENTS.md` "Card pool" line keeps `released<=YYYY-MM-DD` for the session's `scryfall_search` only. The agent-run clause (`--search "QUERY"`) does not say that the query takes the same syntax. I suggest "(Scryfall syntax, `released<=YYYY-MM-DD` included)". A QUERY that holds `"` (for example `o:"draw a card"`) also needs single outer quotes.
- **N2.** `agents/ceo/memory/patterns.md:9` on `origin/main` says "Verify card text via Scryfall (`scryfall_card_by_name` MCP)". It is your file, like TOOLS.md. The routing census did not name it.
- **N3. `main` moved after the routing.** PR #40, PR #47 and others merged. The guard from `0c059b1` to `origin/main` `7b7bfa2` now lists 19 files, so step 2 of your merge plan (update-branch) applies. The merge tree `6e6c1da` is clean.
  - Suite on that tree: `539 passed, 1 skipped, 1189 subtests passed`.
  - With the kill file: `549 passed, 1 skipped, 1191 subtests passed`.
  - PR #51 is still open. `main` still holds the text `wait 30 seconds or more`.
- **N4. Root `AGENTS.md` file map: nothing.** The map on `origin/main` lists no script at all, only `web/` and `data/` rows. A script is named at the step that runs it, and this PR does that.
- **Shared checkout (not in scope):** I see no better way than your merge step.

## 4. Count lines

- Item 1 (tree at `7ca7e9a`): `447 passed, 1 skipped, 1128 subtests passed in 13.54s` (`W/item1-suite.log`).
- Item 2 (socket connect refused): `21 passed in 0.47s` (`W/item2-nosocket.log`).
- Kill file on a `7ca7e9a` copy, socket connect refused: `31 passed, 2 subtests passed in 0.47s` (`W/logs/kill-base-nosocket.log`).
- Full suite with the kill file: `457 passed, 1 skipped, 1130 subtests passed in 14.74s` (`W/logs/kill-base-full-suite.log`).

### Item 3: the script against Ask 1

| Ask 1 | Reading | Lines |
|---|---|---|
| Fields and `source` | met | 61-62, 128-138; `source` 119-125 and 170 |
| 1. Mirror first; case and accents; front face finds `A // B` | met | 69-72, 108-116, 161-164 |
| 2. A miss sends one `/cards/named?exact=` through the helper; a 404 prints `not found: NAME` and goes on | met | 141-153, 165-168 |
| 3. `ScryfallRateLimited`: exit code 1, the helper's text, no later request | met | 236-238. Nothing in `lookup()` or `lookup_api()` catches it. |
| 4. `--api` skips the mirror | met | 224 |
| 5. `--search`: one request, first page, `total_cards`, then `name \| mana_cost \| type_line` | met | 182-196 |
| 6. The mirror path, then the main worktree's copy, then one warning | met | 80-105, 225-228 |
| 7. Exit codes 0, 2 and 1 | met | 171, 237, 242 (191 for an empty search) |

### Item 4: the tests against Ask 2

| Ask 2 | Cases |
|---|---|
| a | `MirrorCases::test_name_in_the_mirror_prints_from_the_mirror_with_no_request` |
| b | `test_case_and_accents_match`, `test_front_face_finds_its_two_part_card` |
| c | `ApiCases::test_missing_name_sends_one_named_exact_request`, `test_two_missing_names_keep_the_600ms_wait`, `test_api_flag_sends_one_request_for_a_name_in_the_mirror` |
| d | `test_404_prints_not_found_and_the_next_name_still_prints` |
| e | `test_429_on_the_first_of_three_missing_names_ends_the_run` (also `test_stop_of_another_process_sends_nothing_and_ends_the_run`, `test_script_exits_with_main_code`) |
| f | `SearchCases::test_search_sends_one_request_to_cards_search` |
| g | `WorktreeCases::test_worktree_without_mirror_reads_the_main_worktree_copy`, `test_without_any_mirror_every_name_goes_to_scryfall` |

Every part of a to g has a case. The lines that no case checked are outside a to g; they are the B items.

## 5. Mutant table

Each copy came from `git archive 7ca7e9a | tar -x` in an empty folder. Before each run I removed every `__pycache__` folder and set `PYTHONDONTWRITEBYTECODE=1`. Then I ran `uv run --with pytest python -m pytest -q -rfEs -p no:cacheprovider tests/test_card_lookup.py`. Logs: `W/logs/<mutant>.log`. Diffs: `W/diffs/<mutant>.diff`. Harness: `W/tools/`.

**Controls.** I wrote the implementer's mutant script over a fresh copy; each one differs from `7ca7e9a` only by its mutation. All three match the hand-back.

| Control | Result | Quote |
|---|---|---|
| M1 (line 161: `card = None`) | 8 failed | `test_name_in_the_mirror_prints_from_the_mirror_with_no_request`: `AssertionError: 2 != 0` |
| M2 (`urlopen`, not the helper) | 6 failed | `test_two_missing_names_keep_the_600ms_wait`: `0.0 != 0.6 within 9 places`. `test_429_on_the_first_of_three_missing_names_ends_the_run`: `'wait 30 seconds or more' not found in 'Scryfall request failed: HTTP Error 429: status 429\n'` |
| M3 (catches `ScryfallRateLimited`) | 1 failed | `test_429_on_the_first_of_three_missing_names_ends_the_run`: `AssertionError: 3 != 1` |

**My mutants.** 37 in total: 23 from the brief's list and 14 of my own. The PR's cases kill 23 of them. The 14 survivors die on the kill file. None is equivalent.

| Mutant | Line | Killed by (PR's cases) / kill case |
|---|---|---|
| fold-no-accent-strip | 72 | `test_case_and_accents_match` (+1) |
| fold-no-casefold | 71 | `test_case_and_accents_match` (+2) |
| load-no-front-faces | 115 | `test_front_face_finds_its_two_part_card` |
| load-front-overwrites | 115 | survives; kill: `test_full_name_answers_before_a_front_face_of_the_same_spelling` |
| mw-skip-main | 102 | `test_worktree_without_mirror_reads_the_main_worktree_copy` |
| mw-no-parent | 94 | `test_worktree_without_mirror_reads_the_main_worktree_copy` |
| find-main-first | 99-105 | survives; kill: `test_worktree_with_its_own_mirror_reads_its_own_copy` |
| ms-wrong-key | 123 | `test_name_in_the_mirror_prints_from_the_mirror_with_no_request` (+2) |
| ms-no-fallback | 121-125 | `test_mirror_without_meta_file_still_prints` |
| sum-all-legalities | 131 | `test_name_in_the_mirror_prints_from_the_mirror_with_no_request` |
| sum-faces-untrimmed | 134 | survives; kill: `test_card_faces_keep_the_mirror_face_fields_for_both_sources` |
| api-full-name | 143 | `test_two_part_name_goes_out_as_its_front_face` |
| api-no-full-name-check | 151 | `test_two_part_name_goes_out_as_its_front_face` |
| api-none-on-every-http-error | 147 | `test_other_failed_request_ends_the_run` |
| lookup-exit-0-on-missing | 171 | `test_404_prints_not_found_and_the_next_name_still_prints` (+1) |
| lookup-break-after-404 | 168 | `test_404_prints_not_found_and_the_next_name_still_prints` |
| search-no-404-branch | 189 | `test_search_that_finds_nothing_exits_with_2` |
| search-404-exit-0 | 191 | `test_search_that_finds_nothing_exits_with_2` |
| search-mana-cost-top-only | 177-179 | `test_search_sends_one_request_to_cards_search` |
| main-no-warning | 227 | `test_without_any_mirror_every_name_goes_to_scryfall` (+1) |
| main-api-reads-mirror | 224 | `test_api_flag_sends_one_request_for_a_name_in_the_mirror` |
| main-oserror-exit-0 | 242 | `test_other_failed_request_ends_the_run` |
| main-error-text-no-details | 202 | survives; kill: `test_failed_request_prints_scryfall_details_when_the_answer_has_them` |
| *own:* fold-no-strip | 71 | survives; kill: `test_spaces_around_a_name_do_not_count` |
| *own:* lookup-no-strip | 165 | survives; kill: `test_spaces_around_a_name_do_not_count` |
| *own:* mw-no-check | 89 | survives; kill: `test_folder_outside_a_repository_does_not_read_the_mirror_of_its_parent` |
| *own:* mw-no-oserror | 91 | survives; kill: `test_no_git_on_the_path_goes_to_scryfall` |
| *own:* ms-narrow-except | 124 | survives; kill: `test_meta_file_that_is_not_an_object_prints_mirror_unknown` (2 subtests) |
| *own:* main-no-args-accepted | 220 | survives; kill: `test_no_name_and_no_search_are_refused` |
| *own:* main-names-and-search-accepted | 221 | `test_names_and_search_together_are_refused` |
| *own:* search-no-quote | 184 | `test_search_sends_one_request_to_cards_search` |
| *own:* error-text-no-suppress | 203 | `test_other_failed_request_ends_the_run` |
| *own:* ratelimit-to-stderr | 237 | `test_429_on_the_first_of_three_missing_names_ends_the_run` (+3) |
| *own:* no-sys-path | 52 | survives; kill: `test_script_runs_by_its_absolute_path_from_another_folder` |
| *own:* face-fields-drop-colors | 66 | survives; kill: `test_card_faces_keep_the_mirror_face_fields_for_both_sources` |
| *own:* face-fields-drop-defense | 66 | survives; kill: `test_card_faces_keep_the_mirror_face_fields_for_both_sources` |
| *own:* error-text-details-none | 205 | survives; kill: `test_failed_request_prints_scryfall_details_when_the_answer_has_them` |

## 6. The five choices

1. **Accept.** A `//` name goes out as its front face and counts only on a full-name match. That is the rule of `fetch_card_metadata.py` and of DEC-1072 live reading 1. Two cases check it.
2. **Accept.** Any other failed request ends the run with exit code 1. The `details` part had no case; that is B3, and my kill case now checks it.
3. **Accept.** A caller can tell the two meanings of exit code 2 apart by the output streams (probe with `FakeScryfall`, 0 live requests, `W/logs/probe-choice3.log`):
   - A missing name writes `not found: NAME` to stdout, and a search that finds nothing writes `total_cards: 0`. stderr stays empty.
   - Bad arguments (names with `--search`, an unknown flag, no argument) write nothing to stdout. stderr gets `usage: ...` and `error: ...`.
   - The no-mirror warning also goes to stderr, but it never holds `usage:`.
4. **Accept.** The "for both sources" part had no case; that is B1, and my kill case now checks it.
5. **Accepted by you.** Item 8 ran under uv's Python 3.14.5.

## 7. The instruction lines

`--help`: `usage: card_lookup.py [-h] [--api] [--search QUERY] [NAME ...]`. Every command below uses `uv run python`, a flag from that usage, and double quotes around NAME or QUERY.

| Line (at `0c059b1`) | (a) session uses the tools | (b) agent run uses the script, absolute path from eternities-mtg-app | (c) no `curl`, nothing outside `scryfall_api.py` | Other rules kept | Command |
|---|---|---|---|---|---|
| `AGENTS.md:100` Card pool | yes (`scryfall_search`) | yes | yes | `released<=YYYY-MM-DD` kept, for the session only (N1) | `--search "QUERY"`: ok |
| `AGENTS.md:101` Card text validation | yes (`scryfall_card_by_name`; `scryfall_collection` for bulk) | yes, and it says "mirror first" | yes | "ALWAYS verify", "Never assume", bulk route | `"NAME" ["NAME" ...]`: ok |
| `AGENTS.md:159` Research source 6 | yes (all three tools) | yes | yes | verify names, oracle text, card data | names or `--search QUERY`: ok |
| `AGENTS.md:174` Review step 5 | yes | yes | yes | "never trust the playbook's pattern match" | `"NAME"`: ok |
| `agents/founding-eng/AGENTS.md:25` | yes | yes | yes | "verified before inclusion" | `"NAME"`: ok |
| `agents/frontend-eng/AGENTS.md:40` | yes | yes | yes | "verified before landing" | `"NAME"`: ok |
| `agents/sim-eng/AGENTS.md:44` | yes | yes | yes | "Verify ... when classifying cards (threats, draw, interaction)" | `"NAME"`: ok |

On the merge tree `6e6c1da` with today's `main`, all seven lines are present, at `AGENTS.md:114`, `:115`, `:174` and `:189`. Word diff: `W/item7-word-diff.txt`.

## 8. Item 8 output

I ran this from `/Users/dpires/Documents/Personal/code/eternities-mtg-app`, without `HOME` and without `UV_CACHE_DIR` (`W/logs/item8.log`). Result: exit code 0, three mirror lines, and `last_answer` unchanged, so 0 requests.

```
$ uv run python -c 'import sys; print(sys.version.split()[0], sys.executable)'
3.14.5 /Users/dpires/.local/bin/python3.14
$ cat /tmp/scryfall-limit/state.json
{"last_answer": 1792059781.347265, "last_slow_answer": 1792059781.347265}
$ uv run python /Users/dpires/Documents/Personal/code/mtg-precon-upgrader/wt-dec1126-review/scripts/card_lookup.py "Sol Ring" "lorien revealed" "Fire"
{"name": "Sol Ring", "mana_cost": "{1}", "cmc": 1.0, "type_line": "Artifact", "oracle_text": "{T}: Add {C}{C}.", "power": null, "toughness": null, "loyalty": null, "defense": null, "color_identity": [], "legalities": {"commander": "legal"}, "card_faces": null, "source": "mirror 2026-10-08T09:01:59.811+00:00"}
{"name": "Lórien Revealed", "mana_cost": "{3}{U}{U}", "cmc": 5.0, "type_line": "Sorcery", "oracle_text": "Draw three cards.\nIslandcycling {1} ({1}, Discard this card: Search your library for an Island card, reveal it, put it into your hand, then shuffle.)", "power": null, "toughness": null, "loyalty": null, "defense": null, "color_identity": ["U"], "legalities": {"commander": "legal"}, "card_faces": null, "source": "mirror 2026-10-08T09:01:59.811+00:00"}
{"name": "Fire // Ice", "mana_cost": "{1}{R} // {1}{U}", "cmc": 4.0, "type_line": "Instant // Instant", "oracle_text": null, "power": null, "toughness": null, "loyalty": null, "defense": null, "color_identity": ["R", "U"], "legalities": {"commander": "legal"}, "card_faces": [{"name": "Fire", "mana_cost": "{1}{R}", "type_line": "Instant", "oracle_text": "Fire deals 2 damage divided as you choose among one or two targets."}, {"name": "Ice", "mana_cost": "{1}{U}", "type_line": "Instant", "oracle_text": "Tap target permanent.\nDraw a card."}], "source": "mirror 2026-10-08T09:01:59.811+00:00"}
$ echo $?
0
$ cat /tmp/scryfall-limit/state.json
{"last_answer": 1792059781.347265, "last_slow_answer": 1792059781.347265}
```

## 9. Trees and folders removed

- `wt-dec1126-review`. `status --porcelain` printed nothing. I ran `git worktree remove` without `--force`, then `git worktree prune`.
- `/tmp/dec1126-review` (5.7 GB: the mutant copies, the merge-tree copy and scratch files). Everything kept is in `W/`.
- I did not touch `wt-dec1124` (still at `7ca7e9a`) or `/tmp/dec1124-mutants` (I only read the implementer's three mutant files from it).
- I sent no request to `api.scryfall.com`.
