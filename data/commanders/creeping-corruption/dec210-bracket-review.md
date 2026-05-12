# DEC-210 — Creeping Corruption Bracket Review

**Date**: 2026-05-12
**Question**: Does the deck win consistently on T5/T6 (true B4), or is it labeled B4 only because the `gameChangers` count puts it over the B3 ceiling?

## TL;DR

**Board's intuition is correct, and the data is also wrong.** Two independent findings:

1. **Speed**: simulation median lethal turn = **T8**. Lethal-by-T6 is **21.9%**; lethal-by-T7 is **47.1%**. Per the project's own B4 Reality Check (`data/bracket-philosophy.md`), <50% at T7 classifies a deck as **"B3-B4 borderline — the combo plan exists but isn't reliable; deck plays as a value pile."** This is B3 speed, not B4 speed.
2. **`gameChangers: 5` is wrong**. Only **3** cards in the decklist match the official Game-Changers list: Cyclonic Rift, Rhystic Study, Teferi's Protection. The strategy text claims Force of Will / Fierce Guardianship / Deadly Rollick are in the deck — they are not in the 99. With 3 GCs the deck is *already inside the B3 ceiling*; the B4 label isn't even forced by the rule.

Net: this deck is mis-labeled. The "B4 floor by GC count" reasoning does not apply. The label should change regardless of which strategic option below is chosen.

## Evidence (`simulation.json`, 10,000 goldfish games)

| Turn | Commander cast | Threat down | Meaningful board | **Lethal proxy** |
|------|----------------|-------------|------------------|------------------|
| T3   | 25.8%          | 54.7%       | 37.6%            | 0.0%             |
| T4   | 56.0%          | 77.3%       | 67.0%            | 0.1%             |
| T5   | 69.4%          | 86.2%       | 79.2%            | **4.3%**         |
| T6   | 78.9%          | 91.7%       | 87.4%            | **21.9%**        |
| T7   | 84.7%          | 94.7%       | 91.9%            | 47.1%            |
| T8   | 88.9%          | 96.7%       | 94.9%            | 68.5%            |
| T10  | 94.2%          | 98.8%       | 98.2%            | 90.0%            |

**Median lethal turn = T8.** B4 target is T5–T7. Soft-B4 (50% at T7) is barely missed; true-B4 (50% at T6) is far below.

> Caveat — same as DEC-208: `lethalProxy` is a combat-damage proxy (≥40 pressure) and under-counts infect kills via Triumph of the Hordes. Even granting that, draw-Triumph-by-T6 is ≈ P(seen) × P(have-board+mana) ≈ 35% × 65% ≈ 23%. Adding that to the 22% combat lethal proxy gets you to ~40% T6 — still short of the 50% B4 threshold.

### Why the deck is slow

| Lever | Current | Comment |
|---|---|---|
| Tutors | **0 / 4** target | Sylvan Library is selection, not a tutor. Triumph of the Hordes, Tekuthal, Vorinclex, Necrogen Rotpriest — none are findable on demand. |
| Fast mana | **Sol Ring only** | No Grim Monolith, no Mana Vault, no Chrome Mox, no Lotus Petal, no Ancient Tomb. CZ731 lists these as "B4 minimum" for non-mono decks. |
| Free interaction | **0 / 4** target | Strategy text claims FoW + Fierce Guardianship + Deadly Rollick. None are in the 99. Real interaction = Counterspell, Swan Song, Spell Pierce, Heroic Intervention — all pay-mana. |
| Counterspells | 3 / 6 target (`gaps[].counterspell.score = 50`) | Already flagged as a gap by the metrics computer. |
| Ramp | 8 / 10 (`ramp.score = 80`) | Acceptable. |
| Threat density | 18 threats, median deploy T4 | Healthy for a fair deck, slow for a B4. |

