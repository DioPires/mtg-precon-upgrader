# Tool Usage

### commanderspellbook_find_combos: Full Decklist Required
Pass the full 99-card decklist (as a `list[str]` of card names) to `commanderspellbook_find_combos`. The tool:
- Returns `included` — combos fully enabled by the decklist
- Returns `almost_included` — combos 1-2 cards away, with `missing_cards` (named cards) and `missing_templates` (generic role requirements like "any persist creature")
- Caches results by SHA256 of sorted decklist for 24 hours
- Always evaluate `almost_included` during deck research — it surfaces the most impactful potential adds
- Source: session ee529a54, 2026-03-17

### Scryfall Mana Symbol SVG URLs
Scryfall SVG CDN URL format: `https://svgs.scryfall.io/card-symbols/{symbol}.svg`
- Strip all slashes from the symbol name before use
- `{U/P}` → `UP.svg` ✓
- `{U/P}` → `U/P.svg` ✗ (404)
- `{U/P}` → `U%2FP.svg` ✗ (404)
In JavaScript: `symbol.replace(/\//g, '')` before constructing the URL.
- Source: session 4c834e83, 2026-03-17

### fetch_card_metadata.py: Regenerate After Deck Changes
Run `scripts/fetch_card_metadata.py` after adding or replacing cards in any deck. It reads all `deck.json` files, identifies cards missing from `card-metadata.json`, and fetches their data from Scryfall. Required for accurate simulation results. Without it, new cards default to CMC 0 and unknown type, skewing avg CMC and land counts.
- Source: session c566e4f7, 2026-03-17

### export_simulation_results.py: Re-Export After Changes
After modifying a simulation script or card metadata, run `export_simulation_results.py` to regenerate all `simulation.json` files. It exports results for all registered decks including the `DECKS` dict entry. If you only modified one deck's script, it's still safest to export all to keep results in sync.
- Source: session f4a29b04, 2026-03-17

### Archidekt API Quirks
- **Deck listing**: use `GET https://archidekt.com/api/decks/cards/?ownerId=958885` (v3). The `owner=username` param does a text search returning global results — use `ownerId=<numeric>` for the correct user filter.
- **Write API**: `PUT /api/decks/{id}/` requires `Authorization` header (undocumented; accepts Django auth tokens via `ARCHIDEKT_AUTH_TOKEN` env var).
- **DFC card names**: double-faced cards use `//` in names (e.g., `"Delver of Secrets // Insectile Aberration"`). The Scryfall collection API may not match these — fall back to just the front face name (before `//`) for resolution.
- **Scryfall batch limit**: collection endpoint accepts max 75 identifiers per request.
- Source: session a9954278, 2026-03-20

### Archidekt MCP Tools
Three tools in `mcp-servers/archidekt/`:
- `archidekt_list_decks()` — lists decks from Archidekt profile (read-only, no auth required)
- `archidekt_publish_deck(deck_id, dry_run=False)` — creates or updates one deck from its `deck.json`; requires `ARCHIDEKT_AUTH_TOKEN`
- `archidekt_sync_all(dry_run=False)` — syncs all `deck.json` files to Archidekt; uses `archidekt_deck_ids.json` to map slugs → Archidekt IDs
Use `dry_run=True` to validate card resolution and payload without writing to Archidekt.
- Source: session a9954278, 2026-03-20

### Pencil MCP: Returns Empty Nodes Despite File Open (v1.1.37 Bug)
Pencil MCP v1.1.37 consistently returns zero nodes when calling `batch_get` or `get_editor_state` on `designs/grimoire-ui.pen` (248KB file). The MCP server reports success and the app is running (PID confirmed), but the desktop app does not return node data. This blocks any programmatic design spec work. Workaround: none found programmatically — requires manually restarting Pencil or verifying the file loads in the GUI before retrying.
- Source: sessions cfbae8d5, 67bea232, 08ae0f62, 2026-03-21/22

### Commander Spellbook REST API: Bracket Endpoint
Commander Spellbook exposes a `/estimate-bracket` endpoint at `backend.commanderspellbook.com` in addition to `/find-my-combos`. Useful for bracket classification of a given decklist. The MCP server currently only exposes `find-my-combos`; bracket estimation would require a direct API call or MCP extension.
- Source: session b27105d7, 2026-03-21
