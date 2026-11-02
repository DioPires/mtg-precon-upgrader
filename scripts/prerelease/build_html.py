"""Write DIR/cheat_sheet.html: the cheat sheet as one page for a phone.

    uv run --with markdown python scripts/prerelease/build_html.py --set-dir DIR

Reads DIR/cheat_sheet.md (build_cheat_sheet.py writes it), DIR/grades.json and
the card dump. Writes one self-contained file: inline CSS and JavaScript, no
font, script, style or image from the network; it works opened from disk. The
only network addresses in it are the Scryfall card links of the sheet.

- The intro and sections 1 to 5 are the sheet's markdown, rendered with
  python-markdown (`uv run --with markdown`; not a project dependency) like
  build_pdf.py. Every word and link stays. Mana costs become small coloured
  symbols drawn with CSS; each keeps its source text in `data-mana`. Section 3
  and 4's colour lists become one block per colour, and section 5's pair plans
  one block per archetype, with Signposts and Look for behind a tap.
- Section 6 is built from grades.json with build_cheat_sheet.py's own groups,
  order, grades, costs, tags, notes and links: one block per card.
- A bar at the bottom of the screen links each section. Without JavaScript the
  page is the full sheet; with it, section 6 gets a search field and filter
  chips, each card a pool counter, and a Pool view counts steps 2, 3, 4 and 7
  of the hand procedure. pool_summary() below is the reference for those
  counts; the page's script does the same counts, and check_html.mjs compares
  the two.

Two builds write the same bytes. A set folder needs only cheat_sheet.md,
grades.json and the card dump. --publish also writes the same bytes to
web/public/prerelease/<set folder name>.html: Vite copies web/public/ into the
site as it is, so the page is served at /prerelease/<name>.html.

Other modes, for the checks:
    --check-text          compare the text of the intro and sections 1 to 5 of
                          the built page with python-markdown's render of the
                          sheet (needs markdown)
    --pool-summary FILE   print pool_summary() for the pool in FILE ({name:
                          copies}; "-" reads stdin), flattened as the page's
                          `data-num` keys
    --check-data          print SEARCH_EXAMPLES and CHECK_POOLS as JSON
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import unicodedata
from html.parser import HTMLParser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PUBLISH_DIR = os.path.join(ROOT, "web", "public", "prerelease")

from build_cheat_sheet import (  # noqa: E402
    COLOR_PIP,
    PAIR_PLANS_LEAD,
    PAIRS,
    card_urls,
    front_cost,
    full_list_groups,
    grade_text,
    heading_pip,
    link_cards,
    mark,
)
from setlib import WUBRG, bucket, load_cards, pips, set_code  # noqa: E402

# Section number -> (anchor, label in the bar).
SECTIONS = {
    1: ("build", "Build"),
    2: ("rules", "Rules"),
    3: ("removal", "Removal"),
    4: ("tricks", "Tricks"),
    5: ("archetypes", "Archetypes"),
    6: ("cards", "Cards"),
}
POOL = ("pool", "Pool")

TAGS = (("★", "bomb"), ("✕", "removal"), ("⚡", "instant speed"), ("◆", "fixing"), ("✚", "card advantage"))

# The search examples of DEC-1223 on the Star Trek list: query -> the cards it
# shows. tests/test_prerelease_tools.py and check_html.mjs both read this list.
SEARCH_EXAMPLES = (
    ("obrien", ("Miles O'Brien, Transporter Ops",)),
    ("uss ent", ("U.S.S. Enterprise-A, Free Spirit", "U.S.S. Enterprise-D, Galaxy-Class")),
    ("spock", ("Mr. Spock, Science Officer", "Spock, Always Your Friend")),
    ("khaan", ("Khaaaaaaaaaaaannn!",)),
)

# Two Star Trek pools for the pool counts. "sample" holds a hybrid, a gold card,
# a ★, a Spacecraft, a colourless creature, a land, a three-colour card, cards
# graded 5.5 and two copies of one card; its ties break on two-drops and pair
# order. In "ties", ties break on ✚, ✕, ★ and pair order. The tests hold the
# hand-counted numbers for both; check_html.mjs loads both into the page.
CHECK_POOLS = {
    "sample": {
        "Captain Jean-Luc Picard": 1,
        "Malfunctioning Holodeck": 2,
        "U.S.S. Excelsior, Cutting Edge": 1,
        "Command Decision": 1,
        "Picard, Leading by Example": 1,
        "Marooned": 1,
        "Guidance Failure": 1,
        "Constable Odo": 1,
        "The Duras Sisters": 1,
        "Locutus, the One Who Speaks": 1,
        "Hemmer, Fixing What Is Broken": 1,
        "Crystalline Entity": 1,
        "Cybernetic Specialist": 1,
        "Vulcan": 1,
        "Sarek, Federation Ambassador": 1,
    },
    "ties": {
        "Captain Jean-Luc Picard": 1,
        "Marooned": 2,
        "Phlox, Unorthodox Doctor": 1,
        "Borg Cube": 1,
    },
}

MANA_NAMES = {
    "W": "white",
    "U": "blue",
    "B": "black",
    "R": "red",
    "G": "green",
    "C": "colourless",
    "S": "snow",
    "P": "Phyrexian",
}
MANA = re.compile(r"\{([0-9]+|[WUBRGCSXYZ]|[0-9WUBRG]/[WUBRGP])\}")


# ------------------------------------------------------------------ the rules


def normalize_name(text: str) -> str:
    """A card name or a query as the search compares them.

    Lower case, accents removed, apostrophes and full stops removed, other
    punctuation turned into spaces, and a run of three or more of one letter
    cut to two, so that "khaan" finds "Khaaaaaaaaaaaannn!" ("khaann"). The
    page's script does the same.
    """
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn").lower()
    text = re.sub(r"['’‘ʼ.]", "", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = re.sub(r"([a-z])\1\1+", r"\1\1", text)
    return text.strip()


def search(query: str, names: list) -> list:
    """The names that hold every word of the query, in the order given."""
    words = normalize_name(query).split()
    return [n for n in names if all(w in normalize_name(n) for w in words)]


def mana_value(cost: str) -> int:
    """Mana value of a front-face cost: {2/W} counts 2, {X} counts 0."""
    total = 0
    for p in pips(cost):
        digits = [int(a) for a in p.split("/") if a.isdigit()]
        if digits:
            total += max(digits)
        elif p not in ("X", "Y", "Z"):
            total += 1
    return total


def kind(entry: dict) -> str:
    """W, U, B, R or G for a mono-coloured card; else hybrid, gold, three, colourless or land."""
    key = bucket(entry)
    if key in WUBRG:
        return key
    if key.startswith("Gold"):
        return "gold"
    return {
        "Hybrid (either color)": "hybrid",
        "Three+ colors": "three",
        "Colorless": "colourless",
        "Lands": "land",
    }[key]


def facts(entry: dict) -> dict:
    """What the pool counts read off one graded card."""
    tags = mark(entry)
    return {
        "kind": kind(entry),
        "colours": "".join(c for c in WUBRG if c in entry["colors"]),
        "grade": entry["grade"],
        "creature": "Creature" in entry["type_line"].split(" // ")[0],
        "mv": mana_value(front_cost(entry)),
        "bomb": "★" in tags,
        "cardadv": "✚" in tags,
        "removal": "✕" in tags,
    }


def in_colour(f: dict, colour: str) -> bool:
    """Step 2: a mono-coloured card of that colour, or a hybrid card with it."""
    return f["kind"] == colour or (f["kind"] == "hybrid" and colour in f["colours"])


TIE_BREAKS = (("bombs", "★"), ("cardadv", "✚"), ("removal", "✕"), ("two_drops", "two-drops"))


def pool_summary(pool: dict, grades: list) -> dict:
    """Steps 2, 3, 4 and 7 of the hand procedure for a pool {card name: copies}.

    Step 2, per colour: the cards graded 6+, 4+ and the ★ cards; mono-coloured
    cards of the colour and hybrid cards with it. Step 3, per pair: the score
    is the pair's cards graded 6+, a ★ counted twice; the pair's cards are its
    two colours' mono-coloured cards and the hybrid cards with either colour.
    Step 4, per pair: those cards plus the pair's gold cards (exactly its two
    colours) and the colourless non-land cards, graded 4+, and the creatures
    among them (front face; a Spacecraft is not a creature). Step 7: a tie in
    score breaks by more ★, ✚, ✕, then two-drops (mana value 2), over the step
    4 cards graded 4+; then by the order of PAIRS. Every comparison is `>=`,
    and two copies count twice. Names that are not graded are left out.
    """
    by_name = {e["name"]: facts(e) for e in grades}
    items = [(by_name[n], c) for n, c in pool.items() if n in by_name and c > 0]

    def count(cards, test) -> int:
        return sum(c for f, c in cards if test(f))

    colours = {}
    for colour in WUBRG:
        cards = [(f, c) for f, c in items if in_colour(f, colour)]
        colours[colour] = {
            "six": count(cards, lambda f: f["grade"] >= 6),
            "four": count(cards, lambda f: f["grade"] >= 4),
            "bombs": count(cards, lambda f: f["bomb"]),
        }

    pairs = []
    for order, pair in enumerate(PAIRS):
        base = [(f, c) for f, c in items if any(in_colour(f, col) for col in pair)]
        deck = base + [
            (f, c) for f, c in items
            if (f["kind"] == "gold" and f["colours"] == pair) or f["kind"] == "colourless"
        ]
        four = [(f, c) for f, c in deck if f["grade"] >= 4]
        pairs.append({
            "pair": pair,
            "order": order,
            "score": sum(c * (2 if f["bomb"] else 1) for f, c in base if f["grade"] >= 6),
            "four": count(four, lambda f: True),
            "creatures": count(four, lambda f: f["creature"]),
            "bombs": count(four, lambda f: f["bomb"]),
            "cardadv": count(four, lambda f: f["cardadv"]),
            "removal": count(four, lambda f: f["removal"]),
            "two_drops": count(four, lambda f: f["mv"] == 2),
        })
    pairs.sort(key=lambda p: (-p["score"], *(-p[k] for k, _ in TIE_BREAKS), p["order"]))

    ties = []
    for above, below in zip(pairs, pairs[1:]):
        if above["score"] != below["score"]:
            continue
        by = next((label for k, label in TIE_BREAKS if above[k] != below[k]), "pair order")
        ties.append({"above": above["pair"], "below": below["pair"], "by": by})
    for p in pairs:
        del p["order"]
    return {"cards": sum(c for _, c in items), "colours": colours, "pairs": pairs, "ties": ties}


def flatten_summary(summary: dict) -> dict:
    """pool_summary() as the Pool view's `data-num` keys and texts."""
    out = {"cards": str(summary["cards"])}
    for colour, counts in summary["colours"].items():
        for k in ("six", "four", "bombs"):
            out[f"colours.{colour}.{k}"] = str(counts[k])
    for rank, p in enumerate(summary["pairs"], 1):
        out[f"rank.{rank}.pair"] = p["pair"]
        for k in ("score", "bombs", "cardadv", "removal", "two_drops"):
            out[f"rank.{rank}.{k}"] = str(p[k])
        if rank <= 3:
            out[f"rank.{rank}.four"] = str(p["four"])
            out[f"rank.{rank}.creatures"] = str(p["creatures"])
    for i, tie in enumerate(summary["ties"], 1):
        for k in ("above", "below", "by"):
            out[f"tie.{i}.{k}"] = tie[k]
    return out