The win plan is **incremental proliferate**: Atraxa ticks +1 poison/opp/end-step (or +2 with Tekuthal). Triumph of the Hordes is the one-shot finisher. Without tutors, you draw Triumph on its natural curve (≈ 35% by T6) — not a B4 reliability floor.

## Game-changer audit

| Declared (`deck.json`) | Actual matches on `data/game-changers.json` |
|---|---|
| `gameChangers: 5` | **3** — Cyclonic Rift, Rhystic Study, Teferi's Protection |

The strategy text says: *"The interaction suite runs the full B4 package — Force of Will, Fierce Guardianship, Deadly Rollick, Cyclonic Rift, Toxic Deluge."* — but none of FoW / Fierce Guardianship / Deadly Rollick are in the 99-card decklist. Strategy text was written aspirationally and never reconciled with `decklist[]`. Should be corrected to `gameChangers: 3` regardless of strategic option chosen.

With 3 GCs, the deck is below the B4-forcing threshold (>3). Labeling it B4 is currently a *user choice*, not a *rule consequence*.

## Three strategic options for the board

### Option A — Reclassify to B3 (honest label) — recommended default

**Premise**: accept the deck as built. It plays like a strong proliferate / infect midrange that wins T7–T9. That's B3.

**Required changes**:
- Flip `bracket` from `"4"` → `"3"` in `data/index.json` and `data/commanders/creeping-corruption/deck.json`.
- Correct `gameChangers: 5` → `3`.
- Update `guideContent.strategyOverview` to remove the false claim that FoW / Fierce Guardianship / Deadly Rollick are in the deck. Replace with the actual interaction list.
- Optional polish: 0–3 small swaps to tighten redundancy (e.g., a second proliferate sweeper, replacing Wurmquake or Phyresis Outbreak if cuts surface).

**Spend**: $0–20.
**Outcome**: deck labeled correctly; pod expectations match reality. Atraxa infect at B3 is a popular, well-respected build — there is no shame in this label.

### Option B — Upgrade speed to a true B4 (DEC-205-style retune)

**Premise**: keep the B4 label and earn it. Apply the DEC-205 Dark Dominion playbook — add fast mana + tutors + a tutor-able win condition.

**Concrete adds (~11 cards, costs ballpark)**:

| Card | Role | Cost | Why |
|---|---|---|---|
| Grim Monolith | Fast mana | ~$80 | T2 access to T3+ plays; double-proc with untap effects |
| Chrome Mox | Fast mana | ~$80 | T1 acceleration; on official GC list (+1 GC) |
| Lotus Petal | Fast mana | ~$3 | T1 one-shot acceleration |
| Vampiric Tutor | Tutor | ~$25 | Universal — finds Triumph, Vorinclex, Tekuthal |
| Demonic Tutor | Tutor | ~$30 | Universal — same; on GC list (+1 GC) |
| Worldly Tutor | Tutor | ~$25 | Creature finder — fetches Tekuthal or a finisher |
| Eladamri's Call | Tutor | ~$10 | Instant-speed creature tutor; flashy on Atraxa's trigger window |
| Necropotence | Card advantage | ~$30 | Premier B4 draw engine; on GC list (+1 GC) |
| Force of Will | Free counter | ~$80 | Strategy text already claims it; on GC list (+1 GC) |
| Fierce Guardianship | Free counter | ~$30 | Strategy text already claims it; on GC list (+1 GC) |
| Deadly Rollick | Free removal | ~$25 | Strategy text already claims it; commander already in play often |

**Required cuts (~11 slots)**: candidates from the soft end of the curve — Wurmquake, Phyresis Outbreak (redundant with Toxic Deluge), one of the proliferate-only 1-drops (Thrummingbird or Grateful Apparition), one redundant infect lord (Hand of the Praetors vs Necrogen Rotpriest), the second sword (Sword of Truth and Justice if Skullclamp draws better), Norn's Choirmaster, Expansion Algorithm if not pulling weight.

