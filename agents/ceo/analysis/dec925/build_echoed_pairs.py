"""Derive the Reality Fracture (fra) echoed-pair table from the Scryfall dump.

Method (documented so the result is auditable rather than asserted):

1.  WotC's "Collecting Reality Fracture" states 86 echoed-pair cards = 43 pairs,
    split 66 uncommon / 14 rare / 6 mythic.
2.  In the set's own collector numbering, 195-280 is a contiguous 86-card block
    that sits after the land section (175-194) and before the basics (281-289).
    Its rarity split is exactly 66 U / 14 R / 6 M.  Nothing else in the set has
    that size or that split, so the block *is* the echoed-pair cycle.
3.  Within the block the cards are colour-ordered (W 195-210, U 211-226,
    B 227-241, R 242-256, G 257-269, multicolour/colourless 270-280) and
    alphabetical within colour -- ordinary Magic set collation.
4.  Pairs are then resolved by character, constrained to equal rarity and to
    each card being used exactly once.  Three cases need more than a first-name
    match; each is forced, not guessed:
      * the "Way of the ..." cycle -- 10 cards, 2 per colour, so each colour's
        two Way cards are each other's halves;
      * renamed characters (Tinybones/Titanbones, Rescue Girl/Massacre Girl,
        Gideon's Memorial/Gideon the Oathless, Jace/Tam) -- all but Jace/Tam
        share a stem or a name; Jace/Tam is the single remaining rare pair
        after the other six rare pairs are fixed, i.e. forced by elimination.
5.  Independent corroboration: Scryfall marks 45 of these 86 cards with the
    `echoverse` or `desparked` watermark.  Under the pairing below that is
    37 pairs with one half marked, 4 with both, 2 with neither -- 37+8 = 45.
    No marked card falls outside a pair, and no pair is contradicted.
    (Codie, Ravenous Codex, #168, also carries the `echoverse` watermark but
    sits outside the block; it is Echoverse-flavoured, not a cycle card.)

Run: uv run python agents/ceo/analysis/dec925/build_echoed_pairs.py
"""

from __future__ import annotations

import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent

BLOCK_LO, BLOCK_HI = 195, 280

# Character key -> the two collector numbers.  Written out in full so the table
# is reviewable by eye; every entry is checked against the dump below.
PAIRS: list[tuple[str, int, int]] = [
    # --- mythic (3) ---
    ("Ajani", 195, 242),
    ("Chandra", 212, 244),
    ("Garruk", 229, 259),
    # --- rare (7) ---
    ("Gideon", 198, 230),
    ("Liliana", 200, 231),
    ("Lyra", 201, 217),
    ("Samut", 220, 251),
    ("Jace / Tam", 216, 276),
    ("Vraska", 277, 278),
    ("Karn", 272, 279),
    # --- uncommon (33) ---
    ("Danitha", 196, 227),
    ("Ghalta", 197, 260),
    ("Koth", 199, 248),
    ("Rescue Girl / Massacre Girl", 202, 234),
    ("Saheeli", 203, 275),
    ("Teyo", 204, 236),
    ("Thalia", 205, 214),
    ("Tomik", 206, 253),
    ("Way of the ... (W)", 207, 208),
    ("Yoshimaru", 209, 269),
    ("Yuriko", 210, 226),
    ("Arni", 211, 243),
    ("Fblthp", 213, 258),
    ("Hapatra", 215, 271),
    ("Proft", 218, 235),
    ("Ruric Thar", 219, 265),
    ("Tetsuko Umezawa", 221, 252),
    ("Traxos", 222, 280),
    ("Way of the ... (U)", 223, 224),
    ("Yargle", 225, 241),
    ("Gallia", 228, 245),
    ("Loot", 232, 262),
    ("Mabel", 233, 274),
    ("Tinybones / Titanbones", 237, 266),
    ("Way of the ... (B)", 238, 239),
    ("Winter", 240, 256),
    ("Jiang Yanggu", 246, 261),
    ("Kiora", 247, 273),
    ("Marwyn", 249, 263),
    ("Pia", 250, 264),
    ("Way of the ... (R)", 254, 255),
    ("Edgar", 257, 270),
    ("Way of the ... (G)", 267, 268),
]

