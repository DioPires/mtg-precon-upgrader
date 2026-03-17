"""Combo lookup tool — async wrapper around sync client."""

import asyncio

from ..config import COMBO_TTL
from ..models import (
    AlmostIncludedResult,
    CardInCombo,
    ComboResult,
    FindCombosResponse,
    TemplateRequirement,
)
from ..services.cache import Cache
from ..services.client import SpellbookClient

_client = SpellbookClient()
_cache = Cache()

COMBO_URL_BASE = "https://commanderspellbook.com/combo"


def _parse_combo(raw: dict) -> ComboResult:
    """Parse a raw combo object into a ComboResult."""
    cards = []
    for use in raw.get("uses", []):
        card_data = use.get("card", {})
        cards.append(
            CardInCombo(
                name=card_data.get("name", ""),
                quantity=use.get("quantity", 1),
                zone_locations=use.get("zoneLocations", []),
                battlefield_card_state=use.get("battlefieldCardState", ""),
                must_be_commander=use.get("mustBeCommander", False),
            )
        )

    requires = []
    for req in raw.get("requires", []):
        tmpl = req.get("template", {})
        requires.append(
            TemplateRequirement(
                name=tmpl.get("name", ""),
                scryfall_query=tmpl.get("scryfallQuery", ""),
                zone_locations=req.get("zoneLocations", []),
            )
        )

    produces = [p["feature"]["name"] for p in raw.get("produces", []) if p.get("feature")]

    combo_id = raw.get("id", "")
    return ComboResult(
        id=combo_id,
        url=f"{COMBO_URL_BASE}/{combo_id}/",
        status=raw.get("status", "OK"),
        identity=raw.get("identity", ""),
        bracket_tag=raw.get("bracketTag", ""),
        cards=cards,
        requires=requires,
        produces=produces,
        description=raw.get("description", ""),
        mana_needed=raw.get("manaNeeded", ""),
        easy_prerequisites=raw.get("easyPrerequisites", ""),
        notable_prerequisites=raw.get("notablePrerequisites", ""),
        notes=raw.get("notes", ""),
    )


def _compute_missing(combo: ComboResult, decklist_lower: set[str]) -> tuple[list[str], list[str]]:
    """Compute missing cards and templates for an almost-included combo.

    Templates are always reported as missing because the API's almostIncluded
    combos include generic requirements (e.g., "Persist Creature") that can't
    be matched against specific card names in the decklist.
    """
    missing_cards = [
        card.name for card in combo.cards if card.name.lower() not in decklist_lower
    ]
    missing_templates = [req.name for req in combo.requires]
    return missing_cards, missing_templates


async def find_combos(decklist: list[str]) -> FindCombosResponse:
    """Find combos for a decklist via Commander Spellbook API."""
    if not decklist:
        return FindCombosResponse(identity="", included=[], almost_included=[])

    cache_key = Cache.make_key(decklist)
    cached = _cache.get(cache_key)
    if cached:
        return FindCombosResponse(**cached)

    raw = await asyncio.to_thread(_client.find_my_combos, decklist)
    results = raw.get("results", {})

    identity = results.get("identity", "")
    decklist_lower = {name.strip().lower() for name in decklist}

    included = [_parse_combo(c) for c in results.get("included", [])]

    almost_included = []
    for raw_combo in results.get("almostIncluded", []):
        combo = _parse_combo(raw_combo)
        missing_cards, missing_templates = _compute_missing(combo, decklist_lower)
        almost_included.append(
            AlmostIncludedResult(
                combo=combo,
                missing_cards=missing_cards,
                missing_templates=missing_templates,
            )
        )

    response = FindCombosResponse(
        identity=identity,
        included=included,
        almost_included=almost_included,
    )
    _cache.set(cache_key, response.model_dump(), COMBO_TTL)
    return response
