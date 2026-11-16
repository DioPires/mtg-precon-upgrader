# MTG Precon Upgrader

The Grimoire: a web app with recommended Magic: The Gathering Commander deck builds up to Bracket 4, with card recommendations, synergies, combos and shopping lists. Built with Commander Brackets format compliance in mind.

## Features

- **Interactive Web Interface** - Browse commander deck guides with card previews
- **Card Categorization** - Clear organization of additions, synergies, and their strategic purposes
- **Combo Lab** - Per-deck combos from Commander Spellbook, plus synergy and loop candidates
- **Commander Brackets Aware** - All decks are designed with the Commander Brackets format in mind
- **Shopping Lists** - Pre-formatted lists ready for deck-building sites

## Quick Start

```bash
# Clone the repository
git clone https://github.com/DioPires/mtg-precon-upgrader.git
cd mtg-precon-upgrader/web

# Install and run the app
npm install
npm run dev      # http://localhost:5173
```

Python scripts run from the repository root with `uv`; the card-pool, metrics and validator scripts need the local Scryfall mirror first: `uv run python scripts/refresh_scryfall_mirror.py`. `AGENTS.md` lists the build, test and data commands.

## Project Structure

```
mtg-precon-upgrader/
├── web/                    # The Grimoire: Vite + React + TypeScript app
├── data/
│   ├── index.json          # Deck catalog
│   ├── game-changers.json  # Official Game Changers list
│   └── commanders/{id}/    # Per-deck data: deck, simulation, metrics, candidates, Combo Lab files
├── scripts/                # Python tools: card pool, simulation, metrics, validators
├── mcp-servers/            # Local MCP servers: Scryfall, Commander Spellbook, Archidekt, YouTube
├── docs/                   # Methodology docs
└── legacy/                 # Archived vanilla-JS app from before the DEC-149 cutover
```

## Decks

`data/index.json` catalogs 21 decks: 15 built and 6 still brewing. The app lists them all.

## Commander Brackets

This project follows the [Commander Brackets](https://mtgcommander.net/index.php/2024-announcements/) system introduced by the Commander Rules Committee:

- **Bracket 1 (Exhibition)** - Casual, lower power
- **Bracket 2 (Core)** - Typical precon level
- **Bracket 3 (Upgraded)** - Enhanced precons
- **Bracket 4 (Optimized)** - Highly tuned decks

The project's bar is Bracket 3+/4- (in-between labels; see [`data/bracket-philosophy.md`](data/bracket-philosophy.md)); a few decks are still labelled 3.

## Technical Details

- **Frontend:** React 18 + Vite + TypeScript single-page app in `web/`; global CSS with design tokens; no backend
- **Data:** static JSON under `data/`, copied into the build
- **Card Data:** Scryfall (a bulk mirror for the scripts; batched API lookups in the app)
- **Hosting:** Vercel builds the `deploy` branch, which CI fast-forwards from `main` when `web/`, `data/` or `vercel.json` change

## Contributing

Feel free to submit issues or pull requests with additional commander deck guides or improvements to existing ones.

## License

This project is for personal and educational use. Magic: The Gathering is a trademark of Wizards of the Coast. Card data and images are provided via the Scryfall API.

---

*Built with love for the Commander community*
