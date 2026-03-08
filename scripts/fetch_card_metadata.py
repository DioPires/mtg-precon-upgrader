#!/usr/bin/env python3
"""Fetch card metadata from Scryfall and cache locally.

Reads all deck.json files, collects unique card names, fetches metadata
via Scryfall Collection API, and saves to data/card-metadata.json.
"""

import json
import time
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_FILE = DATA_DIR / "card-metadata.json"
SCRYFALL_COLLECTION_URL = "https://api.scryfall.com/cards/collection"
BATCH_SIZE = 75
RATE_LIMIT_DELAY = 0.1  # 100ms between requests


def collect_card_names() -> set[str]:
    """Collect all unique card names from every deck.json."""
    names = set()

    deck_paths = list(DATA_DIR.glob("commanders/*/deck.json"))

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
        return {
            "type_line": card.get("type_line", "Unknown"),
            "cmc": card.get("cmc", 0),
            "mana_cost": card.get("mana_cost", ""),
            "colors": card.get("colors", []),
            "oracle_text": card.get("oracle_text", ""),
        }
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
                entry = {
                    "type_line": card.get("type_line", "Unknown"),
                    "cmc": card.get("cmc", 0),
                    "mana_cost": card.get("mana_cost", ""),
                    "colors": card.get("colors", []),
                    "oracle_text": card.get("oracle_text", ""),
                }
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


def main():
    print("Collecting card names from deck files...")
    names = collect_card_names()
    print(f"Found {len(names)} unique card names across all decks.\n")

    print("Fetching metadata from Scryfall...")
    metadata = fetch_metadata(sorted(names))
    print(f"\nCached {len(metadata)} cards.")

    missing = names - set(metadata.keys())
    if missing:
        print(f"Missing {len(missing)}: {sorted(missing)}")

    with open(OUTPUT_FILE, "w") as f:
        json.dump(metadata, f, indent=2, sort_keys=True)

    print(f"\nSaved to {OUTPUT_FILE}")
    print(f"File size: {OUTPUT_FILE.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
