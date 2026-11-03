"""DEC-1218 R1: read Draftsim's pick-order ratings for one set out of its app bundle into {card name: rating 0-5}.

    python3 -I parse_draftsim_pick.py BUNDLE.js SET CARDS_JSON OUT_JSON

https://draftsim.com/<SET>-pick-order/ is a JavaScript page. Its app bundle holds every set's
ratings as a tab-separated table (Name, Name_2, ..., Rarity, Rating, List, ...), with "_" for
spaces. The bundle may be saved gzip-compressed (the Wayback Machine serves it so).

Bundles (saved, not committed):
  TRK, 3 November 2026: https://draftsim.com/draft-app/dist/assets/index-Ctt7WR6J.js  -> draftsim_pick_ratings.json
  FRA, 25 September 2026 (before the Arena release on 29 September):
    https://web.archive.org/web/20260925141719id_/https://draftsim.com/draft-app/dist/assets/index-DPnGdPQd.js
    -> ../fra/backtest/draftsim_pick_fra_20260925.json
  FRA, 3 November 2026 (same table as 14 October, after Arena data): index-Ctt7WR6J.js
    -> ../fra/backtest/draftsim_pick_fra_20261103.json
Rows of the Stardates sheet (List "sds") are left out; rows that match no card are printed.
"""
import gzip
import json
import re
import sys


def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


bundle, code, cards_path, out_path = sys.argv[1:5]
raw = open(bundle, "rb").read()
if raw[:2] == b"\x1f\x8b":
    raw = gzip.decompress(raw)
s = raw.decode("utf-8", errors="replace")
var = dict(re.findall(r'"\.\./data/([A-Za-z0-9_]+)\.txt":(\w+)', s))[code]
table = re.search(r"[,\s]" + re.escape(var) + r"=`(.*?)`", s, re.S).group(1).replace("\\r", "")
lines = [line for line in table.split("\n") if line.strip()]
head = lines[0].split("\t")

names = {}
for c in json.load(open(cards_path, encoding="utf-8")):
    names[norm(c["name"])] = c["name"]
    if " // " in c["name"]:
        names.setdefault(norm(c["name"].split(" // ")[0]), c["name"])

out, unmatched = {}, []
for line in lines[1:]:
    row = dict(zip(head, line.split("\t")))
    if row.get("List") == "sds":
        continue
    name = names.get(norm(row["Name"].replace("_", " ")))
    if name is None:
        unmatched.append(row["Name"])
    elif row["Rating"]:
        out[name] = float(row["Rating"])
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(dict(sorted(out.items())), f, indent=1, ensure_ascii=False)
    f.write("\n")
print(f"{code}: {len(out)} ratings; unmatched rows: {unmatched}")
