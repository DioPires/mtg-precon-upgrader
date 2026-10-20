"""DEC-1215 round 2: Summon: Bahamut re-assessed after the board's comments (owned; noncombat damage is fine as a second route).

    uv run python agents/ceo/analysis/dec1215/projection2.py
Writes nothing. Each line swaps cards in memory, runs compute_deck_metrics.compute and the reveal-pool stats.
"""
import copy
import json
import statistics
import sys

sys.path.insert(0, "scripts")
import compute_deck_metrics as cdm

deck = json.load(open("data/commanders/broodfire-hatchery/deck.json"))
mirror, mirror_ts = cdm.load_mirror()
oracle = {c["name"]: c for c in json.load(open("priv_data/scryfall-oracle.json")) if c.get("layout") != "art_series"}

GAL = {"name": "Galactus, Devourer of Worlds", "type": "Legendary Creature — Elder Alien",
       "primary_role": "wincon", "secondary_role": "removal-spot"}
BAH = {"name": "Summon: Bahamut", "type": "Enchantment Creature — Saga Dragon",
       "primary_role": "removal-spot", "secondary_role": "wincon"}


def face(name):
    c = oracle[name]
    return c["card_faces"][0] if "card_faces" in c and "power" not in c else c


def pool(dl):
    """Creature cards in the library (the commander is not in it). Each entry once per copy."""
    out = []
    for e in dl:
        if "Creature" not in e.get("type", "").split("//")[0]:
            continue
        f = face(e["name"])
        out += [(e["name"], int(f["power"]), oracle[e["name"]]["cmc"])] * e.get("quantity", 1)
    return out


def report(label, dl):
    d = copy.deepcopy(deck)
    d["decklist"] = copy.deepcopy(dl)
    m = cdm.compute(d, "broodfire-hatchery", mirror, mirror_ts)
    mt = m["metrics"]
    det = mt["role_coverage_health"]["details"]
    p = pool(dl)
    print(f"{label:52s} gh={m['global_health']} role={round(mt['role_coverage_health']['score'])} "
          f"curve={round(mt['curve_health']['score'])}({mt['curve_health']['actual_avg_cmc']}) "
          f"spot={det['removal-spot']['actual']} wincon={det['wincon']['actual']} draw={det['card-draw']['actual']} "
          f"creatures={len(p)} meanPower={statistics.mean(x[1] for x in p):.2f} meanCreatureMV={statistics.mean(x[2] for x in p):.2f} "
          f"bigMV9+={sum(1 for x in p if x[2] >= 9)}")


def swap(dl, adds, cuts):
    out = [c for c in dl if c["name"] not in cuts] + list(adds)
    assert len(out) == len(dl), (adds, cuts)
    return out


base = deck["decklist"]
a = swap(base, [GAL], ["Zacama, Primal Calamity"])
report("BASELINE", base)
report("A   +Galactus / -Zacama", a)
for cut in ["Blightsteel Colossus", "Etali, Primal Conqueror // Etali, Primal Sickness", "Krosan Grip", "Llanowar Elves"]:
    report(f"A+C +Bahamut / -{cut.split(' //')[0]}", swap(a, [BAH], [cut]))
report("C only +Bahamut / -Blightsteel Colossus", swap(base, [BAH], ["Blightsteel Colossus"]))
