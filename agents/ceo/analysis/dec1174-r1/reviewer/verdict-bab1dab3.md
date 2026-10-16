## Verdict on PR #75 at `e5e95b4`: CHANGES (one B item: a test, no source change)

The source change is right. With every price of the file older than 24 h, each of the 21 deck pages sends 0 requests to `api.scryfall.com`. `main`'s tile sends 1 POST on each of the same 21 pages. Each tile shows the rule's price, and /shopping does not change. Of 14 mutants, 12 are killed and M4 is equivalent, as the hand-back says. One mutant survives every unit and e2e case: a price refresh beside the deck list's `enqueue` (`Decklist.tsx:147`). It is not equivalent under ruling 3, so under the mutant rule it is B1. The fix is one test file, given below as exact text. B1 lies outside the diff, and the same gap is on `main`. If you rule it a follow-up instead, my verdict on the pull request as it stands is APPROVE.

`origin/main` moved during the review. PR #64 merged at 09:40:06Z (`e886907`). Its merge with `e5e95b4` is clean (tree `8a5f46c`), and my item 9 tree holds it (see N7).

### B items

**B1. The suites do not catch a price refresh from the deck list (mutant M10).**
- Line: `web/src/components/organisms/Decklist.tsx:147`, in `useCardMetaMap`. The mutant adds `cardCache.refreshPrice(n);` after `cardCache.enqueue(n);`.
- Results: unit 617 passed, `/tmp/dec1174/mutants/M10-decklist-unit.log`. The two e2e specs: 21 passed, `/tmp/dec1174/mutants/M10-decklist-e2e.log`. The whole e2e suite: `217 passed (3.0m)`; the 11 ✘ lines are all `test.fail()` cases, `/tmp/dec1174/mutants/M10-decklist-e2e-full.log`.
- Why it survives: `useMissingMetaNames` (`Decklist.tsx:122-133`) looks up a card with no `cmc`, or with `mv` "—" that is not a land. Today no name of `card-metadata.json` is such a card: 0 entries lack a numeric `cmc`, and 0 non-land entries have an empty `mana_cost`. So on today's data the list is empty on every deck, and the added call never runs.
- Why it is not equivalent: `RawCardMetadataEntry.cmc` and `.mana_cost` are optional (`types.ts:311-314`). A card with no mana cost (Ancestral Vision, Living End) gets `mv` "—" from `mvFromRow` (`normalize.ts:156-164`). When the card data script writes such a card into a deck, the mutant sends a refresh POST for it from the deck page.
- Failing input: the file holds Ancestral Vision (`mana_cost: ''`, `cmc: 0`) and Sol Ring (no `cmc`), seeded with prices from two days ago. The deck list shows both.
- Kill case: `/tmp/dec1174/kill/dec1174-deck-route-kill.test.tsx`. On the head it passes (`/tmp/dec1174/kill/kill-M10-head.log`). On M10 it fails at line 58: `AssertionError: expected "spy" to not be called at all, but actually been called 1 times`, with the body `{"identifiers":[{"name":"Ancestral Vision"},{"name":"Sol Ring"}]}` (`/tmp/dec1174/kill/kill-M10-mutant.log`). `npm run typecheck` exits 0 with the file in the tree, and `npx eslint` prints nothing (`/tmp/dec1174/kill/typecheck-with-kill-files.log`).
- Fix: add this file as `web/src/__tests__/components/DecklistNoRefresh.test.tsx`, with the import paths unchanged:

