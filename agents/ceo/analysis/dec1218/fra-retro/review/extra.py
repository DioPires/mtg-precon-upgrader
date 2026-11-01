import sys; sys.path.insert(0, "/tmp/fra_review")
from common import *
cards17, pub, v1, v2, v3, ds, names = setup()
allc={norm(c['name']):c for c in cards17}
for lab,src in (("v3",{k:v['grade'] for k,v in v3.items()}),("ds",ds)):
    for scope in ("all graded","published","unpublished"):
        out=[]
        for rar in ("common","uncommon"):
            ks=[k for k in src if k in allc and allc[k]['rarity']==rar and (scope=="all graded" or (scope=="published")==(k in pub))]
            out.append(f"{rar} n={len(ks)} mean={sum(src[k] for k in ks)/len(ks):.2f}")
        print(lab, scope, "; ".join(out))
# published share by rarity
for rar in ("common","uncommon"):
    t=[c for c in cards17 if c['rarity']==rar]; print(rar, "published", sum(1 for c in t if c['ever_drawn_win_rate'] is not None), "of", len(t))
pdc={r['short_name']:r for r in load(R+"/17lands_fra_color_ratings_PremierDraft.json") if not r['is_summary']}
P=[p for p in pdc if len(p)==2]
for c in "WUBRG":
    ps=[p for p in P if c in p]; w=sum(pdc[p]['wins'] for p in ps); g=sum(pdc[p]['games'] for p in ps); print("PD",c,f"{w/g*100:.2f}")
# tie ceiling
import collections
for lab,vals in (("v3",[v3[k]['grade'] for k in names]),("ds",[ds[k] for k in names])):
    n=len(vals); t=collections.Counter(vals).values(); print(lab,"tie ceiling", round(math.sqrt(1-sum(x**3-x for x in t)/(n**3-n)),3))
# Does removal grade gap differ from Draftsim? and Draftsim on removal vs engine raw
