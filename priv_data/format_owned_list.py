#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from urllib import error, request

SCRIPT_DIR = Path(__file__).resolve().parent
OWNED_CSV = SCRIPT_DIR / "Owned.csv"
FORMATTED_CSV = SCRIPT_DIR / "owned_formatted.csv"
SCRYFALL_COLLECTION_URL = "https://api.scryfall.com/cards/collection"
SCRYFALL_BATCH_SIZE = 75
FORMATTED_FIELDNAMES = [
    "name",
    "quantity",
    "scryfall_id",
    "type_line",
    "mana_cost",
    "oracle_text",
]
FORMATTED_METADATA_HEADERS = ("type_line", "mana_cost", "oracle_text")


def build_header_map(fieldnames: list[str] | None) -> dict[str, str]:
    return {(field or "").strip().lower(): field for field in fieldnames or [] if field}


def get_owned_cards(filename: Path) -> dict[str, dict[str, str | int]]:
    with filename.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        header_map = build_header_map(reader.fieldnames)
        name_key = header_map.get("name")
        quantity_key = header_map.get("quantity")
        scryfall_id_key = header_map.get("scryfall id")
        if not name_key or not quantity_key:
            raise ValueError(f"{filename} is missing Name/Quantity columns")

        cards: dict[str, dict[str, str | int]] = {}
        for row in reader:
            name = (row.get(name_key) or "").strip()
            if not name:
                continue

            quantity_raw = (row.get(quantity_key) or "").strip()
            try:
                quantity = int(quantity_raw or "1")
            except ValueError:
                quantity = 1

            if name not in cards:
                cards[name] = {
                    "name": name,
                    "quantity": 0,
                    "scryfall_id": "",
                }

            cards[name]["quantity"] += quantity
            if scryfall_id_key and not cards[name]["scryfall_id"]:
                cards[name]["scryfall_id"] = (row.get(scryfall_id_key) or "").strip()

    print(f"Computed {len(cards)} unique owned cards from {filename.name}.")
    return cards


def load_cached_metadata(filename: Path) -> dict[str, dict[str, str]]:
    if not filename.exists():
        return {}

    with filename.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        header_map = build_header_map(reader.fieldnames)
        if "name" not in header_map:
            return {}
        if not all(field in header_map for field in FORMATTED_METADATA_HEADERS):
            return {}

        cache: dict[str, dict[str, str]] = {}
        for row in reader:
            name = (row.get(header_map["name"]) or "").strip()
            if not name:
                continue
            cache[name] = {
                "scryfall_id": (row.get(header_map.get("scryfall_id", "")) or "").strip()
                if header_map.get("scryfall_id")
                else "",
                "type_line": (row.get(header_map["type_line"]) or "").strip(),
                "mana_cost": (row.get(header_map["mana_cost"]) or "").strip(),
                "oracle_text": (row.get(header_map["oracle_text"]) or "").strip(),
            }

    return cache


def join_card_faces(card: dict, field: str, separator: str) -> str:
    parts = []
    for face in card.get("card_faces") or []:
        value = (face.get(field) or "").strip()
        if value:
            parts.append(value)
    return separator.join(parts)


def normalize_scryfall_card(card: dict) -> dict[str, str]:
    type_line = (card.get("type_line") or "").strip() or join_card_faces(card, "type_line", " // ")
    mana_cost = (card.get("mana_cost") or "").strip() or join_card_faces(card, "mana_cost", " // ")
    oracle_text = (card.get("oracle_text") or "").strip() or join_card_faces(card, "oracle_text", "\n//\n")
    return {
        "scryfall_id": (card.get("id") or "").strip(),
        "type_line": type_line,
        "mana_cost": mana_cost,
        "oracle_text": oracle_text,
    }


def post_scryfall_collection(identifiers: list[dict[str, str]]) -> dict:
    payload = json.dumps({"identifiers": identifiers}).encode("utf-8")
    req = request.Request(
        SCRYFALL_COLLECTION_URL,
        data=payload,
        method="POST",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "mtg-precon-upgrader/1.0",
        },
    )
    with request.urlopen(req) as response:
        return json.load(response)


def fetch_missing_metadata(cards_to_fetch: list[dict[str, str | int]]) -> tuple[dict[str, dict[str, str]], list[str]]:
    fetched: dict[str, dict[str, str]] = {}
    missing_names: list[str] = []

    for index in range(0, len(cards_to_fetch), SCRYFALL_BATCH_SIZE):
        batch = cards_to_fetch[index:index + SCRYFALL_BATCH_SIZE]
        identifiers = []
        for card in batch:
            scryfall_id = str(card.get("scryfall_id") or "").strip()
            if scryfall_id:
                identifiers.append({"id": scryfall_id})
            else:
                identifiers.append({"name": str(card["name"])})

        try:
            response = post_scryfall_collection(identifiers)
        except error.HTTPError as exc:
            raise RuntimeError(f"Scryfall request failed with HTTP {exc.code}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"Could not reach Scryfall: {exc.reason}") from exc

        by_id = {
            (entry.get("id") or "").strip(): entry
            for entry in response.get("data", [])
            if entry.get("id")
        }
        by_name = {
            (entry.get("name") or "").strip(): entry
            for entry in response.get("data", [])
            if entry.get("name")
        }

        for card in batch:
            name = str(card["name"])
            scryfall_id = str(card.get("scryfall_id") or "").strip()
            match = by_id.get(scryfall_id) if scryfall_id else None
            if match is None:
                match = by_name.get(name)
            if match is None:
                missing_names.append(name)
                continue
            fetched[name] = normalize_scryfall_card(match)

    return fetched, missing_names


def write_owned_cards_to_file(
    filename: Path,
    owned_cards: dict[str, dict[str, str | int]],
    metadata_cache: dict[str, dict[str, str]],
):
    with filename.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FORMATTED_FIELDNAMES)
        writer.writeheader()
        for card in owned_cards.values():
            name = str(card["name"])
            metadata = metadata_cache.get(name, {})
            writer.writerow(
                {
                    "name": name,
                    "quantity": int(card["quantity"]),
                    "scryfall_id": str(card.get("scryfall_id") or metadata.get("scryfall_id") or ""),
                    "type_line": metadata.get("type_line", ""),
                    "mana_cost": metadata.get("mana_cost", ""),
                    "oracle_text": metadata.get("oracle_text", ""),
                }
            )


def main():
    owned_cards = get_owned_cards(OWNED_CSV)
    metadata_cache = load_cached_metadata(FORMATTED_CSV)

    cards_to_fetch = []
    for card in owned_cards.values():
        cached = metadata_cache.get(str(card["name"]))
        if cached and cached.get("type_line"):
            continue
        cards_to_fetch.append(card)

    fetched_metadata, missing_names = fetch_missing_metadata(cards_to_fetch) if cards_to_fetch else ({}, [])
    metadata_cache.update(fetched_metadata)
    write_owned_cards_to_file(FORMATTED_CSV, owned_cards, metadata_cache)

    reused_count = len(owned_cards) - len(cards_to_fetch)
    print(f"Reused cached metadata for {reused_count} cards from {FORMATTED_CSV.name}.")
    print(f"Fetched metadata for {len(fetched_metadata)} new cards from Scryfall.")
    print(f"Wrote {len(owned_cards)} rows to {FORMATTED_CSV.name}.")

    if missing_names:
        print(
            "Warning: no Scryfall metadata found for "
            + ", ".join(sorted(missing_names)),
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
