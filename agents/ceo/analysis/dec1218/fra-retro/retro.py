"""DEC-1218: back-test the DEC-925 Reality Fracture work against 17Lands Arena data.

Inputs (all in this folder unless noted):
  17lands_fra_card_ratings_premierdraft.json  card_ratings/data?expansion=FRA&format=PremierDraft (fetched 2026-11-01)
  17lands_fra_color_ratings_Sealed.json       color_ratings/data?expansion=FRA&event_type=Sealed&start_date=2026-09-29&end_date=2026-11-01&combine_splash=true (a pair includes its splash decks, as the sim does)
  17lands_fra_color_ratings_PremierDraft.json same, PremierDraft
  grades_v1_blind.json, grades_v2.json         git 3e034a7f and 2f2c0683
  ../../dec925/grades.json                     v3 (final), ../../dec925/draftsim_grades.json, ../../dec925/sim_results.json

Run: python3 -I retro.py  (stdlib only)
"""
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DEC925 = os.path.join(HERE, "..", "..", "dec925")
MIN_GAMES = 0  # 17Lands publishes a win rate only above its own game floor; take every card it publishes
MISS_GAMES = 0


def load(path):
    with open(path) as f:
        return json.load(f)


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


def pearson(a, b):
    n = len(a)
    ma, mb = sum(a) / n, sum(b) / n
    cov = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    va = math.sqrt(sum((x - ma) ** 2 for x in a))
    vb = math.sqrt(sum((y - mb) ** 2 for y in b))
    return cov / (va * vb)


def spearman(a, b):
    return pearson(ranks(a), ranks(b))


def norm(name):
    return name.split(" // ")[0].strip().lower()


