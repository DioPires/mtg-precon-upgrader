"""DEC-1215: Galactus, Devourer of Worlds and Summon: Bahamut, zero-write metrics projection.

    uv run python agents/ceo/analysis/dec1215/projection.py
Writes nothing. Each line swaps cards in memory and runs compute_deck_metrics.compute.
"""
import copy
import json
import sys

sys.path.insert(0, "scripts")
import compute_deck_metrics as cdm

deck = json.load(open("data/commanders/broodfire-hatchery/deck.json"))
mirror, mirror_ts = cdm.load_mirror()

GAL = {"name": "Galactus, Devourer of Worlds", "type": "Legendary Creature — Elder Alien",
       "primary_role": "threat", "secondary_role": "removal-spot"}
BAH_SPOT = {"name": "Summon: Bahamut", "type": "Enchantment Creature — Saga Dragon",
            "primary_role": "removal-spot", "secondary_role": "wincon", "wincon_style": "damage"}
BAH_THREAT = {"name": "Summon: Bahamut", "type": "Enchantment Creature — Saga Dragon",
              "primary_role": "threat", "secondary_role": "removal-spot"}


def report(label, dl):
    d = copy.deepcopy(deck)
    d["decklist"] = copy.deepcopy(dl)
    m = cdm.compute(d, "broodfire-hatchery", mirror, mirror_ts)
    mt = m["metrics"]
    roles = mt["role_coverage_health"]["by_role"]
    c = mt["curve_health"]
    gaps = [g.get("role") or g.get("resilience_component") if isinstance(g, dict) else g for g in m.get("gaps", [])]
    print(f"{label:58s} gh={m['global_health']}/{m['global_health_normalized']} role={round(mt['role_coverage_health']['score'])} "
          f"curve={round(c['score'])}({c['actual_avg_cmc']},hi={c['high_curve_count']}) int={round(mt['interaction_density']['score'])} "
          f"spot={roles.get('removal-spot')} board={roles.get('removal-board')} wincon={roles.get('wincon')} "
          f"cohesion={round(mt['gameplan_cohesion']['score'])} res={round(mt['resilience_health']['score'])} gaps={gaps} win={m.get('win_turn',{}).get('typical')}")


def swap(dl, adds, cuts):
    out = [c for c in dl if c["name"] not in cuts] + list(adds)
    assert len(out) == len(dl), (adds, cuts)
    return out


base = deck["decklist"]
report("BASELINE", base)
for cut in ["Worldspine Wurm", "Apex Altisaur", "Zacama, Primal Calamity", "Krosan Grip"]:
    report(f"A  +Galactus / -{cut}", swap(base, [GAL], [cut]))
for tag, bah in [("spot", BAH_SPOT), ("threat", BAH_THREAT)]:
    for cut in ["Apex Altisaur", "Worldspine Wurm", "Krosan Grip", "Zacama, Primal Calamity"]:
        report(f"B[{tag}] +Bahamut / -{cut}", swap(base, [bah], [cut]))
for tag, bah in [("spot", BAH_SPOT), ("threat", BAH_THREAT)]:
    report(f"A+B[{tag}] -Worldspine, -Apex", swap(base, [GAL, bah], ["Worldspine Wurm", "Apex Altisaur"]))
    report(f"A+B[{tag}] -Worldspine, -Krosan Grip", swap(base, [GAL, bah], ["Worldspine Wurm", "Krosan Grip"]))
for tag, bah in [("spot", BAH_SPOT), ("threat", BAH_THREAT)]:
    report(f"A+B[{tag}] -Worldspine, -Zacama", swap(base, [GAL, bah], ["Worldspine Wurm", "Zacama, Primal Calamity"]))
