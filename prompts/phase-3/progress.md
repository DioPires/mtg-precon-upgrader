# DEC-501 — Phase 3 (Tier B verifier) progress log

Contract: `DEC-476 Laço / Combo Lab build plan (v2)` + `Laco Prd`, both on DEC-476.
Phase-3 row + the recorded (k, finite-zone bound) clarification + decision 6b
(provenance gate ENFORCED).

Branch: `dec-501-phase3-verifier` off `origin/main` (fdb62a9 — DEC-491 Phase 2 +
DEC-498 v111 cache bump merged). Worktree: `../mtg-precon-upgrader-wt-dec501`.

## Architecture (locked, mirrors Phases 0/2)
- **Python engine** `scripts/combo_verifier_lib.py` — single source of truth for the
  closure model (PRD 6.1-6.5 + (k, bound)), the closure templates + `CLOSE_SAFE`
  soundness backstop, the provenance gate (`combo_kb_lib.tier_b_view`), deficit
  vectors, ordering-optimised prerequisites + command-zone guards, RT-1 result
  types, DB-6 provenance chain, and the RK-2-completing ranking signals.
- **Fleet mode** = precomputed `data/commanders/{id}/tier-b-loops.json`
  (`build_tier_b_candidates.py`): feature-gated candidate enumeration, superset
  suppression, KB-gap abstentions dropped, EDHREC crowd-prior order-only (no scalar
  shipped). Wired into the deck bundle as `tierBLoops`; STORAGE_PREFIX v111→v112.
- **Regression + calibration** `scripts/qe1_regression.py` — QE-1b B-layer recall
  with QE-2 miss categorisation; QE-1c / RK-3 top-decile; RK-3/RK-4 calibration →
  `data/combo-kb/verifier-ranking.json`.
- **Web** — fleet-mode Tier-B section in `ComboLab.tsx` with EI-2 model-conditional
  labelling; corroborated loops render at Tier A (DB-7); provenance-gate caps
  disclosed. Tier labels survive the plain-text export (EI-4).

## Soundness posture (QE-4 is the whole game)
A false Tier-B positive is the worst failure class. Three mechanisms enforce it:
1. `CLOSE_SAFE` — only `untap_mana` / `blink_untap_mana` may assert closure (their
   argument is fully derivable from mana magnitudes + priced costs). Everything else
   detects structure and abstains.
2. Provenance gate — Tier-B consumes only deterministic / human-reviewed items; a
   would-be loop that needs an LLM item is capped at Tier C with a reason.
3. Corroboration vs novel — a curated loop stays Tier A (can't inflate); a novel
   loop clears a stricter gate. DC-6: novel is rare (0 novel across the fleet).

Regression guard: `test_basalt_plus_thran_is_NOT_infinite` — two mana rocks must
never verify as infinite mana (only a *triggered per-tap amplifier* counts).

## Measured results
- Fleet: 1 corroborated (Basalt Monolith + Forsaken Monument, titan-convergence),
  0 novel false positives across 21 decks, sound near-misses only.
- QE-1b: 1/2000 curated combos verified by the B-layer. Recall is
  **KB-extraction-bound** (dominant misses: sac-recursion pricing, out-of-template
  structures, un-extracted life-loop drain) — every miss a QE-2 diagnostic feeding
  the ontology/extractor (DEC-488). Soundness is the invariant; recall grows only as
  the KB deepens (QE-3), never by loosening the model.
- QE-1c / RK-3: 1/1 evaluable decks pass (thin — bounded by the single corroborated
  combo). Calibration landed; the Phase-2 provisional-ranking caveat is downgraded
  to a "recall-limited evaluable set" note, not fully retired.

## Tests
- `tests/test_combo_verifier.py` (14) — closure, the Basalt+Thran QE-4 guard,
  provenance-gate capping, sac abstention, ordering-optimised prereqs, guard set,
  provenance chain, determinism, mana parsing.
- `web/src/__tests__/lib/tierBReport.test.ts` (6) — tier labels + model-conditional
  qualifier survive export (EI-2/EI-4), corroboration renders as Tier A (DB-7),
  gate caps disclosed.
- Full suites green: Python 142 pass / 1 skip; web 250 pass; web typecheck + build
  clean; lint clean on all touched files (2 pre-existing errors on main untouched).

## Deviations
- Built directly then mirrored into `prompts/phase-3/` as the lifecycle artifact —
  the accepted Phase-0 precedent (the `/prompt-creator`→`/phase-execute` skills were
  not driven interactively). `/phase-validate` run at the gate.
- Paste-mode Tier-B (a client-side verifier mirror + parity fixture) is the one
  slice deferred to a follow-up: the sound verified class is narrow and fleet mode
  ships all 21 decks, so this adds a NEW capability rather than regressing Phase-2's
  paste-mode Tier-A/C (no dark period). Tracked in the handoff.
