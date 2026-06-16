@AGENTS.md

## Frontend (post-DEC-149 cutover, 2026-05-05)

The Grimoire is now `web/` (Vite + React 18 + TypeScript). The vanilla-JS app is archived in `legacy/` for one release. Build with `cd web && npm install && npm run build` — output `web/dist/`. Deploy config is `vercel.json` at repo root. See [`AGENTS.md`](AGENTS.md) for the full file map.

## Deck JSON Validation

After changing any commander `deck.json`, run `uv run python scripts/validate_deck_json.py --deck {id}`. This is also called by `scripts/smoke_test.sh`.

## YouTube Research MCP Server

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

## Commander Spellbook MCP Server

**Location**: `mcp-servers/commanderspellbook/`

An MCP server for looking up combos in a decklist via Commander Spellbook's API.

### Available Tools (after restart)
- `commanderspellbook_find_combos` - Find included combos and near-miss combos for a decklist

### Usage
Pass the full 99-card decklist to find combos:
```
commanderspellbook_find_combos(decklist=["Sol Ring", "Meren of Clan Nel Toth", ...])
```

Returns:
- `included` — combos fully enabled by the decklist
- `almost_included` — combos 1-2 cards away, with `missing_cards` and `missing_templates`

## Archidekt MCP Server

**Location**: `mcp-servers/archidekt/`

An MCP server for publishing deck data to Archidekt (https://archidekt.com/u/pirex).

### Available Tools (after restart)
- `archidekt_list_decks` — List decks on the Archidekt profile (no auth needed)
- `archidekt_publish_deck` — Create or update a deck from deck.json (auth required)
- `archidekt_sync_all` — Sync all deck.json files to Archidekt (auth required)

### Usage
```
archidekt_list_decks()
archidekt_publish_deck(deck_id="titan-convergence", dry_run=True)
archidekt_sync_all(dry_run=True)
```

### Auth
Set `ARCHIDEKT_AUTH_TOKEN` env var for write operations.

### Context File
See `mcp-servers/archidekt/CLAUDE_CONTEXT.md` for full implementation details.
