"""DEC-1218 R1: compare our Star Trek grades with Draftsim's pick-order ratings (x2, plus the mean offset).

    python3 -I compare_draftsim.py [GRADES_JSON]   (default: grades.json beside this file)

Draftsim's set review was not out on 3 November; its pick order was (draftsim_pick_ratings.json,
0 to 5). On Reality Fracture the pick order before the Arena release held the review's ratings:
rank correlation 0.99 on 265 cards (../fra/backtest/score_draftsim_pick.py).
Prints the offset, the rank correlation overall and by rarity, the uncommon-common gap, and every
card where the two differ by 2 or more after the offset, with MTG Arena Zone's mapped grade beside it.
grade_review_log.md records the decision on each one.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # python3 -I leaves this folder off the path

from compare_mtgaz import HERE, pearson, ranks  # noqa: E402


def mean(xs):
    return sum(xs) / len(xs)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "grades.json")
    with open(path, encoding="utf-8") as f:
        ours = {g["name"]: g for g in json.load(f)}
    with open(os.path.join(HERE, "draftsim_pick_ratings.json"), encoding="utf-8") as f:
        ds = json.load(f)
    with open(os.path.join(HERE, "mtgaz_grades.json"), encoding="utf-8") as f:
        mz = json.load(f)
    shared = sorted(n for n in ds if n in ours and "Land" not in ours[n]["type_line"])
    a = [ours[n]["grade"] for n in shared]
    b = [2 * ds[n] for n in shared]
    off = mean(a) - mean(b)
    off_mz = mean(a) - mean([2 * mz[n] for n in shared if n in mz])
    print(f"shared non-land cards {len(shared)}; mean ours {mean(a):.2f}; mean 2 x Draftsim {mean(b):.2f}; offset {off:+.2f}")
    print(f"rank correlation {pearson(ranks(a), ranks(b)):.2f}")
    for r in ("common", "uncommon", "rare", "mythic"):
        ix = [i for i, n in enumerate(shared) if ours[n]["rarity"] == r]
        print(f"  {r:9s} {len(ix):3d} cards: ours {mean([a[i] for i in ix]):.2f}, 2 x Draftsim {mean([b[i] for i in ix]):.2f}, "
              f"rank correlation {pearson(ranks([a[i] for i in ix]), ranks([b[i] for i in ix])):.2f}")
    by = {r: [i for i, n in enumerate(shared) if ours[n]["rarity"] == r] for r in ("common", "uncommon")}
    print(f"uncommon-common gap: ours {mean([a[i] for i in by['uncommon']]) - mean([a[i] for i in by['common']]):.2f}, "
          f"2 x Draftsim {mean([b[i] for i in by['uncommon']]) - mean([b[i] for i in by['common']]):.2f}")
    gaps = sorted(((a[i] - (b[i] + off), n) for i, n in enumerate(shared) if abs(a[i] - (b[i] + off)) >= 2), key=lambda t: (-abs(t[0]), t[1]))
    print(f"\ngaps of 2 or more after the offset: {len(gaps)}")
    for d, n in gaps:
        m = f"MTGAZ {mz[n]}/5 ({2 * mz[n] + off_mz:.1f})" if n in mz else "MTGAZ none"
        print(f"  {d:+5.1f}  {n} ({ours[n]['rarity'][0].upper()}): ours {ours[n]['grade']}, Draftsim {ds[n]}/5 ({b[shared.index(n)] + off:.1f}); {m}")


if __name__ == "__main__":
    main()
