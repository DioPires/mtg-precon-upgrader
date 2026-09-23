"""Build grades.json from grades_src.py + fra_all_cards.json. Validates full coverage."""
import json, re, sys
sys.path.insert(0, ".")
from grades_src import G
cards = {c["name"]: c for c in json.load(open("fra_all_cards.json")) if "Basic" not in c["type_line"]}
names = [g[0] for g in G]
missing = sorted(set(cards) - set(names)); extra = sorted(set(names) - set(cards)); dup = sorted({n for n in names if names.count(n) > 1})
if missing or extra or dup:
    print("MISSING:", missing); print("EXTRA:", extra); print("DUP:", dup); sys.exit(1)
def ora(c): return (c.get("oracle_text") or " ".join(f.get("oracle_text", "") for f in c.get("card_faces", []))).lower()
def provides(c):
    o, t = ora(c), c["type_line"].lower(); p = set()
    if "empower jace" in o or "planeswalker —" in t: p.add("jace")
    if "planeswalker —" in t: p.add("planeswalker")
    if re.search(r"\bmill\b|\bsurveil\b|put .* into your graveyard|from your graveyard", o): p.add("graveyard")
    if re.search(r"\bscry\b|\bsurveil\b", o): p.add("surveil")
    if re.search(r"gain \d+ life|gain life|lifelink|you gain \w+ life", o): p.add("lifegain")
    if "artifact" in t or "artifact token" in o or "heartwood" in o or "thopter" in o or "treasure" in o: p.add("artifact")
    return sorted(p)
out = []
for name, grade, roles, note, syn in G:
    c = cards[name]
    e = {"name": name, "rarity": c["rarity"], "colors": c.get("colors", []), "mana_cost": c.get("mana_cost") or (c.get("card_faces") or [{}])[0].get("mana_cost", ""),
         "type_line": c["type_line"], "grade": grade, "roles": roles, "provides": provides(c), "note": note}
    if syn: e["needs"], e["needs_threshold"], e["grade_synergy"] = syn
    if grade >= 8 and "bomb" not in roles: e["roles"] = roles + ["bomb"]
    out.append(e)
json.dump(out, open("grades.json", "w"), indent=1)
import collections
print("entries:", len(out)); print("grade hist:", dict(sorted(collections.Counter(e["grade"] for e in out).items())))
print("removal:", sum("removal" in e["roles"] for e in out), "bombs:", sum("bomb" in e["roles"] for e in out))
bycol = collections.defaultdict(list)
for e in out:
    k = "".join(sorted(e["colors"])) or "C"
    if len(k) == 1: bycol[k].append(e)
for k in "WUBRG":
    es = bycol[k]; print(k, "n=%d mean=%.2f playable(>=4)=%d removal=%d bombs=%d" % (len(es), sum(e["grade"] for e in es)/len(es), sum(e["grade"] >= 4 for e in es), sum("removal" in e["roles"] for e in es), sum("bomb" in e["roles"] for e in es)))
print("provides jace:", sum("jace" in e["provides"] for e in out), "graveyard:", sum("graveyard" in e["provides"] for e in out), "lifegain:", sum("lifegain" in e["provides"] for e in out))
