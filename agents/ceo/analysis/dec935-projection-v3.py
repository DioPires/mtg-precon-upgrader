"""DEC-935 v3 in-memory metrics projection (zero-write). Lines 13-14 rejected by the board;
Samut, Hazoret's Champion evaluated as a new line and as a Hammer replacement.

    uv run python agents/ceo/analysis/dec935-projection-v3.py
"""
import copy
import json
import sys

sys.path.insert(0, "scripts")
import compute_deck_metrics as cdm

ADDS_12 = [
    {"name": "Xenagos, God of Revels", "type": "Legendary Enchantment Creature — God", "primary_role": "payoff"},
    {"name": "Rhythm of the Wild", "type": "Enchantment", "primary_role": "engine"},
    {"name": "Zopandrel, Hunger Dominus", "type": "Legendary Creature — Phyrexian Horror", "primary_role": "payoff"},
    {"name": "Aurelia, the Warleader", "type": "Legendary Creature — Angel", "primary_role": "payoff"},
    {"name": "Combat Celebrant", "type": "Creature — Human Warrior", "primary_role": "payoff"},
    {"name": "Tifa, Martial Artist", "type": "Legendary Creature — Human Monk", "primary_role": "payoff"},
    {"name": "Ghalta and Mavren", "type": "Legendary Creature — Dinosaur Vampire", "primary_role": "wincon", "wincon_style": "combat"},
    {"name": "Karlach, Fury of Avernus", "type": "Legendary Creature — Tiefling Barbarian", "primary_role": "payoff"},
    {"name": "Hammer of Purphoros", "type": "Legendary Enchantment Artifact", "primary_role": "engine"},
    {"name": "Raph & Mikey, Troublemakers", "type": "Legendary Creature — Mutant Ninja Turtle", "primary_role": "engine", "secondary_role": "payoff"},
    {"name": "Raphael, the Nightwatcher", "type": "Legendary Creature — Mutant Ninja Turtle", "primary_role": "payoff"},
    {"name": "Aggravated Assault", "type": "Enchantment", "primary_role": "payoff"},
]
CUTS_12 = ["Warstorm Surge", "Terror of the Peaks", "Purphoros, God of the Forge", "Solphim, Mayhem Dominus",
           "Mirror Entity", "Idol of Oblivion", "Birthing Pod", "Chord of Calling", "Blasphemous Act",
           "Identity Echo", "Elesh Norn, Mother of Machines", "Shamanic Revelation"]
SAMUT = {"name": "Samut, Hazoret's Champion", "type": "Legendary Creature — Human Warrior Cleric", "primary_role": "engine"}

deck = json.load(open("data/commanders/broodfire-hatchery/deck.json"))
mirror, mirror_ts = cdm.load_mirror()


def apply(dl, cuts, adds):
    out = [c for c in dl if c["name"] not in cuts] + copy.deepcopy(adds)
    assert len(out) == len(dl), (len(out), len(dl))
    return out


def report(label, dl):
    d = copy.deepcopy(deck)
    d["decklist"] = copy.deepcopy(dl)
    m = cdm.compute(d, "broodfire-hatchery", mirror, mirror_ts)
    mh = m["metrics"]["manabase_health"]["inputs"]
    print(f"\n===== {label} =====")
    print(f"global_health={m['global_health']} (normalized {m['global_health_normalized']})")
    for k in ["manabase_health", "role_coverage_health", "curve_health",
              "interaction_density", "gameplan_cohesion", "resilience_health"]:
        print(f"  {k}: {round(m['metrics'][k]['score'], 1)}")
    c = m["metrics"]["curve_health"]
    print(f"  curve avg {c['actual_avg_cmc']} target {c['target_avg_cmc']} high {c['high_curve_count']} penalty {c['topcurve_penalty']}")
    print("  roles:", json.dumps(m["metrics"]["role_coverage_health"]["by_role"]))
    print("  gaps:", json.dumps(m.get("gaps", [])))
    print("  pips required/actual:", {k: (v["required"], v["actual"]) for k, v in mh["color_requirements"].items()})


report("BASELINE (current 99)", deck["decklist"])
report("V3a: 12 lines", apply(deck["decklist"], CUTS_12, ADDS_12))
report("V3b: 12 lines + Samut / -Nesting Dragon (13 lines)", apply(deck["decklist"], CUTS_12 + ["Nesting Dragon"], ADDS_12 + [SAMUT]))
report("V3c: 12 lines, Samut instead of Hammer of Purphoros", apply(deck["decklist"], CUTS_12, [a for a in ADDS_12 if a["name"] != "Hammer of Purphoros"] + [SAMUT]))
report("V3d: 12 lines but keep Elesh Norn, cut Nesting Dragon for Raphael", apply(deck["decklist"], [c for c in CUTS_12 if c != "Elesh Norn, Mother of Machines"] + ["Nesting Dragon"], ADDS_12))
