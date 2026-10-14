#!/usr/bin/env python3
"""Fetch card images from Scryfall and store locally.

Reads all deck.json files, collects unique card names, fetches image URIs
via Scryfall Collection API, downloads normal and art_crop variants.

Every request to api.scryfall.com goes through scryfall_api, which keeps
Scryfall's rate limit. A 429 or a failed batch ends the run with exit code 1.
A batch holds the front face of a ``//`` name: Scryfall does not find the full
name (DEC-1076).
"""

import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import scryfall_api  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
IMAGES_DIR = DATA_DIR / "images" / "cards"
COMMANDERS_DIR = DATA_DIR / "commanders"
BATCH_SIZE = 75
DOWNLOAD_DELAY = 0.075  # 75ms between image downloads (cards.scryfall.io has no rate limit)
MAX_RETRIES = 5
INITIAL_BACKOFF = 1.0  # seconds
VARIANTS = ["normal", "art_crop"]


def request_with_retry(send, label: str = "") -> bytes:
    """Run ``send()`` with exponential backoff on 5xx errors and network errors.

    A timeout inside ``read()`` raises TimeoutError, not URLError; it counts as
    a network error. A 429 is never retried: it raises
    scryfall_api.ScryfallRateLimited.
    """
    backoff = INITIAL_BACKOFF
    for attempt in range(MAX_RETRIES):
        try:
            return send()
        except urllib.error.HTTPError as e:
            if e.code == 429:
                raise scryfall_api.ScryfallRateLimited() from e
            if e.code >= 500:
                if attempt < MAX_RETRIES - 1:
                    wait = backoff * (2 ** attempt)
                    print(f"    {label}HTTP {e.code}, retrying in {wait:.1f}s (attempt {attempt + 1}/{MAX_RETRIES})")
                    time.sleep(wait)
                    continue
            raise
        except (urllib.error.URLError, TimeoutError):
            if attempt < MAX_RETRIES - 1:
                wait = backoff * (2 ** attempt)
                print(f"    {label}Network error, retrying in {wait:.1f}s (attempt {attempt + 1}/{MAX_RETRIES})")
                time.sleep(wait)
                continue
            raise
    raise RuntimeError(f"Max retries exceeded for {label}")


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
    """Fetch image URIs from Scryfall Collection API in batches of 75.

    A ``//`` name goes into the batch as its front face. Returns dict mapping
    card_name -> {"front": {image_uris}, "back": {image_uris}|None}, under the
    full name that Scryfall returned and under its front face.
    A batch that still fails after the retries, or an answer without ``data``,
    raises, so the run ends.
    """
    uris = {}
    names = sorted({name.split(" // ")[0] for name in names})
    batches = [names[i : i + BATCH_SIZE] for i in range(0, len(names), BATCH_SIZE)]

    for i, batch in enumerate(batches):
        print(f"  Fetching URIs batch {i + 1}/{len(batches)} ({len(batch)} cards)...")
        body = {"identifiers": [{"name": name} for name in batch]}
        raw = request_with_retry(
            lambda: scryfall_api.request(scryfall_api.COLLECTION_URL, body),
            f"batch {i + 1}: ",
        )
        data = json.loads(raw)

        for card in data["data"]:
            card_name = card["name"]
            layout = card.get("layout", "normal")
            faces = card.get("card_faces", [])

            if "image_uris" in card:
                entry = {"front": card["image_uris"], "back": None}
            elif faces:
                entry = {"front": faces[0].get("image_uris", {}), "back": None}
                if layout in ("modal_dfc", "transform") and len(faces) > 1:
                    entry["back"] = faces[1].get("image_uris", {})
            else:
                entry = {"front": {}, "back": None}

            uris[card_name] = entry
            if " // " in card_name:
                front = card_name.split(" // ")[0]
                uris[front] = entry

        not_found = data.get("not_found", [])
        if not_found:
            nf_names = [nf.get("name", str(nf)) for nf in not_found]
            print(f"    Not found: {nf_names}")

    return uris


def download_image(url: str, dest: Path) -> bool:
    """Download an image from URL to dest path with retry."""
    req = urllib.request.Request(url, headers={"User-Agent": scryfall_api.USER_AGENT})

    def send() -> bytes:
        with urllib.request.urlopen(req, timeout=scryfall_api.TIMEOUT) as resp:
            return resp.read()

    try:
        data = request_with_retry(send, f"{dest.name}: ")
        dest.write_bytes(data)
        return True
    except scryfall_api.ScryfallRateLimited:
        raise
    except Exception as e:
        print(f"    Failed: {dest.name} — {e}")
        return False


def main() -> int:
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
    try:
        uris = fetch_image_uris(sorted(names))
    except scryfall_api.ScryfallRateLimited as e:
        print(f"\n{e}\nNo image downloaded.")
        return 1
    except (OSError, ValueError, KeyError) as e:
        print(f"\nA batch failed: {type(e).__name__}: {e}\nNo image downloaded.")
        return 1
    print(f"Got URIs for {len(uris)} cards.\n")

    downloaded = 0
    skipped = 0
    failed = 0

    # Build download jobs: (card_name, variant, face, uri_dict)
    jobs = []
    for name in sorted(names):
        entry = uris.get(name)
        if not entry and " // " in name:
            entry = uris.get(name.split(" // ")[0])
        if not entry:
            print(f"  No URIs for: {name}")
            failed += len(VARIANTS)
            continue

        sanitized = sanitize_card_name(name)
        # Front face
        for variant in VARIANTS:
            jobs.append((sanitized, variant, "front", entry.get("front", {})))
        # Back face (DFCs only)
        if entry.get("back"):
            for variant in VARIANTS:
                jobs.append((sanitized, variant, "back", entry["back"]))

    print(f"Downloading images ({len(jobs)} files)...")
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    for sanitized, variant, face, face_uris in jobs:
        suffix = f"back-{variant}" if face == "back" else variant
        dest = IMAGES_DIR / f"{sanitized}-{suffix}.jpg"

        if dest.exists() and dest.stat().st_size > 0:
            skipped += 1
            continue

        url = face_uris.get(variant)
        if not url:
            failed += 1
            continue

        try:
            ok = download_image(url, dest)
        except scryfall_api.ScryfallRateLimited as e:
            print(f"\n{e}\nStopped after {downloaded} downloaded image(s).")
            return 1
        if ok:
            downloaded += 1
        else:
            failed += 1

        time.sleep(DOWNLOAD_DELAY)

    print(f"\nDone! Downloaded: {downloaded}, Skipped: {skipped}, Failed: {failed}")
    print(f"Images dir: {IMAGES_DIR}")

    total_size = sum(f.stat().st_size for f in IMAGES_DIR.iterdir() if f.is_file())
    print(f"Total size: {total_size / (1024 * 1024):.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
