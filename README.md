# MTG Precon Upgrader

A static web application showcasing three custom-built Magic: The Gathering Commander decks. Built with Commander Brackets format compliance in mind.

## Features

- **Interactive Web Interface** - Browse commander deck guides with card hover previews
- **Card Categorization** - Clear organization of additions, synergies, and their strategic purposes
- **Commander Brackets Aware** - All decks are designed with the Commander Brackets format in mind
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
│   ├── index.json          # Deck catalog
│   ├── game-changers.json  # High-impact cards reference
│   └── commanders/         # Deck data per commander
│       ├── titan-convergence/
│       ├── eternal-agony/
│       ├── dark-dominion/
│       ├── mutant-multiplication/
│       └── ...
└── scripts/                # Mana simulation scripts
```

## Featured Decks

### Titan Convergence
- **Commander:** Zhulodok, Void Gorger
- **Colors:** Colorless
- **Strategy:** Eldrazi Cascade -- ramp into high-cost Eldrazi with double cascade triggers
- **Bracket:** 4

### Eternal Agony
- **Commander:** The Lord of Pain
- **Colors:** Black/Red
- **Strategy:** Group Slug -- life manipulation and punishing opponents for their actions
- **Bracket:** 4

### Dark Dominion
- **Commander:** Sauron, the Dark Lord
- **Colors:** Blue/Black/Red
- **Strategy:** Amass / Orc Tribal -- build an army of Orcs and overwhelm opponents
- **Bracket:** 4

## Commander Brackets

This project follows the [Commander Brackets](https://mtgcommander.net/index.php/2024-announcements/) system introduced by the Commander Rules Committee:

- **Bracket 1 (Exhibition)** - Casual, lower power
- **Bracket 2 (Core)** - Typical precon level
- **Bracket 3 (Upgraded)** - Enhanced precons
- **Bracket 4 (Optimized)** - Highly tuned decks

All three decks in this project are Bracket 4.

## Technical Details

- **Frontend:** Vanilla HTML, CSS, JavaScript
- **Fonts:** Cinzel (headings), Source Sans 3 (body), Fira Code (card names)
- **Card Images:** Scryfall API integration
- **No Dependencies:** Zero npm packages, just open and use

## Contributing

Feel free to submit issues or pull requests with additional commander deck guides or improvements to existing ones.

## License

This project is for personal and educational use. Magic: The Gathering is a trademark of Wizards of the Coast. Card data and images are provided via the Scryfall API.

---

*Built with love for the Commander community*
