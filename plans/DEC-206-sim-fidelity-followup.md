# DEC-206 Sim-Fidelity Follow-Up Plan

**Author:** CEO (claude_local)
**Date:** 2026-05-12
**Status:** Reviewed by Plan agent — revised (rev 2)
**Parent issue:** DEC-206 Eternal Agony — bracket review (closed; this is a non-blocking follow-up)

## Problem Statement

Previous heartbeat's honest disclosure on DEC-206 closure:

> the goldfish sim's `comboLethal` heuristic doesn't fully model the new tutors (missing `tutor_targets` metadata for Vampiric / Grim Tutor / Entomb / Diabolic Intent). Flagged a recommended (non-blocking) follow-up to backfill that metadata so future Bracket 4 decks get honest combo-velocity sim numbers.

This plan addresses that follow-up. **Investigation reveals the problem is broader than "missing metadata"** — there are two real schema bugs plus a separate cause for Eternal Agony's `comboLethal=0`.

## Investigation Findings

### F1 — Eternal Agony's `comboLethal` is 0 for a structural reason, not a tutor reason
`scripts/export_simulation_results.py:760-782` (`extract_combo_lines`) requires `winConditions[].kind == "combo"` and `winConditions[].pieces`. Eternal Agony's 5 `winConditions` entries all use `cards` (no `kind`, no `pieces`), so `combo_lines = []` and the sim never tries to fire `comboLethal`.

| deck | wincons | wincons with `kind: "combo"` | tutors | tutors with explicit metadata |
|---|---|---|---|---|
| dark-dominion | 9 | 6 | 8 | 3 |
| eternal-agony | 5 | 0 | 5 | 0 |
| eternal-harvest | 10 | 0 | 6 | 0 |
| (all others) | — | 0 | varies | 0 |

**Only `dark-dominion` has combo-line modeling wired up. Eternal Agony's deck.json schema doesn't expose a combo line to the sim.**

### F2 — V / Grim / Demonic Tutor work correctly via defaults
`extract_tutor_metadata` (line 794-813) defaults `targets=["any"]`, `mv_cap=None`, `free_cast_via_bargain=False`. For Vampiric Tutor / Grim Tutor / Demonic Tutor (all unconditional "search library for any card, put into hand" effects), these defaults are **functionally correct**. Adding explicit `tutor_targets: ["any"]` is legibility paint, not a bug fix.

### F3 — Entomb has a real schema bug (graveyard vs. hand)
Entomb puts a **creature card** from library into **graveyard**. Two issues with the current default:

1. `targets=["any"]` lets the sim "tutor" via Entomb for any card type — wrong. Should be creature-only.
2. Path-2 logic in `combo_ready_this_turn` (line 1065-1081) chains `tutor cost + piece cost` assuming the piece lands in hand and is castable. After Entomb the piece is in the graveyard — must be reanimated, not cast. The correct cost chain is `Entomb cost + reanimation cost`, not `Entomb cost + piece cost`.

### F4 — Diabolic Intent has an unmodeled extra cost (sacrifice a creature)
Diabolic Intent (`1B`, sorcery) requires sacrificing a creature as part of the cost. The sim treats it as a free-cost `1B` universal tutor, ignoring the creature-on-board prerequisite. In token / wide-board strategies this is fine; in non-creature builds it's a meaningful cost.

### F5 — Eternal Agony isn't a 2-card-on-stack combo deck
The 5 `winConditions` describe kill plans, not hard combos:
- Heartless Hidetsugu lethal activation (4 mana, summoning sickness, needs to attack/activate + needs a damage doubler in play)
- Peer into the Abyss kill (7 mana sorcery + Sheoldred/Underworld Dreams on board)
- Repercussion + Blasphemous Act (board wipe with redirect)
- Damage Multiplier Stack (multiple multipliers in play)
- Bolas's Citadel chain (top-of-library reveals)

None of these are "have both pieces in hand on the same turn → win". They're "board-state kill plans". So `comboLethal` (which models "all pieces castable from current hand+battlefield this turn") **should be near 0** for this deck. The metric is honest as-is once Track A bugs are fixed; Eternal Agony just isn't a combo deck.

## Plan — Three Tracks

### Track A — Schema bug fixes in the sim (affects all decks)

These are real correctness fixes, not paint. Backward-compatible defaults.

