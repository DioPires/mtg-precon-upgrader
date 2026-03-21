#!/usr/bin/env python3
"""Export mana simulation results as JSON for all commander decks.

Imports each simulation module under a namespace (they share function names),
runs the simulations, and writes structured JSON to
data/commanders/{id}/simulation.json.
"""

import json
import math
import os
import re
import statistics
import sys
import traceback
from collections import Counter
from datetime import date
from pathlib import Path

# Add scripts dir to path for imports
SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

import mana_simulation_titan_convergence as sim_titan
import mana_simulation_eternal_agony as sim_rakdos
import mana_simulation_dark_dominion as sim_grixis
import mana_simulation_eternal_harvest as sim_golgari
import mana_simulation_phyrexian_perfection as sim_phyrexian
import mana_simulation_compleated_dominion as sim_compleated
import mana_simulation_mutant_multiplication as sim_wubrg
import mana_simulation_azure_dominion as sim_mono_blue
import mana_simulation_genesis_protocol as sim_azorius
import mana_simulation_planar_decree as sim_jeskai
import mana_simulation_forge_and_fury as sim_jund

PROJECT_ROOT = SCRIPTS_DIR.parent
METADATA_FILE = PROJECT_ROOT / "data" / "card-metadata.json"

NUM_GAMES = 100_000
NUM_TURNS = 10

DRAW_PATTERNS = (
    r"\bdraws?\b",
    r"\binvestigate\b",
    r"\bsurveil\b",
    r"\block\b",
    r"\bconnive\b",
)

INTERACTION_PATTERNS = (
    r"\bcounter target\b",
    r"\bdestroy target\b",
    r"\bexile target\b",
    r"\breturn target\b",
    r"\bfight target\b",
    r"\bdeals? \d+ damage to target\b",
    r"\btarget player sacrifices\b",
    r"\beach opponent sacrifices\b",
    r"\bprevent all combat damage\b",
    r"\bcan\'t attack\b",
    r"\bcan\'t block\b",
)

THREAT_EXCLUDED_CATEGORY_TERMS = (
    "land", "mana", "ramp", "draw", "interaction", "removal", "tutor",
)

THREAT_TYPE_MARKERS = ("Creature", "Planeswalker", "Battle")
THREAT_ORACLE_PATTERNS = (
    r"\byou win the game\b",
    r"\bextra turn\b",
    r"\bdouble\b.*\btoken\b",
    r"\bwhenever .* loses life\b",
    r"\bwhenever .* create\b",
    r"\bproliferate\b",
)

COMMANDER_ENGINE_PATTERNS = (
    r"\bdraws?\b",
    r"\bcreate\b",
    r"\bproliferate\b",
    r"\badd\b",
    r"\bsacrifice\b",
    r"\breturn\b.*\bfrom your graveyard\b",
)

KEY_COMBOS = {
    "azure-dominion": [
        {
            "name": "Isochron Reversal",
            "pieces": ["Isochron Scepter", "Dramatic Reversal"],
            "requiresCommander": False,
            "description": "2-card infinite untap line once nonland mana is online.",
        }
    ],
    "compleated-dominion": [
        {
            "name": "Magistrate Engine",
            "pieces": ["Magistrate's Scepter", "Contagion Engine", "Tekuthal, Inquiry Dominus"],
            "requiresCommander": False,
            "description": "Charge-counter extra-turn engine.",
        }
    ],
    "dark-dominion": [
        {
            "name": "Worldgorger Loop",
            "pieces": ["Animate Dead", "Worldgorger Dragon"],
            "requiresCommander": False,
            "description": "Infinite mana reanimation loop.",
        }
    ],
    "eternal-agony": [
        {
            "name": "Hidetsugu Lethal",
            "pieces": ["Heartless Hidetsugu", "Twinflame Tyrant"],
            "requiresCommander": False,
            "description": "Damage doubler turns Hidetsugu activations lethal.",
        }
    ],
    "eternal-harvest": [
        {
            "name": "Ballista Undying",
            "pieces": ["Walking Ballista", "Mikaeus, the Unhallowed"],
            "requiresCommander": False,
            "description": "Repeatable undying damage loop with any sacrifice outlet.",
        }
    ],
    "forge-and-fury": [
        {
            "name": "Skeleton Treasury",
            "pieces": ["Pitiless Plunderer", "Warren Soultrader", "Reassembling Skeleton"],
            "requiresCommander": False,
            "description": "3-card treasure and death-trigger loop.",
        }
    ],
    "genesis-protocol": [
        {
            "name": "Narset Wheel Lock",
            "pieces": ["Narset, Parter of Veils", "Windfall"],
            "requiresCommander": False,
            "description": "Hand denial package.",
        }
    ],
    "mutant-multiplication": [
        {
            "name": "Broodscale Loop",
            "pieces": ["Basking Broodscale", "Rosie Cotton of South Lane"],
            "requiresCommander": False,
            "description": "Counter-driven infinite token engine.",
        }
    ],
    "phyrexian-perfection": [
        {
            "name": "Atraxa Tide Engine",
            "pieces": ["Tekuthal, Inquiry Dominus", "Inexorable Tide"],
            "requiresCommander": True,
            "description": "Atraxa plus doubled proliferate snowballs poison/counters.",
        }
    ],
    "planar-decree": [
        {
            "name": "Puzzle Lock",
            "pieces": ["Teferi's Puzzle Box", "Narset, Parter of Veils"],
            "requiresCommander": False,
            "description": "Opponents spin hands into one-card turns.",
        }
    ],
    "titan-convergence": [
        {
            "name": "Rings Basalt",
            "pieces": ["Rings of Brighthearth", "Basalt Monolith"],
            "requiresCommander": False,
            "description": "2-card infinite colorless mana engine.",
        }
    ],
}


