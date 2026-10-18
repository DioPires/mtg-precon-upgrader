import json, importlib.util, sys
def load(p, n):
    s = importlib.util.spec_from_file_location(n, p); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
mods = [(c, load(f"atr_{c}.py", "m"+c)) for c in sys.argv[1].split(",")]
cards = {c["name"]: c for c in json.load(open("/Users/dpires/Documents/Personal/code/mtg-precon-upgrader/priv_data/scryfall-oracle.json"))}
for n in sys.argv[2:]:
    print(n, [(c, m.classify(cards[n])[0]) for c, m in mods])
