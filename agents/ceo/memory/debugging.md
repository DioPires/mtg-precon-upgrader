# Debugging

Known bugs, tool quirks, and root-cause fixes discovered during development sessions.

---

### Commander Spellbook MCP: Transient Null Error
The Commander Spellbook MCP (`commanderspellbook_find_combos`) occasionally returns a transient null/empty response even when the API is reachable. This is a backend transience issue, not a decklist problem. Workaround: document known combos manually when the MCP fails, then retry in a later heartbeat. The combo was still valid — the error is from the MCP layer, not from the decklist being wrong.

Confirmed example: Hidden Legion deck (DEC-290/DEC-291) — Kiki-Jiki + Cloudstone Curio + Dragon Tempest combo documented manually after MCP null error.
- Source: session c3cac001, 2026-05-20

---

### Scryfall MCP: Planeswalker Loyalty Field Missing
The Scryfall MCP response object for planeswalkers does not include the `loyalty` field. This causes incorrect loyalty values to be stated when relying on the MCP response. Always verify planeswalker loyalty via raw Scryfall API JSON or manual lookup. See also the corresponding entry in `patterns.md` (Scryfall MCP: Planeswalker Loyalty Verification).
- Source: sessions 0ad5aa7d, 4f8fa4d0; 2026-05-19
