"""DEC-934 in-memory metrics projection for broodfire-hatchery (zero-write).

Line A under evaluation (proposal only, nothing applied):
  - Nesting Dragon -> + Ojer Taq, Deepest Foundation // Temple of Civilization (engine -> payoff)

Run from repo root:
    uv run python agents/ceo/analysis/dec934-projection.py
"""
import copy
import json
import sys

sys.path.insert(0, "scripts")
import compute_deck_metrics as cdm

LINES = {
    "A: +Ojer Taq / -Nesting Dragon": {
        "Nesting Dragon": {
            "name": "Ojer Taq, Deepest Foundation // Temple of Civilization",
            "type": "Legendary Creature — God // Land",
            "primary_role": "payoff",
        },
    },
    "B (reference): +Celebrate the Mountain-king / -Shamanic Revelation": {
        "Shamanic Revelation": {
            "name": "Celebrate the Mountain-king",
            "type": "Enchantment",
            "primary_role": "removal-spot",
        },
    },
}

deck = json.load(open("data/commanders/broodfire-hatchery/deck.json"))
mirror, mirror_ts = cdm.load_mirror()


def report(label, dl):
    d = copy.deepcopy(deck)
    d["decklist"] = copy.deepcopy(dl)
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


report("BASELINE (current 99)", deck["decklist"])
for label, swaps in LINES.items():
    report(label, [swaps.get(c["name"], c) for c in deck["decklist"]])
