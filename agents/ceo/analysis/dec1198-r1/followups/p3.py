"""p3.py LIST.txt: among the cards of a 'old | new | name' list that leave card-draw, count those
whose one draw can come more than once through a recast or a re-entry keyword (probe P3).

Prints the count by keyword, with every name.
"""
import collections
import importlib.util
import json
import re
import sys

ATR = "/tmp/dec1198/snap/atr_699cb7e.py"
MIRROR = "/Users/dpires/Documents/Personal/code/mtg-precon-upgrader/priv_data/scryfall-oracle.json"
spec = importlib.util.spec_from_file_location("atr_h", ATR)
atr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(atr)

KEYS = {
    # cast again from the graveyard or from exile
    "flashback": r"\bflashback\b",
    "jump-start": r"\bjump-start\b",
    "retrace": r"\bretrace\b",
    "escape": r"\bescape\b(?! —)",
    "harmonize": r"\bharmonize\b",
    "rebound": r"\brebound\b",
    "buyback": r"\bbuyback\b",
    "cipher": r"\bcipher\b",
    "replicate/storm/copy": r"\breplicate\b|\bstorm\b|\bcopy this spell\b|\bconspire\b|\bcasualty\b",
    "cast from graveyard": r"you may cast this card from your graveyard|cast this card from your graveyard",
    "return to hand from graveyard": r"return this card from your graveyard to your hand",
    # the draw's permanent enters again, or a copy of it enters
    "embalm/eternalize": r"\bembalm\b|\beternalize\b",
    "encore/unearth": r"\bencore\b|\bunearth\b",
    "persist/undying": r"\bpersist\b|\bundying\b",
    "dash/ninjutsu": r"\bdash\b|\bninjutsu\b",
    "offspring/squad/myriad": r"\boffspring\b|\bsquad\b|\bmyriad\b",
    # more than one Clue or other token
    "two or more tokens": r"investigate twice|investigate (?:two|three|x) times|create (?:two|three|x|\d+) clue|"
    r"create (?:two|three|x|\d+) [a-z ]*?tokens?\b[^.]*?draw a card",
}

cards = {c["name"]: c for c in json.load(open(MIRROR))}
rows = [line.rstrip("\n").split(" | ") for line in open(sys.argv[1]) if " | " in line]
hits = collections.defaultdict(list)
n = 0
for old, new, name in rows:
    if old != "card-draw":
        continue
    n += 1
    o, _ = atr.spell_oracle_and_type(cards[name])
    o = o.lower()
    for k, pat in KEYS.items():
        if re.search(pat, o):
            hits[k].append(name)
names = sorted({x for v in hits.values() for x in v})
print(f"cards that leave card-draw: {n}; with a recast or re-entry keyword: {len(names)}")
for k in KEYS:
    if hits[k]:
        print(f"  {k}: {len(hits[k])}: {', '.join(sorted(hits[k]))}")
