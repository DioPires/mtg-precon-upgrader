"""DEC-543 round-6 — project metrics for adding Bloodghast over each candidate cut.

Zero-write: deep-copies the decklist in memory and calls compute_deck_metrics.compute.
"""
import copy
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location("cdm", ROOT / "scripts" / "compute_deck_metrics.py")
cdm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cdm)

DECK_ID = "hoard-and-bleed"
DECK_PATH = ROOT / "data" / "commanders" / DECK_ID / "deck.json"

BLOODGHAST = {
    "name": "Bloodghast",
    "type": "Creature — Vampire Spirit",
    "primary_role": "engine",
    "secondary_role": "recursion",
}

# Cut candidates the board could plausibly accept, plus the no-cut baseline.
CANDIDATE_CUTS = [
    None,
    "Umbral Collar Zealot",
    "Black Market Connections",
    "Fell the Profane",
    "Spiteful Banditry",
    "Bedevil",
    "Crime Novelist",
    "The Misty Mountains Cold",
    "Braids, Arisen Nightmare",
    "Blasphemous Act",
    "Marionette Apprentice",
    "Rain of Riches",
    "Chaos Warp",
    "Feed the Swarm",
]


def run(deck, label):
    m = cdm.compute(deck, DECK_ID, MIRROR, MIRROR_TS)
    c = m["metrics"]
    gaps = m.get("gaps", [])
    return {
        "label": label,
        "global": m["global_health"],
        "norm": m["global_health_normalized"],
        "mana": c["manabase_health"]["score"],
        "roles": c["role_coverage_health"]["score"],
        "curve": c["curve_health"]["score"],
        "inter": c["interaction_density"]["score"],
        "cohesion": c["gameplan_cohesion"]["score"],
        "resil": c["resilience_health"]["score"],
        "gaps": len(gaps),
        "gap_names": [g.get("role") or g.get("kind") or str(g) for g in gaps],
    }


if __name__ == "__main__":
    MIRROR, MIRROR_TS = cdm.load_mirror()
    base = json.loads(DECK_PATH.read_text())

    rows = [run(copy.deepcopy(base), "BASELINE (as committed, 99)")]

    for cut in CANDIDATE_CUTS:
        d = copy.deepcopy(base)
        if cut is not None:
            before = len(d["decklist"])
            d["decklist"] = [c for c in d["decklist"] if c["name"] != cut]
            if len(d["decklist"]) == before:
                print(f"  SKIP {cut!r} — not in decklist", file=sys.stderr)
                continue
        d["decklist"].append(copy.deepcopy(BLOODGHAST))
        label = f"+Bloodghast / -{cut}" if cut else "+Bloodghast (100 cards, illegal — reference only)"
        rows.append(run(d, label))

    hdr = f"{'scenario':<46} {'glob':>4} {'norm':>4} {'mana':>4} {'role':>4} {'curv':>4} {'intr':>4} {'coh':>4} {'res':>4} {'gaps':>4}"
    print(hdr)
    print("-" * len(hdr))
    for r in rows:
        print(
            f"{r['label']:<46} {r['global']:>4} {r['norm']:>4} {r['mana']:>4} {r['roles']:>4} "
            f"{r['curve']:>4} {r['inter']:>4} {r['cohesion']:>4} {r['resil']:>4} {r['gaps']:>4}"
            + (f"  {r['gap_names']}" if r["gaps"] else "")
        )
