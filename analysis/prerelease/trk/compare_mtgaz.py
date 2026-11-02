"""DEC-1218 R1: compare our Star Trek grades with MTG Arena Zone's (x2, plus the mean offset).

    python3 -I compare_mtgaz.py [GRADES_JSON]   (default: grades.json beside this file)

Prints the offset, the rank correlation overall and by rarity, and every card where the two
differ by 2 or more after the offset. grade_review_log.md records the decision on each one.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def ranks(xs):
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    r = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return r


def pearson(x, y):
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    c = sum((p - mx) * (q - my) for p, q in zip(x, y))
    return c / ((sum((p - mx) ** 2 for p in x) * sum((q - my) ** 2 for q in y)) ** 0.5)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "grades.json")
    with open(path, encoding="utf-8") as f:
        ours = {g["name"]: g for g in json.load(f)}
    with open(os.path.join(HERE, "mtgaz_grades.json"), encoding="utf-8") as f:
        mz = json.load(f)
    shared = sorted(n for n in mz if n in ours and "Land" not in ours[n]["type_line"])
    a = [ours[n]["grade"] for n in shared]
    b = [2 * mz[n] for n in shared]
    off = sum(a) / len(a) - sum(b) / len(b)
    print(f"shared non-land cards {len(shared)}; mean ours {sum(a) / len(a):.2f}; mean 2 x MTGAZ {sum(b) / len(b):.2f}; offset {off:+.2f}")
    print(f"rank correlation {pearson(ranks(a), ranks(b)):.2f}")
    for r in ("common", "uncommon", "rare", "mythic"):
        ix = [i for i, n in enumerate(shared) if ours[n]["rarity"] == r]
        print(f"  {r:9s} {len(ix):3d} cards: ours {sum(a[i] for i in ix) / len(ix):.2f}, 2 x MTGAZ {sum(b[i] for i in ix) / len(ix):.2f}, "
              f"rank correlation {pearson(ranks([a[i] for i in ix]), ranks([b[i] for i in ix])):.2f}")
    gaps = sorted(((a[i] - (b[i] + off), n) for i, n in enumerate(shared) if abs(a[i] - (b[i] + off)) >= 2), key=lambda t: (-abs(t[0]), t[1]))
    print(f"\ngaps of 2 or more after the offset: {len(gaps)}")
    for d, n in gaps:
        print(f"  {d:+5.1f}  {n} ({ours[n]['rarity'][0].upper()}): ours {ours[n]['grade']}, MTGAZ {mz[n]}/5")


if __name__ == "__main__":
    main()
