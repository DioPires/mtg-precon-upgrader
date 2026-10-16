"""census.py OLD.py NEW.py [--list]: compare classify (role and confidence) over the mirror.

Prints the count of cards whose (role, confidence) changes, a table by (old role, new role),
and, with --list, one line per changed card: old | new | name | type | oracle (classify's text).
Run from the review tree's root (it reads priv_data/scryfall-oracle.json).
"""
import collections
import importlib.util
import json
import sys


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


old = load(sys.argv[1], "old")
new = load(sys.argv[2], "new")
cards = json.load(open("priv_data/scryfall-oracle.json"))
pairs = collections.Counter()
rows = []
for c in cards:
    a = old.classify(c)
    b = new.classify(c)
    if a != b:
        pairs[(a[0], b[0])] += 1
        o, t = old.spell_oracle_and_type(c)
        rows.append((a, b, c["name"], t, o.replace("\n", " / ")))
print(f"cards {len(cards)} changed {len(rows)}")
for (a, b), n in sorted(pairs.items(), key=lambda kv: (-kv[1], str(kv[0]))):
    print(f"  {a} -> {b}: {n}")
if "--list" in sys.argv:
    for a, b, n, t, o in sorted(rows, key=lambda r: (str(r[0]), str(r[1]), r[2])):
        print(f"    {a} -> {b} | {n} | {t} | {o}")
