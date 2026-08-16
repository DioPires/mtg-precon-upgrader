#!/usr/bin/env python3
"""DEC-90 P7.2 schema migration.

Renames `role` -> `primary_role` per card, normalizes legacy vocabulary into the
15-role canonical set from `docs/role-taxonomy.md`, and adds deck-root metadata
(`commanderRoles`, `wincon_style`) plus per-card `is_mdfc_land` flags.

Idempotent: safe to re-run. Cards already on canonical vocab are left alone;
already-migrated decks no-op.

Usage:
    python scripts/migrate_roles.py [--deck DECK_ID | --all] [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DECKS_DIR = PROJECT_ROOT / "data" / "commanders"

CANONICAL_ROLES = {
    "land", "ramp", "mana-fixing", "card-draw", "tutor",
    "removal-spot", "removal-board", "counterspell", "protection",
    "recursion", "payoff", "wincon", "engine", "threat", "utility",
}

# Mapping from legacy `role` strings to canonical `primary_role`. Keys are
# lowercased on lookup. Values outside this map (and not already canonical)
# are passed through unchanged + flagged for review.
ROLE_MAP = {
    "land": "land",
    "lands": "land",
    "ramp": "ramp",
    "card-draw": "card-draw",
    "draw": "card-draw",
    "tutor": "tutor",
    "removal": "removal-spot",
    "board-wipe": "removal-board",
    "board-wipes": "removal-board",
    "counter-spells": "counterspell",
    "counterspell": "counterspell",
    "protection": "protection",
    "recursion": "recursion",
    "reanimation": "recursion",
    "engine": "engine",
    "value": "engine",
    "enhancer": "payoff",
    "lord": "payoff",
    "tokens": "payoff",
    "token": "payoff",
    "finisher": "wincon",
    "finishers": "wincon",
    "death-payoff": "payoff",
    "sac-outlet": "utility",
    "graveyard-setup": "utility",
    "graveyard-hate": "utility",
}

# Deck-root metadata. wincon_style ∈ {combo, value-incremental, discrete-threats}.
# commanderRoles uses the canonical 15-role set.
DECK_META = {
    "creeping-corruption": {
        "wincon_style": "value-incremental",
        "commanderRoles": {"primary": "engine", "secondary": "threat"},
    },
    "gathering-shadow": {
        "wincon_style": "value-incremental",
        "commanderRoles": {"primary": "engine", "secondary": "card-draw"},
    },
    "eternal-agony": {
        "wincon_style": "value-incremental",
        "commanderRoles": {"primary": "engine", "secondary": "payoff"},
    },
    "eternal-harvest": {
        "wincon_style": "value-incremental",
        "commanderRoles": {"primary": "engine", "secondary": "recursion"},
    },
    "witherbloom-the-balancer": {
        "wincon_style": "value-incremental",
        "commanderRoles": {"primary": "payoff", "secondary": "threat"},
    },
    "the-white-forge": {
        "wincon_style": "value-incremental",
        "commanderRoles": {"primary": "engine", "secondary": "recursion"},
    },
    "titan-convergence": {
        "wincon_style": "discrete-threats",
        "commanderRoles": {"primary": "engine", "secondary": "threat"},
    },
    "verdant-tide": {
        "wincon_style": "discrete-threats",
        "commanderRoles": {"primary": "engine", "secondary": "ramp"},
    },
}


# MDFCs whose front face is a non-land spell and back face is a land.
# Local deck.json type strings only carry one face, so we resolve via this
# explicit list. P7.3 auto-tagger replaces this with Scryfall lookup.
KNOWN_MDFC_LANDS = {
    "Sea Gate Restoration // Sea Gate, Reborn",
    "Bala Ged Recovery // Bala Ged Sanctuary",
    "Shatterskull Smashing // Shatterskull, the Hammer Pass",
    "Turntimber Symbiosis // Turntimber, Serpentine Wood",
    "Agadeem's Awakening // Agadeem, the Undercrypt",
    "Emeria's Call // Emeria, Shattered Skyclave",
    "Glasspool Mimic // Glasspool Shore",
    "Malakir Rebirth // Malakir Mire",
    "Murkfiend Liege // (none)",  # placeholder; never matches
}


def is_mdfc_land(card: dict) -> bool:
    return card.get("name") in KNOWN_MDFC_LANDS


def migrate_card(card: dict, report: dict) -> dict:
    """Mutates the card dict to canonical schema. Idempotent."""
    # 1. Rename role -> primary_role
    if "role" in card and "primary_role" not in card:
        card["primary_role"] = card.pop("role")
    elif "role" in card and "primary_role" in card:
        # both present: keep primary_role, drop legacy role
        del card["role"]

    # 2. Normalize vocabulary
    pr = card.get("primary_role")
    if isinstance(pr, str) and pr:
        canonical = ROLE_MAP.get(pr.lower(), pr if pr in CANONICAL_ROLES else None)
        if canonical is None:
            report["unmapped"].append((card.get("name"), pr))
        elif canonical != pr:
            report["normalized"].append((card.get("name"), pr, canonical))
            card["primary_role"] = canonical
    elif pr == "":
        # explicit empty string: drop so auto-tagger (P7.3) can fill it later
        del card["primary_role"]
        report["cleared_empty"] += 1

    # secondary_role: same normalization if present
    sr = card.get("secondary_role")
    if isinstance(sr, str) and sr:
        canonical = ROLE_MAP.get(sr.lower(), sr if sr in CANONICAL_ROLES else None)
        if canonical and canonical != sr:
            card["secondary_role"] = canonical
        elif canonical is None:
            report["unmapped"].append((card.get("name"), f"secondary:{sr}"))

    # 3. Mark MDFC lands
    if is_mdfc_land(card):
        if not card.get("is_mdfc_land"):
            card["is_mdfc_land"] = True
            report["mdfc_marked"].append(card.get("name"))

    return card


def migrate_deck(path: Path, dry_run: bool) -> dict:
    deck = json.loads(path.read_text())
    deck_id = deck.get("id") or path.parent.name
    report = {
        "deck_id": deck_id,
        "normalized": [],
        "unmapped": [],
        "mdfc_marked": [],
        "cleared_empty": 0,
        "deck_meta_added": False,
    }

    decklist = deck.get("decklist", [])
    for card in decklist:
        migrate_card(card, report)

    meta = DECK_META.get(deck_id)
    if meta:
        if deck.get("wincon_style") != meta["wincon_style"]:
            deck["wincon_style"] = meta["wincon_style"]
            report["deck_meta_added"] = True
        existing_cmd = deck.get("commanderRoles") or {}
        if existing_cmd != meta["commanderRoles"]:
            deck["commanderRoles"] = meta["commanderRoles"]
            report["deck_meta_added"] = True

    if not dry_run:
        path.write_text(json.dumps(deck, indent=2) + "\n")

    return report


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    target = parser.add_mutually_exclusive_group()
    target.add_argument("--deck", help="Single deck id")
    target.add_argument("--all", action="store_true", help="All decks")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    if not args.deck and not args.all:
        args.all = True

    if args.deck:
        paths = [DECKS_DIR / args.deck / "deck.json"]
    else:
        paths = sorted(DECKS_DIR.glob("*/deck.json"))

    total_normalized = 0
    total_unmapped = 0
    total_mdfc = 0
    for p in paths:
        if not p.exists():
            print(f"missing: {p}", file=sys.stderr)
            continue
        r = migrate_deck(p, args.dry_run)
        total_normalized += len(r["normalized"])
        total_unmapped += len(r["unmapped"])
        total_mdfc += len(r["mdfc_marked"])
        print(f"\n[{r['deck_id']}]")
        print(f"  normalized: {len(r['normalized'])}  unmapped: {len(r['unmapped'])}  "
              f"mdfc: {len(r['mdfc_marked'])}  cleared_empty: {r['cleared_empty']}  "
              f"deck_meta_added: {r['deck_meta_added']}")
        for name, old in r["unmapped"][:5]:
            print(f"    UNMAPPED  {name!r}: {old!r}")
        for name, old, new in r["normalized"][:5]:
            print(f"    {old!r} -> {new!r}  ({name})")
        for name in r["mdfc_marked"]:
            print(f"    MDFC      {name!r}")

    print(f"\nTotals: normalized={total_normalized}  unmapped={total_unmapped}  mdfc={total_mdfc}")
    if args.dry_run:
        print("(dry run — no files written)")
    return 0 if total_unmapped == 0 else 0  # don't fail on unmapped; auto-tagger will resolve


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
