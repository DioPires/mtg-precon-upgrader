# Discovery Playbook

**Purpose:** force *retrieval-led* card discovery before any deck build or review. The 14 archetypes below define oracle-text patterns and supporting metadata that sweep the full commander-legal universe (mirrored locally) for candidate cards.

**Source of truth:** [`data/discovery-playbook.json`](../data/discovery-playbook.json) — consumed by `scripts/generate_candidate_pool.py`. This document is a human-readable companion. If they drift, the JSON wins.

## Why this exists (DEC-90)

Discovery without a playbook is recall-led: we query Scryfall for cards we already think of and never sweep the full set of cards matching a deck's criteria. This document mandates a structured archetype → query mapping so that every deck is analysed against the same retrieval lens.

## How to use

1. Tag your deck with one or more archetype IDs in `data/commanders/{id}/deck.json` under the `archetypes` field.
2. Run `python scripts/refresh_card_pool.py --deck {id}` (or `--all`).
3. Review `data/commanders/{id}/candidates.json` — every card scoring above the configured floor that is **not** in the decklist must be explicitly considered. Cuts require a reason.

## Archetype index

| ID | Used by | Strategy in 1 line |
|---|---|---|
| `graveyard-reanimator` | eternal-harvest | Mill/sac into yard, return for value |
| `aristocrats` | eternal-harvest, dark-dominion | Sacrifice + death-trigger payoffs |
| `tokens-go-wide` | mutant-multiplication, dark-dominion | Many small tokens + anthems/doublers |
| `plus-one-counters` | mutant-multiplication, creeping-corruption | Place, double, pay off counters |
| `infect-poison` | creeping-corruption | Win via 10 poison counters |
| `voltron` | (latent — none yet) | One creature stacked with auras/equipment |
| `spellslinger` | dark-dominion | Cast many noncreature spells; cost reduction + copy |
| `group-slug` | eternal-agony | Trickle damage on every action |
| `stax-control` | genesis-protocol | Asymmetric resource denial |
| `artifacts-matter` | the-white-forge, genesis-protocol | Artifact density + flicker engines |
| `ramp-big-mana` | titan-convergence, verdant-tide | Cheat oversized threats into play early |
| `elf-tribal` | verdant-tide | Tribal anthems + mana dorks |
| `lands-matter` | (latent) | Landfall + extra-land effects |
| `etb-flicker` | the-white-forge | Re-fire ETB triggers via flicker |

Multiple tags per deck are expected — most decks lean on 2–3 archetypes.

## Per-archetype entry structure (in JSON)

```jsonc
{
  "name": "Human-readable name",
  "summary": "1-line strategic summary",
  "oracle_patterns": ["case-insensitive Python regex"],   // matched against oracle_text
  "type_constraints": ["Equipment", "Aura"],              // optional; substring match against type_line
  "cmc_max": 5,                                           // optional; cards above this are demoted
  "staples": ["Reanimate", "Animate Dead"],              // always-consider list, even if low pattern density
  "anti_patterns": ["graveyard hate"]                    // patterns that disqualify a card despite matches
}
```

## Scoring contract

Each candidate card is scored 0–100 by the generator. Components:

1. **Archetype keyword density (0–40):** count of `oracle_patterns` matched, scaled by total patterns.
2. **CMC fit (0–20):** distance from deck's average CMC; rewards on-curve options.
3. **Owned (0–15):** binary, from `priv_data/owned_formatted.csv`.
4. **Game Changer × bracket (0–15):** Game Changers score full at B5, partial at B4, zero at B3.
5. **Decklist demotion:** cards already in the deck cap at 5, so they still rank but yield to alternatives.

Anti-patterns disqualify outright (return score 0).

## Maintenance

- New archetype: add a key to `data/discovery-playbook.json` with the entry shape above.
- New deck: tag with applicable archetype IDs.
- Pattern tuning: when the generator misses obvious staples or surfaces noise, edit the patterns/staples and re-run. Track tuning rationale in commit messages.

## Out of scope

- Color identity filtering — handled by the generator, not the playbook.
- Bracket gating — handled by the scoring layer.
- Synergy combos — covered by Commander Spellbook MCP, not this playbook.
