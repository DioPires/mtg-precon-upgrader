# DEC-491 — Phase 2 (Tier C synergy engine) progress log

Contract: `DEC-476 Laço / Combo Lab build plan (v2)` (rev 21d448a4) + `Laco Prd`,
both on DEC-476. Phase-2 row + decisions 4/5/6.

Branch: `dec-491-combo-tier-c-phase2` off `origin/main` (fe475a0). Entry gate
verified: `git merge-base --is-ancestor 96ceaf4 origin/main` → YES. KB on main is
full-coverage (31,830 cards, deterministic + Wave-1 LLM; `meta.json`
`llm_classified_count`=191).

## Architecture (locked)
Mirrors the Phase-0 split so both surfaces agree and EDHREC stays out of the
browser:
- **Python engine** `scripts/combo_synergy_lib.py` — single source of truth:
  provides/wants graph over the ontology `pairs_with` relation, pair/triple/
  4-cycle enumeration, magnitude + deck-fit ranking, coarse RK-5 bands.
- **Fleet mode** = precomputed `data/commanders/{id}/synergy-candidates.json`
  (engine + EDHREC crowd prior baked into ranking; raw rates stay gitignored in
  `priv_data/edhrec/`).
- **Paste mode** = `web/src/lib/synergyMatch.ts`, a TS mirror of the engine
  (magnitude + deck-fit, NO crowd prior — decision 4), loading a compact
  `data/combo-kb/feature-index.json` (~3 MB) in memory like the matcher index.
- **QE-1a** regression + Python↔TS parity + vitest guard the two surfaces.

## Log
- 2026-08-15 — branch created; contract (plan v2 + PRD) read; EDHREC cache
  extended to all 21 fleet decks (13 new low-volume fetches). Prompt scaffolding
  written (P2.1–P2.7). Feature-index size sanity: ~2.8 MB compact.
- 2026-08-15 — engine + all deliverables complete:
  - `combo_synergy_lib.py` (graph, IDF weighting + `mana_add↔mana_sink` noise
    exclusion, pair/triple/4-cycle enumeration with deep-focus bound, reduced-
    signal ranking, coarse bands). Runtime: <1.2 s deep / 4 ms pairs-only per
    deck (NF-3). Quality validated on Meren (aristocrats/recursion) + Norin
    (ETB/tokens).
  - `feature-index.json` (3.27 MB, all 31,830 cards) + `synergy-config.json`
    (shared config, 5.5 KB) via `build_synergy_index.py`.
  - 21 fleet `synergy-candidates.json` via `build_synergy_candidates.py` (EDHREC
    prior baked into ranking; raw rates NOT shipped; 0 uncovered fleet-wide).
  - Web: `synergy.ts`, `synergyMatch.ts` (TS mirror, byte-parity), ComboLab
    Tier-C section + deep-scan, `STORAGE_PREFIX` v109→v110.
  - QE-1a `qe1a_synergy_regression.py`: recall 25% (38% among featureful pairs) —
    tracked metric; misses are QE-2 ontology-gap diagnostics.
  - Tests: `tests/test_combo_synergy.py` (12) + `synergyMatch.test.ts` (10,
    parity) green.
  - Fixed during integration: DFC back-face aliasing (armory false-uncovered),
    4-key edge sort + fully-sorted cycle enumeration for cross-language
    determinism.
