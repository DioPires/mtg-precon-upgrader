"""Write the phone-readable cheat sheet for a prerelease.

    uv run python scripts/prerelease/build_cheat_sheet.py --set-dir DIR

Reads DIR/grades.json, the card dump, DIR/format_rules.md (section 2, written
by hand) and, when they exist, the three sim result files. Writes
DIR/cheat_sheet.md with six sections:

  1. how to score a pool by hand
  2. the set's format rules, copied from format_rules.md
  3. removal by colour
  4. tricks and instant-speed plays
  5. the archetype ranking from the simulation
  6. the full graded list

Sections 1, 3, 4, 5 and 6 are generated from the data. A handful of sentences
in sections 1, 3 and 5 are judgement calls about a particular set rather than
facts the tool can derive, so they can be replaced from an optional
DIR/prose.json; without that file the tool writes a generic version of each.
Run with --print-tiers to see the computed tier reading on its own.
"""

from __future__ import annotations

import argparse
import collections
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from setlib import WUBRG, bucket, load_cards, oracle_text, pips  # noqa: E402

SIM_FILES = [
    ("headline", "sim_results.json"),
    ("spec_splash", "sim_results_spec_splash.json"),
    ("nosplash", "sim_results_nosplash.json"),
]

# Sentences the tool cannot derive. Each can be overridden from DIR/prose.json.
PROSE_KEYS = (
    "title",
    "intro",
    "procedure_splash",
    "procedure_tiebreak",
    "removal_lead",
    "ranking_heading",
    "ranking_commentary",
    "ranking_reading",
)


def pct(x: float) -> str:
    return f"{100 * x:.1f}%"


def load_prose(set_dir: str) -> dict:
    path = os.path.join(set_dir, "prose.json")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        prose = json.load(fh)
    unknown = sorted(k for k in prose if not k.startswith("_") and k not in PROSE_KEYS)
    if unknown:
        raise SystemExit(f"{path}: unknown keys {unknown}; allowed: {list(PROSE_KEYS)}")
    return prose


def format_rules(set_dir: str) -> list:
    """Section 2, verbatim from the hand-written file."""
    path = os.path.join(set_dir, "format_rules.md")
    if not os.path.exists(path):
        raise SystemExit(
            f"missing {path} — write the set's format rules by hand first "
            "(playbook step 7)"
        )
    with open(path, encoding="utf-8") as fh:
        return fh.read().rstrip("\n").split("\n")


def mark(entry: dict) -> str:
    roles, out = entry["roles"], ""
    if "bomb" in roles:
        out += "★"
    if "removal" in roles:
        out += "✕"
    if "trick" in roles:
        out += "⚡"
    if "fixing" in roles:
        out += "◆"
    return out


def row(entry: dict) -> str:
    syn = (
        f" (→{entry['grade_synergy']} with {entry['needs_threshold']}+ {entry['needs']})"
        if "grade_synergy" in entry
        else ""
    )
    cost = entry["mana_cost"].split(" // ")[0]
    return (
        f"| {entry['grade']}{syn} | {entry['name']} | {cost} | "
        f"{entry['rarity'][0].upper()} | {mark(entry)} | {entry['note']} |"
    )


def tier_sentence(p_best: dict) -> str:
    """Read the ranking as tiers.

    Tier 1 is the top pair only when it leads the next by at least 1.5 points;
    otherwise there is no clear tier 1. Tier 3 is every pair below 8%.
    """
    order = sorted(p_best, key=lambda k: -p_best[k])
    tier3 = [p for p in order if p_best[p] < 0.08]
    lead = 100 * (p_best[order[0]] - p_best[order[1]]) if len(order) > 1 else 100.0
    tier1 = [order[0]] if lead >= 1.5 else []
    tier2 = [p for p in order if p not in tier1 and p not in tier3]
    parts = [f"Tier 1: {', '.join(tier1)}." if tier1 else "No clear tier 1."]
    if tier2:
        parts.append(f"Tier 2: {', '.join(tier2)}.")
    if tier3:
        parts.append(f"Tier 3: {', '.join(tier3)}.")
    return " ".join(parts)


def load_sims(set_dir: str) -> dict:
    """The sim runs that exist in the set directory, keyed by role."""
    runs = {}
    for key, filename in SIM_FILES:
        path = os.path.join(set_dir, filename)
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        run = next(iter(data["runs"].values()))
        runs[key] = ({p["pair"]: p for p in run["per_pair"]}, run)
    return runs


