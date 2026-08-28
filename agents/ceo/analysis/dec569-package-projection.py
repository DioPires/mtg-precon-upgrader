"""DEC-569 — project metrics for the board-requested Dionus + Disciple of Freyalise package.

Zero-write: deep-copies the decklist in memory and calls compute_deck_metrics.compute.
Swap 1 is fixed (+Dionus / -Sakura-Tribe Elder, conditionally accepted by the board).
Swap 2 add is fixed (+Disciple of Freyalise); we project each plausible cut.
"""
import copy
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location("cdm", ROOT / "scripts" / "compute_deck_metrics.py")
cdm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cdm)

DECK_ID = "verdant-tide"
DECK_PATH = ROOT / "data" / "commanders" / DECK_ID / "deck.json"

DIONUS = {
    "name": "Dionus, Elvish Archdruid",
    "type": "Legendary Creature — Elf Druid",
    "primary_role": "engine",
    "secondary_role": "payoff",
}
DISCIPLE = {
    "name": "Disciple of Freyalise // Garden of Freyalise",
    "type": "Creature — Elf Druid",
    "primary_role": "card-draw",
    "is_mdfc_land": True,
}

# Cut options for the Disciple slot. SNOW_FOREST = drop 1 Snow-Covered Forest.
CANDIDATE_CUTS = [
    "SNOW_FOREST",
    "Badgermole Cub",
    "Formidable Speaker",
    "Selfless Safewright",
    "Sensei's Divining Top",
]


def run(deck, label):
    m = cdm.compute(deck, DECK_ID, MIRROR, MIRROR_TS)
    c = m["metrics"]
    gaps = m.get("gaps", [])
    n = sum(x.get("quantity", 1) for x in deck["decklist"])
    print(
        f"{label:38s} n={n} global={m['global_health']} norm={m['global_health_normalized']} "
        f"mana={c['manabase_health']['score']} roles={c['role_coverage_health']['score']} "
        f"curve={c['curve_health']['score']} inter={c['interaction_density']['score']} "
        f"cohesion={c['gameplan_cohesion']['score']} resil={c['resilience_health']['score']} "
        f"gaps={[g.get('role') or g.get('kind') or str(g) for g in gaps]}"
    )


if __name__ == "__main__":
    MIRROR, MIRROR_TS = cdm.load_mirror()
    base = json.loads(DECK_PATH.read_text())

    run(copy.deepcopy(base), "BASELINE (current)")

    for cut in CANDIDATE_CUTS:
        d = copy.deepcopy(base)
        dl = d["decklist"]
        dl = [c for c in dl if c["name"] != "Sakura-Tribe Elder"]
        dl.append(copy.deepcopy(DIONUS))
        if cut == "SNOW_FOREST":
            for c in dl:
                if c["name"] == "Snow-Covered Forest":
                    c["quantity"] = c.get("quantity", 1) - 1
        else:
            assert any(c["name"] == cut for c in dl), cut
            dl = [c for c in dl if c["name"] != cut]
        dl.append(copy.deepcopy(DISCIPLE))
        d["decklist"] = dl
        run(d, f"PKG cut={cut}")
