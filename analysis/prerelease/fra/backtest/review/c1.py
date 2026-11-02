import sys; sys.path.insert(0, "/tmp/fra_review")
from common import *
cards17, pub, v1, v2, v3, ds, names = setup()
n=len(names); print("n", n)
y=[pub[k]["ever_drawn_win_rate"]*100 for k in names]
G={"v1":[v1[k]["grade"] for k in names],"v2":[v2[k]["grade"] for k in names],"v3":[v3[k]["grade"] for k in names],"ds":[ds[k] for k in names]}
for lab,g in G.items():
    r=spearman(g,y); lo,hi=fisher_ci(r,n)
    blo,bhi=boot_ci(lambda idx: spearman([g[i] for i in idx],[y[i] for i in idx]), n)
    print(f"{lab}: rho={r:.3f} FisherBW95=({lo:.2f},{hi:.2f}) boot95=({blo:.2f},{bhi:.2f})")
d=lambda idx: spearman([G['ds'][i] for i in idx],[y[i] for i in idx]) - spearman([G['v3'][i] for i in idx],[y[i] for i in idx])
lo,hi=boot_ci(d,n); print(f"diff ds-v3={d(list(range(n))):.3f} boot95=({lo:.2f},{hi:.2f})")
B=10000; rng=random.Random(7); cnt=0; vals=[]
for _ in range(B):
    idx=[rng.randrange(n) for _ in range(n)]; v=d(idx); vals.append(v); cnt+= v<=0
print("boot P(diff<=0)", cnt/B)
# v3 on all 113 published (incl lands)
n113=sorted(set(pub)&set(v3)); print("v3 on", len(n113), spearman([v3[k]['grade'] for k in n113],[pub[k]['ever_drawn_win_rate'] for k in n113]))
lands=[k for k in n113 if k not in ds]; print("lands v3 grades", [(k,v3[k]['grade'],round(pub[k]['ever_drawn_win_rate']*100,1)) for k in lands])
# rarity split
for rar in ("common","uncommon"):
    ix=[i for i,k in enumerate(names) if pub[k]['rarity']==rar]
    for lab in ("v3","ds"):
        r=spearman([G[lab][i] for i in ix],[y[i] for i in ix]); lo,hi=fisher_ci(r,len(ix))
        print(f"  {rar} n={len(ix)} {lab} rho={r:.2f} ({lo:.2f},{hi:.2f})")
# noise ceiling with binomial; also split-half style simulated: simulate true = observed shrunk
obs=[(pub[k]['ever_drawn_win_rate']*100, pub[k]['ever_drawn_game_count']) for k in names]
m=sum(o[0] for o in obs)/n; vo=sum((o[0]-m)**2 for o in obs)/(n-1); vn=sum(o[0]*(100-o[0])/o[1] for o in obs)/n
print("ceiling", math.sqrt(1-vn/vo), "sd obs", math.sqrt(vo), "noise", math.sqrt(vn))
# ceiling with design effect 1.3 (games clustered within decks)
for de in (1.2,1.5):
    print(" ceiling with design effect",de, math.sqrt(max(0,1-de*vn/vo)))
# ties
import collections
print("v3 grade dist on 103", sorted(collections.Counter(G['v3']).items()), "ds", sorted(collections.Counter(G['ds']).items()))
