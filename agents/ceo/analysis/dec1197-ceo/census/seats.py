import json, subprocess, collections, sys
R = "/Users/dpires/Documents/Personal/code/mtg-precon-upgrader"
A, B = sys.argv[1], sys.argv[2]
files = subprocess.run(["git","-C",R,"ls-tree","--name-only","-r",B,"data/commanders"],capture_output=True,text=True).stdout.split()
files = [f for f in files if f.endswith("/candidates.json")]
def load(c, f):
    return {x["name"]: x for x in json.loads(subprocess.run(["git","-C",R,"show",f"{c}:{f}"],capture_output=True,text=True).stdout)["candidates"]}
pairs = collections.Counter(); joins = leaves = scorenorole = 0; seats = []; bad = 0
for f in files:
    d = f.split("/")[2]; a, b = load(A, f), load(B, f)
    joins += len(b.keys() - a.keys()); leaves += len(a.keys() - b.keys())
    for n in a.keys() & b.keys():
        if a[n].get("deck_role") != b[n].get("deck_role"): pairs[(a[n].get("deck_role"), b[n].get("deck_role"))] += 1
        elif a[n]["score"] != b[n]["score"]: scorenorole += 1
    sa = {n for n, x in a.items() if x.get("seeded_for_gap")}; sb = {n for n, x in b.items() if x.get("seeded_for_gap")}
    for n in sb:
        if b[n]["seeded_for_gap"] != b[n].get("deck_role"): bad += 1
    for n in sorted(sb - sa): seats.append((d, "joins", n, b[n]["seeded_for_gap"]))
    for n in sorted(sa - sb): seats.append((d, "leaves", n, a[n]["seeded_for_gap"], (b.get(n) or {}).get("deck_role")))
print(len(files), "files; role pairs", dict(pairs), "sum", sum(pairs.values()), "joins", joins, "leaves", leaves, "score-without-role", scorenorole, "seat!=role", bad)
for s in seats: print(*s)
