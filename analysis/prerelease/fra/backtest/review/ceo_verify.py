import json, math, os, sys
from collections import defaultdict
D = sys.argv[1]
DEC925 = os.path.join(D, "..")
def load(p):
    with open(p) as f: return json.load(f)
def ranks(xs):
    o = sorted(range(len(xs)), key=lambda i: xs[i]); r = [0.0]*len(xs); i = 0
    while i < len(o):
        j = i
        while j+1 < len(o) and xs[o[j+1]] == xs[o[i]]: j += 1
        for k in range(i, j+1): r[o[k]] = (i+j)/2+1
        i = j+1
    return r
def pearson(a, b):
    n=len(a); ma=sum(a)/n; mb=sum(b)/n
    cov=sum((x-ma)*(y-mb) for x,y in zip(a,b)); va=math.sqrt(sum((x-ma)**2 for x in a)); vb=math.sqrt(sum((y-mb)**2 for y in b))
    return cov/(va*vb)
sp = lambda a,b: pearson(ranks(a), ranks(b))
norm = lambda s: s.split(" // ")[0].strip().lower()
gih = {norm(c["name"]): (c["ever_drawn_win_rate"]*100, c["rarity"]) for c in load(os.path.join(D,"17lands_fra_card_ratings_premierdraft.json")) if c["ever_drawn_win_rate"] is not None}
v3 = {norm(g["name"]): g for g in load(os.path.join(DEC925,"grades.json"))}
ds = {norm(k): v for k,v in load(os.path.join(DEC925,"draftsim_grades.json")).items()}
names = sorted(set(gih) & set(v3) & set(ds))
print("matched", len(names))
for rar in ("common","uncommon"):
    nn = [n for n in names if gih[n][1]==rar]
    y=[gih[n][0] for n in nn]
    print(rar, len(nn), "v3 rho %.2f" % sp([v3[n]["grade"] for n in nn], y), "draftsim rho %.2f" % sp([ds[n] for n in nn], y),
          "mean GIH %.1f" % (sum(y)/len(y)), "mean v3 %.2f" % (sum(v3[n]["grade"] for n in nn)/len(nn)), "mean ds %.2f" % (sum(ds[n] for n in nn)/len(nn)))
# grade gap U minus C over all graded cards of the set
fra = {norm(c["name"]): c["rarity"] for c in load(os.path.join(DEC925,"fra_all_cards.json"))}
for label, src in (("v3", {n: v3[n]["grade"] for n in v3}), ("draftsim", ds)):
    by = defaultdict(list)
    for n,g in src.items():
        if n in fra: by[fra[n]].append(g)
    m = {k: sum(v)/len(v) for k,v in by.items()}
    print(label, {k: round(v,2) for k,v in m.items()}, "U-C %.2f" % (m["uncommon"]-m["common"]))
# Sealed colour ratings: share of games by number of colours
cr = load(os.path.join(D,"17lands_fra_color_ratings_Sealed.json"))
print(type(cr), (cr[0].keys() if isinstance(cr,list) else list(cr)[:5]))
