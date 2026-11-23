#!/usr/bin/env python3
"""Refresh local Scryfall oracle-cards mirror.

Downloads commander-legal cards from Scryfall's bulk-data API and stores a
trimmed copy at priv_data/scryfall-oracle.json (gitignored). Idempotent:
re-running with no remote change is a no-op.

The one request to api.scryfall.com (GET /bulk-data) goes through
scripts/scryfall_api.py, so it waits and stops as every other caller does; during
a stop the run writes no file and exits with 1 (DEC-1114 N3). The download of the
export from *.scryfall.io does not: that host has no limit.

Usage:
    python scripts/refresh_scryfall_mirror.py [--force]

DEC-90 phase 1.
"""

import argparse
import gzip
import json
import os
import sys
import tempfile
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import scryfall_api  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PRIV_DIR = PROJECT_ROOT / "priv_data"
MIRROR_FILE = PRIV_DIR / "scryfall-oracle.json"
META_FILE = PRIV_DIR / "scryfall-oracle.meta.json"
BULK_DATA_URL = "https://api.scryfall.com/bulk-data"
USER_AGENT = "mtg-precon-upgrader/1.0 (DEC-90 mirror refresh)"

# Fields retained per card. Drops images, prices, rulings, multiverse ids,
# set printings, illustration metadata, etc. Keeps everything needed for
# archetype matching, color identity filtering, and bracket gating.
KEEP_FIELDS = (
    "id", "oracle_id", "name", "mana_cost", "cmc",
    "type_line", "oracle_text", "power", "toughness",
    "loyalty", "defense", "colors", "color_identity",
    "keywords", "produced_mana", "legalities", "card_faces",
)
KEEP_FACE_FIELDS = (
    "name", "mana_cost", "type_line", "oracle_text",
    "colors", "power", "toughness", "loyalty", "defense",
)


def fetch_json(url: str) -> dict:
    """GET one api.scryfall.com address through the helper; ScryfallRateLimited passes through."""
    return json.loads(scryfall_api.request(url))


def find_oracle_cards_entry(bulk_data: dict) -> dict:
    for item in bulk_data.get("data", []):
        if item.get("type") == "oracle_cards":
            return item
    raise RuntimeError("No oracle_cards entry in Scryfall bulk-data response")


def trim_card(card: dict) -> dict:
    out = {k: card[k] for k in KEEP_FIELDS if k in card}
    if "card_faces" in out:
        out["card_faces"] = [
            {k: f[k] for k in KEEP_FACE_FIELDS if k in f}
            for f in out["card_faces"]
        ]
    return out


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Refresh Scryfall oracle-cards mirror")
    parser.add_argument("--force", action="store_true", help="Re-download even if mirror is current")
    args = parser.parse_args(argv)

    PRIV_DIR.mkdir(exist_ok=True)

    # A git worktree's priv_data may link these files to the main checkout's. A meta file
    # that leads to another folder than its mirror would date the wrong mirror, a link to
    # another file would overwrite it, and a link into a missing folder would fail only
    # after the download.
    mirror_file, meta_file = MIRROR_FILE.resolve(), META_FILE.resolve()
    if not (
        mirror_file.parent.is_dir()
        and meta_file.parent.is_dir()
        and os.path.samefile(mirror_file.parent, meta_file.parent)
        and mirror_file.name == MIRROR_FILE.name
        and meta_file.name == META_FILE.name
    ):
        print(
            f"{MIRROR_FILE} leads to {mirror_file}\n{META_FILE} leads to {meta_file}\n"
            "No file written. The two must lie in one existing folder under these names: "
            "link both files or neither.\n"
            "After repairing the links, run once with --force in the main checkout (the "
            "checkout the links lead to): a pair left by an older run can date an old mirror "
            "as current.",
            file=sys.stderr,
        )
        return 1

    print("Querying Scryfall bulk-data API...", file=sys.stderr)
    try:
        bulk = fetch_json(BULK_DATA_URL)
    except scryfall_api.ScryfallRateLimited as e:
        print(f"\n{e}\nNo file written.", file=sys.stderr)
        return 1
    oracle = find_oracle_cards_entry(bulk)
    remote_updated_at = oracle["updated_at"]
    # Scryfall dropped the plain-JSON `download_uri` (DEC-486, 2026-08-15). The
    # bulk-data entry now only exposes `jsonl_download_uri`: a gzipped JSON Lines
    # file (one card object per line). Fall back to `download_uri` if a future
    # API revision restores it.
    download_uri = oracle.get("jsonl_download_uri") or oracle.get("download_uri")
    if not download_uri:
        raise RuntimeError(
            "Scryfall oracle_cards entry has neither jsonl_download_uri nor "
            "download_uri; API shape changed again."
        )
    is_jsonl = download_uri.endswith((".jsonl", ".jsonl.gz"))
    is_gzip = download_uri.endswith(".gz")

    local_updated_at = None
    if META_FILE.exists() and not args.force:
        try:
            local_meta = json.loads(META_FILE.read_text())
            local_updated_at = local_meta.get("scryfall_updated_at")
        except (json.JSONDecodeError, OSError):
            pass

    if (
        local_updated_at == remote_updated_at
        and MIRROR_FILE.exists()
        and not args.force
    ):
        print(f"Mirror is current ({remote_updated_at}). No download.", file=sys.stderr)
        return 0

    print(
        f"Remote updated_at: {remote_updated_at} (local: {local_updated_at or 'none'})",
        file=sys.stderr,
    )
    print(f"Downloading {download_uri}...", file=sys.stderr)
    req = urllib.request.Request(download_uri, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=300) as resp:
        raw = resp.read()
    if is_gzip:
        raw = gzip.decompress(raw)
    if is_jsonl:
        all_cards = [json.loads(line) for line in raw.splitlines() if line.strip()]
    else:
        all_cards = json.loads(raw)

    print(f"Downloaded {len(all_cards):,} cards. Filtering to commander-legal...", file=sys.stderr)
    legal = [
        trim_card(c)
        for c in all_cards
        if c.get("legalities", {}).get("commander") == "legal"
    ]
    print(f"Filtered to {len(legal):,} commander-legal cards.", file=sys.stderr)
    if not legal:
        print(f"No commander-legal card in {download_uri}. No file written.", file=sys.stderr)
        return 1

    # mirror_file is resolved for this rename: a rename over a link would replace the link.
    # The temporary file is this run's own, so two runs at once cannot publish each other's.
    fd, tmp = tempfile.mkstemp(dir=mirror_file.parent, prefix=mirror_file.name + ".",
                               suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(legal, ensure_ascii=False))
        os.replace(tmp, mirror_file)
    finally:
        Path(tmp).unlink(missing_ok=True)

    META_FILE.write_text(json.dumps({
        "scryfall_updated_at": remote_updated_at,
        "downloaded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "card_count": len(legal),
        "source": download_uri,
    }, indent=2))

    size_mb = MIRROR_FILE.stat().st_size / (1024 * 1024)
    print(
        f"Mirror written to {MIRROR_FILE.relative_to(PROJECT_ROOT)} ({size_mb:.1f} MB).",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