**A1. New field: `tutor_mode: "to_hand" | "to_graveyard"`** (default `"to_hand"`)
- Add to `extract_tutor_metadata` parsing in `scripts/export_simulation_results.py`.
- Modify Path-2 logic in `combo_ready_this_turn`: if `tutor_mode == "to_graveyard"`:
  - Only valid for permanent pieces (creature/planeswalker) that can be reanimated.
  - **Pop a reanim spell from the per-line `reanim_pool`** (same pool Path 3 uses) — if the pool is empty, this tutor cannot resolve the piece, skip and try next tutor.
  - Cost chain becomes `tutor cost + reanim cost` (piece comes from graveyard for free).
  - Per-line state: `tutor_pool` and `reanim_pool` are already per-line copies (lines 1031-1032); the new `to_graveyard` path consumes from both, preventing double-spend.
- **Note on sim graveyard state**: the sim has no graveyard-set tracking. `to_graveyard` is a routing hint, not a graveyard model. Path 3 (existing reanimation) already assumes any reanim spell can target any permanent piece "in graveyard," which is a known approximation. The new field reuses the same approximation; it does not model milled/discarded pieces from prior turns.

**A2. New field: `tutor_extra_cost: "sacrifice-creature" | null`** (default `null`)
- Add to `extract_tutor_metadata` parsing.
- Modify cast-feasibility check: when casting a `sacrifice-creature` tutor, require at least one **non-commander** creature-typed permanent on battlefield (because the goldfish sim always plays commander as early as possible; counting commander as a free sac target would neutralize the cost). If only the commander is in play as a creature, the tutor is not castable.
- Approximation: walk `permanents`, look for any with `"creature" in profiles[name].typeLine.lower()` AND `name != commander_name`.

**A3. ~~Validator update~~ — DROPPED.** `scripts/validate_deck_json.py` is a card-reference checker, not a schema validator (no enum logic exists today). Building a real schema validator is out of scope for this heartbeat. New fields are simply ignored by the validator; the sim parser is the authoritative consumer.

### Track B — Backfill explicit tutor metadata

For each deck, audit every `primary_role: "tutor" | secondary_role: "tutor"` entry and add the explicit metadata. Order chosen to maximize tractability and verifiability.

**B1. Universal library tutors → explicit `tutor_targets: ["any"]`** (legibility, no behavior change)
- Demonic Tutor, Vampiric Tutor, Grim Tutor, Mystical Tutor (no — restricted), Worldly Tutor (no — restricted)
- Note: `tutor_targets: ["any"]` only applies to cards that genuinely tutor for any card type. Restricted tutors get type lists.

**B2. Entomb-class graveyard tutors → `tutor_targets: ["creature"]` + `tutor_mode: "to_graveyard"`**
- Entomb (creature only, to graveyard)
- Buried Alive (creature, x3 to graveyard — model as creature/to_graveyard for simplicity; quantity-3 not modeled in sim)

**B3. Diabolic Intent → `tutor_extra_cost: "sacrifice-creature"`** (targets stay `["any"]`)

**B4. Per-deck affected tutors (audit list)**
| deck | tutor cards to backfill |
|---|---|
| eternal-agony | Demonic Tutor, Vampiric Tutor, Diabolic Intent, Grim Tutor, Entomb |
| dark-dominion | (already has metadata for 3; audit the remaining 5) |
| eternal-harvest | (6 tutors — audit and tag) |
| genesis-protocol, the-white-forge, titan-convergence, verdant-tide | audit and tag tutors |
| creeping-corruption, mutant-multiplication | no tutors — skip |

**Scope decision**: B-track applies metadata to every deck with tutors. Schema fields are no-ops for decks without `kind: "combo"` wincons, but explicit metadata is durable and surfaces in any future combo-line additions.

### Track C — Honest documentation

**C1.** Update `data/bracket-philosophy.md`:
- Clarify that `comboLethal` measures hard-combo velocity (pieces castable this turn).
- Non-combo B4 drain / damage-multiplier decks (like Eternal Agony) score low on `comboLethal` by design.
- Reference `pressure`, `cumulativeDamage`, and `lethalProxy` as the appropriate metrics for those decks.

**C2.** **REVISED per peer review**: Tag `Heartless Hidetsugu + Solphim, Mayhem Dominus` as `kind: "combo"` in Eternal Agony's `winConditions`. Reasoning:
- Both cards are in the decklist (verified).
- Hidetsugu's `{T}: each player loses half life` × Solphim's damage doubler = 40 → 20 → doubled to 40 = lethal at starting 40 life.
- The cost chain is Hidetsugu (4 mana, R) + Solphim (5 mana, 2RR) = 9 mana total. Goldfish-castable.
- **Known approximation**: if both cast same turn, Hidetsugu has summoning sickness and can't tap until next turn. The sim doesn't model activated-ability sickness, so it will report `comboLethal=1` one turn early in that scenario. Acceptable approximation — matches the sim's existing treatment of ETB-triggered combos like Thassa's Oracle.
- Do NOT tag the other Eternal Agony wincons: they require multi-piece board state (Wound Reflection + Citadel + revealed-card draws), opponent-life-dependent kills (Peer + Sheoldred with per-draw triggers), or attack-trigger sequencing that the sim cannot model honestly.

