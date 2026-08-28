import json, os, glob, math

ROOT = '/Users/dpires/Documents/Personal/code/mtg-precon-upgrader'
mirror = json.load(open(f'{ROOT}/priv_data/scryfall-oracle.json'))
by_name = {}
for c in mirror:
    by_name[c['name'].lower()] = c
    if ' // ' in c['name']:
        by_name[c['name'].split(' // ')[0].lower()] = c

BRACKET_RANK = {'2': 2.0, '3': 3.0, '3+': 3.33, '4-': 3.67, '4': 4.0, '4+': 4.33, '5': 5.0}

rows = []
missing = set()
for path in sorted(glob.glob(f'{ROOT}/data/commanders/*/deck.json')):
    deck = json.load(open(path))
    did = deck['id']
    status = deck.get('status', 'production')
    total_mv = 0.0
    nonland_n = 0
    land_n = 0
    for entry in deck['decklist']:
        qty = entry.get('quantity', 1)
        card = by_name.get(entry['name'].lower())
        if card is None:
            missing.add((did, entry['name']))
            continue
        front_type = card.get('type_line', '').split(' // ')[0]
        if 'Land' in front_type:
            land_n += qty
            continue
        nonland_n += qty
        total_mv += card.get('cmc', 0.0) * qty
    sim_path = os.path.join(os.path.dirname(path), 'simulation.json')
    met_path = os.path.join(os.path.dirname(path), 'metrics.json')
    first_threat = board = None
    health = win_turn = None
    if os.path.exists(sim_path):
        sim = json.load(open(sim_path))
        sp = sim.get('goldfish', {}).get('speed', {})
        first_threat = sp.get('firstThreat', {}).get('medianTurn')
        board = sp.get('meaningfulBoard', {}).get('medianTurn')
    if os.path.exists(met_path):
        met = json.load(open(met_path))
        health = met.get('global_health_normalized')
        wt = met.get('win_turn')
        win_turn = wt.get('typical') if isinstance(wt, dict) else wt
    rows.append({
        'id': did, 'status': status, 'bracket': deck.get('bracket'),
        'rank': BRACKET_RANK.get(str(deck.get('bracket'))),
        'nonland_n': nonland_n, 'land_n': land_n,
        'total_mv': round(total_mv, 1),
        'avg_mv': round(total_mv / nonland_n, 3) if nonland_n else None,
        'first_threat': first_threat, 'board': board,
        'health': health, 'win_turn': win_turn,
    })

def spearman(xs, ys):
    pairs = [(x, y) for x, y in zip(xs, ys) if x is not None and y is not None]
    if len(pairs) < 3:
        return None, len(pairs)
    def rank(vals):
        srt = sorted(range(len(vals)), key=lambda i: vals[i])
        r = [0.0] * len(vals)
        i = 0
        while i < len(srt):
            j = i
            while j + 1 < len(srt) and vals[srt[j + 1]] == vals[srt[i]]:
                j += 1
            avg = (i + j) / 2 + 1
            for k in range(i, j + 1):
                r[srt[k]] = avg
            i = j + 1
        return r
    xs2, ys2 = zip(*pairs)
    rx, ry = rank(list(xs2)), rank(list(ys2))
    n = len(rx)
    mx, my = sum(rx) / n, sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return (num / den if den else None), n

hdr = f"{'deck':26} {'st':4} {'brk':4} {'NL#':4} {'totMV':7} {'avgMV':6} {'thrT':5} {'brdT':5} {'hlth':6} {'winT':5}"
print(hdr)
for r in sorted(rows, key=lambda r: r['avg_mv'] or 0):
    print(f"{r['id']:26} {r['status'][:4]:4} {str(r['bracket']):4} {r['nonland_n']:4} {r['total_mv']:7} {str(r['avg_mv']):6} {str(r['first_threat']):5} {str(r['board']):5} {str(r['health']):6} {str(r['win_turn']):5}")

print()
avg = [r['avg_mv'] for r in rows]
tot = [r['total_mv'] for r in rows]
for label, ys in [('bracket rank', [r['rank'] for r in rows]),
                  ('health(norm)', [r['health'] for r in rows]),
                  ('win_turn', [r['win_turn'] for r in rows]),
                  ('firstThreat medianT', [r['first_threat'] for r in rows]),
                  ('meaningfulBoard medianT', [r['board'] for r in rows])]:
    rho_a, n = spearman(avg, ys)
    rho_t, _ = spearman(tot, ys)
    fa = f"{rho_a:+.2f}" if rho_a is not None else 'n/a'
    ft = f"{rho_t:+.2f}" if rho_t is not None else 'n/a'
    print(f"Spearman vs {label:24} avgMV: {fa}   totalMV: {ft}   (n={n})")

if missing:
    print('\nMISSING FROM MIRROR:', sorted(missing))