# ------------------------------------------------------------------- the page


def esc(text) -> str:
    return html.escape(str(text), quote=True)


def mana_symbol(sym: str) -> str:
    """One symbol: a coloured circle, or a two-colour pill for a hybrid."""
    parts = sym.split("/")

    def cls(part: str) -> str:
        return f"m-{part.lower()}" if part in "WUBRG" else "m-n"

    if len(parts) == 2 and parts[1] == "P":
        name = f"Phyrexian {MANA_NAMES.get(parts[0], parts[0])}"
    else:
        name = " or ".join(MANA_NAMES.get(p, p) for p in parts)
    if len(parts) == 1:
        return (
            f'<span class="ms {cls(sym)}" data-mana="{{{esc(sym)}}}" role="img" '
            f'aria-label="{esc(name)}">{esc(sym)}</span>'
        )
    halves = "".join(f'<i class="{cls(p)}">{esc(p)}</i>' for p in parts)
    return f'<span class="ms ms-h" data-mana="{{{esc(sym)}}}" role="img" aria-label="{esc(name)}">{halves}</span>'


def mana_html(cost: str) -> str:
    return "".join(mana_symbol(p) for p in pips(cost))


def symbols(fragment: str) -> str:
    """Mana symbols for every {..} in the text of an HTML fragment, never inside a tag."""
    parts = re.split(r"(<[^>]*>)", fragment)
    return "".join(
        p if p.startswith("<") else MANA.sub(lambda m: mana_symbol(m.group(1)), p) for p in parts
    )


def new_tab(fragment: str) -> str:
    """Links to other sites open in a new tab, so the page keeps its place and search."""
    return re.sub(r'<a href="(https?://[^"]*)">', r'<a href="\1" target="_blank" rel="noopener">', fragment)


def scroll_tables(fragment: str) -> str:
    """A wide table scrolls inside its own box, never the page."""
    return fragment.replace(
        "<table>", '<div class="tbl" role="region" aria-label="Table" tabindex="0"><table>'
    ).replace("</table>", "</table></div>")