**C3.** No `bracket-philosophy.md` doc changes in this heartbeat — park for follow-up. The sim-fidelity story is now told via the `kind: "combo"` tag itself, not prose.

## Out of Scope

- Modeling Peer into the Abyss kill (sorcery + creature on board + per-draw triggers) as a combo line — would require a new sim primitive (draw-per-turn damage simulation).
- Modeling Heartless Hidetsugu attack-trigger kills — requires opponent life tracking, attack legality, removal-spell exposure.
- Modeling Bolas's Citadel chain payments via life — requires life-pay tracking.
- Adjusting Tainted Pact / Demonic Consultation modeling — already handled in dark-dominion; no change needed.
- Frontend (`web/`) changes — `comboLethal` is consumed by metrics + display; values change but contract doesn't.

## Validation Strategy

1. **Unit-level**: re-run `python scripts/validate_deck_json.py --deck {id}` for each touched deck. Must stay clean.
2. **Sim re-run**: re-run goldfish for dark-dominion, eternal-agony, **eternal-harvest** (per reviewer S7 — eternal-harvest has Entomb + Buried Alive + Diabolic Intent, all touched by Track B even though it has no `kind: "combo"` lines yet; metadata changes are no-ops there but re-running confirms it).
   - **Dark Dominion**: has Diabolic Intent (verified). Expect a modest decrease in `comboLethal` once A2's non-commander sac requirement enforces.
   - **Eternal Agony**: with new `kind: "combo"` tag on Hidetsugu+Solphim, expect non-zero `comboLethal` on turns where both pieces are castable. Sanity-check the curve.
   - **Eternal Harvest**: no `kind: "combo"` wincons → `comboLethal` should remain 0. Metadata changes are no-ops; this is a regression check.
3. **Metrics recompute**: `python scripts/compute_deck_metrics.py --deck {id}` for the three touched decks. Verify global_health changes are within tolerance.
4. **Frontend cache**: bump `web/src/data/loader.ts` prefix `v5 → v6` because `simulation.json` values change (even though schema doesn't). Without bumping, browsers cache stale sim values for 24h.

## Rollout / Commit Plan

Single commit (the changes are tightly coupled):
- `feat(DEC-206-followup): sim-fidelity for tutor schema (to_graveyard, sacrifice-creature, explicit targets)`
- Files: `scripts/export_simulation_results.py`, `scripts/validate_deck_json.py`, per-deck `deck.json` files for tutor backfill, regenerated `simulation.json` + `metrics.json` for affected decks, `data/bracket-philosophy.md` C1 note, `web/src/data/loader.ts` cache bump.

## Self-Review Checklist (Soundness)

- [ ] **Backward compatibility**: Decks without new fields keep their current sim behavior. Verified by defaults in `extract_tutor_metadata`.
- [ ] **Dark Dominion regression risk**: Diabolic Intent sac cost will hit DD's sim. Confirm DD's combo-turn distribution shifts but stays sensible.
- [ ] **Commander as sac target**: Diabolic Intent in early game with commander not yet cast — sim correctly blocks the cast. Verified by `is_commander_in_play` check.
- [ ] **Entomb without reanim in hand**: sim correctly skips that path. Verified by reanim-pool check before applying.
- [ ] **No new Scryfall calls**: pure schema/sim change, no card lookup needed (tutor classifications are deterministic from card text already known).
- [ ] **No frontend type changes**: `simulation.json` keys stay the same, `comboLethal` semantics tighten but the field remains.
- [ ] **Validator covers new fields**: a deck.json with bad enum values fails validation cleanly.

## Open Questions for Self-Review

1. Should `Buried Alive` model the "x3 to graveyard" effect? — **Decision: no**, model as single creature/to_graveyard. The sim's combo modeling assumes single-piece tutoring; tri-fetch is over-modeling.
2. Should Beseech the Mirror's `tutor_free_cast_via_bargain` interact with `to_graveyard` mode? — **Decision: no**, Beseech puts the card directly into hand (mv ≤ 4); doesn't apply to graveyard tutors.
3. Does Diabolic Intent's sac requirement need to consider the commander differently from regular creatures? — **Decision: no special case**, commander is sacrificable. A player will sac commander only in extremis; sim approximates "any creature in play" as available.

---

End of plan. Submit to Plan agent for peer review before implementation.
