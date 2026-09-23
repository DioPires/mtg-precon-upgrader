"""Emit cheat_sheet.md from grades.json + fra_all_cards.json. Phone-readable; the sim ranking section is filled by hand."""
import json, re, collections
G = json.load(open("grades.json")); cards = {c["name"]: c for c in json.load(open("fra_all_cards.json"))}
ORDER = {"W": 0, "U": 1, "B": 2, "R": 3, "G": 4}
def pips(mc): return re.findall(r"\{([^}]*)\}", mc or "")
def castable(e, pair):
    for p in pips(e["mana_cost"].split(" // ")[0]):
        if p.isdigit() or p in ("X", "C"): continue
        alts = p.split("/")
        if any(a.isdigit() for a in alts): continue
        if not any(a in pair for a in alts): return False
    return True
def bucket(e):
    cols = "".join(sorted(e["colors"], key=lambda c: ORDER.get(c, 9)))
    mc = e["mana_cost"].split(" // ")[0]
    if "Land" in e["type_line"].split(" //")[0]: return "Lands"
    if not cols: return "Colorless"
    hyb = any("/" in p and not any(a.isdigit() for a in p.split("/")) for p in pips(mc))
    if len(cols) == 1: return cols
    if hyb and len(cols) == 2: return "Hybrid (either color)"
    return "Gold " + cols if len(cols) == 2 else "Three+ colors"
def mark(e):
    r = e["roles"]; m = ""
    if "bomb" in r: m += "★"
    if "removal" in r: m += "✕"
    if "trick" in r: m += "⚡"
    if "fixing" in r: m += "◆"
    return m
def row(e):
    syn = f" (→{e['grade_synergy']} with {e['needs_threshold']}+ {e['needs']})" if "grade_synergy" in e else ""
    return f"| {e['grade']}{syn} | {e['name']} | {e['mana_cost'].split(' // ')[0]} | {e['rarity'][0].upper()} | {mark(e)} | {e['note']} |"
out = ["# Reality Fracture prerelease cheat sheet (DEC-925)", "",
"Grades are Sealed grades, 0 to 10, from oracle text (CEO, 2026-09-23), cross-checked against Draftsim. ★ bomb, ✕ removal, ⚡ trick or instant-speed interaction, ◆ fixing. A grade in parentheses applies when your deck holds the listed number of enablers.", "",
"## 1. Scoring your pool by hand (10 minutes)", "",
"1. Sort the pool by color. Hybrid cards go to whichever of their two colors you are considering; gold cards stay aside.",
"2. For each color, count cards graded 5 or higher. Write the count on the deck box. That is your depth.",
"3. For each color, count ✕ cards. Two colors with at least 3 ✕ between them is the target.",
"4. Take the two deepest colors. Add gold cards for that pair. Count again: you need 22 to 23 spells graded 4 or higher, with 3 or more ✕ and at least one ★ (grade 8 or higher). That is the same viability test the simulation in section 5 uses.",
"5. If a third color holds a card graded 7 or higher, splash it only with 2 or more lands in the pool that make that color: a dual land (common Annex/Commons or rare slowland) or Room of Refuge. Murmuring Volume and the basic landcyclers (Hexhaven Battalion, Undulating Witness, Apex Witchstalker, Awaken the Inferno, Vinelasher Adept) help the splash but do not count toward the 2. Splash at most 2 cards.",
"6. Build: 17 lands (duals count), 23 spells. Curve target: 1-2 one-drops, 7-8 two-drops, 5-6 three-drops, the rest 4+. Play every ✕ you can cast.",
"7. If two pairs tie, prefer the one whose synergy grades turn on (Jace count, graveyard count, lifegain count), then the one with more 2-drops.", "",
"## 2. Format rules that decide games", "",
"- **The Jace token.** Any card that says \"empower Jace N\" creates a blue Jace planeswalker token if you have none and puts N loyalty on it. The token has −1: surveil 1 and −3: draw a card. It can be attacked. Count your Jace sources: 4 or more means the Jace synergy grades apply.",
"- **The 10 common dual lands enter untapped only if you control a planeswalker.** A Jace token counts. Without one they are tapped duals. Play them anyway.",
"- **Prepared creatures** (two-faced cards) enter with a spell you may cast once by paying the spell's cost; three of them (Paradox Shaper, Stingerquill Voxmancer, Woodwork Prodigy) re-prepare every upkeep and are engines.",
"- **Threshold** (7 cards in graveyard) needs mill: Omit Variables, surveil, Something Worth Saving. Without 4+ enablers the threshold cards are their base grade.",
"- **Basic landcycling {2}** on five commons is your splash insurance and your flood insurance.",
"- **3 damage kills most creatures in the set** (limitedmtg count: 68%). Respect No Admittance, Stingerquill Charm, Last Gasp at 2 mana.", "",
"## 3. Removal by color (commons and uncommons you will actually open)", ""]
rem = collections.defaultdict(list)
for e in G:
    if "removal" in e["roles"] and e["rarity"] in ("common", "uncommon") and "Land" not in e["type_line"]:
        rem[bucket(e)].append(e)
