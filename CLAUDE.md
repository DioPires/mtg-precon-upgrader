# MTG Precon Upgrader - Claude Context

## Project Overview

A web application that provides upgrade guides for MTG Commander preconstructed decks. The app displays card recommendations, synergies, cuts, and shopping lists for upgrading precons to higher power levels (bracket system).

## Architecture

- **Frontend**: Single-page vanilla JS app (`index.html`)
- **Data**: JSON files in `data/precons/{id}/deck.json`
- **External API**: Scryfall for card metadata/images
- **Hosting**: Static files (no backend)

## Key Files

| File | Purpose |
|------|---------|
| `index.html` | Main application (HTML + CSS + JS) |
| `data/index.json` | Precon catalog |
| `data/precons/{id}/deck.json` | Per-precon upgrade data |
| `data/game-changers.json` | Official Game Changers card list |
| `docs/{id}/*.md` | Markdown documentation per precon |

## YouTube Research MCP Server (NEW)

**Location**: `mcp-servers/youtube-research/`

An MCP server that allows Claude to research MTG content creator videos when building upgrade guides.

### Available Tools (after restart)
- `youtube_search_videos` - Search YouTube for MTG videos
- `youtube_get_transcript` - Fetch video transcripts
- `youtube_get_metadata` - Get video details
- `youtube_list_channels` - List curated channels

### Usage
Ask Claude to research YouTube videos for a precon:
```
"Research YouTube videos for Eldrazi Unbound upgrades"
```

### Context File
See `mcp-servers/youtube-research/CLAUDE_CONTEXT.md` for full implementation details and troubleshooting.

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

## Common Tasks

### Add a New Precon Guide
1. Create `data/precons/{new-id}/deck.json`
2. Add entry to `data/index.json`
3. Create markdown docs in `docs/{new-id}/`

### Research Upgrades (with YouTube MCP)
1. Search YouTube for relevant videos
2. Fetch transcripts from top results
3. Extract card recommendations
4. Compare with existing guide
5. Update deck.json with new findings