**GC count after**: 3 → ~8 (well into B4 by the rule).
**Spend**: ~$400–450 (high — these are chase rares).
**Outcome**: expected median lethal shifts ~T8 → T6 (estimated; needs sim re-run after swap). Brings the deck inside the DEC-205 case-study band of comboLethal/lethalProxy ≥ 50% at T6.
**Risk**: changes the deck's feel from "fair infect midrange" to "tutor the kill." The board has historically pushed back on this style for some decks; check whether this commander gets that treatment.

### Option C — Add a tutored Triumph-of-the-Hordes finisher line (mid-budget hybrid)

**Premise**: don't go all the way to cEDH-tier card prices, but specifically address the "draw the finisher" reliability problem. Keep the deck's infect identity intact.

**Concrete adds (~6 cards)**:

| Card | Role | Cost | Why |
|---|---|---|---|
| Vampiric Tutor | Tutor | ~$25 | Finds Triumph or Tekuthal |
| Eladamri's Call | Tutor (creature) | ~$10 | Instant-speed Tekuthal / Vorinclex / lord |
| Worldly Tutor | Tutor (creature) | ~$25 | Same role, redundant for consistency |
| Survival of the Fittest | Tutor (creature) | ~$40 | Repeatable creature dig + GY enabler |
| Chrome Mox | Fast mana | ~$80 | T1 acceleration; adds 1 GC (Force/Fierce optional separately) |
| Grim Monolith | Fast mana | ~$80 | T2 explosive turns |

**Required cuts (~6 slots)**: Wurmquake, Phyresis Outbreak, Thrummingbird or Grateful Apparition, Expansion Algorithm, Norn's Choirmaster, Hand of the Praetors or one redundant lord.

**GC count after**: 3 → ~4 (just over the B4 floor — actually forces B4 by rule).
**Spend**: ~$260.
**Outcome**: expected median lethal shifts ~T8 → T6.5 (estimated). Closer to soft-B4 than true-B4, but earns the label honestly.
**Risk**: middle path — pays the tutor money without fully committing to free-spell defense.

## Recommendation

**Option A** is the lowest-friction path and produces an honest label. The deck is well-built for what it is; the only sin is the `gameChangers: 5` data error and the aspirational strategy text. A B3 Atraxa infect deck with this much proliferate density and 11 pieces of interaction is a strong, respected build — not a downgrade in identity.

**Option B** is the right answer if the board values the B4 label as a deliberate power statement (and is willing to spend ~$400+ to back it up). DEC-205 shows the playbook works.

**Option C** is the compromise: meaningful speed gain at half the budget, but lands as "soft B4" not "true B4."

If the board wants to keep the B4 label without spending — that's a fair user preference, but the `gameChangers` field still needs correcting (5 → 3) and the strategy text still needs fixing (remove false free-spell claims), because both are factual errors independent of the bracket decision.

## Files touched

**Option A**:
- `data/index.json` — `bracket: "4"` → `"3"`
- `data/commanders/creeping-corruption/deck.json` — `bracket`, `gameChangers: 5 → 3`, `guideContent.strategyOverview` cleanup
- Optional re-run: `python scripts/refresh_card_pool.py --deck creeping-corruption`

**Option B / C**:
- All of Option A
- `data/commanders/creeping-corruption/deck.json` — `decklist[]` swaps (6 or 11 cards), `sources[]` entries for each add
- `data/commanders/creeping-corruption/metrics.json` — re-run via `scripts/compute_deck_metrics.py`
- `data/commanders/creeping-corruption/simulation.json` — re-run via `scripts/mana_simulation_creeping_corruption.py` (or generic runner)
- `python scripts/validate_deck_json.py --deck creeping-corruption`
- `python scripts/refresh_card_pool.py --deck creeping-corruption`

## Open decisions for board

1. Bracket label: keep at 4, or reclassify to 3?
2. If keeping at 4: Option B (full retune, ~$400) or Option C (tutored hybrid, ~$260)?
3. Strategy text + `gameChangers` field correction is required regardless — confirm.
