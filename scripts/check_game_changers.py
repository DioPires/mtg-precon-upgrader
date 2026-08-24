#!/usr/bin/env python3
"""Game Changers drift check (DEC-396, trigger 1 of the fleet re-audit policy).

Three checks, any failure exits 1:

1. **List drift** — diff `data/game-changers.json` against the live Scryfall
   `format:commander is:gamechanger` search (paginated; Scryfall requires a
   User-Agent header, per DEC-370). Skip with `--offline`.
2. **Mirror sync** — the `web/src/data/gameChangers.ts` copy must contain the
   exact same card set as the JSON source of truth.
3. **Fleet recount** — every deck's `gameChangers` field must equal the count
   of its `decklist` names on the GC list (front face for MDFCs), and the
   count must respect the bracket cap: brackets 1-3 and 3+ cap at 3 GCs,
   4-/4/4+/5 are uncapped, plus per-deck hard caps set by the board
   (DEC-369: verdant-tide <= 1).

Policy context: AGENTS.md "Fleet Re-Audit Policy". On list drift, update the
JSON + TS copies together, then re-run for the corrected fleet recount.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GC_JSON = PROJECT_ROOT / "data" / "game-changers.json"
GC_TS = PROJECT_ROOT / "web" / "src" / "data" / "gameChangers.ts"
INDEX_JSON = PROJECT_ROOT / "data" / "index.json"
COMMANDERS_DIR = PROJECT_ROOT / "data" / "commanders"

SCRYFALL_SEARCH = "https://api.scryfall.com/cards/search"
USER_AGENT = "mtg-precon-upgrader/1.0 (github.com/DioPires/mtg-precon-upgrader)"

# Board-set hard caps (DEC-369); bracket caps are derived from `bracket`.
HARD_CAPS = {"verdant-tide": 1}


def front_face(name: str) -> str:
    return name.split(" // ")[0]


def fetch_remote_gc_names() -> set[str]:
    query = urllib.parse.quote("format:commander is:gamechanger")
    url = f"{SCRYFALL_SEARCH}?q={query}"
    names: set[str] = set()
    while url:
        req = urllib.request.Request(
            url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            page = json.load(resp)
        names.update(front_face(card["name"]) for card in page["data"])
        url = page.get("next_page")
    return names


def parse_ts_mirror() -> set[str]:
    text = GC_TS.read_text(encoding="utf-8")
    match = re.search(r"GAME_CHANGERS[^=]*=\s*\[(.*?)\]", text, re.DOTALL)
    if not match:
        raise ValueError(f"could not find GAME_CHANGERS array in {GC_TS}")
    return {
        m.group(2).replace("\\'", "'").replace('\\"', '"')
        for m in re.finditer(r"(['\"])((?:\\.|(?!\1).)*)\1", match.group(1))
    }


def bracket_cap(bracket: str | None) -> int | None:
    if bracket is None:
        return None
    base = bracket.rstrip("+-")
    return 3 if base in {"1", "2", "3"} else None


def check_fleet(gc_names: set[str]) -> list[str]:
    problems: list[str] = []
    index = json.loads(INDEX_JSON.read_text(encoding="utf-8"))
    for entry in index["commanders"]:
        deck_id = entry["id"]
        deck_path = COMMANDERS_DIR / deck_id / "deck.json"
        if not deck_path.exists():
            problems.append(f"{deck_id}: missing deck.json")
            continue
        deck = json.loads(deck_path.read_text(encoding="utf-8"))
        actual = sorted(
            card["name"]
            for card in deck.get("decklist", [])
            if front_face(card["name"]) in gc_names
        )
        field = deck.get("gameChangers")
        if field != len(actual):
            problems.append(
                f"{deck_id}: gameChangers field {field} != recount {len(actual)} ({actual})"
            )
        cap = HARD_CAPS.get(deck_id, bracket_cap(deck.get("bracket")))
        if cap is not None and len(actual) > cap:
            cap_kind = "hard cap" if deck_id in HARD_CAPS else "bracket cap"
            problems.append(
                f"{deck_id}: {len(actual)} GCs exceeds {cap_kind} {cap} "
                f"(bracket {deck.get('bracket')}): {actual}"
            )
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--offline",
        action="store_true",
        help="skip the live Scryfall diff (mirror sync + fleet recount only)",
    )
    args = parser.parse_args()

    local = {front_face(n) for n in json.loads(GC_JSON.read_text(encoding="utf-8"))["cards"]}
    problems: list[str] = []

    if args.offline:
        print("list drift: SKIPPED (--offline)")
    else:
        remote = fetch_remote_gc_names()
        added = sorted(remote - local)
        removed = sorted(local - remote)
        if added or removed:
            problems.append(f"list drift: +{added} -{removed}")
        print(f"list drift: {'DRIFT' if added or removed else 'ok'} "
              f"(local {len(local)}, scryfall {len(remote)})")

    ts_names = {front_face(n) for n in parse_ts_mirror()}
    if ts_names != local:
        problems.append(
            f"ts mirror out of sync: ts-only {sorted(ts_names - local)}, "
            f"json-only {sorted(local - ts_names)}"
        )
    print(f"ts mirror: {'OUT OF SYNC' if ts_names != local else 'ok'} ({len(ts_names)} cards)")

    fleet_problems = check_fleet(local)
    problems.extend(fleet_problems)
    print(f"fleet recount: {len(fleet_problems)} problem(s)")

    for problem in problems:
        print(f"  FAIL: {problem}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
