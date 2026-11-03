"""DEC-1218 R1: score Draftsim's Reality Fracture pick-order ratings against 17Lands GIH WR.

    python3 -I score_draftsim_pick.py   (stdlib only; reuses retro.py's inputs and score_mtgaz.py's statistics)

Same 103 commons and uncommons as retro.py section 1. Two copies of the pick order
(../../trk/parse_draftsim_pick.py): 25 September 2026, before the Arena release on 29 September,
and 3 November 2026, after Draftsim updated it (the same table as on 14 October).
Also prints how close the pick order sits to Draftsim's set review, and whether each source graded
removal too high or too low at equal grade and rarity.
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # python3 -I leaves this folder off the path

from retro import HERE, load, norm, spearman  # noqa: E402
from score_mtgaz import boot, mrr_z  # noqa: E402

DEC925 = os.path.join(HERE, "..")


def ols_residuals(grade, gih, names):
    """GIH WR minus its fit on the grade, fitted within each rarity."""
    out = {}
    for r in ("common", "uncommon"):
        ix = [n for n in names if gih[n][1] == r]
        x = [grade[n] for n in ix]
        y = [gih[n][0] for n in ix]
        mx, my = sum(x) / len(x), sum(y) / len(y)
        b = sum((p - mx) * (q - my) for p, q in zip(x, y)) / sum((p - mx) ** 2 for p in x)
        for n, p, q in zip(ix, x, y):
            out[n] = q - (my + b * (p - mx))
    return out


def main():
    gih = {norm(c["name"]): (c["ever_drawn_win_rate"] * 100, c["rarity"])
           for c in load(os.path.join(HERE, "17lands_fra_card_ratings_premierdraft.json"))
           if c["ever_drawn_win_rate"] is not None}
    v3 = {norm(g["name"]): g for g in load(os.path.join(DEC925, "grades.json"))}
    src = {
        "v3 final": {k: g["grade"] for k, g in v3.items()},
        "Draftsim review": {norm(k): v for k, v in load(os.path.join(DEC925, "draftsim_grades.json")).items()},
        "MTGAZ": {norm(k): v for k, v in load(os.path.join(HERE, "mtgaz_grades.json")).items()},
        "pick 25 Sep": {norm(k): v for k, v in load(os.path.join(HERE, "draftsim_pick_fra_20260925.json")).items()},
        "pick 3 Nov": {norm(k): v for k, v in load(os.path.join(HERE, "draftsim_pick_fra_20261103.json")).items()},
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
        within = {r: spearman([x[i] for i, n in enumerate(names) if gih[n][1] == r], [y[i] for i, n in enumerate(names) if gih[n][1] == r])
                  for r in ("common", "uncommon")}
        print(f"{k:15s} {spearman(x, y):.2f} (95% {lo:.2f} to {hi:.2f}); commons {within['common']:.2f}, uncommons {within['uncommon']:.2f}")
    for k in ("v3 final", "Draftsim review", "MTGAZ"):
        r_ab, z = mrr_z([src[k][n] for n in names], [src["pick 25 Sep"][n] for n in names], y)
        print(f"pick 25 Sep against {k}: the lists correlate {r_ab:.2f}; z = {z:.2f}")

    review, pick = src["Draftsim review"], src["pick 25 Sep"]
    both = sorted(set(review) & set(pick))
    print(f"\nwhole set, pick 25 Sep against the review: rank correlation {spearman([pick[n] for n in both], [review[n] for n in both]):.2f} on {len(both)} cards")

    rem = [n for n in names if "removal" in v3[n].get("roles", [])]
    print(f"\nremoval ({len(rem)} cards, v3 roles): mean GIH residual at equal grade and rarity, bootstrap 95%")
    for k in ("v3 final", "Draftsim review", "MTGAZ", "pick 25 Sep"):
        s = src[k]
        res = ols_residuals(s, gih, names)
        rnd = random.Random(7)
        reps = []
        for _ in range(4000):
            smp = [rnd.choice(names) for _ in names]
            r2 = ols_residuals(s, gih, smp)
            vals = [r2[n] for n in smp if n in rem]
            if vals:
                reps.append(sum(vals) / len(vals))
        reps.sort()
        pct = sum(sum(s[m] < s[n] for m in names) / len(names) * 100 for n in rem) / len(rem)
        print(f"  {k:15s} {sum(res[n] for n in rem) / len(rem):+.2f} GIH points ({reps[int(0.025 * len(reps))]:+.2f} to {reps[int(0.975 * len(reps))]:+.2f}); "
              f"removal's mean grade percentile {pct:.0f}")


if __name__ == "__main__":
    main()
