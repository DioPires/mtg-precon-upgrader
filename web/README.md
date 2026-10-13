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
npm run typecheck    # tsc -b --noEmit
npm run test         # vitest run
npm run test:e2e     # playwright (builds + previews under the hood)
```

### End-to-end tests

The e2e suite does not call Scryfall. Every spec imports `test` and `expect` from
`tests/support/test.ts`, not from `@playwright/test`. That module answers each request to a
Scryfall host from repository data, so a card gives the same answer on every run:

- A card lookup reads the mana cost, mana value and type line from `data/card-metadata.json`
  and the USD price from `data/spellbook/price-index.json`. A name that `card-metadata.json`
  lacks gets a 404.
- Every card image is one flat rectangle of the size that the page asked for.
- The app still sends one lookup every 120 ms. A page with 88 cards has them all after about
  11 s (`networkidle`). The Shopping summary redraws on a 1.5 s timer, so it can show a lower
  priced count for a moment longer.

A spec picks another state with `test.use`:

```ts
import { expect, test } from './support/test';

test.use({ cards: 'seeded' });  // every card answer is in the app's cache before first paint
test.use({ cards: 'none' });    // no card answers: every lookup and every card image fails
test.use({ fonts: 'blocked' }); // the Google Fonts hosts fail, so the fallback fonts show
```

Three checks keep a spec off the live API:

- `playwright.config.ts` stops the run before it starts when a file in `tests/` imports
  `@playwright/test` directly, and names the line.
- A request to a Scryfall host that the stub did not answer fails its test. The error names
  the request.
- Chromium cannot resolve a Scryfall host name during a run, so such a request fails on this
  machine and never reaches Scryfall. A context that a spec opens itself with
  `browser.newContext()` has no stub; its card lookups fail in this way.

`GRIMOIRE_E2E_PORT` moves the preview server off port 4173:

```sh
GRIMOIRE_E2E_PORT=4319 npm run test:e2e
```

With the variable set, the run always builds and serves this checkout, and it stops if the
port is taken. Without it, a local run reuses a server that already listens on 4173, which
can be the build of another checkout.

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