SOURCE = {
    "primary": (
        "WotC, \"Collecting Reality Fracture\" (magic.wizards.com) -- states 86 "
        "echoed-pair cards = 43 pairs, 66 uncommon / 14 rare / 6 mythic, each "
        "pair a Multiverse half and an Echoverse half of one character."
    ),
    "card_data": (
        "Scryfall `set:fra unique=cards` dump, agents/ceo/analysis/dec925/"
        "fra_all_cards.json (285 cards, fetched 2026-09-23)."
    ),
    "derivation": (
        "Collector-number block 195-280 in that dump is the 86-card cycle "
        "(unique 66/14/6 rarity split); halves matched by character at equal "
        "rarity, with the Way-of-the cycle matched within colour and Jace/Tam "
        "forced by elimination. Corroborated by the echoverse/desparked "
        "watermarks (45 marked cards, all inside the block, no contradictions). "
        "See module docstring of build_echoed_pairs.py for the full argument."
    ),
    "built": "2026-09-23",
}


def num(card: dict) -> int:
    return int("".join(ch for ch in card["collector_number"] if ch.isdigit()))


def main() -> int:
    cards = json.loads((HERE / "fra_all_cards.json").read_text())
    by_num = {num(c): c for c in cards}

    problems: list[str] = []
    block = {n for n in by_num if BLOCK_LO <= n <= BLOCK_HI}
    if len(block) != 86:
        problems.append(f"block 195-280 holds {len(block)} cards, expected 86")

    seen: dict[int, str] = {}
    out = []
    for key, a, b in PAIRS:
        for n in (a, b):
            if n not in by_num:
                problems.append(f"{key}: #{n} not in the dump")
            elif n in seen:
                problems.append(f"#{n} used by both {seen[n]} and {key}")
            else:
                seen[n] = key
        ca, cb = by_num.get(a), by_num.get(b)
        if not (ca and cb):
            continue
        if ca["rarity"] != cb["rarity"]:
            problems.append(
                f"{key}: rarity mismatch {ca['name']}={ca['rarity']} "
                f"vs {cb['name']}={cb['rarity']}"
            )
        for c in (ca, cb):
            if not (BLOCK_LO <= num(c) <= BLOCK_HI):
                problems.append(f"{key}: {c['name']} #{num(c)} outside 195-280")
        marks = [c.get("watermark") for c in (ca, cb)]
        out.append(
            {
                "character": key,
                "rarity": ca["rarity"],
                "halves": [
                    {
                        "name": ca["name"],
                        "collector_number": ca["collector_number"],
                        "watermark": marks[0],
                        "colors": ca.get("colors") or [],
                    },
                    {
                        "name": cb["name"],
                        "collector_number": cb["collector_number"],
                        "watermark": marks[1],
                        "colors": cb.get("colors") or [],
                    },
                ],
            }
        )

    if len(PAIRS) != 43:
        problems.append(f"{len(PAIRS)} pairs listed, expected 43")
    if set(seen) != block:
        problems.append(
            f"paired set != block: missing {sorted(block - set(seen))}, "
            f"extra {sorted(set(seen) - block)}"
        )

    counts = {"uncommon": 0, "rare": 0, "mythic": 0}
    for p in out:
        counts[p["rarity"]] += 1
    if counts != {"uncommon": 33, "rare": 7, "mythic": 3}:
        problems.append(f"pair rarity counts {counts}, expected 33/7/3")

    if problems:
        for p in problems:
            print("FAIL:", p, file=sys.stderr)
        return 1

    paired_names = {h["name"] for p in out for h in p["halves"]}
    payload = {
        "set": "fra",
        "source": SOURCE,
        "pair_count": len(out),
        "card_count": len(paired_names),
        "rarity_pair_counts": counts,
        "unmatched_watermarked_cards": [
            c["name"]
            for c in cards
            if c.get("watermark") and c["name"] not in paired_names
        ],
        "pairs": out,
    }
    (HERE / "echoed_pairs.json").write_text(json.dumps(payload, indent=2) + "\n")
    print(f"wrote echoed_pairs.json: {len(out)} pairs, {len(paired_names)} cards")
    print("rarity:", counts)
    print("watermarked outside the cycle:", payload["unmatched_watermarked_cards"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
