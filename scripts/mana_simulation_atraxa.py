#!/usr/bin/env python3
"""Monte Carlo mana base simulation for Atraxa, Praetors' Voice decks.

Simulates 100,000 games measuring mana production, color balance, and curve
efficiency turns 1-10 for both the Bracket 3 and Bracket 4 WUBG decklists.

Commander: Atraxa, Praetors' Voice ({G}{W}{U}{B}, CMC 4)
"""

import itertools
import json
import multiprocessing
import os
import random
import re
import statistics
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
METADATA_FILE = PROJECT_ROOT / "data" / "card-metadata.json"

NUM_GAMES = 100_000
NUM_TURNS = 10

# --- Mana cost parser ---


def parse_mana_cost(mana_cost: str) -> dict:
    """Parse mana_cost string into pip breakdown.

    "{G}{W}{U}{B}" -> {generic: 0, W: 1, U: 1, B: 1, G: 1, total: 4}
    Split cards (//): parse first half only.
    """
    if "//" in mana_cost:
        mana_cost = mana_cost.split("//")[0].strip()

    result = {"generic": 0, "W": 0, "U": 0, "B": 0, "G": 0, "total": 0, "X": False}
    symbols = re.findall(r"\{([^}]+)\}", mana_cost)
    for sym in symbols:
        if sym == "X":
            result["X"] = True
        elif sym.isdigit():
            result["generic"] += int(sym)
        elif sym in ("W", "U", "B", "G"):
            result[sym] += 1
        # Ignore other symbols (hybrid, phyrexian, etc.)
    result["total"] = result["generic"] + result["W"] + result["U"] + result["B"] + result["G"]
    return result


# --- Rock definitions ---
# Bracket 3 rocks (Phyrexian Perfection)
ROCK_DEFS_B3 = {
    "Sol Ring":          {"cmc": 1, "colors": frozenset({"C"}), "count": 2, "burst": False},
    "Arcane Signet":     {"cmc": 2, "colors": frozenset({"W", "U", "B", "G"}), "count": 1, "burst": False},
    "Glistening Sphere": {"cmc": 3, "colors": frozenset({"W", "U", "B", "G"}), "count": 1, "burst": False},
    "Fellwar Stone":     {"cmc": 2, "colors": frozenset({"W", "U", "B", "G"}), "count": 1, "burst": False},
    "Plague Myr":        {"cmc": 2, "colors": frozenset({"C"}), "count": 1, "burst": False},
}

# Bracket 4 rocks (Compleated Dominion)
ROCK_DEFS_B4 = {
    "Sol Ring":          {"cmc": 1, "colors": frozenset({"C"}), "count": 2, "burst": False},
    "Arcane Signet":     {"cmc": 2, "colors": frozenset({"W", "U", "B", "G"}), "count": 1, "burst": False},
    "Glistening Sphere": {"cmc": 3, "colors": frozenset({"W", "U", "B", "G"}), "count": 1, "burst": False},
    "Chrome Mox":        {"cmc": 0, "colors": frozenset({"W", "U", "B", "G"}), "count": 1, "burst": True},
    "Mana Vault":        {"cmc": 1, "colors": frozenset({"C"}), "count": 3, "burst": True},
}

# Active rock definitions — set by configure_bracket()
ROCK_DEFS = {}

# --- Ramp spell definitions ---
RAMP_DEFS_B3 = {
    "Farseek":        {"mana_cost": "{1}{G}", "fetch_type": "nonforest_typed", "tapped": True},
    "Nature's Lore":  {"mana_cost": "{1}{G}", "fetch_type": "forest_typed", "tapped": False},
    "Three Visits":   {"mana_cost": "{1}{G}", "fetch_type": "forest_typed", "tapped": False},
    "Cultivate":      {"mana_cost": "{2}{G}", "fetch_type": "basic_plus_hand", "tapped": True},
    "Kodama's Reach": {"mana_cost": "{2}{G}", "fetch_type": "basic_plus_hand", "tapped": True},
}

RAMP_DEFS_B4 = {
    "Farseek":        {"mana_cost": "{1}{G}", "fetch_type": "nonforest_typed", "tapped": True},
    "Nature's Lore":  {"mana_cost": "{1}{G}", "fetch_type": "forest_typed", "tapped": False},
    "Kodama's Reach": {"mana_cost": "{2}{G}", "fetch_type": "basic_plus_hand", "tapped": True},
}

# Active ramp definitions — set by configure_bracket()
RAMP_DEFS = {}

