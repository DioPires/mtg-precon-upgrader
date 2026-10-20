**QUEUE ENTRY 6 on [DEC-1178](/DEC/issues/DEC-1178), not ready (CEO run `9a2c6c7e`, 2026-10-16 14:15Z). Read this first. Fix round 2 (the README leg) is out with the Founding Engineer.**

- PR #70 merged at 14:02:27Z as `9cd5a2b`. `git rev-parse origin/main:web/README.md` prints `0e372b5fb74e623e651701a7c9821eea3164ddf0`. `git merge-tree --write-tree --name-only origin/main aa3abe7` stops on `web/README.md` only.
- I rehearsed the round with git plumbing only (`agents/ceo/analysis/dec1172-r2/rehearse.py`, log `rehearse.log`). The merge, the README copy and `apply.py` give tree `f4530926` and README blob `54dda046`. `core.py` on that commit prints `ALL EQUAL` (`core-R.log`).
- No other open pull request (#76, #66, #72, #71, #73) changes `web/README.md`, `cardCache.ts`, `dec1102-card-data.spec.ts`, `dec1131-card-batches.spec.ts`, `CardTile.*` or `Decklist.tsx`. So the README copy holds whichever queue turns merge before the leg's merge of `main`.
- **At the leg's hand-back:** do "CEO: checks at the hand-back (round 2)" at the end of fix round 2. Those steps write READY on this block's first line, take the merge turn and close out.
- PR #75's head is `aa3abe7`, my update-branch merge of `f16e25a` (13:43Z). `web-ci` run 38910090696 on it is green (51 files, 620 tests, 226 e2e), but that reading cannot merge it: its guard now lists PR #70's files.
- A baton that arrives while this block reads "not ready" skips this entry (hub Q6).

---

## Fix round 2: merge `main` with PR #70 and take the reviewer's README

**Implementer: the Founding Engineer (`4e51e111`). Tree: `wt-dec1172` (branch `dec-1172-tile-file-price`; your local branch is at `c16614c`, the remote at `aa3abe7`). Port: `GRIMOIRE_E2E_PORT=14786`. Budget: about 25 minutes. Kit: `/Users/dpires/Documents/Personal/code/mtg-precon-upgrader/agents/ceo/analysis/dec1174-r1/` (`<kit>` below), the kit of round 1.**

### Outcome
PR #75's head merges `main` with PR #70. `web/README.md` is the reviewer's resolution (`<kit>/pr70/README.resolved.md`) with round 1's two README edits made again by `apply.py`. No file changes by hand. CI's `web-ci` is green on the new head, and `core.py` prints `ALL EQUAL`. PR #75 then takes a merge turn on DEC-1178 with no new review.

### Why
- PR #70 merged at 14:02:27Z (`9cd5a2b`). It rewrites the lookup bullet of `web/README.md` beside this branch's refresh bullet, so GitHub's update-branch stops on that file.
- The reviewer of PR #75 resolved that conflict (item 9 of verdict `bab1dab3` on DEC-1174). The kit's control D (`main` `e886907` plus PR #70) and my rehearsal on `9cd5a2b` both end in `ALL EQUAL`.
- `aa3abe7` is my update-branch merge of `f16e25a` (13:43Z). It is only on the remote, so your tree starts with a fast-forward.

### Rules
- Set `HOME="$PAPERCLIP_GITHUB_HOST_HOME"` for every `git` and `gh` command.
- Set `PLAYWRIGHT_BROWSERS_PATH="$PAPERCLIP_GITHUB_HOST_HOME/Library/Caches/ms-playwright"` and `GRIMOIRE_E2E_PORT=14786` for any Playwright run. This round needs none.
- Brace every shell variable that a colon follows (`"${B}:web/x"`). zsh reads `$B:w` as a modifier.
- Send no request to `api.scryfall.com` or `cards.scryfall.io`.
- Keep logs in `$PAPERCLIP_GITHUB_HOST_HOME/.paperclip/instances/default/workspaces/4e51e111-eff7-4619-95dd-9e43a955e637/dec1172-r2/`. Touch no other agent's tree or server.

### Steps
1. In `wt-dec1172`, check that `git status --porcelain` prints nothing. Run `git fetch origin`, then `git merge --ff-only origin/dec-1172-tile-file-price`. `git rev-parse HEAD` must print `aa3abe783e16456bc3070fa87f2fa03435d38b06`, unless a later comment on this issue names another head.
2. Run `git rev-parse origin/main:web/README.md`. It must print `0e372b5fb74e623e651701a7c9821eea3164ddf0`. If it prints another blob, stop and ask (Hand-back step 4).
3. Run `git merge --no-edit origin/main`. Expect it to stop with `CONFLICT (content): Merge conflict in web/README.md` and on no other path. `web/src/data/cardCache.ts` merges with no conflict.
   - If it stops on another path too, keep the text of both sides there. Name each path and the lines that you resolved in the hand-back. `core.py` names such a path for my hand read.
4. Run `cp <kit>/pr70/README.resolved.md web/README.md`, then `git add web/README.md` and `git commit --no-edit`.
5. From the tree's root, run `python3 -I <kit>/apply.py "$PWD"`. Expect these 7 lines. A `STOP` line means that the old text moved: stop there and ask (Hand-back step 4).
```
B1: web/src/__tests__/components/DecklistNoRefresh.test.tsx copied
N2: already
N1: already
N4-spec: already
N3+N4-cache: already
N4-readme-clock: done
N4-readme-bullet: done
```
6. Check the result:
   - `git status --porcelain` prints ` M web/README.md` only. The kill file is already the kit's file, so its copy changes nothing.
   - `git hash-object web/README.md` prints `54dda0461f9d1e80464d452e911360fc31ac55bd`.
   - `git diff --stat` reads `9 insertions(+), 9 deletions(-)` for `web/README.md`. Read the diff: each hunk is one of round 1's two N4 README edits.
7. In `web/`, run `npm run lint`, `npm run typecheck` and `npx vitest run`. The merge changes no package file, so `npm ci` is not needed. Expect `✖ 10 problems (0 errors, 10 warnings)`, exit 0, and the counts of the `main` that you merged. On `9cd5a2b` that is `Test Files  53 passed (53)` and `Tests  652 passed (652)` (PR #70's run 38910068467). Each queue entry that merged after `9cd5a2b` adds its Δ from the table at the top of DEC-1178.
8. Commit `web/README.md` with the message `docs(web): DEC-1172 fix round 2: the README after PR #70 (DEC-1174 item 9)`. Push the branch.
9. Find the `web-ci` run on the new head and wait for it in the foreground: `gh run watch <id> --repo DioPires/mtg-precon-upgrader --interval 20`. Quote its id and the lines for lint, `Test Files`, `Tests` and the e2e count. On `9cd5a2b` expect 53, 652 and `228 passed`, plus each Δ as in step 7. If a case fails or is flaky, quote it and hand back; do not rerun.
10. Run `git fetch origin`, then `python3 -I <kit>/core.py /Users/dpires/Documents/Personal/code/mtg-precon-upgrader <new head>`. Quote the whole output. On `9cd5a2b` I read the lines below; a later `main` changes only the base and the count of other paths.
```
web/src/__tests__/components/DecklistNoRefresh.test.tsx bb559ae9d7dc84fa bb559ae9d7dc84fa EQUAL
web/README.md conflict of PR #70 (base README 0e372b5f): expected = pr70/README.resolved.md + edits 54dda046
web/README.md 54dda046 EQUAL (byte for byte)
web/src/data/cardCache.ts b294d59f EQUAL (byte for byte)
web/tests/dec1102-card-data.spec.ts 2a5fcbd0 EQUAL (byte for byte)
base 9cd5a2b, SIM 38ea342: 2213 other paths keep their blobs
ALL EQUAL
```
11. Check that `git status --porcelain` prints nothing. Keep the tree until the merge.

### Hand-back
1. Post one comment on this issue. Put the outcome first. Then give the new head, the merge lines of step 3, the output of `apply.py`, the readings of steps 6 and 7 with the path of each log, the CI run of step 9 and the output of `core.py`.
2. As the last action of your run, send one PATCH on this issue:
   - `assigneeAgentId`: the CEO (`f9427c33-d719-4fd5-a3c5-cd2f65dd01e8`);
   - `status`: `in_review`;
   - `executionPolicy.monitor`: `nextCheckAt` 30 minutes ahead, `scheduledBy: "assignee"`, and `notes` under 500 characters that name your comment.
3. If the server answers 422 `invalid_issue_disposition`, send the same PATCH again with `nextCheckAt` about ten hours ahead. Never set `done`; only the CEO closes the issue.
4. A question in the middle of the leg: do the steps that the question does not touch, commit and push them, and post the question with its evidence and your recommendation. Then send the PATCH above as the last action of your run. Do not open a child issue assigned to the CEO: the server refuses it (409 `delegation_cycle`).

### CEO: checks at the hand-back (round 2)
For the CEO run that the hand-back starts.
1. Read the hand-back. Run `git fetch origin`. Check that PR #75's head is the head that the hand-back names and that `git merge-base --is-ancestor aa3abe7 <head>` exits 0.
2. Run `python3 -I <kit>/core.py <repo> <head>`: expect `ALL EQUAL`. Read by hand each path that it names.
3. Read the `web-ci` run on the head: green, lint `0 errors, 10 warnings`, and the counts of the DEC-1178 table for #75 (51, 620, 226) plus the Δ of each entry in the head's `main` (with #70 alone: 53, 652, 228).
4. Write READY on the first line of the QUEUE block. Then take the turn as a late entry: if no other queue issue (DEC-1170, DEC-1177, DEC-1155, DEC-1167, DEC-1161, DEC-1171) has a live CEO run, do the hub's Q1 to Q7 at once. Otherwise park this issue `in_review` with a monitor 15 minutes ahead and end; the baton of the turn in flight finds it.
5. After the merge, do steps 7 and 8 of "CEO: checks at the hand-back" of fix round 1 below: the sweep of `wt-dec1172`, then the close of DEC-1174 and of this issue, and the R1 bullet on DEC-1072. PR #70 has merged, so step 8's README note is void.
6. Start [DEC-1188](/DEC/issues/DEC-1188) (note `93bb05ac` on this issue). Refresh its basis first: the head of `main`, the README line numbers of its item (c), and the port (14931). Then PATCH it `todo` and post a short start comment.

---

**STATE (CEO run `7b317106`, 2026-10-16 10:25Z). Read this section first.**

- **Fix round 1 is done, and I checked it.** Hand-back `48273c48` (10:18Z): PR #75's head is `c16614c`, the round's commit on a merge of `14303fa`.
  - `core.py` prints `ALL EQUAL` (base `14303fa`).
  - M10 fails the kill file at `DecklistNoRefresh.test.tsx:58`. N1's control on `main`'s tile reads `3 failed` (2 at `:298`, 1 at `:295`).
  - Local readings on the head: lint `0 errors, 10 warnings`, typecheck exit 0, `51 passed (51)` files, `618 passed (618)` tests, and the whole e2e suite `226 passed (3.4m)` with no failed or flaky case. The logs are in the Founding Engineer's workspace, folder `dec1172-r1/`.
- **The merge waits for the billing block ([DEC-1178](/DEC/issues/DEC-1178)).** GitHub refused CI run 38885802995 on `c16614c`. Hub rule 1 needs a green CI `e2e` reading of the head, and rule 7 gave the one merge of the block to PR #74.
- **PR #74 merged at 10:20Z as `b8ed7fa`, so PR #75 needs update-branch.** The guard `git diff --stat 14303fa origin/main -- web data .github vercel.json` lists `Shopping.tsx`, `Shopping.test.tsx` and one screenshot. /shopping reads them. Hub rule 2 forbids update-branch while the block lasts.
- **Fallback:** this issue is `in_review` with a monitor at 16:30Z. The hub's monitor fires at 16:00Z. [DEC-1174](/DEC/issues/DEC-1174) stays open until the merge (monitor 16:45Z).

**At the block's end (the repository is public; hub rule 6):**
1. Run `git fetch origin`. Check that PR #75's head is still `c16614cd9dc638626340921ab2df6702cda305e0`.
2. If PR #70 has not merged, run `gh api -X PUT repos/DioPires/mtg-precon-upgrader/pulls/75/update-branch -f expected_head_sha=c16614cd9dc638626340921ab2df6702cda305e0`. Compare the new head's tree with `git merge-tree --write-tree origin/main c16614c`.
3. If PR #70 merged first, the update stops on `web/README.md`. Send a short leg to the Founding Engineer in `wt-dec1172`: run `git merge origin/main`; if `git rev-parse origin/main:web/README.md` prints `0e372b5fb74e623e651701a7c9821eea3164ddf0`, copy `<kit>/pr70/README.resolved.md` over `web/README.md`; run `python3 -I <kit>/apply.py "$PWD"` (the README edits apply again, every other edit prints `already`); commit and push. `core.py` reads that README by its rule 3.
4. If PR #75 merges first, PR #70's README after its merge of `main` is `<kit>/pr70/README.after-pr75-round1.md` (blob `54dda046`). Tell the DEC-1153 leg.
5. Wait for `web-ci` on the new head. Expect lint `0 errors, 10 warnings`, `51 passed (51)` files, `620 passed (620)` tests and `226 passed` e2e. PR #74's run 38882262578 read 51, 620 and 226, and this pull request keeps each count.
6. Run `python3 -I <kit>/core.py /Users/dpires/Documents/Personal/code/mtg-precon-upgrader <new head>` after `git fetch origin`. Expect `ALL EQUAL`.
7. Do steps 6 to 8 of "CEO: checks at the hand-back" below: merge pinned to the new head, deploy record, sweep of `wt-dec1172`, close-out. Steps 1 to 4 there are done (this block).
---

## Fix round 1 (route A): one kill file and four text notes

**Implementer: the Founding Engineer (`4e51e111`). Tree: `wt-dec1172` (branch `dec-1172-tile-file-price`, at `e5e95b4`). Port: `GRIMOIRE_E2E_PORT=14786`. Budget: about 45 minutes. Kit: `/Users/dpires/Documents/Personal/code/mtg-precon-upgrader/agents/ceo/analysis/dec1174-r1/` (`<kit>` below). Read its `README.txt` first.**

CEO run that this round's hand-back starts: go to "CEO: checks at the hand-back" at the end of this round.

### Outcome
PR #75 gets one new unit file (the reviewer's kill case for B1) and the reviewer's N1 to N4 edits. No source line changes. The head merges `origin/main`, CI is green, and `core.py` prints `ALL EQUAL`. I then merge with no new review.

### Why
- The review found one mutant that no case kills. M10 adds `cardCache.refreshPrice(n);` after `cardCache.enqueue(n);` at `web/src/components/organisms/Decklist.tsx:147`. With M10, a deck page sends a refresh POST for a deck card with no mana cost or no `cmc`. Today's file holds no such card, so every suite passes. The declared types allow such a card (`types.ts:311-314`).
- The reviewer wrote the kill case and ran it. It passes on the head and fails on M10 at line 58. I ran it on the merge with `main`, and on the merge with `main` and PR #70.
- N1 makes the storage case of `dec1102-card-data.spec.ts` fail on `main`'s tile in every run (6 of 6 in the reviewer's runs, not 4 of 7). N2 puts the deck page hover case on old prices, as the spec header says. N3 says who refreshes a tile's price. N4 writes "sends no price request", because a failed picture still sends one request.
- Route A: the reviewer wrote and ran the text, you read it and take it, and I compare the files. Reviewer and implementer stay separate, and the round needs no delta re-read.

### Rules
- Set `HOME="$PAPERCLIP_GITHUB_HOST_HOME"` for every `git` and `gh` command.
- Set `PLAYWRIGHT_BROWSERS_PATH="$PAPERCLIP_GITHUB_HOST_HOME/Library/Caches/ms-playwright"` and `GRIMOIRE_E2E_PORT=14786` for every Playwright run. Run Playwright with 3 workers at most.
- Brace every shell variable that a colon follows (`"${B}:web/x"`). zsh reads `$B:w` as a modifier.
- Send no request to `api.scryfall.com` or `cards.scryfall.io`. The e2e stub answers every case.
- Keep scratch files and logs in `$PAPERCLIP_GITHUB_HOST_HOME/.paperclip/instances/default/workspaces/4e51e111-eff7-4619-95dd-9e43a955e637/dec1172-r1/`. Touch no other agent's tree or server.

### Steps
1. In `wt-dec1172`, run `git fetch origin`, then `git merge --no-edit origin/main`.
   - If the merge is clean, go to step 2.
   - If it stops on `web/README.md` only (PR #70 merged first), run `git rev-parse origin/main:web/README.md`. If it prints `0e372b5fb74e623e651701a7c9821eea3164ddf0`, copy `<kit>/pr70/README.resolved.md` over `web/README.md`, then run `git add web/README.md` and `git commit --no-edit`. That file keeps PR #70's lookup bullet (with the sentence about a blank front face) and this branch's refresh bullet.
   - If it stops on another path, or the README blob is another one, keep the text of both sides. Name each path and the lines that you resolved in the hand-back. `core.py` names such a path for my hand read.
2. From the tree's root, run `python3 -I <kit>/apply.py "$PWD"`. It prints 7 lines: `B1: ... copied`, then `done` for N2, N1, N4-spec, N3+N4-cache, N4-readme-clock and N4-readme-bullet. A `STOP` line means that the old text moved: stop there and ask (Hand-back step 4).
3. Read `git diff` and `git status`. Check each edit against the verdict `bab1dab3` on DEC-1174 (B1, N1, N2, N3 and N4). Do not edit the spec, `cardCache.ts` or the README by hand: `core.py` compares them byte for byte. You may reword or drop comment lines of the kill file only. If you think a text is wrong, ask before you commit, and give the reason.
4. In `web/`, run `npm run lint`, `npm run typecheck` and `npx vitest run`. Expect `✖ 10 problems (0 errors, 10 warnings)`, exit 0, and the unit counts of `main`'s last push run: the branch deletes 1 file with 1 case and adds 1 file with 1 case. On `main` `e886907` that is `Test Files  51 passed (51)` and `Tests  618 passed (618)`. With PR #70 merged I read `53 passed (53)` and `650 passed (650)`.
5. Run the kill file on M10:
   - In `web/src/components/organisms/Decklist.tsx`, add the line `      cardCache.refreshPrice(n);` after the line `      cardCache.enqueue(n);` (one place).
   - Run `npx vitest run src/__tests__/components/DecklistNoRefresh.test.tsx`. Expect `1 failed` at `DecklistNoRefresh.test.tsx:58` with `expected "spy" to not be called at all, but actually been called 1 times`.
   - Run `git checkout -- src/components/organisms/Decklist.tsx`. Check that `git status --porcelain` lists only the round's four files.
6. Run `npx playwright test tests/dec1102-card-data.spec.ts tests/dec1131-card-batches.spec.ts --workers 3`. Quote the count line. The `test.fail()` cases print ✘ and count as passed.
7. Run N1's control:
   - Write `main`'s old tile over the file: `git show 2cdb0fa:web/src/components/molecules/CardTile.tsx > src/components/molecules/CardTile.tsx`.
   - Run `npx playwright test tests/dec1102-card-data.spec.ts -g "storage holds each card once" --repeat-each 3 --workers 3`. Expect `3 failed`, each at `:295` (the poll) or at `:298` (N1's new check). The reviewer's 6 runs failed 4 times at `:298` and 2 times at `:295`. Quote the lines.
   - Run `git checkout -- src/components/molecules/CardTile.tsx`.
8. Commit the four files: `web/src/__tests__/components/DecklistNoRefresh.test.tsx`, `web/tests/dec1102-card-data.spec.ts`, `web/src/data/cardCache.ts` and `web/README.md`. Message: `test(web): DEC-1172 fix round 1: the deck list asks for no price (DEC-1174 B1, N1-N4)`. Push the branch.
9. Read the `web-ci` run on the new head.
   - If its jobs run, wait for it. Quote its id and the lines for lint, `Test Files`, `Tests` and the e2e count. Expect the e2e count of `main`'s last push run (226 on `e886907`).
   - If GitHub refuses its jobs (the annotation says "The job was not started because recent account payments have failed"; see DEC-1178), do not wait and do not rerun it. Run the whole e2e suite in `web/` instead: `npx playwright test --workers 3`. Quote the count line and the path of its log. Expect 226 passed on `e886907`; the `test.fail()` cases print ✘ and count as passed. Give the refused run's id in the hand-back.
10. Run `git fetch origin`, then `python3 -I <kit>/core.py /Users/dpires/Documents/Personal/code/mtg-precon-upgrader <new head>`. Expect `ALL EQUAL`. Quote the whole output.

### Not in this round
- N5 (unit tiles with `price: '—'`) is declined. E2e case (d) kills M11 and M12 at `dec1131-card-batches.spec.ts:467`, and nobody ran the change.
- N6, N7 and N8 need no change. Step 1's merge and step 9's CI run answer N7.

### Hand-back
1. Post one comment on this issue. Put the outcome first. Then give the new head, the merge of step 1 (clean, or the README resolution), the output of `apply.py`, the lines of steps 4 to 7 with the path of each log, the CI run of step 9 and the output of `core.py`.
2. As the last action of your run, send one PATCH on this issue:
   - `assigneeAgentId`: the CEO (`f9427c33-d719-4fd5-a3c5-cd2f65dd01e8`);
   - `status`: `in_review`;
   - `executionPolicy.monitor`: `nextCheckAt` 30 minutes ahead, `scheduledBy: "assignee"`, and `notes` under 500 characters that name your comment.
3. If the server answers 422 `invalid_issue_disposition`, send the same PATCH again with `nextCheckAt` about ten hours ahead. Never set `done`; only the CEO closes the issue.
4. A question in the middle of the leg: do the steps that the question does not touch, commit and push them, and post the question with its evidence and your recommendation. Then send the PATCH above as the last action of your run. Do not open a child issue assigned to the CEO: the server refuses it (409 `delegation_cycle`).

### CEO: checks at the hand-back
For the CEO run that the hand-back starts.
1. Read the hand-back. Run `git fetch origin`. Check that PR #75's head is the head that the hand-back names, and that `mergeStateStatus` is `CLEAN`.
2. Run `python3 -I <kit>/core.py <repo> <head>`: expect `ALL EQUAL`. Read by hand each path that it names.
3. Read the CI run on the head: lint `0 errors, 10 warnings`, and the unit and e2e counts of `main`'s last push run (51, 618 and 226 on `e886907`). If GitHub refused it (DEC-1178), read the local e2e log of step 9, park this issue on the hub DEC-1178 (rule 5), and merge only after the block ends and CI reads green `e2e` on the head (rule 1).
4. Read the logs of step 5 (M10 fails at `:58`) and step 7 (`3 failed`).
5. Run the guard: `git diff --stat "$(git merge-base <head> origin/main)" origin/main -- web data .github`. If it lists a file that a deck page, /shopping or a test reads, run `gh pr update-branch 75`, compare the new head's tree with `git merge-tree --write-tree origin/main <head>`, run `core.py` again and wait for CI.
6. Merge with `gh pr merge 75 --merge --match-head-commit <head>`. Compare `git rev-parse origin/main^{tree}` with the merge-tree id. Wait for the push run on `main`. While the DEC-1178 block lasts, fast-forward `deploy` by hand (DEC-1178 rule 3).
7. Sweep `wt-dec1172`: `git status --porcelain` prints nothing and `git merge-base --is-ancestor HEAD origin/main` exits 0; then `git worktree remove` (never `--force`), `git branch -D dec-1172-tile-file-price` and `git worktree prune`. Delete the remote branch by API if it still exists (`delete_branch_on_merge` is off in this repository).
8. Close DEC-1174, then this issue, with `planned-by: CEO / executed-by: Founding Engineer` (review: Design System Engineer). Update the R1 bullet on the hub DEC-1072. If PR #70 is still open, tell its leg about the README (see STATE).

---

## The first brief (done: hand-back `d20f6f9c`, PR #75 at `e5e95b4`)

**Tier 1, medium. Implementer: Founding Engineer (`4e51e111`). Parent: DEC-1072 (hub). `<N>` in this brief is this issue's number.**

## Outcome
A deck tile takes its price from the card cache and never asks Scryfall for a fresh one. A deck page then sends 0 requests to `api.scryfall.com` for a deck card, at any date. /shopping keeps its 24-hour refresh and its stop line.

## Why
- The owner answered card `116a1d02` on DEC-1072 at 09:00:09Z on 2026-10-16 with option A: "From the repository file. A deck page sends 0 requests to Scryfall." The option's text says: "The price is as old as the last run of the card data script."
- PR #54 (DEC-1131, `43cf161`) shipped option B, the default on silence. On `main` (`4daf6b8`) the tile asks for a price older than 24 h at `web/src/components/molecules/CardTile.tsx:95-97`:

```
  useEffect(() => {
    if (!highlightPrice) cardCache.refreshPrice(card.n);
  }, [card.n, highlightPrice]);
```

- `prices_as_of` in `data/card-metadata.meta.json` is older than 24 h on most days. So today each deck guide sends refresh batches for its tiles that have no highlight price.

## Rulings
1. Remove the effect at `CardTile.tsx:95-97` and the comment at `:91-92`. Keep the price order at `:93-94`: the deck file's highlight price first, then the cache's price, then `card.price`, then `—`. Remove the `useEffect` import when nothing else uses it.
2. `cardCache.refreshPrice()` and `cardCache.pricePending()` stay. /shopping calls `refreshPrice` (`Shopping.tsx:282`), and its 24-hour rule and its stop line do not change.
3. The tile shows the cache's price. That is the file's price, unless /shopping refreshed that card in the same browser in the last 24 h; then the tile shows the refreshed price. I keep that: it sends no request, and one card shows one price on both pages. Do not add a file-only price field.
4. No `STORAGE_PREFIX` bump: the stored shape does not change. Overlays that a tile stored before the deploy end within 24 h. If you find a reason to bump, say why in the hand-back.
5. Tests:
   - (a) `web/src/__tests__/components/CardTile.test.tsx:98-109` is the option B case. Replace it with a case that seeds the file with prices older than 24 h (`old()`), mounts a tile with no highlight price, and then rerenders the tile with another name of the file. For each name the tile shows the file's price. The case sees 0 `fetch` calls and 0 `refreshPrice` calls, and `pricePending` reads false. Wait long enough for a batch to go out if one were queued: read the cache's pump to choose the wait, or use a fake clock, and give the wait in the hand-back. The case must fail on `main`'s `CardTile.tsx`.
   - (b) Keep the case at `:111-117` (a highlight price asks nothing).
   - (c) Delete `web/src/__tests__/components/dec1149/dec1149-tile-kill.test.tsx`. Its R22 case expects one refresh call for each card. Case (a) covers the rerender under the new rule.
   - (d) Rewrite `web/tests/dec1131-card-batches.spec.ts:416-445` for the new rule, on `eternal-harvest` with `pricesAreOld()`. Scroll to the end so that every tile mounts. Expect 0 POSTs to `/cards/collection` from the page. If a name on the page is outside the file, list those names, assert that only they go out, and say so in the hand-back. Expect each tile with a highlight price to show that price, and each other tile with a `usd` in the file to show the file's price. Keep the reload half of the case.
   - (e) In `web/tests/dec1102-card-data.spec.ts`, set the page clock of the scroll case (`:74`, `creeping-corruption`) to old prices, as `pricesAreOld()` does, so that the case proves 0 requests under the new rule. Do the same at `:281`, and update the comment at `:280`. Update the header comment at `:5-7`: only /shopping refreshes.
6. Documents: change `web/README.md:29-33`, `web/README.md:219-223` and the header comment at `web/src/data/cardCache.ts:18-19`. Each says that /shopping alone refreshes a price older than 24 h, and that a deck page sends no request for a deck card at any date. Run this census and fix every other hit that describes the tile refresh. The `cardCache` tests of `refreshPrice` stay, because /shopping uses that function.

```
git grep -n -i -E 'refreshPrice|tiles? (that show|refresh|ask)|tile foot|option B' origin/main -- web/src web/tests web/README.md CLAUDE.md AGENTS.md
```

## Mutants
Run each mutant on the unit files first. Run it on the e2e specs only when no unit file kills it. Save a log of each run. Restore the file after each mutant; at the end `git status --porcelain` prints nothing.
- M1: `main`'s effect back in its place.
- M2: the effect with no highlight guard (`cardCache.refreshPrice(card.n)` for every tile).
- M3: the effect on a name change only (a ref skips the first mount).
- M4: `cardCache.enqueue(card.n)` in the effect in place of the refresh. I expect it to be equivalent for a name of the file, because `enqueue` sends nothing for such a name. If it is, show that and strike it.

## Setup
- Make a new tree from `origin/main` in the repository root: `git worktree add -b dec-<N>-tile-file-price wt-dec<N> origin/main`. Then run `npm ci` in its `web/`.
- Set `HOME="$PAPERCLIP_GITHUB_HOST_HOME"` for every `git` and `gh` command.
- Set `PLAYWRIGHT_BROWSERS_PATH="$PAPERCLIP_GITHUB_HOST_HOME/Library/Caches/ms-playwright"` for every Playwright run.
- Set `GRIMOIRE_E2E_PORT=14786` for every e2e run in this tree. No issue uses that value, and no process listened on it at 09:05Z.
- Keep scratch files (the mutant runner and the logs) outside the tree, in `$PAPERCLIP_GITHUB_HOST_HOME/.paperclip/instances/default/workspaces/4e51e111-eff7-4619-95dd-9e43a955e637/dec<N>/`.
- Do not `curl` `api.scryfall.com`. The e2e stub answers every Scryfall request.
- Do not touch another agent's tree or server.
- Brace every shell variable that a colon follows (`"${B}:web/src/x"`). zsh reads `$B:w` as a modifier.

## Overlaps
- PR #70 (your DEC-1153, head `a75bcc2`) changes `web/README.md` in the paragraph above line 219, and the header of `cardCache.ts` at lines 27-32. PR #64 (DEC-1162, head `d2cbead`) also changes `web/README.md`. Either can merge before you hand back.
- Before the hand-back PATCH, run `git fetch`, merge `origin/main` into your branch, run the unit suite again, and push.
- For each of PR #70 and PR #64 that is still open at that time, run `git merge-tree --write-tree --name-only <your head> <its head>` and quote the output. Give the resolution of each conflicted path in the hand-back.

## Hand-back
Post one comment on this issue. Put the outcome first. Then give:
1. The pull request number, the head, and `git diff --stat origin/main...<head>`.
2. The census output, and what you changed for each hit.
3. Unit case (a) and its wait, with its run on `main`'s `CardTile.tsx` (fails) and on the head (passes).
4. E2e cases (d) and (e): the count of POSTs to `/cards/collection` and of all requests to `api.scryfall.com`, on the head and on `main`, for `eternal-harvest` and `creeping-corruption` with old prices.
5. The mutant table, with the path of each log.
6. `npm run lint`, `npm run typecheck`, the vitest count line, and the id and totals of CI's `web-ci` run on the head.
7. The merge-tree outputs of the Overlaps section.
8. `git status --porcelain` of your tree (it prints nothing). Keep the tree for the review.

## Handoff
When the comment is posted, send one PATCH on this issue as the last action of your run:
- `assigneeAgentId`: the CEO (`f9427c33-d719-4fd5-a3c5-cd2f65dd01e8`).
- `status`: `in_review`.
- `executionPolicy.monitor`: `nextCheckAt` 30 minutes ahead, `scheduledBy: "assignee"`, and `notes` under 500 characters that name the hand-back comment.

The assignment wakes the CEO, who routes the review to another engineer. The monitor wakes the CEO when the server skips that wake: it skipped two hand-backs this morning (DEC-1162 at 08:55Z, DEC-1153 at 09:03Z). If the server answers 422 `invalid_issue_disposition`, send the same PATCH again with `nextCheckAt` about ten hours ahead. Never set `done`; only the CEO closes the issue.

The hand-back PATCH ends your run at once. For a question in the middle of the leg, finish the parts that the question does not touch, commit and push, post the question (the question, the evidence, the readings and your recommendation), and hand back with the same PATCH. Do not open a child issue assigned to the CEO: the server refuses it (409 `delegation_cycle`).

planned-by: CEO. Source: the owner's answer on card `116a1d02` (DEC-1072, ruling R1).
