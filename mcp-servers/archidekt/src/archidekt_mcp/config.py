"""Archidekt MCP configuration constants."""

import os

BASE_URL = "https://archidekt.com"
API_BASE = f"{BASE_URL}/api"
SCRYFALL_API = "https://api.scryfall.com"
USER_AGENT = "TheGrimoire-MCP/1.0"
RATE_LIMIT_MS = 100
SCRYFALL_RATE_LIMIT_MS = 75

ARCHIDEKT_USERNAME = os.environ.get("ARCHIDEKT_USERNAME", "pirex")
ARCHIDEKT_AUTH_TOKEN = os.environ.get("ARCHIDEKT_AUTH_TOKEN", "")

DATA_DIR = os.environ.get(
    "GRIMOIRE_DATA_DIR",
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "data"),
)

DECK_FORMAT_COMMANDER = 3
