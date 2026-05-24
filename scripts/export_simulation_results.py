#!/usr/bin/env python3
"""Export mana simulation results as JSON for commander decks.

Imports each simulation module under a namespace (they share function names),
runs the simulations, and writes structured JSON to
data/commanders/{id}/simulation.json.
"""

import argparse
import json
import math
import os
import random
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
import mana_simulation_mutant_multiplication as sim_wubrg
import mana_simulation_the_white_forge as sim_mono_white
import mana_simulation_verdant_tide as sim_mono_green
import mana_simulation_creeping_corruption as sim_wubg_poison
import mana_simulation_silverquill_the_disputant as sim_silverquill
import mana_simulation_pyre_and_panic as sim_mono_red
import mana_simulation_hidden_legion as sim_hidden_legion
import mana_simulation_superfriends_esika as sim_superfriends_esika

PROJECT_ROOT = SCRIPTS_DIR.parent
METADATA_FILE = PROJECT_ROOT / "data" / "card-metadata.json"

NUM_GAMES = 100_000
NUM_TURNS = 10
GOLDFISH_GAMES = 10_000
GOLDFISH_MEANINGFUL_PRESSURE_FLOOR = 6
GOLDFISH_LETHAL_DAMAGE_PROXY = 40

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

COLOR_SYMBOLS = "WUBRGC"
LAND_SUBTYPE_COLORS = {
    "Plains": "W",
    "Island": "U",
    "Swamp": "B",
    "Mountain": "R",
    "Forest": "G",
}
NUMBER_WORDS = {
    "a": 1,
    "an": 1,
    "one": 1,
    "two": 2,
    "three": 3,
}

