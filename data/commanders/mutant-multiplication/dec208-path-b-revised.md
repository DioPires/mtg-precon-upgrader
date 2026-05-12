# DEC-208 — Path B (Revised, Budget-Conscious)

**Date**: 2026-05-12
**Status**: awaiting board confirmation
**Board direction**: "more towards path B but I can't afford the Survival of the Fittest or the Grim Monolith"

## Substitution strategy

| Original (dropped) | Replacement | Why it works |
|--------------------|-------------|--------------|
| Survival of the Fittest (~$40) | **Worldly Tutor** + **Eladamri's Call** + **Chord of Calling** (3 tutors total) | Two instant-speed creature tutors + one X-cost convoke-into-play. Together they recover most of Survival's job (find the finisher) without the discard engine — and Chord skips the cast step entirely. |
| Grim Monolith (~$80) | **Basalt Monolith** (OWNED) + **Carpet of Flowers** (~$3) | Basalt Monolith taps for 3 (net 0 after untap, but lets us deploy a 6-mana threat on T4 with a 3-land board). Carpet is 1-mana ramp scaling with blue opponents — common in pods. |

## Adds (7 cards, ~$78 spend)

| # | Card | Cost | Source | $ | Role | Job |
|---|------|------|--------|---|------|-----|
| 1 | **Worldly Tutor** | `{G}` | must-buy | ~$30 | tutor | Instant-speed creature tutor — finds Triumph of the Hordes (wait, that's a sorcery; finds Pathbreaker Ibex / Avenger of Zendikar / Mondrak / Cyberdrive Awakener / Herald of Secret Streams). |
| 2 | **Mystical Tutor** | `{U}` | must-buy | ~$25 | tutor | Instant tutor for instants/sorceries — finds **Triumph of the Hordes**, Cyclonic Rift, Second Harvest. |
| 3 | **Eladamri's Call** | `{G}{W}` | must-buy | ~$10 | tutor | Instant creature tutor straight to hand (no top-deck delay). Bant-color. |
| 4 | **Chord of Calling** | `{X}{G}{G}{G}` | must-buy | ~$10 | tutor + threat | X-mana convoke tutor — **puts creature directly onto battlefield**. With token board, convoke means X=6 costs ~3 real mana. Pathbreaker Ibex hits the battlefield ready to swing. |
| 5 | **Carpet of Flowers** | `{G}` | must-buy | ~$3 | ramp | 1-mana enchantment, +X mana each main phase where X = Islands target opponent controls. ~65% of pods have blue. |
| 6 | **Basalt Monolith** | `{3}` | OWNED (1 free copy) | $0 | fast-mana floor | `{T}: Add {C}{C}{C}`. Doesn't untap but enables a 6-mana commander/finisher one turn earlier. |
| 7 | **Cultivate** | `{2}{G}` | OWNED (3 free copies) | $0 | ramp | Basics → 1 land in play + 1 in hand. Fixes mana and accelerates. |

**Total: ~$78 spend.** (Worldly $30 + Mystical $25 + Eladamri's Call $10 + Chord $10 + Carpet $3 = $78.)

## Cuts (7 cards)

| # | Card | CMC | Why cut |
|---|------|-----|---------|
| 1 | Mona Lisa, Ever Adaptable | 4 | 4-CMC passive Mutagen engine triggering on opponents' creature spells. Synergistic but slow — competes with our T4 commander/threat deploy. |
| 2 | Endless Foot Assault | 3 | Ninja-token enchantment; tokens enter tapped and attacking — they trade poorly without an anthem. Off our +1/+1-counter axis. |
| 3 | Wave Goodbye | 4 | 4-CMC sorcery-speed asymmetric bounce. Cyclonic Rift does the same job at instant speed and we already run it. |
| 4 | Damning Verdict | 5 | 5-CMC asymmetric wipe. Too slow for the T5–T6 curve; we are the aggressor — we don't need a second wipe behind Cyclonic Rift. |
| 5 | Mutagen Man, Living Ooze | X+2 | X-cost spells are tempo-negative. At X=2 (4-CMC), produces 2 Mutagens — worse than dropping a 4-CMC engine card. |
| 6 | Herd Baloth | 5 | 5-CMC 4/4 that makes one 4/4 token per +1/+1 placement on itself. Slow trigger off our broader counter-spreading; payoff doesn't outpace the cost. |
| 7 | Monologue Tax | 3 | Passive Treasure off opponents' second spell each turn. Marginal acceleration; we'd rather a real ramp spell. |

**Average CMC of cuts: 3.86. Average CMC of adds: ~2.0.** Curve shifts ~2 mana faster — exactly what we need.

## Expected impact

Current sim (10k goldfish games):
- median lethal turn = **8**
- lethal-by-T6 = **14.6%**
- 0/4 tutors → roles[].tutor.score = 0

Projected after swap (estimate, needs re-sim to confirm):
- median lethal turn = **6** (Worldly+Mystical+Eladamri+Chord = 4 tutors at 1–3 CMC; Triumph/Pathbreaker findable on T3–T4)
- lethal-by-T6 = ~**45%** (Triumph + token army → infect kill 1 player; Pathbreaker → multi-player race)
- roles[].tutor.score → ~95 (4 tutors vs target 4)
- roles[].ramp.score → ~75 (Basalt + Cultivate + Carpet add 3 ramp permanents to existing 5.5)

## Files to edit (post-approval)

- `data/commanders/mutant-multiplication/deck.json`
  - `decklist`: 7 cuts + 7 adds (net 0; stays at 98 entries)
  - `gameChangers`: 7 → 4 (correction)
  - `cost`: bump from `$420-560` to `$500-640`
  - `adds`, `synergies`, `sources`: entries for new tutors + ramp
  - `addCategories`: route into existing buckets
- `data/commanders/mutant-multiplication/metrics.json`: re-run via `compute_deck_metrics.py`
- `data/commanders/mutant-multiplication/simulation.json`: re-run via `mana_simulation_mutant_multiplication.py`

## Open question for board

**Carpet of Flowers** depends on pod composition. If your typical pod has ≥1 blue opponent, it's S-tier ramp. If your pod is consistently mono-non-blue (rare in EDH), it's a 1-mana dead card. Reply if you want to swap it for **Sylvan Tutor** (~$15, 1-CMC sorcery green creature tutor) — slower than the instants but a tutor either way.

## Acceptance criteria

- 7 cuts + 7 adds applied to `decklist`
- `gameChangers: 4` (correction)
- `cost` updated
- `sources` entries for all 7 adds (each gets `scryfall` + `ai-inferred`)
- `python scripts/validate_deck_json.py --deck mutant-multiplication` passes
- Sim re-run; new `lethalProxy.medianTurn` reported in close-out comment
