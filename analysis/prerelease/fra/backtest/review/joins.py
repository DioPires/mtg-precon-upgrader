import json,sys,collections
R=sys.argv[1]; D=sys.argv[2]
def norm(n): return n.split(" // ")[0].strip().lower()
c=json.load(open(R+"/17lands_fra_card_ratings_premierdraft.json"))
pub=[x for x in c if x['ever_drawn_win_rate'] is not None]
srcs={"v1":{norm(g['name']):g for g in json.load(open(R+"/grades_v1_blind.json"))},
"v2":{norm(g['name']):g for g in json.load(open(R+"/grades_v2.json"))},
"v3":{norm(g['name']):g for g in json.load(open(D+"/grades.json"))},
"ds":{norm(k):v for k,v in json.load(open(D+"/draftsim_grades.json")).items()}}
for x in pub:
    n=norm(x['name'])
    miss=[k for k,s in srcs.items() if n not in s]
    if miss: print("DROP",x['name'],x['rarity'],x['color'],x['ever_drawn_game_count'],round(x['ever_drawn_win_rate']*100,1),"missing in",miss)
# names with // in 17lands
print("17L DFC names:",[x['name'] for x in c if '//' in x['name']][:20])
print("v3 DFC names:",[g for g in srcs['v3'] if False])
v3raw=json.load(open(D+"/grades.json"))
print("v3 names with //:",[g['name'] for g in v3raw if '//' in g['name']])
# duplicates after norm
for k,s in [("17L",[norm(x['name']) for x in c]),("v3",[norm(g['name']) for g in v3raw])]:
    cc=collections.Counter(s); print(k,"dups",[n for n,v in cc.items() if v>1])
# names in 17L not in v3 at all (any rarity)
v3n=set(srcs['v3']); print("17L not in v3:",[x['name'] for x in c if norm(x['name']) not in v3n])
l17=set(norm(x['name']) for x in c); print("v3 not in 17L:",[g['name'] for g in v3raw if norm(g['name']) not in l17])
dsraw=json.load(open(D+"/draftsim_grades.json")); print("ds not in 17L:",[k for k in dsraw if norm(k) not in l17])
# fuzzy check punctuation
import re
def n2(s): return re.sub(r"[^a-z0-9]","",norm(s))
print("17L not in ds (punct-insensitive):",[x['name'] for x in pub if n2(x['name']) not in set(n2(k) for k in dsraw)])
