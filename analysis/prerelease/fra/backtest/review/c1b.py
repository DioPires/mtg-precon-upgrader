import sys; sys.path.insert(0, "/tmp/fra_review")
from common import *
cards17, pub, v1, v2, v3, ds, names = setup()
n=len(names)
y={k:pub[k]["ever_drawn_win_rate"]*100 for k in names}
for rar in ("common","uncommon"):
    ks=[k for k in names if pub[k]['rarity']==rar]
    print(rar, len(ks), "meanGIH %.2f"%(sum(y[k] for k in ks)/len(ks)), "mean v3 %.2f"%(sum(v3[k]['grade'] for k in ks)/len(ks)), "mean ds %.2f"%(sum(ds[k] for k in ks)/len(ks)))
# within-rarity rank-transform then pool: rank within rarity as percentile
def pct_within(vals, groups):
    out=[0]*len(vals)
    for gname in set(groups):
        ix=[i for i,g in enumerate(groups) if g==gname]; rr=ranks([vals[i] for i in ix])
        for i,r in zip(ix,rr): out[i]=(r-0.5)/len(ix)
    return out
grp=[pub[k]['rarity'] for k in names]
Y=[y[k] for k in names]; A=[v3[k]['grade'] for k in names]; Bd=[ds[k] for k in names]
def strat(idx):
    g=[grp[i] for i in idx]
    yy=pct_within([Y[i] for i in idx],g); aa=pct_within([A[i] for i in idx],g); bb=pct_within([Bd[i] for i in idx],g)
    return pearson(aa,yy), pearson(bb,yy)
a,b=strat(list(range(n))); print("rarity-stratified: v3 %.2f ds %.2f diff %.2f"%(a,b,b-a))
print(" boot CI diff", boot_ci(lambda idx: (lambda t: t[1]-t[0])(strat(idx)), n, B=4000))
# colour groups
def col(k):
    c=pub[k]['color']; return c if len(c)==1 else ('gold' if len(c)>1 else 'colorless')
cg=[col(k) for k in names]
import collections; print(collections.Counter(cg))
def stratc(idx, groups):
    g=[groups[i] for i in idx]
    yy=pct_within([Y[i] for i in idx],g); aa=pct_within([A[i] for i in idx],g); bb=pct_within([Bd[i] for i in idx],g)
    return pearson(aa,yy), pearson(bb,yy)
a,b=stratc(list(range(n)), cg); print("colour-stratified: v3 %.2f ds %.2f"%(a,b))
print(" boot CI v3", boot_ci(lambda idx: stratc(idx,cg)[0], n, B=4000), "ds", boot_ci(lambda idx: stratc(idx,cg)[1], n, B=4000))
cr=[c+"/"+r for c,r in zip(cg,grp)]
a,b=stratc(list(range(n)), cr); print("colour x rarity stratified: v3 %.2f ds %.2f"%(a,b))
# mean GIH and grade by colour
for c in sorted(set(cg)):
    ks=[k for k,g in zip(names,cg) if g==c]
    print(c, len(ks), "GIH %.2f v3 %.2f ds %.2f"%(sum(y[k] for k in ks)/len(ks), sum(v3[k]['grade'] for k in ks)/len(ks), sum(ds[k] for k in ks)/len(ks)))
