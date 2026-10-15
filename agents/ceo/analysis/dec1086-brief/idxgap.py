import json, sys
sys.path.insert(0, "scripts")
from build_price_index import normalize_name, name_keys
idx = json.load(open("data/spellbook/price-index.json"))
cm = json.load(open("data/card-metadata.json"))
names = list(cm)
missing = [n for n in names if not any(k in idx for k in name_keys(n))]
print("names", len(names), "index keys", len(idx), "no row", len(missing))
withusd = [n for n in missing if cm[n].get("usd") is not None]
witheur = [n for n in missing if cm[n].get("eur") is not None]
print("of those, card-metadata usd", len(withusd), "eur", len(witheur))
print("no usd anywhere:", [n for n in missing if cm[n].get("usd") is None])
print(sorted(missing)[:80])