def md_links(text: str) -> str:
    """Escape a plain-text cell and turn its [name](url) links into anchors."""
    out, last = [], 0
    for m in re.finditer(r"\[([^\]]+)\]\(([^)\s]+)\)", text):
        out.append(esc(text[last:m.start()]))
        out.append(f'<a href="{esc(m.group(2))}" target="_blank" rel="noopener">{esc(m.group(1))}</a>')
        last = m.end()
    out.append(esc(text[last:]))
    return "".join(out)


class Markdown:
    """python-markdown with build_pdf.py's extensions, and the page's touches."""

    def __init__(self):
        import markdown  # Here, so the tests import this module without the package.

        self._md = markdown.Markdown(extensions=["tables", "sane_lists"])

    def block(self, text: str) -> str:
        self._md.reset()
        return scroll_tables(new_tab(symbols(self._md.convert(text))))

    def inline(self, text: str) -> str:
        out = self.block(text)
        if out.startswith("<p>") and out.endswith("</p>"):
            out = out[3:-4]
        return out


GROUP_HEAD = re.compile(r"^- (\S+) \*\*([^*]+)\*\*$")
CHILD = re.compile(r"^    - (.*)$")
COST_ONLY = re.compile(r"^(.*) \(((?:\{[^}]+\})+)\)$")
PAIR_HEAD = re.compile(r"^- (\S+) \*\*([^*]+)\*\*(?: — (.*))?$")


def chunks(lines: list) -> list:
    """Split a section body at blank lines into runs of lines."""
    out, run = [], []
    for line in lines:
        if line.strip():
            run.append(line)
        elif run:
            out.append(run)
            run = []
    if run:
        out.append(run)
    return out


def colour_groups(run: list, md: Markdown) -> str | None:
    """A list such as "- ⚪ **W**" with indented cards, as one block per colour; None if not one."""
    if not GROUP_HEAD.match(run[0]) or not all(GROUP_HEAD.match(l) or CHILD.match(l) for l in run):
        return None
    out, open_list = ['<div class="cgroups">'], False
    for line in run:
        head = GROUP_HEAD.match(line)
        if head:
            if open_list:
                out.append("</ul>\n</div>")
            out.append(f'<div class="cg">\n<p class="cg-h">{esc(head.group(1))} <strong>{esc(head.group(2))}</strong></p>\n<ul>')
            open_list = True
            continue
        item = CHILD.match(line).group(1)
        cost = COST_ONLY.match(item)
        if cost:
            out.append(
                f'<li class="tr"><span class="tn">{md.inline(cost.group(1))}</span> '
                f'<span class="tc"><span class="vh">(</span>{symbols(esc(cost.group(2)))}<span class="vh">)</span></span></li>'
            )
        else:
            out.append(f"<li>{md.inline(item)}</li>")
    out.append("</ul>\n</div>\n</div>")
    return "\n".join(out)


def pair_blocks(run: list, md: Markdown) -> str | None:
    """Section 5's pair plans: one block per archetype, Signposts and Look for behind a tap."""
    if not PAIR_HEAD.match(run[0]) or not all(PAIR_HEAD.match(l) or CHILD.match(l) for l in run):
        return None
    out, in_block, in_more = ['<div class="archs">'], False, False
    for line in run:
        head = PAIR_HEAD.match(line)
        if head:
            if in_more:
                out.append("</div>")
            if in_block:
                out.append("</div>")
            in_block, in_more = True, False
            out.append(f'<div class="arch">\n<h3>{esc(head.group(1))} {md.inline(head.group(2))}</h3>')
            if head.group(3):
                out.append(f'<p class="plan"><span class="vh">— </span>{md.inline(head.group(3))}</p>')
            continue
        item = CHILD.match(line).group(1)
        label, sep, rest = item.partition(": ")
        if sep and label in ("Signposts", "Look for"):
            if not in_more:
                out.append('<div class="more">')
                in_more = True
            out.append(f"<details>\n<summary>{esc(label)}:</summary>\n<p>{md.inline(rest)}</p>\n</details>")
            continue
        if in_more:
            out.append("</div>")
            in_more = False
        out.append(f"<p>{md.inline(item)}</p>")
    if in_more:
        out.append("</div>")
    out.append("</div>\n</div>")
    return "\n".join(out)


def section_body(number: int, lines: list, md: Markdown) -> str:
    out = []
    for run in chunks(lines):
        special = None
        if number in (3, 4):
            special = colour_groups(run, md)
        if number == 5:
            special = pair_blocks(run, md)
        out.append(special if special is not None else md.block("\n".join(run)))
    return "\n".join(out)


def split_sheet(text: str) -> tuple:
    """(head lines, [(number or None, heading, body lines)]) of the sheet's markdown."""
    lines = text.rstrip("\n").split("\n")
    starts = [i for i, line in enumerate(lines) if line.startswith("## ")]
    head = lines[: starts[0]] if starts else lines
    sections = []
    for i, start in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else len(lines)
        heading = lines[start][3:]
        num = re.match(r"(\d+)\.", heading)
        sections.append((int(num.group(1)) if num else None, heading, lines[start + 1 : end]))
    return head, sections


def card_block(entry: dict, urls: dict, cards: list) -> str:
    f = facts(entry)
    grade = entry["grade"]
    band = "g8" if grade >= 8 else "g6" if grade >= 6 else "g4" if grade >= 4 else "g0"
    grade_html = f'<span class="gb {band}">{esc(grade)}</span>'
    syn = grade_text(entry)[len(str(grade)) :]
    if syn:
        grade_html += f'<span class="syn">{esc(syn)}</span>'
    name = esc(entry["name"])
    if entry["name"] in urls:
        name = f'<a class="cn" href="{esc(urls[entry["name"]])}" target="_blank" rel="noopener">{name}</a>'
    else:
        name = f'<span class="cn">{name}</span>'
    rarity = entry["rarity"]
    tags = "".join(f'<span role="img" aria-label="{n}" title="{n}">{t}</span>' for t, n in TAGS if t in mark(entry))
    note = md_links(link_cards(entry["note"], cards)) if urls else esc(entry["note"])
    attrs = {
        "data-name": entry["name"],
        "data-q": normalize_name(entry["name"]),
        "data-g": grade,
        "data-k": f["kind"],
        "data-c": f["colours"],
        "data-r": rarity[0].upper(),
        "data-t": mark(entry),
        "data-mv": f["mv"],
        "data-cr": int(f["creature"]),
    }
    attr = " ".join(f'{k}="{esc(v)}"' for k, v in attrs.items())
    return (
        f'<li class="card" {attr}><div class="gr">{grade_html}</div>'
        f'<div class="l1">{name} <span class="cost">{mana_html(front_cost(entry))}</span> '
        f'<abbr class="rar" title="{esc(rarity)}">{esc(rarity[0].upper())}</abbr> '
        f'<span class="tags">{tags}</span></div>'
        f'<p class="note">{note}</p></li>'
    )


def chip(kind_: str, value: str, label: str) -> str:
    return f'<button type="button" class="chip" aria-pressed="false" data-f="{kind_}" data-v="{esc(value)}">{label}</button>'


