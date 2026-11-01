import sys; sys.path.insert(0, "/tmp/fra_review")
from common import *
from functools import lru_cache
seal={r['short_name']:r for r in load(R+"/17lands_fra_color_ratings_Sealed.json") if not r['is_summary'] and len(r['short_name'])==2}
P=sorted(seal); wr={p:seal[p]['wins']/seal[p]['games'] for p in P}; tot=sum(seal[p]['games'] for p in P); share={p:seal[p]['games']/tot for p in P}
def eg(p):
    @lru_cache(None)
    def f(w,l):
        if w==7 or l==3: return 0.0
        return 1+p*f(w+1,l)+(1-p)*f(w,l+1)
    return f(0,0)
deck={p:share[p]/eg(wr[p]) for p in P}
orig={p['pair']:p for p in load(D+"/sim_results.json")["runs"]["CEO grades"]["per_pair"]}
for lab,f in (("v3 rerun","/tmp/fra_review/simout/sim_v3100k.json"),("GIH-oracle C/U","/tmp/fra_review/simout/sim_oracle100k.json")):
    s={p['pair']:p for p in load(f)["runs"]["CEO grades"]["per_pair"]}
    if lab=="v3 rerun": print("v3 rerun matches original P(best):", all(abs(s[p]['p_best']-orig[p]['p_best'])<1e-12 for p in P))
    for m in ("p_best","p_viable","mean_score"):
        out=[]
        for tl,t in (("WR",wr),("deck share",deck)):
            r=spearman([s[p][m] for p in P],[t[p] for p in P]); lo,hi=fisher_ci(r,10); out.append(f"{tl} {r:+.2f} ({lo:+.2f},{hi:+.2f})")
        print(f"{lab} {m}: "+"; ".join(out))
    print("  P(best):", ", ".join(f"{p} {s[p]['p_best']*100:.1f}" for p in sorted(P,key=lambda p:-s[p]['p_best'])))
