# DEC-150 source-data reconciliation

Recorded: 2026-05-05. Discovery task per DEC-149 Phase 0.

## Audit results

Plan + HANDOFF.md state "12 decks". Actual count is **9**. Numbers in DEC-149-plan.md and HANDOFF.md are stale.

### Production (`data/commanders/`, canonical) — 9 decks

| Deck ID | deck.json | simulation.json | metrics.json | candidates.json |
|---|---|---|---|---|
| creeping-corruption | yes | yes | yes | yes |
| dark-dominion | yes | yes | yes | yes |
| eternal-agony | yes | yes | yes | yes |
| eternal-harvest | yes | yes | yes | yes |
| genesis-protocol | yes | yes | yes | yes |
| mutant-multiplication | yes | yes | yes | yes |
| the-white-forge | yes | yes | yes | yes |
| titan-convergence | yes | yes | yes | yes |
| verdant-tide | yes | yes | yes | yes |

### Handoff snapshot (`design_handoff_grimoire/source-data/commanders/`) — 8 decks

| Deck ID | deck.json | simulation.json | metrics.json | candidates.json |
|---|---|---|---|---|
| dark-dominion | — | — | yes | yes |
| eternal-agony | — | — | yes | yes |
| eternal-harvest | — | — | yes | yes |
| genesis-protocol | — | — | yes | yes |
| mutant-multiplication | — | — | yes | yes |
| the-white-forge | — | — | yes | yes |
| titan-convergence | yes | yes | yes | yes |
| verdant-tide | — | — | yes | yes |

### Diff

- **Missing from snapshot**: `creeping-corruption` (entirely absent).
- **Partial in snapshot**: 7 of 8 snapshot decks ship only `candidates.json` + `metrics.json`. Only `titan-convergence` carries the full set. `recommendations.json` referenced in HANDOFF.md does not exist anywhere — neither in production nor snapshot.
- All snapshot data is also inlined into `design_handoff_grimoire/prototype/gv1-real-decks.js` for the prototype's hand-loader.

## Decision: drop `source-data/` as snapshot. No changes to production.

Rationale:
- Snapshot is incomplete (no deck.json for 7 of 8 decks; entirely missing creeping-corruption); copying would just reduce drift, not parity.
- `gv1-real-decks.js` already inlines the data the prototype needs. The snapshot has zero independent consumers.
- Phase 2 loader will fetch from production paths directly (see contract below). After cutover, the snapshot becomes load-bearing dead weight.
- Per board default (DEC-150 acceptance): production `deck.json` is canonical.

Action: leave `source-data/` in place as-is for the duration of the prototype's life, **do not invest in reconciling it**. Post-cutover, delete `design_handoff_grimoire/source-data/` and `design_handoff_grimoire/prototype/gv1-real-decks.js`.

No file changes in this heartbeat — the discovery task explicitly forbids production data changes, and the decision is "leave snapshot frozen".

## Loader contract for Phase 2 (frontend-eng)

Production deck data lives at predictable, static paths under the existing site root.

### Index
- `GET /data/index.json` → `{ commanders: [{ id, name, commander, colors, theme, bracket, lastUpdatedSet }, ...] }`

### Per-deck (one deck id per directory)
- `GET /data/commanders/{id}/deck.json` — required. Full deck per AGENTS.md schema.
- `GET /data/commanders/{id}/simulation.json` — required for Battlefield / performance surface.
- `GET /data/commanders/{id}/metrics.json` — required for Apothecary surface.
- `GET /data/commanders/{id}/candidates.json` — required for discovery surface (top-200 scored cards).

### Cross-deck
- `GET /data/game-changers.json` — official MTG Game Changers list (51 cards).

### Notes
- All files are static JSON, no auth, no server. Fetchable from the same origin as `index.html`.
- `deck.json` shape is the same as documented in [`AGENTS.md`](../AGENTS.md) "Commander Deck Data Structure". Not the prototype's normalized `DECK_FULL`; the new app's data layer must port the prototype's `gv1-data.js` normalization step.
- `recommendations.json` mentioned in HANDOFF.md is **not real**. Anything the prototype labelled "recommendations" is sourced from `deck.json` `highlights[]` / `synergies[]` / `categories[]` (see Grimoire naming, post-rename: `highlights`/`categories`).
- The `web/` Vite app should fetch these via `fetch()` + Suspense (per DEC-149 plan). Cache responses in-memory; no service worker needed.

## Follow-up

- Drop reconciliation note into DEC-149 plan §8 (Open questions table) so the row resolves.
- Frontend-eng can write the loader against the four endpoints above.
- Post-cutover cleanup: delete `design_handoff_grimoire/source-data/` and `gv1-real-decks.js`.
