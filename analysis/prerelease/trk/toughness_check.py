"""Toughness shares behind Joel Are Magic's 82% and the sheet's 75% (DEC-1218, 6 November 2026).

Joel's guide (YouTube I_sUtDGvJhM, 8:11 to 8:24) counts the 47 common creatures: -2/-2 kills 24,
-3/-3 kills 34, and 82% of the commons with mana value 3 or less have toughness 2 or less.
The sheet's section 3 counts all 165 creatures (no Spacecraft; Captain Pike's */* is left out).
This script recounts both, with and without Spacecraft, and weights each card by how often its
rarity opens in a Play Booster (slot rates in notes.md, from WotC's Collecting article).

Run: python3 -I analysis/prerelease/trk/toughness_check.py analysis/prerelease/trk/trk_all_cards.json
"""
import json
import sys

# Expected copies of one named card per Play Booster, by rarity (notes.md, WotC slot rates).
WEIGHT = {
    "common": (7 - 1 / 25 + 0.208 + 0.512) / 81,
    "uncommon": (3 + 0.541 + 0.347) / 110,
    "rare": (0.801 + 0.167 + 0.063) / 80,
    "mythic": (0.124 + 0.026 + 0.010) / 25,
}


def fixed_toughness(card):
    t = card.get("toughness")
    return int(t) if t is not None and t.isdigit() else None


def main(path):
    cards = json.load(open(path, encoding="utf-8"))
    main_set = [c for c in cards if c.get("collector_number", "").isdigit() and 1 <= int(c["collector_number"]) <= 306]
    for with_ships in (False, True):
        rows = [c for c in main_set if fixed_toughness(c) is not None
                and ("Creature" in c["type_line"] or (with_ships and "Spacecraft" in c["type_line"]))]
        print(f"--- Spacecraft {'included' if with_ships else 'left out'}")
        groups = (
            ("all creatures", rows),
            ("common creatures", [c for c in rows if c["rarity"] == "common"]),
            ("common, mana value 3 or less", [c for c in rows if c["rarity"] == "common" and c["cmc"] <= 3]),
        )
        for label, group in groups:
            cells = []
            for k in (1, 2, 3, 4):
                m = sum(fixed_toughness(c) <= k for c in group)
                cells.append(f"<={k}: {m}/{len(group)} = {100 * m / len(group):.1f}%")
            print(f"{label:30s} " + " | ".join(cells))
        total = sum(WEIGHT[c["rarity"]] for c in rows)
        cells = [f"<={k}: {100 * sum(WEIGHT[c['rarity']] for c in rows if fixed_toughness(c) <= k) / total:.1f}%"
                 for k in (1, 2, 3, 4)]
        print(f"{'all, weighted by booster rarity':30s} " + " | ".join(cells))


if __name__ == "__main__":
    main(sys.argv[1])