def configure_bracket(bracket: int):
    """Set module-level ROCK_DEFS and RAMP_DEFS for the given bracket."""
    global ROCK_DEFS, RAMP_DEFS
    ROCK_DEFS = ROCK_DEFS_B3 if bracket == 3 else ROCK_DEFS_B4
    RAMP_DEFS = RAMP_DEFS_B3 if bracket == 3 else RAMP_DEFS_B4


# --- Land subtype definitions ---

PLAINS_TYPED_LANDS = {"Plains", "Hallowed Fountain", "Godless Shrine", "Temple Garden",
                      "Indatha Triome"}
ISLAND_TYPED_LANDS = {"Island", "Hallowed Fountain", "Watery Grave", "Breeding Pool",
                      "Zagoth Triome"}
SWAMP_TYPED_LANDS = {"Swamp", "Watery Grave", "Overgrown Tomb", "Godless Shrine",
                     "Zagoth Triome", "Indatha Triome"}
FOREST_TYPED_LANDS = {"Forest", "Overgrown Tomb", "Breeding Pool", "Temple Garden",
                      "Zagoth Triome", "Indatha Triome", "Murmuring Bosk"}

# Farseek fetches any land with Plains/Island/Swamp/Mountain subtype.
# Lands with Forest type AND other types are still valid (e.g. Zagoth Triome
# is Forest Island Swamp — Farseek fetches it via Island/Swamp type).
FARSEEK_TYPED_LANDS = PLAINS_TYPED_LANDS | ISLAND_TYPED_LANDS | SWAMP_TYPED_LANDS

# Basic land names for Cultivate/Kodama's Reach
BASIC_LANDS = {"Plains", "Island", "Swamp", "Forest"}

ALWAYS_TAPPED = {
    "Zagoth Triome", "Indatha Triome", "Bojuka Bog",
}

# Murmuring Bosk: reveals Treefolk or ETB tapped. No Treefolk in deck -> always tapped.
# (Only in B3; B4 swaps it out for Urborg)


def land_enters_tapped(name: str, battlefield_lands: list[str], hand: list[str]) -> bool:
    """Determine if a land enters tapped given current board and hand."""
    if name in ALWAYS_TAPPED:
        return True
    if name == "Murmuring Bosk":
        return True  # No Treefolk to reveal

    # Check lands (need matching basic land type on board)
    if name == "Glacial Fortress":
        return not any(l in PLAINS_TYPED_LANDS or l in ISLAND_TYPED_LANDS
                       for l in battlefield_lands)
    if name == "Drowned Catacomb":
        return not any(l in ISLAND_TYPED_LANDS or l in SWAMP_TYPED_LANDS
                       for l in battlefield_lands)
    if name == "Woodland Cemetery":
        return not any(l in SWAMP_TYPED_LANDS or l in FOREST_TYPED_LANDS
                       for l in battlefield_lands)
    if name == "Hinterland Harbor":
        return not any(l in FOREST_TYPED_LANDS or l in ISLAND_TYPED_LANDS
                       for l in battlefield_lands)
    if name == "Sunpetal Grove":
        return not any(l in FOREST_TYPED_LANDS or l in PLAINS_TYPED_LANDS
                       for l in battlefield_lands)
    if name == "Isolated Chapel":
        return not any(l in PLAINS_TYPED_LANDS or l in SWAMP_TYPED_LANDS
                       for l in battlefield_lands)

    # Shock lands, pain lands, Command Tower, etc. — always untapped
    return False


