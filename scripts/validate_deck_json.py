#!/usr/bin/env python3
"""Validate commander deck JSON card references.

Checks that every card-name reference resolves against the local Scryfall
oracle mirror and that category/highlight/synergy/win-condition references
point at cards in the deck; `candidate_pins` must list objects with a non-empty
`name`, a combo line's `minX` must map its in-deck {X}-cost pieces to integers >= 1,
and a decklist entry's tutor and recursion tags must pass gate_tags_lib.entry_errors,
the check the simulation exporter runs.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import gate_tags_lib

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
    # Front-face mana cost by canonical name, for the win-condition minX check
    # and the tag checks.
    mana_cost_by_canonical: dict[str, str] = field(default_factory=dict)
    # Front-face type line by canonical name, for the tag checks.
    type_line_by_canonical: dict[str, str] = field(default_factory=dict)

    def resolve(self, name: str) -> str | None:
        return self.canonical_by_alias.get(name)

    def mana_cost(self, name: str) -> str:
        """The front-face mana cost of the card ``name`` resolves to ("" if none)."""
        return self.mana_cost_by_canonical.get(self.resolve(name) or "", "")

    def front(self, name: str) -> tuple[str, str] | None:
        """The front face of the card ``name`` resolves to, as (type line, mana
        cost), or None when the name does not resolve."""
        canonical = self.resolve(name)
        if canonical is None:
            return None
        return self.type_line_by_canonical.get(canonical, ""), self.mana_cost_by_canonical.get(canonical, "")


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
    """Load exact Scryfall card names and face names, and each card's front-face
    mana cost and type line, from the local mirror."""
    cards = json.loads(mirror_file.read_text())
    canonical_by_alias: dict[str, str] = {}
    mana_cost_by_canonical: dict[str, str] = {}
    type_line_by_canonical: dict[str, str] = {}
    for card in cards:
        canonical = card.get("name")
        if not canonical:
            continue
        _index_card_name(canonical_by_alias, canonical, canonical)
        faces = card.get("card_faces") or []
        for face in faces:
            _index_card_name(canonical_by_alias, canonical, face.get("name"))
        mana_cost = card.get("mana_cost") or (faces[0].get("mana_cost") if faces else "") or ""
        mana_cost_by_canonical[canonical] = mana_cost.split(" // ")[0]
        type_line = card.get("type_line") or (faces[0].get("type_line") if faces else "") or ""
        type_line_by_canonical[canonical] = type_line.split(" // ")[0]
    return ScryfallNameIndex(canonical_by_alias, mana_cost_by_canonical, type_line_by_canonical)


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


def iter_candidate_pin_issues(
    deck: Mapping[str, object],
    deck_file: Path,
) -> Iterator[ValidationIssue]:
    """Yield shape issues for `candidate_pins`: a list of objects with a non-empty string name.

    The pool generator warns and skips a bad pin (DEC-992); the validator fails it.
    """
    if "candidate_pins" not in deck:
        return
    deck_id = str(deck.get("id") or deck_file.parent.name)
    detail = f"Deck {deck_id}: candidate_pins must be a list of objects, each with a non-empty string name."
    pins = deck["candidate_pins"]
    if not isinstance(pins, list):
        reference = CardReference(deck_id, deck_file, "candidate_pins", repr(pins), False)
        yield ValidationIssue("invalid_candidate_pins", reference, detail)
        return
    for index, item in enumerate(pins):
        name = item.get("name") if isinstance(item, Mapping) else None
        if not isinstance(name, str) or not name.strip():
            reference = CardReference(deck_id, deck_file, f"candidate_pins[{index}]", repr(item), False)
            yield ValidationIssue("invalid_candidate_pins", reference, detail)


def iter_min_x_issues(
    deck: Mapping[str, object],
    deck_file: Path,
    scryfall_index: ScryfallNameIndex,
    deck_names: set[str],
) -> Iterator[ValidationIssue]:
    """Yield issues for each win condition's optional `minX`: on a `kind: "combo"`
    entry whose `pieces` is a list, a mapping from pieces of that line named exactly as
    the deck lists them (`deck_names`: commander, partner, decklist; a face name does
    not match) whose front-face mana cost has {X} to positive integers (the X each is
    priced at; export_simulation_results.extract_combo_lines raises on the same inputs)."""
    deck_id = str(deck.get("id") or deck_file.parent.name)
    wincons = deck.get("winConditions")
    if not isinstance(wincons, list):
        return
    for index, wincon in enumerate(wincons):
        if not isinstance(wincon, Mapping) or "minX" not in wincon:
            continue
        detail = (f"Deck {deck_id}: winConditions[{index}].minX must be on a kind \"combo\" entry with a list of "
                  "pieces and map pieces of that line, named as the deck lists them, whose mana cost has {X} to "
                  "positive integers.")
        min_x = wincon["minX"]
        pieces = wincon.get("pieces")
        if not isinstance(min_x, Mapping) or wincon.get("kind") != "combo" or not isinstance(pieces, list):
            reference = CardReference(deck_id, deck_file, f"winConditions[{index}].minX", repr(min_x), False)
            yield ValidationIssue("invalid_min_x", reference, detail)
            continue
        for piece, x in min_x.items():
            if (piece not in pieces or piece not in deck_names
                    or type(x) is not int or x < 1 or "{X}" not in scryfall_index.mana_cost(piece)):
                reference = CardReference(deck_id, deck_file, f"winConditions[{index}].minX", piece, False)
                yield ValidationIssue("invalid_min_x", reference, detail)


def iter_tag_issues(
    deck: Mapping[str, object],
    deck_file: Path,
    scryfall_index: ScryfallNameIndex,
) -> Iterator[ValidationIssue]:
    """Yield one issue per error gate_tags_lib.entry_errors finds in a decklist
    entry's tags: a key that names a tutor or recursion field ("tutor" or
    "recursion" in it, any case) that the vocabulary does not define, a value
    outside its field's set, a role that is not a string, a tag without its
    role, a missing recursion_mode
    in a deck with a combo win condition, an "X" cap on a card that pays no
    {X}. The exporter (substitute_tables) runs the same check and raises."""
    deck_id = str(deck.get("id") or deck_file.parent.name)
    decklist = deck.get("decklist")
    if not isinstance(decklist, list):
        return
    wincons = deck.get("winConditions")
    has_combo_line = isinstance(wincons, list) and any(
        isinstance(wincon, Mapping) and wincon.get("kind") == "combo" for wincon in wincons)
    for index, entry in enumerate(decklist):
        if not isinstance(entry, Mapping):
            continue
        front = scryfall_index.front(str(entry.get("name")))
        for error in gate_tags_lib.entry_errors(entry, has_combo_line, front):
            reference = CardReference(deck_id, deck_file, f"decklist[{index}]", str(entry.get("name")), False)
            yield ValidationIssue("invalid_tag", reference, f"Deck {deck_id}: {error}")


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

        issues.extend(iter_candidate_pin_issues(deck, deck_file))
        deck_names = {reference.name for reference in iter_deck_core_references(deck, deck_file)}
        issues.extend(iter_min_x_issues(deck, deck_file, scryfall_index, deck_names))
        issues.extend(iter_tag_issues(deck, deck_file, scryfall_index))

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
            "mirror or point outside the decklist, or if candidate_pins, a "
            "win condition's minX or a decklist entry's tutor/recursion tags "
            "are malformed."
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
