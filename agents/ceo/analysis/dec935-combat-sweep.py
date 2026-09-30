"""DEC-935: sweep the Scryfall mirror for Naya combat enablers (extra combats,
power doublers, haste, attack payoffs) and report owned qty + deck locks.

Run: uv run python agents/ceo/analysis/dec935-combat-sweep.py
"""
import csv
import glob
import json
import re
from collections import defaultdict

ROOT = "/Users/dpires/Documents/Personal/code/mtg-precon-upgrader"
TARGET = "broodfire-hatchery"
CI = set("RGW")

CLASSES = {
    "extra_combat": r"additional combat phase",
    "double_power": r"(double|twice) (that|its|the|their)? ?(creature'?s?|damage|power)|deals double|damage doubled|deal(s)? that much damage plus|double the power",
    "haste_anthem": r"creatures you control have haste|have haste|gain haste",
    "attack_payoff": r"whenever (a|one or more) creature(s)? you control attack|whenever you attack|attacks? each combat|can't be blocked|trample and haste",
    "power_matters": r"greatest power|power 4 or greater|power [4-9] or greater|with the greatest power",
    "pump_all": r"creatures you control get \+[X\d]/\+[X\d]|creatures you control get \+X/\+X|creatures you control get \+\d/\+\d until end of turn",
}


def faces_text(c):
    if c.get("oracle_text") is not None:
        return c["oracle_text"]
    return " // ".join(f.get("oracle_text", "") for f in c.get("card_faces", []))


def main():
    mirror = json.load(open(f"{ROOT}/priv_data/scryfall-oracle.json"))
    owned = defaultdict(int)
    with open(f"{ROOT}/priv_data/Owned.csv") as fh:
        for row in csv.DictReader(fh):
            owned[row["Name"].split(" // ")[0]] += int(row["Quantity"] or 0)

    locks = defaultdict(list)
    index = json.load(open(f"{ROOT}/data/index.json"))
    for path in glob.glob(f"{ROOT}/data/commanders/*/deck.json"):
        d = json.load(open(path))
        if d["id"] == TARGET:
            continue
        for c in d["decklist"]:
            locks[c["name"].split(" // ")[0]].append(d["id"])
        locks[d["commander"].split(" // ")[0]].append(d["id"])

    target = json.load(open(f"{ROOT}/data/commanders/{TARGET}/deck.json"))
    in_deck = {c["name"].split(" // ")[0] for c in target["decklist"]}

    seen = set()
    out = defaultdict(list)
    for c in mirror:
        name = c["name"].split(" // ")[0]
        if name in seen:
            continue
        seen.add(name)
        if not set(c.get("color_identity", [])) <= CI:
            continue
        if c.get("legalities", {}).get("commander") != "legal":
            continue
        text = faces_text(c).lower()
        tl = c.get("type_line", "")
        for cls, rx in CLASSES.items():
            if re.search(rx, text):
                out[cls].append((name, c.get("cmc"), tl, owned.get(name, 0), locks.get(name, []), name in in_deck))

    for cls, rows in out.items():
        rows.sort(key=lambda r: (-r[3], r[1] or 0))
        print(f"\n=== {cls} ({len(rows)}) ===")
        for name, cmc, tl, q, lk, ind in rows:
            flag = "IN-DECK" if ind else ""
            print(f"{q:>2}x  mv{cmc:<4} {name:<40} {tl[:38]:<38} locks={lk} {flag}")


if __name__ == "__main__":
    main()
