# DEC-1127 review: apply the brief's 10 title changes to main's three deck.json
# files and compare with the PR head's files, key order included.
# Usage: python3 -I check_titles.py <dir with <deck>.main.json and <deck>.head.json>
import json, copy, sys, os
D = sys.argv[1]
def load(p): return json.load(open(os.path.join(D, p), encoding='utf-8'))
exp_titles = {
 ('slivers','winConditions'): {0:'Go-wide commander damage',1:'Infinite damage combo',2:'Poison / toxic kill',3:'Incremental drain'},
 ('stampede-acres','winConditions'): {0:'Go-wide overrun',1:'Infinite tokens — Scurry Oak line',2:'Halo Fountain alternate win'},
 ('witherbloom-the-balancer','synergies'): {10:'Affinity + Delve stack on Afterlife from the Loam',13:'Stacked Death Drains — Up to Five per Death',14:"Ashnod's Altar — Token Mana into the X Drains"},
}
for (d, field), m in exp_titles.items():
    a = load(f'{d}.main.json'); b = load(f'{d}.head.json')
    exp = copy.deepcopy(a)
    for i, t in m.items():
        it = exp[field][i]
        if 'name' in it:
            assert it['name'] == t, (d, i, it['name'])
            new = {('title' if k == 'name' else k): v for k, v in it.items()}
        else:
            assert 'title' not in it
            new = {'title': t, **it}
        exp[field][i] = new
    ok = json.dumps(exp, ensure_ascii=False) == json.dumps(b, ensure_ascii=False)
    print(d, 'EQUAL incl. key order' if ok else 'DIFFERENT')
