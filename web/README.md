# Grimoire web (DEC-149 rewrite)

Vite + React 18 + TypeScript. Replaces the legacy vanilla-JS `index.html` / `app.js` / `styles.css`
at Phase 6 cutover. Until then this lives entirely in `web/`; legacy keeps serving production.

## Scripts

```sh
npm install
npm run dev          # vite dev server on :5173
npm run build        # tsc -b + vite build → dist/
npm run preview      # serve dist/ on :4173
npm run lint         # eslint
npm run typecheck    # tsc: src/ and the Vite config, then tests/ and playwright.config.ts
npm run test         # vitest run
npm run test:e2e     # playwright (builds + previews under the hood)
```

### End-to-end tests

The e2e suite does not call Scryfall. Every spec imports `test` and `expect` from
`tests/support/test.ts`, not from `@playwright/test`. That module answers each request to a
Scryfall host from repository data, so a card gives the same answer on every run:

- The app takes every deck card from `data/card-metadata.json` (see "Scryfall requests"
  below): the facts, the picture addresses on `cards.scryfall.io` and the USD price. A deck
  page and /shopping therefore show every deck card at first paint, and /shopping shows its
  priced count then.
- /shopping and the deck guide tiles that show the cache's price ask again for a price older
  than 24 h, in batches. On any day after `prices_as_of` of `card-metadata.meta.json` every
  price of the file is that old, so these pages send batches. A case that proves "no request"
  sets `page.clock` to less than 24 h after `prices_as_of`; a case that proves the refresh sets
  it to more than 24 h after. Write no date into a spec: read it from the meta file.
- The app sends its card lookups as batches: `POST /cards/collection` with up to 75 names.
  The stub answers as Scryfall does: `{"object": "list", "not_found": [...], "data": [...]}`,
  with `data` in the order asked. A plain name, or the front face of a `//` card, matches
  without regard to case and accents; a full `//` name goes to `not_found`, as does a name
  that `card-metadata.json` lacks. More than 75 names get a 422 (the shape of that answer is a
  guess). The stub reads the mana cost, mana value, type line, picture path and USD price from
  the file, so an answer gives the entry that the app's own seed holds.
  `data/spellbook/price-index.json` stays the Combo Lab's price source; the stub does not read
  it. The stub still answers `/cards/named` (a 404 for a name outside the file) and
  `/cards/autocomplete`.
- Every `//` card of a batch answer has `card_faces`. A card with two halves on one side
  (adventure, split, room, prepare) keeps the joined cost and its pictures on the whole card,
  so the app shows the mana cost of the first half. A transform or modal_dfc card has
  `image_uris` only in its faces, as Scryfall sends it.
- A name whose `usd` is null in `card-metadata.json` has no price, in the app and in the stub.
  Do not write a priced count into a spec: read it from the file, because the prices change.
- Every card image is one flat rectangle of the size that the page asked for.
- The names outside the file go in one batch at the turn of bucket 1, 1,200 ms or more after
  the last. The first deck of /combos shows 20 cards; 16 of them are outside the file, and
  they go in one batch.

A spec picks another state with `test.use`:

```ts
import { expect, test } from './support/test';

test.use({ cards: 'seeded' });     // as 'repo', plus a gv1-card: entry for each name before first paint
test.use({ cards: 'none' });       // every lookup and card image fails; card-metadata.json has no prices
test.use({ fonts: 'blocked' });    // the Google Fonts hosts fail, so the fallback fonts show
test.use({ scryfall429From: 3 });  // /cards/named and /cards/collection answer 429 from their 3rd request on
test.use({ rateClock: 'page' });   // the rate check reads the page's clock: a spec that moves page.clock
test.use({ scryfallUsdBump: 1 });  // each usd of a /cards/collection answer is $1.00 more than the file's
```

`scryfallUsdBump` (0 by default) lets a case tell a refreshed price from the file's price. A
null `usd` stays null.

A read that measures a page with every price in uses `cards: 'seeded'`. The /shopping summary
then shows its final priced count at first paint, so the read needs no wait. The overflow read
of `dec181-qa` and the shots and audits of `dec184-visual-qa` do this.

The seed of `cards: 'seeded'` writes 1,602 entries, about 992,000 characters, into
`localStorage`: one for each name of `card-metadata.json` and one for each face of a `//` name
that the file does not hold as a name. The app's own seed drops the entries of the file's
names when a page loads deck data, so for those names a seeded page is the page of the
default `'repo'`, and 46 entries (about 30,000 characters) stay. A seeded spec that measures
the quota before a deck page starts from about 19 % of the 5 MB quota, not from zero.

`cards: 'none'` also answers `/data/card-metadata.json` with `usd` and `eur` set to null, so
the page shows its layout with no prices.

