# Debugging

### Scryfall Phyrexian Mana SVG URL: Slash Stripping Required
Scryfall's SVG CDN strips slashes from hybrid/Phyrexian mana symbol filenames. `{U/P}` → `UP.svg` (NOT `U/P.svg` or `U%2FP.svg`). Both `encodeURIComponent()` and preserved slashes return 404. Fix: use `.replace(/\//g, '')` on the symbol string before constructing the URL. This is a systemic issue affecting all hybrid and Phyrexian mana symbols in `renderManaCost()`.
- Source: session 4c834e83, 2026-03-17

### Broken Token Images: Fabricated Scryfall IDs
Token `scryfall_id` fields must use real Scryfall token IDs — fabricated IDs cause broken images in the UI. Always look up the actual token via Scryfall's token search (e.g., `t:pilot`) and use the real `id` from the response. The NEO Pilot token ID is `be84f259-...` (verify via Scryfall if needed).
- Source: session 4c834e83, 2026-03-17

### Simulation Wrong Avg CMC: Missing Card Metadata
If the simulation reports an unexpectedly low avg CMC or wrong land count, the cause is usually missing entries in `card-metadata.json`. The simulation falls back to default values for unknown cards, skewing results. Fix: run `scripts/fetch_card_metadata.py` to regenerate metadata from Scryfall for all decks.
- Source: session c566e4f7, 2026-03-17

### Urza Commander CMC Was Coded as 5, Correct Value is 4
Urza, Lord High Artificer costs `{2}{U}{U}` = CMC **4** (2 generic + 2 blue pips). An initial implementation coded him as CMC 5 with 3 blue pips. This affected castability simulation targets and the commander cost dict. Verify via Scryfall when uncertain about commander mana costs.
- Source: session c566e4f7, 2026-03-17

### Commander Spellbook MCP: Dead Variable and Rate Limit Order
Two bugs fixed in `client.py` during code review:
1. `last_error` variable was assigned but never read — dead code removed
2. `_rate_limit()` was called only after 429 responses, not at the start of every attempt — moved to top of retry loop so all attempts (initial + retries) rate-limit uniformly
- Source: session ee529a54, 2026-03-17

### Missing Land Metadata Causes Inflated Mulligan Rate
When land entries are missing from `card-metadata.json`, the simulation misclassifies them as `type_line: "Unknown"` → those lands are excluded from `land_set` → `should_mulligan()` sees too few mana sources → mulligan rate spikes (e.g., 29% kept vs expected ~90%). Impact chain: missing metadata → land misclassification → undercounted mana sources → inflated free+paid mulligans → incorrect simulation verdict. Root cause: `fetch_card_metadata.py` was not run after a new deck was added. Fix: run the metadata script, then re-export.
- Source: session 975406e6 (DEC-6), 2026-03-20

### CSS `position: fixed` Broken by Ancestor `transform` (View-Switch Animation)
The shopping list card preview tooltip used `position: fixed` with cursor coordinates, but appeared far from the cursor. Root cause: the view-switch animation sets `container.style.transform = 'translateY(0)'` inline, which persists after the transition and creates a new CSS containing block — making `position: fixed` children positioned relative to `.container` instead of the viewport. Fix: clear `container.style.transform = ''` after the transition completes. Any inline `transform`, `filter`, `will-change`, or `perspective` style on an ancestor will break `position: fixed` descendants.
- Source: session cfbae8d5, 2026-03-21

### XSS Risk: Inline onclick Handlers with Card Names
Card names can contain single quotes (e.g., "Painter's Servant", "Delver of Secrets"), which break inline `onclick="func('${cardName}')"` attributes and create XSS vectors. Fix: use `data-*` attributes on the element and add a delegated `click` event listener on the container instead. Pattern: `element.dataset.cardName = cardName` then `container.addEventListener('click', e => { const name = e.target.closest('[data-card-name]')?.dataset.cardName; ... })`.
- Source: session 5931830a, 2026-03-22

