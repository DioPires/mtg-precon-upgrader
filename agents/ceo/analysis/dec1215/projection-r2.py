"""DEC-1215 round 2: Summon: Bahamut on top of line A (+Galactus / -Zacama), zero-write projection.

    uv run python agents/ceo/analysis/dec1215/projection-r2.py
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
       "primary_role": "wincon", "secondary_role": "removal-spot"}
BAH = {"name": "Summon: Bahamut", "type": "Enchantment Creature — Saga Dragon",
       "primary_role": "removal-spot", "secondary_role": "wincon"}


def power(name):
    c = mirror[name]
    p = c.get("power") or (c.get("card_faces") or [{}])[0].get("power")
    try:
        return int(p)
    except (TypeError, ValueError):
        return 0


def report(label, dl):
    d = copy.deepcopy(deck)
    d["decklist"] = copy.deepcopy(dl)
    m = cdm.compute(d, "broodfire-hatchery", mirror, mirror_ts)
    mt = m["metrics"]
    det = mt["role_coverage_health"]["details"]
    c = mt["curve_health"]
    gaps = [g.get("role") or g.get("resilience_component") if isinstance(g, dict) else g for g in m.get("gaps", [])]
    creatures = [x["name"] for x in dl if "Creature" in x["type"]]
    pw = [power(n) for n in creatures]
    print(f"{label:44s} gh={m['global_health']}/{m['global_health_normalized']} role={round(mt['role_coverage_health']['score'])} "
          f"curve={round(c['score'])}(avg {c['actual_avg_cmc']}, 6+={c['high_curve_count']}) "
          f"spot={det['removal-spot']['actual']}/8 board={det['removal-board']['actual']}/3 ramp={det['ramp']['actual']}/10 "
          f"creatures={len(creatures)} meanPow={sum(pw)/len(pw):.2f} pow7+={sum(p >= 7 for p in pw)} gaps={gaps}")


def swap(dl, adds, cuts):
    out = [c for c in dl if c["name"] not in cuts] + list(adds)
    assert len(out) == len(dl), (adds, cuts)
    return out


base = deck["decklist"]
report("BASELINE", base)
lineA = swap(base, [GAL], ["Zacama, Primal Calamity"])
report("A  +Galactus / -Zacama", lineA)
for cut in ["Apex Altisaur", "Worldspine Wurm", "Llanowar Elves", "Birds of Paradise", "Settle the Wreckage",
            "Winds of Abandon", "Krosan Grip", "Jeska's Will", "Three Visits", "Lightning Greaves",
            "Flawless Maneuver", "Raphael, the Nightwatcher", "Nesting Dragon", "Command Beacon"]:
    report(f"A + Bahamut / -{cut}", swap(lineA, [BAH], [cut]))
report("Bahamut / -Zacama (no Galactus)", swap(base, [BAH], ["Zacama, Primal Calamity"]))
