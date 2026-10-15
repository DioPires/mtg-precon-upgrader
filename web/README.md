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
  page and /shopping therefore send no lookup, and /shopping shows its priced count at first
  paint.
- A card lookup reads the mana cost, mana value, type line, picture path and USD price from
  the same file, so a lookup gives the entry that the app's own seed holds. A name that
  `card-metadata.json` lacks gets a 404. `data/spellbook/price-index.json` stays the Combo
  Lab's price source; the stub does not read it.
- A card with two halves on one side (adventure, split, room, prepare) comes with
  `card_faces`, as Scryfall sends it, so the app shows the mana cost of the first half.
- A name whose `usd` is null in `card-metadata.json` has no price, in the app and in the stub.
  Do not write a priced count into a spec: read it from the file, because the prices change.
- Every card image is one flat rectangle of the size that the page asked for.
- A name outside the file gets one lookup through the limiter, 600 ms or more after the last.
  The first deck of /combos shows 20 cards; 16 of them are outside the file, and their 16
  lookups take about 10 s.

A spec picks another state with `test.use`:

```ts
import { expect, test } from './support/test';

test.use({ cards: 'seeded' });     // as 'repo', plus a gv1-card: entry for each name before first paint
test.use({ cards: 'none' });       // every lookup and card image fails; card-metadata.json has no prices
test.use({ fonts: 'blocked' });    // the Google Fonts hosts fail, so the fallback fonts show
test.use({ scryfall429From: 3 });  // /cards/named and /cards/collection answer 429 from their 3rd request on
test.use({ rateClock: 'page' });   // the rate check reads the page's clock: a spec that moves page.clock
```

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

**The rate check.** A test fails when one browser context sent more than 2 requests to
`/cards/named` and `/cards/collection` in any 1 s. Scryfall allows 2 a second on those
methods. The stub counts the requests at its route, in real time. A case proves the app's
limit only when it queues more lookups than the limit allows in 1 s. A case that sends one or
two lookups, or paces its own hovers, reads a low peak whatever the app does. The
`scryfall-stub` attachment of each test that sent a Scryfall request gives the count, the peak
in 1 s and the number of 429 answers (`bucketOne`).

- A spec that moves `page.clock` can start several requests in one real second, because the
  page's timers run ahead of real time. Such a spec sets `rateClock: 'page'`. The check then
  reads the page's own clock each time the app calls `fetch` for those methods, and the limit
  of 2 in 1 s holds in the time that the app sees. Every other spec keeps `'real'`.
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
     `/cards/collection` when the stub's route answers it. A request that a spec's route holds
     and then passes on with `route.fallback()` counts at its release, not at its send, so a
     held request can read as a burst. Pull request 3 of design D (DEC-1072) moves the stamp to
     the request event.
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

`src/data/scryfallLimiter.ts` sends every request to `api.scryfall.com`; no other file names
that host. Bucket 1 holds `/cards/named` and `/cards/collection`: a request starts 600 ms or
more after the last start, and only after the last answer has arrived. The tabs of one origin
share it through `navigator.locks` and `localStorage`. Bucket 2 holds `/cards/autocomplete`,
120 ms apart. A 429, or a `fetch` to that host that rejects, stops both buckets for 30 s; the
request that met it goes first when the stop ends. If that one fails too, the stop doubles, up
to 300 s, and a success resets it. The stop's end lives in `localStorage`, so a reload and a
second tab obey it. The card cache takes every deck card from `data/card-metadata.json`
before a page can show it: facts, USD price, and Scryfall's picture addresses on
`cards.scryfall.io`. It looks up only a name that the file lacks, and once a card whose picture
from the file failed to load.

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
