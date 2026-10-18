"""census.py OLD.py NEW.py [mirror]: print the role changes of classify over the mirror."""
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
cards = json.load(open(sys.argv[3] if len(sys.argv) > 3 else "priv_data/scryfall-oracle.json"))
pairs = collections.Counter()
rows = []
for c in cards:
    a = old.classify(c)[0]
    b = new.classify(c)[0]
    if a != b:
        pairs[(a, b)] += 1
        rows.append((a, b, c["name"]))
print(f"cards {len(cards)} changed {len(rows)}")
for (a, b), n in pairs.most_common():
    print(f"  {a} -> {b}: {n}")
for r in sorted(rows, key=lambda r: (str(r[0]), str(r[1]), r[2])):
    print("   ", " | ".join(map(str, r)))