```tsx
// DEC-1174 reviewer kill case for M10 (a price refresh beside Decklist's enqueue,
// Decklist.tsx:147). Passes on the head of PR #75 and fails on M10.
// The deck list's cmc pass enqueues a card with no cmc or with mv '—' (a card
// with no mana cost, such as Ancestral Vision). For a name of the file the cache
// has a loaded entry, so that enqueue sends nothing, at any date (DEC-1172).
import { afterEach, beforeEach, describe, expect, it, vi, type MockInstance } from 'vitest';
import { render } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { Decklist } from '../../components/organisms/Decklist';
import { cardCache } from '../../data/cardCache';
import { LOOKUP_SPACING_MS } from '../../data/scryfallLimiter';
import type { DeckListGroup, RawCardMetadata } from '../../data/types';

const FILE: RawCardMetadata = {
  // No mana cost: the deck list shows mv '—' and asks the cache for its cmc.
  'Ancestral Vision': { cmc: 0, image: 'front/a/v/av.jpg?1', mana_cost: '', type_line: 'Sorcery', usd: 3.1, eur: 2.8 },
  // No cmc in the file (the field is optional).
  'Sol Ring': { image: 'front/s/r/sr.jpg?1', mana_cost: '{1}', type_line: 'Artifact', usd: 1.42, eur: 1.06 },
};
const old = () => new Date(Date.now() - 2 * 24 * 3_600_000).toISOString();

const LIST: DeckListGroup[] = [
  { name: 'Card draw (1)', cards: [{ n: 'Ancestral Vision', mv: '—', type: 'Sorcery', price: '—', gc: false, cmc: 0 }] },
  { name: 'Ramp (1)', cards: [{ n: 'Sol Ring', mv: '{1}', type: 'Artifact', price: '—', gc: false }] },
];

function clearStorage() {
  for (let i = window.localStorage.length - 1; i >= 0; i--) {
    const k = window.localStorage.key(i);
    if (k) window.localStorage.removeItem(k);
  }
}

let fetchSpy: MockInstance<typeof fetch>;

beforeEach(() => {
  cardCache._reset();
  clearStorage();
  fetchSpy = vi.spyOn(globalThis, 'fetch').mockImplementation(
    async () => new Response(JSON.stringify({ object: 'list', not_found: [], data: [] }), { status: 200 }),
  );
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('DEC-1174 kill: the deck list of a deck page', () => {
  it('asks for no price for a name of the file that it looks up for its cmc, with prices older than 24 h', async () => {
    const refreshSpy = vi.spyOn(cardCache, 'refreshPrice');
    cardCache.seed(FILE, old());
    render(
      <MemoryRouter initialEntries={['/deck/x']}>
        <Decklist list={LIST} commander="Captain" />
      </MemoryRouter>,
    );
    await new Promise((r) => setTimeout(r, LOOKUP_SPACING_MS + 300));
    expect(fetchSpy).not.toHaveBeenCalled();
    expect(refreshSpy).not.toHaveBeenCalled();
    expect(cardCache.pricePending('Ancestral Vision')).toBe(false);
    expect(cardCache.pricePending('Sol Ring')).toBe(false);
  });
});
```

### N items
**N1. Case (e) at `dec1102-card-data.spec.ts:281` kills `main`'s tile only in some runs.** With `main`'s `CardTile.tsx`, the case passed in 4 of 7 runs: 1 single run and 3 of 6 repeats (`/tmp/dec1174/e2e-main-tile.log`, `/tmp/dec1174/e2e-main-tile-281x6.log`). The poll at `:295` passes when it reads 0 file keys before the refresh answer stores its overlays. When it fails, it reads `Received: 34`. The hand-back's claim that this case fails on `main` holds for some runs only. Cases (a), (d) and (e:73) kill `main`'s tile in every run, so this is not a gap under the mutant rule. Fix: after line 295, insert these three lines:

```ts
    // No tile asks for a refresh, which would store a key for its name: look again after a batch's time.
    await page.waitForTimeout(3_000);
    expect((await cardKeys()).filter((key) => USD.has(key))).toEqual([]);
```

With the fix, the case fails in 6 of 6 runs on `main`'s tile and passes in 3 of 3 on the head (`/tmp/dec1174/kill/n-items-281-main-tile.log`, `/tmp/dec1174/kill/n-items-head.log`).

**N2. The new header of `dec1102-card-data.spec.ts` is wrong for one deck page case.** Lines 7 and 8 say that the deck page cases "run on a clock at which every price is older than 24 h". The hover case at `:180` opens `/deck/creeping-corruption` on `PRICES_ARE_FRESH` (`:185`), which is a leftover of option B. Fix: change line 185 to `  await page.clock.install({ time: pricesAreOld() });`. The case then passes in 3 of 3 runs on the head (`/tmp/dec1174/kill/n-items-head.log`). The patched spec with N1 and N2 is `/tmp/dec1174/kill/dec1102-card-data.n-items.spec.ts`, and its diff is `/tmp/dec1174/kill/n-items.diff`.

**N3. One sentence of the `cardCache.ts` header is unclear.** Lines 20 and 21 say: "A deck guide tile that shows the cache's price shows a live refresh too." The sentence does not say who refreshes. Fix: "A deck guide tile that shows the cache's price shows the price that /shopping refreshed in this browser inside 24 h, and asks for none itself."

