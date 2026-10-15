#!/usr/bin/env python3
"""Build the committed card-price derivative for Combo Lab near-miss filtering.

DEC-516 (DEC-476 Phase 4). NM-5 requires completion suggestions to be filterable
by price with currency selection including EUR (Cardmarket) and USD; DR-5 sets the
data requirement (EUR + USD, freshness on the order of days).

The Scryfall oracle mirror (`priv_data/scryfall-oracle.json`) deliberately DROPS
prices, so this script fetches the Scryfall bulk `oracle_cards` export fresh —
which DOES carry per-card `prices` — filters to Commander-legal, and emits a
compact name-keyed derivative committed under `data/spellbook/`:

  - data/spellbook/price-index.json       { "<normalized name>": [eur, usd], ... }
  - data/spellbook/price-index.meta.json  provenance + freshness

Prices are the non-foil Cardmarket EUR (`prices.eur`) and TCGplayer USD
(`prices.usd`); a missing price is stored as null. Names are normalized with the
same casefold+strip rules the Combo Lab matcher/synergy engines use, and every
`//`-face is aliased (first-wins) so a completer card resolves whichever face the
feature index names it by.

All generation is LOCAL; the committed JSON deploys via the Vercel `cp -R ../data`
step. The runtime never calls Scryfall (NF-1/NF-9). Idempotent on a stable corpus.

The one request to api.scryfall.com (GET /bulk-data) goes through
scripts/scryfall_api.py, so it waits and stops as every other caller does; during
a stop the run writes no file and exits with 1 (DEC-1114 N3). The download of the
export from *.scryfall.io does not: that host has no limit.

Usage:
    uv run python scripts/build_price_index.py [--force] [--source jsonl.gz|-]
"""

from __future__ import annotations

import argparse
import gzip
import json
import sys
import unicodedata
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import scryfall_api  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = PROJECT_ROOT / "data" / "spellbook"
INDEX_FILE = OUT_DIR / "price-index.json"
META_FILE = OUT_DIR / "price-index.meta.json"
BULK_DATA_URL = "https://api.scryfall.com/bulk-data"
USER_AGENT = "mtg-precon-upgrader/1.0 (DEC-516 price index)"


def normalize_name(name: str) -> str:
    """Casefold + strip accents/punctuation. Mirror of normalize_name() in
    scripts/sync_spellbook_combos.py and normalizeName() in the TS engines."""
    if not name:
        return ""
    ascii_name = "".join(
        ch for ch in unicodedata.normalize("NFKD", name) if not unicodedata.combining(ch)
    )
    out = []
    for ch in ascii_name.lower():
        out.append(ch if (ch.isalnum() or ch == " ") else " ")
    return " ".join("".join(out).split())


def name_keys(name: str) -> list[str]:
    """Normalized full name plus every ``//``-split face key (order-preserving)."""
    keys: list[str] = []
    full = normalize_name(name)
    if full:
        keys.append(full)
    if "//" in name:
        for face in name.split("//"):
            fk = normalize_name(face)
            if fk and fk not in keys:
                keys.append(fk)
    return keys


def fetch_json(url: str) -> dict:
    """GET one api.scryfall.com address through the helper; ScryfallRateLimited passes through."""
    return json.loads(scryfall_api.request(url))


def find_oracle_cards_entry(bulk_data: dict) -> dict:
    for item in bulk_data.get("data", []):
        if item.get("type") == "oracle_cards":
            return item
    raise RuntimeError("No oracle_cards entry in Scryfall bulk-data response")


def _price(raw: dict, key: str) -> float | None:
    """Parse a Scryfall price string to a float, or None when absent/blank."""
    val = (raw or {}).get(key)
    if val in (None, "", "0", "0.0"):
        return None
    try:
        f = float(val)
    except (TypeError, ValueError):
        return None
    return f if f > 0 else None


def build_index(cards: list[dict]) -> dict[str, list]:
    """Name-key → [eur, usd]. Cards with neither price are skipped entirely.

    Two passes, because a face alias must never outrank an exact full name: an
    MDFC back face can carry a standalone card's whole name (`Grave Researcher
    // Reanimate` vs the sorcery `Reanimate`), and Scryfall's bulk export is
    name-ordered, so the MDFC reached the key first and the standalone card
    displayed the MDFC's price (DEC-553, same defect as the Tier-C name map).
    Full names claim their key first; face aliases only fill what is left.
    Within each pass it stays first-wins."""
    index: dict[str, list] = {}
    aliases: list[tuple[str, list]] = []
    for c in cards:
        eur = _price(c.get("prices"), "eur")
        usd = _price(c.get("prices"), "usd")
        if eur is None and usd is None:
            continue
        keys = [k for k in name_keys(c.get("name", "")) if k]
        if not keys:
            continue
        if keys[0] not in index:
            index[keys[0]] = [eur, usd]
        aliases.extend((k, [eur, usd]) for k in keys[1:])
    for k, price in aliases:
        if k not in index:
            index[k] = price
    return index


