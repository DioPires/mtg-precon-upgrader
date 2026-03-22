#!/usr/bin/env python3
"""Generate recommendations.json for each commander deck.

Reads combo data, simulation baselines, card metadata, and game changers
to produce scored upgrade recommendations per deck.

Usage:
    python scripts/generate_recommendations.py [--deck DECK_ID] [--combos-dir DIR]
"""

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
COMMANDERS_DIR = DATA_DIR / "commanders"
METADATA_FILE = DATA_DIR / "card-metadata.json"
GAME_CHANGERS_FILE = DATA_DIR / "game-changers.json"
OWNED_FILE = PROJECT_ROOT / "priv_data" / "owned_formatted.csv"

METHODOLOGY_VERSION = "v1"

# Health score component weights (from simulation export)
HEALTH_WEIGHTS = {
    "manaReliability": 0.30,
    "threatDeployment": 0.20,
    "interactionDensity": 0.20,
    "comboConsistency": 0.15,
    "commanderIndependence": 0.15,
}

# Card type keywords that help with each health component
HEALTH_TYPE_MAP = {
    "manaReliability": ["Land", "Artifact"],  # mana rocks, lands
    "threatDeployment": ["Creature", "Planeswalker"],
    "interactionDensity": ["Instant", "Sorcery"],
    "comboConsistency": [],  # combo pieces are identified by combo data
    "commanderIndependence": ["Creature", "Planeswalker", "Enchantment"],
}

HEALTH_ORACLE_MAP = {
    "manaReliability": [r"\badd\b.*\bmana\b", r"\bsearch.*\bland\b"],
    "threatDeployment": [r"\bcreate.*\btoken\b", r"\bdeal.*\bdamage\b"],
    "interactionDensity": [
        r"\bdestroy\b", r"\bexile\b", r"\bcounter target\b",
        r"\breturn.*\bhand\b", r"\bsacrifice\b",
    ],
    "comboConsistency": [r"\buntap\b", r"\binfinite\b", r"\bloop\b"],
    "commanderIndependence": [],
}


def load_json(path: Path) -> dict | list | None:
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def load_owned_cards() -> set[str]:
    if not OWNED_FILE.exists():
        return set()
    owned = set()
    with open(OWNED_FILE) as f:
        for line in f:
            line = line.strip()
            match = re.match(r"^\d+x\s+(.+)$", line)
            if match:
                owned.add(match.group(1).strip())
    return owned


def load_game_changers() -> set[str]:
    data = load_json(GAME_CHANGERS_FILE)
    if data and "cards" in data:
        return set(data["cards"])
    return set()


def load_card_metadata() -> dict[str, dict]:
    data = load_json(METADATA_FILE)
    return data if data else {}


def get_deck_card_names(deck: dict) -> set[str]:
    names = set()
    for card in deck.get("decklist", []):
        names.add(card["name"])
    if deck.get("commander"):
        names.add(deck["commander"])
    if deck.get("partner"):
        names.add(deck["partner"])
    return names


def get_weakest_health_components(sim_data: dict) -> list[tuple[str, float]]:
    health = sim_data.get("deckHealthScore", {})
    components = health.get("components", {})
    if not components:
        return []
    sorted_comps = sorted(components.items(), key=lambda x: x[1])
    return sorted_comps


def card_addresses_component(card_meta: dict, component: str) -> bool:
    type_line = (card_meta.get("type_line") or "").lower()
    oracle = (card_meta.get("oracle_text") or "").lower()

    for type_kw in HEALTH_TYPE_MAP.get(component, []):
        if type_kw.lower() in type_line:
            return True

    for pattern in HEALTH_ORACLE_MAP.get(component, []):
        if re.search(pattern, oracle, re.IGNORECASE):
            return True

    return False


def score_source_diversity(sources: list[dict]) -> int:
    n = len(sources)
    if n >= 3:
        return 30
    if n >= 2:
        return 20
    if n >= 1:
        return 10
    return 0


def score_combo_enablement(combo: dict) -> int:
    missing = combo.get("missing_cards", [])
    missing_templates = combo.get("missing_templates", [])
    total_missing = len(missing) + len(missing_templates)

    # Number of cards in the combo
    cards_in_combo = len(combo.get("cards", []))

    if total_missing == 1:
        # Near-miss: 1 card away
        if cards_in_combo <= 2:
            return 25
        elif cards_in_combo <= 3:
            return 20
        else:
            return 15
    elif total_missing == 2:
        # 2 cards away: half points
        if cards_in_combo <= 3:
            return 12
        else:
            return 8
    return 0


def score_health_gap(card_meta: dict, weak_components: list[tuple[str, float]]) -> int:
    if not weak_components or not card_meta:
        return 0

    weakest_name, weakest_score = weak_components[0]
    if card_addresses_component(card_meta, weakest_name):
        return 20

    # Check second weakest
    if len(weak_components) > 1:
        second_name, second_score = weak_components[1]
        if second_score < 70 and card_addresses_component(card_meta, second_name):
            return 10

    return 0


