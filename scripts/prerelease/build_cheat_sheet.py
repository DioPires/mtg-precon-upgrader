"""Write the phone-readable cheat sheet for a prerelease.

    uv run python scripts/prerelease/build_cheat_sheet.py --set-dir DIR

Reads DIR/grades.json, the card dump, DIR/format_rules.md (section 2, written
by hand) and, when they exist, the three sim result files. Writes
DIR/cheat_sheet.md with six sections:

  1. how to score a pool by hand
  2. the set's format rules, copied from format_rules.md
  3. removal by colour
  4. tricks and instant-speed plays
  5. the archetype ranking from the simulation, or without a simulation the
     ten archetypes from prose.json's pair_plans
  6. the full graded list

Sections 1, 3, 4, 5 and 6 are generated from the data. A handful of sentences
in sections 1, 3 and 5 are judgement calls about a particular set rather than
facts the tool can derive, so they can be replaced from an optional
DIR/prose.json; without that file the tool writes a generic version of each.
Run with --print-tiers to see the computed tier reading on its own.

Without sim_results.json, section 5 is written only when prose.json has
pair_plans: the heading, the optional ranking_commentary, then one block per
pair, the named pairs first in their key order and the rest in PAIRS order.
prose.json's `procedure` (a list of lines) replaces all seven step lines of
section 1; it cannot be combined with procedure_splash or procedure_tiebreak.

Grades may be halves (6.5); every comparison is `>=`, so 6.5 counts as 6+.
Tags: ★ bomb, ✕ removal, ⚡ trick, ◆ fixing, ✚ card advantage (role cardadv).

Every card name in the written sheet links to its Scryfall page (link_cards(),
one pass over the text that build() returns; the URL is the card's
`scryfall_uri` from the dump, without its query). --no-scryfall-links writes
the sheet without them.
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
    "procedure",
    "procedure_splash",
    "procedure_tiebreak",
    "removal_lead",
    "ranking_heading",
    "ranking_commentary",
    "ranking_reading",
    "pair_plans",
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
    if "procedure" in prose:
        # `procedure` replaces every step line, so a per-step override beside it
        # would be silently dropped.
        clash = [k for k in ("procedure_splash", "procedure_tiebreak") if k in prose]
        if clash:
            raise SystemExit(f"{path}: 'procedure' replaces all of section 1; remove {clash}")
        if not isinstance(prose["procedure"], list) or not all(
            isinstance(line, str) for line in prose["procedure"]
        ):
            raise SystemExit(f"{path}: 'procedure' must be a list of strings, one per line")
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
    if "cardadv" in roles:
        out += "✚"
    return out


COLOR_PIP = {"W": "⚪", "U": "🔵", "B": "⚫", "R": "🔴", "G": "🟢"}


def pip(entry: dict) -> str:
    """A colour mark that survives markdown, GitHub and the PDF: one circle per colour."""
    cols = [c for c in "WUBRG" if c in entry["colors"]]
    if "Land" in entry["type_line"].split(" //")[0] and not cols:
        return "◇"
    if not cols:
        return "◇"
    if len(cols) == 1:
        return COLOR_PIP[cols[0]]
    mc = entry["mana_cost"].split(" // ")[0]
    hybrid = any("/" in p and not any(a.isdigit() for a in p.split("/")) for p in pips(mc))
    if len(cols) == 2 and hybrid:
        return "".join(COLOR_PIP[c] for c in cols)
    return "🟡"


def heading_pip(key: str) -> str:
    """The pip for a section heading such as "W", "Gold WB", "Hybrid (either color)"."""
    if key in COLOR_PIP:
        return COLOR_PIP[key]
    if key.startswith("Gold"):
        return "🟡"
    if key.startswith("Hybrid"):
        return "⚪🔵"
    return "◇"


def toughness_census(cards: dict) -> tuple:
    """(distribution, cumulative, per_colour_le3, n) over creatures with printed toughness."""
    def front_face(card: dict) -> dict:
        faces = card.get("card_faces")
        return faces[0] if faces and "oracle_text" not in card else card

    vals, by_colour = [], collections.defaultdict(list)
    for card in cards.values():
        face = front_face(card)
        if "Creature" not in face["type_line"].split(" //")[0] or "Basic" in card["type_line"]:
            continue
        t = face.get("toughness", "")
        if not t.isdigit():
            continue
        vals.append(int(t))
        cols = face.get("colors", card.get("colors", []))
        if len(cols) == 1:
            by_colour[cols[0]].append(int(t))
    n = len(vals)
    dist = collections.Counter(min(v, 6) for v in vals)
    cum, running = {}, 0
    for t in range(0, 7):
        running += dist.get(t, 0)
        cum[t] = running / n if n else 0.0
    per_colour = {
        c: (sum(v <= 3 for v in by_colour[c]) / len(by_colour[c]) if by_colour[c] else 0.0)
        for c in WUBRG
    }
    return dist, cum, per_colour, n


def kill_share(entry: dict, card: dict, cum: dict) -> str:
    """What share of the set's creatures this removal spell answers, from its oracle text.

    The first rule that matches gives the label. Every percentage is the share
    of the census with toughness N or less (`cum`, from toughness_census()).

    1. Kill rules. The special cases: "all (no counters)", "flyers only",
       "−X/−X, X = highest MV in your graveyard", "edict", "two colours only".
       Destroy or exile with no restriction: "all", "toughness 4+ (P%)",
       "MV 3+". Damage or a −N/−N change: "≤N toughness (P%)"; when the same
       target can take a second, larger value (an "instead" clause or a
       kicker), "≤A toughness (P%) or ≤B (Q%)". A −N/−0 change is not a kill.
       Twice X damage: "all (2X damage)". A fight, or damage equal to your
       creature's power: "fight (your creature's power)".
    2. Qualifiers, a kill of part of the creatures only: "power 4+ only",
       "tapped only", "nonartifact only", "≤N toughness (P%), attackers only".
    3. "lock": the creature can't block or doesn't untap.
    4. "conditional": anything else.
    """
    text = oracle_text(card).split("//")[0]

    def share(t: int) -> str:
        return f"{100 * cum[min(t, 6)]:.0f}%"

    def up_to(t: int) -> str:
        """≤t toughness, or the "or" form when an instead or kicker clause gives the same target more."""
        more = [
            int(dmg or minus)
            for clause in re.findall(r"[^.]*\b(?:instead|kicked)\b[^.]*", text)
            for dmg, minus in re.findall(
                r"deals (\d+) damage to that creature|that creature gets -\d+/-(\d+)", clause
            )
        ]
        b = max(more, default=0)
        if b > t:
            return f"≤{t} toughness ({share(t)}) or ≤{b} ({share(b)})"
        return f"≤{t} toughness ({share(t)})"

    # 1. Kill rules.
    if re.search(r"base power and toughness 0/0", text):
        return "all (no counters)"
    if re.search(r"target creature with flying", text):
        return "flyers only"
    if re.search(r"x -1/-1 counters", text):
        return "−X/−X, X = highest MV in your graveyard"
    if re.search(r"sacrifices a creature", text):
        return "edict"
    if re.search(r"(that's|target) (green|blue|black|red|white) or (green|blue|black|red|white)", text):
        return "two colours only"
    # "with power" is a qualifier (rule 2), not an unrestricted destroy.
    if re.search(r"destroy target creature(?! with power)|exile target (creature|nonland permanent)|"
                 r"destroy target nonland permanent|"
                 r"put(s)? it on (the|their choice)|choose target nonland permanent|"
                 r"loses all abilities|destroy all creatures|exile all creatures|all creatures get -3/-3",
                 text):
        if re.search(r"toughness 4 or greater", text):
            return f"toughness 4+ ({100 * (1 - cum[3]):.0f}%)"
        if re.search(r"mana value 3 or greater", text):
            return "MV 3+"
        if re.search(r"that's (green|blue|black|red|white) or", text):
            return "two colours only"
        return "all"
    damage = [int(m) for m in re.findall(r"deals (\d) damage to (?:any target|target creature)", text)]
    if damage:
        return up_to(max(damage))
    # A −N/−0 change (no toughness loss) kills nothing.
    m = re.search(r"-(\d)/-([1-9])", text)
    if m:
        return up_to(int(m.group(2)))
    if re.search(r"deals twice x damage to (?:any target|target creature)", text):
        return "all (2X damage)"
    if re.search(r"fights?|deals? damage equal to (?:its|their) power", text):
        return "fight (your creature's power)"

    # 2. Qualifiers: the kill reaches part of the creatures only.
    m = re.search(r"destroy target creature with power (\d) or greater", text)
    if m:
        return f"power {m.group(1)}+ only"
    m = re.search(r"(?:destroy|exile) target (tapped|nonartifact) creature", text)
    if m:
        return f"{m.group(1)} only"
    m = re.search(r"deals (\d) damage to target attacking creature", text)
    if m:
        return f"{up_to(int(m.group(1)))}, attackers only"

    # 3. No kill, but the creature stops blocking or stays tapped.
    if re.search(r"can't block|doesn't untap", text):
        return "lock"
    return "conditional"


def row(entry: dict) -> str:
    syn = (
        f" (→{entry['grade_synergy']} with {entry['needs_threshold']}+ {entry['needs']})"
        if "grade_synergy" in entry
        else ""
    )
    cost = entry["mana_cost"].split(" // ")[0]
    return (
        f"| {entry['grade']}{syn} | {pip(entry)} {entry['name']} | {cost} | "
        f"{entry['rarity'][0].upper()} | {mark(entry)} | {entry['note']} |"
    )


PAIRS = ("WU", "WB", "WR", "WG", "UB", "UR", "UG", "BR", "BG", "RG")

PAIR_PLANS_LEAD = (
    "**Pair plans** (signposts = this pair's two-colour cards graded 5+; grades in brackets):"
)


def pair_blocks(order: list, plans: dict, graded: list) -> list:
    """One block per pair: the title with name and plan, Signposts, Look for.

    Both section 5 paths (with and without a simulation) print through here.
    """
    out = []
    for key in order:
        plan = plans.get(key, {})
        pair_pips = "".join(COLOR_PIP[c] for c in key)
        gold = sorted(
            (e for e in graded
             if "Land" not in e["type_line"] and len(e["colors"]) == 2
             and set(e["colors"]) == set(key) and e["grade"] >= 5),
            key=lambda e: (-e["grade"], e["name"]),
        )
        title = f"{pair_pips} **{key}{' ' + plan['name'] if plan.get('name') else ''}**"
        out.append(f"- {title}" + (f" — {plan['plan']}" if plan.get("plan") else ""))
        if gold:
            out.append("    - Signposts: " + "; ".join(f"{e['name'].split(' // ')[0]} [{e['grade']}]" for e in gold))
        if plan.get("look_for"):
            out.append(f"    - Look for: {plan['look_for']}")
    return out


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
            "⚡ trick or instant-speed interaction, ◆ fixing, ✚ card advantage. A grade "
            "in parentheses applies when your deck holds the listed number of enablers.",
        ),
        "",
        "## 1. Scoring your pool by hand (10 minutes)",
        "",
    ]
    if "procedure" in prose:
        out += prose["procedure"]
    else:
        out += [
            "1. **Sort by colour.** Hybrid cards go with either colour; gold cards aside.",
            "2. **Count per colour:** cards graded 4+ (depth) and 6+ (quality). Write both on the deck box.",
            "3. **Count ✕ per colour.** Target: 3+ across your two colours.",
            "4. **Pick the two deepest colours, add their gold cards.** Need: 22-23 cards graded 4+, 3+ ✕, 1+ ★.",
            prose.get(
                "procedure_splash",
                "5. **Splash only a 7+ card, only with 2+ lands that make its colour. Max 2 cards.**",
            ),
            "6. **Build 17 lands, 23 spells.** Curve: 1-2 one-drops, 7-8 two-drops, 5-6 three-drops. Play every ✕.",
            prose.get(
                "procedure_tiebreak",
                f"7. **Tie between pairs?** More 6+ cards wins; then synergy counts ({synergy_list}); then more 2-drops.",
            ),
        ]
    out += [
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

    dist, cum, per_colour, n_creatures = toughness_census(cards)
    out += [
        "",
        f"**What removal kills.** Toughness of the set's {n_creatures} creatures:",
        "",
        "| Toughness | 1 | 2 | 3 | 4 | 5 | 6+ |",
        "|---|---:|---:|---:|---:|---:|---:|",
        "| Share | " + " | ".join(f"{100 * dist.get(t, 0) / n_creatures:.0f}%" for t in range(1, 7)) + " |",
        "| Cumulative | " + " | ".join(f"{100 * cum[t]:.0f}%" for t in range(1, 7)) + " |",
        "",
        "Share with toughness 3 or less, by colour: "
        + ", ".join(f"{COLOR_PIP[c]} {c} {100 * per_colour[c]:.0f}%" for c in WUBRG)
        + ".",
        "",
        "Commons and uncommons you will actually open (grade, what it kills):",
        "",
    ]
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
            out.append(f"- {heading_pip(key)} **{key}**")
            out += [
                f"    - {e['name']} ({e['mana_cost'].split(' // ')[0]}, {e['grade']}, "
                f"{kill_share(e, cards[e['name']], cum)})"
                for e in sorted(removal[key], key=lambda e: -e["grade"])
            ]

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
            out.append(f"- {heading_pip(key)} **{key}**")
            out += [
                f"    - {e['name']} ({e['mana_cost'].split(' // ')[0]})"
                for e in sorted(tricks[key], key=lambda e: len(pips(e["mana_cost"])))
            ]

    sims = load_sims(set_dir)
    if "headline" in sims:
        head, run = sims["headline"]
        p_best = {k: v["p_best"] for k, v in head.items()}
        order = sorted(head, key=lambda k: -head[k]["p_best"])
        tiers = tier_sentence(p_best)
        lead = [prose.get("ranking_commentary", tiers)]
        footnote = (
            f"P(best): share of {run['pools']:,} simulated pools of {pack_phrase(set_dir)} "
            "where this pair builds the highest-scoring 23. P(viable): the pool holds 23 playables, "
            "3 ✕ and 1 ★ for this pair (2-card splash allowed off 2 lands). "
            f"Some pair is viable in {pct(run['p_any_viable_pair'])} of pools."
        )
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
        out += ["", f"<sub>{footnote}</sub>"]
        if prose.get("ranking_reading"):
            out += ["", prose["ranking_reading"]]
        out += ["", PAIR_PLANS_LEAD, ""]
        out += pair_blocks(order, prose.get("pair_plans", {}), graded)
        out.append("")
    elif prose.get("pair_plans"):
        # No simulation (DEC-1218 R3): show the ten archetypes, unranked. The
        # pairs prose.json names come first, in its key order; the rest follow.
        plans = prose["pair_plans"]
        unknown = [k for k in plans if k not in PAIRS]
        if unknown:
            raise SystemExit(f"prose.json pair_plans: unknown pairs {unknown}; use {list(PAIRS)}")
        order = list(plans) + [p for p in PAIRS if p not in plans]
        out += ["", prose.get("ranking_heading", "## 5. The ten archetypes"), ""]
        if prose.get("ranking_commentary"):
            out += [prose["ranking_commentary"], ""]
        out += [PAIR_PLANS_LEAD, ""]
        out += pair_blocks(order, plans, graded)
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
        out += [f"### {heading_pip(key)} {key}", "", "| Grade | Card | Cost | R | Tags | Why |", "|---|---|---|---|---|---|"]
        out += [row(e) for e in sorted(groups[key], key=lambda e: (-e["grade"], e["name"]))]
        out.append("")
    return "\n".join(out) + "\n"


# A markdown link or image, or an autolink, already in the text: link_cards()
# leaves it as it is.
EXISTING_LINK = re.compile(r"!?\[[^\]]*\]\([^)]*\)|<[A-Za-z][A-Za-z0-9+.-]*:[^>\s]*>")


def card_urls(cards: list) -> dict:
    """Card name -> Scryfall page: the card's `scryfall_uri` without its query.

    A two-faced card is listed under its full name and under its front face
    alone, because the signposts print the front face.
    """
    urls = {}
    for card in cards:
        if " // " in card["name"]:
            urls[card["name"].split(" // ")[0]] = card["scryfall_uri"].split("?", 1)[0]
    # A full card name wins over a front face of the same spelling.
    for card in cards:
        urls[card["name"]] = card["scryfall_uri"].split("?", 1)[0]
    return urls


def link_cards(text: str, cards: list) -> str:
    """Link every card name in the sheet to its Scryfall page.

    On every line that is not a heading (a line that starts with "#"), each
    exact, case-sensitive occurrence of a card name from the dump `cards`
    becomes [name](url). A match touches no letter or digit on either side,
    so "Hemmer" alone stays plain beside "Hemmer, Fixing What Is Broken".
    Longer names are matched first and a match never overlaps another or an
    existing link: "Eject the Warp Core" is one link, and the card "Warp Core"
    inside it gets none. Removing the links ([X](url) -> X) gives back `text`
    byte for byte.
    """
    urls = card_urls(cards)
    names = sorted(urls, key=lambda n: (-len(n), n))
    patterns = {n: re.compile(r"(?<![^\W_])" + re.escape(n) + r"(?![^\W_])") for n in names}
    out = []
    for line in text.split("\n"):
        if line.startswith("#"):
            out.append(line)
            continue
        taken = [m.span() for m in EXISTING_LINK.finditer(line)]
        links = []
        for name in names:
            if name not in line:
                continue
            for m in patterns[name].finditer(line):
                start, end = m.span()
                if all(end <= a or start >= b for a, b in taken):
                    taken.append((start, end))
                    links.append((start, end, name))
        # Right to left, so the earlier offsets stay valid.
        for start, end, name in sorted(links, reverse=True):
            line = f"{line[:start]}[{name}]({urls[name]}){line[end:]}"
        out.append(line)
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--set-dir", required=True)
    ap.add_argument(
        "--print-tiers",
        action="store_true",
        help="print the tier reading computed from sim_results.json and stop",
    )
    ap.add_argument(
        "--no-scryfall-links",
        action="store_true",
        help="write the sheet without the Scryfall link on each card name",
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
    if not args.no_scryfall_links:
        text = link_cards(text, load_cards(args.set_dir))
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
