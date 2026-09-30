"""DEC-935: compact Naya query over the local Scryfall mirror.

usage: uv run python agents/ceo/analysis/dec935-mirror-query.py "<oracle regex>" [type-substring] [max]
Also: NAMES mode -> uv run python ... --names "A" "B" ... prints oracle text for those names.
"""
import csv
import glob
import json
import re
import sys
from collections import defaultdict

ROOT = "/Users/dpires/Documents/Personal/code/mtg-precon-upgrader"
TARGET = "broodfire-hatchery"
CI = set("RGW")


def text(c):
    if c.get("oracle_text") is not None:
        return c["oracle_text"]
    return " // ".join(f.get("oracle_text", "") for f in c.get("card_faces", []))


def load():
    mirror = json.load(open(f"{ROOT}/priv_data/scryfall-oracle.json"))
    owned = defaultdict(int)
    for row in csv.DictReader(open(f"{ROOT}/priv_data/Owned.csv")):
        owned[row["Name"].split(" // ")[0]] += int(row["Quantity"] or 0)
    locks = defaultdict(list)
    for path in glob.glob(f"{ROOT}/data/commanders/*/deck.json"):
        d = json.load(open(path))
        if d["id"] == TARGET:
            continue
        for c in d["decklist"]:
            locks[c["name"].split(" // ")[0]].append(d["id"])
        locks[d["commander"].split(" // ")[0]].append(d["id"])
    in_deck = {c["name"].split(" // ")[0] for c in json.load(open(f"{ROOT}/data/commanders/{TARGET}/deck.json"))["decklist"]}
    return mirror, owned, locks, in_deck


def line(c, owned, locks, in_deck, n=260):
    name = c["name"].split(" // ")[0]
    flag = " IN-DECK" if name in in_deck else ""
    return (f"{c.get('edhrec_rank') or '-':>6} {owned.get(name,0)}x {c['name']} | {c.get('mana_cost') or ''} | "
            f"{c.get('type_line','')[:34]} | locks={locks.get(name,[])}{flag}\n      {text(c).replace(chr(10),' ')[:n]}")


def main():
    mirror, owned, locks, in_deck = load()
    if sys.argv[1] == "--names":
        want = {n.lower() for n in sys.argv[2:]}
        for c in mirror:
            if c["name"].lower() in want or c["name"].split(" // ")[0].lower() in want:
                print(line(c, owned, locks, in_deck, 600))
                want.discard(c["name"].lower()); want.discard(c["name"].split(" // ")[0].lower())
        if want:
            print("NOT FOUND:", want)
        return
    rx = re.compile(sys.argv[1], re.I)
    tsub = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] != "-" else None
    mx = int(sys.argv[3]) if len(sys.argv) > 3 else 25
    hits, seen = [], set()
    for c in mirror:
        if c["name"] in seen:
            continue
        seen.add(c["name"])
        if not set(c.get("color_identity", [])) <= CI:
            continue
        if c.get("legalities", {}).get("commander") != "legal":
            continue
        if tsub and tsub.lower() not in c.get("type_line", "").lower():
            continue
        if rx.search(text(c)):
            hits.append(c)
    hits.sort(key=lambda c: c.get("edhrec_rank") or 10**9)
    print(f"# {sys.argv[1]!r} type={tsub} hits={len(hits)}")
    for c in hits[:mx]:
        print(line(c, owned, locks, in_deck))


if __name__ == "__main__":
    main()
