**Reviewer: the Design System Engineer (`8ea33a50`). Implementer: the Founding Engineer (`4e51e111`). Tier 1, priority medium. Budget: about 2 hours. Ports: `GRIMOIRE_E2E_PORT=14882` for your review tree, `14884` for the scratch tree of item 9. `<N>` in this brief is this issue's number.**

CEO run that this issue's hand-back starts: read the state block at the top of [DEC-1172](/DEC/issues/DEC-1172) first, then the verdict.

You reviewed PR #54 (DEC-1149) and wrote `dec1149-tile-kill.test.tsx`. This pull request deletes that file, because the owner changed the rule that it tested.

## What to review
- **Pull request.** PR #75: https://github.com/DioPires/mtg-precon-upgrader/pull/75. Review head `e5e95b4`. It is the implementer's commit `6554428` plus its merge of `origin/main` at `2cdb0fa` (PR #68).
- **The brief and the hand-back.** The implementer's brief is the description of DEC-1172, below its state block. The hand-back is comment `d20f6f9c` on DEC-1172. It holds the census table, the request counts and the mutant table.
- **The rule.** The owner answered card `116a1d02` on DEC-1072 with option A at 09:00:09Z: "From the repository file. A deck page sends 0 requests to Scryfall." PR #54 shipped option B: a tile with no highlight price asked for a price older than 24 h.
- **The diff.** `git diff --stat origin/main...e5e95b4` lists 7 files under `web/` (117 insertions, 88 deletions). The source change is 2 places: `CardTile.tsx` drops the effect at `main`'s lines 95 to 97, its comment at 91 and 92, and the `useEffect` import; `cardCache.ts` changes only its header comment (lines 18 to 24 at the head). The rest is tests and `web/README.md`. The `web` subtree id at `e5e95b4` is `9838899e`.
- **Guard.** Run `git fetch origin && git diff --stat "$(git merge-base e5e95b4 origin/main)" origin/main -- web data .github`. At 09:40Z the merge base was `origin/main` (`2cdb0fa`), so it printed nothing. If it lists a file, name it in the verdict and say whether a deck page or /shopping reads it.
- **Other open pull requests on these paths.** PR #70 (DEC-1153, head `a75bcc2`) conflicts with this branch in `web/README.md` and merges `cardCache.ts` with no conflict; item 9 covers it. PR #64 (DEC-1162, head `af381c8`) changes `web/README.md` and `web/tests/support/test.ts`; the hand-back's merge-tree read is clean. PR #66, PR #72 and PR #74 change `Shopping.tsx` but not its `refreshPrice` call at line 282, and they share no file with this branch.

## Rulings before the review
1. **The design is DEC-1172 rulings 1 to 5, already accepted.** A tile shows the deck file's highlight price first, then the cache's price, then `card.price`, then `—`, and it never calls `refreshPrice`. The cache's price is the file's price, unless /shopping refreshed that card in the same browser in the last 24 h (ruling 3). /shopping keeps its refresh and its stop line. No `STORAGE_PREFIX` bump. A B item needs one of these: a request that a deck page sends for a name of the file; a tile that shows a price other than the rule's; a change to /shopping's behaviour; a document that states the old rule; or a gap under the mutant rule (item 8).
2. **The deleted kill file.** Its R22 case expected a refresh call for each card when a tile gets another card. Under the new rule that tile asks nothing. Case (a) rerenders a tile with another name of the file and expects 0 calls. Confirm that case (a) kills each mutant that would make a rerender ask (M3 and your own), or name the one that it misses.
3. **Equivalence.** Judge each mutant on the declared input types and on the cache's own states, not on today's `data/` files. The hand-back strikes M4 (`cardCache.enqueue(card.n)` in the effect) as equivalent for every name, because `useCard`'s effect runs first with the same name and leaves a state at which `enqueue` returns (`useCard.ts:15`; `cardCache.ts:411`, `:412` and `:414` at the head). Confirm or refute it.
4. **Not in scope:** the lookup of a name outside the file (the DEC-1131 path; item 5 only counts it), the picture refresh after a failed picture (`imageFailed`), /shopping's 24-hour rule, PR #70's own changes except for item 9, and PR #64's rate check.

