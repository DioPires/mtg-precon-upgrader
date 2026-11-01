import sys; sys.path.insert(0, "/tmp/fra_review")
from common import *
seal_all={r['short_name']:r for r in load(R+"/17lands_fra_color_ratings_Sealed.json") if not r['is_summary']}
pd_all={r['short_name']:r for r in load(R+"/17lands_fra_color_ratings_PremierDraft.json") if not r['is_summary']}
seal={k:v for k,v in seal_all.items() if len(k)==2}
sim={p['pair']:p for p in load(D+"/sim_results.json")["runs"]["CEO grades"]["per_pair"]}
alt={p['pair']:p for p in load(R+"/sim_draftsim_grades.json")["runs"]["CEO grades"]["per_pair"]}
P=sorted(seal)
wr={p:seal[p]['wins']/seal[p]['games'] for p in P}; se={p:math.sqrt(wr[p]*(1-wr[p])/seal[p]['games']) for p in P}
tot=sum(seal[p]['games'] for p in P); share={p:seal[p]['games']/tot for p in P}
# expected games per Bo1 Sealed run (7 wins or 3 losses)
from functools import lru_cache
def eg(p):
    @lru_cache(None)
    def f(w,l):
        if w==7 or l==3: return 0.0
        return 1+p*f(w+1,l)+(1-p)*f(w,l+1)
    return f(0,0)
deck={p:share[p]/eg(wr[p]) for p in P}; s=sum(deck.values()); deck={p:v/s for p,v in deck.items()}
print("E[games] at 0.554/0.589:", round(eg(0.554),2), round(eg(0.589),2))
# 3-colour allocation: add 1/3 of each 3c deck's games to each sub-pair
three={k:v for k,v in seal_all.items() if len(k)==3}
alloc={p:seal[p]['games'] for p in P}
def pairkey(a,b): return [p for p in P if set(p)==set(a+b)][0]
for k,v in three.items():
    for i in range(3):
        for j in range(i+1,3): alloc[pairkey(k[i],k[j])]+=v['games']/3
s=sum(alloc.values()); share3={p:alloc[p]/s for p in P}
wr3={}
for p in P:
    w=seal[p]['wins']; g=seal[p]['games']
    for k,v in three.items():
        if set(p)<=set(k): w+=v['wins']/3; g+=v['games']/3
    wr3[p]=w/g
deck3={p:share3[p]/eg(wr3[p]) for p in P}; s=sum(deck3.values()); deck3={p:v/s for p,v in deck3.items()}
print("3c share of all Sealed games:", sum(v['games'] for v in three.values())/sum(v['games'] for k,v in seal_all.items()))
targets={"Sealed WR":wr,"Sealed game share":share,"deck share (games/E[games])":deck,"deck share incl 3c/3":deck3}
preds={"P(best)":{p:sim[p]['p_best'] for p in P},"P(top2)":{p:sim[p]['p_top2'] for p in P},"P(viable)":{p:sim[p]['p_viable'] for p in P},"mean score":{p:sim[p]['mean_score'] for p in P},"Draftsim P(best)":{p:alt[p]['p_best'] for p in P},"Draftsim P(viable)":{p:alt[p]['p_viable'] for p in P}}
for tl,t in targets.items():
    for pl,pr in preds.items():
        r=spearman([pr[p] for p in P],[t[p] for p in P]); lo,hi=fisher_ci(r,10)
        bl,bh=boot_ci(lambda idx: spearman([pr[P[i]] for i in idx],[t[P[i]] for i in idx]),10,B=5000)
        print(f"{pl:>18} vs {tl:<28}: {r:+.2f}  FisherBW95 ({lo:+.2f},{hi:+.2f})  boot95 ({bl:+.2f},{bh:+.2f})")
print("\ntable: pair, WR, SE, game share, deck share, deck share incl3c, P(best)")
for p in sorted(P,key=lambda p:-wr[p]): print(p, f"{wr[p]*100:.1f} {se[p]*100:.2f} {share[p]*100:.1f} {deck[p]*100:.1f} {deck3[p]*100:.1f} {sim[p]['p_best']*100:.1f}")
# reliability of pair WR ranking
vals=[wr[p]*100 for p in P]; m=sum(vals)/10; vo=sum((v-m)**2 for v in vals)/9; vn=sum((se[p]*100)**2 for p in P)/10
for de in (1.0,1.3,1.6):
    rel=max(0,1-de*vn/vo); print(f"design effect {de}: obs SD {math.sqrt(vo):.2f}, noise SD {math.sqrt(de*vn):.2f}, reliability {rel:.2f}, ceiling corr {math.sqrt(rel):.2f}")
# test-retest of rank: simulate true WR from shrunk posterior, then two replicates
rng=random.Random(2)
for de in (1.0,1.3):
    tau2=max(1e-9,vo-de*vn); rs=[]; rtrue=[]
    for _ in range(4000):
        true=[]; 
        for p in P:
            s2=de*(se[p]*100)**2; w=tau2/(tau2+s2); mu=m+w*(wr[p]*100-m); sd=math.sqrt(w*s2)
            true.append(rng.gauss(mu,sd))
        rep=[t+rng.gauss(0,math.sqrt(de)*se[p]*100) for t,p in zip(true,P)]
        rtrue.append(spearman(true,rep))
    rtrue.sort(); print(f"de {de}: Spearman(observed-like replicate, true order) median {rtrue[2000]:.2f}, 90% ({rtrue[200]:.2f},{rtrue[3800]:.2f})")
# Power: if P(best) had true Spearman rho with TRUE WR, distribution of observed Spearman with noisy WR
def power(rho, de=1.0, B=4000):
    tau=math.sqrt(max(1e-9,vo-de*vn)); out=[]
    for _ in range(B):
        x=[rng.gauss(0,1) for _ in P]; t=[rho*xi+math.sqrt(1-rho*rho)*rng.gauss(0,1) for xi in x]
        y=[tau*ti+rng.gauss(0,math.sqrt(de)*se[p]*100) for ti,p in zip(t,P)]
        out.append(spearman(x,y))
    return sum(1 for o in out if o<=-0.09)/B, sum(1 for o in out if o>=0.56)/B
for rho in (0.0,0.3,0.5,0.7):
    a,b=power(rho); print(f"true rho={rho}: P(obs <= -0.09)={a:.2f}; P(obs >= 0.56, i.e. one-sided p<.05 at n=10)={b:.2f}")
