# DEC-208 — Mutant Multiplication Bracket Review

**Date**: 2026-05-12
**Question**: Does the deck win consistently on T5/T6 (true B4), or is it labeled B4 only because of the >3 game-changer floor?

## TL;DR

**Board's intuition is correct.** Simulation shows median lethal turn = 8. Lethal-by-T6 is 14.6%; lethal-by-T7 is 40.2%. That is B3 speed, not B4 speed. Three structural reasons: zero tutors, anemic ramp (5.5/10), and the deck's only 2-card infinite (Broodscale + Rosie Cotton) assembles only 1.4% by T6.

A second finding surfaced during the review: **`gameChangers: 7` is wrong** — only 4 cards match the official Game-Changers list (Aura Shards, Cyclonic Rift, Fierce Guardianship, Smothering Tithe). Still ≥4 so the B4 floor applies, but the field should be corrected.

## Evidence (from `simulation.json`, 10,000 goldfish games)

| Turn | Commander cast | Threat down | Meaningful board | **Lethal proxy** |
|------|----------------|-------------|------------------|------------------|
| T3   | 84.3%          | 88.3%       | 81.0%            | 0.0%             |
| T4   | 89.7%          | 94.2%       | 91.6%            | 0.1%             |
| T5   | 92.7%          | 96.6%       | 95.9%            | **2.1%**         |
| T6   | 95.0%          | 97.9%       | 97.8%            | **14.6%**        |
| T7   | 96.3%          | 98.9%       | 98.8%            | 40.2%            |
| T8   | 97.2%          | 99.2%       | 99.2%            | 64.7%            |
| T10  | 98.4%          | 99.8%       | 99.8%            | 90.5%            |

**Median lethal turn = 8.** B4 target is T5–T7.

> Caveat: `lethalProxy` is a combat-damage proxy (≥40 cumulative combat pressure). It under-counts infect kills via Triumph of the Hordes (10 poison = lethal). But even granting that, draw-Triumph-by-T6 is roughly P(seen) × P(have mana+board) ≈ 35% × 60% ≈ 21%. Still well short of consistent B4.

### Why the deck is slow

1. **0 / 4 tutors** (`gaps[].tutor.score = 0`). Cathars' Crusade, Triumph, Pathbreaker Ibex, Doubling Season — all top-end finishers — get drawn naturally or not at all.
2. **5.5 / 10 ramp** (`gaps[].ramp.score = 55`). No fast-mana rocks (banned by board direction). Commander cast median T3 — fine, but no acceleration past curve.
3. **Combo backbone is decorative.** Broodscale + Rosie Cotton median assembly: never within 10 turns (1.4% by T6). Counts toward B4 floor by rule, but does not contribute to win speed in practice.
4. **2 / 6 counterspells**. Limited ability to protect the combo turn even when it does land.

## Game-changer audit

| Declared (`deck.json`) | Actual matches on official list |
|------------------------|-------------------------------|
| 7                      | 4 (Aura Shards, Cyclonic Rift, Fierce Guardianship, Smothering Tithe) |

The `7` figure pre-dates the GC list refresh and was never re-validated. Should be corrected to `4` regardless of which strategic option below is chosen.

## Three strategic options for the board

### Option A — Reclassify to B3 (honest label) — recommended default

**Premise**: accept the deck as it is. It plays like a strong tokens / +1/+1 midrange that wins T7–T9. That's B3.

**Required changes**:
- Cut 1 game changer to land at ≤3 (e.g., **Aura Shards** — least synergistic; or **Smothering Tithe** if budget reclaim wanted).
- Cut the 2-card infinite by removing **Basking Broodscale** (the deck doesn't lean on it; assembly rate proves that).
- Flip `bracket` from "4" → "3" in `index.json` and `deck.json`.
- Correct `gameChangers` field to `3`.
- 2 free slots → ramp upgrades (e.g., Cultivate, Three Visits) or token doublers (Annointed Procession is already in; Doubling Season optional).

**Spend**: $0–30. Most cuts are owned.
**Outcome**: deck labeled correctly; pod expectations match reality.

### Option B — Upgrade speed to a true B4

**Premise**: keep the B4 label and earn it. Requires lifting two existing constraints:

- **Tutors** (currently banned per DEC-80 user direction). Bant tutors available: Worldly Tutor (~$30), Mystical Tutor (~$25), Enlightened Tutor (~$25), Survival of the Fittest (~$40), Eladamri's Call (~$10), Chord of Calling (~$10).
- **Fast mana** (currently capped). Legal options post-Mana-Crypt-ban: Grim Monolith (~$80), Mana Vault (~$45), Jeweled Lotus has been banned — only Vault/Monolith remain at the top tier.

**Required cuts**: ~6–8 low-impact cards (Mona Lisa, Ninja-token side pieces, redundant token doublers).

**Spend**: ~$200–300 net (high — these are chase rares).
**Outcome**: median lethal turn shifts from T8 → T6 (estimated; needs sim re-run after swap).
**Risk**: changes the deck's feel from "go-wide combat" to "tutor up the win." Board has historically pushed back on this style.

### Option C — Commit to a combo backbone

**Premise**: Bant has limited true 2-card infinites, but a few are viable:

- **Devoted Druid + Vizier of Remedies** (infinite mana → Walking Ballista / Finale of Devastation). Strong, on-color, ~$30 for the pair.
- **Heliod, Sun-Crowned + Walking Ballista** (infinite damage). White-only, ~$30.
- Keep **Broodscale + Rosie** as backup; add **Survival of the Fittest** as the assembly engine.

**Required cuts**: ~5 cards (some token-doubler redundancy + Mona Lisa + Hangarback Walker if not already cut).
**Adds**: ~5 combo pieces + 1–2 tutors to assemble reliably.

**Spend**: ~$80–150.
**Outcome**: median lethal turn ~T5–T6 if combo lands; still loses to interaction. Identity shifts from tokens-and-counters to combo-with-tokens-as-redundancy.

## Recommendation

**Option A** is the lowest-friction path and most aligned with board's revealed preferences (no tutors, no fast mana, deck plays "as a deck not as a combo"). It also surfaces the underlying truth: this is a beautifully-tuned B3 deck that got mislabeled B4 because of a one-line `gameChangers: 7` value that overstated the true count.

If the board wants to keep the B4 label specifically because the deck contains Cyclonic Rift / Smothering Tithe / Fierce Guardianship and the partner Donatello commander is mechanically novel — that's a fair user preference, but pod expectations should be reset: "this is a B3.5 deck wearing a B4 jersey because of card pool, not speed."

## Files touched if Option A approved

- `data/index.json` — `bracket: "4"` → `"3"`
- `data/commanders/mutant-multiplication/deck.json` — `bracket`, `gameChangers`, `decklist` (1 GC cut + Broodscale cut + 2 replacements)
- `data/commanders/mutant-multiplication/metrics.json` — re-run via `compute_deck_metrics.py`
- `data/commanders/mutant-multiplication/simulation.json` — re-run via `mana_simulation_mutant_multiplication.py`