def compute_land_sources(name: str, battlefield_lands: list[str]) -> list[frozenset]:
    """Return mana sources for a single untapped land."""
    # Basics
    if name == "Plains":
        return [frozenset({"W"})]
    if name == "Island":
        return [frozenset({"U"})]
    if name == "Swamp":
        return [frozenset({"B"})]
    if name == "Forest":
        return [frozenset({"G"})]

    # 4-color / rainbow lands
    if name in {"Command Tower", "Exotic Orchard", "City of Brass",
                "Mana Confluence", "Plaza of Heroes"}:
        return [frozenset({"W", "U", "B", "G"})]

    # Triomes (BUG + WBG)
    if name == "Zagoth Triome":
        return [frozenset({"U", "B", "G"})]
    if name == "Indatha Triome":
        return [frozenset({"W", "B", "G"})]

    # Shock lands
    if name == "Hallowed Fountain":
        return [frozenset({"W", "U"})]
    if name == "Watery Grave":
        return [frozenset({"U", "B"})]
    if name == "Overgrown Tomb":
        return [frozenset({"B", "G"})]
    if name == "Breeding Pool":
        return [frozenset({"U", "G"})]
    if name == "Godless Shrine":
        return [frozenset({"W", "B"})]
    if name == "Temple Garden":
        return [frozenset({"W", "G"})]

    # Check lands
    if name == "Glacial Fortress":
        return [frozenset({"W", "U"})]
    if name == "Drowned Catacomb":
        return [frozenset({"U", "B"})]
    if name == "Woodland Cemetery":
        return [frozenset({"B", "G"})]
    if name == "Hinterland Harbor":
        return [frozenset({"U", "G"})]
    if name == "Sunpetal Grove":
        return [frozenset({"W", "G"})]
    if name == "Isolated Chapel":
        return [frozenset({"W", "B"})]

    # Pain lands
    if name == "Caves of Koilos":
        return [frozenset({"W", "B"})]
    if name == "Yavimaya Coast":
        return [frozenset({"U", "G"})]
    if name == "Llanowar Wastes":
        return [frozenset({"B", "G"})]
    if name == "Adarkar Wastes":
        return [frozenset({"W", "U"})]
    if name == "Underground River":
        return [frozenset({"U", "B"})]
    if name == "Brushland":
        return [frozenset({"W", "G"})]

    # Murmuring Bosk (Treefolk Forest)
    if name == "Murmuring Bosk":
        return [frozenset({"W", "B", "G"})]

    # Urborg, Tomb of Yawgmoth (makes all lands tap for B; itself taps for B)
    if name == "Urborg, Tomb of Yawgmoth":
        return [frozenset({"B"})]

    # Phyrexian Tower (sac creature for BB; baseline: colorless)
    if name == "Phyrexian Tower":
        return [frozenset({"C"})]

    # Utility lands (colorless only)
    if name in {"Karn's Bastion", "Inkmoth Nexus", "The Seedcore", "Rogue's Passage"}:
        return [frozenset({"C"})]
    if name == "Bojuka Bog":
        return [frozenset({"B"})]
    if name == "Ancient Tomb":
        return [frozenset({"C"}), frozenset({"C"})]  # 2 colorless

    # Fallback: colorless
    return [frozenset({"C"})]


# --- ManaPool ---


class ManaPool:
    """Tracks available mana as a list of source atoms."""

    def __init__(self, sources=None):
        self.sources: list[frozenset] = list(sources) if sources else []

    @property
    def total(self) -> int:
        return len(self.sources)

    def count_color(self, color: str) -> int:
        return sum(1 for s in self.sources if color in s)

    def _allocate(self, pips: dict) -> tuple[bool, list[frozenset] | None]:
        """Greedy allocation: colored pips first (most constrained), then generic."""
        needed = {c: pips.get(c, 0) for c in "WUBG"}
        generic = pips.get("generic", 0)
        total_needed = sum(needed.values()) + generic

        if self.total < total_needed:
            return False, None

        available = list(self.sources)

        # Phase 1: Assign colored pips
        for _ in range(sum(needed.values())):
            best_color = None
            best_ratio = float("inf")
            for color in "WUBG":
                if needed[color] <= 0:
                    continue
                supply = sum(1 for s in available if color in s)
                if supply == 0:
                    return False, None
                ratio = supply / needed[color]
                if ratio < best_ratio:
                    best_ratio = ratio
                    best_color = color

            if best_color is None:
                break

            best_idx = None
            best_flex = float("inf")
            for i, s in enumerate(available):
                if best_color in s and len(s) < best_flex:
                    best_idx = i
                    best_flex = len(s)

            if best_idx is None:
                return False, None

            available.pop(best_idx)
            needed[best_color] -= 1

        if any(v > 0 for v in needed.values()):
            return False, None

        # Phase 2: Generic
        available.sort(key=lambda s: len(s))
        if len(available) < generic:
            return False, None

        remaining = available[generic:]
        return True, remaining

    def can_cast(self, pips: dict) -> bool:
        success, _ = self._allocate(pips)
        return success

    def after_spending(self, pips: dict) -> "ManaPool":
        success, remaining = self._allocate(pips)
        if not success:
            return ManaPool()
        return ManaPool(remaining)


# --- Decklist builder ---


def build_decklist(deck_data: dict) -> list[str]:
    """Build 99-card decklist from deck JSON."""
    cards = []
    for card in deck_data["decklist"]:
        qty = card.get("quantity", 1)
        cards.extend([card["name"]] * qty)
    return cards