# --- Helpers ---


def pct(count: int, total: int) -> float:
    """Percentage rounded to 1 decimal."""
    return round(count / total * 100, 1) if total > 0 else 0.0


def r1(val: float) -> float:
    """Round to 1 decimal."""
    return round(val, 1)


def compute_avg_cmc(decklist: list[str], metadata: dict) -> float:
    """Average CMC of non-land cards."""
    cmcs = []
    for name in decklist:
        meta = metadata.get(name, {})
        if "Land" not in meta.get("type_line", ""):
            cmc = meta.get("cmc", 0)
            if isinstance(cmc, (int, float)):
                cmcs.append(cmc)
    return statistics.mean(cmcs) if cmcs else 0.0


def mana_stats(data: list) -> dict:
    """Compute median/p25/p75/mean from a list of values."""
    if not data:
        return {"median": 0.0, "p25": 0.0, "p75": 0.0, "mean": 0.0}
    q = statistics.quantiles(data, n=4)
    return {
        "median": r1(statistics.median(data)),
        "p25": r1(q[0]),
        "p75": r1(q[2]),
        "mean": r1(statistics.mean(data)),
    }


def cumulative_pct(values: list, threshold: int, total: int) -> float:
    """Percentage of values <= threshold."""
    count = sum(1 for v in values if v <= threshold)
    return pct(count, total)


def median_or_null(values: list):
    """Median of a list, or None if empty."""
    if not values:
        return None
    return r1(statistics.median(values))


def median_turn_from_cumulative(by_turn: dict) -> int | None:
    """First turn where cumulative castable % >= 50."""
    for t in range(1, NUM_TURNS + 1):
        if by_turn.get(str(t), 0) >= 50.0:
            return t
    return None


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    """Clamp numeric score into [low, high]."""
    return max(low, min(high, value))


def weighted_average(weighted_values: list[tuple[float, float]]) -> float:
    """Weighted average helper."""
    total_weight = sum(weight for _, weight in weighted_values)
    if total_weight <= 0:
        return 0.0
    return sum(value * weight for value, weight in weighted_values) / total_weight


def pct_to_score(value: float) -> float:
    """Normalize percentage-like values into score space."""
    return clamp(value)


def cards_seen_by_turn(turn: int) -> int:
    """Cards seen by end of turn on the play in a Commander game."""
    return min(99, 6 + turn)


def hypergeom_at_least(deck_size: int, hits_in_deck: int, cards_seen: int,
                       hits_needed: int) -> float:
    """Probability of seeing at least hits_needed successes in cards_seen draws."""
    if hits_needed <= 0:
        return 1.0
    if hits_in_deck < hits_needed or cards_seen <= 0:
        return 0.0

    max_hits = min(hits_in_deck, cards_seen)
    total = math.comb(deck_size, cards_seen)
    success = 0
    for hits in range(hits_needed, max_hits + 1):
        miss_count = cards_seen - hits
        if deck_size - hits_in_deck < miss_count:
            continue
        success += math.comb(hits_in_deck, hits) * math.comb(deck_size - hits_in_deck, miss_count)
    return success / total if total else 0.0


def parse_generic_mana_cost(mana_cost: str) -> dict:
    """Parse WUBRG mana costs from Scryfall-style mana_cost strings."""
    result = {
        "generic": 0,
        "W": 0,
        "U": 0,
        "B": 0,
        "R": 0,
        "G": 0,
        "total": 0,
        "X": False,
    }
    if not mana_cost:
        return result
    if "//" in mana_cost:
        mana_cost = mana_cost.split("//")[0].strip()

    for symbol in re.findall(r"\{([^}]+)\}", mana_cost):
        if symbol == "X":
            result["X"] = True
        elif symbol.isdigit():
            result["generic"] += int(symbol)
        elif symbol in ("W", "U", "B", "R", "G"):
            result[symbol] += 1
    result["total"] = result["generic"] + sum(result[color] for color in "WUBRG")
    return result


def ordered_unique(cards: list[str]) -> list[str]:
    """Keep first-seen order while removing duplicates."""
    seen = set()
    ordered = []
    for card in cards:
        if card in seen:
            continue
        seen.add(card)
        ordered.append(card)
    return ordered


def build_card_category_lookup(deck_data: dict) -> dict[str, set[str]]:
    """Map card name to guide category names for deck-guided threat inference."""
    lookup: dict[str, set[str]] = {}
    guide = deck_data.get("guideContent", {})
    for category in guide.get("deckCategories", []):
        for card in category.get("cards", []):
            lookup.setdefault(card, set()).add(category.get("name", ""))
    return lookup


def text_matches(text: str, patterns: tuple[str, ...]) -> bool:
    """Regex convenience helper."""
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)


def is_draw_card(meta: dict) -> bool:
    """Heuristic card-draw classifier based on Scryfall oracle text."""
    oracle = meta.get("oracle_text", "")
    return text_matches(oracle, DRAW_PATTERNS)


def is_interaction_card(meta: dict, category_names: set[str]) -> bool:
    """Removal / stack interaction / combat denial classifier."""
    oracle = meta.get("oracle_text", "")
    category_blob = " ".join(category_names).lower()
    if any(term in category_blob for term in ("interaction", "removal", "counter", "stax", "disruption", "lock")):
        return True
    if "Board wipe" in oracle:
        return True
    return text_matches(oracle, INTERACTION_PATTERNS)


