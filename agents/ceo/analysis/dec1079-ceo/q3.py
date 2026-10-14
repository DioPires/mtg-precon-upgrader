"""DEC-1079 Q3: read the order of every saved search page of runs 1 and 2.

Model: the sort key of a card is its non-foil price, else its foil price,
else its etched price (usd only); a card with no key sorts as the lowest.
Run 1 sent no dir (most expensive first); run 2 sent dir=asc.
For each page with has_more in run 2, apply reading (a): the page must be
nulls first, then keys ascending; the price is the lowest non-foil price
among the cards that count (paper, released on or before the date, set_type
not memorabilia).
"""
import json
import sys
from urllib.parse import urlparse, parse_qs

FINISHES = {"usd": ("usd", "usd_foil", "usd_etched"), "eur": ("eur", "eur_foil")}


def key(card, cur):
    p = card.get("prices") or {}
    for f in FINISHES[cur]:
        if p.get(f) is not None:
            return float(p[f])
    return None


def counts(card, today):
    return (card.get("released_at", "9") <= today
            and card.get("set_type") != "memorabilia"
            and "paper" in card.get("games", ["paper"]))


def inversions(keys, asc):
    # null is the lowest key
    k = [(-1.0 if x is None else x) for x in keys]
    if not asc:
        k = [-x for x in k]
    return sum(1 for a, b in zip(k, k[1:]) if b < a)


def main(run_dir, asc, today):
    req = json.load(open(f"{run_dir}/requests.json"))["requests"]
    pages = total_inv = 0
    rows = []
    for r in req:
        if "/cards/search" not in r["url"]:
            continue
        q = parse_qs(urlparse(r["url"]).query)
        cur = q["order"][0]
        a = json.load(open(f"{run_dir}/answer-{r['index']:02d}.json"))
        data = a.get("data") or []
        keys = [key(c, cur) for c in data]
        inv = inversions(keys, asc)
        pages += 1
        total_inv += inv
        if a.get("has_more"):
            nulls = sum(1 for x in keys if x is None)
            lead = 0
            for x in (keys if asc else keys[::-1]):
                if x is None:
                    lead += 1
                else:
                    break
            best = None
            for c in data:
                p = (c.get("prices") or {}).get(cur)
                if counts(c, today) and p is not None and (best is None or float(p) < best[0]):
                    best = (float(p), c["set"], c.get("set_type"))
            rows.append((r["index"], data[0]["name"], cur, len(data), nulls, lead, inv, best,
                         keys[-1]))
    print(f"{run_dir}: {pages} search pages, {total_inv} inversions under the model (asc={asc})")
    for row in rows:
        idx, name, cur, n, nulls, lead, inv, best, last = row
        print(f"  answer {idx:02d} {name} {cur}: {n} cards, {nulls} without key, "
              f"{lead} of them {'first' if asc else 'last'}, inversions {inv}, "
              f"last key {last}, lowest counting non-foil {best}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] == "asc", sys.argv[3])
