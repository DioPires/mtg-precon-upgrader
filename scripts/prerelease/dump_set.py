"""Download one Magic set from Scryfall and write the files the prerelease work needs.

    uv run python scripts/prerelease/dump_set.py --set CODE --out-dir DIR

Writes into DIR:
  CODE_all_cards.json   one entry per card (`unique=cards`)
  CODE_all_prints.json  one entry per printing (`unique=prints`)
  grading_sheet.txt     one block per non-basic card, to grade by hand
  set_facts.md          the counts you check against WotC's article

It first asks the Scryfall sets API for the code and prints the set name,
release date and card count, so a wrong code fails loudly instead of
producing a plausible-looking empty dump.

Every request goes through scripts/scryfall_api.py, which keeps Scryfall's rate
limit. A 429 ends the run: the script writes no file and exits with 1 (DEC-1076).

Use --from-dump to rewrite set_facts.md alone from the two dumps that are
already in DIR. It sends no request to Scryfall. The set's name and release
date come from the card dump (`set_name`, and the most common `released_at`);
Scryfall's `card_count`, which no dump holds, comes from the line of the
set_facts.md that it replaces ("?" without that file).

set_facts.md reads the optional, hand-written DIR/mechanics.json: a list of
{"term": ..., "pattern": ...}, one per mechanic of WotC's mechanics article.
Each pattern is a case-insensitive regular expression over the oracle text of
every face; a card counts once.
"""

from __future__ import annotations

import argparse
import collections
import json
import os
import re
import sys
import urllib.error
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import scryfall_api  # noqa: E402

from build_cheat_sheet import cheap_commons  # noqa: E402
from setlib import (  # noqa: E402
    COLOR_ORDER,
    RARITY_LETTER,
    RARITY_RANK,
    WUBRG,
    color_key,
    color_sort_key,
    faces,
    oracle_text,
)

API = "https://api.scryfall.com"


def _get_json(url: str) -> dict:
    return json.loads(scryfall_api.request(url))


def verify_set(code: str) -> dict:
    """Ask Scryfall about the set code and return its record.

    A 404 means Scryfall does not know the code. Any other HTTP status, a 3xx
    among them, is printed with its reason (DEC-1098). Both exit with 1.
    """
    try:
        info = _get_json(f"{API}/sets/{urllib.parse.quote(code)}")
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise SystemExit(f"Scryfall does not know set code {code!r} ({exc.code})") from exc
        raise SystemExit(
            f"Scryfall answered HTTP {exc.code} {exc.reason} for set code {code!r}") from exc
    print(f"set {info['code']}: {info['name']}")
    print(f"  released: {info.get('released_at')}")
    print(f"  card_count (Scryfall): {info.get('card_count')}")
    print(f"  set_type: {info.get('set_type')}")
    return info


def search_all(query: str, unique: str) -> list:
    """Page through a Scryfall search. The helper waits between pages."""
    url = (
        f"{API}/cards/search?q={urllib.parse.quote(query)}"
        f"&unique={unique}&order=set&include_extras=false"
    )
    out: list = []
    while url:
        page = _get_json(url)
        out.extend(page.get("data", []))
        url = page.get("next_page")
    return out


# ---------------------------------------------------------------- grading sheet


def _pt_suffix(card: dict) -> str:
    if card.get("power") is not None:
        return f" {card['power']}/{card['toughness']}"
    if card.get("loyalty") is not None:
        return f" L{card['loyalty']}"
    if card.get("defense") is not None:
        return f" D{card['defense']}"
    return ""


def _face_oracle(card: dict) -> str:
    """Oracle text on one line. Multi-face cards get a header per face."""
    if not card.get("card_faces"):
        return (card.get("oracle_text") or "").replace("\n", " / ")
    chunks = []
    for face in card["card_faces"]:
        head = [face.get("name", ""), face.get("mana_cost") or "", face.get("type_line", "")]
        head = [h for h in head if h]
        head.append(f"{face.get('power') or ''}/{face.get('toughness') or ''}")
        body = (face.get("oracle_text") or "").replace("\n", " / ")
        chunks.append(f"[{' '.join(head)}] {body}")
    return " // ".join(chunks)


