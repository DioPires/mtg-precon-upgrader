#!/usr/bin/env python3
"""DEC-90 P7.3 heuristic role auto-tagger.

Reads decklist + the local Scryfall mirror and emits `primary_role` per card
based on oracle-text and type-line heuristics. Targets seven roles:
land, ramp, card-draw, tutor, removal-spot, removal-board, counterspell.

Other roles in the 15-role taxonomy (engine, payoff, wincon, threat, utility,
protection, recursion, mana-fixing) require human judgment and are left
untagged.

Confidence bands (per `docs/role-taxonomy.md` and DEC-117):
    >= 0.75   auto-apply primary_role
    0.5-0.75  auto-apply + set `_needs_review: true`
    < 0.5     leave primary_role untouched

Existing `primary_role` values are never overwritten unless --force.

Usage:
    python scripts/auto_tag_roles.py --deck DECK_ID [--force] [--dry-run]
    python scripts/auto_tag_roles.py --all [--force] [--dry-run]
    python scripts/auto_tag_roles.py --all --retag-tutors [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DECKS_DIR = PROJECT_ROOT / "data" / "commanders"
MIRROR_FILE = PROJECT_ROOT / "priv_data" / "scryfall-oracle.json"

AUTO_APPLY_THRESHOLD = 0.75
REVIEW_THRESHOLD = 0.5


def load_mirror() -> dict[str, dict]:
    if not MIRROR_FILE.exists():
        print(f"missing scryfall mirror: {MIRROR_FILE}", file=sys.stderr)
        print("run: python scripts/refresh_scryfall_mirror.py", file=sys.stderr)
        sys.exit(2)
    cards = json.loads(MIRROR_FILE.read_text())
    by_name: dict[str, dict] = {}
    for c in cards:
        by_name[c["name"]] = c
        # Index DFC front-face name too so deck.json that stores only the
        # front face (e.g. "Bala Ged Recovery") still resolves.
        for face in c.get("card_faces") or []:
            fname = face.get("name")
            if fname and fname not in by_name:
                by_name[fname] = c
    return by_name


def spell_oracle_and_type(card: dict) -> tuple[str, str]:
    """Return (oracle_text, type_line) for the spell-relevant face.

    For MDFCs whose back face is a Land, only the front face is used (the
    land back is captured separately via `is_mdfc_land`). Other DFCs
    concatenate both faces so transform creatures, etc., are detected from
    either side.
    """
    faces = card.get("card_faces") or []
    if len(faces) == 2:
        front_type = (faces[0].get("type_line") or "").lower()
        back_type = (faces[1].get("type_line") or "").lower()
        front_is_land = "land" in front_type
        back_is_land = "land" in back_type
        if back_is_land and not front_is_land:
            return faces[0].get("oracle_text") or "", faces[0].get("type_line") or ""
        if front_is_land and not back_is_land:
            return faces[0].get("oracle_text") or "", faces[0].get("type_line") or ""
        oracle = "\n".join(f.get("oracle_text", "") for f in faces if f.get("oracle_text"))
        type_line = " // ".join(f.get("type_line", "") for f in faces if f.get("type_line"))
        return oracle, type_line
    return card.get("oracle_text") or "", card.get("type_line") or ""


def is_mdfc_with_land_back(card: dict) -> bool:
    faces = card.get("card_faces") or []
    if len(faces) != 2:
        return False
    front_is_land = "land" in (faces[0].get("type_line") or "").lower()
    back_is_land = "land" in (faces[1].get("type_line") or "").lower()
    return back_is_land and not front_is_land


# ---- Heuristic detectors ----------------------------------------------------
# Each detector takes lowercased oracle text + type line and returns
# (role, confidence) or None. Detector order in DETECTORS is priority order:
# land first (definitive), then specific spell roles, with card-draw last
# because many engines/payoffs incidentally mention drawing.

def _detect_land(oracle: str, type_line: str, card: dict) -> tuple[str, float] | None:
    if is_mdfc_with_land_back(card):
        return None
    if "land" in (card.get("type_line") or "").lower():
        return ("land", 0.99)
    return None


def _detect_counterspell(oracle: str, type_line: str) -> tuple[str, float] | None:
    if re.search(r"counter target (?:[\w\-]+ )*spell", oracle):
        return ("counterspell", 0.95)
    return None


_LAND_SEARCH = re.compile(
    r"search your library for .{0,80}?(?:basic land|land cards?|plains|island|swamp|mountain|forest)",
    re.DOTALL,
)

_MANA_DEVELOPMENT_LAND_SEARCH = re.compile(
    r"search your library for .{0,80}?(?:basic land|plains|island|swamp|mountain|forest)",
    re.DOTALL,
)

_UNRESTRICTED_LAND_TUTOR = re.compile(
    r"search your library for (?:a |an |up to (?:one|two) )?land cards?",
    re.DOTALL,
)

_SEARCH_LIBRARY = re.compile(r"search your library for", re.DOTALL)


def _detect_ramp(oracle: str, type_line: str) -> tuple[str, float] | None:
    if _LAND_SEARCH.search(oracle):
        return ("ramp", 0.9)
    if re.search(r"\{t\}:\s*add\s*\{", oracle) or re.search(
        r"\{t\}:\s*add\s+(?:one|two|three|x|that many)\s+mana", oracle
    ):
        return ("ramp", 0.85)
    if "instant" in type_line or "sorcery" in type_line:
        # Ritual-style: an Add-mana clause that isn't a tapped ability
        if re.search(r"(?:^|[\.\n])\s*add\s+\{", oracle):
            return ("ramp", 0.75)
    return None


def _detect_tutor(oracle: str, type_line: str) -> tuple[str, float] | None:
    if "search your library for" not in oracle:
        return None
    if _LAND_SEARCH.search(oracle):
        return None  # land searches are ramp
    return ("tutor", 0.85)


def _detect_removal_board(oracle: str, type_line: str) -> tuple[str, float] | None:
    if re.search(
        r"destroy all (?:creatures|permanents|nonland permanents|artifacts|enchantments|"
        r"planeswalkers|nonbasic lands|attacking creatures)",
        oracle,
    ):
        return ("removal-board", 0.9)
    if re.search(
        r"exile all (?:creatures|permanents|nonland permanents|artifacts|enchantments|planeswalkers)",
        oracle,
    ):
        return ("removal-board", 0.9)
    if re.search(r"destroy each (?:other )?(?:creature|permanent|nonland)", oracle):
        return ("removal-board", 0.9)
    if re.search(
        r"return all (?:creatures|nonland permanents|permanents) to (?:their owners'|its owner's) hand",
        oracle,
    ):
        return ("removal-board", 0.9)
    if re.search(
        r"deals \d+ damage to each (?:creature|opponent and each creature|other creature)", oracle
    ):
        return ("removal-board", 0.85)
    if "each player sacrifices" in oracle:
        return ("removal-board", 0.85)
    if re.search(r"each (?:other )?creature gets -\d+/-\d+", oracle):
        return ("removal-board", 0.85)
    return None


def _detect_removal_spot(oracle: str, type_line: str) -> tuple[str, float] | None:
    m = re.search(
        r"(?:destroy|exile) target (?:creature|artifact|enchantment|planeswalker|"
        r"permanent|nonland permanent|nonland|battle|nontoken creature|tapped creature|"
        r"attacking creature|blocking creature|land)",
        oracle,
    )
    if m:
        # "destroy target creature you control" — that's a sac outlet, not removal.
        if re.search(r"(?:destroy|exile) target (?:creature|permanent) you control", oracle):
            return ("utility", 0.6)
        return ("removal-spot", 0.85)
    if re.search(
        r"return target (?:creature|nonland permanent|permanent) to (?:its|their) owner['’]?s? hand",
        oracle,
    ):
        return ("removal-spot", 0.8)
    if re.search(r"target creature gets -\d+/-\d+", oracle):
        return ("removal-spot", 0.65)
    return None


def _detect_card_draw(oracle: str, type_line: str) -> tuple[str, float] | None:
    has_draw = (
        re.search(
            r"draws? (?:a|one|two|three|four|five|six|seven|eight|nine|ten|x|that many|\d+) cards?",
            oracle,
        )
        or "draw cards equal to" in oracle
    )
    if not has_draw:
        return None
    # Creature with an "enters" trigger that draws is more often classified
    # engine/value than pure card-draw — hand off to human review.
    if "creature" in type_line and re.search(r"when (?:this creature|\w+) enters", oracle):
        return ("card-draw", 0.65)
    return ("card-draw", 0.85)


DETECTORS = (
    _detect_land,
    _detect_counterspell,
    _detect_ramp,
    _detect_removal_board,
    _detect_tutor,
    _detect_removal_spot,
    _detect_card_draw,
)


def classify(card_data: dict) -> tuple[str | None, float]:
    """Return (primary_role, confidence). (None, 0.0) when nothing matches."""
    oracle, type_line = spell_oracle_and_type(card_data)
    oracle_lc = oracle.lower()
    type_lc = type_line.lower()
    for fn in DETECTORS:
        result = (
            fn(oracle_lc, type_lc, card_data) if fn is _detect_land else fn(oracle_lc, type_lc)
        )
        if result:
            return result
    return (None, 0.0)


def _is_land_card(card_data: dict) -> bool:
    if is_mdfc_with_land_back(card_data):
        return False
    return "land" in (card_data.get("type_line") or "").lower()


def _has_permanent_face(type_line: str) -> bool:
    return any(
        token in type_line
        for token in ("artifact", "creature", "enchantment", "planeswalker", "battle")
    )


def classify_tutor_roles(
    card_data: dict, existing_primary: str | None
) -> tuple[str, str | None, float] | None:
    """Return a primary/secondary tutor retag when oracle text warrants one.

    This is intentionally narrower than --force: it only changes cards with
    library-search tutor text, leaving unrelated role judgments untouched.
    """
    oracle, type_line = spell_oracle_and_type(card_data)
    oracle_lc = oracle.lower()
    type_lc = type_line.lower()
    if not _SEARCH_LIBRARY.search(oracle_lc):
        return None

    is_mana_land_search = bool(_MANA_DEVELOPMENT_LAND_SEARCH.search(oracle_lc))
    is_unrestricted_land_tutor = bool(_UNRESTRICTED_LAND_TUTOR.search(oracle_lc))

    if is_mana_land_search and not is_unrestricted_land_tutor:
        return None

    if _is_land_card(card_data):
        return ("land", "tutor", 0.9)

    is_instant_or_sorcery = "instant" in type_lc or "sorcery" in type_lc
    has_permanent_face = _has_permanent_face(type_lc)

    if "counter target" in oracle_lc and "transmute" in oracle_lc:
        return (existing_primary or "counterspell", "tutor", 0.85)

    if "planeswalker" in type_lc:
        return (existing_primary or "engine", "tutor", 0.75)

    repeatable_or_engine_tutor = (
        re.search(r"\{t\}.{0,160}search your library", oracle_lc, re.DOTALL)
        or "becomes prepared" in oracle_lc
        or re.search(r"search your library.{0,160}activate only as a sorcery", oracle_lc, re.DOTALL)
        or re.search(r"whenever[^.]+search your library", oracle_lc, re.DOTALL)
    )
    if has_permanent_face and repeatable_or_engine_tutor:
        return ("engine", "tutor", 0.85)

    if is_unrestricted_land_tutor:
        secondary = "ramp" if "onto the battlefield" in oracle_lc else None
        return ("tutor", secondary, 0.85)

    if is_instant_or_sorcery and not has_permanent_face:
        return ("tutor", None, 0.9)

    if has_permanent_face:
        secondary = None
        if "costs {" in oracle_lc and "less to cast" in oracle_lc:
            secondary = "ramp"
        elif "untap another target permanent" in oracle_lc:
            secondary = "engine"
        return ("tutor", secondary, 0.8)

    return ("tutor", None, 0.8)


# ---- Per-deck processing ----------------------------------------------------

def process_deck(path: Path, mirror: dict, force: bool, retag_tutors: bool) -> dict:
    deck = json.loads(path.read_text())
    deck_id = deck.get("id") or path.parent.name
    proposals = []
    cards_changed = 0

    for card in deck.get("decklist", []):
        name = card.get("name", "")
        existing = card.get("primary_role")
        if not retag_tutors and existing and not force:
            continue
        scry = mirror.get(name)
        if not scry and " // " in name:
            scry = mirror.get(name.split(" // ", 1)[0])
        if not scry:
            proposals.append(
                {"name": name, "old": existing, "new": None, "confidence": 0.0, "action": "missing"}
            )
            continue

        old_secondary = card.get("secondary_role")
        if retag_tutors:
            tutor_roles = classify_tutor_roles(scry, existing)
            if not tutor_roles:
                continue
            new_role, new_secondary, conf = tutor_roles
            changed = existing != new_role or old_secondary != new_secondary
            proposals.append(
                {
                    "name": name,
                    "old": existing,
                    "old_secondary": old_secondary,
                    "new": new_role,
                    "new_secondary": new_secondary,
                    "confidence": round(conf, 2),
                    "action": "apply" if changed else "unchanged",
                    "needs_review": False,
                }
            )
            if not changed:
                continue
            card["primary_role"] = new_role
            if new_secondary:
                card["secondary_role"] = new_secondary
            elif "secondary_role" in card:
                del card["secondary_role"]
            if "_needs_review" in card:
                del card["_needs_review"]
            cards_changed += 1
            continue

        role, conf = classify(scry)
        if conf >= AUTO_APPLY_THRESHOLD:
            action, new_role, needs_review = "apply", role, False
        elif conf >= REVIEW_THRESHOLD:
            action, new_role, needs_review = "review", role, True
        else:
            action, new_role, needs_review = "low", None, False

        proposals.append(
            {
                "name": name,
                "old": existing,
                "old_secondary": old_secondary,
                "new": new_role,
                "new_secondary": None,
                "confidence": round(conf, 2),
                "action": action,
                "needs_review": needs_review,
            }
        )

        if new_role:
            card["primary_role"] = new_role
            if needs_review:
                card["_needs_review"] = True
            elif "_needs_review" in card:
                del card["_needs_review"]
            cards_changed += 1

    return {
        "deck_id": deck_id,
        "path": path,
        "deck": deck,
        "proposals": proposals,
        "cards_changed": cards_changed,
    }


def print_report(result: dict, dry_run: bool) -> None:
    deck_id = result["deck_id"]
    proposals = result["proposals"]
    by_action: dict[str, list] = {"apply": [], "review": [], "low": [], "missing": [], "unchanged": []}
    for p in proposals:
        by_action[p["action"]].append(p)
    print(f"\n[{deck_id}]")
    print(
        f"  apply: {len(by_action['apply'])}  review: {len(by_action['review'])}  "
        f"low: {len(by_action['low'])}  missing: {len(by_action['missing'])}  "
        f"unchanged: {len(by_action['unchanged'])}"
    )
    if not dry_run:
        return
    for p in by_action["apply"]:
        old_role = str(p["old"])
        old_secondary = p.get("old_secondary")
        old = f"{old_role}/{old_secondary}" if old_secondary else old_role
        new_role = p["new"]
        new_secondary = p.get("new_secondary")
        new = f"{new_role}/{new_secondary}" if new_secondary else new_role
        print(
            f"    APPLY    {p['confidence']:.2f}  {old:>22} -> {new:<22} {p['name']}"
        )
    for p in by_action["review"]:
        print(
            f"    REVIEW   {p['confidence']:.2f}  {str(p['old']):>14} -> {p['new']:<14} {p['name']}  (_needs_review)"
        )
    for p in by_action["low"]:
        print(f"    LOW      {p['confidence']:.2f}  {p['name']}")
    for p in by_action["missing"]:
        print(f"    MISSING  ----  {p['name']}")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Heuristic primary_role auto-tagger (DEC-117)")
    target = parser.add_mutually_exclusive_group()
    target.add_argument("--deck", help="Single deck id")
    target.add_argument("--all", action="store_true", help="All decks")
    parser.add_argument(
        "--force", action="store_true", help="Overwrite existing primary_role values"
    )
    parser.add_argument(
        "--retag-tutors",
        action="store_true",
        help="Correct existing library-search cards to tutor primary/secondary roles only",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Print proposed diffs; don't write deck.json"
    )
    args = parser.parse_args(argv)

    if not args.deck and not args.all:
        args.all = True

    if args.deck:
        paths = [DECKS_DIR / args.deck / "deck.json"]
    else:
        paths = sorted(DECKS_DIR.glob("*/deck.json"))

    mirror = load_mirror()

    total_changed = 0
    for p in paths:
        if not p.exists():
            print(f"missing: {p}", file=sys.stderr)
            continue
        result = process_deck(p, mirror, args.force, args.retag_tutors)
        print_report(result, args.dry_run)
        if not args.dry_run and result["cards_changed"] > 0:
            p.write_text(json.dumps(result["deck"], indent=2, ensure_ascii=False) + "\n")
        total_changed += result["cards_changed"]

    print(f"\nTotal cards updated: {total_changed}")
    if args.dry_run:
        print("(dry run — no files written)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
