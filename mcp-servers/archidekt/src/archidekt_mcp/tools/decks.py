"""Archidekt deck tools — list, publish, sync."""

import json
import os

from ..config import API_BASE, BASE_URL, DATA_DIR, ARCHIDEKT_USERNAME
from ..models import (
    ArchidektDeckSummary,
    ListDecksResponse,
    PublishDeckResult,
    SyncResult,
    SyncAllResponse,
)
from ..services.client import ArchidektClient, ArchidektError, ScryfallError
from ..services.deck_builder import build_deck_payload

_client = ArchidektClient()


def _load_deck_json(deck_id: str) -> dict:
    """Load a deck.json file by deck ID."""
    # Resolve DATA_DIR relative to this package if not absolute
    data_dir = DATA_DIR
    if not os.path.isabs(data_dir):
        data_dir = os.path.normpath(
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "data")
        )

    path = os.path.join(data_dir, "commanders", deck_id, "deck.json")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Deck not found: {path}")
    with open(path) as f:
        return json.load(f)


def _load_index() -> list[dict]:
    """Load data/index.json commander list."""
    data_dir = DATA_DIR
    if not os.path.isabs(data_dir):
        data_dir = os.path.normpath(
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "data")
        )

    path = os.path.join(data_dir, "index.json")
    with open(path) as f:
        return json.load(f).get("commanders", [])


async def list_decks(username: str | None = None) -> ListDecksResponse:
    """List decks on an Archidekt profile."""
    owner = username or ARCHIDEKT_USERNAME
    raw_decks = _client.list_decks(owner)

    decks = []
    for d in raw_decks:
        deck_id = d.get("id", 0)
        decks.append(
            ArchidektDeckSummary(
                id=deck_id,
                name=d.get("name", ""),
                owner=owner,
                format="commander",
                card_count=d.get("size", d.get("cardCount", 0)),
                updated_at=d.get("updatedAt", ""),
                url=f"{BASE_URL}/decks/{deck_id}",
            )
        )

    return ListDecksResponse(username=owner, decks=decks, total=len(decks))


async def publish_deck(
    deck_id: str,
    archidekt_deck_id: int | None = None,
    dry_run: bool = False,
) -> PublishDeckResult:
    """Publish a deck.json to Archidekt (create or update).

    Args:
        deck_id: Local deck ID (e.g., 'titan-convergence').
        archidekt_deck_id: Existing Archidekt deck ID to update. If None, creates new.
        dry_run: If True, resolve cards but don't actually publish.
    """
    deck_data = _load_deck_json(deck_id)
    commander = deck_data.get("commander", "Unknown")

    # Collect all card names from decklist
    card_names = []
    for card in deck_data.get("decklist", []):
        name = card.get("name", "")
        if name:
            card_names.append(name)

    # Also include commander and partner if not in decklist
    if commander and commander not in card_names:
        card_names.append(commander)
    partner = deck_data.get("partner", "")
    if partner and partner not in card_names:
        card_names.append(partner)

    # Resolve all cards via Scryfall
    try:
        resolved = _client.resolve_cards_bulk(card_names)
    except ScryfallError as e:
        return PublishDeckResult(
            deck_id="error",
            name=deck_data.get("name", ""),
            card_count=0,
            commander=commander,
            errors=[str(e)],
        )

    # Build Archidekt payload
    payload, build_errors = build_deck_payload(deck_data, resolved)

    if dry_run:
        return PublishDeckResult(
            deck_id="dry-run",
            name=payload["name"],
            card_count=len(payload["cards"]),
            commander=commander,
            dry_run=True,
            errors=build_errors,
        )

    # Publish to Archidekt
    try:
        if archidekt_deck_id:
            result = _client.update_deck(archidekt_deck_id, payload)
            return PublishDeckResult(
                deck_id=str(archidekt_deck_id),
                name=payload["name"],
                card_count=len(payload["cards"]),
                commander=commander,
                url=f"{BASE_URL}/decks/{archidekt_deck_id}",
                updated=True,
                errors=build_errors,
            )
        else:
            result = _client.create_deck(payload)
            new_id = result.get("id", "unknown")
            return PublishDeckResult(
                deck_id=str(new_id),
                name=payload["name"],
                card_count=len(payload["cards"]),
                commander=commander,
                url=f"{BASE_URL}/decks/{new_id}",
                created=True,
                errors=build_errors,
            )
    except ArchidektError as e:
        return PublishDeckResult(
            deck_id="error",
            name=payload["name"],
            card_count=len(payload["cards"]),
            commander=commander,
            errors=build_errors + [str(e)],
        )


# Map of local deck IDs to known Archidekt deck IDs
KNOWN_ARCHIDEKT_IDS: dict[str, int] = {
    "titan-convergence": 20760135,
    "eternal-agony": 20759936,
    "dark-dominion": 20760109,
    "mutant-multiplication": 20786495,
    "eternal-harvest": 20946261,
}


async def sync_all(dry_run: bool = False) -> SyncAllResponse:
    """Sync all deck.json files to Archidekt.

    Iterates through all commanders in data/index.json and publishes
    each deck to Archidekt. Uses known Archidekt IDs for updates,
    creates new decks for unknown IDs.
    """
    commanders = _load_index()
    results: list[SyncResult] = []
    published = 0
    errors = 0
    skipped = 0

    for cmd in commanders:
        local_id = cmd.get("id", "")
        deck_name = cmd.get("name", "")

        try:
            archidekt_id = KNOWN_ARCHIDEKT_IDS.get(local_id)
            result = await publish_deck(
                deck_id=local_id,
                archidekt_deck_id=archidekt_id,
                dry_run=dry_run,
            )

            if result.errors and result.deck_id == "error":
                results.append(
                    SyncResult(
                        deck_id_local=local_id,
                        deck_name=deck_name,
                        status="error",
                        error="; ".join(result.errors),
                    )
                )
                errors += 1
            elif dry_run:
                results.append(
                    SyncResult(
                        deck_id_local=local_id,
                        deck_name=deck_name,
                        status="dry-run",
                        archidekt_id=str(archidekt_id or "new"),
                    )
                )
                skipped += 1
            else:
                results.append(
                    SyncResult(
                        deck_id_local=local_id,
                        deck_name=deck_name,
                        status="published",
                        archidekt_id=result.deck_id,
                        url=result.url,
                    )
                )
                published += 1

        except Exception as e:
            results.append(
                SyncResult(
                    deck_id_local=local_id,
                    deck_name=deck_name,
                    status="error",
                    error=str(e),
                )
            )
            errors += 1

    return SyncAllResponse(
        results=results,
        total=len(commanders),
        published=published,
        errors=errors,
        skipped=skipped,
    )
