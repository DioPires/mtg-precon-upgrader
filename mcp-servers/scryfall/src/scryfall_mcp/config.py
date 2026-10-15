"""Scryfall MCP configuration constants."""

BASE_URL = "https://api.scryfall.com"
USER_AGENT = "MTGPreconUpgrader-MCP/1.0"
CARD_TTL = 86400  # 24 hours
RULING_TTL = 604800  # 7 days
COLLECTION_BATCH_SIZE = 75

KEEP_FIELDS = {
    "name",
    "mana_cost",
    "cmc",
    "type_line",
    "oracle_text",
    "colors",
    "color_identity",
    "power",
    "toughness",
    "set",
    "image_uris",
    "scryfall_uri",
    "legalities",
    "keywords",
    "card_faces",
    "id",
}
