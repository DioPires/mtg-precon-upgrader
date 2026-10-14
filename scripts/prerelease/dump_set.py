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

Use --from-dump to rebuild grading_sheet.txt and set_facts.md from dumps that
are already on disk, without touching the network.
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

from setlib import (  # noqa: E402
    COLOR_ORDER,
    RARITY_LETTER,
    RARITY_RANK,
    WUBRG,
    color_key,
    color_sort_key,
    oracle_text,
)

API = "https://api.scryfall.com"


def _get_json(url: str) -> dict:
    return json.loads(scryfall_api.request(url))


def verify_set(code: str) -> dict:
    """Ask Scryfall about the set code and return its record."""
    try:
        info = _get_json(f"{API}/sets/{urllib.parse.quote(code)}")
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"Scryfall does not know set code {code!r} ({exc.code})") from exc
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


def set_facts(cards: list, prints: list, info: dict) -> str:
    """The fact sheet: counts to check against WotC's article, plus a few censuses."""
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

    out += [
        "",
        "## Keywords (Scryfall `keywords` field)",
        "",
        "| Keyword | Cards |",
        "|---|---:|",
    ]
    keywords = collections.Counter(k for c in main for k in c.get("keywords", []))
    for keyword, n in sorted(keywords.items(), key=lambda kv: (-kv[1], kv[0])):
        out.append(f"| {keyword} | {n} |")

    out += [
        "",
        "## Mechanics in oracle text (case-insensitive)",
        "",
        "Counted over all faces, lower-cased. Reminder text writes keyword actions in "
        "lower case, so a case-sensitive count undercounts them.",
        "",
        "| Term | Cards |",
        "|---|---:|",
    ]
    texts = [oracle_text(c) for c in main]
    for keyword in sorted(keywords):
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
    facts_file = os.path.join(out_dir, "set_facts.md")
    with open(facts_file, "w", encoding="utf-8") as fh:
        fh.write(set_facts(cards, prints, info))
    for path in (cards_file, prints_file, sheet_file, facts_file):
        print("wrote", path)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--set", required=True, help="Scryfall set code, e.g. fra")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument(
        "--from-dump",
        action="store_true",
        help="rebuild grading_sheet.txt and set_facts.md from dumps already in --out-dir",
    )
    args = ap.parse_args()
    code = args.set.lower()

    if args.from_dump:
        with open(os.path.join(args.out_dir, f"{code}_all_cards.json"), encoding="utf-8") as fh:
            cards = json.load(fh)
        prints_path = os.path.join(args.out_dir, f"{code}_all_prints.json")
        prints = []
        if os.path.exists(prints_path):
            with open(prints_path, encoding="utf-8") as fh:
                prints = json.load(fh)
        info = {
            "code": code,
            "name": cards[0].get("set_name", code) if cards else code,
            "released_at": cards[0].get("released_at") if cards else None,
            "card_count": len(cards),
        }
    else:
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
