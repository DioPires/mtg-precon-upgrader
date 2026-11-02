"""DEC-1218 R1: score MTG Arena Zone's Reality Fracture grades against 17Lands GIH WR.

    python3 -I score_mtgaz.py   (stdlib only; reuses retro.py's inputs and statistics)

Same 103 commons and uncommons as retro.py section 1. MTG Arena Zone's FRA review was
published on 20 and 21 September 2026 and last changed on 26 September, before the Arena
release on 29 September, so it saw no Arena data.
"""
import json
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # python3 -I leaves this folder off the path

from retro import HERE, load, norm, pearson, ranks, spearman  # noqa: E402

DEC925 = os.path.join(HERE, "..")


def boot(xs, ys, reps=4000, seed=1):
    rnd = random.Random(seed)
    n = len(xs)
    out = []
    for _ in range(reps):
        idx = [rnd.randrange(n) for _ in range(n)]
        out.append(spearman([xs[i] for i in idx], [ys[i] for i in idx]))
    out.sort()
    return out[int(0.025 * reps)], out[int(0.975 * reps)]


def mrr_z(a, b, y):
    """Meng-Rosenthal-Rubin z for corr(b, y) minus corr(a, y), on ranks."""
    a, b, y = ranks(a), ranks(b), ranks(y)
    r_ay, r_by, r_ab = pearson(a, y), pearson(b, y), pearson(a, b)
    n = len(a)
    r2 = (r_ay**2 + r_by**2) / 2
    f = min(1.0, (1 - r_ab) / (2 * (1 - r2)))
    h = (1 - f * r2) / (1 - r2)
    return r_ab, (math.atanh(r_by) - math.atanh(r_ay)) * math.sqrt((n - 3) / (2 * (1 - r_ab) * h))


def main():
    gih = {norm(c["name"]): (c["ever_drawn_win_rate"] * 100, c["rarity"])
           for c in load(os.path.join(HERE, "17lands_fra_card_ratings_premierdraft.json"))
           if c["ever_drawn_win_rate"] is not None}
    src = {
        "v1 blind": {norm(g["name"]): g["grade"] for g in load(os.path.join(HERE, "grades_v1_blind.json"))},
        "v3 final": {norm(g["name"]): g["grade"] for g in load(os.path.join(DEC925, "grades.json"))},
        "Draftsim": {norm(k): v for k, v in load(os.path.join(DEC925, "draftsim_grades.json")).items()},
        "MTGAZ": {norm(k): v for k, v in load(os.path.join(HERE, "mtgaz_grades.json")).items()},
    }
    names = set(gih)
    for s in src.values():
        names &= set(s)
    names = sorted(names)
    y = [gih[n][0] for n in names]
    print(f"{len(names)} cards ({sum(gih[n][1] == 'common' for n in names)} commons)")
    for k, s in src.items():
        x = [s[n] for n in names]
        lo, hi = boot(x, y)
        within = {}
        for r in ("common", "uncommon"):
            ix = [i for i, n in enumerate(names) if gih[n][1] == r]
            within[r] = spearman([x[i] for i in ix], [y[i] for i in ix])
        print(f"{k:9s} {spearman(x, y):.2f} (95% {lo:.2f} to {hi:.2f}); commons {within['common']:.2f}, uncommons {within['uncommon']:.2f}")
    for k in ("v3 final", "Draftsim"):
        r_ab, z = mrr_z([src[k][n] for n in names], [src["MTGAZ"][n] for n in names], y)
        print(f"MTGAZ against {k}: the lists correlate {r_ab:.2f}; z = {z:.2f}")


if __name__ == "__main__":
    main()
