# Recommendation Methodology v1

## Overview

The recommendations engine suggests deck optimizations for each curated deck build.
Recommendations are pre-computed and stored as `recommendations.json` per deck.

## Data Sources

Each recommendation is derived from one or more sources:

| Source | Type Key | What It Provides |
|--------|----------|------------------|
| Commander Spellbook | `commanderspellbook` | Near-miss combos (1-2 cards away from a combo) |
| Scryfall | `scryfall` | Card data verification, synergy search |
| Card Metadata | `card-metadata` | CMC, color, type analysis for swap impact |
| Simulation Baselines | `simulation` | Deck health score components for gap analysis |
| Game Changers List | `game-changers` | Bracket impact assessment |
| Owned Cards | `owned-cards` | Personalization overlay |

## Scoring Criteria

Each recommendation receives a composite score (0-100) based on:

### 1. Source Diversity (0-30 points)
- 1 source: 10 points
- 2 sources: 20 points
- 3+ sources: 30 points

Independent corroboration from multiple sources signals a strong recommendation.

### 2. Combo Enablement (0-25 points)
- Enables a 2-card combo: 25 points
- Enables a 3-card combo: 20 points
- Enables a 4+ card combo: 15 points
- Near-miss (1 card away): full points
- Near-miss (2 cards away): half points

Cards that unlock combos with pieces already in the deck are high-value additions.

### 3. Deck Health Gap Fill (0-20 points)
Based on which health score component is weakest:
- Card addresses the weakest component: 20 points
- Card addresses a below-average component: 10 points
- Card is neutral: 0 points

Components: manaReliability, threatDeployment, interactionDensity, comboConsistency, commanderIndependence.

### 4. Bracket Fit (0-15 points)
- Card is NOT a Game Changer: 15 points
- Card IS a Game Changer but deck is already B5: 10 points
- Card IS a Game Changer and deck targets B3-4: 0 points

Recommendations should not inadvertently push a deck above its target bracket.

### 5. Swap Viability (0-10 points)
- Clear swap candidate exists (low-synergy card of same type): 10 points
- Swap candidate exists but type mismatch: 5 points
- No obvious swap: 0 points

## Recommendation Categories

- `combo-enabler` — Completes or nearly completes a combo
- `synergy-upgrade` — Stronger version of an existing card or new synergy piece
- `health-fix` — Addresses a weak deck health component
- `strict-upgrade` — Strictly better version of a card in the deck

## Output Schema

See `data/commanders/{id}/recommendations.json` for the per-deck output format.

## Owned Card Overlay

When `priv_data/owned_formatted.csv` is available, recommendations are tagged with
`owned: true` if the user already owns the card. This is a client-side feature —
the owned card list is loaded separately and cross-referenced at render time.

## Versioning

The `methodology` field in each recommendations.json tracks which version of
scoring criteria was used. Regenerate when methodology changes.
