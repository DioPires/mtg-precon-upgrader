"""DEC-935 follow-up: Ajani's Anguish zero-write metrics projection against candidate cuts.

    uv run python agents/ceo/analysis/dec935-ajani-projection.py
v2: both role taggings (removal-spot primary vs payoff primary) + a Rogue's Passage land line.
"""
import copy
import json
import sys

sys.path.insert(0, "scripts")
import compute_deck_metrics as cdm

TAGS = {
    "spot-primary": {"primary_role": "removal-spot", "secondary_role": "payoff"},
    "payoff-primary": {"primary_role": "payoff", "secondary_role": "removal-spot"},
}
CUTS = ["Deflecting Swat", "Lightning Greaves", "Krosan Grip", "Thornbite Staff", "Roaming Throne", "Garruk's Uprising"]

deck = json.load(open("data/commanders/broodfire-hatchery/deck.json"))
mirror, mirror_ts = cdm.load_mirror()


def report(label, dl):
    d = copy.deepcopy(deck)
    d["decklist"] = copy.deepcopy(dl)
    m = cdm.compute(d, "broodfire-hatchery", mirror, mirror_ts)
    mh = m["metrics"]["manabase_health"]["inputs"]
    roles = m["metrics"]["role_coverage_health"]["by_role"]
    c = m["metrics"]["curve_health"]
    gaps = [g.get("role") or g.get("resilience_component") if isinstance(g, dict) else g for g in m.get("gaps", [])]
    print(f"{label:52s} gh={m['global_health']}/{m['global_health_normalized']} mana={round(m['metrics']['manabase_health']['score'])} "
          f"role={round(m['metrics']['role_coverage_health']['score'])} curve={round(m['metrics']['curve_health']['score'])}({c['actual_avg_cmc']}) "
          f"int={round(m['metrics']['interaction_density']['score'])} spot={roles.get('removal-spot')} prot={roles.get('protection')} "
          f"draw={roles.get('card-draw')} gaps={gaps} "
          f"R={mh['color_requirements']['R']['required']}/{int(mh['color_sources']['R'])} G={mh['color_requirements']['G']['required']}/{int(mh['color_sources']['G'])}")


report("BASELINE", deck["decklist"])
for tag, roles in TAGS.items():
    add = dict(name="Ajani's Anguish", type="Enchantment", **roles)
    for cut in CUTS:
        dl = [c for c in deck["decklist"] if c["name"] != cut] + [add]
        assert len(dl) == len(deck["decklist"])
        report(f"[{tag}] +Anguish / -{cut}", dl)
# Land line: Rogue's Passage replaces one basic Forest (quantity 9 -> 8)
dl = copy.deepcopy(deck["decklist"])
for c in dl:
    if c["name"] == "Forest":
        c["quantity"] = c["quantity"] - 1
dl.append({"name": "Rogue's Passage", "type": "Land", "primary_role": "land"})
report("+Rogue's Passage / -Forest (land line only)", dl)
