"""Shared helpers for the prerelease tools.

Everything here is pure: it reads a Scryfall card dump and turns it into the
small pieces the four scripts need (colour keys, oracle text, sort orders).
No network, no file writing.
"""

from __future__ import annotations

import glob
import json
import os
import re

# Colour order used everywhere in the output: white, blue, black, red, green.
COLOR_ORDER = {"W": 0, "U": 1, "B": 2, "R": 3, "G": 4}
WUBRG = "WUBRG"

RARITY_RANK = {"common": 0, "uncommon": 1, "rare": 2, "mythic": 3, "special": 4, "bonus": 5}
RARITY_LETTER = {
    "common": "C",
    "uncommon": "U",
    "rare": "R",
    "mythic": "M",
    "special": "S",
    "bonus": "B",
}


def find_one(set_dir: str, pattern: str) -> str:
    """Return the single file in set_dir matching pattern, or raise."""
    hits = sorted(glob.glob(os.path.join(set_dir, pattern)))
    if len(hits) != 1:
        raise SystemExit(
            f"expected exactly one {pattern} in {set_dir}, found {len(hits)}: {hits}"
        )
    return hits[0]


def cards_path(set_dir: str) -> str:
    """Path of the `unique=cards` dump inside a set directory."""
    return find_one(set_dir, "*_all_cards.json")


def load_cards(set_dir: str) -> list:
    with open(cards_path(set_dir), encoding="utf-8") as fh:
        return json.load(fh)


def set_code(set_dir: str) -> str:
    return os.path.basename(cards_path(set_dir)).split("_all_cards.json")[0]


def faces(card: dict) -> list:
    """The card's faces, or the card itself when it has only one."""
    return card.get("card_faces") or [card]


def oracle_text(card: dict) -> str:
    """All oracle text of the card, faces joined, lower-cased.

    Lower-casing matters: reminder text writes keyword actions in lower case,
    so a case-sensitive count undercounts mechanics (DEC-925 lesson).
    """
    if card.get("oracle_text"):
        return card["oracle_text"].lower()
    return " ".join(f.get("oracle_text", "") for f in card.get("card_faces", [])).lower()


def color_key(card_or_colors) -> str:
    """Group key for a card's colours: sorted letters, or "C" when colourless."""
    colors = (
        card_or_colors
        if isinstance(card_or_colors, (list, tuple))
        else card_or_colors.get("colors") or []
    )
    return "".join(sorted(colors)) or "C"


def color_sort_key(colors) -> tuple:
    """Sort colourless last, then mono in WUBRG order, then gold by pair, then 3+."""
    colors = list(colors or [])
    return (0 if colors else 1, len(colors), tuple(COLOR_ORDER[c] for c in sorted(colors)))


def pips(mana_cost: str) -> list:
    """The `{...}` symbols of a mana cost, front face only."""
    return re.findall(r"\{([^}]*)\}", (mana_cost or "").split(" // ")[0])


def castable(mana_cost: str, pair: str) -> bool:
    """True when every coloured pip of the front face is payable by `pair`.

    Eligibility is castability, not Scryfall's colour field (DEC-927): a
    hybrid pip belongs to both of its colours, and {2/W}, Phyrexian, generic,
    {X} and {C} are always payable.
    """
    for p in pips(mana_cost):
        if p.isdigit() or p in ("X", "C"):
            continue
        alts = p.split("/")
        if any(a.isdigit() for a in alts):
            continue
        if not any(a in pair for a in alts):
            return False
    return True


def bucket(entry: dict) -> str:
    """Section name for the cheat sheet: a colour, a gold pair, hybrid, etc."""
    cols = "".join(sorted(entry["colors"], key=lambda c: COLOR_ORDER.get(c, 9)))
    mc = entry["mana_cost"].split(" // ")[0]
    if "Land" in entry["type_line"].split(" //")[0]:
        return "Lands"
    if not cols:
        return "Colorless"
    hyb = any("/" in p and not any(a.isdigit() for a in p.split("/")) for p in pips(mc))
    if len(cols) == 1:
        return cols
    if hyb and len(cols) == 2:
        return "Hybrid (either color)"
    return "Gold " + cols if len(cols) == 2 else "Three+ colors"
