#!/usr/bin/env python3
"""Combo Lab KB coverage gate (DEC-476 Phase 1 / DEC-488).

Deterministic coverage check for the two-stage Phase-1 gate:

  Stage 1 (Phase-2 entry gate): the KB must cover
    (a) every card in every fleet decklist (data/commanders/*/deck.json), and
    (b) the top-N (default 2,000) cards by Spellbook variant-membership count,
        computed from the local corpus (data/spellbook/matcher-index.json).

  Stage full (Phase-4 entry gate): the KB must cover every Commander-legal card
    in the local Scryfall mirror (31,830).

"Cover" = a KB entry exists for the card (existence, not LLM completeness).
Exit 0 iff the requested stage is fully covered; 1 otherwise, listing misses.

Usage:
    uv run python scripts/check_kb_coverage.py               # stage 1
    uv run python scripts/check_kb_coverage.py --stage full
    uv run python scripts/check_kb_coverage.py --top-n 2000 --json
"""

from __future__ import annotations

import argparse
import glob
import json
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
COMMANDERS_DIR = PROJECT_ROOT / "data" / "commanders"
MATCHER_INDEX = PROJECT_ROOT / "data" / "spellbook" / "matcher-index.json"
MIRROR_FILE = PROJECT_ROOT / "priv_data" / "scryfall-oracle.json"
ENTRIES_DIR = PROJECT_ROOT / "data" / "combo-kb" / "entries"


def front_face(name: str) -> str:
    return name.split(" // ", 1)[0]


def face_aliases(name: str) -> set[str]:
    """A DFC entry covers a decklist line naming EITHER face (a deck may list
    the transformed back face, e.g. 'The Invincible Iron Man' for the entry
    'Tony Stark // The Invincible Iron Man'). Alias the full name and every
    face."""
    return {name, *(p.strip() for p in name.split(" // "))}


def load_kb_names() -> set[str]:
    """Return every name the KB covers, including per-face aliases so that a
    decklist line naming any single face matches the full DFC entry."""
    names: set[str] = set()
    for fp in ENTRIES_DIR.glob("*.json"):
        for e in json.loads(Path(fp).read_text(encoding="utf-8")):
            nm = e.get("name")
            if nm:
                names |= face_aliases(nm)
    return names


def fleet_cards() -> set[str]:
    cards: set[str] = set()
    for deck_path in sorted(COMMANDERS_DIR.glob("*/deck.json")):
        deck = json.loads(deck_path.read_text(encoding="utf-8"))
        commander = deck.get("commander")
        if commander:
            for part in str(commander).split(" // "):
                cards.add(part.strip())
        for card in deck.get("decklist") or []:
            nm = (card.get("name") if isinstance(card, dict) else card) or ""
            if nm:
                cards.add(front_face(nm.strip()))
    return cards


def top_variant_cards(top_n: int) -> list[str]:
    """Top-N card names by Spellbook variant-membership count from the local
    corpus. Each variant lists its used card ids in ``u``; tally across all."""
    idx = json.loads(MATCHER_INDEX.read_text(encoding="utf-8"))
    id_to_name = {cid: c["n"] for cid, c in idx["cards"].items()}
    membership: Counter = Counter()
    for variant in idx["variants"]:
        for cid in variant.get("u", []):
            name = id_to_name.get(str(cid)) or id_to_name.get(cid)
            if name:
                membership[name] += 1
    return [name for name, _ in membership.most_common(top_n)]


def mirror_names() -> set[str]:
    names: set[str] = set()
    for card in json.loads(MIRROR_FILE.read_text(encoding="utf-8")):
        nm = card.get("name")
        if nm:
            names |= face_aliases(nm)
    return names


def report_group(label: str, required: set[str], kb: set[str]) -> tuple[int, list[str]]:
    misses = sorted(n for n in required if n not in kb)
    covered = len(required) - len(misses)
    status = "OK" if not misses else "MISS"
    print(f"[{status}] {label}: {covered}/{len(required)} covered", file=sys.stderr)
    return covered, misses


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["1", "full"], default="1")
    ap.add_argument("--top-n", type=int, default=2000)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if not any(ENTRIES_DIR.glob("*.json")):
        print("ERROR: no KB entries. Run build_combo_kb.py first.", file=sys.stderr)
        return 1

    kb = load_kb_names()
    result = {"stage": args.stage, "kb_name_count": len(kb), "groups": {}}
    all_misses: list[str] = []

    fleet = fleet_cards()
    covered, misses = report_group("fleet decklist cards", fleet, kb)
    result["groups"]["fleet"] = {"required": len(fleet), "covered": covered,
                                 "misses": misses}
    all_misses += misses

    if args.stage == "1":
        top = set(top_variant_cards(args.top_n))
        covered, misses = report_group(
            f"top-{args.top_n} Spellbook variant-membership cards", top, kb)
        result["groups"]["top_variant"] = {"required": len(top), "covered": covered,
                                           "misses": misses}
        all_misses += misses
    else:
        mirror = mirror_names()
        covered, misses = report_group("full Commander-legal pool (mirror)", mirror, kb)
        result["groups"]["full_pool"] = {"required": len(mirror), "covered": covered,
                                        "misses": misses}
        all_misses += misses

    passed = not all_misses
    result["passed"] = passed
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"\nSTAGE {args.stage}: {'PASS' if passed else 'FAIL'}"
              f" ({len(all_misses)} miss(es))")
        for m in all_misses[:25]:
            print(f"  miss: {m}")
        if len(all_misses) > 25:
            print(f"  ... and {len(all_misses) - 25} more")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
