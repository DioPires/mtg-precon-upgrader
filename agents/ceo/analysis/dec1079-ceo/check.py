import json, sys, glob
D = sys.argv[1]; m = json.load(open(sys.argv[2])); h = json.load(open(sys.argv[3]))
req = json.load(open(f"{D}/requests.json"))["requests"]
basics = {"Forest", "Island", "Mountain", "Plains", "Swamp"}
def pick(data, cur, memo):
    best = None
    for c in data:
        if c.get("released_at", "9") > "2026-10-14" or "paper" not in c.get("games", []): continue
        if memo and c.get("set_type") == "memorabilia": continue
        p = (c.get("prices") or {}).get(cur)
        if p is not None and (best is None or float(p) < best): best = float(p)
    return best
pages = {}
for r in req:
    if "search" in r["url"]:
        a = json.load(open(f"{D}/answer-{r['index']:02d}.json"))
        if a.get("data") and not a.get("has_more"):
            pages.setdefault(a["data"][0]["oracle_id"], []).extend(a["data"])
agree = bad = 0; moved = []
for name, e in h.items():
    if name in basics: continue
    for cur in ("usd", "eur"):
        if m.get(name, {}).get(cur) is None and e.get(cur) is not None:
            data = pages.get(e.get("oracle_id")) or [c for v in pages.values() for c in v if c["name"] == name]
            p0, p1 = pick(data, cur, False), pick(data, cur, True)
            if p0 == e[cur]: agree += 1
            else: bad += 1; print("DIFF", name, cur, e[cur], p0)
            if p1 != p0: moved.append((name, cur, p0, p1))
print("head prices that my pick reproduces:", agree, "differ:", bad)
print("moved by the memorabilia rule:", moved)