def load_source_cards(source: str | None, force: bool) -> tuple[list[dict], str, str]:
    """Return (cards, remote_updated_at, source_uri). ``source`` may be a local
    path or "-" for stdin (jsonl / jsonl.gz / json), else Scryfall bulk is used."""
    if source and source != "-":
        p = Path(source)
        raw = p.read_bytes()
        if p.suffix == ".gz":
            raw = gzip.decompress(raw)
        cards = _parse_cards(raw, p.name.endswith((".jsonl", ".jsonl.gz")))
        return cards, "local", str(p)

    print("Querying Scryfall bulk-data API...", file=sys.stderr)
    bulk = fetch_json(BULK_DATA_URL)
    oracle = find_oracle_cards_entry(bulk)
    remote_updated_at = oracle["updated_at"]
    download_uri = oracle.get("jsonl_download_uri") or oracle.get("download_uri")
    if not download_uri:
        raise RuntimeError("Scryfall oracle_cards entry exposes no download URI.")

    if not force and META_FILE.exists() and INDEX_FILE.exists():
        try:
            local = json.loads(META_FILE.read_text())
            if local.get("scryfall_updated_at") == remote_updated_at:
                print(f"Price index is current ({remote_updated_at}).", file=sys.stderr)
                return [], remote_updated_at, download_uri
        except (json.JSONDecodeError, OSError):
            pass

    print(f"Downloading {download_uri}...", file=sys.stderr)
    req = urllib.request.Request(download_uri, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=300) as resp:
        raw = resp.read()
    if download_uri.endswith(".gz"):
        raw = gzip.decompress(raw)
    cards = _parse_cards(raw, download_uri.endswith((".jsonl", ".jsonl.gz")))
    return cards, remote_updated_at, download_uri


def _parse_cards(raw: bytes, is_jsonl: bool) -> list[dict]:
    if is_jsonl:
        return [json.loads(line) for line in raw.splitlines() if line.strip()]
    return json.loads(raw)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Build the Combo Lab card-price index")
    ap.add_argument("--force", action="store_true", help="Rebuild even if current")
    ap.add_argument("--source", help="Local jsonl(.gz)/json file or '-' for stdin")
    args = ap.parse_args(argv)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        cards, remote_updated_at, source_uri = load_source_cards(args.source, args.force)
    except scryfall_api.ScryfallRateLimited as e:
        print(f"\n{e}\nNo file written.", file=sys.stderr)
        return 1
    if not cards:
        return 0  # already current

    print(f"Downloaded {len(cards):,} cards. Filtering to commander-legal...", file=sys.stderr)
    legal = [c for c in cards if c.get("legalities", {}).get("commander") == "legal"]
    index = build_index(legal)
    print(
        f"Filtered to {len(legal):,} commander-legal; {len(index):,} price keys.",
        file=sys.stderr,
    )

    tmp = INDEX_FILE.with_suffix(".json.tmp")
    # Compact + stable key order so the weekly git diff delta-compresses.
    tmp.write_text(
        json.dumps(index, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    )
    tmp.replace(INDEX_FILE)

    priced_eur = sum(1 for v in index.values() if v[0] is not None)
    priced_usd = sum(1 for v in index.values() if v[1] is not None)
    META_FILE.write_text(
        json.dumps(
            {
                "schema": "combo-lab-price-index",
                "source": "scryfall-bulk-oracle-cards",
                "sourceUrl": source_uri,
                "scryfall_updated_at": remote_updated_at,
                "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "currencies": ["eur", "usd"],
                "keyCount": len(index),
                "pricedEur": priced_eur,
                "pricedUsd": priced_usd,
                "note": (
                    "Name-key → [eur, usd] (non-foil; eur=Cardmarket, usd=TCGplayer). "
                    "null = no price. Keys are normalize_name()-folded with //-faces "
                    "aliased first-wins. Cards with no price are omitted."
                ),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )

    size_mb = INDEX_FILE.stat().st_size / (1024 * 1024)
    print(
        f"Wrote {INDEX_FILE.relative_to(PROJECT_ROOT)} ({size_mb:.1f} MB, "
        f"{len(index):,} keys; eur {priced_eur:,} / usd {priced_usd:,}).",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
