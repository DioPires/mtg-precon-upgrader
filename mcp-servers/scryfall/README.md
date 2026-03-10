# Scryfall MCP Server

MCP server providing structured access to Scryfall's MTG card database with SQLite response caching.

## Tools

- `scryfall_card_by_name` — Look up a card by name (fuzzy or exact)
- `scryfall_search` — Search using Scryfall syntax
- `scryfall_collection` — Bulk lookup multiple cards
- `scryfall_card_by_id` — Look up by Scryfall UUID
- `scryfall_rulings` — Get official rulings for a card

## Install

```bash
uv venv && uv pip install -e ".[dev]"
```

## Run

```bash
python -m scryfall_mcp.server
```

## Test

```bash
pytest tests/
```
