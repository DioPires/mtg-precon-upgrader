"""DEC-544 board-question analysis: ownership, land sweep, metrics projection.

Answers the 2026-08-22 board comment (e16eb18f). Read-only over deck files;
metrics run in-memory per the projection recipe. Run from repo root:
    uv run python agents/ceo/analysis/dec544-board-questions.py
"""
import copy
import csv
import glob
import json
import re
import sys
import unicodedata
from collections import defaultdict

sys.path.insert(0, "scripts")
import compute_deck_metrics as cdm


def norm(name: str) -> str:
    front = name.split(" // ")[0]
    s = unicodedata.normalize("NFKD", front.lower())
    return re.sub(r"[^a-z0-9]", "", s)


# ---------- ownership ----------
owned = defaultdict(int)
with open("priv_data/Owned.csv") as f:
    for row in csv.DictReader(f):
        owned[norm(row["Name"])] += int(row["Quantity"])

committed = defaultdict(int)
for path in glob.glob("data/commanders/*/deck.json"):
    d = json.load(open(path))
    if d.get("status") == "brewing":
        continue
    for c in d.get("decklist", []):
        committed[norm(c["name"])] += c.get("quantity", 1)
    if d.get("commander"):
        committed[norm(d["commander"])] += 1

prices = json.load(open("data/spellbook/price-index.json"))


def price(name: str):
    hit = prices.get(norm_price(name))
    return hit[0] if hit else None  # EUR


def norm_price(name: str) -> str:
    # price-index keys look space-separated lowercase
    front = name.split(" // ")[0]
    s = unicodedata.normalize("NFKD", front.lower())
    s = re.sub(r"[^a-z0-9]+", " ", s).strip()
    return s


CANDIDATES = [
    "Drumbellower",
    "Clever Concealment",
    "Vaultborn Tyrant",
    "Turbulent Steppe",
    "Ojer Taq, Deepest Foundation // Temple of Civilization",
    "Sun Titan",
    "Teferi's Protection",
]
print("=== candidate ownership (owned / committed-to-production / free) ===")
for name in CANDIDATES:
    k = norm(name)
    o, c = owned[k], committed[k]
    print(f"{name}: owned={o} committed={c} free={o - c} eur={price(name)}")

# ---------- proposed 99 ----------
rows = json.load(open("agents/ceo/analysis/dec544-final-rows.json"))
BASIC_QTY = {"Forest": 9, "Plains": 5, "Mountain": 5}
in99 = {norm(r["name"]) for r in rows if r["group"] != "commander"}

# ---------- owned free Naya lands not in the 99 ----------
mirror, mirror_ts = cdm.load_mirror()
mirror_by_norm = {}
for mname, mdata in mirror.items():
    mirror_by_norm.setdefault(norm(mname), mdata)

NAYA = {"R", "G", "W"}
print("\n=== owned FREE lands, Naya CI, not in proposed 99 ===")
land_hits = []
for k, qty in owned.items():
    free = qty - committed[k]
    if free <= 0 or k in in99:
        continue
    m = mirror_by_norm.get(k)
    if not m:
        continue
    tl = m.get("type_line", "")
    if "Land" not in tl.split(" // ")[0] and "Land" not in tl:
        continue
    if not set(m.get("color_identity", [])) <= NAYA:
        continue
    otext = m.get("oracle_text") or ""
    tapped = "enters tapped" in otext or "enters the battlefield tapped" in otext
    land_hits.append((m["name"], tl, free, tapped, otext.replace("\n", " | ")[:110]))
for name, tl, free, tapped, ot in sorted(land_hits):
    print(f"- {name} [{tl}] free={free} tapped={tapped} :: {ot}")

