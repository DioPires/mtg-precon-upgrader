import sys, re; sys.path.insert(0, "/tmp/fra_review")
from common import *
cards17, pub, v1, v2, v3, ds, names = setup()
sc={norm(c['name']):c for c in load(D+"/fra_all_cards.json")}
def oracle(k):
    c=sc.get(k); 
    if not c: return "?"
    if 'card_faces' in c and not c.get('oracle_text'): return " // ".join(f.get('oracle_text','') for f in c['card_faces'])
    t=c.get('oracle_text','')
    if 'card_faces' in c: t=" // ".join(f.get('oracle_text','') for f in c['card_faces'])
    return t
for role in ("removal","engine"):
    print("=====",role)
    for k in names:
        if role in v3[k]['roles']:
            print(f"- {v3[k]['name']} [{pub[k]['rarity'][0]} {pub[k]['color']}] v3={v3[k]['grade']} ds={ds[k]} GIH={pub[k]['ever_drawn_win_rate']*100:.1f} IWD={pub[k]['drawn_improvement_win_rate']*100:.1f} roles={v3[k]['roles']} | {v3[k]['note'][:90]} || {oracle(k)[:230]!r}")
