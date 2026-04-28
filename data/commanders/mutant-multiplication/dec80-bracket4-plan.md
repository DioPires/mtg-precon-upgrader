# DEC-80 — Mutant Multiplication B3 → B4 Upgrade Plan

**Revision**: r5 (executed)
**Date**: 2026-04-28
**Color identity**: Bant (W/U/G).
**Budget envelope**: ≤ ~$700 total deck cost.
**Status**: APPLIED — Option B with Tendershoot Dryad substituted for Mondrak (Mondrak was already in deck).

## Final swap (r5)

**Cuts (4)**: Ninja Pizza, Ghostly Prison, Rampant Growth, Hangarback Walker
**Adds (4)**: Pathbreaker Ibex (must-buy ~$8), Triumph of the Hordes (must-buy ~$30), Vivien Reid (owned), Tendershoot Dryad (owned)
**Spend**: ~$38
**Bracket**: index.json flipped 3 → 4
**Cost field**: $350-500 → $420-560

## User direction (cumulative)

1. **Strategy**: tokens + combat damage.
2. **Banned must-buys**: Ancient Tomb, Chrome Mox, Mana Vault, The One Ring, Force of Will.
3. **Owned cross-deck allocation**: only count owned cards as available if not used by another built deck (excluding `planar-decree` + `genesis-protocol`).
4. **r3 corrections**: 4 cuts reversed (Mona Lisa, Endless Foot Assault, Damning Verdict, Inspiring Call).
5. **r4 corrections**: 4 more cuts reversed (Idol of Oblivion, Wave Goodbye, Mikey & Leo, Rapid Hybridization). Total 8 misread cards across r2 → r4 audit. Deck is much tighter than initial reading suggested.

## Context

The deck's existing card quality is high and tightly tuned to the tokens+counters axis. Most cards I initially flagged as cuttable turned out to be earning their slot through interaction with Leonardo's "+1/+1 counter on each creature when a token enters" trigger or Donatello's "+1 Mutagen per token-creation event" trigger. The audit reduced confident cuts from 12 → 3-4.

## Phase 1 — Metadata fix

| File | Change |
|------|--------|
| `data/index.json` | `"bracket": "3"` → `"bracket": "4"` for `mutant-multiplication` |

## Phase 2 — Card swaps (3 or 4, awaiting board choice)

### Confident cuts (3)

| Cut | Cost | Reason |
|-----|------|--------|
| **Ninja Pizza** | {2}{G} | Foods gain mana ability + 1 Food/turn EOT2. Off-axis (no other Food sac payoffs); 3-CMC for slow generation. |
| **Ghostly Prison** | {2}{W} | Pillowfort tax — CZ731 calls B3-tier; deck wants to attack, not deflect. |
| **Rampant Growth** | {1}{G} | Strictly worse than Nature's Lore (already in deck) — fetches tapped vs untapped, same CMC. |

### Borderline cut (1)

| Cut | Cost | Reason |
|-----|------|--------|
| **Hangarback Walker** | {X}{X} | Slow X-cost grow + Thopter death payoff. Synergistic but tempo-negative. Optional 4th cut. |

### Adds — priority order

| # | Card | Cost | Source | Approx. $ | Role |
|---|------|------|--------|-----------|------|
| 1 | **Mondrak, Glory Dominus** | {2}{W}{W} | must-buy | ~$25 | 5th token doubler. Exponential with the 4 doublers already in deck. |
| 2 | **Pathbreaker Ibex** | {4}{G}{G} | must-buy | ~$8 | Every-attack global Overrun + trample. Top finisher. |
| 3 | **Triumph of the Hordes** | {2}{G}{G} | must-buy | ~$30 | Alpha-strike infect kill (2nd copy; 1st allocated to creeping-corruption). |
| 4 | **Vivien Reid** | {3}{G}{G} | owned | $0 | Creature/land tutor + targeted removal + +2/+2 emblem. |

### Pending board choice

- **Option A (3 swaps)**: cut Ninja Pizza / Ghostly Prison / Rampant Growth, add Mondrak / Pathbreaker Ibex / Vivien Reid. Spend ~$33.
- **Option B (4 swaps, recommended)**: cut Ninja Pizza / Ghostly Prison / Rampant Growth / Hangarback Walker, add Mondrak / Pathbreaker Ibex / Triumph of the Hordes / Vivien Reid. Spend ~$63.
- **Option C**: board specifies different mix.

## All cards PRESERVED (originally cut in r2)

After audit, the following 8 cards remain in the decklist:

- **Mona Lisa, Ever Adaptable** — passive Mutagen engine off all players' creature spells; scales with Donatello.
- **Endless Foot Assault** — 1 Ninja per opponent per attack per copy; Squad doubles output.
- **Damning Verdict** — asymmetric wipe given Leonardo + Cathars' Crusade keep your team countered.
- **Inspiring Call** — instant-speed mass card-draw + indestructible.
- **Idol of Oblivion** — 2-mana artifact, draw a card any turn you create a token (every turn here).
- **Wave Goodbye** — 4-mana asymmetric bounce wipe (only hits creatures without counters).
- **Mikey & Leo, Chaos & Order** — 2-mana 2/2 with one-per-turn draw on counter placement.
- **Rapid Hybridization** — 1-mana hard removal (cheapest in the kill suite).

## Phase 3 — Data hygiene

- `decklist`: apply chosen swap count (3 or 4). Final 98.
- `highlights`: add reason entries for the chosen adds.
- `categories`: route new cards into existing buckets.
- `sources`: each add gets `scryfall` + `ai-inferred` source entries.
- `cost`: bump to "$390-540" (option A) or "$420-560" (option B).
- `bracket` unchanged at "4" in deck.json; only `index.json` flips.
- `gameChangers`: re-count post-swap (no GC cards touched, should remain 7).

## Acceptance

- `data/index.json` bracket = "4" for `mutant-multiplication`
- `decklist` has 98 entries; chosen 3-or-4 swaps applied
- All 8 preserved cards remain in decklist
- No card from banned list added
- `cost`, `highlights`, `categories`, `sources` updated; deck.json schema valid

## Out of scope

- Restoring Rhystic Study + Cyclonic Rift: over-allocated to other built decks.
- Tutors, Force of Will, additional fast-mana — banned/skipped per direction.

## Cost delta

| Option | Adds spend | Net |
|--------|-----------|-----|
| A (3 swaps) | Mondrak + Pathbreaker Ibex + Vivien Reid (owned) | ~$33 |
| B (4 swaps, rec.) | Mondrak + Pathbreaker Ibex + Triumph + Vivien Reid (owned) | ~$63 |

Either way, deck cost stays well inside the $700 envelope.
