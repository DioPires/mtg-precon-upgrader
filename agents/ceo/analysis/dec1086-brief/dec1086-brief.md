**Started (CEO run `0e49d961`, 2026-10-15, at the close-out of [DEC-1079](/DEC/issues/DEC-1079)). Do the work below.** PR #32 merged as `4a21353`, so `card-metadata.json` now takes a missing price from another printing, and this brief carries that rule to the price index. The old brief is below the line.

**Outcome wanted.** Each Commander-legal card that has a non-foil price on some paper printing has a row in `data/spellbook/price-index.json`, by the same rule as `data/card-metadata.json`, and the index is fresh again. Implementer: Simulation Engineer (`6ba3ac88`). Reviewer: the CEO names one at the hand-back, not you. One pull request; nothing under `web/src`. Tier 1, priority low. Budget about 3 hours.

## Facts (read on `main` `4a21353`)
- `scripts/build_price_index.py` reads Scryfall's `oracle_cards` export (one printing for each card), keeps the Commander-legal cards, and skips a card whose printing has neither non-foil price (`build_index`, line 118). No test file covers the script (`git grep build_price_index tests` prints nothing).
- Its one request to `api.scryfall.com` (`fetch_json`, line 76, called at line 143) does not go through `scripts/scryfall_api.py`. The download comes from `data.scryfall.io`, which has no rate limit; the helper refuses every host but `api.scryfall.com`.
- The committed index comes from the export of 2026-09-05 (`price-index.meta.json`: `scryfall_updated_at` `2026-09-05T09:01:53.771+00:00`, `keyCount` 32,141, `pricedEur` 32,100, `pricedUsd` 32,125). On 2026-10-15 it is 40 days old.
- 68 of the 1,556 names of `card-metadata.json` have no row. After PR #32, 67 of them have a `usd` and a `eur` in `card-metadata.json`. Commodore Guff has neither: it has only foil printings. (My read: `name_keys()` of each name against the index's keys.)
- `_price` (line 90) reads `"0"`, `"0.0"` and every value at or below 0 as no price. Since PR #32, `card-metadata.json` takes 0.00 as a price (DEC-1112 B3, kill case S4).
- **The web app.** `web/src/data/prices.ts` holds the index in memory only and never in `localStorage` (lines 10 to 12). It fetches the index with `?v=<scryfall_updated_at>` (lines 68 to 70). So this change needs no `STORAGE_PREFIX` bump, but each new export must change `scryfall_updated_at`.
- **What the user sees.** In the Combo Lab's "Completions", a card with no row reads `· no price yet` (`web/src/routes/ComboLab.tsx:1753`). It passes every "Max price" value, because the filter never cuts a card without a price (`web/src/lib/nearMissComplete.ts:251-254`). So today a budget filter passes a shock land.

## The rule (my ruling on DEC-1112's R4)
DEC-1112 named R4: `card-metadata.json` holds two price meanings. A card whose default printing has a price keeps that price, which need not be the lowest. A card whose default printing has none gets the lowest price of another printing. The index could take either meaning; I choose the same two-step rule as `card-metadata.json`:
1. For each currency by itself, take the non-foil price of the card's printing in `oracle_cards`, as today.
2. When that price is missing, take the lowest non-foil price among the card's printings in `default_cards` that count. A printing counts when `games` holds `paper`, `released_at` is on or before the date of the `default_cards` export, and `set_type` is not `memorabilia`.
3. Never take a foil or etched price.

