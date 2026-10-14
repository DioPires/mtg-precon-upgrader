import json, sys, urllib.parse, collections
D = sys.argv[1]
req = json.load(open(f"{D}/requests.json"))["requests"]
asof = "2026-10-14"
rows = []
for r in req:
    if "search" not in r["url"]:
        continue
    q = urllib.parse.parse_qs(urllib.parse.urlparse(r["url"]).query)
    a = json.load(open(f"{D}/answer-{r['index']:02d}.json"))
    data = a.get("data", [])
    rows.append((r["index"], q.get("q"), q.get("order"), q.get("dir"), a.get("has_more"), a.get("total_cards"), data))
st = collections.Counter(); bc = collections.Counter(); ov = collections.Counter()
def pick(data, cur, excl):
    best = None
    for c in data:
        if c.get("released_at", "9") > asof or "paper" not in c.get("games", []):
            continue
        if excl(c):
            continue
        p = (c.get("prices") or {}).get(cur)
        if p is None:
            continue
        if best is None or float(p) < float(best[0]):
            best = (p, c)
    return best
rules = {
  "head": lambda c: False,
  "-gold": lambda c: c.get("border_color") == "gold",
  "-memorabilia": lambda c: c.get("set_type") == "memorabilia",
  "-gold-oversized-memorabilia": lambda c: c.get("border_color") == "gold" or c.get("oversized") or c.get("set_type") == "memorabilia",
}
diffs = collections.defaultdict(list)
for idx, q, o, d, hm, tot, data in rows:
    name = data[0]["name"] if data else "?"
    for cur in ("usd", "eur"):
        res = {k: pick(data, cur, f) for k, f in rules.items()}
        h = res["head"]
        if h:
            c = h[1]
            st[c.get("set_type")] += 1; bc[c.get("border_color")] += 1; ov[bool(c.get("oversized"))] += 1
            print(f"{idx:02d} {name[:28]:28} {cur} {h[0]:>7} {c['set']:6} {c.get('set_type'):12} {c.get('border_color'):10} ov={c.get('oversized')} hm={hm} tot={tot}")
        for k, v in res.items():
            if k != "head" and (v and v[0]) != (h and h[0]):
                diffs[k].append((name, cur, h and h[0], h and h[1]["set"], v and v[0], v and v[1]["set"]))
print("set_type", dict(st)); print("border", dict(bc)); print("oversized", dict(ov))
for k, v in diffs.items():
    print(k, len(v))
    for x in v: print("   ", x)