def cards_section(heading: str, graded: list, urls: dict, cards: list) -> str:
    anchor, _ = SECTIONS[6]
    total = len(graded)
    legend = " ".join(f'<span class="lg"><b>{t}</b> {name}</span>' for t, name in TAGS)
    colour_chips = "".join(chip("c", c, mana_symbol(c)) for c in WUBRG) + chip("c", "gold", "Gold") + chip(
        "c", "colourless", "Colourless"
    )
    rarity_chips = "".join(chip("r", r, r) for r in "CURM")
    tag_chips = "".join(chip("t", t, f'<span aria-hidden="true">{t}</span><span class="vh">{n}</span>') for t, n in TAGS)
    grade_chips = chip("g", "4", "4+") + chip("g", "6", "6+") + chip("p", "1", "In my pool")
    groups = []
    for key, entries in full_list_groups(graded):
        gid = "g-" + re.sub(r"[^a-z0-9]+", "-", key.lower()).strip("-")
        blocks = "\n".join(card_block(e, urls, cards) for e in entries)
        groups.append(
            f'<section class="grp" aria-labelledby="{gid}">\n<h3 id="{gid}">{esc(heading_pip(key))} {esc(key)}</h3>\n'
            f'<ul class="cards">\n{blocks}\n</ul>\n</section>'
        )
    return f"""<section id="{anchor}" aria-labelledby="h-{anchor}">
<h2 id="h-{anchor}">{esc(heading)}</h2>
<p class="legend">{legend}</p>
<p class="legend">Grade: <span class="gb g8">8+</span> <span class="gb g6">6–7.5</span> <span class="gb g4">4–5.5</span> <span class="gb g0">under 4</span></p>
<div class="controls js-only" id="controls">
<div class="srch"><label for="q" class="vh">Search card names</label><input id="q" type="search" placeholder="Search card names" autocomplete="off" autocorrect="off" autocapitalize="none" spellcheck="false" enterkeyhint="search"><button type="button" id="q-clear" aria-label="Clear the search">×</button></div>
<div class="crow"><span id="shown" aria-live="polite">{total} of {total}</span><button type="button" id="ftoggle" aria-expanded="false" aria-controls="fpanel">Filters</button><a href="#{POOL[0]}" id="pool-link">Pool <span id="pool-n">0</span></a></div>
<div id="fpanel" hidden>
<div class="chips" role="group" aria-label="Colour">{colour_chips}</div>
<div class="chips" role="group" aria-label="Rarity">{rarity_chips}</div>
<div class="chips" role="group" aria-label="Tag">{tag_chips}</div>
<div class="chips" role="group" aria-label="Grade and pool">{grade_chips}<button type="button" id="freset">Clear filters</button></div>
</div>
</div>
<div id="list">
{chr(10).join(groups)}
</div>
<p id="none" class="js-only" hidden>No card matches.</p>
</section>"""


POOL_SECTION = f"""<section id="{POOL[0]}" class="js-only" aria-labelledby="h-{POOL[0]}">
<h2 id="h-{POOL[0]}">Pool</h2>
<div id="pool-body"></div>
</section>"""


def nav(sections: list) -> str:
    items = []
    for num, _, _ in sections:
        if num in SECTIONS:
            anchor, label = SECTIONS[num]
            items.append(f'<li><a href="#{anchor}">{label}</a></li>')
    items.append(f'<li class="js-only"><a href="#{POOL[0]}">{POOL[1]}</a></li>')
    return f'<nav class="bar" id="bar" aria-label="Sections">\n<ul>\n{chr(10).join(items)}\n</ul>\n</nav>'


def build(set_dir: str) -> str:
    with open(os.path.join(set_dir, "cheat_sheet.md"), encoding="utf-8") as fh:
        sheet = fh.read()
    with open(os.path.join(set_dir, "grades.json"), encoding="utf-8") as fh:
        graded = json.load(fh)
    cards = load_cards(set_dir)
    # Link section 6 only when the sheet itself carries the Scryfall links.
    urls = card_urls(cards) if "](https://scryfall.com/" in sheet else {}
    md = Markdown()

    head, sections = split_sheet(sheet)
    title = re.sub(r"^#\s*", "", next((l for l in head if l.startswith("# ")), "# Cheat sheet"))
    parts = [f'<header class="intro">\n{md.block(chr(10).join(head))}\n</header>']
    for num, heading, body in sections:
        if num == 6:
            parts.append(cards_section(heading, graded, urls, cards))
            continue
        anchor = SECTIONS[num][0] if num in SECTIONS else "s-" + re.sub(r"[^a-z0-9]+", "-", heading.lower()).strip("-")
        parts.append(
            f'<section id="{anchor}" aria-labelledby="h-{anchor}">\n'
            f'<h2 id="h-{anchor}">{symbols(esc(heading))}</h2>\n{section_body(num, body, md)}\n</section>'
        )
    parts.append(POOL_SECTION)

    config = {"set": set_code(set_dir), "pairs": list(PAIRS), "pips": COLOR_PIP}
    return f"""<!doctype html>
<html lang="en" data-set="{esc(set_code(set_dir))}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="color-scheme" content="light dark">
<title>{esc(title)}</title>
<script>document.documentElement.classList.add("js")</script>
<style>{CSS}</style>
</head>
<body>
<a class="skip" href="#main">Skip to the sheet</a>
{nav(sections)}
<main id="main">
{chr(10).join(parts)}
</main>
<script>const CONFIG = {json.dumps(config, ensure_ascii=False, sort_keys=True)};
{SCRIPT}</script>
</body>
</html>
"""


# --------------------------------------------------------------------- checks


class _Text(HTMLParser):
    """The text of a page or a render: a mana symbol reads as its source text."""

    def __init__(self, stop_id: str | None):
        super().__init__(convert_charrefs=True)
        self.stop_id, self.stopped, self.out, self.skip, self.inside = stop_id, False, [], 0, stop_id is None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if self.stop_id and a.get("id") == self.stop_id:
            self.stopped = True
        if tag == "main":
            self.inside = True
        if self.stopped or not self.inside:
            return
        if self.skip:
            if tag == "span":
                self.skip += 1
            return
        if "data-mana" in a:
            self.out.append(a["data-mana"])
            self.skip = 1

    def handle_endtag(self, tag):
        if self.skip and tag == "span":
            self.skip -= 1

    def handle_data(self, data):
        if self.inside and not self.stopped and not self.skip:
            self.out.append(data)

    def text(self) -> str:
        return " ".join("".join(self.out).split())


