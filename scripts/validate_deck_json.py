#!/usr/bin/env python3
"""Validate commander deck JSON card references.

Checks that every card-name reference resolves against the local Scryfall
oracle mirror, then checks that category/highlight/synergy/win-condition
references point at cards actually present in the deck.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
COMMANDERS_DIR = PROJECT_ROOT / "data" / "commanders"
MIRROR_FILE = PROJECT_ROOT / "priv_data" / "scryfall-oracle.json"
ROOT_CARD_FIELDS = ("commander", "partner")
DECKLIST_FIELDS = ("decklist",)
CARD_OBJECT_LIST_FIELDS = ("adds", "highlights")
CARD_ARRAY_FIELDS = (
    ("categories", "cards"),
    ("winConditions", "cards"),
    ("synergies", "cards"),
    ("guideContent.deckCategories", "cards"),
)


@dataclass(frozen=True)
class CardReference:
    deck_id: str
    deck_file: Path
    json_path: str
    name: str
    require_in_deck: bool

    def to_report_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["deck_file"] = relative_path(self.deck_file)
        return data


@dataclass(frozen=True)
class ValidationIssue:
    issue_type: str
    reference: CardReference
    detail: str

    def to_report_dict(self) -> dict[str, object]:
        return {
            "issue_type": self.issue_type,
            "reference": self.reference.to_report_dict(),
            "detail": self.detail,
        }


@dataclass(frozen=True)
class ScryfallNameIndex:
    canonical_by_alias: dict[str, str]

    def resolve(self, name: str) -> str | None:
        return self.canonical_by_alias.get(name)


def available_deck_paths(commanders_dir: Path = COMMANDERS_DIR) -> list[Path]:
    """Return sorted commander deck files."""
    return sorted(commanders_dir.glob("*/deck.json"))


def deck_paths_for_ids(deck_ids: Sequence[str] | None) -> list[Path]:
    """Resolve requested deck ids to deck.json paths, or all decks when omitted."""
    if not deck_ids:
        return available_deck_paths()
    return [COMMANDERS_DIR / deck_id / "deck.json" for deck_id in deck_ids]


def relative_path(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def _index_card_name(index: dict[str, str], canonical: str, alias: str | None) -> None:
    if not alias:
        return
    index[alias] = canonical
    if " // " in alias:
        index[alias.split(" // ", 1)[0]] = canonical


def load_scryfall_name_index(mirror_file: Path = MIRROR_FILE) -> ScryfallNameIndex:
    """Load exact Scryfall card names and face names from the local mirror."""
    cards = json.loads(mirror_file.read_text())
    canonical_by_alias: dict[str, str] = {}
    for card in cards:
        canonical = card.get("name")
        if not canonical:
            continue
        _index_card_name(canonical_by_alias, canonical, canonical)
        for face in card.get("card_faces") or []:
            _index_card_name(canonical_by_alias, canonical, face.get("name"))
    return ScryfallNameIndex(canonical_by_alias)


def _nested_value(root: Mapping[str, object], dotted_path: str) -> object:
    value: object = root
    for part in dotted_path.split("."):
        if not isinstance(value, Mapping):
            return None
        value = value.get(part)
    return value


def iter_card_references(
    deck: Mapping[str, object],
    deck_file: Path,
) -> Iterator[CardReference]:
    """Yield card-name references from the deck schema."""
    deck_id = str(deck.get("id") or deck_file.parent.name)

    for field in ROOT_CARD_FIELDS:
        value = deck.get(field)
        if isinstance(value, str) and value:
            yield CardReference(deck_id, deck_file, field, value, False)

    for field in DECKLIST_FIELDS:
        value = deck.get(field)
        if not isinstance(value, list):
            continue
        for index, item in enumerate(value):
            if not isinstance(item, Mapping):
                continue
            name = item.get("name")
            if isinstance(name, str) and name:
                yield CardReference(deck_id, deck_file, f"{field}[{index}].name", name, False)

    for field in CARD_OBJECT_LIST_FIELDS:
        value = deck.get(field)
        if not isinstance(value, list):
            continue
        for index, item in enumerate(value):
            if not isinstance(item, Mapping):
                continue
            name = item.get("name")
            if isinstance(name, str) and name:
                yield CardReference(deck_id, deck_file, f"{field}[{index}].name", name, True)

    for field, cards_key in CARD_ARRAY_FIELDS:
        value = _nested_value(deck, field)
        if not isinstance(value, list):
            continue
        for index, item in enumerate(value):
            if not isinstance(item, Mapping):
                continue
            cards = item.get(cards_key)
            if not isinstance(cards, list):
                continue
            for card_index, name in enumerate(cards):
                if isinstance(name, str) and name:
                    yield CardReference(
                        deck_id,
                        deck_file,
                        f"{field}[{index}].{cards_key}[{card_index}]",
                        name,
                        True,
                    )


def iter_deck_core_references(
    deck: Mapping[str, object],
    deck_file: Path,
) -> Iterator[CardReference]:
    """Yield commander/partner/decklist names that define the deck's card set."""
    for reference in iter_card_references(deck, deck_file):
        if not reference.require_in_deck:
            yield reference


