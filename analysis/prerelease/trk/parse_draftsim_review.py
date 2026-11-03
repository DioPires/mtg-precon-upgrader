"""DEC-1218 R1: read the ratings out of Draftsim's Star Trek set review into {card name: rating 0-10}.

    python3 -I parse_draftsim_review.py REVIEW_HTML CARDS_JSON OUT_JSON

https://draftsim.com/mtg-trk-limited-set-review/ (published 2 November 2026, 17:00Z) gives each
card an <h3> heading with its name, then its image, then "Rating: X/10". The last <h3> before a
rating names the card. Ratings that match no card are printed. The page is saved, not committed.
"""
import html
import json
import re
import sys


def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


page_path, cards_path, out_path = sys.argv[1:4]
page = open(page_path, encoding="utf-8", errors="replace").read()

names = {}
for c in json.load(open(cards_path, encoding="utf-8")):
    names[norm(c["name"])] = c["name"]
    if " // " in c["name"]:
        for face in c["name"].split(" // "):
            names.setdefault(norm(face), c["name"])

out, unmatched, last = {}, [], 0
for m in re.finditer(r"Rating:\s*([0-9.]+)\s*/\s*10", page):
    heads = re.findall(r"<h3[^>]*>(.*?)</h3>", page[last:m.start()], re.S)
    last = m.end()
    if not heads:
        unmatched.append(f"(no heading before rating {m.group(1)})")
        continue
    head = html.unescape(re.sub(r"<[^>]+>", "", heads[-1])).strip()
    name = names.get(norm(head))
    if name is None:
        unmatched.append(head)
    elif name in out and out[name] != float(m.group(1)):
        unmatched.append(f"{name}: rated twice ({out[name]} and {m.group(1)})")
    else:
        out[name] = float(m.group(1))
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(dict(sorted(out.items())), f, indent=1, ensure_ascii=False)
    f.write("\n")
print(f"{len(out)} ratings; unmatched: {unmatched}")