def is_threat_card(name: str, meta: dict, category_names: set[str]) -> bool:
    """Threat classifier leaning on curated guide categories first, text second."""
    if category_names:
        if not any(term in cat.lower() for cat in category_names for term in THREAT_EXCLUDED_CATEGORY_TERMS):
            return True

    type_line = meta.get("type_line", "")
    cmc = meta.get("cmc", 0) or 0
    oracle = meta.get("oracle_text", "")

    if any(marker in type_line for marker in THREAT_TYPE_MARKERS) and cmc >= 3:
        return True

    if any(marker in type_line for marker in ("Artifact", "Enchantment")) and cmc >= 4:
        return text_matches(oracle, THREAT_ORACLE_PATTERNS)

    return False


def classify_functional_cards(decklist: list[str], deck_data: dict, metadata: dict) -> dict:
    """Classify threats, draw, and interaction cards from deck data + metadata."""
    category_lookup = build_card_category_lookup(deck_data)
    threats = []
    draw = []
    interaction = []

    for name in decklist:
        meta = metadata.get(name, {})
        if not meta or "Land" in meta.get("type_line", ""):
            continue

        category_names = category_lookup.get(name, set())
        if is_threat_card(name, meta, category_names):
            threats.append(name)
        if is_draw_card(meta):
            draw.append(name)
        if is_interaction_card(meta, category_names):
            interaction.append(name)

    return {
        "threats": threats,
        "draw": draw,
        "interaction": interaction,
    }


def produced_colors_for_card(name: str, meta: dict, commander_colors: list[str]) -> set[str]:
    """Best-effort color production / fixing derived from oracle text."""
    oracle = meta.get("oracle_text", "")
    lower = oracle.lower()
    colors = set()

    if "add one mana of any color in your commander's color identity" in lower:
        return set(commander_colors)
    if "add one mana of any color" in lower:
        return set(commander_colors)

    add_clauses = re.findall(r"Add([^.\n]+)", oracle)
    for clause in add_clauses:
        colors.update(symbol for symbol in re.findall(r"\{([WUBRG])\}", clause))

    # Fetchlands / land tutors that represent true source access in deck construction.
    if "type_line" in meta and "Land" in meta.get("type_line", "") and "search your library for a" in lower:
        for subtype, color in {
            "plains": "W",
            "island": "U",
            "swamp": "B",
            "mountain": "R",
            "forest": "G",
        }.items():
            if subtype in lower:
                colors.add(color)

    return colors


def is_static_source_card(meta: dict) -> bool:
    """Cards that remain on board and contribute mana after resolution."""
    type_line = meta.get("type_line", "")
    return "Land" in type_line or ("Artifact" in type_line or "Creature" in type_line)


def source_count_for_color(decklist: list[str], metadata: dict, commander_colors: list[str],
                           color: str, deadline_turn: int) -> int:
    """Count sources for a color by a given turn using static board sources only."""
    count = 0
    for name in decklist:
        meta = metadata.get(name, {})
        if not meta or not is_static_source_card(meta):
            continue

        produces = produced_colors_for_card(name, meta, commander_colors)
        if color not in produces:
            continue

        type_line = meta.get("type_line", "")
        cmc = int(meta.get("cmc", 0) or 0)
        if "Land" in type_line:
            count += 1
        elif cmc <= max(1, deadline_turn - 1):
            count += 1
    return count


def compute_probability_curve(card_pool: list[str]) -> dict[str, float]:
    """Probability of seeing at least one card from pool by each turn."""
    hit_count = len(card_pool)
    curve = {}
    for turn in range(1, NUM_TURNS + 1):
        curve[str(turn)] = r1(hypergeom_at_least(99, hit_count, cards_seen_by_turn(turn), 1) * 100)
    return curve


def compute_threat_density(threat_cards: list[str], metadata: dict, result: dict) -> dict:
    """Deployable threat density curve using median simulated mana as CMC cutoff."""
    by_turn = {}
    for turn in range(1, NUM_TURNS + 1):
        mana_limit = result["manaByTurn"][str(turn)]["median"]
        eligible = [
            name for name in threat_cards
            if (metadata.get(name, {}).get("cmc", 0) or 0) <= mana_limit
        ]
        by_turn[str(turn)] = r1(hypergeom_at_least(99, len(eligible), cards_seen_by_turn(turn), 1) * 100)
    return {
        "count": len(threat_cards),
        "examples": ordered_unique(threat_cards)[:8],
        "byTurn": by_turn,
        "medianDeploymentTurn": median_turn_from_cumulative(by_turn),
    }


def compute_reliability_curve(cards: list[str], label: str) -> dict:
    """Shared schema for draw / interaction availability curves."""
    by_turn = compute_probability_curve(cards)
    return {
        "count": len(cards),
        "examples": ordered_unique(cards)[:8],
        "byTurn": by_turn,
        "medianTurn": median_turn_from_cumulative(by_turn),
        "label": label,
    }