def classify_cards(decklist: list[str], metadata: dict) -> dict:
    """Classify each card as land, rock, or spell."""
    classified = {"lands": [], "rocks": [], "spells": []}
    for name in decklist:
        if name in ROCK_DEFS:
            classified["rocks"].append(name)
        else:
            meta = metadata.get(name, {})
            type_line = meta.get("type_line", "")
            if "Land" in type_line:
                classified["lands"].append(name)
            else:
                classified["spells"].append(name)
    return classified


# --- Mulligan ---

MAX_MULLIGANS = 2


def should_mulligan(hand: list[str], land_set: set[str]) -> bool:
    sources = sum(1 for c in hand if c in land_set or c in ROCK_DEFS)
    return sources <= 1


def choose_bottom_cards(hand: list[str], count: int, metadata: dict,
                        land_set: set[str]) -> list[str]:
    candidates = [c for c in hand if c not in land_set and c not in ROCK_DEFS]
    candidates.sort(key=lambda c: metadata.get(c, {}).get("cmc", 0), reverse=True)
    return candidates[:count]


# --- Game state ---


class GameState:
    def __init__(self, decklist: list[str], metadata: dict, land_set: set[str]):
        self.library = list(decklist)
        random.shuffle(self.library)
        self.hand: list[str] = []
        self.battlefield_lands: list[str] = []
        self.tapped_lands: set[int] = set()
        self.battlefield_rocks: list[str] = []
        self.metadata = metadata
        self.land_set = land_set
        self.mana_per_turn: list[ManaPool] = []
        self.mulligan_attempt = 0

    def draw(self, n: int = 1):
        for _ in range(n):
            if self.library:
                self.hand.append(self.library.pop())

    def count_lands_in_hand(self) -> int:
        return sum(1 for c in self.hand if c in self.land_set)

    def _is_land(self, name: str) -> bool:
        return name in self.land_set

    def _land_play_priority(self, name: str) -> float:
        tapped = land_enters_tapped(name, self.battlefield_lands, self.hand)
        base = 0 if tapped else 10

        sources = compute_land_sources(name, self.battlefield_lands)
        if sources:
            n_colors = sum(1 for c in "WUBG" if c in sources[0])
            base += n_colors * 2
        return base

    def compute_mana_pool(self) -> ManaPool:
        pool_sources: list[frozenset] = []

        for i, land in enumerate(self.battlefield_lands):
            if i in self.tapped_lands:
                continue
            sources = compute_land_sources(land, self.battlefield_lands)
            pool_sources.extend(sources)

        for rock in self.battlefield_rocks:
            rdef = ROCK_DEFS[rock]
            for _ in range(rdef["count"]):
                pool_sources.append(rdef["colors"])

        return ManaPool(pool_sources)

    def play_turn(self, turn_number: int):
        if turn_number > 1:
            self.draw(1)

        self.tapped_lands.clear()

        hand_lands = [(self._land_play_priority(c), c) for c in self.hand if self._is_land(c)]
        hand_lands.sort(reverse=True)

        if hand_lands:
            _, land_name = hand_lands[0]
            self.hand.remove(land_name)
            tapped = land_enters_tapped(land_name, self.battlefield_lands, self.hand)
            self.battlefield_lands.append(land_name)
            if tapped:
                self.tapped_lands.add(len(self.battlefield_lands) - 1)

        pool = self.compute_mana_pool()
        self._try_cast_rocks(pool)

        # After rocks, try ramp spells (Farseek, Nature's Lore, etc.)
        pool = self.compute_mana_pool()
        self._try_cast_ramp(pool)

        self.mana_per_turn.append(self.compute_mana_pool())

    def _find_best_fetchable(self, typed_set: set[str]) -> str | None:
        """Find the best fetchable land in library from a typed set.

        Prioritize by color coverage: pick the land that adds the most
        colors needed for casting Atraxa (WUBG).
        """
        # Colors already available on battlefield
        have_colors = set()
        for land in self.battlefield_lands:
            sources = compute_land_sources(land, self.battlefield_lands)
            for s in sources:
                have_colors.update(c for c in s if c != "C")

        candidates = [c for c in self.library if c in typed_set]
        if not candidates:
            return None

        def score(name: str) -> tuple[int, int]:
            sources = compute_land_sources(name, [])
            if not sources:
                return (0, 0)
            colors = {c for c in sources[0] if c != "C"}
            missing_covered = len(colors - have_colors)
            return (missing_covered, len(colors))

        candidates.sort(key=score, reverse=True)
        return candidates[0]

    def _try_cast_ramp(self, pool: ManaPool):
        """Try to cast one ramp spell from hand, fetching a land to battlefield."""
        # Sort by CMC ascending (2-cost first for earlier impact)
        ramp_in_hand = [(name, RAMP_DEFS[name]) for name in self.hand
                        if name in RAMP_DEFS]
        ramp_in_hand.sort(key=lambda x: parse_mana_cost(x[1]["mana_cost"])["total"])

        for ramp_name, rdef in ramp_in_hand:
            pips = parse_mana_cost(rdef["mana_cost"])
            if not pool.can_cast(pips):
                continue

            fetch_type = rdef["fetch_type"]

            if fetch_type == "forest_typed":
                target = self._find_best_fetchable(FOREST_TYPED_LANDS)
            elif fetch_type == "nonforest_typed":
                target = self._find_best_fetchable(FARSEEK_TYPED_LANDS)
            elif fetch_type == "basic_plus_hand":
                target = self._find_best_fetchable(BASIC_LANDS)
            else:
                continue

            if target is None:
                continue

            # Cast the ramp spell
            pool = pool.after_spending(pips)
            self.hand.remove(ramp_name)
            self.library.remove(target)
            self.battlefield_lands.append(target)
            if rdef["tapped"]:
                self.tapped_lands.add(len(self.battlefield_lands) - 1)

            # basic_plus_hand: also fetch a second basic to hand
            if fetch_type == "basic_plus_hand":
                basics_in_lib = [c for c in self.library if c in BASIC_LANDS]
                if basics_in_lib:
                    # Pick the basic whose color is most needed
                    second = self._find_best_fetchable(BASIC_LANDS)
                    if second:
                        self.library.remove(second)
                        self.hand.append(second)

            # Only cast one ramp spell per turn
            return

    def _try_cast_rocks(self, pool: ManaPool):
        priority_order = [
            "Chrome Mox",
            "Sol Ring", "Mana Vault",
            "Arcane Signet", "Fellwar Stone", "Plague Myr",
            "Glistening Sphere",
        ]

        for rock_name in priority_order:
            if rock_name not in self.hand or rock_name not in ROCK_DEFS:
                continue
            rdef = ROCK_DEFS[rock_name]

            # Special handling for Chrome Mox (imprint a colored nonartifact nonland)
            if rock_name == "Chrome Mox":
                imprintable = [c for c in self.hand
                               if c not in self.land_set
                               and c not in ROCK_DEFS
                               and c != rock_name]
                if not imprintable:
                    continue
                # Imprint highest CMC card
                imprintable.sort(key=lambda c: self.metadata.get(c, {}).get("cmc", 0))
                self.hand.remove(imprintable[0])
                self.hand.remove(rock_name)
                self.battlefield_rocks.append(rock_name)
                for _ in range(rdef["count"]):
                    pool.sources.append(rdef["colors"])
                continue

            pips = parse_mana_cost(
                self.metadata.get(rock_name, {}).get("mana_cost", ""))
            if pool.can_cast(pips):
                pool = pool.after_spending(pips)
                self.hand.remove(rock_name)
                self.battlefield_rocks.append(rock_name)
                for _ in range(rdef["count"]):
                    pool.sources.append(rdef["colors"])