**N4. "No request at any date" reads as absolute, but a failed picture still sends one.** `web/README.md:221-222`, `cardCache.ts:19-20` and `dec1102-card-data.spec.ts:7` say "a deck page sends no request for a deck card at any date". `web/README.md:227` and `cardCache.ts:25` say that a picture that fails to load sends the card in a batch. Ruling 4 puts that path out of scope, but a reader sees two rules that conflict. Fix: write "sends no price request for a deck card at any date" in the three places. The tests need no change.

**N5. The unit tiles get no `price`, but the app gives "—".** `normalize.ts:174` and `:352` give each tile with no highlight price `price: '—'`. Every `CardTile.test.tsx` case leaves `price` out. So no unit case catches M11 (`card.price` before `priceLive`) or M12 ("—" counts as a highlight price). Case (d) catches both in e2e at `dec1131-card-batches.spec.ts:467`. Optional fix: in case (a), render `{ n: 'Sol Ring', price: '—' }` and `{ n: 'Arcane Signet', price: '—' }`. I did not run this change.

**N6. Item 2(c) prints more lines than the brief expected.** The `git grep` also lists `Shopping.tsx:380` and `:462`. Both are `pricePending` reads on /shopping and send nothing.

**N7. `origin/main` moved during the review.** PR #64 merged at 09:40:06Z (`e886907`). The guard now lists `web/README.md`, `web/tests/dec1152-rate-check-post.spec.ts` (new) and `web/tests/support/test.ts`. A deck page and /shopping read none of them at run time. `support/test.ts` is the e2e fixture that every spec imports: its rate check now counts each POST twice. The merge with `e5e95b4` is clean (`8a5f46c`, the same tree that the hand-back read). My item 9 tree holds `e886907`, and the three specs pass there. CI run 38879467021 ran on the merge with `2cdb0fa`. A CI run on the merge with `e886907` before the merge would confirm the result.

**N8. The reload half of case (d) needs no scroll.** Every tile mounts at the first render: `web/src` has no `IntersectionObserver`, and on all 21 decks item 5 read the same tile count before and after the scroll. After a reload, a scroll only loads lazy pictures. M13 (a refresh when a picture loads) is already killed by the first half. No change is needed.

### 1. CI
- `web-ci` run 38879467021 on `e5e95b4` (pull_request, created 09:17:43Z): both jobs passed. Lint: `✖ 10 problems (0 errors, 10 warnings)`. Unit: `Test Files  50 passed (50)` and `Tests  617 passed (617)`. E2e: `217 passed (10.6m)`.
- `main`'s push run 38878552668 on `2cdb0fa`: both jobs passed. Lint: `✖ 10 problems (0 errors, 10 warnings)`. Unit: `Test Files  51 passed (51)` and `Tests  618 passed (618)`. E2e: `217 passed (9.7m)`.
- The difference is 1 file and 1 case: the deleted kill file. The e2e count is the same.

### 2. The source change
- (a) `CardTile.tsx` calls nothing on `cardCache` except `imageFailed` at `:109`. `grep -n 'cardCache\.'` prints only `109:              cardCache.imageFailed(card.n);`. The tile still reads the cache through `useCard(card.n)` at `:82`.
- (b) The price lines are the same as `main`'s, two lines higher (`main` `:93-94`, head `:91-92`):
  `const highlightPrice = !!card.price && card.price !== '—';` and `const price = highlightPrice ? card.price! : (priceLive || card.price || '—');`
- (c) The output:

