"""Check the board's event feedback against the three reviews (DEC-1218, 9 November 2026).

The board played the prerelease on 6 November and reported (DEC-1218, comment 7c924d32):
Spacecraft were too slow against many aggressive decks; strange new worlds and the Borg
typal decks ("they play kind of like slivers") were good.

For each group of cards the feedback names, this script compares our final grades with the
consensus of the three reviews (MTG Arena Zone, Draftsim's set review, Limited Resources), each
put on our scale by its mean offset, as compare_lr.py does. A group's figure is its mean gap
(consensus minus ours) minus the mean gap of the other cards of the same rarity band, with a
bootstrap 95% interval (10,000 resamples, seed 1). Commons and uncommons use the cards that
all three reviews grade; rares and mythics use the cards that two grade (Limited Resources
grades no rares).

This is a check against other graders' opinions, not against results. The back-test
(backtest-plan.md, question 12) scores the same groups against 17Lands win rates.

Run: python3 -I analysis/prerelease/trk/feedback_check.py analysis/prerelease/trk
"""
import json
import os
import random
import re
import statistics as st
import sys

BASE = {"A": 4.0, "B": 3.0, "C": 2.0, "D": 1.0, "F": 0.0}


def lr_points(letter):
    """'B-' -> 5.33; 'C+/B-' -> mean of the two (as compare_lr.py)."""
    vals = []
    for p in letter.split("/"):
        p = p.strip()
        v = BASE[p[0]] + (1 / 3 if p.endswith("+") else -1 / 3 if p.endswith("-") else 0)
        vals.append(2 * v)
    return sum(vals) / len(vals)


def main():
    d = sys.argv[1]

    def load(name):
        with open(os.path.join(d, name), encoding="utf-8") as f:
            return json.load(f)

    ours = {g["name"]: g for g in load("grades.json")}
    cards = {c["name"]: c for c in load("trk_all_cards.json")}
    mz = load("mtgaz_grades.json")
    ds = load("draftsim_review_ratings.json")
    lr = {n: v for n, v in load("lr_grades.json").items() if v.get("grade")}
    nonland = [n for n in ours if "Land" not in ours[n]["type_line"]]

    def offset(src, f):
        sh = [n for n in nonland if n in src]
        return st.mean(ours[n]["grade"] for n in sh) - st.mean(f(src[n]) for n in sh)

    o_mz = offset(mz, lambda v: 2 * v)
    o_ds = offset(ds, lambda v: v)
    o_lr = offset(lr, lambda v: lr_points(v["grade"]))

    def consensus(n):
        xs = []
        if n in mz:
            xs.append(2 * mz[n] + o_mz)
        if n in ds:
            xs.append(ds[n] + o_ds)
        if n in lr:
            xs.append(lr_points(lr[n]["grade"]) + o_lr)
        return (st.mean(xs), len(xs)) if xs else (None, 0)

    def text(n):
        c = cards.get(n, {})
        if "card_faces" in c:
            return " ".join(f.get("oracle_text", "") for f in c["card_faces"])
        return c.get("oracle_text", "")

    groups = {
        "Borg": lambda n: "Borg" in ours[n]["type_line"],
        "Spacecraft": lambda n: "Spacecraft" in ours[n]["type_line"],
        "Strange new worlds": lambda n: "strange new worlds" in text(n).lower(),
        "Flying creatures": lambda n: "Creature" in ours[n]["type_line"]
        and re.search(r"(^|\n)Flying", text(n)) is not None,
    }
    bands = {
        "C/U": {n: consensus(n)[0] - ours[n]["grade"] for n in nonland
                if ours[n]["rarity"] in ("common", "uncommon") and consensus(n)[1] >= 3},
        "R/M": {n: consensus(n)[0] - ours[n]["grade"] for n in nonland
                if ours[n]["rarity"] in ("rare", "mythic") and consensus(n)[1] >= 2},
    }
    print(f"Offsets: MTG Arena Zone {o_mz:+.2f}, Draftsim review {o_ds:+.2f}, Limited Resources {o_lr:+.2f}")
    for band, pool in bands.items():
        print(f"{band}: {len(pool)} cards, mean gap (consensus minus ours) {st.mean(pool.values()):+.2f}")
    print()
    print("Group gap against the rest of its rarity band (consensus minus ours):")
    random.seed(1)
    for g, f in groups.items():
        for band, pool in bands.items():
            ins = [v for n, v in pool.items() if f(n)]
            out = [v for n, v in pool.items() if not f(n)]
            if len(ins) < 2:
                continue
            gap = st.mean(ins) - st.mean(out)
            bs = sorted(st.mean(random.choices(ins, k=len(ins))) - st.mean(random.choices(out, k=len(out)))
                        for _ in range(10000))
            print(f"  {g:19} {band} n={len(ins):2}  group {st.mean(ins):+.2f}  rest {st.mean(out):+.2f}  "
                  f"difference {gap:+.2f}  95% [{bs[250]:+.2f}, {bs[9750]:+.2f}]")
    print()
    for g, f in groups.items():
        print(f"{g}:")
        for n in sorted((n for n in nonland if f(n)), key=lambda n: ("cumr".index(ours[n]["rarity"][0]), n)):
            c, k = consensus(n)
            cs = f"{c:.1f}" if c is not None else "-"
            print(f"  {ours[n]['rarity'][0].upper()}  ours {ours[n]['grade']:>4}  consensus {cs:>4} ({k})  {n}")


if __name__ == "__main__":
    main()