def commander_mulligan(decklist: list[str], metadata: dict,
                       land_set: set[str]) -> GameState:
    attempt = 0
    while True:
        state = GameState(decklist, metadata, land_set)
        state.draw(7)
        if should_mulligan(state.hand, land_set) and attempt < MAX_MULLIGANS:
            attempt += 1
            continue
        break

    if attempt >= 2:
        bottom = choose_bottom_cards(state.hand, attempt - 1, metadata, land_set)
        for card in bottom:
            state.hand.remove(card)
            state.library.append(card)

    state.mulligan_attempt = attempt
    return state


def can_cast_from_hand(state: GameState, pool: ManaPool) -> list[str]:
    castable = []
    for card in state.hand:
        if card in ROCK_DEFS or card in state.land_set:
            continue
        meta = state.metadata.get(card, {})
        mc = meta.get("mana_cost", "")
        if not mc:
            continue
        pips = parse_mana_cost(mc)
        if pips["total"] == 0 and not pips["X"]:
            continue
        if pool.can_cast(pips):
            castable.append(card)
    return castable


# --- Static analysis ---


def print_static_analysis(decklist: list[str], metadata: dict,
                          classified: dict, deck_name: str) -> tuple:
    print("=" * 65)
    print(f"STATIC ANALYSIS — {deck_name.upper()}")
    print("=" * 65)

    print(f"\n--- Deck Composition ---")
    print(f"Total cards (excl. commander): {len(decklist)}")
    print(f"Lands: {len(classified['lands'])}")
    print(f"Mana rocks: {len(classified['rocks'])}")
    print(f"Spells/creatures: {len(classified['spells'])}")

    cmcs = []
    for name in decklist:
        meta = metadata.get(name, {})
        if "Land" not in meta.get("type_line", ""):
            cmc = meta.get("cmc", 0)
            if isinstance(cmc, (int, float)):
                cmcs.append(int(cmc))

    avg_cmc = statistics.mean(cmcs) if cmcs else 0
    print(f"\nAverage CMC (non-land): {avg_cmc:.2f}")

    cmc_hist = Counter(cmcs)
    print(f"\n  CMC histogram:")
    max_cmc = max(cmc_hist.keys()) if cmc_hist else 0
    for cmc_val in range(0, max_cmc + 1):
        count = cmc_hist.get(cmc_val, 0)
        if count > 0:
            bar = "#" * count
            print(f"    {cmc_val:>2} CMC: {count:>2} {bar}")

    total_W, total_U, total_B, total_G = 0, 0, 0, 0
    for name in decklist:
        meta = metadata.get(name, {})
        mc = meta.get("mana_cost", "")
        if "Land" in meta.get("type_line", ""):
            continue
        pips = parse_mana_cost(mc)
        total_W += pips["W"]
        total_U += pips["U"]
        total_B += pips["B"]
        total_G += pips["G"]

    total_pips = total_W + total_U + total_B + total_G
    if total_pips > 0:
        print(f"\n--- Pip Demand ---")
        print(f"  Total {{W}}: {total_W}  {{U}}: {total_U}  {{B}}: {total_B}  {{G}}: {total_G}")
        print(f"  Ratio: {total_W/total_pips*100:.0f}% W / {total_U/total_pips*100:.0f}% U / "
              f"{total_B/total_pips*100:.0f}% B / {total_G/total_pips*100:.0f}% G")

    lands = classified["lands"]
    w_lands, u_lands, b_lands, g_lands, c_only = 0, 0, 0, 0, 0
    for l in lands:
        sources = compute_land_sources(l, [])
        if not sources:
            continue
        colors = sources[0]
        if "W" in colors:
            w_lands += 1
        if "U" in colors:
            u_lands += 1
        if "B" in colors:
            b_lands += 1
        if "G" in colors:
            g_lands += 1
        if colors == frozenset({"C"}):
            c_only += 1

    print(f"\n--- Mana Source Inventory ---")
    print(f"  Lands: {len(lands)} total")
    print(f"    W: {w_lands}  U: {u_lands}  B: {b_lands}  G: {g_lands}  C-only: {c_only}")

    return avg_cmc, total_W, total_U, total_B, total_G


