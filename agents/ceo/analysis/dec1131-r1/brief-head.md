**For the CEO run that a hand-back on this issue starts: the state block at the top of [DEC-1131](/DEC/issues/DEC-1131) holds the steps on APPROVE and on CHANGES. Read it first.**

Review PR #54 for DEC-1131 and post a verdict. Reviewer: you, the Design System Engineer (`8ea33a50`). Implementer: the Founding Engineer (`4e51e111`). Reviewer and implementer stay separate. The CEO merges after your verdict: do not merge, do not push to the branch, and do not fix what you find.

**Why you.** You reviewed pull request 2 (PR #38, DEC-1110). This pull request builds your notes N2 to N7, H7 and delta N1 to N4, and it moves your kill cases. Your kill mutants and `reading-3b.test.ts` are still in `/tmp/dec1110/`. Your fix round on DEC-1116 is live, and nothing else waits in your queue, so this review starts after it. The Frontend Engineer has five runs queued. The Interactive Tools Engineer reviews PR #56 (DEC-1145). The Simulation Engineer is idle, but it has never read the app's limiter.

**Order.** High priority. Budget: about 4 hours. Items 7, 8, 11 and 12 cost the most; do them last. If you skip a check, say so in the verdict and give the reason; do not drop it silently.

`<N>` is this issue's number.

## What the pull request does
Design D of DEC-1072, pull request 3 of 3 (ruling `15c825e9` on DEC-1072). The brief is the description of DEC-1131. The hand-back is comment `7ea5a029` on DEC-1131 (`GET /api/issues/abdbe7c0-9e4e-4d78-8f60-33d5203b1230/comments`). Verify it; do not take it on faith.
1. **The limiter** (`web/src/data/scryfallLimiter.ts`). Bucket 1 spacing is 1,200 ms. `fetch()` and `next()` can send a method, headers and a body. A request with no answer after 20 s is aborted and counts as a rejected `fetch`. The stop record holds `{until, ms, n}`: a request notes `n` when it starts, and it can double or end only that stop. A record that ended more than 300 s ago counts as none. A stop in memory is capped as a stored one is. Inside a tab the spacing runs on `performance.now()`.
2. **The batch** (`web/src/data/cardCache.ts`). At its turn, bucket 1 sends one `POST /cards/collection` with up to 75 identifiers: names asked `first`, then lookups, then refreshes. A `//` name goes out as its front face. The answer is matched by `normalizeName()` on the full name and on the front face. A `not_found` name holds 24 h in storage. A 400 or 422 fails the batch's lookups for 30 s in memory and holds its refreshes for 24 h.
3. **The refresh.** `refreshPrice()` asks for a file price older than 24 h. The overlay under `gv1-card:` holds only the changed fields. The file's price wins when the file is newer. The callers are each /shopping row and one `useEffect` in `CardTile.tsx` (option B; the owner's card `116a1d02` is still open).
4. **/shopping.** The summary holds while a buy row's refresh waits or is out. The footer shows the oldest date among the priced buy rows. `PricePausedLine` shows `<p role="status">` while a stop holds and a row waits.
5. **Autocomplete and the loader.** `scryfallSuggest()` sends nothing during a stop (N5). `loadCardMetadata()` keeps no failed or empty file (N6), and it fetches `card-metadata.meta.json` beside the file to date the prices.
6. **The harness** (`web/tests/support/`). The stub answers `POST /cards/collection`. New option `scryfallUsdBump`. The rate check stamps at `context.on('request')` (N2). Page mode counts a POST (H7).
7. **Tests.** `web/src/setupTests.ts` rejects any unit-case fetch to a Scryfall host. Vitest fakes `performance` too (`web/vite.config.ts`). New unit file `PricePausedLine.test.tsx` and new e2e spec `tests/dec1131-card-batches.spec.ts` (13 cases).

## What to review
- **PR:** https://github.com/DioPires/mtg-precon-upgrader/pull/54, branch `dec-1131-card-data-batch`, head `73f6fd5e28e3f6f8e5126db7d0b3ca50a37c165b`.
- **Files (31, +2684 −498).** Confirm with `git diff --stat origin/main...origin/dec-1131-card-data-batch`. Nothing under `data/`, `scripts/` or `.github/` changed.
- **Commits.** Four work commits (`42147fd`, `92b573f`, `556ba50`, `b53621f`) and six merges of `main`. Three merges hold a hand edit, and `git show --remerge-diff --format=%h <merge>` shows each: `2d1b858` (`loaderEnvelope.test.ts`, the `v158` pin), `0f786fc` (`web/README.md`, my ruling `4ed5d079`) and `73f6fd5` (`Shopping.tsx`, my note `8c5f79d1`). The other three print only their id.
- **Blob ids at the head** (`git rev-parse HEAD:<path>`):

| Path | Status | Blob at the head |
|---|---|---|
