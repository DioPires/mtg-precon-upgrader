"""DEC-934 archetype-recipe sweep for broodfire-hatchery (DEC-238 step 1b).

Runs every live sub-recipe query for the deck's archetype tags with the
colour-identity splice, EDHREC order and a 50-card cap, then drops anything
already in the 99 or in candidates.json top-50. Output: JSON in the run scratch
dir plus a stdout summary.
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DECK = "broodfire-hatchery"
CI = "grw"
UA = {"User-Agent": "mtg-precon-upgrader/ceo-dec934 (+https://github.com/DioPires)", "Accept": "application/json"}


def main():
    deck = json.load(open(f"{ROOT}/data/commanders/{DECK}/deck.json"))
    names = {c["name"] for c in deck["decklist"]} | {deck["commander"]}
    cands = json.load(open(f"{ROOT}/data/commanders/{DECK}/candidates.json"))["candidates"]
    top50 = {c["name"] for c in cands if c["name"] not in names}
    top50 = set(list(top50)[:50])
    edh = json.load(open(f"{ROOT}/priv_data/edhrec/{DECK}.json"))["rates"]

    out = {}
    nq = 0
    for arch in deck["archetypes"]:
        rid = {"ramp-big-mana": "ramp-bigmana"}.get(arch, arch)
        rec = json.load(open(f"{ROOT}/data/archetype-recipes/{rid}.json"))
        if rec.get("status") != "live":
            print(f"skip {rid}: status {rec.get('status')}")
            continue
        for sub, spec in rec["sub_recipes"].items():
            if "commander" in sub:
                continue
            hits = {}
            for q in spec["queries"]:
                qq = q if "order:" in q else q + " order:edhrec"
                qq = f"{qq} id<={CI}"
                url = "https://api.scryfall.com/cards/search?" + urllib.parse.urlencode({"q": qq, "unique": "cards"})
                nq += 1
                try:
                    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                        data = json.load(r)
                except Exception as e:  # noqa: BLE001
                    print(f"  ! {rid}/{sub}: {e} :: {qq}", file=sys.stderr)
                    time.sleep(0.2)
                    continue
                for card in data.get("data", [])[:50]:
                    n = card["name"]
                    if n in names or n in top50 or n in hits:
                        continue
                    hits[n] = {
                        "mv": card.get("cmc"),
                        "type": card.get("type_line"),
                        "edhrec_rank": card.get("edhrec_rank"),
                        "deck_rate": edh.get(n),
                        "oracle": (card.get("oracle_text") or " // ".join(f.get("oracle_text", "") for f in card.get("card_faces", [])))[:400],
                    }
                time.sleep(0.12)
            out[f"{rid}/{sub}"] = hits
    scratch = os.environ.get("PAPERCLIP_RUN_SCRATCH_DIR", "/tmp")
    path = os.path.join(scratch, "dec934-recipe-deltas.json")
    json.dump(out, open(path, "w"), indent=1)
    total = sum(len(v) for v in out.values())
    print(f"queries {nq}; sub-recipes {len(out)}; deltas {total}; written {path}")
    for k, v in out.items():
        print(f"\n== {k} ({len(v)})")
        rows = sorted(v.items(), key=lambda kv: (-(kv[1]['deck_rate'] or 0), kv[1]['edhrec_rank'] or 10**9))
        for n, d in rows[:12]:
            print(f"  {n} | mv {d['mv']} | rate {d['deck_rate']} | rank {d['edhrec_rank']} | {d['type']}")


if __name__ == "__main__":
    main()
