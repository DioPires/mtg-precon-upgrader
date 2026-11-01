import sys; sys.path.insert(0, "/tmp/fra_review")
from common import *
seal={r['short_name']:r for r in load(R+"/17lands_fra_color_ratings_Sealed.json") if not r['is_summary'] and len(r['short_name'])==2}
P=sorted(seal); wr={p:seal[p]['wins']/seal[p]['games'] for p in P}
s={p['pair']:p for p in load("/tmp/fra_review/simout/sim_v3nosyn.json")["runs"]["CEO grades"]["per_pair"]}
r=spearman([s[p]['p_best'] for p in P],[wr[p] for p in P]); print("v3 no synergy P(best) vs WR", round(r,2), "P(best):", ", ".join(f"{p} {s[p]['p_best']*100:.1f}" for p in sorted(P,key=lambda p:-s[p]['p_best'])))
