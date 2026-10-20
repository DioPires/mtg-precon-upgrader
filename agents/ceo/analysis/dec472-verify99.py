"""DEC-472 final-99 verification: counts, legality, color identity, pip census."""
import json
from collections import Counter

spec = json.load(open("agents/ceo/analysis/dec472-final99.json"))
mirror = json.load(open("priv_data/scryfall-oracle.json"))
by_name = {}
for c in mirror if isinstance(mirror, list) else mirror.get("cards", []):
    by_name[c["name"]] = c
    if "//" in c["name"]:
        by_name[c["name"].split(" //")[0]] = c

names = list(spec["nonland"]) + [n for n, q in spec["lands"].items() for _ in range(q)]
print("total cards:", len(names))
assert len(names) == 99, len(names)
dupes = [n for n, k in Counter(names).items() if k > 1 and n not in ("Island", "Mountain", "Plains")]
print("unexpected duplicates:", dupes or "none")

CI = {"W", "U", "R"}
problems = []
for n in sorted(set(names)):
    c = by_name.get(n)
    if not c:
        problems.append(f"NOT IN MIRROR: {n}")
        continue
    ci = set(c.get("color_identity", []))
    if not ci <= CI:
        problems.append(f"CI VIOLATION: {n} = {sorted(ci)}")
    leg = c.get("legalities", {}).get("commander")
    if leg != "legal":
        problems.append(f"NOT LEGAL: {n} = {leg}")
print("problems:", problems or "none")

# pip census on nonland mana costs
pips = Counter()
for n in spec["nonland"]:
    c = by_name.get(n)
    if not c:
        continue
    cost = c.get("mana_cost") or (c.get("card_faces", [{}])[0].get("mana_cost", ""))
    for sym in ("W", "U", "R"):
        pips[sym] += cost.count(sym)
print("pip census (nonland):", dict(pips))

# colored-source count per color from lands
src = Counter()
for n, q in spec["lands"].items():
    c = by_name.get(n)
    text = (c.get("oracle_text") or "") if c else ""
    tl = (c.get("type_line") or "") if c else ""
    for col, base in (("W", "Plains"), ("U", "Island"), ("R", "Mountain")):
        if base in tl or f"{{{col}}}" in text or "any color" in text or "Command Tower" == n or n in ("Exotic Orchard", "Path of Ancestry"):
            src[col] += q
print("approx colored sources:", dict(src), "| total lands:", sum(spec['lands'].values()))

# commander check
cmd = by_name.get(spec["commander"])
print("commander:", spec["commander"], "found:", bool(cmd))
if cmd:
    print("  CI:", cmd.get("color_identity"), "| legal:", cmd.get("legalities", {}).get("commander"))
    print("  oracle:", (cmd.get("oracle_text") or "").replace("\n", " | "))
