# Tools

## Paperclip API (local instance)

- Base URL: `$PAPERCLIP_API_URL` (http://127.0.0.1:3100); auth via `Authorization: Bearer $PAPERCLIP_API_KEY` (env, short-lived JWT per run).
- Issue UUID for the current wake: `PAPERCLIP_WAKE_PAYLOAD_JSON` → `.issue.id` (DEC-### identifiers do NOT resolve in API paths).
- Post comment: `POST /api/issues/{uuid}/comments` with `{"body": "..."}`.
- Set status: `PATCH /api/issues/{uuid}` with `{"status": "done" | ...}`.
- Route-shape gotchas: see memory `reference_paperclip_api_route_shapes`.

## MCP servers (project-scoped)

- `scryfall_*` — card oracle text / search / bulk collection. Mandatory for any card claim.
- `commanderspellbook_find_combos` — combo + near-miss lookup (MCP pydantic crash workaround: curl backend, see memory).
- `youtube_*` — deck-tech research.
- `archidekt_*` — publish decks (needs `ARCHIDEKT_AUTH_TOKEN` for writes).