def compute_combo_assembly(deck_id: str, decklist: list[str], commander_name: str) -> dict:
    """Probability curves for curated combo packages per deck."""
    deck_cards = set(decklist)
    combos = []
    best_by_turn = {str(turn): 0.0 for turn in range(1, NUM_TURNS + 1)}

    for combo in KEY_COMBOS.get(deck_id, []):
        non_commander_pieces = [piece for piece in combo["pieces"] if piece != commander_name]
        present_pieces = [piece for piece in non_commander_pieces if piece in deck_cards]
        if len(present_pieces) != len(non_commander_pieces):
            continue

        needed = len(present_pieces)
        by_turn = {}
        for turn in range(1, NUM_TURNS + 1):
            pct_value = r1(hypergeom_at_least(99, needed, cards_seen_by_turn(turn), needed) * 100)
            by_turn[str(turn)] = pct_value
            best_by_turn[str(turn)] = max(best_by_turn[str(turn)], pct_value)

        combos.append({
            "name": combo["name"],
            "pieces": combo["pieces"],
            "requiresCommander": combo["requiresCommander"],
            "description": combo["description"],
            "byTurn": by_turn,
            "medianAssemblyTurn": median_turn_from_cumulative(by_turn),
        })

    fastest = None
    if combos:
        fastest = min(
            combos,
            key=lambda combo: combo["medianAssemblyTurn"] if combo["medianAssemblyTurn"] is not None else 999,
        )["name"]

    return {
        "combos": combos,
        "bestByTurn": best_by_turn,
        "fastestCombo": fastest,
        "medianAssemblyTurn": median_turn_from_cumulative(best_by_turn),
    }


def compute_colored_source_adequacy(decklist: list[str], metadata: dict,
                                    commander_name: str, commander_colors: list[str]) -> dict:
    """Hypergeometric colored-source adequacy by spell deadline."""
    if not commander_colors:
        return None

    score_rows = []
    by_color = {}
    candidate_spells = decklist + ([commander_name] if commander_name else [])

    for color in commander_colors:
        rows = []
        for name in candidate_spells:
            meta = metadata.get(name, {})
            if not meta or "Land" in meta.get("type_line", ""):
                continue
            pips = parse_generic_mana_cost(meta.get("mana_cost", ""))
            needed = pips.get(color, 0)
            if needed <= 0:
                continue

            deadline_turn = max(1, min(NUM_TURNS, int(meta.get("cmc", 0) or pips["total"] or 1)))
            sources = source_count_for_color(decklist, metadata, commander_colors, color, deadline_turn)
            probability = hypergeom_at_least(99, sources, cards_seen_by_turn(deadline_turn), needed)
            row = {
                "card": name,
                "pips": needed,
                "deadlineTurn": deadline_turn,
                "sources": sources,
                "probability": r1(probability * 100),
            }
            rows.append(row)
            score_rows.append((probability * 100, needed))

        rows.sort(key=lambda row: (row["probability"], row["deadlineTurn"], row["card"]))
        turn3 = source_count_for_color(decklist, metadata, commander_colors, color, 3)
        turn4 = source_count_for_color(decklist, metadata, commander_colors, color, 4)
        turn5 = source_count_for_color(decklist, metadata, commander_colors, color, 5)
        by_color[color] = {
            "turn3Sources": turn3,
            "turn4Sources": turn4,
            "turn5Sources": turn5,
            "weightedAdequacy": r1(weighted_average([(row["probability"], row["pips"]) for row in rows])),
            "weakSpells": rows[:5],
        }

    overall = r1(weighted_average(score_rows))
    return {
        "overallScore": overall,
        "byColor": by_color,
        "method": "Hypergeometric source adequacy using cards seen by spell CMC turn and source counts from lands plus low-CMC mana permanents.",
    }


def compute_commander_dependency(deck_data: dict, commander_name: str, commander_meta: dict,
                                 combo_assembly: dict, threat_density: dict,
                                 draw_reliability: dict, interaction_availability: dict) -> dict:
    """Heuristic commander dependency. Higher means deck leans harder on commander access."""
    synergies = deck_data.get("synergies", [])
    synergy_hits = sum(1 for synergy in synergies if commander_name in synergy.get("cards", []))
    synergy_share = (synergy_hits / len(synergies) * 100) if synergies else 0.0
    combo_requires_commander = any(combo.get("requiresCommander") for combo in combo_assembly.get("combos", []))
    commander_engine = 100.0 if text_matches(commander_meta.get("oracle_text", ""), COMMANDER_ENGINE_PATTERNS) else 0.0
    self_sufficiency = weighted_average([
        (threat_density["byTurn"].get("4", 0.0), 0.35),
        (draw_reliability["byTurn"].get("4", 0.0), 0.35),
        (interaction_availability["byTurn"].get("3", 0.0), 0.30),
    ])
    dependency = clamp(
        0.45 * synergy_share +
        0.25 * (100.0 if combo_requires_commander else 0.0) +
        0.20 * commander_engine +
        0.10 * (100.0 - self_sufficiency)
    )
    if dependency >= 70:
        label = "high"
    elif dependency >= 45:
        label = "moderate"
    else:
        label = "low"
    return {
        "score": r1(dependency),
        "label": label,
        "synergyShare": r1(synergy_share),
        "comboRequiresCommander": combo_requires_commander,
        "selfSufficiency": r1(self_sufficiency),
    }


