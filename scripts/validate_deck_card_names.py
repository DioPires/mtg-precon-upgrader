#!/usr/bin/env python3
"""Validate deck card-name fields against the local Scryfall oracle mirror.

This intentionally checks only fields whose schema stores actual card names:
root commanders/partners plus card objects in decklist, adds, and highlights.
Narrative arrays such as synergy cards can contain non-card placeholders today,
so they are not treated as strict card-name fields by this check.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
COMMANDERS_DIR = PROJECT_ROOT / "data" / "commanders"
MIRROR_FILE = PROJECT_ROOT / "priv_data" / "scryfall-oracle.json"
ROOT_CARD_FIELDS = ("commander", "partner")
CARD_OBJECT_LIST_FIELDS = ("decklist", "adds", "highlights")


@dataclass(frozen=True)
class CardNameReference:
    deck_id: str
    deck_file: Path
    json_path: str
    name: str


def available_deck_paths(commanders_dir: Path = COMMANDERS_DIR) -> list[Path]:
    """Return sorted commander deck files."""
    return sorted(commanders_dir.glob("*/deck.json"))


def deck_paths_for_ids(deck_ids: Sequence[str] | None) -> list[Path]:
    """Resolve requested deck ids to deck.json paths, or all decks when omitted."""
    if not deck_ids:
        return available_deck_paths()
    return [COMMANDERS_DIR / deck_id / "deck.json" for deck_id in deck_ids]


def _index_card_name(index: set[str], name: str | None) -> None:
    if not name:
        return
    index.add(name)
    if " // " in name:
        index.add(name.split(" // ", 1)[0])


def load_scryfall_name_index(mirror_file: Path = MIRROR_FILE) -> set[str]:
    """Load exact Scryfall card names and face names from the local mirror."""
    cards = json.loads(mirror_file.read_text())
    names: set[str] = set()
    for card in cards:
        _index_card_name(names, card.get("name"))
        for face in card.get("card_faces") or []:
            _index_card_name(names, face.get("name"))
    return names


def iter_card_name_references(
    deck: Mapping[str, object],
    deck_file: Path,
) -> Iterator[CardNameReference]:
    """Yield strict card-name fields from a deck.json document."""
    deck_id = str(deck.get("id") or deck_file.parent.name)

    for field in ROOT_CARD_FIELDS:
        value = deck.get(field)
        if isinstance(value, str) and value:
            yield CardNameReference(deck_id, deck_file, field, value)

    for field in CARD_OBJECT_LIST_FIELDS:
        value = deck.get(field)
        if not isinstance(value, list):
            continue
        for index, item in enumerate(value):
            if not isinstance(item, Mapping):
                continue
            name = item.get("name")
            if isinstance(name, str) and name:
                yield CardNameReference(deck_id, deck_file, f"{field}[{index}].name", name)


def validate_deck_card_names(
    deck_paths: Iterable[Path],
    scryfall_names: set[str],
) -> list[CardNameReference]:
    """Return card-name references that are absent from the Scryfall index."""
    missing: list[CardNameReference] = []
    for deck_file in sorted(deck_paths):
        deck = json.loads(deck_file.read_text())
        for reference in iter_card_name_references(deck, deck_file):
            if reference.name not in scryfall_names:
                missing.append(reference)
    return missing


def _relative(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Fail if strict deck.json card-name fields are absent from the local Scryfall mirror."
    )
    parser.add_argument(
        "--deck",
        dest="deck_ids",
        action="append",
        help="Validate one deck id. Repeat to validate multiple decks. Defaults to all decks.",
    )
    parser.add_argument(
        "--mirror-file",
        type=Path,
        default=MIRROR_FILE,
        help=f"Scryfall mirror path (default: {_relative(MIRROR_FILE)})",
    )
    args = parser.parse_args(argv)

    deck_paths = deck_paths_for_ids(args.deck_ids)
    missing_deck_files = [path for path in deck_paths if not path.exists()]
    if missing_deck_files:
        for path in missing_deck_files:
            print(f"missing deck file: {_relative(path)}", file=sys.stderr)
        return 2

    if not args.mirror_file.exists():
        print(f"missing Scryfall mirror: {_relative(args.mirror_file)}", file=sys.stderr)
        print("run: python scripts/refresh_scryfall_mirror.py", file=sys.stderr)
        return 2

    scryfall_names = load_scryfall_name_index(args.mirror_file)
    missing = validate_deck_card_names(deck_paths, scryfall_names)
    if missing:
        print("Card names missing from Scryfall mirror:", file=sys.stderr)
        for reference in missing:
            print(
                f"  {_relative(reference.deck_file)} {reference.json_path}: {reference.name}",
                file=sys.stderr,
            )
        return 1

    checked = sum(
        1
        for deck_file in deck_paths
        for _ in iter_card_name_references(json.loads(deck_file.read_text()), deck_file)
    )
    print(
        f"Validated {checked} card-name references across {len(deck_paths)} deck(s) "
        f"against {_relative(args.mirror_file)}."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