```
e5e95b4:web/src/components/organisms/Shopping.tsx:282:    cardCache.refreshPrice(name);
e5e95b4:web/src/components/organisms/Shopping.tsx:380:  const waiting = buy.some((c) => cardCache.pricePending(c.name));
e5e95b4:web/src/components/organisms/Shopping.tsx:462:  const waitingForPrice = [...buy, ...own].some((c) => cardCache.pricePending(c.name));
e5e95b4:web/src/data/cardCache.ts:18://   - The price, when the price shown is older than 24 h (refreshPrice(): the
e5e95b4:web/src/data/cardCache.ts:49://   cardCache.refreshPrice(name)        → void             (refresh the price if it is older than 24 h)
e5e95b4:web/src/data/cardCache.ts:50://   cardCache.pricePending(name)        → boolean          (a price refresh of this card waits or is out)
e5e95b4:web/src/data/cardCache.ts:105:  refreshPrice(name: string): void;
e5e95b4:web/src/data/cardCache.ts:106:  pricePending(name: string): boolean;
e5e95b4:web/src/data/cardCache.ts:438:  function refreshPrice(name: string): void {
e5e95b4:web/src/data/cardCache.ts:446:    if (pricePending(name)) return;
e5e95b4:web/src/data/cardCache.ts:450:  function pricePending(name: string): boolean {
e5e95b4:web/src/data/cardCache.ts:631:  return { get, subscribe, enqueue, seed, imageFailed, refreshPrice, pricePending, _reset };
```

- (d) I computed the import closure of `main.tsx`, `App.tsx` and `routes/DeckGuide.tsx` (36 modules) and listed every `cardCache.` call and every `fetch(` in it:

| Call | Can it send a request for a name of the file? |
|---|---|
| `useCard.ts:5`, `:12` `get`; `:14` `subscribe` (the tiles, `GV1CommanderArt`) | No: these calls only read and subscribe. |
| `useCard.ts:15` `enqueue(name, { first })` | No. It runs only for a missing entry or an error entry. `loadCardMetadata` seeds the cache before any bundle resolves (`loader.ts:397-418`), and `seed()` gives every name of the file a `loaded` entry. `enqueue` returns at `cardCache.ts:411`. |
| `Decklist.tsx:147` `enqueue`; `:148` `subscribe`; `:155` `get` | No, for the same reason (`:411`). B1 is the mutant at this call. |
| `GV1CardHoverLayer.tsx:82-84` `subscribe`, `get`, `enqueue(hovered, { first: true })`; `:137` `get` | No, for a name of the file (`:411`). These calls run only on a hover. |
| `cardType.ts:14` `get` | No. |
| `CardTile.tsx:109`, `GV1CommanderArt.tsx:38`, `GV1CardHoverLayer.tsx:185` `imageFailed` | Yes, once in 24 h after a picture fails to load. This path is out of scope (ruling 4); see N4. |
| `loader.ts:371`, `spellbook.ts:123`, `synergy.ts:129` `fetchImpl(url)` | No: each fetches a `/data/...` path on the same origin. |
| `scryfallLimiter.ts:424` `fetchImpl(request.url, init)` | This is the only fetch to `api.scryfall.com`. The cache's pump (`cardCache.ts:601`) reaches it, and only for the calls above. |

- (e) `git diff -U0 origin/main...e5e95b4 -- web/src/data/cardCache.ts` changes 4 lines out and 6 lines in, and every one starts with `//`. A token compare with comments removed (the TypeScript scanner) gives 3,401 tokens with the same SHA-256 (`c6306b395587103b…`) on both files.

### 3. Unit case (a)
- The checks are as the brief says. The tile shows `$1.42` at the mount and `$0.35` after the rerender. After the wait, the case reads 0 `fetch` calls (`:121`), 0 `refreshPrice` calls (`:122`), `pricePending` false for both names (`:123-124`), and `$0.35` again (`:125`).
- The wait is long enough. `_reset()` calls `limiter._reset()`, which sets `lastStart = -Infinity` and clears the stop in memory. `clearStorage()` removes the shared last start and the stop record. A refresh calls `want()`, which calls `pump()`, which calls `limiter.next('lookup')`, which calls `drain()`. In `drain()`, `waitFor()` returns `max(0, -Infinity, -Infinity)` = 0, so `send()` calls `fetch` within microtasks. `render` and `rerender` both run before the first microtask, so a refresh at the mount and a refresh at the rerender go in one batch. On `main` the batch is `{"identifiers":[{"name":"Sol Ring"},{"name":"Arcane Signet"}]}`. If a batch were already out, the next one would start at `lastStart + 1,200 ms`, which is still inside the 1,500 ms. That holds because the stub answers at once with a 200. A 429 or a held answer would delay the next batch by the stop, but this case has neither. The wait misses only a refresh that the code itself delays by more than 1.5 s (M9); e2e cases (d) and (e:73) kill M9.
- On the head: `✓ … also when the tile gets another card 1503ms`, and the file reads `Tests  7 passed (7)` (`/tmp/dec1174/case-a-head.log`).
- On `main`'s `CardTile.tsx`: `× … 1506ms` at `CardTile.test.tsx:121:26`, with `AssertionError: expected "spy" to not be called at all, but actually been called 1 times`. The received line is `1st spy call: "https://api.scryfall.com/cards/collection"` with the body above. The file reads `Tests  1 failed | 6 passed (7)` (`/tmp/dec1174/case-a-main.log`). I restored the file from `HEAD`.
- Ruling 2: case (a) kills every mutant that makes a rerender ask with no delay: M1, M2, M3, M5, M6 and M7, all at `:121`. It misses two. M9 asks 2 s after a rerender, after the 1.5 s wait. M13 asks when a picture loads, and jsdom loads no picture. E2e cases (d) and (e:73) kill both.

