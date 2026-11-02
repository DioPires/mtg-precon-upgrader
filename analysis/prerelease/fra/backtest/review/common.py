import json, math, os, random
REPO = "/Users/dpires/Documents/Personal/code/mtg-precon-upgrader"
R = REPO + "/analysis/prerelease/fra/backtest"
D = REPO + "/analysis/prerelease/fra"
def load(p):
    with open(p) as f: return json.load(f)
def norm(n): return n.split(" // ")[0].strip().lower()
def ranks(xs):
    order = sorted(range(len(xs)), key=lambda i: xs[i]); r = [0.0]*len(xs); i = 0
    while i < len(order):
        j = i
        while j+1 < len(order) and xs[order[j+1]] == xs[order[i]]: j += 1
        for k in range(i, j+1): r[order[k]] = (i+j)/2+1
        i = j+1
    return r
def pearson(a, b):
    n=len(a); ma=sum(a)/n; mb=sum(b)/n
    cov=sum((x-ma)*(y-mb) for x,y in zip(a,b)); va=math.sqrt(sum((x-ma)**2 for x in a)); vb=math.sqrt(sum((y-mb)**2 for y in b))
    return cov/(va*vb) if va>0 and vb>0 else float('nan')
def spearman(a,b): return pearson(ranks(a), ranks(b))
def fisher_ci(r, n, spear=True):
    se = math.sqrt((1 + r*r/2)/(n-3)) if spear else 1/math.sqrt(n-3)  # Bonett-Wright for Spearman
    z = math.atanh(r); return math.tanh(z-1.96*se), math.tanh(z+1.96*se)
def boot_ci(stat, n, B=10000, seed=1):
    rng = random.Random(seed); vals=[]
    for _ in range(B):
        idx=[rng.randrange(n) for _ in range(n)]
        v=stat(idx)
        if v==v: vals.append(v)
    vals.sort(); return vals[int(0.025*len(vals))], vals[int(0.975*len(vals))-1]
def setup():
    cards17 = load(R+"/17lands_fra_card_ratings_premierdraft.json")
    pub = {norm(c["name"]): c for c in cards17 if c["ever_drawn_win_rate"] is not None}
    v1 = {norm(g["name"]): g for g in load(R+"/grades_v1_blind.json")}
    v2 = {norm(g["name"]): g for g in load(R+"/grades_v2.json")}
    v3 = {norm(g["name"]): g for g in load(D+"/grades.json")}
    ds = {norm(k): v for k, v in load(D+"/draftsim_grades.json").items()}
    names = sorted(set(pub) & set(v1) & set(v2) & set(v3) & set(ds))
    return cards17, pub, v1, v2, v3, ds, names
