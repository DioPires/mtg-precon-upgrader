"""DEC-935 v4 in-memory metrics projection (zero-write) after the adversarial review.

    uv run python agents/ceo/analysis/dec935-projection-v4.py
"""
import copy
import json
import sys

sys.path.insert(0, "scripts")
import compute_deck_metrics as cdm

ADDS = {
    "Xenagos, God of Revels": {"type": "Legendary Enchantment Creature — God", "primary_role": "payoff"},
    "Rhythm of the Wild": {"type": "Enchantment", "primary_role": "engine"},
    "Zopandrel, Hunger Dominus": {"type": "Legendary Creature — Phyrexian Horror", "primary_role": "payoff"},
    "Aurelia, the Warleader": {"type": "Legendary Creature — Angel", "primary_role": "payoff"},
    "Combat Celebrant": {"type": "Creature — Human Warrior", "primary_role": "payoff"},
    "Tifa, Martial Artist": {"type": "Legendary Creature — Human Monk", "primary_role": "payoff"},
    "Ghalta and Mavren": {"type": "Legendary Creature — Dinosaur Vampire", "primary_role": "wincon", "wincon_style": "combat"},
    "Annie Joins Up": {"type": "Legendary Enchantment", "primary_role": "engine", "secondary_role": "removal-spot"},
    "Rising of the Day": {"type": "Enchantment", "primary_role": "engine"},
    "Raph & Mikey, Troublemakers": {"type": "Legendary Creature — Mutant Ninja Turtle", "primary_role": "engine", "secondary_role": "payoff"},
    "Raphael, the Nightwatcher": {"type": "Legendary Creature — Mutant Ninja Turtle", "primary_role": "payoff"},
    "Aggravated Assault": {"type": "Enchantment", "primary_role": "payoff"},
    "Samut, Hazoret's Champion": {"type": "Legendary Creature — Human Warrior Cleric", "primary_role": "engine"},
}
LINES = [  # (add, cut)
    ("Xenagos, God of Revels", "Warstorm Surge"),
    ("Rhythm of the Wild", "Terror of the Peaks"),
    ("Zopandrel, Hunger Dominus", "Solphim, Mayhem Dominus"),
    ("Aurelia, the Warleader", "Purphoros, God of the Forge"),
    ("Combat Celebrant", "Mirror Entity"),
    ("Tifa, Martial Artist", "Idol of Oblivion"),
    ("Ghalta and Mavren", "Birthing Pod"),
    ("Annie Joins Up", "Chord of Calling"),
    ("Rising of the Day", "Caretaker's Talent"),
    ("Raph & Mikey, Troublemakers", "Identity Echo"),
    ("Raphael, the Nightwatcher", "Nesting Dragon"),
    ("Aggravated Assault", "Shamanic Revelation"),
    ("Samut, Hazoret's Champion", "Blasphemous Act"),
]

deck = json.load(open("data/commanders/broodfire-hatchery/deck.json"))
mirror, mirror_ts = cdm.load_mirror()


def apply(dl, lines):
    cuts = {c for _, c in lines}
    adds = [dict(name=a, **ADDS[a]) for a, _ in lines]
    out = [c for c in dl if c["name"] not in cuts] + adds
    assert len(out) == len(dl), (len(out), len(dl))
    return out


def report(label, dl, wincon_style=None):
    d = copy.deepcopy(deck)
    d["decklist"] = copy.deepcopy(dl)
    if wincon_style:
        d["wincon_style"] = wincon_style
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
report("V4: 13 lines", apply(deck["decklist"], LINES))
report("V4 minus line 13 (keep Blasphemous Act, no Samut)", apply(deck["decklist"], LINES[:-1]))
report("V4 with wincon_style=combat (post-approval retag preview)", apply(deck["decklist"], LINES), wincon_style="combat")