**The rate check.** A test fails when one browser context started more than 2 requests to
`/cards/named` and `/cards/collection` in any 1 s. Scryfall allows 2 a second on those
methods. A GET counts once. A POST counts twice: the browser sends a CORS preflight
(`OPTIONS`) before it, nobody knows whether Scryfall counts the preflight, and neither a route
nor the `request` event shows it (DEC-1131 ruling 5, DEC-1149 N3). Playwright answers
Chromium's preflight itself, so the double count is the only way the check sees it. The check
stamps each request when the browser sends it (the context's `request` event), in real time.
The app also counts each POST as two starts, and spaces its POSTs 1,200 ms apart, so two
batches in 1 s fail the test. A case proves the app's limit only when the app has lookups for
two batches or more. A case that sends one batch, or paces its own hovers, reads a low peak
whatever the app does. The `scryfall-stub` attachment of each test that sent a Scryfall request
gives the count of requests, the peak in 1 s (a POST counts twice) and the number of 429
answers (`bucketOne`). The error lists each send of the context with its method.

- A spec that moves `page.clock` can start several requests in one real second, because the
  page's timers run ahead of real time. Such a spec sets `rateClock: 'page'`. The check then
  reads the page's own clock each time the app calls `fetch` for those methods, a GET or a
  POST, and the limit of 2 in 1 s holds in the time that the app sees. It reads the method of
  the call too, so a POST counts twice in this clock as well. Every other spec keeps `'real'`.
- `scryfall429From: n` makes the stub answer 429 from the n-th request to those methods on,
  counted over the test. Scryfall's own 429 has no CORS header, so the browser blocks it and
  the app's `fetch` rejects. Playwright adds that header to an answer without one, so the stub
  sends a header for another origin, and the browser blocks the answer in the same way.

Three checks keep a spec off the live API. Each has limits, and they are listed here.

1. **The import scan.** `playwright.config.ts` reads every script file under `tests/` as text.
   It stops the run before the build when one of them imports, requires or names in a comment
   `@playwright/test`, `playwright/test`, `playwright` or `playwright-core`. The import can
   break across lines. The error names the file and the line that holds the module name.
   - The scan does not see a dynamic import whose module name is put together at run time.
   - The scan does not read files outside `tests/`. A helper there that passes Playwright's
     own `test` on gives a spec no stub.
2. **The per-test check.** The stub and this check are on the `context` fixture, and on every
   context that a test or a `beforeEach` opens with `browser.newContext()` or
   `browser.newPage()`. A request to a Scryfall host that the stub did not answer fails its
   test, and the error names the request and what happened to it.
   - A spec cannot answer a Scryfall host with its own route: that request fails the test too
     ("a route of the spec answered it"). The check cannot see where a route took its answer
     from, and `route.fetch()` calls the live API from Node. To change the timing of an answer,
     wait in the route and then call `route.fallback()`; the stub answers.
   - With `rateClock: 'real'`, the rate check stamps a request to `/cards/named` or
     `/cards/collection` when the browser sends it, before any route. A request that a spec's
     route holds and then passes on with `route.fallback()` counts at its send (DEC-1131 N2).
   - A request that the page cancelled (`net::ERR_ABORTED`) does not fail the test. It did not
     leave the browser. A spec's own `route.abort('aborted')` reads the same.
   - A context that a spec opens in `beforeAll` or `afterAll` has no stub and no check. Its
     card lookups fail at the DNS block.
   - `page.request`, `context.request` and `route.fetch()` send from Node. No route, no check
     and no DNS block applies to them. Do not give them a Scryfall or a Moxfield URL.
   - A host name that ends in the root dot (`api.scryfall.com.`) is the same host. The stub's
     route takes the request, but the stub has no answer for that name. The test fails, and
     the error says "(the stub has no answer for it)".
   - A request to a Moxfield host (`moxfield.com` and every name under it) needs an answer from
     a route of the spec. Unlike for Scryfall, a spec's own route answer passes. The IN-2 case
     of `combo-lab.spec.ts` answers `api2.moxfield.com` with HTTP 403, the refusal that the
     live host gives a headless browser. The check names a Moxfield request that passes every
     route of the spec. The stub stops such a request when no route of the spec took it. A
     spec's `route.continue()` sends it on, and the DNS block then fails it with
     `net::ERR_NAME_NOT_RESOLVED`. The check names both, and also one that the network
     answered.
   - Behind an HTTP proxy the DNS block does nothing. A Moxfield request that a spec's route
     sends on and that the proxy refuses is not named.
   - A spec's own `route.abort('namenotresolved')` on a Moxfield URL is named, although it
     never left the browser. `request.timing()` cannot tell it from a request that the DNS
     block stopped: every field reads -1 in both.
3. **The DNS block.** Chromium gets `--host-resolver-rules`, so it cannot resolve a Scryfall
   host name or a Moxfield host name. A request that passes the stub or a spec's route fails
   on this machine with `net::ERR_NAME_NOT_RESOLVED`, and it does not reach Scryfall or
   Moxfield. The flag stays when a spec sets its own `launchOptions`. Each name has a rule
   without and a rule with the root dot: a rule without the dot does not match
   `api.scryfall.com.`.
   - Behind an HTTP proxy (the `proxy` option, or `--proxy-server`) the proxy resolves the
     names, and the block does nothing. The stub and the per-test check still apply.
   - A browser that a spec launches itself has the flag only if the spec passes it:
     `withScryfallDnsBlock(args)` in `tests/support/guard.ts`.

`GRIMOIRE_E2E_PORT` moves the preview server off port 4173:

```sh
GRIMOIRE_E2E_PORT=4319 npm run test:e2e
```

On a machine that other checkouts share, set the variable on every run, with a port value of
your own. With it set, the run builds this checkout, starts its own server and sends its
cases to that server only. It does not ask the port who is there. It waits for the line that
its own `vite preview` prints after it holds the port.

- If another process holds the port on 127.0.0.1, the run stops after the build with
  `Port <n> is already in use`, and no case runs. That takes the build time and about one
  second: 3 s to 4 s on a warm build. A listener that accepts and never answers stops the run
  in the same way.
- If two runs with one port value overlap, the run whose server takes the port first runs
  the cases, on its own build. The other stops with the same message. A run whose server
  starts after the other run has ended takes the free port and runs its cases on its own
  build.
- On macOS a server that listens on every address (`*:<n>`) does not stop the run. The run's
  server binds 127.0.0.1 next to it and gets the cases.

Without the variable nothing is checked: a local run reuses a server that already listens on
4173, which can be the build of another checkout. CI runs without the variable and always
starts its own server. In CI the run also writes the HTML report to `playwright-report/`, and
web-ci uploads it when the `e2e` job fails.

## Scryfall requests

`src/data/scryfallLimiter.ts` sends every request to `api.scryfall.com`; no other file in
`src/` outside the tests names that host.

- **Bucket 1** holds `/cards/collection`. Every card lookup is one POST of up to 75 names. A
  JSON POST goes after a CORS preflight, and nobody knows whether Scryfall counts it, so each
  POST counts as two starts: a request starts 1,200 ms or more after the last start, and only
  after the last answer has arrived. Inside a tab the spacing runs on `performance.now()`, so
  a step of the wall clock does not shorten it. The tabs of one origin share the bucket
  through `navigator.locks` and the last start (wall time) in `localStorage`.
- **Bucket 2** holds `/cards/autocomplete`, 120 ms apart. While a stop holds, the Atlas sends
  no autocomplete and keeps its own suggestions.
- **The timeout.** A request with no answer after 20 s is aborted, and it counts as a rejected
  `fetch`. An abort by the caller is no failure.
- **The stop.** A 429, a rejected `fetch` or the timeout stops both buckets for 30 s; the
  request that met it goes first when the stop ends. If that one fails too, the stop doubles,
  up to 300 s, and a success resets it. The stop record holds its end, its length and a
  number: a request can double or end only the stop whose number it noted when it started. A
  record that ended more than 300 s ago counts as none. A clock that went back cannot stretch
  a stop past now plus its length, also when the stop lives in memory. The record lives in
  `localStorage`, so a reload and a second tab obey it.

The card cache (`src/data/cardCache.ts`) takes every deck card from `data/card-metadata.json`
before a page can show it: facts, USD price dated `prices_as_of`, and Scryfall's picture
addresses on `cards.scryfall.io`.

- A name that the file lacks goes in the next batch. Names asked `first` (the hover, the
  commander art) go before the other lookups, and lookups go before refreshes. A `//` name
  goes out as its front face, two names with one front face go out once, and the answer is
  matched by name, never by position. A name in `not_found` gets no other request for 24 h,
  also after a reload. An answer with another status (a 400 or a 422) fails the batch's names
  for 30 s and starts no stop.
- /shopping and the deck guide tiles that show the cache's price (a tile shows the deck
  file's highlight price first) ask again for a price older than 24 h. A refresh changes only
  the price and its date, and lives 24 h under `gv1-card:` next to the file's entry; the
  file's price wins when the file is newer. A refresh that gets no price keeps the price shown
  and is not asked again inside 24 h.
- A picture from the file that fails to load sends the card in a batch once; the answer's
  addresses replace the file's for 24 h.
- /shopping shows the file's prices at first paint. Its estimate changes once, when the
  answers for its rows have arrived. The footer gives the oldest date among the priced rows.
  While a stop holds and a row waits for a refresh, a line with `role="status"` says that the
  refresh is paused, the date of the prices shown and the clock time of the next try.

## Layout

```
web/
├── src/
│   ├── components/     atoms + molecules (port targets in Phase 1)
│   ├── routes/         one per artboard (7 stubs in Phase 0)
│   ├── styles/         tokens.css · states.css · styles.css · app.css
│   ├── App.tsx         router + shell
│   └── main.tsx        entry
├── tests/              playwright smoke tests
└── …                   vite / tsconfig / eslint / playwright config
```

Source of truth for design tokens: `src/styles/tokens.css` (port of
`design_handoff_grimoire/prototype/gv1-tokens.css`). Components use
`var(--gv1-*)` exclusively — no inline hex.
