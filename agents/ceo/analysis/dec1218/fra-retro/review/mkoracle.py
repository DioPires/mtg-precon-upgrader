import sys, copy; sys.path.insert(0, "/tmp/fra_review")
from common import *
cards17=load(R+"/17lands_fra_card_ratings_premierdraft.json")
pub={norm(c['name']):c['ever_drawn_win_rate']*100 for c in cards17 if c['ever_drawn_win_rate'] is not None}
v3=load(D+"/grades.json")
ks=[g for g in v3 if norm(g['name']) in pub]
mg=sum(g['grade'] for g in ks)/len(ks); sg=math.sqrt(sum((g['grade']-mg)**2 for g in ks)/(len(ks)-1))
my=sum(pub[norm(g['name'])] for g in ks)/len(ks); sy=math.sqrt(sum((pub[norm(g['name'])]-my)**2 for g in ks)/(len(ks)-1))
out=[]
for g in v3:
    h=copy.deepcopy(g)
    k=norm(g['name'])
    if k in pub:
        h['grade']=round(mg+(pub[k]-my)/sy*sg,2)
        for f in ('needs','needs_threshold','grade_synergy'): h.pop(f,None)
    out.append(h)
json.dump(out, open("/tmp/fra_review/simout/grades_oracle_gih.json","w"), indent=1)
print(len(ks), mg, sg, my, sy, min(x['grade'] for x in out if norm(x['name']) in pub), max(x['grade'] for x in out if norm(x['name']) in pub))