def text_check(set_dir: str) -> tuple:
    """(equal, page text, sheet text) for the intro and sections 1 to 5."""
    import markdown

    with open(os.path.join(set_dir, "cheat_sheet.md"), encoding="utf-8") as fh:
        sheet = fh.read()
    with open(os.path.join(set_dir, "cheat_sheet.html"), encoding="utf-8") as fh:
        page = fh.read()
    lines = sheet.split("\n")
    cut = next((i for i, l in enumerate(lines) if l.startswith("## 6.")), len(lines))
    render = markdown.markdown("\n".join(lines[:cut]), extensions=["tables", "sane_lists"])
    a, b = _Text(SECTIONS[6][0]), _Text(None)
    a.feed(page)
    b.feed(render)
    return a.text() == b.text(), a.text(), b.text()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--set-dir")
    ap.add_argument("--check-text", action="store_true")
    ap.add_argument("--pool-summary", metavar="FILE")
    ap.add_argument("--check-data", action="store_true")
    ap.add_argument("--publish", action="store_true", help="also write web/public/prerelease/<set folder name>.html")
    args = ap.parse_args()

    if args.check_data:
        print(json.dumps({"search_examples": SEARCH_EXAMPLES, "pools": CHECK_POOLS}, ensure_ascii=False))
        return 0
    if not args.set_dir:
        ap.error("--set-dir is required")
    if args.pool_summary:
        with (sys.stdin if args.pool_summary == "-" else open(args.pool_summary, encoding="utf-8")) as fh:
            pool = json.load(fh)
        with open(os.path.join(args.set_dir, "grades.json"), encoding="utf-8") as fh:
            graded = json.load(fh)
        print(json.dumps(flatten_summary(pool_summary(pool, graded)), ensure_ascii=False))
        return 0
    if args.check_text:
        equal, page, render = text_check(args.set_dir)
        if equal:
            print(f"text check: intro and sections 1 to 5 equal ({len(page)} characters, {len(page.split())} words)")
            return 0
        i = next((i for i, (x, y) in enumerate(zip(page, render)) if x != y), min(len(page), len(render)))
        print(f"text check: DIFFER at character {i}")
        print("  page :", page[max(0, i - 80) : i + 80])
        print("  sheet:", render[max(0, i - 80) : i + 80])
        return 1

    data = build(args.set_dir).encode("utf-8")
    out_paths = [os.path.join(args.set_dir, "cheat_sheet.html")]
    if args.publish:
        os.makedirs(PUBLISH_DIR, exist_ok=True)
        out_paths.append(os.path.join(PUBLISH_DIR, os.path.basename(os.path.abspath(args.set_dir)) + ".html"))
    for out_path in out_paths:
        with open(out_path, "wb") as fh:
            fh.write(data)
        print(f"wrote {out_path} ({len(data)} bytes)")
    return 0


