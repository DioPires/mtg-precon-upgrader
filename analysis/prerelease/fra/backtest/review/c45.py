import sys; sys.path.insert(0, "/tmp/fra_review")
from common import *
seal={r['short_name']:r for r in load(R+"/17lands_fra_color_ratings_Sealed.json") if not r['is_summary'] and len(r['short_name'])==2}
pd={r['short_name']:r for r in load(R+"/17lands_fra_color_ratings_PremierDraft.json") if not r['is_summary'] and len(r['short_name'])==2}
P=sorted(seal); wr={p:seal[p]['wins']/seal[p]['games'] for p in P}; se={p:math.sqrt(wr[p]*(1-wr[p])/seal[p]['games']) for p in P}
rng=random.Random(4)
for de in (1.0,1.3):
    top1={p:0 for p in P}; top2={p:0 for p in P}; both=0; B=20000
    for _ in range(B):
        d={p:rng.gauss(wr[p], math.sqrt(de)*se[p]) for p in P}
        o=sorted(P,key=lambda p:-d[p]); top1[o[0]]+=1; top2[o[0]]+=1; top2[o[1]]+=1
        both+= set(o[:2])=={'WU','UB'}
    print(f"de {de}: P(top1)", {p:round(v/B,2) for p,v in sorted(top1.items(),key=lambda kv:-kv[1]) if v/B>0.01}, "P(top2)", {p:round(v/B,2) for p,v in sorted(top2.items(),key=lambda kv:-kv[1]) if v/B>0.05}, "P(WU,UB are top 2)", round(both/B,2))
# pairwise
for a,b in (("WU","BG"),("UB","BG"),("WU","WR"),("WB","RG")):
    d=wr[a]-wr[b]; s=math.sqrt(se[a]**2+se[b]**2); print(f"{a}-{b}: {d*100:+.2f} se {s*100:.2f} z {d/s:.2f}")
# blue vs non-blue (games weighted)
def agg(ps): w=sum(seal[p]['wins'] for p in ps); g=sum(seal[p]['games'] for p in ps); return w/g, math.sqrt((w/g)*(1-w/g)/g)
bl=[p for p in P if 'U' in p]; nb=[p for p in P if 'U' not in p]
a,sa=agg(bl); b,sb=agg(nb); print(f"blue pairs {a*100:.2f} non-blue {b*100:.2f} diff {(a-b)*100:+.2f} ({(a-b-1.96*math.sqrt(sa*sa+sb*sb))*100:+.2f},{(a-b+1.96*math.sqrt(sa*sa+sb*sb))*100:+.2f})")
for c in "WUBRG":
    ps=[p for p in P if c in p]; x,s=agg(ps); print(c, f"{x*100:.2f}±{1.96*s*100:.2f}")
# black/red pairs vs rest (advice: count black and red removal first -> WB, WR, BR)
adv=["WB","WR","BR"]; a,sa=agg(adv); b,sb=agg([p for p in P if p not in adv]); print(f"advised WB/WR/BR {a*100:.2f} vs rest {b*100:.2f} diff {(a-b)*100:+.2f}±{1.96*math.sqrt(sa*sa+sb*sb)*100:.2f}")
# PD vs Sealed
r=spearman([wr[p] for p in P],[pd[p]['wins']/pd[p]['games'] for p in P]); print("Sealed vs PD WR spearman", round(r,2), fisher_ci(r,10))
pdwr={p:pd[p]['wins']/pd[p]['games'] for p in P}
print("PD order:", sorted(P,key=lambda p:-pdwr[p]))
print("Sealed order:", sorted(P,key=lambda p:-wr[p]))
# C5 from grades.json
g=load(D+"/grades.json")
for scope in ("C+U mono","C+U incl gold/hybrid by colour","all rarities mono"):
    out={}
    for c in "WUBRG":
        if scope=="C+U mono": L=[x for x in g if 'removal' in x['roles'] and x['rarity'] in('common','uncommon') and x['colors']==[c]]
        elif scope=="all rarities mono": L=[x for x in g if 'removal' in x['roles'] and x['colors']==[c]]
        else: L=[x for x in g if 'removal' in x['roles'] and x['rarity'] in('common','uncommon') and c in x['colors']]
        out[c]=(len(L), round(sum(x['grade'] for x in L)/len(L),2) if L else None, sorted([x['grade'] for x in L],reverse=True))
    print(scope, out)
print([ (x['name'],x['grade']) for x in g if 'removal' in x['roles'] and x['rarity'] in('common','uncommon') and x['colors']==['W']])
print([ (x['name'],x['grade']) for x in g if 'removal' in x['roles'] and x['rarity'] in('common','uncommon') and x['colors']==['R']])
print([ (x['name'],x['grade']) for x in g if 'removal' in x['roles'] and x['rarity'] in('common','uncommon') and x['colors']==['B']])
