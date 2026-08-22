"""DEC-544 final amended 99 (A1-A5 board-accepted 2026-08-22): metrics + role census.

In-memory projection only — no deck files exist yet (decklist gate still open).
Run from repo root:
    uv run python agents/ceo/analysis/dec544-final-metrics.py
"""
import copy
import json
import sys
from collections import Counter

sys.path.insert(0, "scripts")
import compute_deck_metrics as cdm

ROLE = {
    "Mirror Entity": ("wincon", "combo"),
    "Seedborn Muse": ("engine", None),
    "Palani's Hatcher": ("engine", None),
    "Nesting Dragon": ("engine", None),
    "Mondrak, Glory Dominus": ("payoff", None),
    "Birds of Paradise": ("ramp", None),
    "Llanowar Elves": ("ramp", None),
    "Zacama, Primal Calamity": ("wincon", "combat"),
    "Etali, Primal Conqueror // Etali, Primal Sickness": ("wincon", "combat"),
    "Terror of the Peaks": ("payoff", None),
    "Purphoros, God of the Forge": ("wincon", "drain"),
    "Worldspine Wurm": ("threat", None),
    "Blightsteel Colossus": ("wincon", "combat"),
    "Vigor": ("protection", None),
    "Avacyn, Angel of Hope": ("protection", None),
    "Craterhoof Behemoth": ("wincon", "combat"),
    "Elesh Norn, Mother of Machines": ("payoff", None),
    "Titan of Industry": ("threat", None),
    "Apex Altisaur": ("removal-board", None),
    "Roaming Throne": ("payoff", None),
    "Sun Titan": ("recursion", None),
    "Vaultborn Tyrant": ("card-draw", None),
    "Sol Ring": ("ramp", None),
    "Arcane Signet": ("ramp", None),
    "Skullclamp": ("card-draw", None),
    "Ashnod's Altar": ("utility", None),
    "Phyrexian Altar": ("utility", None),
    "Thornbite Staff": ("engine", None),
    "Maskwood Nexus": ("utility", None),
    "Birthing Pod": ("tutor", None),
    "Idol of Oblivion": ("card-draw", None),
    "Goblin Bombardment": ("utility", None),
    "Impact Tremors": ("payoff", None),
    "Sylvan Library": ("card-draw", None),
    "Guardian Project": ("card-draw", None),
    "Garruk's Uprising": ("card-draw", None),
    "Aura Shards": ("removal-spot", None),
    "Smothering Tithe": ("ramp", None),
    "Warleader's Call": ("payoff", None),
    "Worldly Tutor": ("tutor", None),
    "Enlightened Tutor": ("tutor", None),
    "Eladamri's Call": ("tutor", None),
    "Gamble": ("tutor", None),
    "Natural Order": ("tutor", None),
    "Chord of Calling": ("tutor", None),
    "Deflecting Swat": ("protection", None),
    "Flawless Maneuver": ("protection", None),
    "Clever Concealment": ("protection", None),
    "Heroic Intervention": ("protection", None),
    "Swords to Plowshares": ("removal-spot", None),
    "Path to Exile": ("removal-spot", None),
    "Krosan Grip": ("removal-spot", None),
    "Force of Vigor": ("removal-spot", None),
    "Blasphemous Act": ("removal-board", None),
    "Nature's Lore": ("ramp", None),
    "Three Visits": ("ramp", None),
    "Farseek": ("ramp", None),
    "Utopia Sprawl": ("ramp", None),
    "Wild Growth": ("ramp", None),
    "Jeska's Will": ("ramp", None),
    "Rishkar's Expertise": ("card-draw", None),
    "Lightning Greaves": ("protection", None),
    "Beast Within": ("removal-spot", None),
}

ADDED_TYPES = {"Lightning Greaves": "Artifact — Equipment", "Beast Within": "Instant"}
BASIC_QTY = {"Forest": 9, "Plains": 5, "Mountain": 5}

# A1-A5, all board-accepted (comment fece0faf)
SWAPS = {
    "Witty Roastmaster": ("Bountiful Promenade", "Land"),
    "Ojer Taq, Deepest Foundation // Temple of Civilization": ("Vaultborn Tyrant", "Creature — Dinosaur"),
    "Teferi's Protection": ("Clever Concealment", "Instant"),
    "Angel of the Ruins": ("Idol of Oblivion", "Artifact"),
    "Congregation at Dawn": ("Clifftop Retreat", "Land"),
}


def entry(name, type_line, qty=None):
    role, wstyle = ROLE.get(name, ("land", None))
    e = {"name": name, "type": type_line.split(" // ")[0], "primary_role": role}
    if wstyle:
        e["wincon_style"] = wstyle
    if qty:
        e["quantity"] = qty
    return e


rows = json.load(open("agents/ceo/analysis/dec544-final-rows.json"))
decklist = []
for r in rows:
    if r["group"] == "commander":
        continue
    name, tl = SWAPS.get(r["name"], (r["name"], r.get("type") or ADDED_TYPES[r["name"]]))
    decklist.append(entry(name, tl, BASIC_QTY.get(name)))

deck = {
    "id": "atla-hatchery",
    "type": "commander",
    "name": "Atla projection",
    "commander": "Atla Palani, Nest Tender",
    "bracket": "4",
    "wincon_style": "combo",
    "archetypes": ["ramp-big-mana", "aristocrats"],
    "commanderRoles": {"primary_role": "engine", "secondary_role": "tutor"},
    "decklist": decklist,
}

total = sum(c.get("quantity", 1) for c in decklist)
print(f"cards in 99: {total} ({len(decklist)} entries)")

gc = {c.lower() for c in json.load(open("data/game-changers.json"))["cards"]} \
    if isinstance(json.load(open("data/game-changers.json")), dict) else None
gc_raw = json.load(open("data/game-changers.json"))
gc_names = {(c["name"] if isinstance(c, dict) else c).lower()
            for c in (gc_raw["cards"] if isinstance(gc_raw, dict) else gc_raw)}
in_gc = sorted(c["name"] for c in decklist if c["name"].split(" // ")[0].lower() in gc_names)
print(f"game changers ({len(in_gc)}):", ", ".join(in_gc))

role_census = Counter(c["primary_role"] for c in decklist for _ in range(c.get("quantity", 1)))
print("\nrole census:")
for role, n in role_census.most_common():
    print(f"  {role}: {n}")

mirror, mirror_ts = cdm.load_mirror()
m = cdm.compute(copy.deepcopy(deck), "atla-projection", mirror, mirror_ts)
print(f"\nglobal_health={m['global_health']} (normalized {m['global_health_normalized']})")
for k in ["manabase_health", "role_coverage_health", "curve_health",
          "interaction_density", "gameplan_cohesion", "resilience_health"]:
    print(f"\n--- {k}: {round(m['metrics'][k]['score'], 1)} ---")
    print(json.dumps({kk: vv for kk, vv in m["metrics"][k].items() if kk != "score"},
                     ensure_ascii=False)[:900])
print("\ngaps:", json.dumps(m.get("gaps", []), indent=1))
