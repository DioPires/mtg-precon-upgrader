"""Card rulings lookup tool."""

import asyncio

from ..config import RULING_TTL
from ..models import RulingEntry, RulingsResult
from ..services.cache import Cache
from ..services.client import client as _client

_cache = Cache()


async def rulings_lookup(scryfall_id: str, card_name: str = "") -> RulingsResult:
    """Fetch rulings for a card by Scryfall UUID."""
    cache_key = Cache.make_key(f"cards/{scryfall_id}/rulings", "")
    cached = _cache.get(cache_key)
    if cached:
        return RulingsResult(**cached)

    raw = await asyncio.to_thread(_client.rulings, scryfall_id)

    entries = [
        RulingEntry(
            source=r.get("source", ""),
            published_at=r.get("published_at", ""),
            comment=r.get("comment", ""),
        )
        for r in raw.get("data", [])
    ]

    result = RulingsResult(card_name=card_name, rulings=entries)
    _cache.set(cache_key, result.model_dump(), RULING_TTL)
    return result