### Shell Heredoc Contamination in Paperclip Plan Updates
When updating a Paperclip plan document via bash, using a shell heredoc (`cat <<'PLANEOF' | python3 -c ...`) leaks the heredoc delimiter string (`cat <<'PLANEOF'`) into the JSON body field. The Paperclip API stores the contaminated literal text, corrupting the plan document. Fix: use a pure Python heredoc instead — `python3 << 'PYEOF'` with `json.dumps()` to construct the payload, then pipe to curl. This keeps the JSON construction entirely in Python where there is no shell heredoc leakage.
- Source: session fd90e34c, 2026-04-06

### Simulation Script Requires --json Flag to Export JSON
The deck simulation scripts (`mana_simulation_*.py`) only print results to stdout by default. They do NOT automatically update `simulation.json`. To regenerate the JSON output file, run `export_simulation_results.py` (or the script with `--json` flag if supported). After a card swap, re-running the simulation script alone is insufficient — must also trigger the export step.
- Source: session 60e50238, 2026-04-06

### Simulation --json Flag Parsed But Not Wired (Older Scripts)
Some per-deck-ID simulation scripts (`argparse` added `--json`) but the `main()` function never calls the exporter — the flag is parsed and silently ignored. Fix: add the export call at the end of `main()` when `args.json` is true, calling `exporter.export_<deck>()`. Affected scripts discovered in DEC-66: `mana_simulation_the_white_forge.py` and `mana_simulation_verdant_tide.py`. Check any newly created sim script for this wiring before marking it complete.
- Source: session a1a821dd, 2026-04-06

### White Forge Deck Directory: the-white-forge (Renamed from gandalf-the-white)
The "The White Forge" deck (Gandalf the White commander) was renamed in DEC-68 (2026-04-07). Current path: `data/commanders/the-white-forge/deck.json`. Previous path `data/commanders/gandalf-the-white/` no longer exists. `data/commanders/forge-and-fury/` is a completely different deck (Korvold, Fae-Cursed King — Jund artifact token drain strategy). Always use the deck catalog in `data/index.json` to resolve the correct directory slug.
- Sources: session e350bd34, 2026-04-06; session c4b05b83, 2026-04-07

### Fabricated Card Category: High-Society Hunter Called "Tutor"
Session c5d1cff9 caught an error where the agent described High-Society Hunter as a tutor (listing it among tutors like Demonic Tutor, Buried Alive, Entomb). Hunter is a 5CMC 5/3 flying Human Warrior with a death-draw ability — completely different role. The card name ("Hunter") and high CMC triggered a false pattern-match to "tutor" without Scryfall verification. The board corrected this; the swap rationale had to be rewritten (cut as redundant death-draw, not as redundant tutor). Always call `scryfall_card_by_name` before categorizing a card's role — card names are not reliable indicators of card text.
- Source: session c5d1cff9, 2026-04-16

### DFC (Prepare Mechanic) Mana Cost Display Bug
DFC cards (e.g., "Emeritus of Woe // Demonic Tutor") showed no mana cost in the UI. Root cause: the app caches Scryfall metadata keyed by `card.name`, but for DFCs Scryfall returns the combined name (e.g., "Emeritus of Woe // Demonic Tutor") while the decklist stores only the front face name ("Emeritus of Woe") — cache lookup misses → no mana cost renders. Additionally, `data.mana_cost` for DFCs returns the combined string (e.g., `{3}{B} // {1}{B}`) rather than the front face cost. Fix: in both single-card and batch Scryfall fetch paths, detect DFCs via `card.card_faces`, use `card_faces[0]` mana cost, and cache metadata under BOTH the full combined name and the front face name. Also add DFCs to `card-metadata.json` using the FRONT FACE mana cost only.
- Source: session bbb82b17, 2026-04-24

### jq Deck Size Undercounts When Basics Use `quantity` Field
Never use `.decklist | length` to count total cards in a deck.json — it counts unique entries, not total cards. Basic lands frequently use a `quantity` field > 1 (e.g., `{"name":"Swamp","quantity":11}`). On 2026-05-03 (DEC-101 eternal-agony review), `.decklist | length` returned 84 for a 99-card deck: 84 unique entries + 10 extra Swamps + 5 extra Mountains. Use `jq '[.decklist[] | .quantity // 1] | add' deck.json` for the correct total. Applies to all validation, swap sanity checks, and any deck size reporting.
- Source: session fd3ef271, 2026-05-03
