# MTG Precon Upgrader

## Dryness Dial — This project: High

## Tooling

No build step. Static files. Serve with any HTTP server or open index.html directly.

## Project Overview

A web application that provides recommended commander deck builds for Magic: The Gathering. The app displays card recommendations, synergies, and shopping lists for building commander decks up to Bracket 4.

## Architecture

- **Frontend**: Single-page vanilla JS app (`index.html`)
- **Data**: JSON files in `data/commanders/{id}/deck.json`
- **External API**: Scryfall for card metadata/images
- **Hosting**: Static files (no backend)

## Key Files

| File | Purpose |
|------|---------|
| `index.html` | Main application (HTML + CSS + JS) |
| `data/index.json` | Deck catalog (commanders) |
| `data/commanders/{id}/deck.json` | Per-commander deck data |
| `data/game-changers.json` | Official Game Changers card list |

## Commander Deck Data Structure

Each deck JSON is a flat structure with no tier/upgrade wrappers:

```json
{
  "id": "titan-convergence",
  "type": "commander",
  "name": "Titan Convergence",
  "subtitle": "Cascading Inevitability",
  "commander": "Zhulodok, Void Gorger",
  "cost": "$200-350",
  "bracket": "4",
  "gameChangers": 2,
  "sources": [...],
  "guideContent": {
    "strategyOverview": "...",
    "deckCategories": [{ "name": "Eldrazi Threats", "description": "...", "cards": [...] }]
  },
  "addCategories": [...],
  "adds": [...],
  "synergies": [...],
  "decklist": [{ "name": "Card Name", "type": "Creature" }, ...]
}
```

**Key fields:**
- `type: "commander"` (required)
- `bracket` — display field indicating deck power level
- `gameChangers` — count of Game Changer cards in the deck
- `guideContent.deckCategories` — deck theme groupings
- `decklist` — full 99-card list as `{name, type}` objects with optional `quantity` field
- `adds` — notable/highlighted cards
- `synergies` — card synergy pairs/groups
- `sources` — attribution for the deck build

## Deck Rules

- **Display names should be strategic** (e.g., "Dark Dominion", not "Sauron Deck")
- Every card recommendation must be attributed via `sources`
- **Card pool**: Cards printed through March 2026
- **Card text validation**: ALWAYS verify card names and oracle text via the `scryfall_card_by_name` MCP tool before recommending cards. Never assume card text or abilities from memory — validate every card considered. For bulk validation, use `scryfall_collection`.
- **Bracket 4/5 deckbuilding principles**: See [`data/bracket-philosophy.md`](data/bracket-philosophy.md) for mana base, fast mana, free spells, interaction, and card quality standards. Apply when building or updating B4+ decks.

## Source Attribution Schema

Every card add, synergy, and deck must have a `sources` array for traceability.

**Source object shape:**
```json
{
  "type": "edhrec" | "youtube" | "draftsim" | "article" | "scryfall" | "commanderspellbook" | "ai-inferred" | "other",
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
- Per-deck: `sources` (root level)
- Per-card: `adds[].sources`
- Per-synergy: `synergies[].sources`

**When to use `ai-inferred`:** For synergy identification, strategic analysis, or card recommendations that came from Claude's analysis rather than a specific external source.

## Research Workflow

When building or updating deck guides, use all available sources and cross-reference findings:

1. **Candidate Pool (mandatory first step — DEC-90)** — Run `python scripts/refresh_card_pool.py --deck {id}` before any review. This refreshes the local Scryfall mirror and regenerates `data/commanders/{id}/candidates.json`: the top-200 commander-legal cards scored against the deck's archetype tags + color identity + curve + ownership. Diff the `decklist` against the top of `candidates.json`. Any high-scoring candidate that is *not* in the decklist must be explicitly considered. Cuts require a reason captured in deck `sources` or review notes. See [`docs/discovery-playbook.md`](docs/discovery-playbook.md) for the archetype tagging contract.
2. **YouTube** — Search for commander deck tech videos, fetch transcripts, extract card recommendations
3. **EDHREC** — Check commander pages for top cards, new additions from recent sets
4. **Commander Spellbook** — Use `commanderspellbook_find_combos` MCP tool with the full decklist.
   - Record `included` combos as synergies with `"type": "commanderspellbook"` source
   - **Review `almost_included` combos** (1-2 cards away) — evaluate whether adding the missing card(s) makes strategic sense given deck strategy, budget, and bracket target
   - If a near-miss card enables a strong combo without hurting consistency, recommend it as an add with `commanderspellbook` source and note it was discovered via near-miss analysis
   - Combo URLs: `https://commanderspellbook.com/combo/{id}/`
5. **Moxfield** — Search popular decklists for the commander
6. **Scryfall** — Use `scryfall_card_by_name`, `scryfall_search`, and `scryfall_collection` MCP tools to verify card names, check oracle text, and look up card data
7. **Web Search** — Articles, Reddit discussions, deck tech write-ups

Attribute every recommendation to its source(s). Multiple sources for the same card strengthens the recommendation.

### Deck Review Checklist (DEC-90)

Before recommending changes to any deck:

1. Confirm `archetypes` is set on `data/commanders/{id}/deck.json`. If missing, tag with one or more IDs from [`data/discovery-playbook.json`](data/discovery-playbook.json).
2. Run `python scripts/refresh_card_pool.py --deck {id}`.
3. Open `data/commanders/{id}/candidates.json`. Scan the top 50 — each entry not already in the decklist is a potential overlook.
4. For each top candidate not in the deck, decide: include, defer (with note), or reject (with reason).
5. Verify any candidate you plan to add via `scryfall_card_by_name` MCP — never trust the playbook's pattern match without confirming the card text.
6. Update `decklist`, `highlights`, `synergies` as needed. Always attribute via `sources`.

## Common Tasks

### Add a New Commander Deck
1. Create `data/commanders/{new-id}/deck.json` with flat structure (see data structure above)
2. Add entry to `data/index.json` `commanders` array (with `theme` and `colors`)
3. Include full 99-card `decklist` array
4. Use `deckCategories` in `guideContent` for deck theme groupings

### Research Deck Updates (with YouTube MCP)
1. Search YouTube for relevant videos
2. Fetch transcripts from top results
3. Extract card recommendations
4. Compare with existing deck data
5. Update deck.json with new findings