### 4. E2e cases (d) and (e)
- On the head, the two specs give `21 passed (35.7s)` on port 14882 with 3 workers. The two ✘ lines are the `test.fail()` cases at `dec1131-card-batches.spec.ts:504` and `:526` (`/tmp/dec1174/e2e-head.log`).
- With `main`'s `CardTile.tsx` (`/tmp/dec1174/e2e-main-tile.log`, file restored from `HEAD`):
  - (d) `:437` fails at `> 459 |     expect(seen.batches).toEqual([]);` with `Received + 15` (one batch of 11 names, the first of them `Gray Merchant of Asphodel`).
  - (e) `:73` fails at `> 89 |   expect(seen.api).toEqual([]);` with `+   "POST https://api.scryfall.com/cards/collection",`.
  - (e) `:281` passed in this run, and fails only in some runs; see N1.
  - The run reads `2 failed` and `1 passed (21.4s)`.
- Case (d) checks the price of every tile. A tile with a highlight price must show that price (`:466`). Every other tile with a `usd` in the file must show `usdText(usd)` (`:467`). `formatUsd` (`cardEntry.ts:18-22`) writes the file's price as `$${usd.toFixed(2)}`. The stub's `usdOf` (`support/scryfall.ts:163-165`) answers `(usd + 1).toFixed(2)`. So with `scryfallUsdBump: 1`, a refreshed price is always $1.00 above the file's price. M11 and M12 fail at `:467`.
- The reload half: see N8. No change is needed.
- The 18 names outside the file on `eternal-harvest` all sit in `article.gv1-apo-remedy`, and none is a tile. Item 5 reads the same on every deck: names outside the file sit only in `article.gv1-apo-remedy` (and in `article.gv1-apo-pin` on `anvil-chorus`), and there are 0 tiles outside the file.

### 5. Every deck page
I used a scratch spec (`/tmp/dec1174/e2e/specs/every-deck.spec.ts`) and a scratch config (`/tmp/dec1174/e2e/playwright.config.ts`) on the head, with port 14882 and 3 workers. For each deck the spec sets `page.clock` as `pricesAreOld()` does, opens the page, scrolls to the end and waits 3 s. It counts every request that the context sends to `api.scryfall.com`. The head run gives `21 passed (49.7s)` (`/tmp/dec1174/e2e-every-deck-head.log`). As a control, I ran the same spec with `main`'s tile: `21 failed` (`/tmp/dec1174/e2e-every-deck-main-tile.log`).

