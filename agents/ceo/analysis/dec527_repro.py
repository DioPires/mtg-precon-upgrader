#!/usr/bin/env python3
"""DEC-527 near-miss parity audit — faithful headless port of paste-mode matchDecklist.

Mirrors web/src/lib/spellbookMatch.ts (parseDecklist + matchDecklist) exactly,
reading the committed data/spellbook/matcher-index.json. Emits our near-miss set
(and included set) by combo id to a JSON for diffing against the live API.
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
INDEX = ROOT / "data" / "spellbook" / "matcher-index.json"

NEAR_MISS_POPULARITY_FLOOR = 1
NEAR_MISS_LIMIT = 120

_PUNCT_RE = re.compile(r"[^a-z0-9 ]+")
_WS_RE = re.compile(r"\s+")


def normalize_name(name: str) -> str:
    if not name:
        return ""
    decomposed = unicodedata.normalize("NFKD", name)
    ascii_only = "".join(c for c in decomposed if not unicodedata.combining(c))
    lowered = ascii_only.lower()
    stripped = _PUNCT_RE.sub(" ", lowered)
    return _WS_RE.sub(" ", stripped).strip()


def name_keys(name: str):
    keys = set()
    full = normalize_name(name)
    if full:
        keys.add(full)
    if "//" in name:
        front = normalize_name(name.split("//", 1)[0])
        if front:
            keys.add(front)
    return keys


CMDR_TAG = re.compile(r"\*?cmdr\*?|\[commander\]|\(commander\)", re.I)
QTY = re.compile(r"^(\d+)\s*[xX]?\s+")
SETSUFFIX = re.compile(r"\s+\([0-9A-Za-z]{2,6}\)(\s+[0-9A-Za-z-]+)?\s*(\*[^*]+\*)?\s*$")
ANGLE = re.compile(r"\s+<[^>]*>\s*$")
SECTION = re.compile(r"^(commander|deck|maybeboard|sideboard|companion)\s*:?\s*$", re.I)
SB = re.compile(r"^sb:", re.I)


def parse_decklist(text: str):
    card_names, commander_names, unresolved = [], [], []
    for raw in text.split("\n"):
        original = raw.strip()
        line = original
        if not line or line.startswith("#") or line.startswith("//"):
            continue
        if SECTION.match(line):
            continue
        if SB.match(line):
            continue
        is_commander = False
        if CMDR_TAG.search(line):
            is_commander = True
            line = CMDR_TAG.sub("", line).strip()
        line = QTY.sub("", line)
        line = SETSUFFIX.sub("", line).strip()
        line = ANGLE.sub("", line).strip()
        if not line or not re.search(r"[a-zA-Z]", line):
            unresolved.append(original)
            continue
        (commander_names if is_commander else card_names).append(line)
    return card_names, commander_names, unresolved


def match_decklist(card_names, commander_names, index):
    cards = index["cards"]
    templates = index["templates"]
    all_keys, commander_keys = set(), set()
    for n in card_names:
        all_keys |= name_keys(n)
    for n in commander_names:
        commander_keys |= name_keys(n)
    all_keys |= commander_keys

    included, near = [], []
    for v in index["variants"]:
        missing_cards = []
        present = 0
        for cid in v["u"]:
            name = cards.get(str(cid), {}).get("n", "")
            keys = name_keys(name)
            target = commander_keys if cid in v["c"] else all_keys
            if keys & target:
                present += 1
            else:
                missing_cards.append(name)
        unmet = len(missing_cards) + len(v["r"])
        if unmet == 0:
            included.append({"id": v["id"], "pop": v["pop"]})
            continue
        if unmet < 1 or unmet > 2:
            continue
        if present < 1 or present < unmet:
            continue
        if v["pop"] < NEAR_MISS_POPULARITY_FLOOR:
            continue
        near.append({
            "id": v["id"],
            "pop": v["pop"],
            "distance": unmet,
            "present": present,
            "missing_cards": missing_cards,
            "missing_templates": [templates.get(str(t), {}).get("n", "") for t in v["r"]],
            "num_cards": len(v["u"]),
            "num_templates": len(v["r"]),
        })
    near.sort(key=lambda d: (d["distance"], -d["pop"], d["id"]))
    return included, near


def main():
    text = (Path(sys.argv[1])).read_text()
    index = json.loads(INDEX.read_text())
    card_names, commander_names, unresolved = parse_decklist(text)
    included, near = match_decklist(card_names, commander_names, index)
    print(f"corpusVersion: {index['meta'].get('corpusVersion')}", file=sys.stderr)
    print(f"parsed cards={len(card_names)} commanders={len(commander_names)} unresolved={len(unresolved)}", file=sys.stderr)
    print(f"included={len(included)} near_total={len(near)} near_shown(cap {NEAR_MISS_LIMIT})={min(len(near), NEAR_MISS_LIMIT)}", file=sys.stderr)
    out = {
        "corpusVersion": index["meta"].get("corpusVersion"),
        "counts": {"included": len(included), "nearTotal": len(near)},
        "included": sorted(str(x["id"]) for x in included),
        "near": {str(x["id"]): x for x in near},
    }
    Path(sys.argv[2]).write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