def grading_sheet_block(card: dict) -> list:
    """The two lines the grader reads for one card."""
    header = " | ".join(
        [
            f"#{card['collector_number']} {card['name']}",
            card.get("mana_cost") or "",
            f"{RARITY_LETTER.get(card['rarity'], '?')} {color_key(card)}",
            card["type_line"] + _pt_suffix(card),
            f"WM:{card.get('watermark') or '-'}",
        ]
    )
    return [header, "   " + _face_oracle(card)]


def gradable(cards: list) -> list:
    """Every card a grader has to grade: the whole set minus basic lands."""
    return [c for c in cards if "Basic" not in c["type_line"]]


def grading_sheet(cards: list) -> str:
    """The full sheet, sorted by colour then rarity then name."""
    ordered = sorted(
        gradable(cards),
        key=lambda c: (
            color_sort_key(c.get("colors")),
            RARITY_RANK.get(c["rarity"], 9),
            c["name"],
        ),
    )
    lines: list = []
    for card in ordered:
        lines.extend(grading_sheet_block(card))
    return "\n".join(lines) + "\n"


# ------------------------------------------------------------------- set facts


def _int_number(card: dict):
    m = re.fullmatch(r"(\d+)", card["collector_number"])
    return int(m.group(1)) if m else None


def main_numbering_end(numbers: list, run: int = 10) -> int:
    """Last number of the main run.

    Sets number their special treatments well above the main sequence, leaving a
    wide empty stretch in between. The main numbering ends at the number just
    before the first stretch of `run` or more consecutive missing numbers.
    """
    if not numbers:
        return 0
    last = numbers[0]
    for current in numbers[1:]:
        if current - last - 1 >= run:
            return last
        last = current
    return last


def is_label(keyword: str, cards: list) -> bool:
    """True when each card's text prints `keyword` only directly before " — ".

    Such a keyword is a label: an ability word ("Landfall — ") or the name of
    one mode ("Kill — "), not a keyword ability. The match is whole-word and
    keeps Scryfall's spelling and case, so the rules text "stun counter" does
    not hide the mode name "Stun — ". A card whose text never prints the
    keyword makes it no label.
    """
    pattern = re.compile(r"(?<!\w)" + re.escape(keyword) + r"(?!\w)")
    for card in cards:
        text = "\n".join(face.get("oracle_text") or "" for face in faces(card))
        found = list(pattern.finditer(text))
        if not found or any(not text.startswith(" — ", m.end()) for m in found):
            return False
    return True


def split_keywords(cards: list) -> tuple:
    """(keywords, ability words, mode names): Scryfall's `keywords`, each with its card count.

    A label (is_label()) on 2 or more cards is an ability word; a label on 1
    card is a mode name. Every other keyword stays a keyword.
    """
    holders: dict = collections.defaultdict(list)
    for card in cards:
        for keyword in card.get("keywords", []):
            holders[keyword].append(card)
    keywords, ability_words, mode_names = {}, {}, {}
    for keyword, held in holders.items():
        if not is_label(keyword, held):
            keywords[keyword] = len(held)
        elif len(held) >= 2:
            ability_words[keyword] = len(held)
        else:
            mode_names[keyword] = len(held)
    return keywords, ability_words, mode_names


