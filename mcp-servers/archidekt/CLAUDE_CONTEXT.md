# Archidekt MCP Server — Context

## Overview

Publishes deck data from The Grimoire (`data/commanders/{id}/deck.json`) to Archidekt.

## Architecture

```
src/archidekt_mcp/
├── server.py              # FastMCP server with 3 tools
├── config.py              # Constants, env vars
├── models.py              # Pydantic response models
├── services/
│   ├── client.py          # HTTP client (Archidekt + Scryfall APIs)
│   └── deck_builder.py    # Converts deck.json → Archidekt payload
└── tools/
    └── decks.py           # Tool implementations
```

## Tools

| Tool | Auth | Description |
|------|------|-------------|
| `archidekt_list_decks` | No | List decks on Archidekt profile |
| `archidekt_publish_deck` | Yes | Create or update a single deck |
| `archidekt_sync_all` | Yes | Sync all deck.json files |

## API Endpoints Used

| Operation | Endpoint | Auth |
|-----------|----------|------|
| List decks | `GET /api/decks/v3/?ownerId={id}` | No |
| Get deck | `GET /api/decks/{id}/` | No |
| Update deck | `PUT /api/decks/{id}/` | Yes |
| Create deck | `POST /api/decks/` | Yes |

**Note:** Archidekt's write API is undocumented. Auth uses `Authorization: Bearer {token}`.

## Card Resolution

Cards are resolved from names → Scryfall IDs using:
1. `POST /cards/collection` (bulk, 75 per batch)
2. Fallback to `GET /cards/named?exact={name}` for DFCs and not-found cards

## Known Archidekt Deck ID Mapping

Hardcoded in `tools/decks.py:KNOWN_ARCHIDEKT_IDS`:
- titan-convergence → 20760135
- eternal-agony → 20759936
- dark-dominion → 20760109
- mutant-multiplication → 20786495
- planar-decree → 20949443
- azure-dominion → 20946158
- genesis-protocol → 20946250
- eternal-harvest → 20946261
- compleated-dominion → (new)
- forge-and-fury → (new)

## Environment Variables

| Var | Required | Default | Description |
|-----|----------|---------|-------------|
| `ARCHIDEKT_AUTH_TOKEN` | For writes | (none) | Auth token for Archidekt API |
| `ARCHIDEKT_USERNAME` | No | `pirex` | Profile username |
| `GRIMOIRE_DATA_DIR` | No | auto | Path to `data/` directory |

## Claude Code MCP Config

Add to `.claude/settings.json`:
```json
{
  "mcpServers": {
    "archidekt": {
      "command": "/path/to/mcp-servers/archidekt/.venv/bin/archidekt",
      "env": {
        "ARCHIDEKT_AUTH_TOKEN": "your-token-here",
        "GRIMOIRE_DATA_DIR": "/path/to/data"
      }
    }
  }
}
```