for k in ["W", "U", "B", "R", "G"] + sorted(k for k in rem if k not in "WUBRG"):
    if k in rem: out.append(f"- **{k}**: " + "; ".join(f"{e['name']} ({e['mana_cost'].split(' // ')[0]}, {e['grade']})" for e in sorted(rem[k], key=lambda e: -e["grade"])))
out += ["", "## 4. Tricks and instant-speed plays to respect (by open mana)", ""]
tr = collections.defaultdict(list)
for e in G:
    t = e["type_line"]; o = (cards[e["name"]].get("oracle_text") or " ".join(f.get("oracle_text", "") for f in cards[e["name"]].get("card_faces", []))).lower()
    if ("Instant" in t.split(" //")[0] or re.search(r"\bflash\b", o.split("//")[0])) and e["rarity"] in ("common", "uncommon"):
        tr[bucket(e)].append(e)
for k in ["W", "U", "B", "R", "G"] + sorted(k for k in tr if k not in "WUBRG"):
    if k in tr: out.append(f"- **{k}**: " + "; ".join(f"{e['name']} ({e['mana_cost'].split(' // ')[0]})" for e in sorted(tr[k], key=lambda e: len(pips(e["mana_cost"])))))
def sim_rows(path):
    r = json.load(open(path))["runs"]["CEO grades"]; return {p["pair"]: p for p in r["per_pair"]}, r
head, hr = sim_rows("sim_results.json"); spec, _ = sim_rows("sim_results_spec_splash.json"); nos, _ = sim_rows("sim_results_nosplash.json")
order = sorted(head, key=lambda k: -head[k]["p_best"])
pct = lambda x: f"{100*x:.1f}%"
out += ["", "## 5. Archetype ranking (Monte Carlo over the booster collation, DEC-926)", "",
f"{hr['pools']:,} simulated pools of 6 Play Boosters plus a promo, scored with the grades below. P(best) = share of pools where this pair builds the highest-scoring 23. P(viable) = pool holds 23 playables, 3 removal and a bomb for this pair, with at most a 2-card splash gated on 2 lands that make the colour. Any pair is viable in {pct(hr['p_any_viable_pair'])} of pools. Read this as \"what the set makes likely\", not as a pick: mean scores sit within 0.1 of each other, so the pool you open decides.", "",
"| Pair | P(best) | P(viable) | Mean score | Removal in deck | Bombs | P(viable) if splash gate also counts landcyclers | P(viable) with no splash |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
for k in order:
    h = head[k]; out.append(f"| {k} | {pct(h['p_best'])} | {pct(h['p_viable'])} | {h['mean_score']:.2f} | {h['mean_removal']:.1f} | {h['mean_bombs']:.2f} | {pct(spec[k]['p_viable'])} | {pct(nos[k]['p_viable'])} |")
out += ["", "**How to read it at the table.** White pairs top P(viable) because white has the most playables; red and black pairs carry the removal (BR deepest at about 8 per deck); blue pairs are removal-poor (UG and WU under 4.2). A pool that opens 3 or more black or red removal spells is usually a BR/WB/WR deck; a pool with a white bomb and lifegain is WG. Green is the least likely main colour, not a bad one.", ""]
out += ["## 6. Full graded list", ""]
groups = collections.defaultdict(list)
for e in G: groups[bucket(e)].append(e)
keys = ["W", "U", "B", "R", "G"] + sorted(k for k in groups if k.startswith("Gold")) + ["Hybrid (either color)", "Three+ colors", "Colorless", "Lands"]
for k in keys:
    if k not in groups: continue
    out += [f"### {k}", "", "| Grade | Card | Cost | R | Tags | Why |", "|---|---|---|---|---|---|"]
    out += [row(e) for e in sorted(groups[k], key=lambda e: (-e["grade"], e["name"]))]
    out.append("")
open("cheat_sheet.md", "w").write("\n".join(out) + "\n"); print("cheat_sheet.md lines:", len(out))
# sanity on castability helper
E = {e["name"]: e for e in G}
assert castable(E["Blessed Ghoul"], "WU") and castable(E["Blessed Ghoul"], "BR") and not castable(E["Twisted Fates"], "WU") and castable(E["Hallway Heckler // Vicious Verse"], "RG")
print("castability helper ok")