def main():
    cards17 = load(os.path.join(HERE, "17lands_fra_card_ratings_premierdraft.json"))
    gih = {}
    for c in cards17:
        if c["ever_drawn_game_count"] >= MIN_GAMES and c["ever_drawn_win_rate"] is not None:
            gih[norm(c["name"])] = (c["ever_drawn_win_rate"] * 100, c["ever_drawn_game_count"], c["rarity"], c["name"])

    versions = {
        "v1 blind": {norm(g["name"]): g for g in load(os.path.join(HERE, "grades_v1_blind.json"))},
        "v2 after Draftsim": {norm(g["name"]): g for g in load(os.path.join(HERE, "grades_v2.json"))},
        "v3 final": {norm(g["name"]): g for g in load(os.path.join(DEC925, "grades.json"))},
    }
    draftsim = {norm(k): {"grade": v} for k, v in load(os.path.join(DEC925, "draftsim_grades.json")).items()}

    out = []
    out.append(f"# DEC-925 back-test against 17Lands (FRA, fetched 2026-11-01)\n")
    out.append(f"Card metric: Premier Draft GIH WR (win rate in games where the card was drawn or in the opening hand), published for {len(gih)} of {len(cards17)} cards. 17Lands' public card endpoint returns a sample (median 380 games a card) and withholds the win rate below its own floor, so it covers 65 commons and 48 uncommons and no rare or mythic. At 400 games one card's GIH WR carries about +/-2.5 points of noise. Sealed card data is not published (23 games in total). The comparison is therefore about commons and uncommons only.\n")

    out.append("## 1. Card grades against GIH WR\n")
    out.append("| Grade set | Cards matched | Spearman | Pearson |")
    out.append("|---|---:|---:|---:|")
    common_names = set(gih)
    for src in list(versions.values()) + [draftsim]:
        common_names &= set(src)
    for label, src in list(versions.items()) + [("Draftsim", draftsim)]:
        rows = [(src[n]["grade"], gih[n][0], gih[n][2]) for n in sorted(common_names)]
        out.append(
            f"| {label} | {len(rows)} | {spearman([r[0] for r in rows], [r[1] for r in rows]):.2f} | "
            f"{pearson([r[0] for r in rows], [r[1] for r in rows]):.2f} |"
        )
    out.append("\nSame card set for every row (cards graded by all four and over the game floor).\n")

    # Noise ceiling: the share of the spread in observed GIH WR that is not sampling noise.
    obs = [gih[n] for n in common_names]
    mean_wr = sum(o[0] for o in obs) / len(obs)
    var_obs = sum((o[0] - mean_wr) ** 2 for o in obs) / (len(obs) - 1)
    var_noise = sum(o[0] * (100 - o[0]) / o[1] for o in obs) / len(obs)
    rel = max(0.0, 1 - var_noise / var_obs)
    out.append(
        f"Noise ceiling: observed GIH WR spread SD {math.sqrt(var_obs):.2f} points, sampling noise SD {math.sqrt(var_noise):.2f}. "
        f"A perfect grade list would correlate at about {math.sqrt(rel):.2f}, not 1.0.\n"
    )

    # Steiger's test: is Draftsim's correlation with GIH WR higher than v3's, on the same cards?
    v3 = versions["v3 final"]
    names = sorted(common_names)
    a = ranks([v3[n]["grade"] for n in names])
    b = ranks([draftsim[n]["grade"] for n in names])
    y = ranks([gih[n][0] for n in names])
    r_ay, r_by, r_ab = pearson(a, y), pearson(b, y), pearson(a, b)
    n = len(names)
    # Meng, Rosenthal and Rubin (1992): z for two dependent correlations with a shared variable.
    r2bar = (r_ay**2 + r_by**2) / 2
    f = min(1.0, (1 - r_ab) / (2 * (1 - r2bar)))
    h = (1 - f * r2bar) / (1 - r2bar)
    z = (math.atanh(r_by) - math.atanh(r_ay)) * math.sqrt((n - 3) / (2 * (1 - r_ab) * h))
    out.append(f"Draftsim against v3 on the same {n} cards (rank correlations): Draftsim {r_by:.2f}, v3 {r_ay:.2f}, the two grade lists with each other {r_ab:.2f}. Meng-Rosenthal-Rubin z for the difference: {z:.2f} (above 1.96 means the gap is unlikely to be noise).\n")

    # Biggest misses of v3: the gap between a card's rank by our grade and its rank by GIH WR, in percentiles.
    pct_g = {nm: (r - 1) / (n - 1) * 100 for nm, r in zip(names, a)}
    pct_y = {nm: (r - 1) / (n - 1) * 100 for nm, r in zip(names, y)}
    pct_d = {nm: (r - 1) / (n - 1) * 100 for nm, r in zip(names, b)}
    gaps = sorted(names, key=lambda nm: pct_y[nm] - pct_g[nm])
    head = "| Card | Rarity | v3 grade | Draftsim | GIH WR | Games | v3 percentile | GIH percentile | Roles |"
    rule = "|---|---|---:|---:|---:|---:|---:|---:|---|"

    def line(nm):
        g = v3[nm]
        return (
            f"| {gih[nm][3]} | {gih[nm][2][0].upper()} | {g['grade']} | {draftsim[nm]['grade']} | {gih[nm][0]:.1f}% | {gih[nm][1]} | "
            f"{pct_g[nm]:.0f} | {pct_y[nm]:.0f} | {', '.join(g.get('roles', []))} |"
        )

    out.append("### Overrated by v3 (GIH percentile 50+ below our grade's percentile)\n")
    out += [head, rule] + [line(nm) for nm in gaps if pct_y[nm] - pct_g[nm] <= -50]
    out.append("\n### Underrated by v3 (GIH percentile 50+ above our grade's percentile)\n")
    out += [head, rule] + [line(nm) for nm in reversed(gaps) if pct_y[nm] - pct_g[nm] >= 50]
    by_role = {}
    for nm in names:
        for role in v3[nm].get("roles", []) or ["none"]:
            by_role.setdefault(role, []).append(pct_y[nm] - pct_g[nm])
    out.append("\nMean gap (GIH percentile minus v3 percentile) by role; negative means we graded the role too high:\n")
    out.append("| Role | Cards | Mean gap |")
    out.append("|---|---:|---:|")
    for role, gs in sorted(by_role.items(), key=lambda kv: sum(kv[1]) / len(kv[1])):
        out.append(f"| {role} | {len(gs)} | {sum(gs) / len(gs):+.0f} |")
    rows = [(nm, v3[nm]["grade"], gih[nm][0], gih[nm][1], gih[nm][2], v3[nm]) for nm in sorted(set(gih) & set(v3))]

    # Role-level: removal, and colour-level mean GIH WR of C+U.
    out.append("\n## 2. Removal and colour depth\n")
    out.append("Mean GIH WR of commons and uncommons, mono-coloured, by colour, and of the removal-tagged ones:\n")
    out.append("| Colour | C+U cards | Mean GIH WR | Removal cards | Removal mean GIH WR |")
    out.append("|---|---:|---:|---:|---:|")
    for col in "WUBRG":
        sel = [r for r in rows if r[4] in ("common", "uncommon") and r[5]["colors"] == [col]]
        rem = [r for r in sel if "removal" in r[5].get("roles", [])]
        mean = lambda L: (sum(r[2] for r in L) / len(L)) if L else float("nan")
        out.append(f"| {col} | {len(sel)} | {mean(sel):.1f}% | {len(rem)} | {mean(rem):.1f}% |")

    # Pairs: Sealed and Premier Draft win rate and share against the sim.
    sim = load(os.path.join(DEC925, "sim_results.json"))["runs"]["CEO grades"]["per_pair"]
    simd = {p["pair"]: p for p in sim}
    out.append("\n## 3. Pair ranking against Arena Sealed results\n")
    out.append("17Lands two-colour decks, splash decks folded into their pair. Share = the pair's games over all two-colour games; it is the nearest observed analogue of P(best). SE is the binomial standard error of the win rate.\n")
    seal = {r["short_name"]: r for r in load(os.path.join(HERE, "17lands_fra_color_ratings_Sealed.json")) if not r["is_summary"] and len(r["short_name"]) == 2}
    pd = {r["short_name"]: r for r in load(os.path.join(HERE, "17lands_fra_color_ratings_PremierDraft.json")) if not r["is_summary"] and len(r["short_name"]) == 2}
    tot = sum(r["games"] for r in seal.values())
    out.append("| Pair | Our tier | P(best) | P(viable) | Sealed WR | SE | Sealed share | Premier Draft WR |")
    out.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    tiers = {"WB": 1, "UG": 3, "RG": 3}
    rows_p = []
    for pair in sorted(seal, key=lambda k: -seal[k]["wins"] / seal[k]["games"]):
        s = seal[pair]
        wr = s["wins"] / s["games"]
        se = math.sqrt(wr * (1 - wr) / s["games"])
        p = simd[pair]
        pwr = pd[pair]["wins"] / pd[pair]["games"]
        rows_p.append((pair, p["p_best"], p["p_viable"], p["mean_score"], wr, s["games"] / tot, pwr))
        out.append(f"| {pair} | {tiers.get(pair, 2)} | {p['p_best']*100:.1f}% | {p['p_viable']*100:.1f}% | {wr*100:.1f}% | {se*100:.1f} | {s['games']/tot*100:.1f}% | {pwr*100:.1f}% |")
    out.append("")
    for label, idx in (("P(best)", 1), ("P(viable)", 2), ("mean score", 3)):
        out.append(f"- Spearman of {label} with Sealed WR: {spearman([r[idx] for r in rows_p], [r[4] for r in rows_p]):.2f}; with Sealed share: {spearman([r[idx] for r in rows_p], [r[5] for r in rows_p]):.2f}.")
    alt = {q["pair"]: q for q in load(os.path.join(HERE, "sim_draftsim_grades.json"))["runs"]["CEO grades"]["per_pair"]}
    alt_best = [alt[r[0]]["p_best"] for r in rows_p]
    alt_score = [alt[r[0]]["mean_score"] for r in rows_p]
    out.append(f"- Same sim, Draftsim grades + 1 in place of ours (`sim_draftsim_grades.md`, same seed and roles): Spearman of P(best) with Sealed WR {spearman(alt_best, [r[4] for r in rows_p]):.2f}, with share {spearman(alt_best, [r[5] for r in rows_p]):.2f}; of mean score with Sealed WR {spearman(alt_score, [r[4] for r in rows_p]):.2f}.")
    out.append("  P(best) under Draftsim grades: " + ", ".join(f"{k} {v['p_best']*100:.1f}%" for k, v in sorted(alt.items(), key=lambda kv: -kv[1]["p_best"])) + ".")
    out.append(f"- Spearman of Sealed WR with Premier Draft WR: {spearman([r[4] for r in rows_p], [r[6] for r in rows_p]):.2f}.")
    colwr = {}
    for col in "WUBRG":
        sel = [r for r in rows_p if col in r[0]]
        g = sum(seal[r[0]]["games"] for r in sel)
        w = sum(seal[r[0]]["wins"] for r in sel)
        colwr[col] = (w / g, g / tot / 2)
    out.append("\nBy colour (the four pairs that hold it, games-weighted): " + ", ".join(f"{c} {v[0]*100:.1f}%" for c, v in sorted(colwr.items(), key=lambda kv: -kv[1][0])) + ".")

    out.append("\n## 4. Limits of this check\n")
    out.append("- One set. Read the direction and size of each gap, not a rule.")
    out.append("- Card data is Premier Draft, not Sealed, and covers commons and uncommons only; the public endpoint returns a recent sample and ignores date parameters.")
    out.append("- GIH WR credits cards in the strongest decks: blue won most in this format, so blue cards look better, and that is part of the engine gap.")
    out.append("- Sealed WR is the result of decks that Arena players built; P(best) is a statement about pools. Share is the nearer analogue, and it does not match either.")
    out.append("- Arena Sealed is mostly best-of-one and 17Lands users play above the average. A paper prerelease differs on both.")
    with open(os.path.join(HERE, "retro.md"), "w") as f:
        f.write("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
