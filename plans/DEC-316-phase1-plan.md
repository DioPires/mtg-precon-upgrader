# DEC-316 Phase 1 — Tagging sweep plan

Status: **REV 2 — convention accepted (`mixed`), Q2/Q3 answered with deeper scan results**. Per local-board comment 2026-05-29: each deck plan must be explicitly accepted before any change lands.

## Board decisions logged

- **Convention `"mixed"`**: accepted. Proceeding with option A (new enum value + add to both resilience target dicts + doc reconciliation).
- **Q2 (eternal-harvest retag depth)**: my recommendation below, reasoning included.
- **Q3 (deeper oracle scan)**: completed against all 5 ±8 decks (not just verdant-tide — the original narrow pattern set produced the "structural gap" verdict on three decks, and that deserved the same rigor). Five candidate cards Scryfall-verified. Updated dispositions below.

## Diagnostic correction up front

The issue body's "TBD likely cause" guesses were wrong on the ±8 cohort. Actual penalty breakdown (`confidence_inputs.penalties`, read from current `metrics.json`):

| Deck | margin | firing penalty term | actual cause |
|---|---:|---|---|
| silverquill-the-disputant | ±11 | `wincon_style_unset` (+6) | `wincon_style: null`; 5 `winConditions[].kind` lines split combat(2) / burst / combo / value |
| creeping-corruption | ±8 | `resilience_signal_low` (+3) | `recursion` component scores 0 (3 targeted, 0 in deck) |
| eternal-harvest | ±8 | `resilience_signal_low` (+3) | `protection` component scores 0 (4 targeted, 0 in deck) |
| mutant-multiplication | ±8 | `resilience_signal_low` (+3) | `recursion` component scores 0 (4 targeted, 0 in deck) |
| pyre-and-panic | ±8 | `resilience_signal_low` (+3) | `protection` component scores 0 (2 targeted, 0 in deck) |
| verdant-tide | ±8 | `resilience_signal_low` (+3) | `recursion` component scores 0 (2 targeted, 0 in deck) |

`role_unset_cards`, `archetypes_unset`, `simulation_missing`, `candidates_stale` all = 0/false for every deck in scope. **The issue's framing as a tagging sweep only applies cleanly to silverquill.** The other five hit `resilience_signal_low` because one resilience component scores zero, and Phase 1 scope says "no `decklist[]` changes". So for those five, the only Phase-1-legal lever is **retagging existing cards** that already perform the missing role but lack the right `primary_role`/`secondary_role`. If no such cards exist in the deck, the penalty is structural and we document the why-line in `sources` per the acceptance criterion, not paper over it.

## Cross-cutting decision (blocks silverquill)

**Convention for `wincon_style` on multi-kind decks.** Issue recommended `"mixed"`. Three options reconsidered against the existing code:

- **A. New enum `"mixed"`.** `RESILIENCE_RECURSION_TARGETS`, `RESILIENCE_WINCON_LINE_FLOOR`, `_WIN_TURN_LP_STYLES`, `_WIN_TURN_COMBO_STYLES` all fall through to `None`/`max` defaults on unknown values, so `"mixed"` would silently inherit the `None` row (recursion target 2/3/4 by bracket, line floor 1, win-turn source = `max`). Pro: explicit signal that the deck has no dominant plan. Con: invisible to the closed set unless we also add the value to the dicts and update `docs/role-taxonomy.md`.
- **B. Pick highest-frequency `winConditions[].kind`.** For silverquill that's `combat` (2/5). Con: silverquill is a Witherbloom-style aristocrats deck on a +1/+1-counter-ish commander; calling it `combat` misrepresents the gameplan. Forcing this convention on future decks will keep producing dishonest tags.
- **C. Array-valued `wincon_style`.** Truthful. Invasive: every `wincon_style`-keyed dict and `_is_multi_kind_wincon` would have to learn array semantics. Out of scope for a "tagging sweep".

**Recommendation: A — `"mixed"` — with three mechanical follow-ups in the same change so it is not just a magic string:**

1. Add `"mixed"` to `RESILIENCE_RECURSION_TARGETS` and `RESILIENCE_WINCON_LINE_FLOOR` mapping to the same numbers as the `None` row (no behavior change, just makes the value first-class).
2. `_win_turn_source` falls through to `max` for `"mixed"` already; no code change there, but add a one-line comment so future readers understand the intent.
3. Document the new value in `docs/role-taxonomy.md` §`wincon_style` and `docs/deck-metrics.md` §resilience targets. While there, **reconcile the documented closed set** — the role-taxonomy doc currently lists only `{combat, combo, drain, mill, alt}` but the code recognizes `value-incremental`, `drain-x`, `discrete-threats`, `burst`. The doc has been drifting since DEC-308. Add the missing values to the taxonomy table.