def pack_phrase(set_dir: str) -> str:
    """"6 Play Boosters plus a promo", read off the collation config."""
    path = os.path.join(set_dir, "collation.json")
    if not os.path.exists(path):
        return "one Sealed pool"
    with open(path, encoding="utf-8") as fh:
        config = json.load(fh)
    phrase = f"{config.get('packs_per_pool', '?')} Play Boosters"
    promo = config.get("promo") or {}
    if promo.get("enabled"):
        phrase += " plus a promo"
    return phrase


def build(set_dir: str) -> str:
    with open(os.path.join(set_dir, "grades.json"), encoding="utf-8") as fh:
        graded = json.load(fh)
    cards = {c["name"]: c for c in load_cards(set_dir)}
    prose = load_prose(set_dir)
    set_name = next((c.get("set_name") for c in cards.values() if c.get("set_name")), "the set")

    needs = []
    for entry in graded:
        if entry.get("needs") and entry["needs"] not in needs:
            needs.append(entry["needs"])
    synergy_list = ", ".join(f"{n} count" for n in needs) or "your synergy counts"

    out = [
        prose.get("title", f"# {set_name} prerelease cheat sheet"),
        "",
        prose.get(
            "intro",
            "Grades are Sealed grades, 0 to 10, from oracle text. ★ bomb, ✕ removal, "
            "⚡ trick or instant-speed interaction, ◆ fixing. A grade in parentheses "
            "applies when your deck holds the listed number of enablers.",
        ),
        "",
        "## 1. Scoring your pool by hand (10 minutes)",
        "",
        "1. Sort the pool by color. Hybrid cards go to whichever of their two colors you "
        "are considering; gold cards stay aside.",
        "2. For each color, count cards graded 4 or higher (playables). Write the count on "
        "the deck box. That is your depth. Count the 6-or-higher cards too; that is your "
        "quality.",
        "3. For each color, count ✕ cards. Two colors with at least 3 ✕ between them is the "
        "target.",
        "4. Take the two deepest colors. Add gold cards for that pair. Count again: you need "
        "22 to 23 spells graded 4 or higher, with 3 or more ✕ and at least one ★ (grade 8 or "
        "higher). That is the same viability test the simulation in section 5 uses.",
        prose.get(
            "procedure_splash",
            "5. If a third color holds a card graded 7 or higher, splash it only with 2 or "
            "more lands in the pool that make that color. Splash at most 2 cards.",
        ),
        "6. Build: 17 lands (duals count), 23 spells. Curve target: 1-2 one-drops, 7-8 "
        "two-drops, 5-6 three-drops, the rest 4+. Play every ✕ you can cast.",
        prose.get(
            "procedure_tiebreak",
            f"7. If two pairs tie, prefer the one with more 6-or-higher cards, then the one "
            f"whose synergy grades turn on ({synergy_list}), then the one with more 2-drops.",
        ),
        "",
        "## 2. Format rules that decide games",
        "",
    ]
    out += format_rules(set_dir)
    out += [
        "",
        "## 3. Removal by color",
        "",
        prose.get(
            "removal_lead",
            "Count and quality by colour (mono-colour cards only; ✕ role).",
        ),
        "",
        "| Colour | Common | Uncommon | Rare/Mythic | Total | Mean grade |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    counts: dict = collections.defaultdict(collections.Counter)
    grades: dict = collections.defaultdict(list)
    for entry in graded:
        if (
            "removal" in entry["roles"]
            and "Land" not in entry["type_line"]
            and len(entry["colors"]) == 1
        ):
            counts[entry["colors"][0]][entry["rarity"]] += 1
            grades[entry["colors"][0]].append(entry["grade"])
    for color in WUBRG:
        c, g = counts[color], grades[color]
        mean = f"{sum(g) / len(g):.1f}" if g else "-"
        out.append(
            f"| {color} | {c['common']} | {c['uncommon']} | {c['rare'] + c['mythic']} | "
            f"{sum(c.values())} | {mean} |"
        )

    out += ["", "Commons and uncommons you will actually open:", ""]
    removal: dict = collections.defaultdict(list)
    for entry in graded:
        if (
            "removal" in entry["roles"]
            and entry["rarity"] in ("common", "uncommon")
            and "Land" not in entry["type_line"]
        ):
            removal[bucket(entry)].append(entry)
    for key in list(WUBRG) + sorted(k for k in removal if k not in WUBRG):
        if key in removal:
            body = "; ".join(
                f"{e['name']} ({e['mana_cost'].split(' // ')[0]}, {e['grade']})"
                for e in sorted(removal[key], key=lambda e: -e["grade"])
            )
            out.append(f"- **{key}**: {body}")

    out += ["", "## 4. Tricks and instant-speed plays to respect (by open mana)", ""]
    tricks: dict = collections.defaultdict(list)
    for entry in graded:
        card = cards[entry["name"]]
        # `\bflash\b` on purpose: "flashback" is not instant speed.
        front_text = oracle_text(card).split("//")[0]
        is_instant_speed = "Instant" in entry["type_line"].split(" //")[0] or re.search(
            r"\bflash\b", front_text
        )
        if (
            is_instant_speed
            and entry["rarity"] in ("common", "uncommon")
            and ({"trick", "removal", "threat"} & set(entry["roles"]))
        ):
            tricks[bucket(entry)].append(entry)
    for key in list(WUBRG) + sorted(k for k in tricks if k not in WUBRG):
        if key in tricks:
            body = "; ".join(
                f"{e['name']} ({e['mana_cost'].split(' // ')[0]})"
                for e in sorted(tricks[key], key=lambda e: len(pips(e["mana_cost"])))
            )
            out.append(f"- **{key}**: {body}")

    sims = load_sims(set_dir)
    if "headline" in sims:
        head, run = sims["headline"]
        p_best = {k: v["p_best"] for k, v in head.items()}
        order = sorted(head, key=lambda k: -head[k]["p_best"])
        tiers = tier_sentence(p_best)
        lead = [
            f"{run['pools']:,} simulated pools of {pack_phrase(set_dir)}, scored with the "
            "grades below.",
            "P(best) = share of pools where this pair builds the highest-scoring 23.",
            "P(viable) = pool holds 23 playables, 3 removal and a bomb for this pair, with "
            "at most a 2-card splash gated on 2 lands that make the colour.",
            f"Any pair is viable in {pct(run['p_any_viable_pair'])} of pools.",
            prose.get("ranking_commentary", tiers),
        ]
        header = ["Pair", "P(best)", "P(viable)", "Mean score", "Removal in deck", "Bombs"]
        align = ["---", "---:", "---:", "---:", "---:", "---:"]
        if "spec_splash" in sims:
            header.append("P(viable) if splash gate also counts landcyclers")
            align.append("---:")
        if "nosplash" in sims:
            header.append("P(viable) with no splash")
            align.append("---:")
        out += [
            "",
            prose.get(
                "ranking_heading",
                "## 5. Archetype ranking (Monte Carlo over the booster collation)",
            ),
            "",
            " ".join(lead),
            "",
            "| " + " | ".join(header) + " |",
            "|" + "|".join(align) + "|",
        ]
        for key in order:
            h = head[key]
            cells = [
                key,
                pct(h["p_best"]),
                pct(h["p_viable"]),
                f"{h['mean_score']:.2f}",
                f"{h['mean_removal']:.1f}",
                f"{h['mean_bombs']:.2f}",
            ]
            if "spec_splash" in sims:
                cells.append(pct(sims["spec_splash"][0][key]["p_viable"]))
            if "nosplash" in sims:
                cells.append(pct(sims["nosplash"][0][key]["p_viable"]))
            out.append("| " + " | ".join(cells) + " |")
        if prose.get("ranking_reading"):
            out += ["", prose["ranking_reading"], ""]
        else:
            out.append("")

    out += ["## 6. Full graded list", ""]
    groups: dict = collections.defaultdict(list)
    for entry in graded:
        groups[bucket(entry)].append(entry)
    keys = (
        list(WUBRG)
        + sorted(k for k in groups if k.startswith("Gold"))
        + ["Hybrid (either color)", "Three+ colors", "Colorless", "Lands"]
    )
    for key in keys:
        if key not in groups:
            continue
        out += [f"### {key}", "", "| Grade | Card | Cost | R | Tags | Why |", "|---|---|---|---|---|---|"]
        out += [row(e) for e in sorted(groups[key], key=lambda e: (-e["grade"], e["name"]))]
        out.append("")
    return "\n".join(out) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--set-dir", required=True)
    ap.add_argument(
        "--print-tiers",
        action="store_true",
        help="print the tier reading computed from sim_results.json and stop",
    )
    args = ap.parse_args()

    sims = load_sims(args.set_dir)
    if args.print_tiers:
        if "headline" not in sims:
            raise SystemExit("no sim_results.json in the set directory")
        head, _ = sims["headline"]
        print(tier_sentence({k: v["p_best"] for k, v in head.items()}))
        return 0

    text = build(args.set_dir)
    out_path = os.path.join(args.set_dir, "cheat_sheet.md")
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(text)
    print("cheat_sheet.md lines:", len(text.rstrip("\n").split("\n")))
    if "headline" in sims:
        head, _ = sims["headline"]
        print("tiers from the data:", tier_sentence({k: v["p_best"] for k, v in head.items()}))
    print("wrote", out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
