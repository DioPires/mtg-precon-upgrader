"""Convert deck.json data to Archidekt API payload format."""

from ..config import DECK_FORMAT_COMMANDER

# Map deck.json card types to Archidekt default categories
TYPE_TO_CATEGORY = {
    "Creature": "Creature",
    "Instant": "Instant",
    "Sorcery": "Sorcery",
    "Enchantment": "Enchantment",
    "Artifact": "Artifact",
    "Planeswalker": "Planeswalker",
    "Land": "Land",
    "Battle": "Battle",
}


def card_category(card_type: str) -> str:
    """Map a deck.json type to an Archidekt category name."""
    for key, val in TYPE_TO_CATEGORY.items():
        if key.lower() in card_type.lower():
            return val
    return "Nonland"


def build_categories(deck_data: dict) -> list[dict]:
    """Build Archidekt categories array from deck data."""
    categories = [
        {
            "name": "Commander",
            "isPremier": True,
            "includedInDeck": True,
            "includedInPrice": True,
        },
    ]

    # Collect unique categories from the decklist
    seen = {"Commander"}
    for card in deck_data.get("decklist", []):
        cat = card_category(card.get("type", ""))
        if cat not in seen:
            seen.add(cat)
            categories.append(
                {
                    "name": cat,
                    "isPremier": False,
                    "includedInDeck": True,
                    "includedInPrice": True,
                }
            )

    # Always include Maybeboard
    categories.append(
        {
            "name": "Maybeboard",
            "isPremier": False,
            "includedInDeck": False,
            "includedInPrice": False,
        }
    )

    return categories


def build_card_entry(
    card_name: str,
    card_type: str,
    scryfall_id: str,
    is_commander: bool = False,
    quantity: int = 1,
) -> dict:
    """Build a single Archidekt card entry."""
    category = "Commander" if is_commander else card_category(card_type)
    return {
        "quantity": quantity,
        "modifier": "Normal",
        "categories": [category],
        "companion": False,
        "flippedDefault": False,
        "card": {"uid": scryfall_id},
    }


def build_deck_payload(
    deck_data: dict,
    resolved_cards: dict[str, dict],
) -> tuple[dict, list[str]]:
    """Build full Archidekt deck payload from deck.json and resolved Scryfall cards.

    Args:
        deck_data: Parsed deck.json data.
        resolved_cards: Map of card name -> Scryfall card data.

    Returns:
        Tuple of (payload dict, list of error messages).
    """
    errors: list[str] = []

    commander_name = deck_data.get("commander", "")
    partner_name = deck_data.get("partner", "")
    commanders = {commander_name}
    if partner_name:
        commanders.add(partner_name)

    cards = []
    for card in deck_data.get("decklist", []):
        name = card.get("name", "")
        card_type = card.get("type", "")
        quantity = card.get("quantity", 1)

        scryfall_data = resolved_cards.get(name, {})
        if "error" in scryfall_data or not scryfall_data:
            errors.append(f"Could not resolve: {name}")
            continue

        scryfall_id = scryfall_data.get("id", "")
        if not scryfall_id:
            errors.append(f"No Scryfall ID for: {name}")
            continue

        is_commander = name in commanders
        entry = build_card_entry(
            name, card_type, scryfall_id, is_commander, quantity
        )
        cards.append(entry)

    # Add commander(s) if not already in decklist
    decklist_names = {c.get("name", "") for c in deck_data.get("decklist", [])}
    for cmd_name in commanders:
        if cmd_name and cmd_name not in decklist_names:
            scryfall_data = resolved_cards.get(cmd_name, {})
            if "error" in scryfall_data or not scryfall_data:
                errors.append(f"Could not resolve commander: {cmd_name}")
                continue
            scryfall_id = scryfall_data.get("id", "")
            if not scryfall_id:
                errors.append(f"No Scryfall ID for commander: {cmd_name}")
                continue
            # Infer type from Scryfall data
            type_line = scryfall_data.get("type_line", "Creature")
            entry = build_card_entry(cmd_name, type_line, scryfall_id, True, 1)
            cards.append(entry)

    deck_name = deck_data.get("name", "Untitled Deck")

    payload = {
        "name": deck_name,
        "deckFormat": DECK_FORMAT_COMMANDER,
        "description": _build_description(deck_data),
        "cards": cards,
        "categories": build_categories(deck_data),
    }

    return payload, errors


def _build_description(deck_data: dict) -> str:
    """Build Archidekt deck description from deck.json metadata."""
    parts = []
    subtitle = deck_data.get("subtitle", "")
    if subtitle:
        parts.append(f"*{subtitle}*")

    overview = deck_data.get("guideContent", {}).get("strategyOverview", "")
    if overview:
        parts.append(overview)

    bracket = deck_data.get("bracket", "")
    if bracket:
        parts.append(f"Bracket: {bracket}")

    parts.append("Built with The Grimoire")
    return "\n\n".join(parts)
