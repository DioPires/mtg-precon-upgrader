# MTG Precon Upgrader

## Dryness Dial — This project: High

## Tooling

No build step. Static files. Serve with any HTTP server or open index.html directly.

## Project Overview

A web application that provides upgrade guides for MTG Commander preconstructed decks and recommended commander deck builds. The app displays card recommendations, synergies, cuts (for precons), and shopping lists for upgrading precons to Bracket 3 or building commander decks up to Bracket 4.

## Architecture

- **Frontend**: Single-page vanilla JS app (`index.html`)
- **Data**: JSON files in `data/precons/{id}/deck.json` and `data/commanders/{id}/deck.json`
- **External API**: Scryfall for card metadata/images
- **Hosting**: Static files (no backend)

## Key Files

| File | Purpose |
|------|---------|
| `index.html` | Main application (HTML + CSS + JS) |
| `data/index.json` | Deck catalog (precons + commanders) |
| `data/precons/{id}/deck.json` | Per-precon upgrade data |
| `data/commanders/{id}/deck.json` | Per-commander deck recommendations |
| `data/game-changers.json` | Official Game Changers card list |
| `docs/{id}/*.md` | Markdown documentation per precon |

## Precon Data Structure

```json
{
  "id": "eldrazi-unbound",
  "name": "Eldrazi Unbound",
  "commander": "Kozilek, the Great Distortion",
  "currentBracket": "1-2",
  "targetBracket": "3",
  "baseDeck": [...],
  "cuts": [...],
  "upgrades": {
    "full": { "adds": [...], "synergies": [...] },
    "midrange": { "adds": [...], "synergies": [...] }
  }
}
```

## Commander Deck Data Structure

Commander decks (`type: "commander"`) are full recommended builds — no baseDeck or cuts. Each tier contains a complete `decklist` array.

```json
{
  "id": "sauron-the-dark-lord",
  "type": "commander",
  "name": "Sauron, The Dark Lord",
  "commander": "Sauron, the Dark Lord",
  "targetBracket": "3",
  "guideContent": {
    "strategyOverview": "...",
    "deckCategories": [{ "name": "Amass Payoffs", "description": "...", "cards": [...] }]
  },
  "upgrades": {
    "full": {
      "name": "Dark Dominion",
      "cost": "$180-250",
      "adds": [...],
      "synergies": [...],
      "decklist": [{ "name": "Card Name", "type": "Creature" }, ...]
    }
  }
}
```

**Key differences from precon data:**
- `type: "commander"` (required) — triggers commander deck UI mode
- No `baseDeck`, `cuts`, or `currentBracket` fields
- `guideContent.deckCategories` replaces `cutCategories` — shows deck theme groupings instead of cut reasons
- Each tier has a `decklist` array with the full 99 cards
- `adds` array serves as "notable/highlighted cards" (not a diff against a base)

## Upgrade Guide Rules

### Precon Upgrades
- **All precon tiers target Bracket 3** — strongest builds possible while staying in Bracket 3
- **Up to 3 Game Changers allowed** per tier (per `data/game-changers.json`). Vampiric Tutor in baseDeck counts toward this limit
- **At least 1 budget tier per precon** — affordable entry point ($40-60), 0 Game Changers
- **Non-budget tiers = strongest Bracket 3 builds** — different tiers represent different strategic concepts/archetypes, not just different price points
- **Alternate commander builds** are valid tiers if research suggests a different commander from the precon creates a meaningfully distinct deck
- **Cuts are shared** — each precon has a single top-level `cuts` array used by all tiers
- **No card should appear in both `adds` and `baseDeck`**

### Commander Decks
- **Commander decks can target up to Bracket 4** — higher power ceiling since there's no precon starting point
- **At least 3 tiers required**: 1 budget (Bracket 3, 0 GCs), at least 1 Bracket 3 tier (up to 3 GCs), at least 1 Bracket 4 tier (no GC limit)
- **Bracket 4 tiers have no Game Changer limit** — include as many as the strategy warrants
- **Each tier uses a per-tier `bracket` field** that controls the bracket bar display

### Shared Rules
- **Tier keys control UI ordering**: full → midrange → budget → others
- **Display names should be strategic** (e.g., "Dark Dominion", not "Full Upgrade")
- Tiers are NOT just price tiers — each should have a distinct strategic identity

## Tier Philosophy

- **Budget tier** = affordable entry point (~$40-60, 0 Game Changers, Bracket 3). Focuses on high-synergy, low-cost cards
- **Bracket 3 tiers** = strong builds with up to 3 Game Changers. Each should have a distinct identity (e.g., reanimator-focused, tribal-focused, control-focused)
- **Bracket 4 tiers** (commander decks only) = maximum power, no GC limit. Optimized mana, best-in-slot cards, multiple synergy axes
- Tiers are NOT just price tiers — a $100 tier and a $150 tier should explore different strategies, not the same strategy at different budgets

## Source Attribution Schema

Every card add, synergy, and tier must have a `sources` array for traceability.

**Source object shape:**
```json
{
  "type": "edhrec" | "youtube" | "draftsim" | "article" | "scryfall" | "ai-inferred" | "other",
  "name": "Human-readable label",
  "url": "https://...",
  "detail": "Extra context (timestamp, section, etc.)"
}
```
- `type` (required): determines icon shown in UI
- `name` (required): human-readable label
- `url` (optional): link to source. Omit for `ai-inferred`
- `detail` (optional): extra context

**Where sources arrays go:**
- Per-card: `adds[].sources`
- Per-synergy: `synergies[].sources`
- Per-tier: `upgrades.{tier}.sources`

**When to use `ai-inferred`:** For synergy identification, strategic analysis, or card recommendations that came from Claude's analysis rather than a specific external source.

## Research Workflow

When building or updating upgrade guides, use all available sources and cross-reference findings:

1. **YouTube** — Search for precon upgrade videos, fetch transcripts, extract card recommendations
2. **EDHREC** — Check commander pages for top cards, new additions from recent sets
3. **Moxfield** — Search popular decklists for the commander
4. **Scryfall** — Verify card names exist, check current pricing
5. **Web Search** — Articles, Reddit discussions, deck tech write-ups

Attribute every recommendation to its source(s). Multiple sources for the same card strengthens the recommendation.

## Common Tasks

### Add a New Precon Guide
1. Create `data/precons/{new-id}/deck.json`
2. Add entry to `data/index.json` `precons` array
3. Create markdown docs in `docs/{new-id}/`

### Add a New Commander Deck
1. Create `data/commanders/{new-id}/deck.json` with `type: "commander"`
2. Add entry to `data/index.json` `commanders` array (with `theme` instead of `set`)
3. Include full 99-card `decklist` array in each tier
4. Use `deckCategories` instead of `cutCategories` in `guideContent`

### Research Upgrades (with YouTube MCP)
1. Search YouTube for relevant videos
2. Fetch transcripts from top results
3. Extract card recommendations
4. Compare with existing guide
5. Update deck.json with new findings
