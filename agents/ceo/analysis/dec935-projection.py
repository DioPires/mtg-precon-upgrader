"""DEC-935 in-memory metrics projection for broodfire-hatchery (zero-write).

Combat remake proposal (nothing applied). Run from repo root:
    uv run python agents/ceo/analysis/dec935-projection.py
"""
import copy
import json
import sys

sys.path.insert(0, "scripts")
import compute_deck_metrics as cdm

ADDS = [
    {"name": "Xenagos, God of Revels", "type": "Legendary Enchantment Creature — God", "primary_role": "payoff"},
    {"name": "Rhythm of the Wild", "type": "Enchantment", "primary_role": "engine"},
    {"name": "Zopandrel, Hunger Dominus", "type": "Legendary Creature — Phyrexian Horror", "primary_role": "payoff"},
    {"name": "Aurelia, the Warleader", "type": "Legendary Creature — Angel", "primary_role": "payoff"},
    {"name": "Combat Celebrant", "type": "Creature — Human Warrior", "primary_role": "payoff"},
    {"name": "Tifa, Martial Artist", "type": "Legendary Creature — Human Monk", "primary_role": "payoff"},
    {"name": "Ghalta and Mavren", "type": "Legendary Creature — Dinosaur Vampire", "primary_role": "wincon", "wincon_style": "combat"},
    {"name": "Karlach, Fury of Avernus", "type": "Legendary Creature — Tiefling Barbarian", "primary_role": "payoff"},
    {"name": "Hammer of Purphoros", "type": "Legendary Enchantment Artifact", "primary_role": "engine"},
]
CUTS_MAIN = ["Warstorm Surge", "Terror of the Peaks", "Purphoros, God of the Forge", "Solphim, Mayhem Dominus",
             "Mirror Entity", "Idol of Oblivion", "Birthing Pod", "Chord of Calling", "Blasphemous Act"]
CUTS_ALT = CUTS_MAIN[:-1] + ["Shamanic Revelation"]

deck = json.load(open("data/commanders/broodfire-hatchery/deck.json"))
mirror, mirror_ts = cdm.load_mirror()


def apply(dl, cuts, adds, archetypes=None):
    out = [c for c in dl if c["name"] not in cuts] + copy.deepcopy(adds)
    assert len(out) == len(dl), (len(out), len(dl))
    return out


def report(label, dl, archetypes=None):
    d = copy.deepcopy(deck)
    d["decklist"] = copy.deepcopy(dl)
    if archetypes:
        d["archetypes"] = archetypes
    m = cdm.compute(d, "broodfire-hatchery", mirror, mirror_ts)
    print(f"\n===== {label} =====")
    print(f"global_health={m['global_health']} (normalized {m['global_health_normalized']})")
    for k in ["manabase_health", "role_coverage_health", "curve_health",
              "interaction_density", "gameplan_cohesion", "resilience_health"]:
        print(f"  {k}: {round(m['metrics'][k]['score'], 1)}")
    c = m["metrics"]["curve_health"]
    print(f"  curve avg {c['actual_avg_cmc']} target {c['target_avg_cmc']} high {c['high_curve_count']} penalty {c['topcurve_penalty']}")
    print("  roles:", json.dumps(m["metrics"]["role_coverage_health"]["by_role"]))
    print("  gaps:", json.dumps(m.get("gaps", [])))
    print("  mana:", json.dumps(m["metrics"]["manabase_health"]["inputs"]["color_requirements"]))


ADDS_V2 = ADDS + [
    {"name": "Raph & Mikey, Troublemakers", "type": "Legendary Creature — Mutant Ninja Turtle", "primary_role": "engine", "secondary_role": "payoff"},
    {"name": "Raphael, the Nightwatcher", "type": "Legendary Creature — Mutant Ninja Turtle", "primary_role": "payoff"},
    {"name": "Aggravated Assault", "type": "Enchantment", "primary_role": "payoff"},
]
CUTS_V2 = CUTS_MAIN + ["Identity Echo", "Elesh Norn, Mother of Machines", "Shamanic Revelation"]
ADDS_V2_OPT = ADDS_V2 + [
    {"name": "Raph & Leo, Sibling Rivals", "type": "Legendary Creature — Mutant Ninja Turtle", "primary_role": "payoff"},
    {"name": "Fiery Emancipation", "type": "Enchantment", "primary_role": "payoff"},
]
CUTS_V2_OPT = CUTS_V2 + ["Nesting Dragon", "Caretaker's Talent"]

report("BASELINE (current 99)", deck["decklist"])
report("V1: 9 swaps (cut Blasphemous Act)", apply(deck["decklist"], CUTS_MAIN, ADDS))
report("V2: 12 swaps (+Raph & Mikey, Raphael, Aggravated Assault)", apply(deck["decklist"], CUTS_V2, ADDS_V2))
report("V2 + optional 13-14 (+Raph & Leo, Fiery Emancipation)", apply(deck["decklist"], CUTS_V2_OPT, ADDS_V2_OPT))
