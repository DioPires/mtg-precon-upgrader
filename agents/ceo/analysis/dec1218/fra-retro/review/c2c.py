import sys, re; sys.path.insert(0, "/tmp/fra_review")
from common import *
cards17, pub, v1, v2, v3, ds, names = setup()
sc={norm(c['name']):c for c in load(D+"/fra_all_cards.json")}
def oracle(k):
    c=sc[k]; t=c.get('oracle_text','')
    if 'card_faces' in c: t=" // ".join(f.get('oracle_text','') for f in c['card_faces'])
    return t
def tl(k): return sc[k].get('type_line','')
n=len(names); Y=[pub[k]["ever_drawn_win_rate"]*100 for k in names]; IWD=[pub[k]["drawn_improvement_win_rate"]*100 for k in names]
A=[v3[k]['grade'] for k in names]; Bd=[ds[k] for k in names]
REM=re.compile(r"(destroy target (creature|nonland permanent)|exile target (creature|nonland permanent)|deals? \d+ damage to (target creature|any target|target creature or planeswalker)|gets -\d+/-\d+|fights? |sacrifices a creature|loses all abilities|base power and toughness 0/0|-1/-1 counters on|puts? it on (the )?(top|bottom)|destroy target creature with)", re.I)
CA=re.compile(r"(draw (two|three|a) cards?|return target .{0,60}card from your graveyard|put .{0,40}into your hand|flashback)", re.I)
tags={}
tags['v3 removal']=[ 'removal' in v3[k]['roles'] for k in names]
tags['v3 removal, non-creature only']=[ 'removal' in v3[k]['roles'] and 'Creature' not in tl(k).split('//')[0] for k in names]
tags['oracle removal (broad)']=[bool(REM.search(oracle(k))) for k in names]
tags['v3 engine']=[ 'engine' in v3[k]['roles'] for k in names]
nonCA={'medic\'s kitesail','heartwood crafter','stingerquill voxmancer','saheeli, jewel of avishkar','way of the wildspeaker','way of the paradox'}
tags['v3 engine minus non-card-advantage']=[ 'engine' in v3[k]['roles'] and k not in nonCA for k in names]
tags['oracle card advantage']=[bool(CA.search(oracle(k))) and 'removal' not in v3[k]['roles'] for k in names]
tags['v3 engine minus Fblthp']=[ 'engine' in v3[k]['roles'] and k!='fblthp, impossibly lost' for k in names]
def pct(v): r=ranks(v); return [(x-1)/(len(v)-1)*100 for x in r]
py,pa=pct(Y),pct(A); r=pearson(pa,py)
def mean(L): return sum(L)/len(L)
def ols(X,y):
    p=len(X[0]); M=[[sum(X[r][i]*X[r][j] for r in range(len(X))) for j in range(p)]+[sum(X[r][i]*y[r] for r in range(len(X)))] for i in range(p)]
    for c in range(p):
        piv=max(range(c,p), key=lambda q: abs(M[q][c])); M[c],M[piv]=M[piv],M[c]
        if abs(M[c][c])<1e-12: return None
        for q in range(p):
            if q!=c:
                f=M[q][c]/M[c][c]
                for j in range(c,p+1): M[q][j]-=f*M[c][j]
    return [M[i][p]/M[i][i] for i in range(p)]
print("tag | n | gap | RTM-exp | excess | coef at equal v3 grade +rarity (GIH pts) boot95 | same on IWD")
for lab,t in tags.items():
    ix=[i for i in range(n) if t[i]]
    gap=mean([py[i]-pa[i] for i in ix]); exp=mean([(r-1)*(pa[i]-50) for i in ix])
    def fit(idx, yv):
        X=[[1.0,A[i],1.0 if t[i] else 0.0,1.0 if pub[names[i]]['rarity']=='uncommon' else 0.0] for i in idx]; return ols(X,[yv[i] for i in idx])
    out=[]
    for yv in (Y,IWD):
        b=fit(range(n),yv)[2]; rng=random.Random(11); bs=[]
        for _ in range(3000):
            idx=[rng.randrange(n) for _ in range(n)]; f=fit(idx,yv)
            if f: bs.append(f[2])
        bs.sort(); out.append(f"{b:+.2f} ({bs[75]:+.2f},{bs[2924]:+.2f})")
    print(f"{lab} | {len(ix)} | {gap:+.0f} | {exp:+.0f} | {gap-exp:+.0f} | {out[0]} | {out[1]}")
# engine - removal contrast at equal grade
def fit2(idx, yv, rt, et, ctrl=True):
    X=[[1.0,A[i],1.0 if rt[i] else 0.0,1.0 if et[i] else 0.0]+([1.0 if pub[names[i]]['rarity']=='uncommon' else 0.0] if ctrl else []) for i in idx]; return ols(X,[yv[i] for i in idx])
for rl,el in (('v3 removal','v3 engine'),('oracle removal (broad)','oracle card advantage'),('v3 removal, non-creature only','v3 engine minus non-card-advantage')):
    for yl,yv in (('GIH',Y),('IWD',IWD)):
        b=fit2(range(n),yv,tags[rl],tags[el]); d=b[3]-b[2]; rng=random.Random(12); bs=[]
        for _ in range(3000):
            idx=[rng.randrange(n) for _ in range(n)]; f=fit2(idx,yv,tags[rl],tags[el])
            if f: bs.append(f[3]-f[2])
        bs.sort(); print(f"engine-removal at equal grade+rarity [{rl} / {el}] {yl}: {d:+.2f} ({bs[75]:+.2f},{bs[2924]:+.2f})")
print("oracle-removal not tagged by v3:", [v3[names[i]]['name'] for i in range(n) if tags['oracle removal (broad)'][i] and not tags['v3 removal'][i]])
print("v3 removal not matched by oracle:", [v3[names[i]]['name'] for i in range(n) if tags['v3 removal'][i] and not tags['oracle removal (broad)'][i]])
print("oracle CA:", [v3[names[i]]['name'] for i in range(n) if tags['oracle card advantage'][i]])
print("mean v3 grade removal %.2f engine %.2f; ds removal %.2f engine %.2f"%(mean([A[i] for i in range(n) if tags['v3 removal'][i]]),mean([A[i] for i in range(n) if tags['v3 engine'][i]]),mean([Bd[i] for i in range(n) if tags['v3 removal'][i]]),mean([Bd[i] for i in range(n) if tags['v3 engine'][i]])))
