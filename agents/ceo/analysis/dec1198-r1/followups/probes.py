"""probes.py: recount the CEO's probes P1 and P2 over the mirror, on 607dd65 and on the head.

P1: a Saga line that names two or more chapters ("I, II — ...") and holds a draw.
P2: one draw of one card in the whole text, whose line's cost before ":" spends the card by its
    name ("sacrifice <name>") or exiles it from your graveyard ("exile this card from your graveyard").
"""
import importlib.util
import json
import re


def load(p, n):
    s = importlib.util.spec_from_file_location(n, p)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


old = load("/tmp/dec1198/snap/atr_607dd65.py", "old")
head = load("/tmp/dec1198/snap/atr_699cb7e.py", "head")
cards = json.load(open("/Users/dpires/Documents/Personal/code/mtg-precon-upgrader/priv_data/scryfall-oracle.json"))
CHAPTERS = re.compile(r"^(?:[ivx]+, )+[ivx]+ — ", re.M)

p1, p2 = [], []
for c in cards:
    o, t = head.spell_oracle_and_type(c)
    o = o.lower()
    a, b = old.classify(c)[0], head.classify(c)[0]
    for line in o.split("\n"):
        if CHAPTERS.match(line) and head._DRAW.search(line):
            p1.append((c["name"], a, b, line))
            break
    draws = list(head._DRAW.finditer(o))
    if len(draws) == 1 and re.match(r"draws? (?:a|one) card\b(?! for each)", o[draws[0].start():]):
        s = o.rfind("\n", 0, draws[0].start()) + 1
        line = o[s:draws[0].start()]
        if ":" not in line:
            continue
        cost = line[: line.find(":")]
        names = {c["name"].lower()} | {f["name"].lower() for f in c.get("card_faces") or []}
        names |= {n.split(",")[0] for n in names}
        spend = any(f"sacrifice {n}" in cost or f"exile {n} from your graveyard" in cost for n in names)
        if spend or "exile this card from your graveyard" in cost:
            p2.append((c["name"], a, b, cost))

print(f"P1: {len(p1)} cards hold a line that names two or more chapters with a draw")
print(f"  read card-draw on 607dd65: {sum(x[1] == 'card-draw' for x in p1)}; leave card-draw on the head: "
      f"{sum(x[1] == 'card-draw' and x[2] != 'card-draw' for x in p1)}")
for x in p1:
    print("   ", " | ".join(map(str, x)))
print(f"P2: {len(p2)} cards; read card-draw on the head: {sum(x[2] == 'card-draw' for x in p2)}")
for x in p2:
    print("   ", " | ".join(map(str, x)))
