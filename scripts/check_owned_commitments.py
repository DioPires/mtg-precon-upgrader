"""Audit deck commitments against owned card quantities (DEC-528).

Aggregates every deck.json decklist (plus commanders) and compares per-card
commitment totals against priv_data/Owned.csv quantities. Basic lands are
excluded. Names are matched on the front face, casefolded, so DFC naming
differences between ManaBox exports and decklists do not create false gaps.

Usage:
    uv run python scripts/check_owned_commitments.py                 # production decks only
    uv run python scripts/check_owned_commitments.py --all           # include brewing decks
    uv run python scripts/check_owned_commitments.py --show-unowned  # also list owned-0 cards

Exit code 0 always — this is a reporting tool, not a gate. Brewing decks
intentionally commit cards we do not own yet (their decklists double as buy
lists), so the default scope is production decks, where a deficit means a
physical copy is promised to more assembled decks than exist.
"""

import argparse
import collections
import csv
import glob
import json
import os

ROOT = os.path.join(os.path.dirname(__file__), "..")
OWNED_CSV = os.path.join(ROOT, "priv_data", "Owned.csv")
INDEX_JSON = os.path.join(ROOT, "data", "index.json")
DECK_GLOB = os.path.join(ROOT, "data", "commanders", "*", "deck.json")

BASICS = {
    n.casefold()
    for n in (
        "Plains", "Island", "Swamp", "Mountain", "Forest", "Wastes",
        "Snow-Covered Plains", "Snow-Covered Island", "Snow-Covered Swamp",
        "Snow-Covered Mountain", "Snow-Covered Forest", "Snow-Covered Wastes",
    )
}


def norm(name):
    return name.split(" // ")[0].strip().casefold()


def load_owned():
    owned = collections.Counter()
    display = {}
    with open(OWNED_CSV) as f:
        for row in csv.DictReader(f):
            key = norm(row["Name"])
            owned[key] += int(row["Quantity"])
            display.setdefault(key, row["Name"].split(" // ")[0].strip())
    return owned, display


def load_commitments(include_brewing):
    with open(INDEX_JSON) as f:
        index = json.load(f)
    brewing = {c["id"] for c in index["commanders"] if c.get("brewing") or c.get("status") == "brewing"}

    commitments = collections.defaultdict(list)  # key -> [(deck_id, qty)]
    display = {}
    for path in sorted(glob.glob(DECK_GLOB)):
        with open(path) as f:
            deck = json.load(f)
        deck_id = deck["id"]
        if not include_brewing and deck_id in brewing:
            continue
        names = [(c["name"], int(c.get("quantity", 1))) for c in deck.get("decklist", [])]
        commander = deck.get("commander")
        if commander:
            names += [(n, 1) for n in ([commander] if isinstance(commander, str) else commander)]
        for name, qty in names:
            key = norm(name)
            if key in BASICS:
                continue
            commitments[key].append((deck_id, qty))
            display.setdefault(key, name.split(" // ")[0].strip())
    return commitments, display, brewing


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--all", action="store_true", help="include brewing decks in commitments")
    parser.add_argument("--show-unowned", action="store_true", help="also list committed cards with 0 owned copies")
    args = parser.parse_args()

    owned, owned_display = load_owned()
    commitments, commit_display, brewing = load_commitments(include_brewing=args.all)

    deficits, unowned = [], []
    for key, uses in commitments.items():
        total = sum(q for _, q in uses)
        have = owned.get(key, 0)
        if total > have:
            (unowned if have == 0 else deficits).append((key, have, total, uses))
    deficits.sort(key=lambda r: (r[1] - r[2], r[0]))

    scope = "all decks (incl. brewing)" if args.all else "production decks"
    print(f"Scope: {scope} | decks with brewing status: {len(brewing)}")
    print(f"Over-committed cards with at least 1 owned copy: {len(deficits)}")
    for key, have, total, uses in deficits:
        name = commit_display.get(key) or owned_display.get(key, key)
        decks = ", ".join(f"{d}{'' if q == 1 else f' x{q}'}" for d, q in uses)
        print(f"  deficit {total - have}: {name} — owned {have}, committed {total} :: {decks}")

    print(f"Committed cards with 0 owned copies (buy list): {len(unowned)}")
    if args.show_unowned:
        for key, _, total, uses in sorted(unowned):
            name = commit_display.get(key, key)
            print(f"  {name} x{total} :: {', '.join(d for d, _ in uses)}")


if __name__ == "__main__":
    main()