def compute_deck_health_score(result: dict, threat_density: dict, draw_reliability: dict,
                              interaction_availability: dict, combo_assembly: dict,
                              color_adequacy: dict, commander_dependency: dict) -> dict:
    """Composite deck health score from mana, pressure, interaction, combo, and commander independence."""
    mana_reliability = weighted_average([
        (pct_to_score(result["commanderTiming"]["byTurn"].get(str(result["commanderTiming"]["cmc"]), 0.0)), 0.35),
        (pct_to_score(color_adequacy["overallScore"] if color_adequacy else 100.0), 0.30),
        (pct_to_score((100.0 - (result["mulliganStats"]["paidMulligan"] * 12.0))
                      - (result["mulliganStats"]["freeMulligan"] * 3.0)), 0.20),
        (pct_to_score((result["manaByTurn"]["4"]["mean"] / max(1.0, result["deckComposition"]["avgCmc"])) * 100), 0.15),
    ])
    threat_score = weighted_average([
        (threat_density["byTurn"].get("4", 0.0), 0.45),
        (threat_density["byTurn"].get("5", 0.0), 0.35),
        (threat_density["byTurn"].get("6", 0.0), 0.20),
    ])
    interaction_score = weighted_average([
        (interaction_availability["byTurn"].get("2", 0.0), 0.30),
        (interaction_availability["byTurn"].get("3", 0.0), 0.45),
        (interaction_availability["byTurn"].get("4", 0.0), 0.25),
    ])
    combo_score = weighted_average([
        (combo_assembly["bestByTurn"].get("5", 0.0), 0.40),
        (combo_assembly["bestByTurn"].get("6", 0.0), 0.60),
    ]) if combo_assembly["combos"] else 50.0
    commander_independence = 100.0 - commander_dependency["score"]

    overall = weighted_average([
        (mana_reliability, 0.30),
        (threat_score, 0.20),
        (interaction_score, 0.20),
        (combo_score, 0.15),
        (commander_independence, 0.15),
    ])

    if overall >= 75:
        grade = "A"
    elif overall >= 65:
        grade = "B"
    elif overall >= 55:
        grade = "C"
    else:
        grade = "D"

    return {
        "score": r1(overall),
        "grade": grade,
        "components": {
            "manaReliability": r1(mana_reliability),
            "threatDeployment": r1(threat_score),
            "interactionDensity": r1(interaction_score),
            "comboConsistency": r1(combo_score),
            "commanderIndependence": r1(commander_independence),
        },
        "methodology": "Weighted composite: mana 30%, threats 20%, interaction 20%, combo 15%, commander independence 15%.",
    }


def enrich_result(result: dict, deck_id: str, deck_data: dict, decklist: list[str],
                  metadata: dict, commander_name: str, colors: list[str]) -> dict:
    """Attach enhanced reliability metrics and deck health score."""
    functional = classify_functional_cards(decklist, deck_data, metadata)
    threat_density = compute_threat_density(functional["threats"], metadata, result)
    draw_reliability = compute_reliability_curve(functional["draw"], "Card draw")
    interaction_availability = compute_reliability_curve(functional["interaction"], "Interaction")
    combo_assembly = compute_combo_assembly(deck_id, decklist, commander_name)
    color_adequacy = compute_colored_source_adequacy(decklist, metadata, commander_name, colors)
    commander_dependency = compute_commander_dependency(
        deck_data=deck_data,
        commander_name=commander_name,
        commander_meta=metadata.get(commander_name, {}),
        combo_assembly=combo_assembly,
        threat_density=threat_density,
        draw_reliability=draw_reliability,
        interaction_availability=interaction_availability,
    )

    result["reliabilityMetrics"] = {
        "threatDensity": threat_density,
        "drawEngineReliability": draw_reliability,
        "interactionAvailability": interaction_availability,
        "comboAssembly": combo_assembly,
        "coloredSourceAdequacy": color_adequacy,
        "commanderDependency": commander_dependency,
    }
    result["deckHealthScore"] = compute_deck_health_score(
        result=result,
        threat_density=threat_density,
        draw_reliability=draw_reliability,
        interaction_availability=interaction_availability,
        combo_assembly=combo_assembly,
        color_adequacy=color_adequacy,
        commander_dependency=commander_dependency,
    )
    return result


def derive_assessment(result: dict) -> dict:
    """Derive qualitative assessments from simulation data."""
    # Mana adequacy: compare median mana at T4-5 to avg CMC
    avg_cmc = result["deckComposition"]["avgCmc"]
    t4_median = result["manaByTurn"]["4"]["median"]
    t5_median = result["manaByTurn"]["5"]["median"]

    if t5_median >= avg_cmc + 2:
        mana_adequacy = "strong"
    elif t4_median >= avg_cmc:
        mana_adequacy = "adequate"
    else:
        mana_adequacy = "light"

    # Mulligan verdict
    paid_pct = result["mulliganStats"]["paidMulligan"]
    if paid_pct < 3:
        mulligan_verdict = "excellent"
    elif paid_pct < 5:
        mulligan_verdict = "acceptable"
    else:
        mulligan_verdict = "concerning"

    # Commander timing
    # For 4+ color commanders, the simultaneous multi-pip requirement makes
    # casting structurally harder than equivalent CMC with fewer colors.
    # Allow +1 turn grace for 4+ color identities.
    cmd = result["commanderTiming"]
    cmd_cmc = cmd["cmc"]
    median_turn = cmd["medianTurn"]
    cb = result.get("colorBalance") or {}
    num_colors = len(cb.get("colors", []))
    curve_grace = 2 if num_colors >= 4 else 0
    if median_turn is None:
        cmd_timing = "unreliable"
    elif median_turn <= cmd_cmc - 1:
        cmd_timing = "ahead of curve"
    elif median_turn <= cmd_cmc + curve_grace:
        cmd_timing = "on curve"
    else:
        cmd_timing = "behind curve"

    return {
        "manaAdequacy": mana_adequacy,
        "mulliganVerdict": mulligan_verdict,
        "commanderTiming": cmd_timing,
    }


