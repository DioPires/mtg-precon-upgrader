# DEC-516 — Phase 4 (Computed near-miss + polish) progress log

Contract: `DEC-476 Laço / Combo Lab build plan (v2)` (rev `21d448a4`, Phase-4 row) +
`Laco Prd`, both on DEC-476. **FINAL phase** of the plan. Entry gate (full KB
coverage, needs_llm 0) passed; board accepted (confirmation `f51480d3`, 2026-08-16).

Branch: `dec-516-phase4-combo-lab` off `origin/main` (`627788d`). Push, do NOT merge —
merge follows review approval (reviewer = Design System Engineer, matrix P4).

## Architecture (mirrors Phases 0/2/3)

- **Computed near-miss runs CLIENT-SIDE** over the committed full-coverage KB feature
  index (`data/combo-kb/feature-index.json`, 31,830 cards — the deployed KB
  projection). No backend, no browser verifier, no runtime upstream call. Per-hole
  cost linear in the pool (NM-4); measured ~58 ms (NF-4 budget).
  - **Tier C** (both modes): dangling half-edge cover using the same collapsed
    feature model + `compat` relation as `synergyMatch.ts` — a completion forms the
    exact coupling the Tier-C engine would then show.
  - **Tier B** (fleet only): deficit cover over the Phase-3 verifier's PRECOMPUTED
    engine deficit vectors (`tier-b-loops.json`). Consumes precomputed deficits only —
    the deferred paste-mode Tier-B verifier TS mirror is NOT touched. Paste-mode
    Tier-B completion is deferred with it and disclosed in the UI.
- **Price data** = new committed derivative `data/spellbook/price-index.json`
  (`scripts/build_price_index.py`, Scryfall bulk oracle-cards → EUR/USD). Local
  generation, deploys via the Vercel data copy; `web/src/data/prices.ts` loads it
  in-memory (localStorage bypass), never a runtime price API.
- **Deck-URL** (`web/src/lib/deckUrl.ts`): pure Moxfield/Archidekt URL parser +
  response mappers + a thin client fetch that degrades to a paste-fallback message
  when the host blocks CORS (both currently do — see deviations).
- No STORAGE_PREFIX bump: the persisted deck-bundle envelope is unchanged (price +
  feature indexes bypass the localStorage cache).

## Slices (see manifest.json)

| Prompt | Slice | Requirements | Status |
|---|---|---|---|
| P4.1 | Price index derivative | DR-5, NM-5 | done |
| P4.2 | Near-miss completion engine | NM-1..7, NF-4 | done |
| P4.3 | Deck-URL input | IN-2, IN-4 | done |
| P4.4 | Export/share polish | RT-4 | done |
| P4.5 | UI + filters + latency | NM-5, IN-2, NF-4, OQ-1 | done |
| P4.6 | Lifecycle + validate + handoff | — | done |

## Gate evidence

- `cd web && npm run build` — green (tsc -b + vite build).
- `cd web && npm run test` — 284/284 (26 files); new: `nearMissComplete.test.ts`
  (17), `prices.test.ts` (4), `deckUrl.test.ts` (10), export additions.
- `npx playwright test tests/combo-lab.spec.ts --project=chromium` — 9/9 (real
  browser: completion panel, filters, paste Tier-B deferral, deck-URL degradation,
  Markdown tier-label survival).
- Price index regenerated locally: 32,157 keys, eur 32,115 / usd 32,102.

## Deviations / judgment calls (flagged to CEO on the issue)

1. **IN-2 CORS wall.** Static/backendless (locked DEC-149); both hosts gate
   cross-origin browser fetch (Archidekt pins ACAO to localhost:3000; Moxfield 403s).
   Shipped: best-effort direct fetch + actionable paste-fallback degradation. A
   runtime CORS proxy would lift the wall but adds a third-party query-path dependency
   + terms exposure (RSK-4) — surfaced as a board decision, not adopted unilaterally.
2. **Tier-B closer map (NM-2 soundness).** Only per-iteration amplifiers/reducers
   (`trigger_doubler`, `cost_reduction`) close a per-iteration mana leak; one-shot
   `mana_add` is excluded (it can't change the per-iteration net). Conservative, in
   the provenance-gate spirit (withhold rather than inflate). Card-evaluation-adjacent
   → CEO to confirm.
3. **Paste-mode Tier-B completion deferred** with the pending paste-mode verifier
   mirror (board decision on DEC-476). Disclosed in-UI and in exports.

## Pre-existing (not introduced by this phase)

`npm run lint` reports 2 errors in files this phase did not touch
(`web/src/data/normalize.ts:153` `_q` unused; `web/tests/dec184-visual-qa.spec.ts:84`
`any`) — both present on `origin/main`. All Phase-4 files lint clean.

## P4.7 — Paste-mode Tier-B verifier mirror (board INCLUDE, DEC-516 relay)

Board reversed the paste-mode Tier-B deferral (INCLUDE, DEC-476 `851b18d5`); CEO
relayed on DEC-516. Shipped:

- `scripts/build_tier_b_index.py` → committed `data/combo-kb/tier-b-index.json`
  (13,950 records: 9,899 seeds + 4,051 Spellbook bystanders; 14,843 name keys;
  5.42 MB, gzips to ~1 MB). Loop-relevant raw KB projection; provenance-carrying
  items + precomputed `tier_b_capped` + `untaps_other`. Pure function of the corpus.
- `web/src/data/tierBIndex.ts` — loader (in-memory, localStorage-bypass, shared
  corpus-version buster).
- `web/src/lib/comboVerify.ts` — full TS mirror of `combo_verifier_lib.py` +
  `build_deck` driver. Runs client-side; NF-1 holds (no query-path generation).
- `web/src/lib/comboVerify.test.ts` — **byte-parity vs every fleet deck's committed
  `tier-b-loops.json`** + per-template unit tests over real KB cards (27 tests).
- ComboLab paste flow: runs `verifyDeck`, renders the Tier-B verified-loops section,
  and feeds computed engine deficits to `analyzeCompletions` (paste Tier-B
  completion no longer deferred). Deferral disclosures updated in UI + exports.

### Gate evidence (P4.7)

- `uv run python scripts/build_tier_b_index.py` — byte-stable (function of corpus).
- `cd web && npm run typecheck` — clean.
- `cd web && npm run test` — 311/311 (was 284; +27 `comboVerify.test.ts` incl. full
  fleet parity across all 21 decks).
- `cd web && npm run build` — green (JS 383.63 kB / 113.79 gz).
- `npx playwright test tests/combo-lab.spec.ts --project=chromium` — 9/9 (real
  browser; the paste-mode Tier-B test surfaces a known loop from a pasted decklist).
- NF-4 latency: `verifyDeck` over an 88-card deck = p50 0.36 ms / max 2.44 ms (Node);
  the one-time 5.42 MB index fetch dominates, not the verification.

Design note (soundness): the tier-b-index stores FULL loop-relevant records for
Spellbook bystanders (not name-only stubs) because the prerequisite math reads a
bystander's activated costs + guards (e.g. Voltaic Construct's `pay 2` + `zone_exile`
in the Basalt + Karn + Voltaic Construct engine). Byte-parity would break otherwise.

Judgment-call #3 above (paste-mode Tier-B deferred) is now RESOLVED by the board's
INCLUDE decision and this slice; the deferral text in the UI/exports is replaced by
an "index unavailable" fallback (fires only if the derivative fails to load).
