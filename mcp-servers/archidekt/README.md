# Archidekt MCP Server

MCP server for publishing deck data from The Grimoire to Archidekt.

## Setup

```bash
cd mcp-servers/archidekt
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Environment Variables

- `ARCHIDEKT_AUTH_TOKEN` — Required for write operations (create/update decks)
- `ARCHIDEKT_USERNAME` — Archidekt profile username (default: `pirex`)
- `GRIMOIRE_DATA_DIR` — Path to data directory (default: auto-detected)

## Tools

- `archidekt_list_decks` — List decks on the Archidekt profile
- `archidekt_publish_deck` — Create or update a deck from deck.json
- `archidekt_sync_all` — Sync all deck.json files to Archidekt