def run_parallel(run_chunk_fn, merge_fn, decklist, metadata, num_games):
    """Run simulation with multiprocessing, return merged stats."""
    import multiprocessing
    n_workers = os.cpu_count() or 4
    chunk_size = num_games // n_workers
    remainder = num_games % n_workers
    chunks = [chunk_size + (1 if i < remainder else 0) for i in range(n_workers)]

    with multiprocessing.Pool(n_workers) as pool:
        results = pool.map(run_chunk_fn, [(decklist, metadata, n) for n in chunks])
    return merge_fn(results)


def validate_output(result: dict, deck_id: str) -> bool:
    """Validate required top-level keys and manaByTurn entries."""
    required_keys = [
        "metadata", "deckComposition", "manaByTurn", "mulliganStats",
        "openingHand", "commanderTiming", "colorBalance", "curveEfficiency",
        "specialMetrics", "assessment", "reliabilityMetrics", "deckHealthScore",
    ]
    for key in required_keys:
        if key not in result:
            print(f"  VALIDATION FAIL [{deck_id}]: missing key '{key}'")
            return False

    for t in range(1, NUM_TURNS + 1):
        if str(t) not in result["manaByTurn"]:
            print(f"  VALIDATION FAIL [{deck_id}]: manaByTurn missing turn {t}")
            return False

    return True


# --- Deck-specific exporters ---


def export_titan(metadata: dict) -> dict:
    """Export Titan Convergence (colorless Eldrazi) simulation."""
    deck_file = PROJECT_ROOT / "data" / "commanders" / "titan-convergence" / "deck.json"
    with open(deck_file) as f:
        deck_data = json.load(f)

    decklist = sim_titan.build_decklist(deck_data)
    classified = sim_titan.classify_cards(decklist, metadata)
    avg_cmc = compute_avg_cmc(decklist, metadata)

    print(f"  Running {NUM_GAMES:,} games for Titan Convergence...")
    stats = run_parallel(sim_titan._run_chunk, sim_titan.merge_stats,
                         decklist, metadata, NUM_GAMES)
    total = NUM_GAMES

    # manaByTurn
    mana_by_turn = {}
    for t in range(1, NUM_TURNS + 1):
        mana_by_turn[str(t)] = mana_stats(stats["mana_by_turn"][t])

    # mulliganStats
    mull = stats["mulligan_attempts"]
    mulligan_stats = {
        "keptFirst": pct(mull.get(0, 0), total),
        "freeMulligan": pct(mull.get(1, 0), total),
        "paidMulligan": pct(mull.get(2, 0), total),
    }

    # openingHand
    land_dist = {}
    for n in range(8):
        count = stats["hand_land_counts"].get(n, 0)
        if count > 0:
            land_dist[str(n)] = pct(count, total)
    opening_hand = {"landDistribution": land_dist}

    # commanderTiming (Zhulodok = 6 CMC, cumulative % by turn)
    cmd_by_turn = {}
    for t in range(1, NUM_TURNS + 1):
        cmd_by_turn[str(t)] = cumulative_pct(stats["zhulodok_turns"], t, total)

    commander_timing = {
        "name": "Zhulodok, Void Gorger",
        "cmc": 6,
        "byTurn": cmd_by_turn,
        "medianTurn": median_turn_from_cumulative(cmd_by_turn),
    }

    # curveEfficiency
    castable_by_turn = {}
    for t in range(1, NUM_TURNS + 1):
        castable_by_turn[str(t)] = pct(stats["castable_spell_by_turn"][t], total)

    curve_efficiency = {
        "castableByTurn": castable_by_turn,
        "curveOutRate": pct(stats["curve_out_games"], total),
    }

    # specialMetrics: cascadeReadiness
    cascade_by_turn = {}
    for t in range(1, NUM_TURNS + 1):
        cascade_by_turn[str(t)] = cumulative_pct(stats["cascade_ready_turns"], t, total)

    special_metrics = {
        "cascadeReadiness": {
            "byTurn": cascade_by_turn,
            "medianTurn": median_or_null(stats["cascade_ready_turns"]),
        },
        "etbTapped": None,
    }

    result = {
        "metadata": {
            "numGames": NUM_GAMES,
            "numTurns": NUM_TURNS,
            "generatedAt": str(date.today()),
        },
        "deckComposition": {
            "totalCards": len(decklist),
            "lands": len(classified["lands"]),
            "rocks": len(classified["rocks"]),
            "spells": len(classified["spells"]) + len(classified.get("amplifiers", [])),
            "avgCmc": r1(avg_cmc),
        },
        "manaByTurn": mana_by_turn,
        "mulliganStats": mulligan_stats,
        "openingHand": opening_hand,
        "commanderTiming": commander_timing,
        "colorBalance": None,
        "curveEfficiency": curve_efficiency,
        "specialMetrics": special_metrics,
        "assessment": {},
    }
    result["assessment"] = derive_assessment(result)
    return enrich_result(
        result=result,
        deck_id="titan-convergence",
        deck_data=deck_data,
        decklist=decklist,
        metadata=metadata,
        commander_name="Zhulodok, Void Gorger",
        colors=[],
    )


