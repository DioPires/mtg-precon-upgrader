# Archetype Recipe Taxonomy — Proposal (Gate 1)

Status: **draft, pending board approval** (DEC-238 Gate 1).

## Method

I inventoried two sources:

1. **`data/discovery-playbook.json`** — 17 archetype entries used today for regex scoring
2. **Active archetype tags on the 11 existing decks** under `data/commanders/`

Then cross-referenced against standard EDH archetype conventions (Command Zone vocabulary, EDHREC archetype tags). The goal is a taxonomy that (a) covers every existing tagged deck without losing fidelity, (b) maps cleanly to recognizable EDH deck archetypes, (c) is small enough to author and maintain.

## Current state

**Per-deck archetype tags (11 decks):**

| Deck | Archetypes |
|---|---|
| creeping-corruption | infect-poison, plus-one-counters |
| dark-dominion | amass-orcs, amass-armies, tokens-go-wide |
| eternal-agony | group-slug |
| eternal-harvest | graveyard-reanimator, aristocrats |
| genesis-protocol | stax-control, artifacts-matter |
| mutant-multiplication | tokens-go-wide, plus-one-counters, artifacts-matter |
| silverquill-the-disputant | aristocrats, graveyard-reanimator, spellslinger |
| the-white-forge | artifacts-matter, etb-flicker |
| titan-convergence | eldrazi-colorless, ramp-big-mana |
| verdant-tide | elf-tribal, ramp-big-mana |
| witherbloom-the-balancer | aristocrats, tokens-go-wide, spellslinger |

**Playbook entries currently unused on any deck:** `voltron`, `lands-matter`

## Proposed recipe taxonomy — 13 archetypes

I overshot the "10-12" target by one. Rationale below; cuts are board-adjudicable.

### Core 10 (high-confidence keepers)

1. **aristocrats** — Sac outlets, death-trigger payoffs, drains, recursion. _Used by 3 decks._
2. **graveyard-reanimator** — Self-mill, reanimation, recursion engines. _Used by 2 decks._
3. **tokens-go-wide** — Token producers + anthems + doublers + amass. **Absorbs** `amass-orcs` and `amass-armies` as sub-recipes (same mechanic, different franchise). _Used by 3 decks (counting amass)._
4. **counters-payoffs** — +1/+1 counters, doublers, proliferate, counter-matters. **Renamed** from `plus-one-counters` to anticipate -1/-1 and other counter axes. _Used by 2 decks._
5. **infect-poison** — Toxic, infect, corrupted, alt-win-via-poison. **Kept separate** from counters: alt-win-con + distinct oracle idioms. _Used by 1 deck._
6. **spellslinger** — Instants/sorceries matter, prowess, magecraft, copy. _Used by 2 decks._
7. **stax-control** — Asymmetric resource denial, taxes, restrictions, pillowfort. _Used by 1 deck._
8. **artifacts-matter** — Artifact density, cost reduction, ETB/recursion engines on artifacts. _Used by 3 decks._
9. **ramp-bigmana** — Fast mana + cheat into oversized threats. **Absorbs** `eldrazi-colorless` as a sub-recipe (Eldrazi is one threat type; ramp is the engine). _Used by 2 decks (counting Eldrazi)._
10. **tribal** — Creature-type-cares, parameterized on tribe. **Absorbs** `elf-tribal` as one instance. _Used by 1 deck (elf)._

### Adjudicable 3 (board to confirm or cut)

11. **group-slug** — Pinger/punisher damage, opponent-action triggers. **Could** be absorbed into `stax-control` (both are opponent-hurt), but oracle idioms are distinct (pinger triggers vs. tax restrictions). _Used by 1 deck (Eternal Agony)._
12. **lands-matter** — Landfall, lands recursion, ETB-tapped synergies. _Unused today._ Worth keeping for future Omnath/Windgrace decks; archetype is canonical in EDH. Risk: low priority since no current deck needs it.
13. **etb-flicker** — ETB-trigger loops + flicker/blink/bounce. _Used by 1 deck (White Forge)._ Could be absorbed into `artifacts-matter` (most flicker is artifact-adjacent) but the idiom is creature-ETB-focused.

### Explicitly deferred

- **voltron** — No current deck uses it. Author when first voltron deck enters our catalog.
- **eldrazi-colorless** — Folded into `ramp-bigmana` as a sub-recipe (colorless threats + devoid + annihilator).
- **amass-orcs**, **amass-armies** — Folded into `tokens-go-wide` as sub-recipes (same mechanic, two franchise variants).
- **elf-tribal** — Folded into `tribal` as the first instance, with tribe as a parameter.

## Coverage check — every existing deck maps cleanly

| Deck | Currently tagged | Maps to (proposed) |
|---|---|---|
| creeping-corruption | infect-poison, plus-one-counters | infect-poison, counters-payoffs |
| dark-dominion | amass-orcs, amass-armies, tokens-go-wide | tokens-go-wide (amass sub-recipes) |
| eternal-agony | group-slug | group-slug |
| eternal-harvest | graveyard-reanimator, aristocrats | graveyard-reanimator, aristocrats |
| genesis-protocol | stax-control, artifacts-matter | stax-control, artifacts-matter |
| mutant-multiplication | tokens-go-wide, plus-one-counters, artifacts-matter | tokens-go-wide, counters-payoffs, artifacts-matter |
| silverquill-the-disputant | aristocrats, graveyard-reanimator, spellslinger | aristocrats, graveyard-reanimator, spellslinger |
| the-white-forge | artifacts-matter, etb-flicker | artifacts-matter, etb-flicker |
| titan-convergence | eldrazi-colorless, ramp-big-mana | ramp-bigmana (eldrazi sub-recipe) |
| verdant-tide | elf-tribal, ramp-big-mana | tribal (elf), ramp-bigmana |
| witherbloom-the-balancer | aristocrats, tokens-go-wide, spellslinger | aristocrats, tokens-go-wide, spellslinger |

No deck loses coverage. Some gain potential coverage via newly accessible sub-recipes (e.g., dark-dominion gains amass sub-recipes plus the broader tokens base).

## What this implies for `discovery-playbook.json`

The regex playbook will need to align — same archetype IDs, same `name`. Migration work:

- Rename `plus-one-counters` → `counters-payoffs`.
- Rename `ramp-big-mana` → `ramp-bigmana` (or keep hyphenated — board preference).
- Merge `amass-orcs` + `amass-armies` regex patterns into `tokens-go-wide`'s patterns or a sub-section.
- Merge `eldrazi-colorless` regex patterns into `ramp-bigmana`.
- Generalize `elf-tribal` regex into `tribal` parameterized on tribe (or keep current concrete entries and add per-tribe rows).
- Remove `voltron` from playbook (no deck uses it).

This is a follow-up DEC- issue, blocked on this taxonomy's approval.

## What I need from the board

Approve, decline, or amend this 13-archetype list. Specifically:

1. Do you want me to cut `group-slug` (merge into `stax-control`), `lands-matter` (defer), or `etb-flicker` (merge into `artifacts-matter`)? Any one of those gets us to 12. None is required; 13 is workable if you'd rather keep them all.
2. Are the absorbed sub-recipes (amass, eldrazi, elf-tribal under tribal) the right choice, or do you want them kept as top-level archetypes?
3. Any archetype missing that you anticipate building toward (e.g., enchantress, lifegain, mill, equipment-cares, discard-madness)?

Once approved, Gate 2 (canon set) work begins for the first archetype — I'd suggest **aristocrats** as the pilot since three existing decks use it, giving us the broadest validation surface.