**Open question for the board**: do you want `"mixed"` added now, or do you prefer option B for silverquill specifically (tag it `combat` because 2/5 lines win that way) and defer the convention decision to a separate ticket? My read: A is the cleaner long-term answer, and silverquill alone is reason enough — but it does mean Phase 1 grows by one small doc + code edit. Awaiting explicit go.

---

## Deck 1 — silverquill-the-disputant  (next up; needs convention decision above first)

**Diagnosis** (from `confidence_inputs.penalties`): `wincon_style_unset: true` → +6. Everything else: 0. Margin clamps at default 5 + 6 = 11.

**Proposed change** (after convention sign-off):

1. `data/commanders/silverquill-the-disputant/deck.json`: set root-level `"wincon_style": "mixed"` (assuming option A is accepted).
2. `scripts/compute_deck_metrics.py`: add `"mixed"` row to `RESILIENCE_RECURSION_TARGETS` and `RESILIENCE_WINCON_LINE_FLOOR` mirroring the `None` defaults. One-line comment near `_win_turn_source` noting `"mixed"` intentionally falls through to `max`.
3. `docs/role-taxonomy.md`: add `mixed` to the §`wincon_style` table with the doc string *"Deck wins through multiple kinds with no dominant plan (use only when no single kind ≥ 60% of `winConditions[]` lines)."* Same pass: backfill missing entries `value-incremental`, `drain-x`, `discrete-threats`, `burst` so the doc matches code.
4. `docs/deck-metrics.md`: one-line note under §resilience that `"mixed"` inherits the default-row targets.
5. Run `python scripts/compute_deck_metrics.py --deck silverquill-the-disputant` to refresh `metrics.json`.
6. Run `python scripts/validate_deck_json.py --deck silverquill-the-disputant`.

**Expected outcome**: margin drops from ±11 to ±5 (wincon_style penalty cleared; no other penalty firing; bonus-floor still ineligible because `role_coverage_score = 100` but `candidates_age_days = 4.8` ≤ 30 so all five floor conditions become true → margin clamps further to ±2).

**Acceptance for this deck**: `confidence_margin ≤ 5` (and ideally ±2 via bonus floor). The issue's stated target was "≤ ±5"; bonus floor is a happy bonus.

**Commit shape**: single `feat(DEC-316): adopt "mixed" wincon_style convention and tag silverquill` covering all five files above. Push.

---

## Deck 2 — creeping-corruption

**Diagnosis**: `resilience_signal_low` (+3). `recursion` component = 0/30 (deck has 0 cards tagged recursion, target is 3 for `value-incremental` @ B3).

**Deep oracle scan**: Wurmquake flagged on `\bflashback\b` and `cast … from … graveyard`. Scryfall-verified: "Flashback {8}{G}{G} (You may cast this card from your graveyard for its flashback cost. Then exile it.)"

**Disposition: STRUCTURAL GAP (not a retag candidate).** Flashback is a self-recurring spell cost — the card casts *itself* from the yard, it does not return *other* cards. The role taxonomy distinguishes recursion (returns other cards from yard) from self-recurring graveyard mechanics (flashback, jump-start, harmonize, retrace, aftermath, embalm, eternalize). Tagging Wurmquake as recursion would conflate the two and is inconsistent with how the existing fleet is tagged. Current `primary: wincon, secondary: payoff` is honest.

**Proposed change**: append a single explanatory `sources[]` entry to `data/commanders/creeping-corruption/deck.json`:

```jsonc
{ "type": "ai-inferred", "name": "DEC-316: resilience_signal_low (recursion=0)",
  "detail": "Phase-1 documented: deep oracle scan found no recursion-tagged candidates (Wurmquake's flashback is self-recurring, not card recursion). Closing this gap requires a Phase-2 card swap." }
```

**Expected outcome**: margin stays at ±8. Documented per the issue's "leave penalties that reflect real data holes with a one-line note in the deck's `sources` array explaining why" clause.

---

## Deck 3 — eternal-harvest

**Diagnosis**: `resilience_signal_low` (+3). `protection` component = 0/25 (target 4 @ B4 `value-incremental`). Three candidates surfaced, all Scryfall-verified.

**Recommendation (Q2 answer)**: flip **primary** role on two cards, **leave the third untouched**.