def _export_colored(sim_module, deck_id: str, deck_name: str,
                    commander_name: str, commander_cmc: int,
                    colors: list[str], metadata: dict) -> dict:
    """Export a colored (Rakdos/Grixis) simulation."""
    deck_file = PROJECT_ROOT / "data" / "commanders" / deck_id / "deck.json"
    with open(deck_file) as f:
        deck_data = json.load(f)

    decklist = sim_module.build_decklist(deck_data)
    classified = sim_module.classify_cards(decklist, metadata)
    avg_cmc = compute_avg_cmc(decklist, metadata)

    print(f"  Running {NUM_GAMES:,} games for {deck_name}...")
    stats = run_parallel(sim_module._run_chunk, sim_module.merge_stats,
                         decklist, metadata, NUM_GAMES)
    total = NUM_GAMES

    # manaByTurn
    mana_by_turn = {}
    for t in range(1, NUM_TURNS + 1):
        mana_by_turn[str(t)] = mana_stats(stats["mana_by_turn"][t])

    # mulliganStats
    mull = stats["mulligan_attempts"]
    mulligan_stats = {
        "keptFirst": pct(mull.get(0, 0), total),
        "freeMulligan": pct(mull.get(1, 0), total),
        "paidMulligan": pct(mull.get(2, 0), total),
    }

    # openingHand
    land_dist = {}
    for n in range(8):
        count = stats["hand_land_counts"].get(n, 0)
        if count > 0:
            land_dist[str(n)] = pct(count, total)
    opening_hand = {"landDistribution": land_dist}

    # commanderTiming (cumulative from commander_by_turn)
    cmd_by_turn = {}
    for t in range(1, NUM_TURNS + 1):
        cmd_by_turn[str(t)] = pct(stats["commander_by_turn"][t], total)

    commander_timing = {
        "name": commander_name,
        "cmc": commander_cmc,
        "byTurn": cmd_by_turn,
        "medianTurn": median_turn_from_cumulative(cmd_by_turn),
    }

    # colorBalance
    color_keys = {c: c.lower() for c in colors}
    color_by_turn = {}
    for t in range(1, NUM_TURNS + 1):
        turn_data = {}
        for color in colors:
            key = f"{color_keys[color]}_by_turn"
            data = stats[key][t]
            turn_data[color] = {
                "median": r1(statistics.median(data)),
                "mean": r1(statistics.mean(data)),
            }
        color_by_turn[str(t)] = turn_data

    color_screw_by_turn = {}
    for t in range(1, NUM_TURNS + 1):
        turn_screw = {}
        for color in colors:
            key = f"zero_{color_keys[color]}_by_turn"
            turn_screw[color] = pct(stats[key][t], total)
        color_screw_by_turn[str(t)] = turn_screw

    color_balance = {
        "colors": colors,
        "byTurn": color_by_turn,
        "colorScrewByTurn": color_screw_by_turn,
    }

    # curveEfficiency
    castable_by_turn = {}
    for t in range(1, NUM_TURNS + 1):
        castable_by_turn[str(t)] = pct(stats["castable_spell_by_turn"][t], total)

    curve_efficiency = {
        "castableByTurn": castable_by_turn,
        "curveOutRate": pct(stats["curve_out_games"], total),
    }

    # specialMetrics: etbTapped
    etb_tapped = {}
    for t in stats["tapped_land_turns"]:
        etb_tapped[str(t)] = pct(stats["tapped_land_turns"][t], total)

    special_metrics = {
        "cascadeReadiness": None,
        "etbTapped": etb_tapped,
    }

    result = {
        "metadata": {
            "numGames": NUM_GAMES,
            "numTurns": NUM_TURNS,
            "generatedAt": str(date.today()),
        },
        "deckComposition": {
            "totalCards": len(decklist),
            "lands": len(classified["lands"]),
            "rocks": len(classified["rocks"]),
            "spells": len(classified["spells"]),
            "avgCmc": r1(avg_cmc),
        },
        "manaByTurn": mana_by_turn,
        "mulliganStats": mulligan_stats,
        "openingHand": opening_hand,
        "commanderTiming": commander_timing,
        "colorBalance": color_balance,
        "curveEfficiency": curve_efficiency,
        "specialMetrics": special_metrics,
        "assessment": {},
    }
    result["assessment"] = derive_assessment(result)
    return enrich_result(
        result=result,
        deck_id=deck_id,
        deck_data=deck_data,
        decklist=decklist,
        metadata=metadata,
        commander_name=commander_name,
        colors=colors,
    )


def export_rakdos(metadata: dict) -> dict:
    """Export Eternal Agony (Rakdos) simulation."""
    return _export_colored(
        sim_module=sim_rakdos,
        deck_id="eternal-agony",
        deck_name="Eternal Agony",
        commander_name="The Lord of Pain",
        commander_cmc=5,
        colors=["B", "R"],
        metadata=metadata,
    )


def export_grixis(metadata: dict) -> dict:
    """Export Dark Dominion (Grixis) simulation."""
    return _export_colored(
        sim_module=sim_grixis,
        deck_id="dark-dominion",
        deck_name="Dark Dominion",
        commander_name="Sauron, the Dark Lord",
        commander_cmc=6,
        colors=["U", "B", "R"],
        metadata=metadata,
    )


def export_golgari(metadata: dict) -> dict:
    """Export Eternal Harvest (Golgari) simulation."""
    return _export_colored(
        sim_module=sim_golgari,
        deck_id="eternal-harvest",
        deck_name="Eternal Harvest",
        commander_name="Meren of Clan Nel Toth",
        commander_cmc=4,
        colors=["B", "G"],
        metadata=metadata,
    )


def export_phyrexian_perfection(metadata: dict) -> dict:
    """Export Phyrexian Perfection (Atraxa B3) simulation."""
    return _export_colored(
        sim_module=sim_phyrexian,
        deck_id="phyrexian-perfection",
        deck_name="Phyrexian Perfection",
        commander_name="Atraxa, Praetors' Voice",
        commander_cmc=4,
        colors=["W", "U", "B", "G"],
        metadata=metadata,
    )


