"""DEC-544 final soundness sweep before build go.

Checks the amended 99 (dec544-final-rows.json + A1-A5 swaps) against the
local Scryfall mirror: name resolves, color identity within Naya (WRG),
Commander-legal, no duplicates, board price-bans absent.
Run from repo root: uv run python agents/ceo/analysis/dec544-soundness-check.py
"""
import json

SWAPS = {
    "Witty Roastmaster": "Bountiful Promenade",
    "Ojer Taq, Deepest Foundation // Temple of Civilization": "Vaultborn Tyrant",
    "Teferi's Protection": "Clever Concealment",
    "Angel of the Ruins": "Idol of Oblivion",
    "Congregation at Dawn": "Clifftop Retreat",
}
BASICS = {"Forest", "Plains", "Mountain"}
BANNED = {"grim monolith", "chrome mox", "mox opal", "mox diamond", "mox amber",
          "mox tantalite", "mox emerald", "mox jet", "mox pearl", "mox ruby",
          "mox sapphire", "mana crypt", "ancient tomb"}

rows = json.load(open("agents/ceo/analysis/dec544-final-rows.json"))
names = []
commander = None
for r in rows:
    n = SWAPS.get(r["name"], r["name"])
    if r["group"] == "commander":
        commander = n
    else:
        names.append(n)

mirror = json.load(open("priv_data/scryfall-oracle.json"))
cards = mirror["cards"] if isinstance(mirror, dict) and "cards" in mirror else mirror
by_name = {}
for c in (cards.values() if isinstance(cards, dict) else cards):
    by_name[c["name"].lower()] = c
    if " // " in c["name"]:
        by_name[c["name"].split(" // ")[0].lower()] = c

problems = []

# duplicates (basics exempt)
seen = set()
for n in names:
    if n in seen and n not in BASICS:
        problems.append(f"DUPLICATE: {n}")
    seen.add(n)

# per-card checks
for n in [commander] + names:
    c = by_name.get(n.lower())
    if c is None:
        problems.append(f"UNRESOLVED in mirror: {n}")
        continue
    ci = set(c.get("color_identity", []))
    if not ci <= {"W", "R", "G"}:
        problems.append(f"COLOR IDENTITY: {n} = {sorted(ci)}")
    leg = c.get("legalities", {}).get("commander")
    if leg != "legal":
        problems.append(f"NOT COMMANDER-LEGAL: {n} = {leg}")
    if c["name"].lower() in BANNED or n.lower() in BANNED:
        problems.append(f"BOARD-BANNED: {n}")

print(f"commander: {commander}")
print(f"entries in 99: {len(names)}  unique: {len(seen)}")
if problems:
    print("\nPROBLEMS:")
    for p in problems:
        print(" ", p)
else:
    print("\nALL CLEAR: names resolve, CI within Naya, commander-legal, no dupes, no banned cards.")
