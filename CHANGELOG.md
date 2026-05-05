# Changelog

## 2026-05-05 — DEC-149 Phase 6: Big-bang cutover

The Grimoire moves to a new frontend. **Production-visible event.**

### Added
- New app at [`web/`](web): Vite + React 18 + TypeScript, react-router with `?deck=...&view=...` URL state
- Seven artboards ported from `design_handoff_grimoire/prototype/`:
  Deck Guide, Codex (overview), Compare (sortable health table), Shopping (CSV/TXT import,
  `grimoire-owned-cards` localStorage migrated), Mobile, Scrying Pool (hand sim + swap analyzer),
  Dev (component sandbox)
- `useCard()` hook with 80ms throttle + dedupe + 24h localStorage cache
- Deck loader with 24h localStorage TTL (`gv1-deck-data:` keys)
- Vitest unit tests on data normalization + useCard cache + Scrying delta math
- Playwright smoke per artboard
- 3-layer design-token system in `web/src/styles/tokens.css` (`--gv1-*`)

### Changed
- Deploy: `vercel.json` now runs `cd web && npm install && npm run build`, copies `data/` into `dist/data/`, and serves `web/dist/` as host root
- `AGENTS.md`: dropped "no build step" rule; documents new build/dev/test commands and architecture
- `CLAUDE.md`: notes cutover and points contributors at `web/`

### Archived
- `index.html`, `app.js`, `styles.css` → [`legacy/`](legacy) for one release. Will be deleted in a follow-up. See `legacy/README.md` for rollback notes.

### Unchanged
- `data/commanders/{id}/{deck,simulation,metrics,candidates}.json` — canonical, shared (legacy archive consumed the same JSON)
- `data/index.json` schema — no path changes needed (loader hardcodes `/data/commanders/{id}/...`)
- `data/game-changers.json` — same 51-card list
- `localStorage` keys: `grimoire-prefs`, `grimoire-owned-cards` preserved across cutover

### Phase plan reference
See [`DEC-149-plan.md`](DEC-149-plan.md). Phases 0–5 landed in DEC-151 through DEC-156.
Phase 7 (post-port refactors: Sigil/MonoLabel/RuneRule/PriceChip/StatBlock/SwapRow,
font-size token scale, hex-to-token sweep) is queued separately.
