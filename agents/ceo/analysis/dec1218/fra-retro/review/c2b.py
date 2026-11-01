import sys; sys.path.insert(0, "/tmp/fra_review")
from common import *
cards17, pub, v1, v2, v3, ds, names = setup()
pd={r['short_name']:r for r in load(R+"/17lands_fra_color_ratings_PremierDraft.json") if not r['is_summary']}
pairs=[p for p in pd if len(p)==2]
def basewr(c):
    if len(c)==2:
        key=[p for p in pairs if set(p)==set(c)][0]; return pd[key]['wins']/pd[key]['games']*100
    sel=[p for p in pairs if (c in p if len(c)==1 else True)]
    return sum(pd[p]['wins'] for p in sel)/sum(pd[p]['games'] for p in sel)*100
def metric(k, m):
    c=pub[k]
    if m=='GIH': return c['ever_drawn_win_rate']*100
    if m=='GIH-colour baseline': return c['ever_drawn_win_rate']*100 - basewr(c['color']) if len(c['color'])<=2 else None
    if m=='IWD': return c['drawn_improvement_win_rate']*100
    if m=='GP WR': return c['win_rate']*100
    if m=='GD WR': return c['drawn_win_rate']*100 if c['drawn_win_rate'] is not None else None
    if m=='OH WR': return c['opening_hand_win_rate']*100 if c['opening_hand_win_rate'] is not None else None
    if m=='GNS WR': return c['never_drawn_win_rate']*100
    if m=='-ATA': return -c['avg_pick']
    if m=='-ALSA': return -c['avg_seen']
    if m=='play rate': return c['play_rate']
def has(k,role): return role in (v3[k].get('roles') or [])
def col(k):
    c=pub[k]['color']; return c if len(c)==1 else ('M' if len(c)>1 else 'C')
def pct_within(vals, groups):
    out=[0]*len(vals)
    for g in set(groups):
        ix=[i for i,x in enumerate(groups) if x==g]; rr=ranks([vals[i] for i in ix])
        for i,r in zip(ix,rr): out[i]=(r-0.5)/len(ix)*100
    return out
def mean(L): return sum(L)/len(L)
print("metric | n | rho v3 | rho ds | removal gap | (RTM-expected) | engine gap | (expected) | within-colour removal gap | engine")
for m in ['GIH','GIH-colour baseline','IWD','GP WR','GD WR','GNS WR','-ATA','-ALSA']:
    ks=[k for k in names if metric(k,m) is not None]
    y=[metric(k,m) for k in ks]; a=[v3[k]['grade'] for k in ks]; b=[ds[k] for k in ks]
    ra=spearman(a,y); rb=spearman(b,y)
    def pct(v): r=ranks(v); return [(x-1)/(len(v)-1)*100 for x in r]
    py,pa=pct(y),pct(a); r=pearson(pa,py)
    rem=[i for i,k in enumerate(ks) if has(k,'removal')]; eng=[i for i,k in enumerate(ks) if has(k,'engine')]
    gr=mean([py[i]-pa[i] for i in rem]); ge=mean([py[i]-pa[i] for i in eng])
    er=mean([(r-1)*(pa[i]-50) for i in rem]); ee=mean([(r-1)*(pa[i]-50) for i in eng])
    grp=[col(k) for k in ks]; wy=pct_within(y,grp); wa=pct_within(a,grp)
    wr=mean([wy[i]-wa[i] for i in rem]); we=mean([wy[i]-wa[i] for i in eng])
    lo,hi=fisher_ci(ra,len(ks)); lo2,hi2=fisher_ci(rb,len(ks))
    print(f"{m} | {len(ks)} | {ra:+.2f} ({lo:+.2f},{hi:+.2f}) | {rb:+.2f} ({lo2:+.2f},{hi2:+.2f}) | {gr:+.0f} | ({er:+.0f}) | {ge:+.0f} | ({ee:+.0f}) | {wr:+.0f} | {we:+.0f}")
# Raw mean metric for removal vs engine vs rest, with diff CI
print()
for m in ['GIH','GIH-colour baseline','IWD','GP WR','-ATA']:
    ks=[k for k in names if metric(k,m) is not None]
    def grpmean(f): L=[metric(k,m) for k in ks if f(k)]; return mean(L),len(L)
    r_=grpmean(lambda k: has(k,'removal')); e_=grpmean(lambda k: has(k,'engine')); o_=grpmean(lambda k: not has(k,'removal') and not has(k,'engine'))
    # boot diff engine - removal
    rem=[metric(k,m) for k in ks if has(k,'removal')]; eng=[metric(k,m) for k in ks if has(k,'engine')]
    rng=random.Random(5); ds_=[]
    for _ in range(5000):
        ds_.append(mean([rng.choice(eng) for _ in eng])-mean([rng.choice(rem) for _ in rem]))
    ds_.sort()
    print(f"{m}: removal {r_[0]:.2f} (n={r_[1]}), engine {e_[0]:.2f} (n={e_[1]}), other {o_[0]:.2f} (n={o_[1]}); engine-removal {e_[0]-r_[0]:+.2f} boot95 ({ds_[125]:+.2f},{ds_[4874]:+.2f})")
print("colour baselines PD:", {c: round(basewr(c),1) for c in "WUBRG"})
# colour composition of removal & engine tags
import collections
print("removal colours", collections.Counter(col(k) for k in names if has(k,'removal')))
print("engine colours", collections.Counter(col(k) for k in names if has(k,'engine')))
print("removal rarity", collections.Counter(pub[k]['rarity'] for k in names if has(k,'removal')), "engine rarity", collections.Counter(pub[k]['rarity'] for k in names if has(k,'engine')))