def score_bracket_fit(card_name: str, game_changers: set[str], deck: dict) -> int:
    is_gc = card_name in game_changers
    if not is_gc:
        return 15
    bracket = deck.get("bracket", "4")
    if bracket == "5":
        return 10
    return 0


def score_swap_viability(
    card_meta: dict, deck: dict, metadata: dict[str, dict],
    deck_synergy_cards: set[str]
) -> tuple[int, str | None]:
    if not card_meta:
        return 0, None

    add_type = (card_meta.get("type_line") or "").lower()
    add_cmc = card_meta.get("cmc", 0) or 0
    deck_cards = deck.get("decklist", [])

    candidates = []

    for card in deck_cards:
        card_name = card["name"]
        if card_name == deck.get("commander") or card_name == deck.get("partner"):
            continue

        cmeta = metadata.get(card_name, {})
        card_type = (cmeta.get("type_line") or card.get("type", "")).lower()

        # Skip cards in synergies (high-value)
        if card_name.lower() in deck_synergy_cards:
            continue

        type_match = False
        for t in ["creature", "instant", "sorcery", "artifact", "enchantment"]:
            if t in add_type and t in card_type:
                type_match = True
                break

        card_cmc = cmeta.get("cmc", 0) or 0
        cmc_distance = abs(card_cmc - add_cmc)

        candidates.append((card_name, type_match, cmc_distance))

    if not candidates:
        return 0, None

    # Sort: type match first, then closest CMC
    candidates.sort(key=lambda x: (not x[1], x[2]))
    best = candidates[0]
    score = 10 if best[1] else 5
    return score, best[0]


def get_synergy_card_set(deck: dict) -> set[str]:
    cards = set()
    for syn in deck.get("synergies", []):
        for card in syn.get("cards", []):
            cards.add(card.lower())
    return cards


def extract_combo_info(entry: dict) -> tuple[dict, list[str], list[str]]:
    """Extract combo details from either included or almostIncluded format.

    almostIncluded: { combo: {...}, missing_cards: [...], missing_templates: [...] }
    included: { id, url, cards: [...], produces: [...], ... }
    """
    if "combo" in entry:
        combo = entry["combo"]
        missing = entry.get("missing_cards", [])
        missing_templates = entry.get("missing_templates", [])
    else:
        combo = entry
        missing = []
        missing_templates = []
    return combo, missing, missing_templates


def get_combo_card_names(combo: dict) -> list[str]:
    cards = combo.get("cards", [])
    names = []
    for c in cards:
        if isinstance(c, dict):
            names.append(c.get("name", ""))
        elif isinstance(c, str):
            names.append(c)
    return [n for n in names if n]


def get_combo_result(combo: dict) -> str:
    produces = combo.get("produces", [])
    if isinstance(produces, list):
        return ", ".join(str(p) for p in produces[:3])
    return str(produces) if produces else ""


def process_combo_recommendations(
    combo_data: dict,
    deck: dict,
    metadata: dict[str, dict],
    game_changers: set[str],
    weak_components: list[tuple[str, float]],
) -> list[dict]:
    recs = []
    deck_cards = get_deck_card_names(deck)
    deck_cards_lower = {c.lower() for c in deck_cards}
    synergy_cards = get_synergy_card_set(deck)
    seen_cards: dict[str, list] = {}  # card_name -> list of combo entries

    for entry in combo_data.get("almostIncluded", []):
        combo, missing, missing_templates = extract_combo_info(entry)
        combo_card_names = get_combo_card_names(combo)

        for card_name in missing:
            if card_name.lower() in deck_cards_lower:
                continue
            if card_name not in seen_cards:
                seen_cards[card_name] = []
            seen_cards[card_name].append((combo, missing, missing_templates))

    for card_name, combos in seen_cards.items():
        card_meta = metadata.get(card_name, {})

        # Build sources — one per combo
        sources = []
        combo_details_list = []
        for combo, missing, missing_templates in combos:
            combo_id = combo.get("id", "")
            combo_url = combo.get("url", "")
            if not combo_url and combo_id:
                combo_url = f"https://commanderspellbook.com/combo/{combo_id}/"

            combo_card_names = get_combo_card_names(combo)
            in_deck = [c for c in combo_card_names if c.lower() in deck_cards_lower]

            sources.append({
                "type": "commanderspellbook",
                "name": "Commander Spellbook",
                "url": combo_url,
                "detail": f"Near-miss ({len(missing) + len(missing_templates)} away)",
            })
            combo_details_list.append({
                "comboId": combo_id,
                "comboUrl": combo_url,
                "cardsInDeck": in_deck,
                "totalMissing": len(missing) + len(missing_templates),
                "result": get_combo_result(combo),
            })

        # Use the best combo (fewest missing) for scoring
        best_combo_idx = min(
            range(len(combos)),
            key=lambda i: len(combos[i][1]) + len(combos[i][2]),
        )
        best_combo, best_missing, best_mt = combos[best_combo_idx]
        best_combo_cards = get_combo_card_names(best_combo)

        # Score
        s_source = score_source_diversity(sources)
        s_combo = score_combo_enablement({
            "missing_cards": best_missing,
            "missing_templates": best_mt,
            "cards": best_combo_cards,
        })
        s_health = score_health_gap(card_meta, weak_components)
        s_bracket = score_bracket_fit(card_name, game_changers, deck)
        s_swap, swap_candidate = score_swap_viability(
            card_meta, deck, metadata, synergy_cards
        )

        total = s_source + s_combo + s_health + s_bracket + s_swap

        in_deck_cards = [c for c in best_combo_cards if c.lower() in deck_cards_lower]

        rec = {
            "card": card_name,
            "score": total,
            "category": "combo-enabler",
            "rationale": f"Enables combo with {', '.join(in_deck_cards[:3])}",
            "sources": sources[:3],  # Keep top 3 sources
            "comboDetails": combo_details_list[0],
            "impact": {
                "cmcDelta": (card_meta.get("cmc", 0) or 0),
                "gameChangerAdded": card_name in game_changers,
                "colors": card_meta.get("colors", []),
                "typeLine": card_meta.get("type_line", ""),
            },
            "scoring": {
                "sourceDiversity": s_source,
                "comboEnablement": s_combo,
                "healthGapFill": s_health,
                "bracketFit": s_bracket,
                "swapViability": s_swap,
            },
        }

        if len(combo_details_list) > 1:
            rec["additionalCombos"] = combo_details_list[1:3]

        if swap_candidate:
            rec["swapSuggestion"] = {
                "cut": swap_candidate,
                "reason": "Lower synergy density card of compatible type",
            }

        recs.append(rec)

    return recs