Why: one card then shows one price on /shopping and in the Combo Lab, from one rule. The cost: a price can sit above the cheapest copy when the default printing costs more (Wayfarer's Bauble read `usd` 5.79 on `main` before PR #32, and 0.31 from another printing after it). Name that limit in the hand-back.

`default_cards` holds every printing, so the fill needs no page proof and no `/cards/search` request.

## Ask
1. **Second source.** Read `default_cards` beside `oracle_cards`. Stream its `.jsonl.gz` line by line, and keep only what the fill needs for each `oracle_id`. Do not hold the whole export in memory: the Mac is shared.
2. **The `oracle_id` of a printing.** A `reversible_card` printing carries its `oracle_id` on each face only. Take the top-level `oracle_id`, else `card_faces[0]["oracle_id"]` (DEC-1112 B1). Join the fill to the Commander-legal `oracle_cards` entries by `oracle_id`. Keep the name keys and their order as today (full names first, then the `//` faces).
3. **The `/bulk-data` request goes through `scripts/scryfall_api.py`** (`scryfall_api.request`). The two downloads from `data.scryfall.io` go direct, as today.
4. **Local sources for every run without a request.** Give the script one argument for each export (for example `--oracle-source` and `--default-source`), so that the tests and the reviewer run it with no request. Keep `--force`. The "already current" check reads both exports' times.
5. **The meta file.** Keep `scryfall_updated_at` as the `oracle_cards` export's time (the web app's cache buster reads it). Add the `default_cards` export's time and address, and the count of prices that came from another printing, for each currency. Bring the `note` and `source` up to date.
6. **Atomic writes.** Write each file to a temporary file in the same folder and `os.replace` it, the meta file last (the DEC-1080 N1 rule that PR #32 applied to `card-metadata.json`). Today the meta file is written in place.
7. **0.00.** Count the non-foil prices at or below 0 in both exports. If there are none, keep `_price` as it is and name the difference from `card-metadata.json` as a known limit. If there are some, ask (see the Handoff section).
8. **Cases and mutants.** Add `tests/test_build_price_index.py`, with small exports in memory or in a temporary folder, and no request: a socket guard must fail any connect. Cover at least:
   - the default printing's price stays, also when another printing is cheaper;
   - a missing price takes the lowest price of a printing that counts, for each currency by itself;
   - a memorabilia printing, a printing with no `paper` in `games`, and a printing released after the export's date do not count;
   - a foil or etched price never counts;
   - a `reversible_card` printing joins by its front face's `oracle_id`;
   - a card with no price on any printing that counts gets no row;
   - the name keys and their order do not change;
   - the meta file's counts, and the order of the two moves.
   For each line that the pull request adds or rewrites, make mutants. Run each one with `PYTHONDONTWRITEBYTECODE=1` after you remove every `__pycache__`, on a clone of your tree. In the hand-back, give a table: each mutant, and the case that kills it or the reason that it is equivalent.
9. **One live run.** When the cases pass, run the script once against the live exports, with no `--source`. Save both downloaded files in `$PAPERCLIP_GITHUB_HOST_HOME/.paperclip/instances/default/workspaces/6ba3ac88-12e8-41a7-834f-98e3d92dae78/dec1086-scratch/live/`, so that the reviewer runs the script on them with no request. Commit the index and the meta file. A second live run needs my word on this issue first.
10. **One rule for both files.** Check the fill against PR #32's saved run 2 (`dec1079-scratch/live/run2/` in your workspace):
    - For each card whose run 2 search page has `has_more` false, compare the set of printing ids that count on the page with the set that counts in `default_cards`. Give the differences, each with its cause (a printing released after 2026-10-14, a variation, a language, or another cause).
    - For the 1,556 names of `card-metadata.json`, count how many have the same default printing in `oracle_cards` as in `card-metadata.json`. The printing id is in the `image` address. Name the names that differ.
11. **Counts before and after.** Give rows, rows with EUR, rows with USD, the prices from another printing, and the names of `card-metadata.json` with no row (68 today; name the ones that stay).
12. **What moves in the web app.** Read it from the files; start no browser. Give, for each deck's Combo Lab completions, the number of cards that gain a price, and the "Max price" values that now cut a card that passed before. Name every committed file, test or reading that holds a price from the index (`git grep` under `web/`, `data/` and `tests/`).

## Rules
1. **Scryfall.** Send no request to a Scryfall host except the live run of item 9: one `/bulk-data` request through the helper and the two downloads. Use no card tool.
2. **Start no browser and no preview server, and run no local e2e.** CI's `web-ci` is the record for the web side.
3. **Environment.** Export `HOME="$PAPERCLIP_GITHUB_HOST_HOME"` for every `git` and `gh` command. Use `uv run` for every Python command.
4. **Tree.** Work in `wt-dec1086` only. Keep scratch files in `/tmp/dec1086/`, and the files that the reviewer needs in `dec1086-scratch/` in your workspace.
5. **One pytest process at a time.** Export a new, empty `SCRYFALL_LIMIT_DIR` for each test run. The live run of item 9 uses the default folder, so that it shares the limit with the card tools.
6. Change no file under `web/src`, and do not change `card-metadata.json`.

## Setup
1. `cd /Users/dpires/Documents/Personal/code/mtg-precon-upgrader`
2. `git fetch origin`
3. `git worktree add -b dec-1086-price-index-fill wt-dec1086 origin/main`
4. `mkdir -p /tmp/dec1086`
5. The suite is CI's command, from the tree's root: `CI=true uv run --with pytest python -m pytest -q -rfEs`. On `main` at `4a21353`, CI's push run 38716323591 reads `486 passed, 1 skipped, 1189 subtests passed`. The expected line on your head is that plus your new cases. If `main` gained tests, add them and name the cause.

## Hand-back
Before the hand-back PATCH, run `git fetch origin`, then this guard. It names the writer's paths and the readers of the index: `git diff --stat "$(git merge-base HEAD origin/main)" origin/main -- scripts tests data .github pytest.ini web/src/data/prices.ts web/src/lib/nearMissComplete.ts web/src/routes/ComboLab.tsx web/src/__tests__ web/tests web/README.md`. It must print nothing. If it prints, merge `main` (no rebase), run the suite again, push and wait for CI.

Post one comment that holds:
- the pull request number, its head, and the blob id of each file that it changes;
- the suite's count line, and CI's run ids with their total lines (`python-tests`, and `web-ci` because `data/` changes);
- the mutant table;
- the live run: the time, both export addresses and their `updated_at`, the saved files' paths and SHA-256, and the command that rebuilds the committed files from them with no request;
- items 7, 10, 11 and 12, and the known limits.

## Handoff
- Post the hand-back comment first. Then send one PATCH on this issue as the last action of your run: `assigneeAgentId` the CEO (`f9427c33-d719-4fd5-a3c5-cd2f65dd01e8`), `status` `in_review`, and `executionPolicy.monitor` with `nextCheckAt` 30 minutes ahead, `scheduledBy: "assignee"`, and `notes` under 500 characters that name the hand-back comment.
- If the server answers 422 `invalid_issue_disposition`, send the same PATCH again with `nextCheckAt` about ten hours ahead. Never set `done`.
- For a question in the middle of the leg: do the parts that it does not touch, commit and push, post the question on this issue (question, evidence, readings, your recommendation), and hand back with the same PATCH. Do not open a child issue assigned to the CEO: the server refuses it (409 `delegation_cycle`).

## CEO: at the hand-back
The Simulation Engineer does nothing under this heading.
1. Read the guard, the blob ids and CI's totals. Rebuild the committed files from the saved exports with the hand-back's command in a detached scratch tree, under a socket guard, and compare the blob ids.
2. Name a reviewer who is not the implementer. The review brief asks for the reviewer's own read of the fill on the saved `default_cards`, mutants on a clone, and items 10 to 12 again.
3. Owed at this issue's close-out: refresh and start [DEC-1138](/DEC/issues/DEC-1138) (the same engineer; tests only).

planned-by: CEO. Parent: DEC-1072. Source: DEC-1073 item 9 (hand-back `d118725b`); the rule from DEC-1079 (PR #32) and DEC-1112 R4.

---

## The old brief (2026-10-14, replaced by the section above)

**Outcome wanted.** Each card that has a non-foil price on some printing has a row in `data/spellbook/price-index.json`, and the index is fresh again.

- `scripts/build_price_index.py` reads Scryfall's `oracle_cards` bulk export, which holds one printing for each card, and drops a card whose printing has no non-foil price.
- The committed index came from the export of 2026-09-05; 68 deck-pool names had no row on `1e9df22`.
- Bloodline Recollector's printing (set `fra`) was released on 2026-10-02, 27 days after the export. For the other 67 names the export's printing was not checked.
- Source: DEC-1073 item 9 (the Founding Engineer's hand-back, comment `d118725b`).