def export_compleated_dominion(metadata: dict) -> dict:
    """Export Compleated Dominion (Atraxa B4) simulation."""
    return _export_colored(
        sim_module=sim_compleated,
        deck_id="compleated-dominion",
        deck_name="Compleated Dominion",
        commander_name="Atraxa, Praetors' Voice",
        commander_cmc=4,
        colors=["W", "U", "B", "G"],
        metadata=metadata,
    )


def export_wubrg(metadata: dict) -> dict:
    """Export Mutant Multiplication (WUBRG) simulation."""
    return _export_colored(
        sim_module=sim_wubrg,
        deck_id="mutant-multiplication",
        deck_name="Mutant Multiplication",
        commander_name="Donatello, the Brains",
        commander_cmc=3,
        colors=["W", "U", "B", "R", "G"],
        metadata=metadata,
    )


def export_mono_blue(metadata: dict) -> dict:
    """Export Azure Dominion (mono-blue Urza) simulation."""
    return _export_colored(
        sim_module=sim_mono_blue,
        deck_id="azure-dominion",
        deck_name="Azure Dominion",
        commander_name="Urza, Lord High Artificer",
        commander_cmc=4,
        colors=["U"],
        metadata=metadata,
    )


def export_forge(metadata: dict) -> dict:
    """Export Forge & Fury (Jund Korvold) simulation."""
    return _export_colored(
        sim_module=sim_jund,
        deck_id="forge-and-fury",
        deck_name="Forge & Fury",
        commander_name="Korvold, Fae-Cursed King",
        commander_cmc=5,
        colors=["B", "R", "G"],
        metadata=metadata,
    )


def export_azorius(metadata: dict) -> dict:
    """Export Genesis Protocol (Azorius Shorikai) simulation."""
    result = _export_colored(
        sim_module=sim_azorius,
        deck_id="genesis-protocol",
        deck_name="Genesis Protocol",
        commander_name="Shorikai, Genesis Engine",
        commander_cmc=4,
        colors=["W", "U"],
        metadata=metadata,
    )

    # Re-run to get Shorikai-specific stats (crew readiness, isochron threshold)
    # The _export_colored call already ran the sim; re-extract special metrics.
    deck_file = PROJECT_ROOT / "data" / "commanders" / "genesis-protocol" / "deck.json"
    with open(deck_file) as f:
        deck_data = json.load(f)
    decklist = sim_azorius.build_decklist(deck_data)

    print(f"  Running {NUM_GAMES:,} games for Genesis Protocol (Shorikai-specific metrics)...")
    stats = run_parallel(sim_azorius._run_chunk, sim_azorius.merge_stats,
                         decklist, metadata, NUM_GAMES)
    total = NUM_GAMES

    # Add Shorikai-specific special metrics
    crew_by_turn = {}
    for t in range(1, NUM_TURNS + 1):
        crew_by_turn[str(t)] = pct(stats["crew_ready_by_turn"][t], total)

    isochron_by_turn = {}
    for t in range(1, NUM_TURNS + 1):
        isochron_by_turn[str(t)] = pct(stats["isochron_ready_by_turn"][t], total)

    result["specialMetrics"]["crewReadiness"] = {
        "description": "3+ cumulative Shorikai activations (enough Pilots to crew)",
        "byTurn": crew_by_turn,
    }
    result["specialMetrics"]["isochronComboThreshold"] = {
        "description": "3+ mana from nonland permanents (Isochron + Dramatic Reversal goes infinite)",
        "byTurn": isochron_by_turn,
    }

    return result


def export_jeskai(metadata: dict) -> dict:
    """Export Planar Decree (Jeskai Commodore Guff) simulation."""
    return _export_colored(
        sim_module=sim_jeskai,
        deck_id="planar-decree",
        deck_name="Planar Decree",
        commander_name="Commodore Guff",
        commander_cmc=4,
        colors=["W", "U", "R"],
        metadata=metadata,
    )


# --- Main ---


DECKS = [
    ("titan-convergence", "Titan Convergence", export_titan),
    ("eternal-agony", "Eternal Agony", export_rakdos),
    ("dark-dominion", "Dark Dominion", export_grixis),
    ("eternal-harvest", "Eternal Harvest", export_golgari),
    ("forge-and-fury", "Forge & Fury", export_forge),
    ("phyrexian-perfection", "Phyrexian Perfection", export_phyrexian_perfection),
    ("compleated-dominion", "Compleated Dominion", export_compleated_dominion),
    ("mutant-multiplication", "Mutant Multiplication", export_wubrg),
    ("azure-dominion", "Azure Dominion", export_mono_blue),
    ("genesis-protocol", "Genesis Protocol", export_azorius),
    ("planar-decree", "Planar Decree", export_jeskai),
]


def main():
    with open(METADATA_FILE) as f:
        metadata = json.load(f)

    print(f"Loaded card metadata ({len(metadata)} cards)")
    print(f"Exporting simulation results for {len(DECKS)} decks...\n")

    for deck_id, deck_name, export_fn in DECKS:
        try:
            print(f"[{deck_name}]")
            result = export_fn(metadata)

            if not validate_output(result, deck_id):
                print(f"  SKIPPED: validation failed\n")
                continue

            out_path = PROJECT_ROOT / "data" / "commanders" / deck_id / "simulation.json"
            with open(out_path, "w") as f:
                json.dump(result, f, indent=2)
            print(f"  Written: {out_path}")
            print(f"  Size: {out_path.stat().st_size / 1024:.1f} KB\n")

        except Exception:
            print(f"  ERROR processing {deck_name}:")
            traceback.print_exc()
            print()

    print("Done.")


if __name__ == "__main__":
    main()
