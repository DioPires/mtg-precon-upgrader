---
issue: DEC-149
title: Web UI redesign — implementation plan
revision: 2
status: approved (board answered 2026-05-05; decisions locked)
owner: CEO
date: 2026-05-05
---

## Board decisions (locked 2026-05-05)

- **Stack**: Vite + React + TypeScript ✓
- **Migration**: Build alongside in `web/`, swap when ready ✓
- **Team**: Hire `frontend-eng`, refactor `design-eng` → `design-system-eng`, merge `interactive-eng` into `frontend-eng` ✓
- **Rollout**: **Big-bang** — hold until all 7 surfaces reach parity, then a single coordinated launch. (Overrode my phased-deploy recommendation.)

What "big-bang" changes from the original phased plan:
- Phases still run sequentially (work has dependencies); but no `/v2/...` deployable-each-phase gating.
- The new app lives entirely in `web/` until cutover. Legacy site keeps serving production traffic the whole time.
- Each phase still produces a real PR + working slice — they merge into the rewrite branch / `web/`, not into a public route.
- Phase 6 (cutover) becomes the **only** production-visible event: domain swap, legacy archive, CHANGELOG, comms.

---

# DEC-149 — Grimoire v1 Implementation Plan

## TL;DR

The handoff in `design_handoff_grimoire/` is a **pixel-final React/JSX prototype of seven surfaces**, not an iteration on the current vanilla-JS app. Treating this as anything less than a full frontend rewrite undersells the scope and leads to a strangler that paints us into a corner.

**Recommended path**:

1. **Stack**: Vite + React + TypeScript, deployed as static output. Closest to the prototype's shape, lowest port friction, keeps us hostable anywhere.
2. **Strategy**: Build alongside in `web/` directory; current `index.html` keeps serving until parity. Surface-by-surface, deployable each phase.
3. **Team**: Hire `frontend-eng` (React/Vite/TS). Refactor `design-eng` → `design-system-eng` (drop Pencil, own tokens + a11y + visual QA). Merge `interactive-eng` into `frontend-eng` (Scrying is now a React component). Keep `sim-eng` and `founding-eng` as-is, with `founding-eng` pivoting to data normalization + research glue.
4. **Rollout**: 6 phases, ~4–7 weeks of focused work. Each phase ships a real PR.

Open questions at the bottom — please react.

---

## Reality check on the handoff

**What it actually is**:
- 12 React/JSX components organized atoms → molecules → organisms → artboards
- `gv1-tokens.css`: 3-layer (primitive → semantic → component) design-token system
- `gv1-data.js`: deck normalization layer that produces a single `DECK_FULL[]` shape
- `useCard()` hook: shared Scryfall cache, throttled + deduped
- Container queries (`@container`) for Scrying mobile reflow inside the canvas
- Hand-loaded via `@babel/standalone` + `?v=N` cache-busting — explicitly **not** production
- Inlined deck JSON in `gv1-real-decks.js` — production must fetch from `data/commanders/{id}/*.json`

**What's missing / explicitly cut**:
- URL state (`?deck=...&view=...`) — was on the recommended-yes list, never wired
- `preview.html` is stale
- Hard-coded hex values in `gv1-styles.css` (mana-value chips, card-art fallback)
- No font-size token scale — utility classes per component
- Several patterns visible in design but not factored into components: `Sigil`, `MonoLabel`, `RuneRule`, `PriceChip`, `StatBlock`, `SwapRow`

