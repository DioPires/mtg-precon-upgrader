#!/usr/bin/env python3
"""Build the committed card-price derivative for Combo Lab near-miss filtering.

DEC-516 (DEC-476 Phase 4). NM-5 requires completion suggestions to be filterable
by price with currency selection including EUR (Cardmarket) and USD; DR-5 sets the
data requirement (EUR + USD, freshness on the order of days).

The Scryfall oracle mirror (`priv_data/scryfall-oracle.json`) deliberately DROPS
prices, so this script reads two Scryfall bulk exports, which DO carry per-card
`prices`, filters to Commander-legal, and emits a compact name-keyed derivative
committed under `data/spellbook/`:

  - data/spellbook/price-index.json       { "<normalized name>": [eur, usd], ... }
  - data/spellbook/price-index.meta.json  provenance + freshness

Prices are the non-foil Cardmarket EUR (`prices.eur`) and TCGplayer USD
(`prices.usd`); a missing price is stored as null. For each currency by itself
(DEC-1086, the rule of data/card-metadata.json since DEC-1079):

  1. the price of the card's printing in `oracle_cards` (one printing for each card);
  2. when that printing has none, the lowest price among the card's printings in
     `default_cards` (every printing) that count: "paper" in `games`, released on
     or before the date of the `default_cards` export, and not memorabilia.

A foil or etched price never counts. A card with no price in either currency has
no row. Names are normalized with the same casefold+strip rules the Combo Lab
matcher/synergy engines use, and every `//`-face is aliased (first-wins) so a
completer card resolves whichever face the feature index names it by.

The one request to api.scryfall.com (`/bulk-data`) goes through scripts/scryfall_api.py.
The two exports download from data.scryfall.io, which has no rate limit, into
--download-dir with the /bulk-data answer as bulk-data.json. The script reads each
export one line at a time and keeps only what the index needs. --bulk-data with
--oracle-source and --default-source reads saved files and sends no request; such a
run always rebuilds, and it writes the same index as the run that saved them.

All generation is LOCAL; the committed JSON deploys via the Vercel `cp -R ../data`
step. The runtime never calls Scryfall (NF-1/NF-9). Idempotent on a stable corpus.

Usage:
    uv run python scripts/build_price_index.py [--force] [--download-dir DIR]
    uv run python scripts/build_price_index.py --bulk-data DIR/bulk-data.json \\
        --oracle-source DIR/oracle-cards-*.jsonl.gz --default-source DIR/default-cards-*.jsonl.gz
"""

from __future__ import annotations

import argparse
import gzip
import json
import os
import shutil
import sys
import tempfile
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
BULK_DATA_URL = f"https://{scryfall_api.API_HOST}/bulk-data"
BULK_DATA_FILE = "bulk-data.json"
USER_AGENT = "mtg-precon-upgrader/1.0 (DEC-516 price index)"
CURRENCIES = ("eur", "usd")  # the order of a row
# Scryfall's set type of gold-bordered, oversized, trophy, 30th Anniversary
# Edition and Collectors' Edition printings. No sanctioned game allows them, so
# their prices do not count (DEC-1079 Q2, the rule of fetch_card_metadata.py).
MEMORABILIA = "memorabilia"


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


def find_entry(bulk_data: dict, kind: str) -> dict:
    for item in bulk_data.get("data", []):
        if item.get("type") == kind:
            return item
    raise RuntimeError(f"No {kind} entry in Scryfall bulk-data response")


def jsonl_uri(entry: dict) -> str:
    """The address of an export's JSON Lines file: the script reads one card a line."""
    uri = entry.get("jsonl_download_uri")
    if not uri:
        raise RuntimeError(f"Scryfall's {entry['type']} entry exposes no JSON Lines download URI.")
    return uri


def oracle_id_of(card: dict) -> str | None:
    """The card's oracle id. A reversible_card printing carries it on each face
    only, so the front face gives it (DEC-1112 B1)."""
    return card.get("oracle_id") or (card.get("card_faces") or [{}])[0].get("oracle_id")


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


def _counts(printing: dict, export_date: str) -> bool:
    """Whether a printing's price counts: on paper, released on or before
    ``export_date`` (``YYYY-MM-DD``) and not memorabilia."""
    return ("paper" in printing["games"] and printing["released_at"] <= export_date
            and printing["set_type"] != MEMORABILIA)