| Deck | Tiles (at load / after the scroll) | Tiles outside the file | POST `/cards/collection` | All requests to `api.scryfall.com` | Control, `main`'s tile: POSTs (identifiers) |
|---|---|---|---|---|---|
| `titan-convergence` | 57 / 57 | 0 | 0 | 0 | 1 (6) |
| `eternal-agony` | 75 / 75 | 0 | 0 | 0 | 1 (2) |
| `eternal-harvest` | 126 / 126 | 0 | 0 | 0 | 1 (11) |
| `the-white-forge` | 40 / 40 | 0 | 0 | 0 | 1 (20) |
| `verdant-tide` | 80 / 80 | 0 | 0 | 0 | 1 (20) |
| `creeping-corruption` | 53 / 53 | 0 | 0 | 0 | 1 (34) |
| `witherbloom-the-balancer` | 64 / 64 | 0 | 0 | 0 | 1 (23) |
| `zada-hedron-grinder` | 53 / 53 | 0 | 0 | 0 | 1 (21) |
| `hidden-legion` | 48 / 48 | 0 | 0 | 0 | 1 (22) |
| `stampede-acres` | 46 / 46 | 0 | 0 | 0 | 1 (32) |
| `exponential-growth` | 46 / 46 | 0 | 0 | 0 | 1 (27) |
| `tidal-legion` | 30 / 30 | 0 | 0 | 0 | 1 (21) |
| `hoard-and-bleed` | 47 / 47 | 0 | 0 | 0 | 1 (22) |
| `grave-dividends` | 36 / 36 | 0 | 0 | 0 | 1 (16) |
| `slivers` | 29 / 29 | 0 | 0 | 0 | 1 (14) |
| `armory-protocol` | 35 / 35 | 0 | 0 | 0 | 1 (21) |
| `shield-doctrine` | 40 / 40 | 0 | 0 | 0 | 1 (19) |
| `gandalf-party-guest` | 41 / 41 | 0 | 0 | 0 | 1 (20) |
| `gathering-shadow` | 40 / 40 | 0 | 0 | 0 | 1 (28) |
| `broodfire-hatchery` | 44 / 44 | 0 | 0 | 0 | 1 (7) |
| `anvil-chorus` | 48 / 48 | 0 | 0 | 0 | 1 (26) |
| **All 21** | 1078 | 0 | 0 | 0 | 21 |

There is no request for a name of the file, and no tile name outside the file. I have no N item for the hub.

### 6. /shopping does not change
- `git diff origin/main...e5e95b4 -- web/src/components/organisms/Shopping.tsx` prints nothing. The `cardCache.ts` change is comments only; see 2(e).
- The describe block "/shopping refreshes the prices older than 24 h" passed in my item 4 run: `✓   9 [chromium] › tests/dec1131-card-batches.spec.ts:113:3 › /shopping refreshes the prices older than 24 h › first paint shows the file's prices with no request; …`. The `//` case (`:180`) and the stop line case (`:207`) passed in the same run.

### 7. Census and documents
- The brief's census on the head gives 32 hits. They are: case (a)'s spy (`CardTile.test.tsx:112`); case (b)'s title (`:128`); 17 hits in `cardCache.test.ts:345-518` and 6 in `dec1149-kills.test.ts:50-192`, all cache-level `refreshPrice` cases with no tile in any title; `Shopping.tsx:282`; the `cardCache.ts` API and header (`:18`, `:49`, `:105`, `:438`, `:631`); and the new comment at `dec1102-card-data.spec.ts:284`. Each hit is /shopping, the cache's API and its tests, or a text of the new rule.
- My wider search was a Python scan of `git ls-files web/src web/tests web/README.md CLAUDE.md AGENTS.md docs`. It prints each line that matches `refresh|older than 24|24 ?h\b|asks? (again|for a price)` when that line or a line next to it matches `\btiles?\b|deck guide|deck page|deck route|/deck/`. It found 13 hits: `web/README.md:32`, `:34`, `:221`, `:223`; `CardTile.test.tsx:99`, `:100`; `cardCache.ts:18`, `:21`; `dec1102-card-data.spec.ts:6`, `:284`; and `dec1131-card-batches.spec.ts:432`, `:433`, `:434`. Each states the new rule. A second search, `git grep -n -i -E 'PRICES_ARE_FRESH|pricesAreFresh|younger than 24'`, found the one case that the scan missed: the deck page hover case on a fresh clock (N2). `CLAUDE.md`, `AGENTS.md` and `docs/` have no hits.
- `web/README.md:29-35` and `:221-226` say that /shopping alone refreshes a price older than 24 h, and that a deck page sends no request for a deck card at any date. Lines 222 and 223 state ruling 3: "else the cache's price (the file's, or the price that /shopping refreshed in this browser inside 24 h)". The `cardCache.ts` header at `:18-24` says the same, with the unclear sentence of N3. N4 gives a wording fix for the picture exception.

### 8. Mutants
I wrote my own runner, based on the implementer's: `/tmp/dec1174/mutants.py`. It writes logs only under `/tmp/dec1174/mutants/`. It changes one or more files, finds each replaced text exactly once, restores each file byte for byte, and asserts the restore. `git status --porcelain` printed nothing after every run. I ran each mutant on the whole unit suite (617 cases) first. I ran the two specs of case (d) and case (e) only for a unit survivor.