KEY_COMBOS = {
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
    "the-white-forge": [
        {
            "name": "Heliod Ballista",
            "pieces": ["Heliod, Sun-Crowned", "Walking Ballista"],
            "requiresCommander": False,
            "description": "Infinite damage via lifelink counter loop.",
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
    "titan-convergence": [
        {
            "name": "Rings Basalt",
            "pieces": ["Rings of Brighthearth", "Basalt Monolith"],
            "requiresCommander": False,
            "description": "2-card infinite colorless mana engine.",
        }
    ],
    "creeping-corruption": [
        {
            "name": "Vorinclex Vraska Kill",
            "pieces": ["Vorinclex, Monstrous Raider", "Vraska, Betrayal's Sting"],
            "requiresCommander": False,
            "description": "Vraska enters with doubled loyalty, -9 deals doubled poison for instant kill.",
        }
    ],
    "hidden-legion": [
        {
            "name": "Snoop+Kiki+Tremors",
            "pieces": ["Conspicuous Snoop", "Kiki-Jiki, Mirror Breaker", "Impact Tremors"],
            "requiresCommander": False,
            "description": "Worldly Tutor → Kiki-Jiki on top; Snoop copies Kiki's ability; tap Snoop to make a token copy of Snoop (legendary clause irrelevant — copies are token, sac EOT, but loop fires infinitely while Snoop reads top of library). Each token ETB triggers Impact Tremors → infinite damage.",
        }
    ],
    "pyre-and-panic": [
        {
            "name": "Norin Drain Stack",
            "pieces": ["Impact Tremors", "Purphoros, God of the Forge", "Panharmonicon"],
            "requiresCommander": True,
            "description": "Norin's repeating self-flicker triggers Impact Tremors + Purphoros twice each per cycle under Panharmonicon — 6 dmg/opp baseline, scales with Torbran/Fiery Emancipation.",
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


def paid_mulligan_pct(mulligan_attempts: Counter, total: int) -> float:
    """Percentage of games that took any non-free mulligan."""
    return pct(sum(count for attempt, count in mulligan_attempts.items() if attempt >= 2), total)


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
        "C": 0,
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
        elif symbol in COLOR_SYMBOLS:
            result[symbol] += 1
    result["total"] = result["generic"] + sum(result[color] for color in COLOR_SYMBOLS)
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


def is_permanent_card(meta: dict) -> bool:
    """Return True for cards that remain on battlefield after resolution."""
    type_line = meta.get("type_line", "")
    return any(marker in type_line for marker in ("Land", "Artifact", "Creature", "Enchantment", "Planeswalker", "Battle"))


def extract_land_subtypes(meta: dict) -> set[str]:
    """Extract basic land subtypes from a land type line."""
    type_line = meta.get("type_line", "")
    if "Land" not in type_line or "—" not in type_line:
        return set()
    _, subtype_blob = type_line.split("—", 1)
    return {subtype.strip() for subtype in subtype_blob.split() if subtype.strip() in LAND_SUBTYPE_COLORS}


def parse_add_clause_atoms(clause: str, commander_colors: list[str]) -> list[frozenset]:
    """Convert a single oracle Add-clause into mana atoms."""
    lower = clause.lower()
    if "one mana of any color in your commander's color identity" in lower:
        return [frozenset(commander_colors)]
    if "one mana of any color" in lower:
        colors = commander_colors or list("WUBRG")
        return [frozenset(colors)]

    symbols = re.findall(r"\{([WUBRGC])\}", clause)
    if not symbols:
        return []
    if " or " in lower:
        return [frozenset(symbols)]
    return [frozenset({symbol}) for symbol in symbols]


def mana_atoms_for_card(meta: dict, commander_colors: list[str]) -> list[frozenset]:
    """Infer mana atoms a permanent can generate from oracle text."""
    oracle = meta.get("oracle_text", "")
    activation_match = re.search(r"^\{[^}]+\},\s*\{T\}: Add([^.\n]+)", oracle)
    if activation_match:
        symbols = re.findall(r"\{([WUBRGC])\}", activation_match.group(1))
        if symbols:
            return [frozenset(symbols)]

    atoms = []
    for clause in re.findall(r"Add([^.\n]+)", oracle):
        atoms.extend(parse_add_clause_atoms(clause, commander_colors))

    if atoms:
        return atoms

    # Fetchlands / land tutors function as access to typed colored mana.
    lower = oracle.lower()
    if "Land" in meta.get("type_line", "") and "search your library for a" in lower:
        colors = {
            color for subtype, color in LAND_SUBTYPE_COLORS.items()
            if subtype.lower() in lower
        }
        if colors:
            return [frozenset(colors)]

    return []


def mana_source_delay(meta: dict) -> int | None:
    """Turns until a permanent begins producing mana after being cast."""
    type_line = meta.get("type_line", "")
    oracle = meta.get("oracle_text", "")
    if "Land" in type_line:
        return 0
    if "{T}" not in oracle or "Add" not in oracle:
        return None
    if "Creature" in type_line:
        return 1
    if re.search(r"^\{[^}]+\},\s*\{T\}", oracle):
        return 1
    return 0


def parse_land_ramp_profile(meta: dict) -> dict | None:
    """Detect spells that put lands directly onto battlefield."""
    oracle = meta.get("oracle_text", "")
    lower = oracle.lower()
    type_line = meta.get("type_line", "")
    if "search your library" not in lower or "onto the battlefield" not in lower:
        return None
    if "land card" not in lower and not any(f"{subtype.lower()} card" in lower for subtype in LAND_SUBTYPE_COLORS):
        return None
    if any(marker in type_line for marker in ("Artifact", "Creature", "Enchantment")) and "enters" not in lower:
        return None

    count = 1
    count_match = re.search(r"(up to )?(a|an|one|two|three)\s+[^.]*land cards?", lower)
    if count_match:
        count = NUMBER_WORDS.get(count_match.group(2), 1)

    allowed_subtypes = {
        subtype for subtype in LAND_SUBTYPE_COLORS
        if f"{subtype.lower()} card" in lower or f"{subtype.lower()} cards" in lower
    }

    return {
        "count": count,
        "basicOnly": "basic land card" in lower or "basic land cards" in lower,
        "allowedSubtypes": allowed_subtypes,
        "entersTapped": "onto the battlefield tapped" in lower,
    }


def immediate_draw_count(meta: dict) -> int:
    """Best-effort immediate draw count from cast/ETB text."""
    sentences = [sentence.strip() for sentence in re.split(r"[\n.]", meta.get("oracle_text", "")) if sentence.strip()]
    for sentence in sentences:
        lower = sentence.lower()
        if "draw" not in lower:
            continue
        if "whenever" in lower or "at the beginning" in lower or "attacks" in lower:
            continue
        if "dies" in lower or "deals combat damage" in lower:
            continue
        if "enters" not in lower and lower.startswith("when "):
            continue

        match = re.search(r"draw (a|an|one|two|three|four|five|\d+) cards?", lower)
        if match:
            token = match.group(1)
            if token.isdigit():
                return int(token)
            return {
                "a": 1,
                "an": 1,
                "one": 1,
                "two": 2,
                "three": 3,
                "four": 4,
                "five": 5,
            }.get(token, 1)
        if "draw a card" in lower:
            return 1
    return 0


def land_enters_tapped(meta: dict, battlefield_lands: list[dict]) -> bool:
    """Best-effort ETB tapped heuristic for generic goldfish simulation."""
    oracle = meta.get("oracle_text", "")
    lower = oracle.lower()
    if "enters tapped" not in lower:
        return False
    if "you may pay 2 life" in lower:
        return False
    if "unless you have two or more opponents" in lower:
        return False

    other_land_count = len(battlefield_lands)
    subtype_set = set()
    basic_count = 0
    for land in battlefield_lands:
        subtype_set.update(land.get("subtypes", set()))
        if land.get("isBasic"):
            basic_count += 1

    if "unless you control two or fewer other lands" in lower:
        return other_land_count > 2
    if "unless you control two or more other lands" in lower:
        return other_land_count < 2
    if "unless you control a basic land" in lower:
        return basic_count == 0
    if "unless you control" in lower:
        required_subtypes = {subtype for subtype in LAND_SUBTYPE_COLORS if subtype.lower() in lower}
        if required_subtypes:
            return not any(subtype in subtype_set for subtype in required_subtypes)

    return True


def choose_best_land_index(library: list[str], metadata: dict, commander_colors: list[str],
                           battlefield_lands: list[dict], candidate_indices: list[int]) -> int | None:
    """Choose best land target from library for ramp/fetch effects."""
    if not candidate_indices:
        return None

    present_colors = set()
    for land in battlefield_lands:
        present_colors.update(land.get("colors", set()))

    best_index = None
    best_score = None
    for idx in candidate_indices:
        meta = metadata.get(library[idx], {})
        colors = set().union(*mana_atoms_for_card(meta, commander_colors)) if mana_atoms_for_card(meta, commander_colors) else set()
        untapped_bonus = 10 if not land_enters_tapped(meta, battlefield_lands) else 0
        new_colors = len((set(colors) & set(commander_colors)) - present_colors)
        score = (
            untapped_bonus,
            new_colors,
            len(set(colors) & set(commander_colors)),
            len(colors),
            library[idx],
        )
        if best_score is None or score > best_score:
            best_score = score
            best_index = idx
    return best_index


def select_ramp_targets(library: list[str], metadata: dict, commander_colors: list[str],
                        battlefield_lands: list[dict], ramp_profile: dict) -> list[str]:
    """Select concrete land cards from library for a ramp effect."""
    candidate_indices = []
    for idx, name in enumerate(library):
        meta = metadata.get(name, {})
        type_line = meta.get("type_line", "")
        if "Land" not in type_line:
            continue
        if ramp_profile["basicOnly"] and "Basic" not in type_line:
            continue
        subtypes = extract_land_subtypes(meta)
        if ramp_profile["allowedSubtypes"] and not (subtypes & ramp_profile["allowedSubtypes"]):
            continue
        candidate_indices.append(idx)

    selected = []
    for _ in range(ramp_profile["count"]):
        best_idx = choose_best_land_index(library, metadata, commander_colors, battlefield_lands, candidate_indices)
        if best_idx is None:
            break
        selected.append(library.pop(best_idx))
        candidate_indices = [idx - 1 if idx > best_idx else idx for idx in candidate_indices if idx != best_idx]
        selected_meta = metadata.get(selected[-1], {})
        battlefield_lands.append({
            "name": selected[-1],
            "colors": set().union(*mana_atoms_for_card(selected_meta, commander_colors)) if mana_atoms_for_card(selected_meta, commander_colors) else set(),
            "subtypes": extract_land_subtypes(selected_meta),
            "isBasic": "Basic" in selected_meta.get("type_line", ""),
        })
        battlefield_lands.pop()
    return selected


def build_goldfish_profile(name: str, meta: dict, category_names: set[str],
                           commander_colors: list[str], commander_name: str) -> dict:
    """Compile per-card goldfish heuristics from metadata."""
    mana_cost = parse_generic_mana_cost(meta.get("mana_cost", ""))
    type_line = meta.get("type_line", "")
    oracle = meta.get("oracle_text", "")
    is_land = "Land" in type_line
    is_threat = is_threat_card(name, meta, category_names) or name == commander_name
    is_draw = is_draw_card(meta)
    is_interaction = is_interaction_card(meta, category_names)
    land_ramp = None if is_land else parse_land_ramp_profile(meta)
    mana_atoms = mana_atoms_for_card(meta, commander_colors) if is_static_source_card(meta) else []
    source_delay = mana_source_delay(meta)

    impact = 0
    if is_threat:
        impact += max(2, min(8, int(meta.get("cmc", 0) or mana_cost["total"] or 2)))
        if "Planeswalker" in type_line or "Battle" in type_line:
            impact += 1
    if is_draw:
        impact += 1
    if "create" in oracle.lower() and "token" in oracle.lower():
        impact += 1
    if text_matches(oracle, THREAT_ORACLE_PATTERNS):
        impact += 1

    combat = 0
    if "Creature" in type_line:
        combat = max(1, min(8, int(meta.get("cmc", 0) or mana_cost["total"] or 1)))
        if any(keyword in oracle for keyword in ("Flying", "Trample", "Menace", "Double strike", "First strike")):
            combat += 1

    return {
        "name": name,
        "cmc": int(meta.get("cmc", 0) or mana_cost["total"] or 0),
        "manaCost": mana_cost,
        "typeLine": type_line,
        "isLand": is_land,
        "isPermanent": is_permanent_card(meta),
        "isThreat": is_threat,
        "isDraw": is_draw,
        "isInteraction": is_interaction,
        "manaAtoms": mana_atoms,
        "manaSourceDelay": source_delay,
        "landRamp": land_ramp,
        "immediateDraw": immediate_draw_count(meta),
        "impact": impact,
        "combat": combat,
        "subtypes": extract_land_subtypes(meta),
        "isBasic": "Basic" in type_line,
    }


class GoldfishManaPool:
    """Flexible mana pool backed by source atoms."""

    def __init__(self, sources=None):
        self.sources = list(sources or [])

    @property
    def total(self) -> int:
        return len(self.sources)

    def _allocate(self, pips: dict) -> tuple[bool, list[frozenset] | None]:
        needed = {color: pips.get(color, 0) for color in COLOR_SYMBOLS}
        generic = pips.get("generic", 0)
        total_needed = generic + sum(needed.values())
        if self.total < total_needed:
            return False, None

        available = list(self.sources)
        for _ in range(sum(needed.values())):
            best_color = None
            best_ratio = float("inf")
            for color in COLOR_SYMBOLS:
                if needed[color] <= 0:
                    continue
                supply = sum(1 for source in available if color in source)
                if supply == 0:
                    return False, None
                ratio = supply / needed[color]
                if ratio < best_ratio:
                    best_ratio = ratio
                    best_color = color

            best_idx = None
            best_flex = float("inf")
            for idx, source in enumerate(available):
                if best_color in source and len(source) < best_flex:
                    best_idx = idx
                    best_flex = len(source)
            if best_idx is None:
                return False, None
            available.pop(best_idx)
            needed[best_color] -= 1

        available.sort(key=len)
        if len(available) < generic:
            return False, None
        return True, available[generic:]

    def can_cast(self, pips: dict) -> bool:
        success, _ = self._allocate(pips)
        return success

    def after_spending(self, pips: dict) -> "GoldfishManaPool":
        success, remaining = self._allocate(pips)
        return GoldfishManaPool(remaining if success else [])


def combine_mana_costs(costs: list[dict]) -> dict:
    """Sum a list of pip-cost dicts into one combined cost.

    Used to build a synthetic mana cost for casting multiple combo pieces in one turn.
    Drops the X flag (combo pieces with X are not modeled).
    """
    combined = {
        "generic": 0, "W": 0, "U": 0, "B": 0, "R": 0, "G": 0, "C": 0, "total": 0, "X": False,
    }
    for cost in costs:
        for key in ("generic", "W", "U", "B", "R", "G", "C", "total"):
            combined[key] += cost.get(key, 0)
    return combined


def extract_combo_lines(deck_data: dict, profiles: dict) -> list[dict]:
    """Parse winConditions[] entries with kind=='combo' into combo-line specs.

    Each combo line: {pieces: [name], costs: [pip_dict], permanentPieces: set[name]}.
    Pieces not found in profiles are skipped (with the whole line dropped if any piece is missing).
    """
    lines = []
    for wincon in deck_data.get("winConditions", []) or []:
        if wincon.get("kind") != "combo":
            continue
        pieces = wincon.get("pieces") or []
        if not pieces:
            continue
        if not all(p in profiles for p in pieces):
            continue
        costs = [profiles[p]["manaCost"] for p in pieces]
        permanent_pieces = {p for p in pieces if profiles[p].get("isPermanent")}
        lines.append({
            "pieces": list(pieces),
            "costs": costs,
            "permanentPieces": permanent_pieces,
        })
    return lines


PIECE_TYPE_KEYWORDS = ("creature", "instant", "sorcery", "planeswalker", "artifact", "enchantment", "land", "battle")


def card_type_tokens(type_line: str) -> set[str]:
    """Lowercase set of card-type tokens present in a typeLine."""
    lowered = (type_line or "").lower()
    return {token for token in PIECE_TYPE_KEYWORDS if token in lowered}


def extract_tutor_metadata(deck_data: dict) -> dict:
    """Build per-tutor metadata table.

    Returns name → {targets: set[str], mv_cap: int|None, free_cast_via_bargain: bool,
    mode: "to_hand"|"to_graveyard", extra_cost: str|None}.
    Default tutor with no schema overrides is universal (targets={"any"}, mv_cap=None,
    mode="to_hand", extra_cost=None).
    """
    tutors = {}
    for entry in deck_data.get("decklist", []) or []:
        name = entry.get("name")
        if not name:
            continue
        if entry.get("primary_role") != "tutor" and entry.get("secondary_role") != "tutor":
            continue
        targets = entry.get("tutor_targets") or ["any"]
        tutors[name] = {
            "targets": {t.lower() for t in targets},
            "mv_cap": entry.get("tutor_mv_cap"),
            "free_cast_via_bargain": bool(entry.get("tutor_free_cast_via_bargain", False)),
            "mode": entry.get("tutor_mode") or "to_hand",
            "extra_cost": entry.get("tutor_extra_cost"),
        }
    return tutors


def extract_tutor_names(deck_data: dict) -> set[str]:
    """Collect tutor card names from decklist[].primary_role / secondary_role."""
    return set(extract_tutor_metadata(deck_data).keys())


def extract_reanimation_names(deck_data: dict) -> set[str]:
    """Collect reanimation card names from decklist[].primary_role / secondary_role == 'recursion'."""
    names = set()
    for entry in deck_data.get("decklist", []) or []:
        name = entry.get("name")
        if not name:
            continue
        if entry.get("primary_role") == "recursion" or entry.get("secondary_role") == "recursion":
            names.add(name)
    return names


def build_goldfish_context(decklist: list[str], deck_data: dict, metadata: dict,
                           commander_name: str, commander_colors: list[str]) -> dict:
    """Precompute per-card profiles for goldfish simulation."""
    category_lookup = build_card_category_lookup(deck_data)
    profiles = {}
    for name in ordered_unique(decklist + [commander_name]):
        profiles[name] = build_goldfish_profile(
            name=name,
            meta=metadata.get(name, {}),
            category_names=category_lookup.get(name, set()),
            commander_colors=commander_colors,
            commander_name=commander_name,
        )
    combo_lines = extract_combo_lines(deck_data, profiles)
    tutor_meta = extract_tutor_metadata(deck_data) if combo_lines else {}
    reanim_names = extract_reanimation_names(deck_data) if combo_lines else set()
    return {
        "profiles": profiles,
        "commanderName": commander_name,
        "commanderColors": commander_colors,
        "comboLines": combo_lines,
        "tutorNames": set(tutor_meta.keys()),
        "tutorMeta": tutor_meta,
        "reanimationNames": reanim_names,
    }


def should_goldfish_mulligan(hand: list[str], profiles: dict) -> bool:
    """Simple Commander goldfish mulligan heuristic."""
    lands = sum(1 for name in hand if profiles[name]["isLand"])
    cheap_ramp = sum(
        1 for name in hand
        if not profiles[name]["isLand"]
        and (profiles[name]["manaSourceDelay"] is not None or profiles[name]["landRamp"])
        and profiles[name]["cmc"] <= 2
    )
    return lands <= 1 or lands >= 6 or (lands == 2 and cheap_ramp == 0)


def goldfish_bottom_cards(hand: list[str], count: int, profiles: dict) -> list[str]:
    """Bottom expensive reactive cards first."""
    candidates = sorted(
        hand,
        key=lambda name: (
            profiles[name]["isLand"],
            not profiles[name]["isInteraction"],
            profiles[name]["cmc"],
            name,
        ),
        reverse=True,
    )
    return candidates[:count]


def commander_mulligan_goldfish(decklist: list[str], profiles: dict) -> tuple[list[str], list[str]]:
    """Run Commander mulligan and return library + kept hand."""
    attempt = 0
    while True:
        library = list(decklist)
        random.shuffle(library)
        hand = [library.pop() for _ in range(7)]
        if should_goldfish_mulligan(hand, profiles) and attempt < 2:
            attempt += 1
            continue
        break

    if attempt >= 2:
        for card in goldfish_bottom_cards(hand, attempt - 1, profiles):
            hand.remove(card)
            library.append(card)
    return library, hand


def choose_land_to_play(hand: list[str], profiles: dict, metadata: dict,
                        battlefield_lands: list[dict], commander_colors: list[str]) -> str | None:
    """Pick best land from hand for current board."""
    land_names = [name for name in hand if profiles[name]["isLand"]]
    if not land_names:
        return None

    present_colors = set()
    for land in battlefield_lands:
        present_colors.update(land.get("colors", set()))

    best_name = None
    best_score = None
    for name in land_names:
        profile = profiles[name]
        meta = metadata.get(name, {})
        colors = set().union(*profile["manaAtoms"]) if profile["manaAtoms"] else set()
        untapped_bonus = 10 if not land_enters_tapped(meta, battlefield_lands) else 0
        score = (
            untapped_bonus,
            len((colors & set(commander_colors)) - present_colors),
            len(colors & set(commander_colors)),
            len(colors),
            name,
        )
        if best_score is None or score > best_score:
            best_name = name
            best_score = score
    return best_name


def proactive_cast_priority(name: str, profile: dict, commander_name: str,
                            commander_cast: bool) -> tuple:
    """Sort order for proactive solitaire decisions."""
    if profile["isInteraction"]:
        return (99, 99, 99, name)
    if profile["landRamp"] or profile["manaSourceDelay"] is not None:
        ramp_value = len(profile["manaAtoms"]) + (profile["landRamp"]["count"] if profile["landRamp"] else 0)
        return (0, profile["cmc"], -ramp_value, name)
    if name == commander_name and not commander_cast:
        return (1, 0, -profile["impact"], name)
    if profile["isThreat"]:
        return (2, -profile["impact"], -profile["cmc"], name)
    if profile["isDraw"]:
        return (3, profile["cmc"], -profile["immediateDraw"], name)
    if profile["isPermanent"]:
        return (4, -profile["impact"], -profile["cmc"], name)
    return (5, profile["cmc"], 0, name)


def turn_sources(permanents: list[dict], turn: int) -> list[frozenset]:
    """Collect currently active mana sources."""
    sources = []
    for permanent in permanents:
        if permanent["manaActiveTurn"] <= turn:
            sources.extend(permanent["manaAtoms"])
    return sources


def piece_type_matches(piece_types: set[str], tutor_targets: set[str]) -> bool:
    """Check whether a tutor's target-type list permits fetching a piece of these types."""
    if "any" in tutor_targets:
        return True
    return bool(piece_types & tutor_targets)


def is_bargainable_battlefield(permanents: list[dict], profiles: dict,
                               commander_in_play: bool, commander_play_turn: int | None,
                               current_turn: int) -> bool:
    """Whether at least one bargain-legal target exists on battlefield.

    Bargain (per Beseech the Mirror): sacrifice an artifact, enchantment, or token.
    Approximated as: any enchantment permanent on battlefield OR (commander in play
    for >= 1 prior turn — proxy for "Sauron's Army token has appeared via opponent
    casts in a real 4-player game"). Mana rocks are excluded as bargain targets to
    avoid double-counting their mana production.
    """
    for permanent in permanents:
        if permanent["kind"] == "land":
            continue
        if permanent["kind"] == "ramp":
            continue  # don't bargain mana rocks
        type_line = profiles.get(permanent["name"], {}).get("typeLine", "")
        if "Enchantment" in type_line:
            return True
    if commander_in_play and commander_play_turn is not None and current_turn > commander_play_turn:
        return True
    return False


def combo_ready_this_turn(turn: int, hand: list[str], permanents: list[dict],
                          combo_lines: list[dict], profiles: dict,
                          tutor_meta: dict, reanim_names: set[str],
                          commander_in_play: bool, commander_play_turn: int | None,
                          commander_name: str = "") -> bool:
    """Check whether any combo line is fully assembled and castable this turn.

    Three substitution paths for a missing piece, tried in priority order:
      1. Bargain-free-cast tutor (e.g. Beseech the Mirror) — to_hand tutors only.
         If bargainable + piece MV ≤ tutor's mv_cap + piece type matches tutor's targets,
         adds tutor cost; piece is free.
      2. Type-matched regular tutor — cheapest tutor whose targets include piece's type
         and whose mv_cap permits the piece's MV.
         - to_hand mode (default): adds tutor cost + piece cost.
         - to_graveyard mode (e.g. Entomb, Buried Alive): requires piece is permanent AND
           a reanim spell is popped from the per-line reanim_pool. Cost chain becomes
           tutor cost + reanim cost (piece comes from graveyard).
      3. Reanimation — only for permanent pieces (creature/planeswalker). Adds reanim cost;
         piece's cast cost is replaced by reanim's cost.

    Tutors with extra_cost == "sacrifice-creature" (e.g. Diabolic Intent) only fire if a
    non-commander creature-typed permanent is on the battlefield. The commander itself does
    not satisfy the cost (the goldfish always casts commander early; counting it as a free
    sac target would neutralize the cost).

    Returns True if any combo line has all pieces resolved (via presence or substitution)
    AND the synthetic combined mana cost is payable from this turn's mana pool.
    """
    if not combo_lines:
        return False
    battlefield_names = {permanent["name"] for permanent in permanents if permanent["kind"] != "land"}
    hand_names = set(hand)
    pool = GoldfishManaPool(turn_sources(permanents, turn))
    bargainable = is_bargainable_battlefield(
        permanents, profiles, commander_in_play, commander_play_turn, turn,
    )

    # Non-commander creature-typed permanent available as a sac target?
    sac_creature_available = any(
        "creature" in (profiles.get(p["name"], {}).get("typeLine", "") or "").lower()
        and p["name"] != commander_name
        for p in permanents
        if p["kind"] != "land"
    )

    def tutor_extra_cost_satisfied(meta: dict) -> bool:
        if meta.get("extra_cost") == "sacrifice-creature":
            return sac_creature_available
        return True

    # Pre-build cheapest-first ordered lists of substitute resources currently in hand.
    tutors_in_hand = [name for name in hand if name in tutor_meta]
    tutors_in_hand.sort(key=lambda n: profiles[n]["manaCost"].get("total", 0))
    reanims_in_hand = [name for name in hand if name in reanim_names]
    reanims_in_hand.sort(key=lambda n: profiles[n]["manaCost"].get("total", 0))

    for line in combo_lines:
        to_cast_costs = []
        # Per-line copies so consumption doesn't bleed across lines.
        tutor_pool = list(tutors_in_hand)
        reanim_pool = list(reanims_in_hand)
        line_ok = True
        for piece, piece_cost in zip(line["pieces"], line["costs"]):
            if piece in battlefield_names:
                continue
            if piece in hand_names:
                to_cast_costs.append(piece_cost)
                continue

            piece_profile = profiles.get(piece, {})
            piece_types = card_type_tokens(piece_profile.get("typeLine", ""))
            piece_mv = piece_profile.get("manaCost", {}).get("total", 0)
            piece_is_permanent = piece_profile.get("isPermanent", False)

            # Path 1: bargain free-cast (e.g. Beseech the Mirror) — to_hand only
            bargain_idx = None
            if bargainable:
                for idx, tname in enumerate(tutor_pool):
                    meta = tutor_meta[tname]
                    if not meta["free_cast_via_bargain"]:
                        continue
                    if meta.get("mode", "to_hand") != "to_hand":
                        continue  # bargain semantics assume piece arrives in hand
                    if meta["mv_cap"] is not None and piece_mv > meta["mv_cap"]:
                        continue
                    if not piece_type_matches(piece_types, meta["targets"]):
                        continue
                    if not tutor_extra_cost_satisfied(meta):
                        continue
                    bargain_idx = idx
                    break
            if bargain_idx is not None:
                tname = tutor_pool.pop(bargain_idx)
                to_cast_costs.append(profiles[tname]["manaCost"])
                # piece cast is free under bargain; nothing added for the piece itself
                continue

            # Path 2: type-matched regular tutor (cheapest-first).
            # to_graveyard tutors require a reanim spell and a permanent piece.
            chosen_tutor_idx = None
            chosen_reanim_idx = None  # only set for to_graveyard mode
            for idx, tname in enumerate(tutor_pool):
                meta = tutor_meta[tname]
                if meta["free_cast_via_bargain"]:
                    continue  # reserved for bargain path
                if meta["mv_cap"] is not None and piece_mv > meta["mv_cap"]:
                    continue
                if not piece_type_matches(piece_types, meta["targets"]):
                    continue
                if not tutor_extra_cost_satisfied(meta):
                    continue
                mode = meta.get("mode", "to_hand")
                if mode == "to_graveyard":
                    if not piece_is_permanent:
                        continue
                    if not reanim_pool:
                        continue  # graveyard tutor needs a reanim to deliver the piece
                    chosen_tutor_idx = idx
                    chosen_reanim_idx = 0  # cheapest reanim
                    break
                # to_hand
                chosen_tutor_idx = idx
                break
            if chosen_tutor_idx is not None:
                tname = tutor_pool.pop(chosen_tutor_idx)
                to_cast_costs.append(profiles[tname]["manaCost"])
                if chosen_reanim_idx is not None:
                    rname = reanim_pool.pop(chosen_reanim_idx)
                    to_cast_costs.append(profiles[rname]["manaCost"])
                    # piece comes from graveyard for free
                else:
                    to_cast_costs.append(piece_cost)
                continue

            # Path 3: reanimation for permanent pieces (creature/planeswalker etc.)
            if piece_is_permanent and reanim_pool:
                rname = reanim_pool.pop(0)
                to_cast_costs.append(profiles[rname]["manaCost"])
                # piece cast cost replaced by reanim cost (piece comes from graveyard)
                continue

            line_ok = False
            break

        if not line_ok:
            continue
        if not to_cast_costs:
            return True  # all pieces already on battlefield
        combined = combine_mana_costs(to_cast_costs)
        if pool.can_cast(combined):
            return True
    return False


def metrics_from_board(turn: int, permanents: list[dict], commander_name: str,
                       commander_in_play: bool, cumulative_damage: float,
                       meaningful_threshold: int, combo_ready_ever: bool) -> dict:
    """Summarize goldfish board state at end of turn."""
    lands = sum(1 for permanent in permanents if permanent["kind"] == "land")
    ramp = sum(1 for permanent in permanents if permanent["kind"] == "ramp")
    threats = sum(1 for permanent in permanents if permanent["isThreat"])
    pressure = sum(permanent["impact"] for permanent in permanents if permanent["kind"] != "land")
    combat = sum(
        permanent["combat"] for permanent in permanents
        if permanent["combat"] > 0 and permanent["combatReadyTurn"] <= turn
    )
    meaningful = pressure >= meaningful_threshold or threats >= 2 or (commander_in_play and pressure >= meaningful_threshold - 1)
    return {
        "lands": lands,
        "ramp": ramp,
        "threats": threats,
        "availableMana": len(turn_sources(permanents, turn)),
        "pressure": pressure,
        "combat": combat,
        "cumulativeDamage": cumulative_damage,
        "commanderCast": 1 if commander_in_play else 0,
        "firstThreat": 1 if threats > 0 else 0,
        "meaningfulBoard": 1 if meaningful else 0,
        "lethalProxy": 1 if cumulative_damage >= GOLDFISH_LETHAL_DAMAGE_PROXY else 0,
        "comboLethal": 1 if combo_ready_ever else 0,
    }


def simulate_goldfish_game(decklist: list[str], metadata: dict, context: dict,
                           meaningful_threshold: int) -> dict:
    """Simulate one solitaire game with heuristic sequencing."""
    profiles = context["profiles"]
    commander_name = context["commanderName"]
    commander_colors = context["commanderColors"]
    combo_lines = context.get("comboLines", [])

    tutor_names = context.get("tutorNames", set())
    tutor_meta = context.get("tutorMeta", {})
    reanim_names = context.get("reanimationNames", set())
    library, hand = commander_mulligan_goldfish(decklist, profiles)
    permanents = []
    battlefield_lands = []
    commander_in_play = False
    commander_play_turn = None
    cumulative_damage = 0.0
    combo_ready_ever = False
    # Reserve non-permanent combo pieces (e.g. Demonic Consultation), tutors, and
    # reanimation spells — never cast as filler. Permanent pieces (e.g. Thassa's Oracle)
    # can still be cast proactively; once on the battlefield they remain available for
    # the combo check.
    reserved_combo_pieces = {
        piece
        for line in combo_lines
        for piece in line["pieces"]
        if not profiles[piece].get("isPermanent")
    } | tutor_names | reanim_names
    by_turn = {}

    for turn in range(1, NUM_TURNS + 1):
        if turn > 1 and library:
            hand.append(library.pop())

        land_name = choose_land_to_play(hand, profiles, metadata, battlefield_lands, commander_colors)
        if land_name:
            hand.remove(land_name)
            land_profile = profiles[land_name]
            enters_tapped_now = land_enters_tapped(metadata[land_name], battlefield_lands)
            colors = set().union(*land_profile["manaAtoms"]) if land_profile["manaAtoms"] else set()
            land_record = {
                "name": land_name,
                "kind": "land",
                "manaAtoms": land_profile["manaAtoms"],
                "manaActiveTurn": turn + (1 if enters_tapped_now else 0),
                "combatReadyTurn": 99,
                "impact": 0,
                "combat": 0,
                "isThreat": False,
            }
            permanents.append(land_record)
            battlefield_lands.append({
                "name": land_name,
                "colors": colors,
                "subtypes": land_profile["subtypes"],
                "isBasic": land_profile["isBasic"],
            })

        while True:
            pool = GoldfishManaPool(turn_sources(permanents, turn))
            candidates = []
            for name in ordered_unique(hand):
                profile = profiles[name]
                if profile["isLand"] or profile["isInteraction"]:
                    continue
                if name in reserved_combo_pieces:
                    continue
                if not pool.can_cast(profile["manaCost"]):
                    continue
                candidates.append(name)
            if not commander_in_play and pool.can_cast(profiles[commander_name]["manaCost"]):
                candidates.append(commander_name)

            if not candidates:
                break

            candidates.sort(key=lambda name: proactive_cast_priority(name, profiles[name], commander_name, commander_in_play))
            chosen = candidates[0]
            chosen_profile = profiles[chosen]
            pool = pool.after_spending(chosen_profile["manaCost"])
            if chosen in hand:
                hand.remove(chosen)

            if chosen_profile["landRamp"]:
                fetched = select_ramp_targets(
                    library=library,
                    metadata=metadata,
                    commander_colors=commander_colors,
                    battlefield_lands=battlefield_lands,
                    ramp_profile=chosen_profile["landRamp"],
                )
                for land_name in fetched:
                    land_profile = profiles[land_name]
                    colors = set().union(*land_profile["manaAtoms"]) if land_profile["manaAtoms"] else set()
                    land_record = {
                        "name": land_name,
                        "kind": "land",
                        "manaAtoms": land_profile["manaAtoms"],
                        "manaActiveTurn": turn + (1 if chosen_profile["landRamp"]["entersTapped"] else 0),
                        "combatReadyTurn": 99,
                        "impact": 0,
                        "combat": 0,
                        "isThreat": False,
                    }
                    permanents.append(land_record)
                    battlefield_lands.append({
                        "name": land_name,
                        "colors": colors,
                        "subtypes": land_profile["subtypes"],
                        "isBasic": land_profile["isBasic"],
                    })
                    if not chosen_profile["landRamp"]["entersTapped"]:
                        pool.sources.extend(land_profile["manaAtoms"])

            if chosen_profile["isPermanent"]:
                mana_active_turn = turn + (chosen_profile["manaSourceDelay"] or 0)
                if chosen_profile["manaSourceDelay"] == 0 and chosen_profile["manaAtoms"]:
                    pool.sources.extend(chosen_profile["manaAtoms"])
                permanents.append({
                    "name": chosen,
                    "kind": "ramp" if (chosen_profile["landRamp"] or chosen_profile["manaSourceDelay"] is not None) else "spell",
                    "manaAtoms": chosen_profile["manaAtoms"],
                    "manaActiveTurn": mana_active_turn,
                    "combatReadyTurn": turn + (1 if chosen_profile["combat"] > 0 else 99),
                    "impact": chosen_profile["impact"],
                    "combat": chosen_profile["combat"],
                    "isThreat": chosen_profile["isThreat"],
                })

            if chosen == commander_name:
                commander_in_play = True
                if commander_play_turn is None:
                    commander_play_turn = turn

            for _ in range(chosen_profile["immediateDraw"]):
                if library:
                    hand.append(library.pop())

        cumulative_damage += sum(
            permanent["combat"] for permanent in permanents
            if permanent["combat"] > 0 and permanent["combatReadyTurn"] <= turn
        )
        if not combo_ready_ever and combo_lines:
            combo_ready_ever = combo_ready_this_turn(
                turn=turn,
                hand=hand,
                permanents=permanents,
                combo_lines=combo_lines,
                profiles=profiles,
                tutor_meta=tutor_meta,
                reanim_names=reanim_names,
                commander_in_play=commander_in_play,
                commander_play_turn=commander_play_turn,
                commander_name=commander_name,
            )
        by_turn[turn] = metrics_from_board(
            turn=turn,
            permanents=permanents,
            commander_name=commander_name,
            commander_in_play=commander_in_play,
            cumulative_damage=cumulative_damage,
            meaningful_threshold=meaningful_threshold,
            combo_ready_ever=combo_ready_ever,
        )

    return by_turn


def _run_goldfish_chunk(args):
    """Worker chunk for multiprocessing goldfish simulation."""
    decklist, metadata, context, num_games, meaningful_threshold = args
    aggregate = {
        "lands": {turn: [] for turn in range(1, NUM_TURNS + 1)},
        "ramp": {turn: [] for turn in range(1, NUM_TURNS + 1)},
        "threats": {turn: [] for turn in range(1, NUM_TURNS + 1)},
        "available_mana": {turn: [] for turn in range(1, NUM_TURNS + 1)},
        "pressure": {turn: [] for turn in range(1, NUM_TURNS + 1)},
        "combat": {turn: [] for turn in range(1, NUM_TURNS + 1)},
        "cumulative_damage": {turn: [] for turn in range(1, NUM_TURNS + 1)},
        "commander_cast": Counter(),
        "first_threat": Counter(),
        "meaningful_board": Counter(),
        "lethal_proxy": Counter(),
        "combo_lethal": Counter(),
    }

    for _ in range(num_games):
        game = simulate_goldfish_game(decklist, metadata, context, meaningful_threshold)
        for turn in range(1, NUM_TURNS + 1):
            metrics = game[turn]
            aggregate["lands"][turn].append(metrics["lands"])
            aggregate["ramp"][turn].append(metrics["ramp"])
            aggregate["threats"][turn].append(metrics["threats"])
            aggregate["available_mana"][turn].append(metrics["availableMana"])
            aggregate["pressure"][turn].append(metrics["pressure"])
            aggregate["combat"][turn].append(metrics["combat"])
            aggregate["cumulative_damage"][turn].append(metrics["cumulativeDamage"])
            aggregate["commander_cast"][turn] += metrics["commanderCast"]
            aggregate["first_threat"][turn] += metrics["firstThreat"]
            aggregate["meaningful_board"][turn] += metrics["meaningfulBoard"]
            aggregate["lethal_proxy"][turn] += metrics["lethalProxy"]
            aggregate["combo_lethal"][turn] += metrics["comboLethal"]

    return aggregate


def merge_goldfish_stats(chunks: list[dict]) -> dict:
    """Merge multiprocessing goldfish chunk results."""
    merged = {
        "lands": {turn: [] for turn in range(1, NUM_TURNS + 1)},
        "ramp": {turn: [] for turn in range(1, NUM_TURNS + 1)},
        "threats": {turn: [] for turn in range(1, NUM_TURNS + 1)},
        "available_mana": {turn: [] for turn in range(1, NUM_TURNS + 1)},
        "pressure": {turn: [] for turn in range(1, NUM_TURNS + 1)},
        "combat": {turn: [] for turn in range(1, NUM_TURNS + 1)},
        "cumulative_damage": {turn: [] for turn in range(1, NUM_TURNS + 1)},
        "commander_cast": Counter(),
        "first_threat": Counter(),
        "meaningful_board": Counter(),
        "lethal_proxy": Counter(),
        "combo_lethal": Counter(),
    }

    for chunk in chunks:
        for key in ("lands", "ramp", "threats", "available_mana", "pressure", "combat", "cumulative_damage"):
            for turn in range(1, NUM_TURNS + 1):
                merged[key][turn].extend(chunk[key][turn])
        for key in ("commander_cast", "first_threat", "meaningful_board", "lethal_proxy", "combo_lethal"):
            merged[key].update(chunk[key])
    return merged


def compute_goldfish_section(decklist: list[str], deck_data: dict, metadata: dict,
                             commander_name: str, commander_colors: list[str]) -> dict:
    """Compute generic solitaire goldfish metrics for a deck."""
    context = build_goldfish_context(decklist, deck_data, metadata, commander_name, commander_colors)
    meaningful_threshold = max(
        GOLDFISH_MEANINGFUL_PRESSURE_FLOOR,
        int(round(compute_avg_cmc(decklist, metadata) * 2)),
    )
    import multiprocessing
    n_workers = os.cpu_count() or 4
    chunk_size = GOLDFISH_GAMES // n_workers
    remainder = GOLDFISH_GAMES % n_workers
    chunks = [chunk_size + (1 if i < remainder else 0) for i in range(n_workers)]
    with multiprocessing.Pool(n_workers) as pool:
        chunk_results = pool.map(
            _run_goldfish_chunk,
            [(decklist, metadata, context, games, meaningful_threshold) for games in chunks if games > 0],
        )
    stats = merge_goldfish_stats(chunk_results)

    by_turn = {}
    commander_curve = {}
    threat_curve = {}
    meaningful_curve = {}
    lethal_curve = {}
    combo_curve = {}

    for turn in range(1, NUM_TURNS + 1):
        commander_curve[str(turn)] = pct(stats["commander_cast"][turn], GOLDFISH_GAMES)
        threat_curve[str(turn)] = pct(stats["first_threat"][turn], GOLDFISH_GAMES)
        meaningful_curve[str(turn)] = pct(stats["meaningful_board"][turn], GOLDFISH_GAMES)
        lethal_curve[str(turn)] = pct(stats["lethal_proxy"][turn], GOLDFISH_GAMES)
        combo_curve[str(turn)] = pct(stats["combo_lethal"][turn], GOLDFISH_GAMES)
        by_turn[str(turn)] = {
            "lands": mana_stats(stats["lands"][turn]),
            "rampPermanents": mana_stats(stats["ramp"][turn]),
            "threats": mana_stats(stats["threats"][turn]),
            "availableMana": mana_stats(stats["available_mana"][turn]),
            "pressureScore": mana_stats(stats["pressure"][turn]),
            "combatPressure": mana_stats(stats["combat"][turn]),
            "cumulativeDamageProxy": mana_stats(stats["cumulative_damage"][turn]),
            "commanderCast": commander_curve[str(turn)],
            "firstThreat": threat_curve[str(turn)],
            "meaningfulBoard": meaningful_curve[str(turn)],
            "lethalProxy": lethal_curve[str(turn)],
            "comboLethal": combo_curve[str(turn)],
        }

    combo_lines = context.get("comboLines", [])
    return {
        "numGames": GOLDFISH_GAMES,
        "byTurn": by_turn,
        "comboLines": [
            {"pieces": line["pieces"]} for line in combo_lines
        ],
        "speed": {
            "commanderCast": {
                "byTurn": commander_curve,
                "medianTurn": median_turn_from_cumulative(commander_curve),
            },
            "firstThreat": {
                "byTurn": threat_curve,
                "medianTurn": median_turn_from_cumulative(threat_curve),
            },
            "meaningfulBoard": {
                "byTurn": meaningful_curve,
                "medianTurn": median_turn_from_cumulative(meaningful_curve),
            },
            "lethalProxy": {
                "byTurn": lethal_curve,
                "medianTurn": median_turn_from_cumulative(lethal_curve),
            },
            "comboLethal": {
                "byTurn": combo_curve,
                "medianTurn": median_turn_from_cumulative(combo_curve),
            },
        },
        "methodology": (
            f"{GOLDFISH_GAMES:,}-game solitaire heuristic. Sequencing: land drop, cheapest ramp, "
            "commander on affordability, biggest affordable threat, then other proactive spells. "
            f"Meaningful board = pressure score >= {meaningful_threshold} or 2+ threats. "
            f"Lethal proxy = cumulative combat-pressure proxy >= {GOLDFISH_LETHAL_DAMAGE_PROXY}; "
            "combat pressure uses mana-value-based creature scoring because card metadata omits power/toughness. "
            "Combo lethal = at least one winConditions[] entry tagged kind:'combo' has all pieces "
            "present (hand, battlefield, or substitutable) and combined mana cost payable. Substitution "
            "priority for missing pieces: (1) bargain free-cast tutor (e.g. Beseech the Mirror) when a "
            "non-rock enchantment is on battlefield OR commander has been in play for 1+ turn (approximates "
            "Sauron-style amass token from real-game opponent casts); (2) type-matched regular tutor "
            "whose tutor_targets includes piece's card type and tutor_mv_cap permits piece's MV; "
            "(3) reanimation spell (decklist[].primary_role/secondary_role == 'recursion') for permanent "
            "pieces only — cost replaces piece's cast cost (treats piece as if in graveyard). Each substitute "
            "is consumed once per combo line. Tutors, non-permanent combo pieces, and reanimation spells "
            "are reserved from filler casting. v2 limitations: no literal graveyard tracking (reanim "
            "assumes piece could be in GY), no opponent interaction, no multi-turn assembly tracking, "
            "no stack-trigger ordering."
        ),
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
    commander_colors = colors or ["C"]
    goldfish = compute_goldfish_section(
        decklist=decklist,
        deck_data=deck_data,
        metadata=metadata,
        commander_name=commander_name,
        commander_colors=commander_colors,
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
    result["goldfish"] = goldfish
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
        "goldfish",
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
        "paidMulligan": paid_mulligan_pct(mull, total),
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
        "paidMulligan": paid_mulligan_pct(mull, total),
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


def export_mono_white(metadata: dict) -> dict:
    """Export The White Forge (mono-white Gandalf) simulation."""
    return _export_colored(
        sim_module=sim_mono_white,
        deck_id="the-white-forge",
        deck_name="The White Forge",
        commander_name="Gandalf the White",
        commander_cmc=5,
        colors=["W"],
        metadata=metadata,
    )


def export_mono_red(metadata: dict) -> dict:
    """Export Pyre & Panic (mono-red Norin the Wary) simulation."""
    result = _export_colored(
        sim_module=sim_mono_red,
        deck_id="pyre-and-panic",
        deck_name="Pyre & Panic",
        commander_name="Norin the Wary",
        commander_cmc=1,
        colors=["R"],
        metadata=metadata,
    )

    # Add Norin-specific special metrics: engine readiness + flicker triggers
    deck_file = PROJECT_ROOT / "data" / "commanders" / "pyre-and-panic" / "deck.json"
    with open(deck_file) as f:
        deck_data = json.load(f)
    decklist = sim_mono_red.build_decklist(deck_data)

    print(f"  Running {NUM_GAMES:,} games for Norin-specific metrics...")
    stats = run_parallel(sim_mono_red._run_chunk, sim_mono_red.merge_stats,
                         decklist, metadata, NUM_GAMES)
    total = NUM_GAMES

    engine_ready = {}
    for t in range(1, NUM_TURNS + 1):
        engine_ready[str(t)] = pct(stats["engine_ready_by_turn"][t], total)

    flicker_data = stats["flicker_triggers_per_game"]
    flicker_mean = r1(statistics.mean(flicker_data)) if flicker_data else 0.0
    flicker_median = r1(statistics.median(flicker_data)) if flicker_data else 0.0

    result["specialMetrics"]["engineReadiness"] = {
        "description": "Probability 3+ ETB-damage payoffs (Impact Tremors / Purphoros / Witty Roastmaster / etc.) on battlefield",
        "byTurn": engine_ready,
    }
    result["specialMetrics"]["flickerTriggers"] = {
        "description": "Average Norin self-flicker triggers per game (one per combat post-cast through T10)",
        "mean": flicker_mean,
        "median": flicker_median,
    }

    return result


def export_hidden_legion(metadata: dict) -> dict:
    """Export Hidden Legion (5-color Ur-Dragon changeling tribal) simulation."""
    result = _export_colored(
        sim_module=sim_hidden_legion,
        deck_id="hidden-legion",
        deck_name="Hidden Legion",
        commander_name="The Ur-Dragon",
        commander_cmc=9,
        colors=["W", "U", "B", "R", "G"],
        metadata=metadata,
    )

    # Add Ur-Dragon-specific metrics: engine readiness, changelings curve, Ur castability
    deck_file = PROJECT_ROOT / "data" / "commanders" / "hidden-legion" / "deck.json"
    with open(deck_file) as f:
        deck_data = json.load(f)
    decklist = sim_hidden_legion.build_decklist(deck_data)

    print(f"  Running {NUM_GAMES:,} games for Hidden Legion engine metrics...")
    stats = run_parallel(sim_hidden_legion._run_chunk, sim_hidden_legion.merge_stats,
                         decklist, metadata, NUM_GAMES)
    total = NUM_GAMES

    engine_ready = {}
    for t in range(1, NUM_TURNS + 1):
        engine_ready[str(t)] = pct(stats["engine_ready_by_turn"][t], total)

    ur_castable = {}
    for t in range(1, NUM_TURNS + 1):
        ur_castable[str(t)] = pct(stats["ur_castable_by_turn"][t], total)

    changelings_curve = {}
    for t in range(1, NUM_TURNS + 1):
        changelings_curve[str(t)] = mana_stats(stats["changelings_by_turn"][t])

    result["specialMetrics"]["engineReadiness"] = {
        "description": (
            "Probability Ur-Dragon is castable (9 mana with WUBRG) AND at least one "
            "changeling is in play. Core engine state — Ur-Dragon as a Dragon with "
            "the tribe assembled enables Eminence-discounted casts, attack triggers, "
            "and Sliver Legion / Dragon Tempest payoffs."
        ),
        "byTurn": engine_ready,
    }
    result["specialMetrics"]["urDragonCastable"] = {
        "description": "Ur-Dragon (9 CMC, {4}{W}{U}{B}{R}{G}) castable by turn",
        "byTurn": ur_castable,
    }
    result["specialMetrics"]["changelingsInPlay"] = {
        "description": "Changelings on battlefield per turn (median/mean). Drives Eminence-discount value and tribal scaling.",
        "byTurn": changelings_curve,
    }

    return result


def export_superfriends_esika(metadata: dict) -> dict:
    """Export Esika's Council (5C Superfriends) simulation."""
    result = _export_colored(
        sim_module=sim_superfriends_esika,
        deck_id="superfriends-esika",
        deck_name="Esika's Council",
        commander_name="Esika, God of the Tree",
        commander_cmc=6,
        colors=["W", "U", "B", "R", "G"],
        metadata=metadata,
    )

    # Esika-specific metrics: engine readiness, doublers curve, Esika castability
    deck_file = PROJECT_ROOT / "data" / "commanders" / "superfriends-esika" / "deck.json"
    with open(deck_file) as f:
        deck_data = json.load(f)
    decklist = sim_superfriends_esika.build_decklist(deck_data)

    print(f"  Running {NUM_GAMES:,} games for Esika engine metrics...")
    stats = run_parallel(sim_superfriends_esika._run_chunk, sim_superfriends_esika.merge_stats,
                         decklist, metadata, NUM_GAMES)
    total = NUM_GAMES

    engine_ready = {}
    for t in range(1, NUM_TURNS + 1):
        engine_ready[str(t)] = pct(stats["engine_ready_by_turn"][t], total)

    esika_castable = {}
    for t in range(1, NUM_TURNS + 1):
        esika_castable[str(t)] = pct(stats["esika_castable_by_turn"][t], total)

    doublers_curve = {}
    for t in range(1, NUM_TURNS + 1):
        doublers_curve[str(t)] = mana_stats(stats["counter_doublers_by_turn"][t])

    result["specialMetrics"]["engineReadiness"] = {
        "description": (
            "Probability Esika has been cast AND at least one counter-doubler "
            "(Doubling Season, Parallel Lives, Vorinclex, Deepglow Skate, "
            "Innkeeper's Talent) is in play. Core engine state — Bridge active "
            "with a doubler accelerates every walker ETB into ult range."
        ),
        "byTurn": engine_ready,
    }
    result["specialMetrics"]["esikaCastable"] = {
        "description": "Esika back-side (Prismatic Bridge, 6 CMC, {1}{W}{U}{B}{R}{G}) castable by turn",
        "byTurn": esika_castable,
    }
    result["specialMetrics"]["counterDoublersInPlay"] = {
        "description": "Counter-doublers / proliferate enablers in play per turn (median/mean). Combo-readiness scaffolding.",
        "byTurn": doublers_curve,
    }

    return result


def export_orzhov(metadata: dict) -> dict:
    """Export Quill of Casualties (Orzhov Silverquill aristocrats) simulation."""
    return _export_colored(
        sim_module=sim_silverquill,
        deck_id="silverquill-the-disputant",
        deck_name="Quill of Casualties",
        commander_name="Silverquill, the Disputant",
        commander_cmc=4,
        colors=["W", "B"],
        metadata=metadata,
    )


def export_wubg_poison(metadata: dict) -> dict:
    """Export Creeping Corruption (WUBG Atraxa poison/proliferate) simulation."""
    return _export_colored(
        sim_module=sim_wubg_poison,
        deck_id="creeping-corruption",
        deck_name="Creeping Corruption",
        commander_name="Atraxa, Praetors' Voice",
        commander_cmc=4,
        colors=["W", "U", "B", "G"],
        metadata=metadata,
    )


def export_verdant_tide(metadata: dict) -> dict:
    """Export Verdant Tide (mono-green Eladamri) simulation."""
    result = _export_colored(
        sim_module=sim_mono_green,
        deck_id="verdant-tide",
        deck_name="Verdant Tide",
        commander_name="Eladamri, Korvecdal",
        commander_cmc=3,
        colors=["G"],
        metadata=metadata,
    )

    # Add Eladamri-specific: creature topcast probability
    deck_file = PROJECT_ROOT / "data" / "commanders" / "verdant-tide" / "deck.json"
    with open(deck_file) as f:
        deck_data = json.load(f)
    decklist = sim_mono_green.build_decklist(deck_data)

    print(f"  Running {NUM_GAMES:,} games for Eladamri-specific metrics...")
    stats = run_parallel(sim_mono_green._run_chunk, sim_mono_green.merge_stats,
                         decklist, metadata, NUM_GAMES)
    total = NUM_GAMES

    creature_on_top = {}
    for t in range(1, NUM_TURNS + 1):
        creature_on_top[str(t)] = pct(stats["creature_on_top_by_turn"][t], total)

    result["specialMetrics"]["creatureTopcast"] = {
        "description": "Probability of creature on top of library (Eladamri free cast)",
        "byTurn": creature_on_top,
    }

    return result


# --- Main ---


DECKS = [
    ("titan-convergence", "Titan Convergence", export_titan),
    ("eternal-agony", "Eternal Agony", export_rakdos),
    ("dark-dominion", "Dark Dominion", export_grixis),
    ("eternal-harvest", "Eternal Harvest", export_golgari),
    ("mutant-multiplication", "Mutant Multiplication", export_wubrg),
    ("the-white-forge", "The White Forge", export_mono_white),
    ("verdant-tide", "Verdant Tide", export_verdant_tide),
    ("creeping-corruption", "Creeping Corruption", export_wubg_poison),
    ("silverquill-the-disputant", "Quill of Casualties", export_orzhov),
    ("pyre-and-panic", "Pyre & Panic", export_mono_red),
    ("hidden-legion", "Hidden Legion", export_hidden_legion),
    ("superfriends-esika", "Esika's Council", export_superfriends_esika),
]


DECK_MAP = {deck_id: (deck_name, export_fn) for deck_id, deck_name, export_fn in DECKS}


def resolve_decks(deck_ids: list[str] | None) -> list[tuple[str, str, object]]:
    """Return selected deck tuples in canonical order."""
    if not deck_ids:
        return DECKS
    requested = set(deck_ids)
    return [deck for deck in DECKS if deck[0] in requested]


def output_path_for(deck_id: str, output_dir: Path | None) -> Path:
    """Resolve output path for a deck export."""
    if output_dir is None:
        return PROJECT_ROOT / "data" / "commanders" / deck_id / "simulation.json"
    return output_dir / deck_id / "simulation.json"


def export_selected_decks(metadata: dict, selected_decks: list[tuple[str, str, object]],
                          output_dir: Path | None) -> int:
    """Export selected decks. Return number of failures."""
    failures = 0

    for deck_id, deck_name, export_fn in selected_decks:
        try:
            print(f"[{deck_name}]")
            result = export_fn(metadata)

            if not validate_output(result, deck_id):
                print(f"  SKIPPED: validation failed\n")
                failures += 1
                continue

            out_path = output_path_for(deck_id, output_dir)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with open(out_path, "w") as f:
                json.dump(result, f, indent=2)
            print(f"  Written: {out_path}")
            print(f"  Size: {out_path.stat().st_size / 1024:.1f} KB\n")

        except Exception:
            failures += 1
            print(f"  ERROR processing {deck_name}:")
            traceback.print_exc()
            print()

    return failures


def main():
    global NUM_GAMES, GOLDFISH_GAMES

    parser = argparse.ArgumentParser(
        description="Export mana simulation results as JSON")
    parser.add_argument(
        "--deck",
        dest="deck_ids",
        action="append",
        choices=sorted(DECK_MAP),
        help="Export only the specified deck id. Repeat to select multiple decks.",
    )
    parser.add_argument(
        "--games",
        type=int,
        default=NUM_GAMES,
        help=f"Monte Carlo games per deck (default: {NUM_GAMES})",
    )
    parser.add_argument(
        "--goldfish-games",
        type=int,
        default=GOLDFISH_GAMES,
        help=f"Goldfish games per deck (default: {GOLDFISH_GAMES})",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Optional base directory for outputs; writes {output-dir}/{deck-id}/simulation.json",
    )
    args = parser.parse_args()

    if args.games <= 0:
        parser.error("--games must be > 0")
    if args.goldfish_games <= 0:
        parser.error("--goldfish-games must be > 0")

    NUM_GAMES = args.games
    GOLDFISH_GAMES = args.goldfish_games
    selected_decks = resolve_decks(args.deck_ids)

    with open(METADATA_FILE) as f:
        metadata = json.load(f)

    print(f"Loaded card metadata ({len(metadata)} cards)")
    print(f"Exporting simulation results for {len(selected_decks)} decks...")
    print(f"  Mana sim games: {NUM_GAMES:,}")
    print(f"  Goldfish games: {GOLDFISH_GAMES:,}")
    if args.output_dir:
        print(f"  Output dir: {args.output_dir}")
    print()

    failures = export_selected_decks(metadata, selected_decks, args.output_dir)

    if failures:
        print(f"Done with {failures} failure(s).")
        raise SystemExit(1)

    print("Done.")


if __name__ == "__main__":
    main()