CSS = """
:root{--bg:#fff;--fg:#1b1c1f;--muted:#50545c;--line:#d3d6dc;--surface:#f2f3f5;--link:#0b55c4;--accent:#5326b8;--pool:#ebf2ff;
--g8b:#5b21b6;--g8f:#fff;--g6b:#14632f;--g6f:#fff;--g4b:#fde68a;--g4f:#3d2c00;--g0b:#e3e5e9;--g0f:#33373e;--bar:56px}
@media (prefers-color-scheme:dark){:root{--bg:#121316;--fg:#ebecef;--muted:#b3b7bf;--line:#3b3e45;--surface:#1e2025;--link:#8db7ff;--accent:#c4b0ff;--pool:#1b2a45;
--g8b:#c4b5fd;--g8f:#1f1147;--g6b:#86efac;--g6f:#06301a;--g4b:#fcd34d;--g4f:#3d2c00;--g0b:#4a4e57;--g0f:#f2f3f5}}
*{box-sizing:border-box}
[hidden]{display:none!important}
html{-webkit-text-size-adjust:100%;color-scheme:light dark}
@media (prefers-reduced-motion:no-preference){html{scroll-behavior:smooth}}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif,"Apple Color Emoji","Segoe UI Emoji";padding-bottom:calc(var(--bar) + env(safe-area-inset-bottom) + 16px);overflow-wrap:break-word}
main{max-width:46rem;margin:0 auto;padding:0 16px}
a{color:var(--link)}
:focus-visible{outline:3px solid var(--accent);outline-offset:2px}
.vh{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
.skip{position:absolute;left:8px;top:-60px;background:var(--bg);padding:8px;z-index:20}
.skip:focus{top:8px}
h1{font-size:1.5rem;line-height:1.25;margin:20px 0 8px}
h2{font-size:1.3rem;line-height:1.3;margin:32px 0 12px;padding-top:16px;border-top:2px solid var(--line);scroll-margin-top:8px}
h3{font-size:1.1rem;line-height:1.3;margin:20px 0 8px;scroll-margin-top:8px}
section[id]{scroll-margin-top:8px}
p,li{margin:0 0 8px}
ul,ol{padding-left:1.4em;margin:0 0 12px}
li>ul{margin-top:6px}
sub{font-size:1rem;vertical-align:baseline;color:var(--muted);display:block;line-height:1.4}
.tbl{overflow-x:auto;margin:0 0 16px;border:1px solid var(--line);border-radius:8px}
table{border-collapse:collapse;font-variant-numeric:tabular-nums;min-width:100%}
th,td{padding:6px 7px;border-bottom:1px solid var(--line);text-align:left;white-space:nowrap}
th{background:var(--surface);font-weight:600}
tr:last-child td{border-bottom:0}
td[align="right"],th[align="right"],td[style*="right"],th[style*="right"]{text-align:right}
.ms{display:inline-flex;align-items:center;justify-content:center;min-width:1.45em;height:1.45em;padding:0 .2em;margin:0 .06em;border-radius:1em;font:700 .75em/1 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;vertical-align:.08em;box-shadow:inset 0 0 0 1px rgba(0,0,0,.28)}
.ms-h{padding:0;overflow:hidden;min-width:2.4em}
.ms-h i{flex:1;align-self:stretch;display:flex;align-items:center;justify-content:center;font-style:normal}
.m-w{background:#f6f0cf;color:#38331f}.m-u{background:#1d63b3;color:#fff}.m-b{background:#2e2925;color:#f4efe9}
.m-r{background:#bd3226;color:#fff}.m-g{background:#1b7440;color:#fff}.m-n{background:#d5d0ca;color:#24211d}
@media (prefers-color-scheme:dark){.ms{box-shadow:inset 0 0 0 1px rgba(255,255,255,.35)}}
.intro p{color:var(--fg)}
#build ol>li{padding-left:.2em;margin-bottom:12px}
#rules ul>li{margin-bottom:12px}
.cgroups{display:grid;gap:12px;margin:0 0 16px}
.cg{border:1px solid var(--line);border-radius:10px;padding:10px 12px 4px}
.cg-h{margin:0 0 6px;font-size:1.05rem}
.cg ul{list-style:none;padding:0;margin:0}
.cg li{padding:6px 0;border-top:1px solid var(--line);margin:0}
.cg li.tr{display:flex;justify-content:space-between;align-items:baseline;gap:12px}
.tc{white-space:nowrap}
.archs{display:grid;gap:12px}
.arch{border:1px solid var(--line);border-radius:10px;padding:12px}
.arch h3{margin:0 0 4px}
.arch .plan{margin:0 0 8px}
.more{display:flex;flex-wrap:wrap;gap:8px;border-top:1px solid var(--line);padding-top:10px}
.more details{flex:0 0 auto}
.more details[open]{flex:1 0 100%}
summary{cursor:pointer;padding:0 14px;font-weight:600;min-height:44px;display:inline-flex;align-items:center;gap:8px;list-style:none;border:1px solid var(--line);border-radius:22px;background:var(--surface)}
summary::-webkit-details-marker{display:none}
summary::before{content:"";width:.5em;height:.5em;border-right:2px solid currentColor;border-bottom:2px solid currentColor;transform:rotate(-45deg);transition:transform .15s}
details[open]>summary::before{transform:rotate(45deg)}
@media (prefers-reduced-motion:reduce){summary::before{transition:none}}
details>p{margin:8px 0 4px}
.legend{margin:0 0 8px;display:flex;flex-wrap:wrap;gap:4px 14px}
.lg b{font-weight:400}
.gb{display:inline-block;min-width:2.5em;padding:.15em .3em;border-radius:6px;font-weight:700;text-align:center;font-variant-numeric:tabular-nums;line-height:1.3}
.g8{background:var(--g8b);color:var(--g8f)}.g6{background:var(--g6b);color:var(--g6f)}.g4{background:var(--g4b);color:var(--g4f)}.g0{background:var(--g0b);color:var(--g0f)}
.syn{display:block;color:var(--muted)}
.controls{position:sticky;top:0;z-index:5;background:var(--bg);padding:8px 0;border-bottom:1px solid var(--line);margin:0 0 4px}
.srch{display:flex;gap:6px}
#q{flex:1;min-width:0;font:inherit;padding:10px 12px;border:2px solid var(--line);border-radius:10px;background:var(--surface);color:var(--fg);height:48px}
#q:focus{border-color:var(--accent);outline:none}
#q::-webkit-search-cancel-button{display:none}
#q::placeholder{color:var(--muted);opacity:1}
#q-clear{width:48px;height:48px;font-size:1.5rem;border-radius:10px}
.crow{display:flex;align-items:center;gap:8px;margin-top:6px}
#shown{flex:1;color:var(--muted);font-variant-numeric:tabular-nums}
#pool-link{display:inline-flex;align-items:center;gap:.3em;min-height:44px;padding:0 4px;font-weight:600}
button{font:inherit;color:var(--fg);background:var(--surface);border:1px solid var(--line);border-radius:8px;min-height:44px;min-width:44px;padding:0 12px;cursor:pointer}
button[aria-pressed="true"]{background:var(--fg);color:var(--bg);border-color:var(--fg)}
#fpanel{margin-top:8px;max-height:55vh;overflow-y:auto}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin:0 0 8px}
.chip{padding:0 10px;min-width:44px}
#list{margin-top:4px}
.grp h3{margin:16px 0 0;padding:8px 0;border-bottom:2px solid var(--line)}
.cards{list-style:none;padding:0;margin:0}
.card{display:grid;grid-template-columns:2.9em minmax(0,1fr) auto;grid-template-areas:"g l c" ". s s" ". n n";column-gap:10px;padding:10px 0;margin:0;border-bottom:1px solid var(--line)}
.card .gr{display:contents}
.card .gb{grid-area:g;align-self:start}
.card .syn{grid-area:s}
.card .l1{grid-area:l;line-height:1.45}
.card .note{grid-area:n;margin:2px 0 0;color:var(--muted)}
.cn{font-weight:600;text-decoration:none}
.cn:hover,.cn:focus{text-decoration:underline}
.cost{white-space:nowrap}
.rar{text-decoration:none;font-weight:700;color:var(--muted);padding:0 2px}
.tags span{margin-right:2px}
.card.inpool{background:var(--pool);box-shadow:-8px 0 0 var(--pool),8px 0 0 var(--pool)}
.ctr{grid-area:c;display:flex;align-items:flex-start;gap:4px}
.ctr button{width:44px;height:44px;padding:0;font-size:1.4rem;line-height:1}
.ctr .n{min-width:1.4em;text-align:center;font-weight:700;line-height:44px;font-variant-numeric:tabular-nums}
.ctr.zero .dec,.ctr.zero .n{display:none}
.bar{position:fixed;left:0;right:0;bottom:0;z-index:10;background:var(--surface);border-top:1px solid var(--line);padding-bottom:env(safe-area-inset-bottom)}
.bar ul{display:flex;list-style:none;margin:0 auto;padding:0;max-width:46rem}
.bar li{flex:1 1 auto;margin:0;min-width:44px}
.bar a{display:flex;align-items:center;justify-content:center;height:var(--bar);padding:0 2px;font-size:13px;font-weight:600;color:var(--fg);text-decoration:none;white-space:nowrap;letter-spacing:-.01em}
.bar a[aria-current]{color:var(--accent);box-shadow:inset 0 3px 0 var(--accent)}
@media (hover:none) and (pointer:coarse){.typing .bar{display:none}}
html:not(.js) .js-only{display:none!important}
#pool-body table{margin:0}
.ok{color:var(--g6b)}
.st{color:var(--muted);font-weight:600}
.top3 td,.top3 th{font-weight:700}
.hint{color:var(--muted)}
#clear-pool{margin-top:8px}
"""