def iter_cards(path: Path):
    """Each card of a JSON Lines export (gzip when the name ends in .gz), one
    line at a time, so no export is held in memory whole."""
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def read_oracle_cards(path: Path) -> list[tuple]:
    """The Commander-legal cards of an ``oracle_cards`` export, in its order, as
    (name, oracle id, [eur, usd] of the card's printing)."""
    cards = []
    for c in iter_cards(path):
        if c.get("legalities", {}).get("commander") == "legal":
            prices = [_price(c.get("prices"), currency) for currency in CURRENCIES]
            cards.append((c.get("name", ""), oracle_id_of(c), prices))
    return cards


def lowest_prices(path: Path, wanted: set[str], export_date: str) -> dict[str, list]:
    """For each oracle id of ``wanted``, the lowest non-foil [eur, usd] among
    its printings in a ``default_cards`` export that count (_counts)."""
    lowest: dict[str, list] = {}
    for printing in iter_cards(path):
        oracle_id = oracle_id_of(printing)
        if oracle_id not in wanted or not _counts(printing, export_date):
            continue
        row = lowest.setdefault(oracle_id, [None, None])
        for i, currency in enumerate(CURRENCIES):
            price = _price(printing.get("prices"), currency)
            if price is not None and (row[i] is None or price < row[i]):
                row[i] = price
    return lowest


def build_index(cards: list[tuple], lowest: dict[str, list]) -> tuple[dict[str, list], dict[str, int]]:
    """Name-key → [eur, usd]. Cards with neither price are skipped entirely.

    ``cards`` comes from read_oracle_cards. A price that the card's printing
    lacks comes from ``lowest`` (lowest_prices), currency by currency. Also
    returns, for each currency, the number of keys whose price came from
    another printing.

    Two passes, because a face alias must never outrank an exact full name: an
    MDFC back face can carry a standalone card's whole name (`Grave Researcher
    // Reanimate` vs the sorcery `Reanimate`), and Scryfall's bulk export is
    name-ordered, so the MDFC reached the key first and the standalone card
    displayed the MDFC's price (DEC-553, same defect as the Tier-C name map).
    Full names claim their key first; face aliases only fill what is left.
    Within each pass it stays first-wins."""
    index: dict[str, list] = {}
    other: dict[str, list[bool]] = {}  # key -> [eur, usd] from another printing
    aliases: list[tuple[str, list, list[bool]]] = []
    for name, oracle_id, own in cards:
        fill = lowest.get(oracle_id, [None, None])
        row = [p if p is not None else f for p, f in zip(own, fill)]
        if row == [None, None]:
            continue
        keys = [k for k in name_keys(name) if k]
        if not keys:
            continue
        filled = [p is None and r is not None for p, r in zip(own, row)]
        if keys[0] not in index:
            index[keys[0]] = row
            other[keys[0]] = filled
        aliases.extend((k, row, filled) for k in keys[1:])
    for k, row, filled in aliases:
        if k not in index:
            index[k] = row
            other[k] = filled
    counts = {c: sum(f[i] for f in other.values()) for i, c in enumerate(CURRENCIES)}
    return index, counts


def download(uri: str, folder: Path) -> Path:
    """Copy one export from data.scryfall.io into ``folder`` under its own name."""
    path = folder / uri.rsplit("/", 1)[-1]
    print(f"Downloading {uri}...", file=sys.stderr)
    req = urllib.request.Request(uri, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=300) as resp, path.open("wb") as out:
        shutil.copyfileobj(resp, out)
    return path