## Items
1. **CI.** Read `web-ci` run 38879467021 on `e5e95b4` (created 09:17:43Z, after PR #68 merged at 09:09:43Z). I read success on both jobs. The hand-back quotes: lint `✖ 10 problems (0 errors, 10 warnings)`, `Test Files  50 passed (50)`, `Tests  617 passed (617)` and `217 passed (10.6m)`. Basis: `main`'s push run 38878552668 on `2cdb0fa` read 51 files, 618 tests and 217 e2e cases. The branch deletes 1 test file with 1 case, replaces 1 case of `CardTile.test.tsx` in place (7 cases before and after), and rewrites 1 e2e case in place. So expect 50, 617 and 217. Confirm the lines in both runs' logs. If the head's run is red, stop and hand back with the failing lines.
2. **The source change.** Read `CardTile.tsx` lines 75 to 115 at the head and confirm:
   - (a) The tile calls nothing on `cardCache` except `imageFailed` (line 109, the picture's error handler).
   - (b) The price order is `main`'s: compare the `highlightPrice` and `price` lines with `origin/main`'s file.
   - (c) `git grep -n -E 'refreshPrice|pricePending' e5e95b4 -- web/src ':!web/src/__tests__'` lists only `cardCache.ts` and `Shopping.tsx:282`. Quote the output.
   - (d) Nothing else that a deck route mounts asks for a price. List every `cardCache.` call and every `fetch(` in the components and hooks that `/deck/:id` renders, and say for each whether it can send a request for a name of the file. My reading: `useCard` calls `enqueue` only for a missing or failed entry, and `seed()` gives every name of the file a `loaded` entry.
   - (e) The `cardCache.ts` change is comments only. Show it with a token compare of the two files with comments removed, or with `git diff -U0` hunks in which every changed line starts with `//`.
3. **Unit case (a)** (`CardTile.test.tsx`, "shows the file's price older than 24 h and asks for no refresh, also when the tile gets another card").
   - Confirm its checks: 0 `fetch` calls, 0 `refreshPrice` calls, `pricePending` false for both names, and the file's price for both names.
   - Confirm its wait. It waits `LOOKUP_SPACING_MS + 300` = 1,500 ms of real time. Read `pump()` in `cardCache.ts` and `next()` and `waitFor()` in `scryfallLimiter.ts`. Show that a refresh queued at the mount or at the rerender starts its `fetch` within 1,500 ms after `_reset()` and an empty storage. If it can start later, give the case and the time.
   - Run the case on the head (it passes), then with `origin/main`'s `CardTile.tsx` in your tree (it fails). Quote the `Expected` and `Received` lines. Restore the file from `HEAD` after the run.
4. **E2e cases (d) and (e).** Case (d) is the one case of the describe block at `dec1131-card-batches.spec.ts:433` (`eternal-harvest`). Case (e) is the two cases of `dec1102-card-data.spec.ts` at lines 73 and 281 (`creeping-corruption` and the storage case).
   - Run both specs on the head with port 14882 and quote the count lines. The two `test.fail()` rate-check cases print ✘ and count as passed.
   - Run the three cases with `origin/main`'s `CardTile.tsx` in your tree. Each must fail at its check for no request; quote the lines. Restore the file from `HEAD`.
   - Confirm that case (d) checks every tile's price: a tile with a highlight price shows that price, and every other tile with a `usd` in the file shows `usdText(usd)`. Confirm that `scryfallUsdBump: 1` would make a refreshed price differ from the file's.
   - The reload half of case (d) waits 3 s and does not scroll, so only the first screen of tiles mounts. Say whether that matters under the new rule. Give it as an N item with the exact change if you think a scroll would add proof.
   - The hand-back finds 18 names on the page outside the file, all in the Apothecary's remedy articles (`article.gv1-apo-remedy`), which only a hover looks up. Confirm that none of them is a tile.
5. **Every deck page.** Write a scratch spec and a scratch Playwright config under `/tmp/dec<N>/`. For each deck id in `data/index.json`, set the page clock as `pricesAreOld()` does, open `/deck/<id>`, scroll to the end, wait 3 s, and count every request that the context sends to `api.scryfall.com`. Run it on the head with port 14882 and `--workers 3` at most. Give a table: deck, tiles, tiles outside the file, POSTs to `/cards/collection`, all requests to `api.scryfall.com`.
   - A request for a name of the file is a B item.
   - A request for a tile name outside the file is an N item for the hub, not a B item on PR #75: the card data script missed that name. Name the deck and the names.
6. **/shopping does not change.** Confirm that the branch changes no line of `Shopping.tsx` and no code line of `cardCache.ts`. Quote the count line of the describe block "/shopping refreshes the prices older than 24 h" from your item 4 run.
7. **Census and documents.**
   - Run the brief's census on the head: `git grep -n -i -E 'refreshPrice|tiles? (that show|refresh|ask)|tile foot|option B' e5e95b4 -- web/src web/tests web/README.md CLAUDE.md AGENTS.md`. Confirm that each hit is /shopping, the cache's `refreshPrice` API and its tests, or a text of the new rule.
   - Run a wider search of your own for text that still describes a tile or a deck page refresh (for example "deck guide" or "tile" within a line of "refresh" or "price"), in `web/src`, `web/tests`, `web/README.md`, `CLAUDE.md`, `AGENTS.md` and `docs/`. Quote the command and every hit. The implementer's wider search found one title that the census missed (`dec1131-card-batches.spec.ts:416` on `main`).
   - Read `web/README.md` lines 25 to 36 and 215 to 232 at the head, and the `cardCache.ts` header at lines 14 to 30. Confirm that each says that /shopping alone refreshes a price older than 24 h, that a deck page sends no request for a deck card at any date, and what ruling 3 says about a /shopping refresh on a tile. Quote any sentence that is wrong or unclear, with your fix as exact text.
8. **Mutants.** Read the implementer's runner first (`/Users/dpires/.paperclip/instances/default/workspaces/4e51e111-eff7-4619-95dd-9e43a955e637/dec1172/mutants.py`, with logs `M1-unit.log` to `M4-e2e.log` beside it). If you reuse it, copy it to `/tmp/dec<N>/` and change its output paths before you run it, so that your run does not overwrite the implementer's logs. Run each mutant on the unit files first, and on the e2e specs only when no unit file kills it. Run at least these:
   - the hand-back's M1, M2 and M3 again in your own run;
   - M4, with your reading under ruling 3;
   - the refresh in `useLayoutEffect` in place of `useEffect`;
   - the refresh in the render body, with no effect, for a tile with no highlight price;
   - the refresh in `useCard`'s effect for every name (`hooks/useCard.ts`), so that every user of the hook asks;
   - the price order with `priceLive` before the highlight price;
   - at least two more of your own.

   A survivor stands as a B item unless you show that it is equivalent under ruling 3. For each survivor that stands, write and run a kill case, save the log of each kill run, and give its path. The mutant rule wins over any limit that the hand-back names.
9. **Merged with PR #70.** Build a scratch tree that holds `main`, PR #75 and PR #70.
   - Commit the merge tree of `origin/main` and `e5e95b4`: `git commit-tree "$(git merge-tree --write-tree origin/main e5e95b4)" -p origin/main -p e5e95b4`.
   - Run `git worktree add --detach /tmp/dec<N>/merged70 <commit>`, then `git -C /tmp/dec<N>/merged70 merge --no-edit a75bcc2`. It stops on `web/README.md`.
   - Resolve the conflict yourself. Then compare your file with the implementer's resolution (`/Users/dpires/.paperclip/instances/default/workspaces/4e51e111-eff7-4619-95dd-9e43a955e637/dec1172/pr70-merge-README.resolved.md`) and quote the `diff`. Read the merged `cardCache.ts` header and confirm that it reads as one text.
   - Clone `node_modules` from your review tree when `cmp` shows the same `package-lock.json`; otherwise run `npm ci`. Run `npx vitest run`, then `dec1131-card-batches.spec.ts`, `dec1102-card-data.spec.ts` and `dec1153-card-data-followups.spec.ts` with port 14884. Quote the count lines.
   - A failure here is not a B item on PR #75 by itself. Say which pull request's lines fail, and give the resolution if you find one. If PR #70's head is no longer `a75bcc2` when you start, use its new head and say so.

## Rules
- **Environment.** Set `HOME="$PAPERCLIP_GITHUB_HOST_HOME"` for every `git` and `gh` command. Set `PLAYWRIGHT_BROWSERS_PATH="$PAPERCLIP_GITHUB_HOST_HOME/Library/Caches/ms-playwright"` for every Playwright run; without it every case fails at launch.
- **Tree.** `cd /Users/dpires/Documents/Personal/code/mtg-precon-upgrader && git fetch origin && git worktree add --detach wt-dec<N>-review e5e95b4`, then `npm ci` in its `web/`. Touch no other tree in the repository folder. Do not touch `wt-dec1172`: the merge needs it. Keep scratch files under `/tmp/dec<N>/`, outside the tree, and keep any scratch Playwright config there too. Push nothing to the PR branch.
- **Ports.** Use 14882 in the review tree and 14884 in the scratch tree of item 9, never the same value in two trees. At 09:40Z no issue named either value and no process listened on either.
- **No live request.** Send no request to `api.scryfall.com` or `cards.scryfall.io` from a script, a test, a browser or `curl`. The e2e stub answers every case.
- **Workers.** Run Playwright with 3 workers at most; the Mac is shared.
- **Shell.** Brace every shell variable that a colon follows (`"${B}:web/src/x"`). zsh reads `$B:w` as a modifier.
- **Kill files.** Put them under `/tmp/dec<N>/kill/`. Run `npm run typecheck` once with your kill files in the tree, because vitest does not typecheck. Name each file in the verdict.
- **At the verdict,** remove your trees. For `wt-dec<N>-review` and `/tmp/dec<N>/merged70`: `git -C <tree> status --porcelain` must print nothing (for `merged70`, commit the resolved merge first or run `git -C /tmp/dec<N>/merged70 merge --abort`), then `git worktree remove <tree>` (never `--force`) and `git worktree prune`. Name each removed tree in the verdict.

## Verdict
Give APPROVE or CHANGES. List B items (they block the merge) and N items (notes). For each B item, give the line, the failing input, the case or the mutant, the log path, and the fix as exact text where you can.

## Handoff
1. Post the verdict as one comment on this issue.
2. As the last action of your run, send one PATCH on this issue:
   - `assigneeAgentId`: the CEO (`f9427c33-d719-4fd5-a3c5-cd2f65dd01e8`);
   - `status`: `in_review`;
   - `executionPolicy.monitor`: `nextCheckAt` 30 minutes ahead, `scheduledBy: "assignee"`, and `notes` under 500 characters that name your verdict comment.
3. If the server answers 422 `invalid_issue_disposition`, send the same PATCH again with `nextCheckAt` about ten hours ahead. Never set `done`; only the CEO closes the issue.
4. **A question in the middle of the leg.** Do the parts that the question does not touch. Post the question with its evidence and your recommendation. Then send the PATCH above as the last action of your run. Do not open a child issue assigned to the CEO: the server refuses it (409 `delegation_cycle`).

planned-by: CEO. Parent: DEC-1172. Implementing hand-back: `d20f6f9c`.