# ---------- metrics projection ----------
ROLE = {
    # creatures
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
    "Ojer Taq, Deepest Foundation // Temple of Civilization": ("payoff", None),
    "Angel of the Ruins": ("removal-spot", None),
    "Witty Roastmaster": ("payoff", None),
    "Sun Titan": ("recursion", None),
    # artifacts
    "Sol Ring": ("ramp", None),
    "Arcane Signet": ("ramp", None),
    "Skullclamp": ("card-draw", None),
    "Ashnod's Altar": ("utility", None),
    "Phyrexian Altar": ("utility", None),
    "Thornbite Staff": ("engine", None),
    "Maskwood Nexus": ("utility", None),
    "Birthing Pod": ("tutor", None),
    # enchantments
    "Goblin Bombardment": ("utility", None),
    "Impact Tremors": ("payoff", None),
    "Sylvan Library": ("card-draw", None),
    "Guardian Project": ("card-draw", None),
    "Garruk's Uprising": ("card-draw", None),
    "Aura Shards": ("removal-spot", None),
    "Smothering Tithe": ("ramp", None),
    "Warleader's Call": ("payoff", None),
    # tutors
    "Worldly Tutor": ("tutor", None),
    "Enlightened Tutor": ("tutor", None),
    "Eladamri's Call": ("tutor", None),
    "Gamble": ("tutor", None),
    "Natural Order": ("tutor", None),
    "Chord of Calling": ("tutor", None),
    "Congregation at Dawn": ("tutor", None),
    # protection / interaction / ramp / draw / added
    "Deflecting Swat": ("protection", None),
    "Flawless Maneuver": ("protection", None),
    "Teferi's Protection": ("protection", None),
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


def entry(name, type_line, qty=None):
    if name in ROLE:
        role, wstyle = ROLE[name]
    else:
        role, wstyle = ("land", None)
    e = {"name": name, "type": type_line.split(" // ")[0], "primary_role": role}
    if wstyle:
        e["wincon_style"] = wstyle
    if qty:
        e["quantity"] = qty
    return e


def build_deck(rows):
    decklist = []
    for r in rows:
        if r["group"] == "commander":
            continue
        qty = BASIC_QTY.get(r["name"])
        tl = r.get("type") or ADDED_TYPES[r["name"]]
        decklist.append(entry(r["name"], tl, qty))
    return {
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


def show(tag, deck):
    m = cdm.compute(copy.deepcopy(deck), "atla-projection", mirror, mirror_ts)
    comp = {k: round(m["metrics"][k]["score"], 1) for k in
            ["manabase_health", "role_coverage_health", "curve_health",
             "interaction_density", "gameplan_cohesion", "resilience_health"]}
    print(f"\n=== {tag}: global_health={m['global_health']} (norm {m['global_health_normalized']}) ===")
    print(json.dumps(comp, indent=1))
    print("gaps:", json.dumps(m.get("gaps", []), indent=1))
    mb = m["metrics"]["manabase_health"]
    print("manabase detail:", json.dumps({k: v for k, v in mb.items() if k != "score"})[:500])
    return m


base = build_deck(rows)
show("BASE proposed 99 (34 lands)", base)

# amended: -Sun Titan +Turbulent Steppe; -Ojer Taq +Vaultborn Tyrant;
#          -Teferi's Protection +Clever Concealment
amended = build_deck(rows)
ROLE["Vaultborn Tyrant"] = ("card-draw", None)
ROLE["Clever Concealment"] = ("protection", None)
repl = {
    "Sun Titan": ("Mana Confluence", "Land"),
    "Ojer Taq, Deepest Foundation // Temple of Civilization": ("Vaultborn Tyrant", "Creature — Dinosaur"),
    "Teferi's Protection": ("Clever Concealment", "Instant"),
}
amended["decklist"] = [
    entry(*repl[c["name"]]) if c["name"] in repl else c
    for c in amended["decklist"]
]
show("AMENDED-A 99 (cut Sun Titan for land; 35 lands, +Vaultborn, +Clever Concealment)", amended)

# variant B: keep Sun Titan (recursion); cut Witty Roastmaster for the land instead
amended_b = build_deck(rows)
repl_b = {
    "Witty Roastmaster": ("Mana Confluence", "Land"),
    "Ojer Taq, Deepest Foundation // Temple of Civilization": ("Vaultborn Tyrant", "Creature — Dinosaur"),
    "Teferi's Protection": ("Clever Concealment", "Instant"),
}
amended_b["decklist"] = [
    entry(*repl_b[c["name"]]) if c["name"] in repl_b else c
    for c in amended_b["decklist"]
]
show("AMENDED-B 99 (cut Witty Roastmaster for land; Sun Titan stays)", amended_b)

# RECOMMENDED: B + (Angel of the Ruins -> Idol of Oblivion) for a second draw engine
ROLE["Idol of Oblivion"] = ("card-draw", None)
rec = build_deck(rows)
repl_r = dict(repl_b)
repl_r["Angel of the Ruins"] = ("Idol of Oblivion", "Artifact")
rec["decklist"] = [
    entry(*repl_r[c["name"]]) if c["name"] in repl_r else c
    for c in rec["decklist"]
]
show("RECOMMENDED 99 (B + Idol of Oblivion for Angel of the Ruins)", rec)

# optional 36th land: Congregation at Dawn -> Prismatic Vista
rec36 = copy.deepcopy(rec)
rec36["decklist"] = [
    entry("Prismatic Vista", "Land") if c["name"] == "Congregation at Dawn" else c
    for c in rec36["decklist"]
]
show("OPTIONAL 36-land variant (also cut Congregation at Dawn for Prismatic Vista)", rec36)
