"""DEC-987 (2026-10-12): creature casts per turn for anvil-chorus, the basis for the
Flickering Hound flicker-rate figure (one Hound flicker per creature cast).

Model: shuffle the actual 99, draw 7 (second player draws on turn 1 in half the games),
one card a turn plus EXTRA cards a turn from turn 4 (draw-engine sensitivity), one land drop
a turn (MDFC when no land), rocks cast first (Sol Ring, Arcane Signet add mana next turn;
Pearl Medallion and Herald's Horn reduce every creature by 1), Fili once at four mana, then
creatures cheapest-first with all remaining mana. Noncreature spells never compete for mana,
so the figure favours the Hound. Run with: python3 -I agents/ceo/analysis/dec987-cast-rate-mc.py
"""
import json, random

d = json.load(open('data/commanders/anvil-chorus/deck.json'))
mirror = json.load(open('priv_data/scryfall-oracle.json'))
cards = mirror if isinstance(mirror, list) else (mirror.get('cards') or list(mirror.values()))
byname = {c['name']: c for c in cards if c.get('name')}
rocks = {'Sol Ring': 2, 'Arcane Signet': 1, 'Pearl Medallion': 0, "Herald's Horn": 0, "Archaeomancer's Map": 0}

lib = []
for e in d['decklist']:
    n = e['name']
    c = byname.get(n) or byname.get(n.split(' // ')[0])
    front = c['type_line'].split('//')[0]
    if e.get('is_mdfc_land'):
        kind = 'mdfc'
    elif e.get('primary_role') == 'land':
        kind = 'land'
    elif 'Creature' in front:
        kind = 'creature'
    elif n in rocks:
        kind = 'rock'
    else:
        kind = 'other'
    dwarf = 'Dwarf' in front or 'Shapeshifter' in front
    for _ in range(e.get('quantity', 1)):
        lib.append((n, c.get('cmc', 0), kind, dwarf))


def run(extra, N=20000, T=10, seed=7):
    random.seed(seed)
    casts = [0.0] * (T + 1)
    dwarves = [0.0] * (T + 1)
    for g in range(N):
        L = lib[:]
        random.shuffle(L)
        hand, L = L[:7], L[7:]
        lands = rockmana = reducer = 0
        cmd = True
        for t in range(1, T + 1):
            draws = (1 if (t > 1 or g % 2) else 0) + (extra if t >= 4 else 0)
            for _ in range(draws):
                hand.append(L.pop(0))
            li = next((i for i, c in enumerate(hand) if c[2] == 'land'), None)
            if li is None:
                li = next((i for i, c in enumerate(hand) if c[2] == 'mdfc'), None)
            if li is not None:
                hand.pop(li)
                lands += 1
            mana = lands + rockmana
            for c in sorted([c for c in hand if c[2] == 'rock'], key=lambda c: c[1]):
                if c[1] <= mana:
                    mana -= c[1]
                    hand.remove(c)
                    rockmana += rocks[c[0]]
                    if c[0] in ("Pearl Medallion", "Herald's Horn"):
                        reducer += 1
                    if c[0] == "Archaeomancer's Map":
                        lands += 1
            if cmd and mana >= 4:
                mana -= 4
                cmd = False
                casts[t] += 1
                dwarves[t] += 1
            for c in sorted([c for c in hand if c[2] == 'creature'], key=lambda c: c[1]):
                cost = max(1, c[1] - reducer)
                if c[1] > 0 and cost <= mana:
                    mana -= cost
                    hand.remove(c)
                    casts[t] += 1
                    dwarves[t] += c[3]
    return [x / N for x in casts], [x / N for x in dwarves]


if __name__ == '__main__':
    for extra in (0, 1):
        c, dw = run(extra)
        print(f"extra draw from t4 = {extra}: casts t5..t9 =", [f"{c[t]:.2f}" for t in range(5, 10)],
              f"| avg {sum(c[5:10]) / 5:.2f} | Dwarf casts avg {sum(dw[5:10]) / 5:.2f}")
