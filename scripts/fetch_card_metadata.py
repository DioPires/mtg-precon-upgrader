#!/usr/bin/env python3
"""Fetch card metadata from Scryfall and cache locally.

Reads all deck.json files, collects unique card names, fetches metadata
via Scryfall Collection API, and saves to data/card-metadata.json.
"""

import argparse
import json
import time
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_FILE = DATA_DIR / "card-metadata.json"
COMMANDERS_DIR = DATA_DIR / "commanders"
SCRYFALL_COLLECTION_URL = "https://api.scryfall.com/cards/collection"
BATCH_SIZE = 75
RATE_LIMIT_DELAY = 0.1  # 100ms between requests


def available_deck_ids() -> list[str]:
    """Sorted deck ids discovered from commander deck data."""
    return sorted(path.parent.name for path in COMMANDERS_DIR.glob("*/deck.json"))


def collect_card_names(deck_ids: list[str] | None = None) -> set[str]:
    """Collect unique card names from selected deck.json files."""
    names = set()
    if deck_ids:
        deck_paths = [COMMANDERS_DIR / deck_id / "deck.json" for deck_id in deck_ids]
    else:
        deck_paths = list(COMMANDERS_DIR.glob("*/deck.json"))

    for path in deck_paths:
        with open(path) as f:
            deck = json.load(f)

        # Commander(s)
        if deck.get("commander"):
            names.add(deck["commander"])
        if deck.get("partner"):
            names.add(deck["partner"])

        # Adds (notable/highlighted cards)
        for card in deck.get("adds", []):
            names.add(card["name"])

        # Full decklist
        for card in deck.get("decklist", []):
            names.add(card["name"])

    return names


def _entry_from_card(card: dict) -> dict:
    """Build a metadata entry from a Scryfall card object.

    Transform/modal DFC layouts carry mana_cost, oracle_text, and colors on
    card_faces, not top-level — fill empty fields from the FRONT face (the
    cast face; matches the project's MDFC handling policy). type_line and cmc
    stay top-level ("A // B", front-face cmc) so land/type checks still see
    both faces.
    """
    layout = card.get("layout", "normal")
    entry = {
        "type_line": card.get("type_line", "Unknown"),
        "cmc": card.get("cmc", 0),
        "mana_cost": card.get("mana_cost", ""),
        "colors": card.get("colors", []),
        "oracle_text": card.get("oracle_text", ""),
    }
    faces = card.get("card_faces") or []
    if faces:
        front = faces[0]
        if not entry["mana_cost"]:
            entry["mana_cost"] = front.get("mana_cost", "")
        if not entry["oracle_text"]:
            entry["oracle_text"] = front.get("oracle_text", "")
        if not entry["colors"]:
            entry["colors"] = front.get("colors", [])
    if layout in ("modal_dfc", "transform"):
        entry["layout"] = layout
    return entry


def _fetch_single(name: str) -> dict | None:
    """Fetch a single card by name via Scryfall named search."""
    import urllib.parse
    url = f"https://api.scryfall.com/cards/named?exact={urllib.parse.quote(name)}"
    req = urllib.request.Request(url, headers={
        "Accept": "application/json",
        "User-Agent": "MTGPreconUpgrader/1.0",
    })
    try:
        with urllib.request.urlopen(req) as resp:
            card = json.loads(resp.read())
        return _entry_from_card(card)
    except Exception:
        return None


def fetch_metadata(names: list[str]) -> dict:
    """Fetch metadata from Scryfall Collection API in batches of 75."""
    metadata = {}
    batches = [names[i : i + BATCH_SIZE] for i in range(0, len(names), BATCH_SIZE)]

    for i, batch in enumerate(batches):
        print(f"  Fetching batch {i + 1}/{len(batches)} ({len(batch)} cards)...")

        body = json.dumps(
            {"identifiers": [{"name": name} for name in batch]}
        ).encode()

        req = urllib.request.Request(
            SCRYFALL_COLLECTION_URL,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "MTGPreconUpgrader/1.0",
            },
        )

        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read())

            for card in data.get("data", []):
                entry = _entry_from_card(card)
                metadata[card["name"]] = entry
                # DFC cards: also cache by front face name
                if " // " in card["name"]:
                    front = card["name"].split(" // ")[0]
                    metadata[front] = entry

            not_found = data.get("not_found", [])
            if not_found:
                nf_names = [nf.get("name", str(nf)) for nf in not_found]
                print(f"    Not found: {nf_names}")
                # Retry not-found cards by front face name (for Room/split cards)
                for nf_name in nf_names:
                    if " // " in nf_name:
                        front = nf_name.split(" // ")[0]
                        retry = _fetch_single(front)
                        if retry:
                            metadata[nf_name] = retry
                            metadata[front] = retry

        except Exception as e:
            print(f"    Batch {i + 1} failed: {e}")

        if i < len(batches) - 1:
            time.sleep(RATE_LIMIT_DELAY)

    return metadata


def load_existing_metadata(output_file: Path) -> dict:
    """Load existing metadata cache if present."""
    if not output_file.exists():
        return {}
    with open(output_file) as f:
        return json.load(f)


def main():
    deck_ids = available_deck_ids()

    parser = argparse.ArgumentParser(
        description="Fetch Scryfall card metadata for commander decks")
    parser.add_argument(
        "--deck",
        dest="deck_ids",
        action="append",
        choices=deck_ids,
        help="Refresh metadata for only the specified deck id. Repeat to select multiple decks.",
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        default=OUTPUT_FILE,
        help=f"Metadata output path (default: {OUTPUT_FILE})",
    )
    args = parser.parse_args()

    print("Collecting card names from deck files...")
    names = collect_card_names(args.deck_ids)
    if args.deck_ids:
        print(f"Found {len(names)} unique card names across {len(args.deck_ids)} selected deck(s).\n")
    else:
        print(f"Found {len(names)} unique card names across all decks.\n")

    print("Fetching metadata from Scryfall...")
    metadata = fetch_metadata(sorted(names))
    print(f"\nCached {len(metadata)} cards.")

    missing = names - set(metadata.keys())
    if missing:
        print(f"Missing {len(missing)}: {sorted(missing)}")

    output_file = args.output_file
    if args.deck_ids:
        existing = load_existing_metadata(output_file)
        if existing:
            existing.update(metadata)
            metadata = existing
            print(f"Merged subset refresh into existing cache: {len(metadata)} cards total.")
        else:
            print(f"Created subset cache: {len(metadata)} cards total.")

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(metadata, f, indent=2, sort_keys=True)

    print(f"\nSaved to {output_file}")
    print(f"File size: {output_file.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
