# MTG Precon Upgrader

A static web application and collection of upgrade guides for Magic: The Gathering Commander preconstructed decks. Built with Commander Brackets format compliance in mind.

## Features

- **Interactive Web Interface** - Browse precon upgrade guides with card hover previews and detailed upgrade paths
- **Multiple Upgrade Tiers** - Choose between midrange and full upgrade paths based on your budget
- **Card Categorization** - Clear organization of cuts, additions, and their strategic purposes
- **Commander Brackets Aware** - All upgrades are designed with the Commander Brackets format in mind
- **Shopping Lists** - Pre-formatted lists ready for deck-building sites

## Quick Start

Simply open `index.html` in your web browser - no build step or server required.

```bash
# Clone the repository
git clone https://github.com/DioPires/mtg-precon-upgrader.git

# Open in browser
open index.html  # macOS
# or
start index.html  # Windows
```

## Project Structure

```
mtg-precon-upgrader/
├── index.html              # Main web application
├── data/
│   ├── index.json          # Precon metadata
│   ├── game-changers.json  # High-impact cards reference
│   └── precons/            # Deck data per precon
│       ├── eldrazi-unbound/
│       ├── endless-punishment/
│       └── necron-dynasties/
└── docs/                   # Markdown upgrade guides
    ├── eldrazi-unbound/
    ├── endless-punishment/
    └── necron-dynasties/
```

## Featured Precons

### Eldrazi Unbound
- **Commander:** Kozilek, the Great Distortion
- **Set:** Modern Horizons 3
- **Colors:** Colorless
- **Strategy:** Colorless ramp into devastating Eldrazi threats

### Endless Punishment
- **Commander:** The Lord of Pain
- **Set:** Duskmourn Commander
- **Colors:** Black/Red
- **Strategy:** Life manipulation and punishing opponents for their actions

### Necron Dynasties
- **Commander:** Imotekh the Stormlord
- **Set:** Warhammer 40,000 Commander
- **Colors:** Mono-Black
- **Strategy:** Artifact recursion and relentless armies of Necron tokens

## Commander Brackets

This project follows the [Commander Brackets](https://mtgcommander.net/index.php/2024-announcements/) system introduced by the Commander Rules Committee. Each upgrade guide considers bracket implications:

- **Bracket 1 (Exhibition)** - Casual, lower power
- **Bracket 2 (Core)** - Typical precon level
- **Bracket 3 (Upgraded)** - Enhanced precons
- **Bracket 4 (Optimized)** - Highly tuned decks

Most upgrades in this project target Bracket 2-3, making decks competitive at casual tables without becoming pubstompers.

## Upgrade Guide Contents

Each precon directory in `docs/` contains:

| File | Description |
|------|-------------|
| `UPGRADE_GUIDE.md` | Comprehensive upgrade strategy and overview |
| `CUTS.md` | Cards to remove with explanations |
| `MIDRANGE_UPGRADE.md` | Budget-friendly upgrade path |
| `FULL_UPGRADE.md` | Complete optimization guide |
| `SHOPPING_LIST.md` | Formatted card lists for purchasing |
| `precon_list.txt` | Original decklist |
| `decklist_midrange.txt` | Midrange upgrade decklist |
| `decklist_full_upgrade.txt` | Full upgrade decklist |

## Technical Details

- **Frontend:** Vanilla HTML, CSS, JavaScript
- **Fonts:** Cinzel (headings), Source Sans 3 (body), Fira Code (card names)
- **Card Images:** Scryfall API integration
- **No Dependencies:** Zero npm packages, just open and use

## Contributing

Feel free to submit issues or pull requests with additional precon upgrade guides or improvements to existing ones.

## License

This project is for personal and educational use. Magic: The Gathering is a trademark of Wizards of the Coast. Card data and images are provided via the Scryfall API.

---

*Built with love for the Commander community*
