"""Card lookup tools — async wrappers around sync client."""

import asyncio

from ..config import CARD_TTL, KEEP_FIELDS
from ..models import CardResult, SearchResults
from ..services.cache import Cache
from ..services.client import client as _client

_cache = Cache()


def _filter_card(raw: dict) -> dict:
    """Filter raw Scryfall response to KEEP_FIELDS and normalize."""
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


async def card_by_name(name: str, exact: bool = False) -> CardResult:
    """Look up a card by name."""
    cache_key = Cache.make_key("cards/named", {"name": name, "exact": exact})
    cached = _cache.get(cache_key)
    if cached:
        return CardResult(**cached)

    raw = await asyncio.to_thread(_client.card_by_name, name, exact)
    filtered = _filter_card(raw)
    _cache.set(cache_key, filtered, CARD_TTL)
    return CardResult(**filtered)


async def card_by_id(scryfall_id: str) -> CardResult:
    """Look up a card by Scryfall UUID."""
    cache_key = Cache.make_key(f"cards/{scryfall_id}", "")
    cached = _cache.get(cache_key)
    if cached:
        return CardResult(**cached)

    raw = await asyncio.to_thread(_client.card_by_id, scryfall_id)
    filtered = _filter_card(raw)
    _cache.set(cache_key, filtered, CARD_TTL)
    return CardResult(**filtered)


async def search(query: str, order: str = "name", max_results: int = 20) -> SearchResults:
    """Search cards via Scryfall search syntax."""
    cache_key = Cache.make_key("cards/search", {"q": query, "order": order, "max": max_results})
    cached = _cache.get(cache_key)
    if cached:
        return SearchResults(**cached)

    all_cards: list[dict] = []
    page = 1

    while len(all_cards) < max_results:
        raw = await asyncio.to_thread(_client.search, query, order, page)
        for card in raw.get("data", []):
            all_cards.append(_filter_card(card))
            if len(all_cards) >= max_results:
                break
        if not raw.get("has_more"):
            break
        page += 1

    total = raw.get("total_cards", len(all_cards)) if "raw" in dir() else len(all_cards)
    result = SearchResults(
        total_cards=total,
        results=[CardResult(**c) for c in all_cards],
    )
    _cache.set(cache_key, result.model_dump(), CARD_TTL)
    return result
