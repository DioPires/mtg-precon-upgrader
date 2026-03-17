# Commander Spellbook MCP Server

MCP server for Commander Spellbook combo lookup with SQLite response caching.

## Tools

- `commanderspellbook_find_combos` — Find combos in a decklist (included + near-miss)

## Install

```bash
uv venv && uv pip install -e ".[dev]"
```

## Run

```bash
python -m commanderspellbook_mcp.server
```

## Test

```bash
pytest tests/
```