| Mutant | Unit (617) | E2e (two specs) | Status | Log |
|---|---|---|---|---|
| M1: `main`'s effect | 1 failed: `CardTile.test.tsx:121` (a) | not run | killed | `M1-unit.log` |
| M2: no highlight guard | 2 failed: `:121` (a), `:132` (b) | not run | killed | `M2-unit.log` |
| M3: a name change only (a ref skips the mount) | 1 failed: `:121` (a) | not run | killed | `M3-unit.log` |
| M4: `cardCache.enqueue(card.n)` in an effect on `[card.n]` | 617 passed | 21 passed | equivalent (below) | `M4-unit.log`, `M4-e2e.log` |
| M5: the guarded refresh in `useLayoutEffect` | 1 failed: `:121` | not run | killed | `M5-layout-unit.log` |
| M6: the guarded refresh in the render body | 1 failed: `:121` | not run | killed | `M6-render-unit.log` |
| M7: `cardCache.refreshPrice(name)` in `useCard`'s effect for every name | 2 failed: `:121`, `:132` | not run | killed | `M7-usecard-unit.log` |
| M8: `priceLive` before the highlight price | 1 failed: `:61` ("keeps the deck file's price first") | not run | killed | `M8-live-first-unit.log` |
| M9 (own): the guarded refresh 2,000 ms after the mount, in a `setTimeout` | 617 passed | 2 failed: (d) `:459`, (e) `:89` | killed | `M9-delay2s-unit.log`, `M9-delay2s-e2e.log` |
| M10 (own): `cardCache.refreshPrice(n)` after `Decklist.tsx:147` | 617 passed | 21 passed; whole suite 217 passed | **survives: B1** | `M10-decklist-unit.log`, `M10-decklist-e2e.log`, `M10-decklist-e2e-full.log`, kill `M10-decklist-kill.log` |
| M11 (own): `card.price || priceLive` (the deck's "—" before the cache's price) | 617 passed | 1 failed: (d) `:467` | killed | `M11-file-dash-first-unit.log`, `M11-file-dash-first-e2e.log` |
| M12 (own): `highlightPrice = !!card.price` ("—" counts as a highlight) | 617 passed | 1 failed: (d) `:467` | killed | `M12-dash-is-highlight-unit.log`, `M12-dash-is-highlight-e2e.log` |
| M13 (own): the guarded refresh in the picture's `onLoad` | 617 passed | 2 failed: (d) `:459`, (e) `:89` | killed | `M13-onload-unit.log`, `M13-onload-e2e.log` |
| M14 (own): `cardCache.refreshPrice(hoveredName)` in the hover layer's effect | 2 failed: `CardPictures.test.tsx:69`, `dec1110/kill-pictures.test.tsx:72` | not run | killed | `M14-hover-unit.log` |

Every log is under `/tmp/dec1174/mutants/`. M7, M10 and M14 put a refresh beside each `cardCache` lookup that a deck route mounts (`useCard`, the deck list and the hover layer). Only the deck list's refresh survives.

**M4 is equivalent; I confirm the strike.** The reasons are these:
- The tile calls `useCard(card.n)` at `:82`, before the mutant's effect. React runs one component's passive effects in order and with no pause between them. So `useCard`'s effect (`useCard.ts:7-17`) runs first, with the same name.
- Its deps `[name, first]` change only when `card.n` changes, because `first` is always false for a tile. The mutant's deps are `[card.n]`, so both effects run in the same commits.
- After `useCard`'s effect, the entry is in one of these states:
  - The entry is `loaded` or `loading`: `useCard` sends nothing, and the mutant's `enqueue` returns at `cardCache.ts:411`. Every name of the file is in this state after `seed()`.
  - The entry is an error that is still held: both calls return at `:412`.
  - The entry is missing, or an error that is no longer held: `useCard`'s `enqueue` calls `want(…, 'lookup')`. The batch is taken only after `await waitForTurn()`, so the mutant's call finds `queued.lookup` set and returns at `:414`. If the pick had run, the entry would be `loading`, and the call would return at `:411`.
  - The name is empty: the call returns at `:407`.
- There is one theoretical gap. An error entry whose hold ends inside the sub-millisecond gap between the two synchronous calls gets one more lookup. A name of the file never holds an error entry after `seed()`, and a name outside the file is out of scope (ruling 4).