def load_mechanics(out_dir: str):
    """DIR/mechanics.json, the set's mechanics written by hand; None without the file."""
    path = os.path.join(out_dir, "mechanics.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        mechanics = json.load(fh)
    if not isinstance(mechanics, list) or not all(
        isinstance(m, dict) and isinstance(m.get("term"), str) and isinstance(m.get("pattern"), str)
        for m in mechanics
    ):
        raise SystemExit(f'{path}: expected a list of {{"term": "...", "pattern": "..."}}')
    return mechanics


def mechanic_rows(cards: list, mechanics: list) -> list:
    """One table row per mechanic: term, cards, and the cards by rarity (C, U, R, M)."""
    rows = []
    for mechanic in mechanics:
        pattern = re.compile(mechanic["pattern"], re.IGNORECASE)
        hits = collections.Counter(
            card["rarity"]
            for card in cards
            if any(pattern.search(face.get("oracle_text") or "") for face in faces(card))
        )
        by_rarity = " | ".join(str(hits[r]) for r in ("common", "uncommon", "rare", "mythic"))
        rows.append(f"| {mechanic['term']} | {sum(hits.values())} | {by_rarity} |")
    return rows


def set_facts(cards: list, prints: list, info: dict, mechanics: list | None = None) -> str:
    """The fact sheet: counts to check against WotC's article, plus a few censuses.

    `mechanics` is DIR/mechanics.json (load_mechanics()); without it the
    "Set mechanics" table is absent.
    """
    main = gradable(cards)
    out = [
        f"# {info.get('name', '?')} ({info.get('code', '?').upper()}) — set facts",
        "",
        "Generated by `scripts/prerelease/dump_set.py`. Every number here comes from the "
        "Scryfall dump in this folder. Check the rarity totals against WotC's "
        '"Collecting" article before trusting the collation config.',
        "",
        f"- Released: {info.get('released_at', '?')}",
        f"- Scryfall `card_count` for the set: {info.get('card_count', '?')}",
        f"- Cards in this dump (`unique=cards`): {len(cards)} ({len(main)} excluding basic lands)",
        f"- Printings in this dump (`unique=prints`): {len(prints)}",
        "",
        "## Counts by rarity",
        "",
        "| Rarity | Cards |",
        "|---|---:|",
    ]
    rarities = collections.Counter(c["rarity"] for c in main)
    for rarity in sorted(rarities, key=lambda r: RARITY_RANK.get(r, 9)):
        out.append(f"| {rarity} | {rarities[rarity]} |")

    out += [
        "",
        "## Counts by colour",
        "",
        "Colour here is Scryfall's `colors` field. Gold cards count once, under their pair.",
        "",
        "| Colour | Common | Uncommon | Rare | Mythic | Total |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    by_color: dict = collections.defaultdict(collections.Counter)
    for card in main:
        by_color[color_key(card)][card["rarity"]] += 1
    for key in sorted(by_color, key=lambda k: color_sort_key([] if k == "C" else list(k))):
        counts = by_color[key]
        total = sum(counts.values())
        out.append(
            f"| {key} | {counts['common']} | {counts['uncommon']} | "
            f"{counts['rare']} | {counts['mythic']} | {total} |"
        )

    if mechanics is not None:
        out += [
            "",
            "## Set mechanics (from `mechanics.json`)",
            "",
            "Written by hand from WotC's mechanics article. Each pattern is a case-insensitive "
            "regular expression over the oracle text of every face; a card counts once.",
            "",
            "| Term | Cards | C | U | R | M |",
            "|---|---:|---:|---:|---:|---:|",
        ]
        out += mechanic_rows(main, mechanics)

    keywords, ability_words, mode_names = split_keywords(main)
    out += [
        "",
        "## Keywords (Scryfall `keywords` field)",
        "",
        'A label that the text prints directly before " — " is an ability word or a mode '
        'name, under "Ability words" below.',
        "",
        "| Keyword | Cards |",
        "|---|---:|",
    ]
    for keyword, n in sorted(keywords.items(), key=lambda kv: (-kv[1], kv[0])):
        out.append(f"| {keyword} | {n} |")

    out += [
        "",
        "## Ability words",
        "",
        'Labels of the `keywords` field that the text prints directly before " — ", '
        "on 2 or more cards.",
        "",
        "| Ability word | Cards |",
        "|---|---:|",
    ]
    for keyword, n in sorted(ability_words.items(), key=lambda kv: (-kv[1], kv[0])):
        out.append(f"| {keyword} | {n} |")
    if mode_names:
        out += [
            "",
            f'{len(mode_names)} more labels stand before " — " on one card each; they name '
            "that card's modes or abilities and are not mechanics, so no table here counts them.",
        ]

    out += [
        "",
        "## Mechanics in oracle text (case-insensitive)",
        "",
        "Counted over all faces, lower-cased. Reminder text writes keyword actions in "
        "lower case, so a case-sensitive count undercounts them. The terms are the "
        "keywords and the ability words above.",
        "",
        "| Term | Cards |",
        "|---|---:|",
    ]
    texts = [oracle_text(c) for c in main]
    for keyword in sorted({**keywords, **ability_words}):
        n = sum(1 for t in texts if keyword.lower() in t)
        out.append(f"| {keyword} | {n} |")

    out += ["", "## Creature toughness census", ""]
    toughness = []
    for card in main:
        raw = card.get("toughness")
        if raw is None and card.get("card_faces"):
            raw = card["card_faces"][0].get("toughness")
        if raw is not None and re.fullmatch(r"\d+", str(raw)):
            toughness.append(int(raw))
    if toughness:
        out += [
            f"{len(toughness)} creatures with a fixed toughness. "
            "Read this against the set's cheap damage spells.",
            "",
            "| Toughness | Cards | Share |",
            "|---|---:|---:|",
        ]
        for limit in (2, 3, 4, 5):
            n = sum(1 for t in toughness if t <= limit)
            out.append(f"| <= {limit} | {n} | {100 * n / len(toughness):.0f}% |")
        # The cheat sheet's figure, with the sheet's census rule (front face,
        # creatures only): 2 damage against the cheap commons.
        killed, cheap = cheap_commons(main)
        if cheap:
            out.append(
                f"| <= 2, common creatures with mana value 3 or less | {killed} of {cheap} | "
                f"{100 * killed / cheap:.0f}% |"
            )
    else:
        out.append("No creatures with a fixed toughness in the dump.")

    out += ["", "## Collector-number gaps", ""]
    # Basics are numbered too, so count them here even though they are not graded.
    numbers = sorted({n for n in (_int_number(c) for c in cards) if n is not None})
    prints_by_number: dict = collections.defaultdict(list)
    for card in prints:
        n = _int_number(card)
        if n is not None:
            prints_by_number[n].append(card["name"])
    if numbers:
        end = main_numbering_end(numbers)
        present = set(numbers)
        gaps = [n for n in range(numbers[0], end + 1) if n not in present]
        above = [n for n in numbers if n > end]
        out.append(
            f"The main numbering runs #{numbers[0]} to #{end}; {len(gaps)} numbers in that "
            f"range are missing, and {len(above)} cards are numbered above it."
        )
        out.append("")
        out.append(
            "A gap is almost always a showcase-first printing: `unique=cards` keeps one "
            "printing per card, and when the special-treatment version is the one it keeps, "
            "the main-set number looks absent while the card sits above the main numbering. "
            "The prints dump resolves each gap below. Treat a gap with no printing at all as "
            "a real hole and re-dump."
        )
        if gaps:
            out += ["", "| Missing # | Card at that number in the prints dump |", "|---|---|"]
            for n in gaps:
                names = sorted(set(prints_by_number.get(n, [])))
                out.append(f"| {n} | {', '.join(names) if names else '(nothing — check this)'} |")
    else:
        out.append("No numeric collector numbers in the dump.")

    out += ["", "## Watermarks", "", "| Watermark | Cards |", "|---|---:|"]
    watermarks = collections.Counter(c.get("watermark") or "(none)" for c in main)
    for watermark, n in sorted(watermarks.items(), key=lambda kv: (-kv[1], kv[0])):
        out.append(f"| {watermark} | {n} |")

    out += [
        "",
        "## Two-colour uncommons per pair",
        "",
        "The signposts for the ten pairs. An empty pair means the set has no gold "
        "uncommon there.",
        "",
        "| Pair | Uncommons |",
        "|---|---:|",
    ]
    gold = collections.Counter(
        color_key(c) for c in main if c["rarity"] == "uncommon" and len(c.get("colors") or []) == 2
    )
    for i, first in enumerate(WUBRG):
        for second in WUBRG[i + 1 :]:
            key = "".join(sorted(first + second))
            label = "".join(sorted(first + second, key=lambda c: COLOR_ORDER[c]))
            out.append(f"| {label} | {gold.get(key, 0)} |")

    return "\n".join(out) + "\n"


# ------------------------------------------------------------------------ main


def write_outputs(out_dir: str, code: str, cards: list, prints: list, info: dict) -> None:
    os.makedirs(out_dir, exist_ok=True)
    cards_file = os.path.join(out_dir, f"{code}_all_cards.json")
    prints_file = os.path.join(out_dir, f"{code}_all_prints.json")
    with open(cards_file, "w", encoding="utf-8") as fh:
        json.dump(cards, fh, indent=1)
    with open(prints_file, "w", encoding="utf-8") as fh:
        json.dump(prints, fh, indent=1)
    sheet_file = os.path.join(out_dir, "grading_sheet.txt")
    with open(sheet_file, "w", encoding="utf-8") as fh:
        fh.write(grading_sheet(cards))
    facts_file = write_set_facts(out_dir, cards, prints, info)
    for path in (cards_file, prints_file, sheet_file, facts_file):
        print("wrote", path)


def write_set_facts(out_dir: str, cards: list, prints: list, info: dict) -> str:
    facts_file = os.path.join(out_dir, "set_facts.md")
    text = set_facts(cards, prints, info, load_mechanics(out_dir))
    with open(facts_file, "w", encoding="utf-8") as fh:
        fh.write(text)
    return facts_file


CARD_COUNT_LINE = re.compile(r"^- Scryfall `card_count` for the set: (.+)$", re.MULTILINE)


def info_from_dump(out_dir: str, code: str, cards: list) -> dict:
    """The set record that --from-dump uses in place of the sets API.

    Name: the cards' `set_name`. Release date: the most common `released_at`
    of the cards. `card_count`: no dump holds it, so it comes from the
    set_facts.md that the run replaces, which recorded the API's figure; "?"
    without that file.
    """
    card_count = "?"
    facts_file = os.path.join(out_dir, "set_facts.md")
    if os.path.exists(facts_file):
        with open(facts_file, encoding="utf-8") as fh:
            m = CARD_COUNT_LINE.search(fh.read())
        if m:
            card_count = m.group(1)
    released = collections.Counter(c.get("released_at") for c in cards if c.get("released_at"))
    return {
        "code": code,
        "name": cards[0].get("set_name", code) if cards else code,
        "released_at": released.most_common(1)[0][0] if released else "?",
        "card_count": card_count,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--set", required=True, help="Scryfall set code, e.g. fra")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument(
        "--from-dump",
        action="store_true",
        help="rewrite set_facts.md alone from the dumps already in --out-dir; no network",
    )
    args = ap.parse_args()
    code = args.set.lower()

    if args.from_dump:
        with open(os.path.join(args.out_dir, f"{code}_all_cards.json"), encoding="utf-8") as fh:
            cards = json.load(fh)
        with open(os.path.join(args.out_dir, f"{code}_all_prints.json"), encoding="utf-8") as fh:
            prints = json.load(fh)
        info = info_from_dump(args.out_dir, code, cards)
        print("wrote", write_set_facts(args.out_dir, cards, prints, info))
        return 0

    try:
        info = verify_set(code)
        cards = search_all(f"set:{code}", "cards")
        prints = search_all(f"set:{code}", "prints")
    except scryfall_api.ScryfallRateLimited as e:
        print(f"\n{e}\nNo file written.")
        return 1
    print(f"  dumped {len(cards)} cards, {len(prints)} printings")

    write_outputs(args.out_dir, code, cards, prints, info)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