**Source-data gap**: handoff `source-data/commanders/` has 8 decks; production has 9 (HANDOFF.md's "12" is stale). Resolved in DEC-150 — snapshot dropped, production canonical. See [`design_handoff_grimoire/RECONCILIATION.md`](design_handoff_grimoire/RECONCILIATION.md).

---

## Why this is a rewrite, not an iteration

The current app:
- 669-line `index.html` + 6293-line `app.js` + 5863-line `styles.css`, vanilla JS, no build step
- Project AGENTS.md hard-codes "No build step. Static files."
- All views (Grimoire / Battlefield / Scrying Pool / Shopping List) live in one `app.js`
- Naming, data shape, and CSS classes all baked to the existing scheme (see memory: `highlights`, `categories`, `.highlighted`, etc.)

The handoff:
- React component model with prop contracts (`components.api.js`)
- New normalized `DECK_FULL` shape that diverges from raw `deck.json`
- Token system with `gv1-*` prefix everywhere
- Surfaces re-named (Grimoire → Deck Guide / Codex / Compare / Shopping / Scrying / Mobile)

Trying to bridge these incrementally inside the current `index.html` means dragging React + tokens + container queries into a vanilla DOM — net negative. Build alongside, swap when ready.

---

## Architecture decisions (proposed)

| Decision | Pick | Why |
|---|---|---|
| Framework | **React 18 + Vite + TypeScript** | Direct port of JSX, fast HMR, static `dist/` output, TS catches deck.json contract drift |
| Routing | **react-router** with `?deck=...&view=...` URL state | Cuts deferred work from prototype; 7 artboards become 7 routes |
| Styling | **CSS modules + tokens.css imported globally** | Mirrors prototype structure; no Tailwind/CSS-in-JS overhead |
| Data fetching | `useCard()` ported as-is; deck JSON via `fetch` + Suspense | Matches prototype contract; no SSR needed |
| Card cache | **In-memory Map + localStorage TTL (24h)** | Reduces Scryfall load on repeat visits |
| Component lib | **None** — port handoff atoms/molecules into `components/` | Avoids style fights with shadcn/etc.; design system is opinionated |
| Test stack | **Vitest + Playwright** | Vitest for normalization/data layer; Playwright smoke for each artboard |
| Deploy | **Static** — same hosting story as today | No backend. Deploy `dist/` to wherever `index.html` lives now |
| Directory | `web/` for new app; existing files untouched until cutover | Lowest-risk migration |

---

## Team changes

### Current team
| Role | Tools | Status post-DEC-149 |
|---|---|---|
| ceo | (governance) | Keep |
| design-eng | Pencil MCP, browse, scryfall | **Refactor → design-system-eng** (Pencil dead, design is final) |
| founding-eng | scryfall, csb, youtube, scripts | Keep, pivot frontend → data |
| interactive-eng | scryfall, csb, scripts | **Merge into frontend-eng** |
| sim-eng | python sim, scryfall | Keep (independent) |

### Proposed team after DEC-149
| Role | Owns | Tools |
|---|---|---|
| ceo | governance, prioritization, board sync | (unchanged) |
| **frontend-eng (NEW)** | Vite/React build, all components, tokens.ts, data layer, URL state, Scrying logic | Vite, React, TS, browse, scryfall MCP |
| **design-system-eng (refactor of design-eng)** | tokens.css guardian, a11y audits, visual QA via /browse + screenshots, post-port component factoring (Sigil/MonoLabel/etc.), design QA gates on PRs | browse, gstack, scryfall (NO Pencil) |
| founding-eng | deck data research, deck.json schema, normalization layer source data, 12-deck reconciliation, MCP server stewardship (commanderspellbook/youtube/archidekt) | scryfall, csb, youtube, archidekt, scripts |
| sim-eng | simulation.json schema, sim scripts, Karsten-style metrics, deck health score | python, scryfall |

### Rationale
- **Pencil is dead** → design-eng tools list updates anyway. No more .pen files. "Design" work going forward is QA + token stewardship + factoring, not pixel comps.
- **interactive-eng's signature features (hand sim, swap analyzer) are already implemented in `gv1-scrying.jsx`**. After the port, ongoing maintenance is React work — folds naturally into frontend-eng. Keeping interactive-eng as a separate role would mean duplicating React expertise.
- **frontend-eng is the gap**. None of the current team is scoped for React/Vite/TS/component-library work. Without this hire we'd be teaching one of the existing eng on the job, slowing the rewrite by weeks.
- **founding-eng** has been the de-facto generalist. After DEC-149, frontend leaves their plate. They become the deck/data/research authority — which is more aligned with the project's actual differentiation.
- **sim-eng** is unaffected; sim infrastructure is Python and feeds JSON the frontend consumes.

---

## Phased implementation plan

Each phase is a separable PR that ships a working slice. Phases run roughly sequential; some parallelization noted.

### Phase 0 — Foundation (frontend-eng, 2–3 days)
- Scaffold Vite + React + TS in `web/`
- Port `gv1-tokens.css` as `web/src/styles/tokens.css`, imported globally
- Port `gv1-states.css`, `gv1-styles.css` as global stylesheets
- Set up routing (`react-router`) with empty routes for the 7 artboards
- CI: lint + tsc + vitest + playwright on `web/**`
- Deploy a hello-world build to confirm host pipeline
- **Exit criteria** (in `web/` dev build only — not deployed): visiting `/` renders an empty token-themed shell with the topbar

### Phase 1 — Atoms, molecules, hooks (frontend-eng, 3–4 days)
- Port `useCard()` hook with localStorage 24h cache addition
- Port atoms: `ManaCost`, `GV1ManaPips`
- Port molecules: `CardTile`, `GV1CommanderArt`
- Port `GV1CardHoverLayer` (mounted at root)
- Vitest unit tests on the data layer + useCard cache behavior
- **Exit criteria**: a Storybook-equivalent route (`/v2/_dev`) renders all atoms/molecules with sample data

### Phase 2 — Data layer + Deck Guide (frontend-eng + founding-eng, 5–7 days)
- founding-eng: ✅ resolved (DEC-150) — `source-data/` dropped as snapshot; production canonical. See [`design_handoff_grimoire/RECONCILIATION.md`](design_handoff_grimoire/RECONCILIATION.md). Actual deck count is **9**, not 12.
- frontend-eng: write loader that fetches `data/commanders/{id}/{deck,simulation,metrics,candidates}.json` for each of 9 decks. (`recommendations.json` from HANDOFF.md does not exist — drop it.)
- frontend-eng: port `gv1-data.js` → `web/src/data/normalize.ts` with TypeScript types for `DeckFull`
- frontend-eng: port Deck Guide organisms (Topbar, Hero, DeckSelector, Commander, WinCons, Engine, Combos, Apothecary, Performance, Decklist)
- design-system-eng: visual QA pass against prototype screenshots
- **Exit criteria**: `web/` dev build at `/deck/:id` renders all 9 decks with full Deck Guide parity

### Phase 3 — Codex + Compare (frontend-eng, 3–4 days)
- Port `GV1Codex` (cross-deck overview)
- Port `GV1Compare` (sortable table with health components)
- design-system-eng: a11y audit (tablist patterns, keyboard nav, focus rings)
- **Exit criteria**: `web/` dev build at `/codex` and `/compare` render all 9 decks; click a deck → navigates to Deck Guide

### Phase 4 — Shopping + Mobile reflows (frontend-eng + design-system-eng, 4–5 days)
- Port `GV1Shopping` with localStorage `grimoire-owned-cards` (preserve existing key for migration)
- Port `GV1Mobile` (per-deck mobile artboard)
- design-system-eng: container-query and viewport responsive verification across surfaces
- **Exit criteria**: Shopping with CSV/TXT import works; mobile guide renders on real phone

### Phase 5 — Scrying Pool (frontend-eng, 5–7 days)
- Port `GV1Scrying` (hand simulator + swap analyzer + KPIs)
- Port `gv1-game-changers.js` (already 51-card list)
- Container-query mobile reflow
- Vitest tests on shuffle/mulligan/delta math
- design-system-eng: extensive interaction QA — this is the most state-heavy surface
- **Exit criteria**: hand sim full London mulligan flow + swap analyzer with all 7 delta categories

### Phase 6 — Cutover + cleanup (frontend-eng + design-system-eng, 2–3 days)
- Promote `web/` build to root, retire `index.html` + `app.js` + `styles.css` (move to `legacy/` for one release)
- Update `data/index.json` references if needed
- Update `AGENTS.md` ("No build step" → "Vite build")
- Update memory: rename `highlights` references, etc.
- design-system-eng: full-site visual regression sweep
- **Exit criteria**: production traffic on new app; old code archived; CHANGELOG entry; CLAUDE.md updated

### Phase 7 — Post-port refactors (design-system-eng + frontend-eng, ongoing)
- Promote `Sigil`, `MonoLabel`, `RuneRule`, `PriceChip`, `StatBlock`, `SwapRow` to standalone components
- Promote font-size utility classes to numeric scale tokens
- Promote remaining hard-coded hex values to tokens
- Service worker / prefetch for Scryfall (out-of-scope until measured)

---

## Cross-cutting work

| Item | Owner | When |
|---|---|---|
| ~~12-deck reconciliation (source-data has 8)~~ | ✅ founding-eng (DEC-150, 2026-05-05) — actual count 9; snapshot dropped, production canonical |
| Source-attribution rendering (existing `sources` field — verify it surfaces somewhere in new UI) | frontend-eng | Phase 2 |
| Bracket philosophy display (existing `bracket` field) | frontend-eng | Phase 2 (Hero) |
| Validate `python scripts/validate_deck_json.py` still passes after any data-layer changes | founding-eng | Each phase |
| Archidekt sync continues to work (publishes from same `deck.json`) | founding-eng | Verify Phase 6 |
| YouTube + Commander Spellbook MCP servers — no changes needed | n/a | n/a |

---

## Risks

1. **Source-data drift (12 vs 8 decks)** — must resolve before Phase 2 or normalization will fail silently for missing decks. **Mitigation**: founding-eng audits in Phase 0.
2. **AGENTS.md "no build step" rule conflicts with Vite** — needs explicit board approval to retire the rule.
3. **Hand-loaded JSX in prototype hides any Babel-only behavior** — once compiled with Vite/SWC, behavior should be identical, but transpilation differences (esp. JSX runtime) may surface bugs.
4. **Scryfall throttling under TS-strict mode** — port carefully; the 80ms throttle + dedupe is load-bearing.
5. **localStorage migration** — existing `grimoire-prefs` and `grimoire-owned-cards` keys must keep working post-cutover, or users lose state.
6. **Memory churn** — most repo memory describes the current vanilla-JS app (variable names, CSS classes). Will be obsoleted by this project. Plan for a memory cleanup pass during Phase 6.

---

## Out of scope for v1

- Constellation Map (cut in prototype, stay cut)
- AI-driven swap recommendations (prototype is user-driven)
- Multi-card swap (1-for-1 only)
- Live Scryfall search in swap analyzer (cache-only, matches prototype)
- Side-by-side card comparison (different view)
- SSR / static prefetch for Scryfall
- Service worker

---

## Effort estimate

Sum of phases: **~25–35 focused workdays** for frontend-eng, **~6–10 days** for design-system-eng, **~5–8 days** for founding-eng. Wall-clock with parallelization: **~4–7 weeks**. (Prototype's own SCOPE.md self-estimated 21–30h for just the 4 ported surfaces; we're adding the full Deck Guide port + framework migration + URL state + cutover.)

---

## Open questions — resolutions

| # | Question | Resolution |
|---|---|---|
| 1 | Stack | Vite + React + TS (locked) |
| 2 | Migration | `web/` alongside, swap when ready (locked) |
| 3 | Team | Hire `frontend-eng`, refactor `design-eng`, merge `interactive-eng` (locked) |
| 4 | Rollout | Big-bang (locked) |
| 5 | AGENTS.md "no build step" rule | Implicitly retired by stack decision; updated 2026-05-05 |
| 6 | TS yes/no | TS (locked via #1) |
| 7 | URL state | **Defaulting to YES** (recommended in rev1; no veto received). Wire `?deck=...&view=...` during the rewrite. |
| 8 | Source-data reconciliation | **Resolved 2026-05-05 (DEC-150)**: drop `source-data/` as snapshot, do not reconcile. Production `data/commanders/{id}/*.json` canonical. Loader contract documented in [`design_handoff_grimoire/RECONCILIATION.md`](design_handoff_grimoire/RECONCILIATION.md). Audit also corrected stale "12 decks" → actual 9. |
| 9 | Cutover cleanliness | **Defaulting to: move legacy to `legacy/` for one release**, then delete in a follow-up. |
| 10 | Old-app freeze policy | **Defaulting to: deck-data updates allowed (both consume same JSON), freeze edits to `index.html`/`app.js`/`styles.css`.** |

If any default (#7–#10) is wrong, raise on the issue and I'll adjust before the affected phase starts.

---

## Status

- **Plan**: approved (rev2)
- **Team changes**: in progress (this run)
- **Child issues**: pending creation (this run)
- **Phase 0 start**: pending `frontend-eng` hire confirmation