### 9. Merged with PR #70
- PR #70's head is still `a75bcc2`. `origin/main` was `e886907` (PR #64 merged) when I built the tree. `git merge-tree --write-tree origin/main e5e95b4` gave `8a5f46c`, and `git commit-tree` gave `372cbef`. `git worktree add --detach /tmp/dec1174/merged70 372cbef` and `git merge --no-edit a75bcc2` stopped on `web/README.md`, with one hunk. `cardCache.ts` auto-merged.
- My resolution keeps PR #70's lookup bullet, with the sentence about a blank front face, and this branch's refresh bullet. The merge commit is `6e02f0a`.
- `diff` of my file against the implementer's `pr70-merge-README.resolved.md` (`<` is mine):

```
87c87
< **The rate check.** A test fails when one browser context started more than 2 requests to
---
> **The rate check.** A test fails when one browser context sent more than 2 requests to
89,100c89,96
< methods. A GET counts once. A POST counts twice: the browser sends a CORS preflight
< (`OPTIONS`) before it, nobody knows whether Scryfall counts the preflight, and neither a route
< nor the `request` event shows it (DEC-1131 ruling 5, DEC-1149 N3). Playwright answers
< Chromium's preflight itself, so the double count is the only way the check sees it. The check
< stamps each request when the browser sends it (the context's `request` event), in real time.
< The app also counts each POST as two starts, and spaces its POSTs 1,200 ms apart. Two
< batches in 1 s start 4 requests and fail the test. A case proves the app's limit only when
< the app has lookups for two batches or more. A case that sends one batch, or paces its own
< hovers, reads a low peak whatever the app does. The `scryfall-stub` attachment of each test
< that sent a Scryfall request gives the count of requests, the peak in 1 s (a POST counts
< twice) and the number of 429 answers (`bucketOne`). The error lists each send of the context
< with its method.
---
> methods. The check stamps each request when the browser sends it (the context's `request`
> event), in real time. Playwright answers Chromium's CORS preflight of a batch itself: neither
> a route nor the `request` event sees an `OPTIONS` request, so the check counts the POST only.
> The app counts each POST as two starts and spaces them 1,200 ms apart. A case proves the
> app's limit only when it queues more lookups than the limit allows in 1 s. A case that sends one or
> two lookups, or paces its own hovers, reads a low peak whatever the app does. The
> `scryfall-stub` attachment of each test that sent a Scryfall request gives the count, the peak
> in 1 s and the number of 429 answers (`bucketOne`).
105,106c101,102
<   POST, and the limit of 2 in 1 s holds in the time that the app sees. It reads the method of
<   the call too, so a POST counts twice in this clock as well. Every other spec keeps `'real'`.
---
>   POST, and the limit of 2 in 1 s holds in the time that the app sees. Every other spec keeps
>   `'real'`.
```

  The conflict hunk is the same in both files. Every difference is PR #64's README text, which merged after the implementer resolved the conflict. `git merge-file -p <implementer's file> <README at 2cdb0fa> <README at e886907>` gives my file byte for byte.
- The merged `cardCache.ts` header reads as one text. The refresh paragraph is this branch's (`:18-24`). The ordering paragraph holds PR #70's sentence about a blank front face (`:32-34`).
- `package-lock.json` is the same as in the review tree (`cmp`), so I cloned `node_modules`. `npx vitest run` gives `Test Files  52 passed (52)` and `Tests  649 passed (649)` (`/tmp/dec1174/merged70-vitest.log`). The three specs on port 14884 give `23 passed (34.7s)`, with the two `test.fail()` cases as ✘ (`/tmp/dec1174/merged70-e2e.log`). Nothing fails.

### Trees
- Removed: `wt-dec1174-review` and `/tmp/dec1174/merged70`. Each `git status --porcelain` printed nothing first; for `merged70` I committed the resolved merge (`6e02f0a`). Then I ran `git worktree remove` (no `--force`) and `git worktree prune`. I did not touch `wt-dec1172`.
- At the end, PR #75's head is still `e5e95b4` (`MERGEABLE`), PR #70's head is still `a75bcc2`, and `origin/main` is `e886907`.
- I used two ports: 14882 in the review tree and 14884 in `merged70`. Every Playwright run used 3 workers. No run sent a request to a live Scryfall host. I pushed nothing.
- Scratch files and logs stay under `/tmp/dec1174/`.
