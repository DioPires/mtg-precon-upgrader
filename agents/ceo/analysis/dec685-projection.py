"""DEC-685 in-memory metrics projection for stampede-acres (zero-write).

Revised package after board comment (2026-09-07):
  - Raise the Alarm  -> + Gleaming Splendor   (threat  -> engine)
  - Parallel Lives   -> + The Queen of Dale   (payoff  -> engine)

Run from repo root:
    uv run python agents/ceo/analysis/dec685-projection.py
"""
import copy
import json
import sys

sys.path.insert(0, "scripts")
import compute_deck_metrics as cdm

SWAPS = {
    "Raise the Alarm": {
        "name": "Gleaming Splendor", "type": "Enchantment",
        "primary_role": "engine", "secondary_role": "ramp",
    },
    "Parallel Lives": {
        "name": "The Queen of Dale", "type": "Legendary Creature — Human Noble",
        "primary_role": "engine", "secondary_role": "card-draw",
    },
}

deck = json.load(open("data/commanders/stampede-acres/deck.json"))
mirror, mirror_ts = cdm.load_mirror()

for label, dl in [
    ("BASELINE (current 99)", deck["decklist"]),
    ("PROJECTED (2-for-2 package)", [SWAPS.get(c["name"], c) for c in deck["decklist"]]),
]:
    d = copy.deepcopy(deck)
    d["decklist"] = copy.deepcopy(dl)
    m = cdm.compute(d, "stampede-acres", mirror, mirror_ts)
    print(f"\n===== {label} =====")
    print(f"global_health={m['global_health']} (normalized {m['global_health_normalized']})")
    for k in ["manabase_health", "role_coverage_health", "curve_health",
              "interaction_density", "gameplan_cohesion", "resilience_health"]:
        print(f"  {k}: {round(m['metrics'][k]['score'], 1)}")
    print("  gaps:", json.dumps(m.get("gaps", [])))
