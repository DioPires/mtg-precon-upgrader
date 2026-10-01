#!/usr/bin/env python3
"""DEC-940 — one-off backfill of printed power/toughness into card-metadata.json.

`scripts/fetch_card_metadata.py` now emits `power`/`toughness` on every entry
(see `_entry_from_card`), so a future network refresh produces them. This script
fills the two new keys into the existing cache from the local Scryfall mirror
instead of refetching 1541 cards, and deliberately touches nothing else: every
other field keeps its current value, so the diff is exactly the two new keys.

Front-face values only, matching `_entry_from_card`: top-level power/toughness
when present, otherwise `card_faces[0]`. The mirror is keyed by full name, with
MDFC front-face names added as aliases only where the full name does not already
claim them (DEC-553).

Run: uv run python agents/sim-eng/analysis/dec940-backfill-power.py [--check]
"""

import argparse
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
METADATA_FILE = PROJECT_ROOT / "data" / "card-metadata.json"
MIRROR_FILE = PROJECT_ROOT / "priv_data" / "scryfall-oracle.json"


def mirror_power_index() -> dict[str, tuple[str | None, str | None]]:
    """Full card name -> (power, toughness), plus front-face-name aliases."""
    with open(MIRROR_FILE) as handle:
        cards = json.load(handle)

    def front_pt(card: dict) -> tuple[str | None, str | None]:
        power, toughness = card.get("power"), card.get("toughness")
        faces = card.get("card_faces") or []
        if faces:
            if power is None:
                power = faces[0].get("power")
            if toughness is None:
                toughness = faces[0].get("toughness")
        return power, toughness

    index: dict[str, tuple[str | None, str | None]] = {}
    aliases: dict[str, tuple[str | None, str | None]] = {}
    for card in cards:
        name = card.get("name")
        if not name:
            continue
        index[name] = front_pt(card)
        if " // " in name:
            aliases.setdefault(name.split(" // ")[0], front_pt(card))
    for alias, value in aliases.items():
        index.setdefault(alias, value)
    return index


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="report coverage without writing")
    args = parser.parse_args()

    with open(METADATA_FILE) as handle:
        metadata = json.load(handle)
    index = mirror_power_index()

    missing = []
    for name, entry in metadata.items():
        if name in index:
            entry["power"], entry["toughness"] = index[name]
        else:
            entry.setdefault("power", None)
            entry.setdefault("toughness", None)
            missing.append(name)

    creatures_with_power = sum(
        1 for entry in metadata.values()
        if "Creature" in entry.get("type_line", "") and entry.get("power") is not None
    )
    creatures = sum(
        1 for entry in metadata.values() if "Creature" in entry.get("type_line", "")
    )
    print(f"entries: {len(metadata)}  creatures: {creatures}  "
          f"creatures with printed power: {creatures_with_power}")
    if missing:
        print(f"not in mirror ({len(missing)}): {sorted(missing)}")

    if args.check:
        return 0

    # Same write format as fetch_card_metadata.py: indent=2, sort_keys=True,
    # no trailing newline.
    with open(METADATA_FILE, "w") as handle:
        json.dump(metadata, handle, indent=2, sort_keys=True)
    print(f"wrote {METADATA_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