def is_current(oracle: dict, default: dict) -> bool:
    """Whether the committed files come from these two exports."""
    if not (META_FILE.exists() and INDEX_FILE.exists()):
        return False
    try:
        local = json.loads(META_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return False
    return (local.get("scryfall_updated_at") == oracle["updated_at"]
            and local.get("default_cards_updated_at") == default["updated_at"])


def exports(bulk_data: dict) -> tuple[dict, dict]:
    """The oracle_cards and default_cards entries of a /bulk-data answer."""
    return find_entry(bulk_data, "oracle_cards"), find_entry(bulk_data, "default_cards")


def build(oracle: dict, default: dict, oracle_path: Path, default_path: Path) -> None:
    """Read both exports, build the index and write both files. ``oracle`` and
    ``default`` are the exports' entries of the /bulk-data answer."""
    export_date = default["updated_at"][:10]
    cards = read_oracle_cards(oracle_path)
    wanted = {oid for _, oid, own in cards if oid and None in own}
    print(
        f"{len(cards):,} commander-legal cards; {len(wanted):,} lack a price. "
        f"Reading the printings released on or before {export_date}...",
        file=sys.stderr,
    )
    index, other = build_index(cards, lowest_prices(default_path, wanted, export_date))
    write_outputs(index, other, oracle, default)


def write_outputs(index: dict, other: dict[str, int], oracle: dict, default: dict) -> None:
    """Write the index and its meta file.

    Each file goes to ``<name>.tmp`` in its folder first, then os.replace moves
    both into place, the meta file last (DEC-1080 N1, as in
    fetch_card_metadata.py). A run that fails before the moves leaves both old
    files as they were.
    """
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    priced_eur = sum(1 for v in index.values() if v[0] is not None)
    priced_usd = sum(1 for v in index.values() if v[1] is not None)
    meta = {
        "schema": "combo-lab-price-index",
        "source": "scryfall-bulk-oracle-cards+default-cards",
        "sourceUrl": jsonl_uri(oracle),
        "scryfall_updated_at": oracle["updated_at"],
        "defaultCardsUrl": jsonl_uri(default),
        "default_cards_updated_at": default["updated_at"],
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "currencies": list(CURRENCIES),
        "keyCount": len(index),
        "pricedEur": priced_eur,
        "pricedUsd": priced_usd,
        "pricedEurFromOtherPrinting": other["eur"],
        "pricedUsdFromOtherPrinting": other["usd"],
        "note": (
            "Name-key → [eur, usd] (non-foil; eur=Cardmarket, usd=TCGplayer). "
            "null = no price. Each price is the card's oracle_cards printing's; "
            "when that has none, the lowest among the card's default_cards printings "
            "on paper, released by the default_cards export's date and not memorabilia. "
            "Never a foil or etched price. Keys are normalize_name()-folded with "
            "//-faces aliased first-wins. Cards with no price are omitted."
        ),
    }
    texts = {
        # Compact + stable key order so the weekly git diff delta-compresses.
        INDEX_FILE: json.dumps(index, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        META_FILE: json.dumps(meta, indent=2, sort_keys=True) + "\n",
    }
    temps = {path: path.with_name(path.name + ".tmp") for path in texts}
    try:
        for path, text in texts.items():
            temps[path].write_text(text)
        for path in texts:
            os.replace(temps[path], path)
    finally:
        for temp in temps.values():
            temp.unlink(missing_ok=True)

    size_mb = INDEX_FILE.stat().st_size / (1024 * 1024)
    print(
        f"Wrote {INDEX_FILE.relative_to(PROJECT_ROOT)} ({size_mb:.1f} MB, "
        f"{len(index):,} keys; eur {priced_eur:,} / usd {priced_usd:,}; "
        f"from another printing eur {other['eur']:,} / usd {other['usd']:,}).",
        file=sys.stderr,
    )


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Build the Combo Lab card-price index")
    ap.add_argument("--force", action="store_true", help="Rebuild even if current")
    ap.add_argument("--download-dir", type=Path,
                    help="Keep the /bulk-data answer and both exports in this folder "
                         "(default: a temporary folder that the run removes)")
    ap.add_argument("--bulk-data", type=Path, help="A saved /bulk-data answer")
    ap.add_argument("--oracle-source", type=Path, help="A saved oracle_cards .jsonl(.gz)")
    ap.add_argument("--default-source", type=Path, help="A saved default_cards .jsonl(.gz)")
    args = ap.parse_args(argv)
    local = (args.bulk_data, args.oracle_source, args.default_source)
    if any(local) and not all(local):
        ap.error("--bulk-data, --oracle-source and --default-source go together")

    if all(local):
        oracle, default = exports(json.loads(args.bulk_data.read_bytes()))
        build(oracle, default, args.oracle_source, args.default_source)
        return 0

    print("Querying Scryfall bulk-data API...", file=sys.stderr)
    try:
        raw = scryfall_api.request(BULK_DATA_URL)
    except scryfall_api.ScryfallRateLimited as e:
        print(f"{e}\nNo file written.", file=sys.stderr)
        return 1
    oracle, default = exports(json.loads(raw))
    if not args.force and is_current(oracle, default):
        print(f"Price index is current ({oracle['updated_at']}, {default['updated_at']}).",
              file=sys.stderr)
        return 0

    with tempfile.TemporaryDirectory() as tmp:
        folder = args.download_dir or Path(tmp)
        folder.mkdir(parents=True, exist_ok=True)
        (folder / BULK_DATA_FILE).write_bytes(raw)
        oracle_path = download(jsonl_uri(oracle), folder)
        default_path = download(jsonl_uri(default), folder)
        build(oracle, default, oracle_path, default_path)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