# --- Simulation ---


def run_simulation(decklist: list[str], metadata: dict, num_games: int = NUM_GAMES) -> dict:
    land_set = set()
    for name in set(decklist):
        meta = metadata.get(name, {})
        if "Land" in meta.get("type_line", ""):
            land_set.add(name)

    mana_by_turn = {t: [] for t in range(1, NUM_TURNS + 1)}
    w_by_turn = {t: [] for t in range(1, NUM_TURNS + 1)}
    u_by_turn = {t: [] for t in range(1, NUM_TURNS + 1)}
    b_by_turn = {t: [] for t in range(1, NUM_TURNS + 1)}
    g_by_turn = {t: [] for t in range(1, NUM_TURNS + 1)}
    hand_land_counts = Counter()
    mulligan_attempts = Counter()

    zero_w_by_turn = {t: 0 for t in range(1, NUM_TURNS + 1)}
    zero_u_by_turn = {t: 0 for t in range(1, NUM_TURNS + 1)}
    zero_b_by_turn = {t: 0 for t in range(1, NUM_TURNS + 1)}
    zero_g_by_turn = {t: 0 for t in range(1, NUM_TURNS + 1)}

    commander_castable_turn = []
    commander_by_turn = {t: 0 for t in range(1, NUM_TURNS + 1)}

    castable_spell_by_turn = {t: 0 for t in range(1, NUM_TURNS + 1)}
    curve_out_games = 0

    tapped_land_turns = {1: 0, 2: 0}

    for _ in range(num_games):
        state = commander_mulligan(decklist, metadata, land_set)
        mulligan_attempts[state.mulligan_attempt] += 1
        hand_land_counts[state.count_lands_in_hand()] += 1

        cmd_cast_turn = None
        cast_every_turn = True

        for t in range(1, NUM_TURNS + 1):
            lands_before = len(state.battlefield_lands)
            state.play_turn(t)
            lands_after = len(state.battlefield_lands)

            pool = state.mana_per_turn[-1]

            mana_by_turn[t].append(pool.total)
            w_by_turn[t].append(pool.count_color("W"))
            u_by_turn[t].append(pool.count_color("U"))
            b_by_turn[t].append(pool.count_color("B"))
            g_by_turn[t].append(pool.count_color("G"))

            if pool.count_color("W") == 0:
                zero_w_by_turn[t] += 1
            if pool.count_color("U") == 0:
                zero_u_by_turn[t] += 1
            if pool.count_color("B") == 0:
                zero_b_by_turn[t] += 1
            if pool.count_color("G") == 0:
                zero_g_by_turn[t] += 1

            # Commander: Atraxa, Praetors' Voice {G}{W}{U}{B}
            cmd_pips = {"generic": 0, "W": 1, "U": 1, "B": 1, "G": 1}
            if cmd_cast_turn is None and pool.can_cast(cmd_pips):
                cmd_cast_turn = t
                commander_by_turn[t] += 1

            castable = can_cast_from_hand(state, pool)
            if castable:
                castable_spell_by_turn[t] += 1
            elif t <= 4:
                cast_every_turn = False

            if t <= 2 and lands_after > lands_before:
                new_idx = lands_after - 1
                if new_idx in state.tapped_lands:
                    tapped_land_turns[t] += 1

        if cmd_cast_turn is not None:
            commander_castable_turn.append(cmd_cast_turn)
            for future_t in range(cmd_cast_turn + 1, NUM_TURNS + 1):
                commander_by_turn[future_t] += 1

        if cast_every_turn:
            curve_out_games += 1

    return {
        "mana_by_turn": mana_by_turn,
        "w_by_turn": w_by_turn,
        "u_by_turn": u_by_turn,
        "b_by_turn": b_by_turn,
        "g_by_turn": g_by_turn,
        "hand_land_counts": hand_land_counts,
        "mulligan_attempts": mulligan_attempts,
        "zero_w_by_turn": zero_w_by_turn,
        "zero_u_by_turn": zero_u_by_turn,
        "zero_b_by_turn": zero_b_by_turn,
        "zero_g_by_turn": zero_g_by_turn,
        "commander_castable_turn": commander_castable_turn,
        "commander_by_turn": commander_by_turn,
        "castable_spell_by_turn": castable_spell_by_turn,
        "curve_out_games": curve_out_games,
        "tapped_land_turns": tapped_land_turns,
    }