def generate_recommendations(deck_id: str, combos_dir: Path) -> dict | None:
    deck_path = COMMANDERS_DIR / deck_id / "deck.json"
    sim_path = COMMANDERS_DIR / deck_id / "simulation.json"
    combo_path = combos_dir / f"combos-{deck_id}.json"

    deck = load_json(deck_path)
    if not deck:
        print(f"  Skipping {deck_id}: no deck.json", file=sys.stderr)
        return None

    sim_data = load_json(sim_path) or {}
    combo_data = load_json(combo_path) or {"included": [], "almostIncluded": []}
    metadata = load_card_metadata()
    game_changers = load_game_changers()
    owned = load_owned_cards()

    # Health baselines
    health = sim_data.get("deckHealthScore", {})
    weak_components = get_weakest_health_components(sim_data)

    # Generate recommendations from combos
    recs = process_combo_recommendations(
        combo_data, deck, metadata, game_changers, weak_components
    )

    # Already deduplicated in process_combo_recommendations
    merged_recs = sorted(recs, key=lambda r: r["score"], reverse=True)

    # Rank
    for i, rec in enumerate(merged_recs):
        rec["rank"] = i + 1

    # Tag owned cards
    for rec in merged_recs:
        rec["owned"] = rec["card"] in owned

    # Build output
    output = {
        "deckId": deck_id,
        "generatedAt": str(date.today()),
        "methodology": METHODOLOGY_VERSION,
        "healthBaseline": {
            "score": health.get("score", 0),
            "grade": health.get("grade", "?"),
            "components": health.get("components", {}),
            "weakestComponent": weak_components[0][0] if weak_components else None,
        },
        "includedCombos": len(combo_data.get("included", [])),
        "nearMissCombos": len(combo_data.get("almostIncluded", [])),
        "recommendations": merged_recs[:25],  # Top 25
        "totalCandidates": len(merged_recs),
    }

    return output


def main():
    parser = argparse.ArgumentParser(description="Generate deck recommendations")
    parser.add_argument("--deck", help="Single deck ID to process")
    parser.add_argument(
        "--combos-dir", default="/tmp",
        help="Directory containing combos-{id}.json files",
    )
    args = parser.parse_args()

    combos_dir = Path(args.combos_dir)

    if args.deck:
        deck_ids = [args.deck]
    else:
        deck_ids = sorted(
            p.parent.name for p in COMMANDERS_DIR.glob("*/deck.json")
        )

    results = {}
    for deck_id in deck_ids:
        print(f"Processing {deck_id}...")
        result = generate_recommendations(deck_id, combos_dir)
        if result:
            out_path = COMMANDERS_DIR / deck_id / "recommendations.json"
            with open(out_path, "w") as f:
                json.dump(result, f, indent=2)
            n_recs = len(result["recommendations"])
            print(f"  {n_recs} recommendations written to {out_path}")
            results[deck_id] = n_recs
        else:
            print(f"  No output for {deck_id}")

    print(f"\nDone. Generated recommendations for {len(results)} deck(s).")
    for deck_id, count in results.items():
        print(f"  {deck_id}: {count} recommendations")


if __name__ == "__main__":
    main()