SCRIPT = r"""
(function () {
  "use strict";
  var KEY = "prerelease-pool-" + CONFIG.set;
  var TIE_BREAKS = [["bombs", "★"], ["cardadv", "✚"], ["removal", "✕"], ["two_drops", "two-drops"]];

  function norm(s) {
    return s.normalize("NFD").replace(/\p{Mn}/gu, "").toLowerCase()
      .replace(/['’‘ʼ.]/g, "").replace(/[^a-z0-9]+/g, " ")
      .replace(/([a-z])\1\1+/g, "$1$1").trim();
  }
  window.cheatSheet = { norm: norm };

  var cards = Array.prototype.map.call(document.querySelectorAll("#list .card"), function (el) {
    var d = el.dataset;
    return { el: el, name: d.name, q: d.q, g: parseFloat(d.g), k: d.k, c: d.c, r: d.r, t: d.t,
             mv: parseInt(d.mv, 10), cr: d.cr === "1", ctr: null };
  });
  var groups = Array.prototype.slice.call(document.querySelectorAll("#list .grp"));

  var pool = {};
  try { pool = JSON.parse(localStorage.getItem(KEY) || "{}") || {}; } catch (e) { pool = {}; }
  function save() {
    try { localStorage.setItem(KEY, JSON.stringify(pool)); } catch (e) { /* private mode: counts last this visit */ }
  }
  function copies(name) { var n = pool[name]; return typeof n === "number" && n > 0 ? Math.floor(n) : 0; }

  // ---------------------------------------------------------------- the counts
  // The same rules as pool_summary() in build_html.py.
  function inColour(d, col) { return d.k === col || (d.k === "hybrid" && d.c.indexOf(col) >= 0); }
  function count(list, test) {
    var n = 0;
    list.forEach(function (x) { if (test(x[0])) n += x[1]; });
    return n;
  }
  function summary() {
    var items = [];
    cards.forEach(function (d) { var n = copies(d.name); if (n > 0) items.push([d, n]); });
    var out = { cards: count(items, function () { return true; }), colours: {}, pairs: [], ties: [] };
    "WUBRG".split("").forEach(function (col) {
      var cs = items.filter(function (x) { return inColour(x[0], col); });
      out.colours[col] = {
        six: count(cs, function (d) { return d.g >= 6; }),
        four: count(cs, function (d) { return d.g >= 4; }),
        bombs: count(cs, function (d) { return d.t.indexOf("★") >= 0; })
      };
    });
    CONFIG.pairs.forEach(function (pair, order) {
      var base = items.filter(function (x) { return inColour(x[0], pair[0]) || inColour(x[0], pair[1]); });
      var deck = base.concat(items.filter(function (x) {
        return (x[0].k === "gold" && x[0].c === pair) || x[0].k === "colourless";
      }));
      var four = deck.filter(function (x) { return x[0].g >= 4; });
      var score = 0;
      base.forEach(function (x) { if (x[0].g >= 6) score += x[1] * (x[0].t.indexOf("★") >= 0 ? 2 : 1); });
      out.pairs.push({
        pair: pair, order: order, score: score,
        four: count(four, function () { return true; }),
        creatures: count(four, function (d) { return d.cr; }),
        bombs: count(four, function (d) { return d.t.indexOf("★") >= 0; }),
        cardadv: count(four, function (d) { return d.t.indexOf("✚") >= 0; }),
        removal: count(four, function (d) { return d.t.indexOf("✕") >= 0; }),
        two_drops: count(four, function (d) { return d.mv === 2; })
      });
    });
    out.pairs.sort(function (a, b) {
      if (a.score !== b.score) return b.score - a.score;
      for (var i = 0; i < TIE_BREAKS.length; i++) {
        var k = TIE_BREAKS[i][0];
        if (a[k] !== b[k]) return b[k] - a[k];
      }
      return a.order - b.order;
    });
    for (var i = 0; i + 1 < out.pairs.length; i++) {
      var a = out.pairs[i], b = out.pairs[i + 1];
      if (a.score !== b.score) continue;
      var by = "pair order";
      for (var j = 0; j < TIE_BREAKS.length; j++) {
        if (a[TIE_BREAKS[j][0]] !== b[TIE_BREAKS[j][0]]) { by = TIE_BREAKS[j][1]; break; }
      }
      out.ties.push({ above: a.pair, below: b.pair, by: by });
    }
    return out;
  }

  // ------------------------------------------------------------- the Pool view
  function esc(s) {
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }
  function num(key, value) { return '<span data-num="' + key + '">' + esc(value) + "</span>"; }
  function pairName(p, key) {
    return '<span aria-hidden="true">' + CONFIG.pips[p[0]] + CONFIG.pips[p[1]] + "</span> " + num(key, p);
  }
  // Beside a step 4 count: a tick on target, else "short" or "over" (no ✗: it reads as the removal tag).
  function target(n, lo, hi) {
    if (n < lo) return ' <span class="st">short</span>';
    if (hi && n > hi) return ' <span class="st">over</span>';
    return ' <span class="ok" role="img" aria-label="on target">✓</span>';
  }
  function renderPool() {
    var s = summary();
    var h = [];
    h.push("<p>" + num("cards", s.cards) + " cards counted. " +
      (s.cards ? "" : "Tap + on a card in the list to count it. ") + '<a href="#cards">Back to the cards</a></p>');
    h.push("<h3>Step 2: per colour</h3>");
    h.push('<p class="hint">Mono-coloured cards of the colour and hybrid cards with it. Gold, three-colour, colourless cards and lands do not count here.</p>');
    h.push('<div class="tbl" role="region" aria-label="Step 2" tabindex="0"><table><thead><tr><th>Colour</th><th>6+</th><th>4+</th><th>★</th></tr></thead><tbody>');
    "WUBRG".split("").forEach(function (c) {
      var v = s.colours[c];
      h.push('<tr><th><span aria-hidden="true">' + CONFIG.pips[c] + "</span> " + c + "</th><td>" +
        num("colours." + c + ".six", v.six) + "</td><td>" + num("colours." + c + ".four", v.four) +
        "</td><td>" + num("colours." + c + ".bombs", v.bombs) + "</td></tr>");
    });
    h.push("</tbody></table></div>");
    h.push("<h3>Step 3: pairs by score</h3>");
    h.push('<p class="hint">Score: the pair\'s cards graded 6+, a ★ counted twice. ★, ✚, ✕ and 2-drops count the step 4 cards graded 4+; they break a tie (step 7).</p>');
    h.push('<div class="tbl" role="region" aria-label="Step 3" tabindex="0"><table><thead><tr><th>#</th><th>Pair</th><th>Score</th><th>★</th><th>✚</th><th>✕</th><th>2-drops</th></tr></thead><tbody>');
    s.pairs.forEach(function (p, i) {
      var r = "rank." + (i + 1) + ".";
      h.push("<tr" + (i < 3 ? ' class="top3"' : "") + "><td>" + (i + 1) + "</td><td>" + pairName(p.pair, r + "pair") +
        "</td><td>" + num(r + "score", p.score) + "</td><td>" + num(r + "bombs", p.bombs) + "</td><td>" +
        num(r + "cardadv", p.cardadv) + "</td><td>" + num(r + "removal", p.removal) + "</td><td>" +
        num(r + "two_drops", p.two_drops) + "</td></tr>");
    });
    h.push("</tbody></table></div>");
    h.push("<h3>Step 4: the top three pairs</h3>");
    h.push('<p class="hint">The pair\'s cards from step 3, its gold cards and your colourless cards, graded 4+. Spacecraft are not creatures. Targets: 22-23 cards, 15+ creatures.</p>');
    h.push('<div class="tbl" role="region" aria-label="Step 4" tabindex="0"><table><thead><tr><th>Pair</th><th>Cards 4+</th><th>Creatures</th></tr></thead><tbody>');
    s.pairs.slice(0, 3).forEach(function (p, i) {
      var r = "rank." + (i + 1) + ".";
      h.push('<tr><td><span aria-hidden="true">' + CONFIG.pips[p.pair[0]] + CONFIG.pips[p.pair[1]] + "</span> " + p.pair +
        "</td><td>" + num(r + "four", p.four) + target(p.four, 22, 23) + "</td><td>" +
        num(r + "creatures", p.creatures) + target(p.creatures, 15, 0) + "</td></tr>");
    });
    h.push("</tbody></table></div>");
    h.push("<h3>Step 7: ties</h3>");
    if (s.ties.length) {
      h.push("<ul>");
      s.ties.forEach(function (t, i) {
        var k = "tie." + (i + 1) + ".";
        h.push("<li>" + num(k + "above", t.above) + " ranks above " + num(k + "below", t.below) +
          " on " + num(k + "by", t.by) + ".</li>");
      });
      h.push("</ul>");
    } else {
      h.push("<p>No two pairs tie on score.</p>");
    }
    h.push('<p>Steps 5 (splash) and 6 (build) stay by hand: see <a href="#build">section 1</a>.</p>');
    h.push('<p><button type="button" id="clear-pool">Clear pool</button></p>');
    document.getElementById("pool-body").innerHTML = h.join("\n");
    document.getElementById("pool-n").textContent = s.cards;
    document.getElementById("clear-pool").addEventListener("click", function () {
      if (!window.confirm("Clear the pool? Every count goes back to 0.")) return;
      pool = {};
      save();
      cards.forEach(updateCard);
      renderPool();
      apply();
    });
  }

  // ----------------------------------------------------------------- counters
  function updateCard(d) {
    var n = copies(d.name);
    d.ctr.querySelector(".n").textContent = n;
    d.ctr.classList.toggle("zero", n === 0);
    d.el.classList.toggle("inpool", n > 0);
  }
  cards.forEach(function (d) {
    var div = document.createElement("div");
    div.className = "ctr";
    div.innerHTML = '<button type="button" class="dec">−</button><span class="n">0</span><button type="button" class="inc">+</button>';
    div.querySelector(".dec").setAttribute("aria-label", "Remove one " + d.name);
    div.querySelector(".inc").setAttribute("aria-label", "Add one " + d.name);
    div.querySelector(".n").setAttribute("aria-label", "copies in the pool");
    d.el.appendChild(div);
    d.ctr = div;
    updateCard(d);
    // Keep the focus (and a phone's keyboard) in the search field while counting.
    div.addEventListener("mousedown", function (e) { if (e.target.closest("button")) e.preventDefault(); });
    div.addEventListener("click", function (e) {
      var b = e.target.closest("button");
      if (!b) return;
      var n = copies(d.name) + (b.classList.contains("inc") ? 1 : -1);
      if (n > 0) pool[d.name] = n; else delete pool[d.name];
      save();
      updateCard(d);
      renderPool();
      if (state.pool) apply();
    });
  });

  // ------------------------------------------------------- search and filters
  var q = document.getElementById("q");
  var shown = document.getElementById("shown");
  var none = document.getElementById("none");
  var fpanel = document.getElementById("fpanel");
  var ftoggle = document.getElementById("ftoggle");
  var controls = document.getElementById("controls");
  var list = document.getElementById("list");
  var state = { c: [], r: [], t: [], g: 0, pool: false };

  function matches(d, words) {
    for (var i = 0; i < words.length; i++) if (d.q.indexOf(words[i]) < 0) return false;
    if (state.c.length && !state.c.some(function (c) {
      if (c === "gold") return d.c.length >= 2 && d.k !== "hybrid";
      if (c === "colourless") return d.c === "";
      return d.c === c || (d.k === "hybrid" && d.c.indexOf(c) >= 0);
    })) return false;
    if (state.r.length && state.r.indexOf(d.r) < 0) return false;
    if (state.t.length && !state.t.some(function (t) { return d.t.indexOf(t) >= 0; })) return false;
    if (d.g < state.g) return false;
    if (state.pool && !copies(d.name)) return false;
    return true;
  }
  function apply() {
    var words = norm(q.value).split(" ").filter(Boolean);
    var n = 0;
    cards.forEach(function (d) {
      var ok = matches(d, words);
      d.el.hidden = !ok;
      if (ok) n++;
    });
    groups.forEach(function (g) { g.hidden = !g.querySelector(".card:not([hidden])"); });
    shown.textContent = n + " of " + cards.length;
    none.hidden = n > 0;
    var active = state.c.length + state.r.length + state.t.length + (state.g ? 1 : 0) + (state.pool ? 1 : 0);
    ftoggle.textContent = active ? "Filters (" + active + ")" : "Filters";
  }
  function toTop() {
    // After the list changes, show its first card just below the search field.
    var y = list.getBoundingClientRect().top + window.scrollY - controls.offsetHeight - 8;
    if (window.scrollY > y) window.scrollTo(0, y);
  }
  q.addEventListener("input", function () { apply(); toTop(); });
  q.addEventListener("keydown", function (e) { if (e.key === "Enter") q.blur(); });
  q.addEventListener("focus", function () { document.documentElement.classList.add("typing"); });
  q.addEventListener("blur", function () { document.documentElement.classList.remove("typing"); });
  document.getElementById("q-clear").addEventListener("mousedown", function (e) { e.preventDefault(); });
  document.getElementById("q-clear").addEventListener("click", function () {
    q.value = "";
    apply();
    q.focus();
  });
  ftoggle.addEventListener("click", function () {
    var open = fpanel.hidden;
    fpanel.hidden = !open;
    ftoggle.setAttribute("aria-expanded", String(open));
  });
  fpanel.addEventListener("click", function (e) {
    var b = e.target.closest("button");
    if (!b) return;
    if (b.id === "freset") {
      state = { c: [], r: [], t: [], g: 0, pool: false };
      fpanel.querySelectorAll(".chip").forEach(function (c) { c.setAttribute("aria-pressed", "false"); });
    } else {
      var on = b.getAttribute("aria-pressed") !== "true";
      var f = b.dataset.f, v = b.dataset.v;
      if (f === "g") {
        fpanel.querySelectorAll('.chip[data-f="g"]').forEach(function (c) { c.setAttribute("aria-pressed", "false"); });
        state.g = on ? parseFloat(v) : 0;
      } else if (f === "p") {
        state.pool = on;
      } else {
        state[f] = state[f].filter(function (x) { return x !== v; });
        if (on) state[f].push(v);
      }
      b.setAttribute("aria-pressed", String(on));
    }
    apply();
    toTop();
  });

  // ------------------------------------------------- the bar marks the section
  var links = Array.prototype.slice.call(document.querySelectorAll("#bar a"));
  var targets = links.map(function (a) { return document.getElementById(a.getAttribute("href").slice(1)); });
  var ticking = false;
  function spy() {
    ticking = false;
    var line = window.innerHeight * 0.3, current = -1;
    targets.forEach(function (t, i) { if (t && t.getBoundingClientRect().top <= line) current = i; });
    links.forEach(function (a, i) {
      if (i === current) a.setAttribute("aria-current", "location"); else a.removeAttribute("aria-current");
    });
  }
  window.addEventListener("scroll", function () { if (!ticking) { ticking = true; requestAnimationFrame(spy); } }, { passive: true });
  window.addEventListener("resize", spy);

  renderPool();
  apply();
  spy();
})();
"""


if __name__ == "__main__":
    raise SystemExit(main())