| card | current → proposed | Scryfall-verified oracle text | reasoning |
|---|---|---|---|
| Lightning Greaves | `primary: payoff` → `primary: protection` | "Equipped creature has haste and shroud. Equip {0}" | The card has exactly one job: grant shroud + haste. There is no second job. The `payoff` tag was a clerical mis-tag (Greaves doesn't pay off anything). Honest primary is `protection`. No secondary. |
| Spore Frog | `primary: payoff` → `primary: protection` | "Sacrifice this creature: Prevent all combat damage that would be dealt this turn." | In a B4 value-incremental graveyard recursion deck, Spore Frog is a recurring fog — its repeated job is preventing combat damage. That IS protection. The `payoff` tag is wrong; Spore Frog has no payoff text. No secondary. |
| Yawgmoth, Thran Physician | **no change** (stays `primary: utility`) | "Protection from Humans. Pay 1 life, sac another creature: Put -1/-1 counter and draw. {B}{B}, Discard: Proliferate." | His three real jobs in eternal-harvest are sac-draw engine, -1/-1 removal, and proliferate. Protection-from-Humans is a defensive freebie but in EDH multiplayer it's load-bearing maybe once per ten games. Tagging a 4-mana sac engine as `protection` just to satisfy the metric would distort the signal and set a precedent that "any card with a protection clause anywhere on it" counts. |

**Reasoning on why-flip-primary-not-add-secondary**: the role taxonomy's purpose is to describe what a card is *for* in the deck. Spore Frog and Lightning Greaves are protection cards full stop — `payoff` was simply a wrong tag. Adding a secondary while keeping a dishonest primary would (a) preserve the bad data, (b) under-credit the protection axis (0.5 vs 1.0 weight), and (c) leave the next reviewer wondering why Greaves is a payoff. The primary flip is the truthful repair.

**Net protection weight gained**: 2.0 (1.0 × Greaves + 1.0 × Spore Frog) against target 4 → component score = 12.5/25 (50% of max — still in `gaps[]` because <70%, which is correct: the deck *is* protection-light, the metric just shouldn't read it as zero).

**Expected margin**: ±8 → ±5. Bonus floor inaccessible (`role_coverage_score` = 79, needs ≥100).

**Validator note**: `_role_count_weighted` uses `primary_role == role` OR `secondary_role == role`; flipping primary does not break the role coverage count for `payoff` because the deck has 3 archetypes (graveyard-reanimator, value-incremental B4) that don't target `payoff` specifically. I will re-run `compute_deck_metrics.py` after edit to confirm no role-coverage regression.

---

## Deck 4 — mutant-multiplication

**Diagnosis**: `resilience_signal_low` (+3). `recursion` component = 0/30 (target 4 @ B4 `value-incremental`).

**Deep oracle scan**: Nature's Rhythm flagged on `cast … from … graveyard`. Scryfall-verified: "Harmonize {X}{G}{G}{G}{G} (You may cast this card from your graveyard for its harmonize cost. … Then exile this spell.)"

**Disposition: STRUCTURAL GAP.** Same reasoning as Wurmquake — harmonize is self-recurring, not recursion. Current `primary: tutor` is honest.

**Proposed change**: same `sources[]` note pattern as creeping-corruption with Nature's Rhythm noted instead of Wurmquake.

**Expected outcome**: margin stays at ±8, documented.

---

## Deck 5 — pyre-and-panic

**Diagnosis**: `resilience_signal_low` (+3). `protection` component = 0/25 (target 2 @ B3 `drain`).

**Deep oracle scan**: two candidates surfaced, both Scryfall-verified.

| card | current → proposed | Scryfall-verified text | reasoning |
|---|---|---|---|
| Purphoros, God of the Forge | **no change** | "Indestructible. As long as your devotion to red is less than five, Purphoros isn't a creature. Whenever another creature you control enters, Purphoros deals 2 damage to each opponent. {2}{R}: +1/+0…" | Indestructibility is incidental — Purphoros's actual job is the ETB damage trigger (the deck's drain wincon). Tagging engine creatures as protection because they're indestructible would re-tag every Theros god and Avacyn-class permanent. That breaks the metric. |
| Cavern of Souls | **no change** | "As this land enters, choose a creature type. {T}: Add {C}. {T}: Add one mana of any color. Spend this mana only to cast a creature spell of the chosen type, and that spell can't be countered." | Verified deck context: Norin the Wary etb-flicker, **not tribal** (8+ distinct creature types in 99 cards — no type density ≥ 3). The "can't be countered" clause requires a chosen creature type at ETB and only fires for spells of that type, so in pyre-and-panic the protection is incidental at best. The `land` tag is correct. |

**Disposition: STRUCTURAL GAP.** No honest retag candidates. Same `sources[]` note pattern as creeping-corruption.

**Expected outcome**: margin stays at ±8, documented.

---

## Deck 6 — verdant-tide

**Diagnosis**: `resilience_signal_low` (+3). `recursion` component = 0/30 (target 2 @ B3 `discrete-threats`).

**Deep oracle scan**: two candidates surfaced, both Scryfall-verified.

| card | current → proposed | Scryfall-verified text | reasoning |
|---|---|---|---|
| Shigeki, Jukai Visionary | `primary: utility` → `primary: utility, secondary: recursion` | Main: tap-bounce-self to fetch a land. **"Channel — {X}{X}{G}{G}, Discard this card: Return X target nonlegendary cards from your graveyard to your hand."** | Channel is genuine recursion — returns *other* cards from yard. But main-line use of Shigeki in verdant-tide is land ramp/utility (his tap-bounce ability), so keep primary `utility` and add `secondary: recursion` to credit the channel mode. |
| Nature's Rhythm | **no change** (stays `primary: tutor`) | "Search your library for a creature card with mana value X or less, put it onto the battlefield, then shuffle. Harmonize {X}{G}{G}{G}{G} (cast from graveyard)." | Same logic as Wurmquake/mutant-multiplication — harmonize is self-recurring, not recursion. The `tutor` tag is honest. |

**Note on scan completeness**: the deep scan widened the pattern set to ~20 recursion phrases including all major graveyard mechanics (flashback/jump-start/embalm/eternalize/escape/dredge/disturb/encore/unearth, plus all "return X from graveyard" variants and reanimator phrasings). It now matches both the resilience metric's intent (card-recursion) and self-recurring spells (excluded by reasoning, not by oversight). I am confident Shigeki is the only honest retag.

**Net recursion weight gained**: 0.5 (Shigeki secondary) against target 2 → component score = 7.5/30 (25% of max — still in `gaps[]` because <70%, correctly: the deck *is* recursion-light, the metric just shouldn't read it as zero).

**Expected outcome**: margin ±8 → ±5. Bonus floor inaccessible (role coverage 91 < 100).

---

## Execution order

1. ✅ Convention resolved (`"mixed"`, accepted by board).
2. ✅ Q2 + Q3 answered (deeper scan complete, recommendations above).
3. **Awaiting**: explicit board approval of this revised plan via `request_confirmation`.
4. Implement silverquill commit: `feat(DEC-316): adopt "mixed" wincon_style convention and tag silverquill` (code + 2 docs + 1 deck.json + metrics regen).
5. Implement eternal-harvest commit: `feat(DEC-316): retag Spore Frog + Lightning Greaves as protection in Eternal Harvest` (deck.json + metrics regen).
6. Implement verdant-tide commit: `feat(DEC-316): tag Shigeki channel recursion in Verdant Tide` (deck.json + metrics regen).
7. Implement creeping-corruption / mutant-multiplication / pyre-and-panic: one bundled commit `feat(DEC-316): document structural resilience gaps on 3 decks` adding the `sources[]` notes.
8. After all six land, sanity check: `python scripts/compute_deck_metrics.py` over all decks; confirm no margin regressions on the other 9.

## Projected margin movement (post-Phase 1)

| Deck | Before | After | Method |
|---|---:|---:|---|
| silverquill-the-disputant | ±11 | **±2** (bonus floor) | wincon_style tag |
| eternal-harvest | ±8 | **±5** | 2 retag (protection) |
| verdant-tide | ±8 | **±5** | 1 retag (recursion) |
| creeping-corruption | ±8 | ±8 (documented) | structural gap noted |
| mutant-multiplication | ±8 | ±8 (documented) | structural gap noted |
| pyre-and-panic | ±8 | ±8 (documented) | structural gap noted |

Issue acceptance: silverquill `confidence_margin ≤ 5` ✅ (will land at ±2 due to bonus floor). Other decks: tagging gaps fixed where they exist; structural gaps documented per the issue's `sources[]` clause. All within Phase-1 scope (no `decklist[]` changes).

## What this plan does NOT do (out of scope, per issue)

- Touch `decklist[]` for any deck.
- Add or remove cards to close structural recursion/protection gaps. Those moves are Phase 2.
- Adjust resilience targets or confidence weights.
- Rewrite `confidence_components` (the field is null on every deck — the code writes `confidence_inputs` instead; the issue body referenced `confidence_components` but the metric uses `confidence_inputs`. Not changing this here; it's a doc nit at most).