# --- Results ---


def print_results(stats: dict, classified: dict,
                  avg_cmc: float, pip_W: int, pip_U: int, pip_B: int, pip_G: int,
                  deck_name: str):
    total = NUM_GAMES

    print("\n" + "=" * 65)
    print(f"MONTE CARLO SIMULATION — {deck_name.upper()} ({NUM_GAMES:,} games, {NUM_TURNS} turns)")
    print("=" * 65)

    print(f"\n--- Dimension 1: Mana Base Adequacy ---")
    print(f"\n  Total mana available per turn:")
    print(f"  {'Turn':<6} {'Median':>7} {'P25':>7} {'P75':>7} {'Mean':>7}")
    print(f"  {'-'*34}")
    for t in range(1, NUM_TURNS + 1):
        data = stats["mana_by_turn"][t]
        med = statistics.median(data)
        p25 = statistics.quantiles(data, n=4)[0]
        p75 = statistics.quantiles(data, n=4)[2]
        mean = statistics.mean(data)
        print(f"    T{t:<4} {med:>7.0f} {p25:>7.0f} {p75:>7.0f} {mean:>7.1f}")

    mull = stats["mulligan_attempts"]
    print(f"\n  Mulligan stats (Commander London):")
    print(f"    Kept first hand:     {mull.get(0, 0)/total*100:>5.1f}%")
    print(f"    Free mulligan used:  {mull.get(1, 0)/total*100:>5.1f}%")
    print(f"    Paid mulligan (→6):  {mull.get(2, 0)/total*100:>5.1f}%")

    print(f"\n--- Dimension 2: Color Balance ---")
    print(f"\n  W, U, B, G sources per turn (median):")
    print(f"  {'Turn':<6} {'W':>4} {'U':>4} {'B':>4} {'G':>4}")
    print(f"  {'-'*24}")
    for t in range(1, NUM_TURNS + 1):
        w_med = statistics.median(stats["w_by_turn"][t])
        u_med = statistics.median(stats["u_by_turn"][t])
        b_med = statistics.median(stats["b_by_turn"][t])
        g_med = statistics.median(stats["g_by_turn"][t])
        print(f"    T{t:<4} {w_med:>4.0f} {u_med:>4.0f} {b_med:>4.0f} {g_med:>4.0f}")

    print(f"\n  Color screw (0 sources of a color):")
    for t in range(2, NUM_TURNS + 1):
        w_pct = stats["zero_w_by_turn"][t] / total * 100
        u_pct = stats["zero_u_by_turn"][t] / total * 100
        b_pct = stats["zero_b_by_turn"][t] / total * 100
        g_pct = stats["zero_g_by_turn"][t] / total * 100
        print(f"    T{t}: 0W={w_pct:.1f}% 0U={u_pct:.1f}% 0B={b_pct:.1f}% 0G={g_pct:.1f}%")

    print(f"\n--- Dimension 3: Curve Efficiency ---")
    print(f"\n  Commander castable (Atraxa, {{G}}{{W}}{{U}}{{B}}):")
    for t in range(3, NUM_TURNS + 1):
        count = stats["commander_by_turn"][t]
        print(f"    By T{t}: {count/total*100:.1f}%")
    if stats["commander_castable_turn"]:
        med = statistics.median(stats["commander_castable_turn"])
        print(f"    Median turn: {med:.1f}")

    print(f"\n  ETB tapped frequency:")
    for t in [1, 2]:
        pct_val = stats["tapped_land_turns"][t] / total * 100
        print(f"    T{t} land entered tapped: {pct_val:.1f}%")


