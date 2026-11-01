"""How much fixing a Star Trek prerelease pool holds (DEC-1218 N1, playbook step 7).

Arithmetic for the splash rule, not the Sealed sim. Slot rates from WotC's
"Collecting Magic: The Gathering | Star Trek" article:
- Land slot: common dual 40% non-foil + 10% foil. Common duals appear in no other slot.
- Main-set rares: 80.1% (rare slot) + 16.7% (wildcard) + 6.3% (foil slot) per pack,
  plus LCARS shock lands at 1.4% of the rare slot.
- Commons: 7 common slots (a Stardates card replaces one in 1 of 25 packs) + 20.8%
  wildcard + 51.2% foil slot, spread over 81 commons (the 10 duals are not among them).
- Prerelease Pack: 6 Play Boosters + 1 foil rare or mythic (rare share 80.1 / 92.5).
- 10 of the 80 main-set rares are shock lands; each dual makes 2 of the 5 colours.

For each pool, the main pair is drawn at random and the best of the 3 other colours
is counted. Run: python3 -I splash_sources.py
"""
import collections
import itertools
import random

random.seed(20261106)
COLOURS = "WUBRG"
DUALS = ["".join(p) for p in itertools.combinations(COLOURS, 2)]
P_COMMON = (7 - 1 / 25 + 0.208 + 0.512) / 81  # one named common, per pack
FIXERS = ("classf", "territory", "warpcore", "xeno", "frontier")


def pool():
    duals, shocks, commons = collections.Counter(), collections.Counter(), collections.Counter()
    for _ in range(6):
        if random.random() < 0.5:
            duals[random.choice(DUALS)] += 1
        for p_rare in (0.801, 0.167, 0.063):
            if random.random() < p_rare and random.random() < 10 / 80:
                shocks[random.choice(DUALS)] += 1
        if random.random() < 0.014:
            shocks[random.choice(DUALS)] += 1
        for name in FIXERS:
            commons[name] += random.random() < P_COMMON
    if random.random() < 0.801 / 0.925 and random.random() < 10 / 80:
        shocks[random.choice(DUALS)] += 1
    return duals, shocks, commons


def main():
    n = 200_000
    lands_ge, lands_cf_ge, all_ge = (collections.Counter() for _ in range(3))
    total_duals = total_shocks = 0
    for _ in range(n):
        duals, shocks, commons = pool()
        total_duals += sum(duals.values())
        total_shocks += sum(shocks.values())
        main_pair = random.choice(DUALS)
        green = "G" in main_pair
        best_lands = best_lands_cf = best_all = 0
        for colour in COLOURS:
            if colour in main_pair:
                continue
            lands = sum(v for k, v in duals.items() if colour in k)
            lands += sum(v for k, v in shocks.items() if colour in k)
            lands_cf = lands + commons["classf"] + (commons["xeno"] if green else 0)
            everything = lands_cf + commons["territory"] + commons["warpcore"]
            everything += commons["frontier"] if green else 0
            best_lands = max(best_lands, lands)
            best_lands_cf = max(best_lands_cf, lands_cf)
            best_all = max(best_all, everything)
        for k in range(1, 7):
            lands_ge[k] += best_lands >= k
            lands_cf_ge[k] += best_lands_cf >= k
            all_ge[k] += best_all >= k
    print(f"pools {n:,}; mean common duals {total_duals / n:.2f}; mean shock lands {total_shocks / n:.2f}")
    rows = (
        ("dual and shock lands", lands_ge),
        ("+ Class-F Shuttlecraft, Xenobotanist (green)", lands_cf_ge),
        ("+ Unexplored Territory, Warp Core, Final Frontier (green)", all_ge),
    )
    print("non-basic sources of the best third colour, share of pools with at least k:")
    print("| Sources | " + " | ".join(f">= {k}" for k in range(1, 7)) + " |")
    print("|---|" + "---:|" * 6)
    for label, counter in rows:
        print(f"| {label} | " + " | ".join(f"{100 * counter[k] / n:.0f}%" for k in range(1, 7)) + " |")


if __name__ == "__main__":
    main()
