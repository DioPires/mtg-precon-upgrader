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