def _run_chunk(args):
    decklist, metadata, num_games = args
    return run_simulation(decklist, metadata, num_games)


def merge_stats(chunks: list[dict]) -> dict:
    merged = {}
    first = chunks[0]
    for key in first:
        vals = [c[key] for c in chunks]
        sample = vals[0]
        if isinstance(sample, int):
            merged[key] = sum(vals)
        elif isinstance(sample, list):
            merged[key] = list(itertools.chain.from_iterable(vals))
        elif isinstance(sample, Counter):
            merged[key] = sum(vals, Counter())
        elif isinstance(sample, dict):
            sub_sample = next(iter(sample.values()), None)
            if isinstance(sub_sample, list):
                merged[key] = {k: list(itertools.chain.from_iterable(v[k] for v in vals))
                               for k in sample}
            else:
                merged[key] = {k: sum(v[k] for v in vals) for k in sample}
    return merged


def main():
    with open(METADATA_FILE) as f:
        metadata = json.load(f)

    for bracket, deck_id, deck_name in [
        (3, "phyrexian-perfection", "Phyrexian Perfection"),
        (4, "compleated-dominion", "Compleated Dominion"),
    ]:
        deck_file = PROJECT_ROOT / "data" / "commanders" / deck_id / "deck.json"
        if not deck_file.exists():
            print(f"Skipping {deck_name}: {deck_file} not found")
            continue

        configure_bracket(bracket)

        with open(deck_file) as f:
            deck_data = json.load(f)

        print(f"\nBuilding {deck_name} decklist (Bracket {bracket})...")
        decklist = build_decklist(deck_data)
        print(f"Decklist: {len(decklist)} cards")

        classified = classify_cards(decklist, metadata)
        result = print_static_analysis(decklist, metadata, classified, deck_name)
        avg_cmc, pip_W, pip_U, pip_B, pip_G = result

        n_workers = os.cpu_count() or 4
        chunk_size = NUM_GAMES // n_workers
        remainder = NUM_GAMES % n_workers
        chunks = [chunk_size + (1 if i < remainder else 0) for i in range(n_workers)]

        print(f"\nRunning {NUM_GAMES:,} game simulations ({n_workers} workers)...")
        with multiprocessing.Pool(n_workers) as pool:
            results = pool.map(_run_chunk, [(decklist, metadata, n) for n in chunks])
        stats = merge_stats(results)

        print_results(stats, classified, avg_cmc, pip_W, pip_U, pip_B, pip_G, deck_name)
        print("\n" + "=" * 65)


if __name__ == "__main__":
    main()
