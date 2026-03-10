"""Bulk collection lookup tool."""

import asyncio

from ..config import CARD_TTL, COLLECTION_BATCH_SIZE
from ..models import CardResult, CollectionResult
from ..services.cache import Cache
from ..services.client import ScryfallClient

_client = ScryfallClient()
_cache = Cache()


def _filter_card(raw: dict) -> dict:
    """Filter raw Scryfall response to kept fields."""
    return {
        "name": raw.get("name", ""),
        "mana_cost": raw.get("mana_cost", ""),
        "cmc": raw.get("cmc", 0),
        "type_line": raw.get("type_line", ""),
        "oracle_text": raw.get("oracle_text", ""),
        "colors": raw.get("colors", []),
        "color_identity": raw.get("color_identity", []),
        "power": raw.get("power"),
        "toughness": raw.get("toughness"),
        "set_code": raw.get("set", ""),
        "image_uris": raw.get("image_uris"),
        "scryfall_uri": raw.get("scryfall_uri", ""),
        "legalities": raw.get("legalities", {}),
        "keywords": raw.get("keywords", []),
        "card_faces": raw.get("card_faces"),
        "scryfall_id": raw.get("id", ""),
    }


async def collection_lookup(card_names: list[str]) -> CollectionResult:
    """Look up multiple cards by name in batches of 75."""
    found: list[CardResult] = []
    not_found: list[str] = []

    # Check cache first, collect misses
    uncached_names: list[str] = []
    for name in card_names:
        cache_key = Cache.make_key("cards/named", {"name": name, "exact": True})
        cached = _cache.get(cache_key)
        if cached:
            found.append(CardResult(**cached))
        else:
            uncached_names.append(name)

    # Batch uncached names
    batches = [
        uncached_names[i : i + COLLECTION_BATCH_SIZE]
        for i in range(0, len(uncached_names), COLLECTION_BATCH_SIZE)
    ]

    for batch in batches:
        identifiers = [{"name": name} for name in batch]
        raw = await asyncio.to_thread(_client.collection, identifiers)

        batch_found_names = set()
        for card in raw.get("data", []):
            filtered = _filter_card(card)
            card_result = CardResult(**filtered)
            found.append(card_result)
            batch_found_names.add(card["name"])

            # Cache individual cards
            cache_key = Cache.make_key("cards/named", {"name": card["name"], "exact": True})
            _cache.set(cache_key, filtered, CARD_TTL)

            # Also cache front face name for DFC
            if " // " in card["name"]:
                front = card["name"].split(" // ")[0]
                front_key = Cache.make_key("cards/named", {"name": front, "exact": True})
                _cache.set(front_key, filtered, CARD_TTL)

        for nf in raw.get("not_found", []):
            nf_name = nf.get("name", str(nf))
            not_found.append(nf_name)

    return CollectionResult(found=found, not_found=not_found)
