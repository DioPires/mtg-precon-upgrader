#!/usr/bin/env python3
"""Cross-reference owned cards against 5 decks with strategy-aware scoring."""

import csv
import json
import re
import sys
from collections import defaultdict

DECKS = [
    {
        "id": "eternal-agony",
        "colors": {"B", "R"},
        "keywords": [
            # Core strategy: group slug, damage, punish
            "damage to each", "damage to each opponent", "deals damage", "loses life",
            "each opponent", "whenever a player", "whenever an opponent",
            "can't gain life", "prevent.*lifegain", "life loss",
            # Damage multipliers
            "double", "twice", "additional damage", "triple",
            # Punisher
            "whenever.*cast", "whenever.*spell", "enters.*damage",
            "pay.*life", "sacrifice.*or", "each upkeep",
            # Drain/burn
            "drain", "burn", "ping", "shock",
            # Value engines
            "draw a card", "card advantage", "whenever.*loses life",
            # Mana/ramp
            "add.*mana", "treasure",
        ],
        "anti_keywords": [
            "gain life", "you gain", "lifelink",  # anti-synergy with Lord of Pain strategy
            "counter target",  # wrong colors for counterspells
        ]
    },
    {
        "id": "dark-dominion",
        "colors": {"U", "B", "R"},
        "keywords": [
            # Core: amass, Army, Orc, Ring
            "amass", "army", "orc", "ring tempts",
            # Token synergy
            "+1/+1 counter", "counter on", "grows",
            # Evasion for Army
            "menace", "trample", "flying", "unblockable", "can't be blocked",
            # Reanimation
            "return.*graveyard.*battlefield", "reanimate", "from your graveyard",
            # Cast triggers
            "whenever.*cast", "whenever an opponent casts",
            # Card draw
            "draw a card", "draw cards", "draw two",
            # Removal
            "destroy target", "exile target", "deals.*damage",
            # LotR synergy
            "nazg", "sauron", "mordor",
        ],
        "anti_keywords": []
    },
    {
        "id": "mutant-multiplication",
        "colors": {"W", "U", "G"},
        "keywords": [
            # Core: tokens, counters, doubling
            "create.*token", "token", "create a", "populate",
            "double.*counter", "double.*token", "+1/+1 counter",
            "additional.*token", "twice.*many", "proliferate",
            # Token payoffs
            "for each creature", "for each token", "number of creatures",
            "whenever.*token", "whenever a creature enters",
            # Counters
            "counter on each", "put.*+1/+1", "counters on",
            # Go wide
            "creatures you control get", "anthem", "all creatures",
            "whenever a creature enters",
            # Card draw
            "draw a card", "draw cards",
            # Protection
            "hexproof", "indestructible", "protection",
        ],
        "anti_keywords": [
            "sacrifice", "destroy all",  # token armies don't want sweepers
        ]
    },
    {
        "id": "eternal-harvest",
        "colors": {"B", "G"},
        "keywords": [
            # Core: sacrifice, death, reanimation, graveyard
            "sacrifice", "sacrificed", "when.*dies", "whenever.*dies",
            "return.*graveyard.*battlefield", "reanimate",
            "from your graveyard", "graveyard.*hand",
            # Death triggers
            "experience counter", "death trigger", "leaves the battlefield",
            # Self-mill
            "mill", "put.*graveyard", "into your graveyard",
            # Sac outlets
            "sacrifice a creature", "sacrifice another",
            # ETB value
            "enters the battlefield", "enters.*you may",
            # Ramp creatures
            "search.*land", "add.*mana",
            # Card draw from death
            "draw a card", "whenever.*dies.*draw",
            # Recursion
            "return.*creature.*hand", "return target creature",
        ],
        "anti_keywords": [
            "exile.*graveyard", "exile all",  # anti-synergy with graveyard
        ]
    },
    {
        "id": "the-white-forge",
        "colors": {"W"},
        "keywords": [
            # Core: artifacts, ETB, LTB, historic, recursion
            "artifact", "historic", "whenever.*artifact",
            "enters the battlefield", "leaves the battlefield",
            # Artifact recursion
            "return.*artifact", "from your graveyard",
            # Cost reduction
            "cost.*less", "reduce.*cost", "affinity",
            # Blink/flicker
            "exile.*return", "flicker", "blink",
            # Stax/disruption
            "can't", "opponents can't", "each opponent",
            "tax", "additional cost",
            # Combo pieces
            "untap", "whenever you cast",
            # Protection
            "indestructible", "hexproof", "protection",
            # Token artifacts
            "create.*token", "treasure", "clue", "food",
        ],
        "anti_keywords": []
    },
]

COLOR_SYMBOLS = {"W", "U", "B", "R", "G"}


def parse_color_identity(mana_cost, oracle_text):
    colors = set()
    for text in [mana_cost or "", oracle_text or ""]:
        for c in COLOR_SYMBOLS:
            if "{" + c + "}" in text or "{" + c + "/" in text or "/" + c + "}" in text:
                colors.add(c)
    return colors


def fits_color_identity(card_colors, deck_colors):
    return card_colors.issubset(deck_colors)


