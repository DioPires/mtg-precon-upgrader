"""DEC-1218 R1: parse MTG Arena Zone's Limited set review (J2SJosh) into {card name: rating 0-5}.

    python3 -I parse_mtgaz.py CARDS_JSON OUT_JSON PAGE.html [PAGE.html ...]

Each card is a heading (any level) followed by an <h3> "Rating: X/5". Names match the card dump
with punctuation and case ignored ("Type 2 Phaser", "All Good Things . . ."). Group ratings
("Shock lands", "Planets") match no card and are printed as unmatched.

Pages (saved 2026-11-02 14:1xZ, not committed):
  https://mtgazone.com/star-trek-trk-limited-set-review-{white,blue,black,red,green,multicolor,artifacts-and-lands}/
  https://mtgazone.com/reality-fracture-fra-limited-set-review-{same seven}/  -> ../fra/backtest/mtgaz_grades.json
"""
import html, json, re, sys

def norm(s):
    for a, b in (("’", "'"), ("‘", "'"), ("“", '"'), ("”", '"'), (" ", " ")):
        s = s.replace(a, b)
    return re.sub(r"[^a-z0-9]", "", s.lower())

cards = json.load(open(sys.argv[1], encoding="utf-8"))
names = {}
for c in cards:
    n = c["name"]
    names[norm(n)] = n
    if " // " in n:
        names.setdefault(norm(n.split(" // ")[0]), n)
tok = re.compile(r'(?is)<h3[^>]*>\s*Rating:\s*([0-9.]+)\s*/\s*5\s*</h3>|<h([1-6])[^>]*>(.*?)</h\2>')
out, unmatched, dup = {}, [], []
for page in sys.argv[3:]:
    raw = open(page, encoding="utf-8", errors="replace").read()
    cur = None
    for m in tok.finditer(raw):
        if m.group(1) is None:
            t = norm(html.unescape(re.sub(r"(?s)<[^>]+>", "", m.group(3))))
            cur = names.get(t)
            if cur is None:
                cur = ("?", t)
        else:
            r = float(m.group(1))
            if isinstance(cur, tuple):
                unmatched.append((cur[1], r, page.rsplit("/", 1)[-1]))
            elif cur is None:
                unmatched.append(("<none>", r, page))
            elif cur in out:
                dup.append(cur)
            else:
                out[cur] = r
            cur = None
json.dump(dict(sorted(out.items())), open(sys.argv[2], "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print("ratings", len(out), "unmatched", len(unmatched), "dups", len(dup))
for u in unmatched: print("  unmatched:", u)
for d in dup: print("  dup:", d)
