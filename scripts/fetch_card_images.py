#!/usr/bin/env python3
"""Fetch card images from Scryfall and store locally.

Reads all deck.json files, collects unique card names, fetches image URIs
via Scryfall Collection API, downloads normal and art_crop variants.
"""

import json
import re
import time
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
IMAGES_DIR = DATA_DIR / "images" / "cards"
COMMANDERS_DIR = DATA_DIR / "commanders"
SCRYFALL_COLLECTION_URL = "https://api.scryfall.com/cards/collection"
BATCH_SIZE = 75
RATE_LIMIT_DELAY = 0.1  # 100ms between collection API requests
DOWNLOAD_DELAY = 0.075  # 75ms between image downloads
VARIANTS = ["normal", "art_crop"]


def sanitize_card_name(name: str) -> str:
    """Sanitize card name for use as filename. Must match JS sanitizeCardName()."""
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def collect_card_names() -> set[str]:
    """Collect unique card names from all deck.json files."""
    names = set()
    for path in COMMANDERS_DIR.glob("*/deck.json"):
        with open(path) as f:
            deck = json.load(f)
        if deck.get("commander"):
            names.add(deck["commander"])
        if deck.get("partnerCommander"):
            names.add(deck["partnerCommander"])
        if deck.get("partner"):
            names.add(deck["partner"])
        for card in deck.get("adds", []):
            names.add(card["name"])
        for card in deck.get("decklist", []):
            names.add(card["name"])
        for syn in deck.get("synergies", []):
            for card in syn.get("cards", []):
                names.add(card)
    return names


def fetch_image_uris(names: list[str]) -> dict[str, dict]:
    """Fetch image URIs from Scryfall Collection API in batches of 75."""
    uris = {}
    batches = [names[i : i + BATCH_SIZE] for i in range(0, len(names), BATCH_SIZE)]

    for i, batch in enumerate(batches):
        print(f"  Fetching URIs batch {i + 1}/{len(batches)} ({len(batch)} cards)...")
        body = json.dumps({"identifiers": [{"name": name} for name in batch]}).encode()
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
                card_name = card["name"]
                if "image_uris" in card:
                    uris[card_name] = card["image_uris"]
                elif "card_faces" in card and card["card_faces"]:
                    uris[card_name] = card["card_faces"][0].get("image_uris", {})
                # Also map front face name for DFCs
                if " // " in card_name:
                    front = card_name.split(" // ")[0]
                    uris[front] = uris.get(card_name, {})

            not_found = data.get("not_found", [])
            if not_found:
                nf_names = [nf.get("name", str(nf)) for nf in not_found]
                print(f"    Not found: {nf_names}")

        except Exception as e:
            print(f"    Batch {i + 1} failed: {e}")

        if i < len(batches) - 1:
            time.sleep(RATE_LIMIT_DELAY)

    return uris


def download_image(url: str, dest: Path) -> bool:
    """Download an image from URL to dest path."""
    req = urllib.request.Request(url, headers={"User-Agent": "MTGPreconUpgrader/1.0"})
    try:
        with urllib.request.urlopen(req) as resp:
            dest.write_bytes(resp.read())
        return True
    except Exception as e:
        print(f"    Failed: {dest.name} — {e}")
        return False


def main():
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    print("Collecting card names from deck files...")
    names = collect_card_names()
    print(f"Found {len(names)} unique card names.\n")

    # Check for sanitized name collisions
    seen: dict[str, str] = {}
    for name in sorted(names):
        sanitized = sanitize_card_name(name)
        if sanitized in seen:
            print(f"  WARNING: collision! '{name}' and '{seen[sanitized]}' -> '{sanitized}'")
        seen[sanitized] = name

    print("Fetching image URIs from Scryfall...")
    uris = fetch_image_uris(sorted(names))
    print(f"Got URIs for {len(uris)} cards.\n")

    downloaded = 0
    skipped = 0
    failed = 0
    total = len(names) * len(VARIANTS)

    print(f"Downloading images ({total} files)...")
    for name in sorted(names):
        card_uris = uris.get(name)
        if not card_uris and " // " in name:
            card_uris = uris.get(name.split(" // ")[0])
        if not card_uris:
            print(f"  No URIs for: {name}")
            failed += len(VARIANTS)
            continue

        sanitized = sanitize_card_name(name)
        for variant in VARIANTS:
            dest = IMAGES_DIR / f"{sanitized}-{variant}.jpg"

            if dest.exists() and dest.stat().st_size > 0:
                skipped += 1
                continue

            url = card_uris.get(variant)
            if not url:
                print(f"  No {variant} URI for: {name}")
                failed += 1
                continue

            if download_image(url, dest):
                downloaded += 1
            else:
                failed += 1

            time.sleep(DOWNLOAD_DELAY)

    print(f"\nDone! Downloaded: {downloaded}, Skipped: {skipped}, Failed: {failed}")
    print(f"Images dir: {IMAGES_DIR}")

    total_size = sum(f.stat().st_size for f in IMAGES_DIR.iterdir() if f.is_file())
    print(f"Total size: {total_size / (1024 * 1024):.1f} MB")


if __name__ == "__main__":
    main()
