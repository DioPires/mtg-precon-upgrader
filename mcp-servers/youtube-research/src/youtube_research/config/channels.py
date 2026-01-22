"""Curated MTG YouTube channels for research."""

from typing import TypedDict


class Channel(TypedDict):
    """Channel configuration."""
    handle: str
    name: str
    channel_id: str | None
    specialty: list[str]


CURATED_CHANNELS: list[Channel] = [
    {
        "handle": "@commandzone",
        "name": "The Command Zone",
        "channel_id": "UCLsiaNUb42gRAP7ewbJ0ecQ",
        "specialty": ["deck_techs", "upgrade_guides", "gameplay"],
    },
    {
        "handle": "@EDHRECast",
        "name": "EDHRECast",
        "channel_id": "UCns4i09wJKuPgIGhvVKd0iA",
        "specialty": ["data_analysis", "recommendations", "deck_building"],
    },
    {
        "handle": "@NitpickingNerds",
        "name": "Nitpicking Nerds",
        "channel_id": "UCrwOIvg-wjYD_g-HzNxUeCA",
        "specialty": ["upgrade_guides", "budget", "optimization"],
    },
    {
        "handle": "@TolarianCommunityCollege",
        "name": "Tolarian Community College",
        "channel_id": "UC7-hR5EfgpM6oHfiGDkxfMA",
        "specialty": ["reviews", "deck_building", "tutorials"],
    },
    {
        "handle": "@MTGGoldfish",
        "name": "MTGGoldfish",
        "channel_id": "UCZAZTSd0xnor7hJFmINIBIw",
        "specialty": ["budget", "meta_analysis", "deck_techs"],
    },
    {
        "handle": "@PlayingWithPowerMTG",
        "name": "Playing With Power MTG",
        "channel_id": "UCum8N4KUUC0l_NK_mybvilg",
        "specialty": ["cedh", "competitive", "gameplay"],
    },
    {
        "handle": "@MTGMuddstah",
        "name": "MTGMuddstah",
        "channel_id": "UCG8Yi6I_XYjYtvFgOleqYxg",
        "specialty": ["gameplay", "casual", "variety"],
    },
    {
        "handle": "@IHateYourDeck",
        "name": "I Hate Your Deck",
        "channel_id": "UC-w5MNByr4SNy3z2232sj0g",
        "specialty": ["gameplay", "cedh", "high_power"],
    },
]


def get_channel_by_handle(handle: str) -> Channel | None:
    """Get channel configuration by handle."""
    # Normalize handle (add @ if missing)
    if not handle.startswith("@"):
        handle = f"@{handle}"

    for channel in CURATED_CHANNELS:
        if channel["handle"].lower() == handle.lower():
            return channel
    return None


def get_all_channel_handles() -> list[str]:
    """Get list of all curated channel handles."""
    return [channel["handle"] for channel in CURATED_CHANNELS]