def _canonical_deck_card_names(
    deck: Mapping[str, object],
    deck_file: Path,
    scryfall_index: ScryfallNameIndex,
) -> set[str]:
    names: set[str] = set()
    for reference in iter_deck_core_references(deck, deck_file):
        canonical = scryfall_index.resolve(reference.name)
        if canonical:
            names.add(canonical)
    return names


def validate_deck_json(
    deck_paths: Iterable[Path],
    scryfall_index: ScryfallNameIndex,
) -> list[ValidationIssue]:
    """Return all unresolved or inconsistent deck JSON card references."""
    issues: list[ValidationIssue] = []
    for deck_file in sorted(deck_paths):
        deck = json.loads(deck_file.read_text())
        deck_canonical_names = _canonical_deck_card_names(deck, deck_file, scryfall_index)

        for reference in iter_card_references(deck, deck_file):
            canonical = scryfall_index.resolve(reference.name)
            if not canonical:
                issues.append(
                    ValidationIssue(
                        "missing_scryfall",
                        reference,
                        "Name does not resolve in the local Scryfall oracle mirror.",
                    )
                )
                continue

            if reference.require_in_deck and canonical not in deck_canonical_names:
                issues.append(
                    ValidationIssue(
                        "not_in_decklist",
                        reference,
                        "Reference resolves in Scryfall but is not in commander/partner/decklist.",
                    )
                )

    return issues


def _print_text_report(issues: list[ValidationIssue]) -> None:
    print("Deck JSON validation failed:", file=sys.stderr)
    for issue in issues:
        reference = issue.reference
        print(
            f"  {issue.issue_type} {relative_path(reference.deck_file)} "
            f"{reference.json_path}: {reference.name} -- {issue.detail}",
            file=sys.stderr,
        )


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Fail if deck.json card references are absent from the local Scryfall "
            "mirror or point outside the decklist."
        )
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
        help=f"Scryfall mirror path (default: {relative_path(MIRROR_FILE)})",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable validation issues.",
    )
    args = parser.parse_args(argv)

    deck_paths = deck_paths_for_ids(args.deck_ids)
    missing_deck_files = [path for path in deck_paths if not path.exists()]
    if missing_deck_files:
        for path in missing_deck_files:
            print(f"missing deck file: {relative_path(path)}", file=sys.stderr)
        return 2

    if not args.mirror_file.exists():
        print(f"missing Scryfall mirror: {relative_path(args.mirror_file)}", file=sys.stderr)
        print("run: python scripts/refresh_scryfall_mirror.py", file=sys.stderr)
        return 2

    scryfall_index = load_scryfall_name_index(args.mirror_file)
    issues = validate_deck_json(deck_paths, scryfall_index)
    if issues:
        if args.json:
            print(json.dumps([issue.to_report_dict() for issue in issues], indent=2))
        else:
            _print_text_report(issues)
        return 1

    checked = sum(
        1
        for deck_file in deck_paths
        for _ in iter_card_references(json.loads(deck_file.read_text()), deck_file)
    )
    print(
        f"Validated {checked} card references across {len(deck_paths)} deck(s) "
        f"against {relative_path(args.mirror_file)}."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
