"""DEC-1218 R1: compare our Star Trek grades with Limited Resources 878 (commons and uncommons).

    python3 -I compare_lr.py [GRADES_JSON]   (default: grades.json beside this file)

Source: Limited Resources 878, "Star Trek Set Review: Commons and Uncommons" (Marshall Sutcliffe and
Luis Scott-Vargas, published 3 November 2026; YouTube E8GMevAKQ9w). The grades were read from the
episode's auto-captions on 4 November 2026 into lr_grades.json: {card: {"grade", "build_around",
"time", "quote", "confidence"}}. A split grade ("C+/B-") counts as the mean of its two letters.

Letters map to points as a grade-point scale doubled: A 8, B 6, C 4, D 2, F 0, and a plus or minus
moves a third of a letter (B- 5.33, C+ 4.67). Then the mean offset is added, as for the other sources.
Prints the offset, the rank correlation overall and by rarity, the uncommon-common gap, and every
card where the two differ by 2 or more after the offset, with Draftsim's review and MTG Arena Zone
beside it. grade_review_log.md records the decision on each one.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # python3 -I leaves this folder off the path

from compare_mtgaz import HERE, pearson, ranks  # noqa: E402

BASE = {"A": 4.0, "B": 3.0, "C": 2.0, "D": 1.0, "F": 0.0}


def points(letter):
    """'B-' -> 5.33; 'C+/B-' -> mean of the two."""
    parts = letter.split("/")
    vals = []
    for p in parts:
        p = p.strip()
        v = BASE[p[0]]
        if p.endswith("+"):
            v += 1 / 3
        elif p.endswith("-"):
            v -= 1 / 3
        vals.append(2 * v)
    return sum(vals) / len(vals)


def mean(xs):
    return sum(xs) / len(xs)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "grades.json")
    with open(path, encoding="utf-8") as f:
        ours = {g["name"]: g for g in json.load(f)}
    with open(os.path.join(HERE, "lr_grades.json"), encoding="utf-8") as f:
        lr = {n: v for n, v in json.load(f).items() if v.get("grade")}
    with open(os.path.join(HERE, "draftsim_review_ratings.json"), encoding="utf-8") as f:
        ds = json.load(f)
    with open(os.path.join(HERE, "mtgaz_grades.json"), encoding="utf-8") as f:
        mz = json.load(f)
    shared = sorted(n for n in lr if n in ours and "Land" not in ours[n]["type_line"])
    a = [ours[n]["grade"] for n in shared]
    b = [points(lr[n]["grade"]) for n in shared]
    off = mean(a) - mean(b)
    ds_sh = [n for n in shared if n in ds]
    mz_sh = [n for n in shared if n in mz]
    off_ds = mean([ours[n]["grade"] for n in ds_sh]) - mean([ds[n] for n in ds_sh])
    off_mz = mean([ours[n]["grade"] for n in mz_sh]) - mean([2 * mz[n] for n in mz_sh])
    print(f"shared non-land cards {len(shared)}; mean ours {mean(a):.2f}; mean LR points {mean(b):.2f}; offset {off:+.2f}")
    print(f"rank correlation {pearson(ranks(a), ranks(b)):.2f}")
    for r in ("common", "uncommon"):
        ix = [i for i, n in enumerate(shared) if ours[n]["rarity"] == r]
        print(f"  {r:9s} {len(ix):3d} cards: ours {mean([a[i] for i in ix]):.2f}, LR {mean([b[i] for i in ix]):.2f}, "
              f"rank correlation {pearson(ranks([a[i] for i in ix]), ranks([b[i] for i in ix])):.2f}")
    by = {r: [i for i, n in enumerate(shared) if ours[n]["rarity"] == r] for r in ("common", "uncommon")}
    print(f"uncommon-common gap on these cards: ours {mean([a[i] for i in by['uncommon']]) - mean([a[i] for i in by['common']]):.2f}, "
          f"LR {mean([b[i] for i in by['uncommon']]) - mean([b[i] for i in by['common']]):.2f}")
    for label, other in (("Draftsim review", lambda n: ds[n]), ("MTG Arena Zone x2", lambda n: 2 * mz[n])):
        sh = [n for n in shared if n in (ds if label.startswith("D") else mz)]
        print(f"rank correlation LR vs {label} on {len(sh)} cards: "
              f"{pearson(ranks([points(lr[n]['grade']) for n in sh]), ranks([other(n) for n in sh])):.2f}")
    gaps = sorted(((a[i] - (b[i] + off), n) for i, n in enumerate(shared) if abs(a[i] - (b[i] + off)) >= 2),
                  key=lambda t: (-abs(t[0]), t[1]))
    print(f"\ngaps of 2 or more after the offset: {len(gaps)}")
    for d, n in gaps:
        g = lr[n]
        ba = " build-around" if g.get("build_around") else ""
        dd = f"Draftsim {ds[n]:g}/10 ({ds[n] + off_ds:.1f})" if n in ds else "Draftsim none"
        m = f"MTGAZ {mz[n]}/5 ({2 * mz[n] + off_mz:.1f})" if n in mz else "MTGAZ none"
        print(f"  {d:+5.1f}  {n} ({ours[n]['rarity'][0].upper()}): ours {ours[n]['grade']}, "
              f"LR {g['grade']}{ba} ({points(g['grade']) + off:.1f}) at {g.get('time')}; {dd}; {m}")


if __name__ == "__main__":
    main()
