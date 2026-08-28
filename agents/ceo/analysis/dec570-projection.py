"""DEC-570 in-memory metrics projection for broodfire-hatchery (zero-write).

Package under evaluation (proposal only, nothing applied):
  - Idol of Oblivion      -> + Caretaker's Talent   (card-draw -> card-draw)
  - Gamble                -> + Winds of Abandon     (tutor     -> removal-board)
  - Warleader's Call      -> + Elspeth, Storm Slayer (payoff   -> payoff)

Run from repo root:
    uv run python agents/ceo/analysis/dec570-projection.py
"""
import copy
import json
import sys

sys.path.insert(0, "scripts")
import compute_deck_metrics as cdm

SWAPS = {
    "Idol of Oblivion": {
        "name": "Caretaker's Talent", "type": "Enchantment",
        "primary_role": "card-draw",
    },
    "Gamble": {
        "name": "Winds of Abandon", "type": "Sorcery",
        "primary_role": "removal-board",
    },
    "Warleader's Call": {
        "name": "Elspeth, Storm Slayer", "type": "Planeswalker",
        "primary_role": "payoff",
    },
}

deck = json.load(open("data/commanders/broodfire-hatchery/deck.json"))
mirror, mirror_ts = cdm.load_mirror()

for label, dl in [
    ("BASELINE (current 99)", deck["decklist"]),
    ("PROJECTED (3-swap package)", [SWAPS.get(c["name"], c) for c in deck["decklist"]]),
]:
    d = copy.deepcopy(deck)
    d["decklist"] = copy.deepcopy(dl)
    m = cdm.compute(d, "broodfire-hatchery", mirror, mirror_ts)
    print(f"\n===== {label} =====")
    print(f"global_health={m['global_health']} (normalized {m['global_health_normalized']})")
    for k in ["manabase_health", "role_coverage_health", "curve_health",
              "interaction_density", "gameplan_cohesion", "resilience_health"]:
        print(f"  {k}: {round(m['metrics'][k]['score'], 1)}")
    print("  gaps:", json.dumps(m.get("gaps", [])))