def is_basic_land(name):
    basics = {"Plains", "Island", "Swamp", "Mountain", "Forest",
              "Snow-Covered Plains", "Snow-Covered Island", "Snow-Covered Swamp",
              "Snow-Covered Mountain", "Snow-Covered Forest", "Wastes"}
    return name in basics


def score_card(card, keywords, anti_keywords):
    """Score a card's relevance to a deck strategy based on keywords."""
    score = 0
    oracle = (card.get("oracle_text") or "").lower()
    type_line = (card.get("type_line") or "").lower()
    combined = oracle + " " + type_line

    for kw in keywords:
        try:
            if re.search(kw, combined):
                score += 1
        except re.error:
            if kw in combined:
                score += 1

    for akw in anti_keywords:
        try:
            if re.search(akw, combined):
                score -= 2
        except re.error:
            if akw in combined:
                score -= 2

    # Bonus for legendary (commander-relevant)
    if "legendary" in type_line:
        score += 0.5

    return score


def load_owned_cards(csv_path):
    cards = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get("name", "").strip()
            if not name:
                continue
            cards.append({
                "name": name,
                "quantity": int(row.get("quantity", 1)),
                "type_line": row.get("type_line", ""),
                "mana_cost": row.get("mana_cost", ""),
                "oracle_text": row.get("oracle_text", ""),
                "color_identity": parse_color_identity(
                    row.get("mana_cost", ""),
                    row.get("oracle_text", "")
                ),
            })
    return cards


def load_deck(deck_id):
    with open(f"data/commanders/{deck_id}/deck.json") as f:
        data = json.load(f)
    deck_cards = set()
    for card in data.get("decklist", []):
        deck_cards.add(card["name"])
    if data.get("commander"):
        deck_cards.add(data["commander"])
    if data.get("partner"):
        deck_cards.add(data["partner"])
    for add in data.get("adds", []) + data.get("highlights", []):
        if isinstance(add, dict) and add.get("name"):
            deck_cards.add(add["name"])
        elif isinstance(add, str):
            deck_cards.add(add)
    return data, deck_cards


def categorize(type_line):
    if not type_line:
        return "Other"
    tl = type_line.lower()
    if "land" in tl: return "Land"
    if "creature" in tl: return "Creature"
    if "planeswalker" in tl: return "Planeswalker"
    if "instant" in tl: return "Instant"
    if "sorcery" in tl: return "Sorcery"
    if "enchantment" in tl: return "Enchantment"
    if "artifact" in tl: return "Artifact"
    return "Other"


def main():
    owned = load_owned_cards("priv_data/owned_formatted.csv")
    print(f"Loaded {len(owned)} owned cards\n")

    # Collect all cards across all 5 decks
    all_deck_cards = set()
    for dcfg in DECKS:
        _, dc = load_deck(dcfg["id"])
        all_deck_cards.update(dc)

    for deck_cfg in DECKS:
        deck_data, deck_cards = load_deck(deck_cfg["id"])
        deck_colors = deck_cfg["colors"]
        keywords = deck_cfg["keywords"]
        anti_kws = deck_cfg["anti_keywords"]

        print(f"\n{'=' * 70}")
        print(f"  {deck_data['name']} — {deck_data['commander']}")
        print(f"  Colors: {', '.join(sorted(deck_colors))} | Strategy: {deck_data.get('subtitle', '')}")
        print(f"  Current decklist: {len(deck_cards)} cards")
        print(f"{'=' * 70}\n")

        # Filter candidates
        candidates = []
        for card in owned:
            if card["name"] in deck_cards:
                continue
            if is_basic_land(card["name"]):
                continue
            if not fits_color_identity(card["color_identity"], deck_colors):
                continue
            s = score_card(card, keywords, anti_kws)
            if s >= 2:  # Only show cards with meaningful strategy relevance
                candidates.append({**card, "score": s, "cat": categorize(card["type_line"])})

        # Sort by score descending
        candidates.sort(key=lambda c: (-c["score"], c["name"]))

        # Show top candidates grouped by category
        by_cat = defaultdict(list)
        for c in candidates:
            by_cat[c["cat"]].append(c)

        print(f"  High-relevance candidates (score >= 2): {len(candidates)}\n")

        cat_order = ["Creature", "Artifact", "Enchantment", "Instant", "Sorcery",
                      "Planeswalker", "Land", "Other"]

        for cat in cat_order:
            cards_in_cat = by_cat.get(cat, [])
            if not cards_in_cat:
                continue
            print(f"  --- {cat} ({len(cards_in_cat)}) ---")
            for c in cards_in_cat[:30]:  # Cap at 30 per category
                ci = "".join(sorted(c["color_identity"])) if c["color_identity"] else "C"
                in_other = " [*]" if c["name"] in (all_deck_cards - deck_cards) else ""
                oracle_preview = (c["oracle_text"] or "")[:80].replace("\n", " ")
                print(f"    [{c['score']:4.1f}] {c['name']:<38s} {c['mana_cost']:<12s} {oracle_preview}{in_other}")
            if len(cards_in_cat) > 30:
                print(f"    ... and {len(cards_in_cat) - 30} more")
            print()

        print()


if __name__ == "__main__":
    main()
