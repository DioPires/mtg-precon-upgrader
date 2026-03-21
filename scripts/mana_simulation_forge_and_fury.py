#!/usr/bin/env python3
"""Monte Carlo mana base simulation for Forge & Fury (Korvold, Fae-Cursed King).

Simulates 100,000 games measuring mana production, color balance, and curve
efficiency turns 1-10 for the Bracket 4 Jund decklist.

Commander: Korvold, Fae-Cursed King ({2}{B}{R}{G}, CMC 5)
"""

import argparse
import itertools
import json
import multiprocessing
import os
import random
import re
import statistics
from collections import Counter
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DECK_FILE = PROJECT_ROOT / "data" / "commanders" / "forge-and-fury" / "deck.json"
METADATA_FILE = PROJECT_ROOT / "data" / "card-metadata.json"
JSON_OUTPUT = PROJECT_ROOT / "data" / "commanders" / "forge-and-fury" / "simulation.json"

NUM_GAMES = 100_000
NUM_TURNS = 10

# --- Mana cost parser ---


def parse_mana_cost(mana_cost: str) -> dict:
    """Parse mana_cost string into pip breakdown.

    "{2}{B}{R}{G}" -> {generic: 2, B: 1, R: 1, G: 1, total: 5}
    "{B}{B}{G}" -> {generic: 0, B: 2, R: 0, G: 1, total: 3}

    Split cards (//): parse first half only.
    """
    if "//" in mana_cost:
        mana_cost = mana_cost.split("//")[0].strip()

    result = {"generic": 0, "B": 0, "R": 0, "G": 0, "total": 0, "X": False}
    symbols = re.findall(r"\{([^}]+)\}", mana_cost)
    for sym in symbols:
        if sym == "X":
            result["X"] = True
        elif sym.isdigit():
            result["generic"] += int(sym)
        elif sym in ("B", "R", "G"):
            result[sym] += 1
        # Ignore other symbols (hybrid, phyrexian, etc.)
    result["total"] = result["generic"] + result["B"] + result["R"] + result["G"]
    return result


# --- Rock definitions ---

ROCK_DEFS = {
    "Sol Ring":           {"cmc": 1, "C": 2, "burst": False},
    "Arcane Signet":      {"cmc": 2, "C": 0, "burst": False, "flex_type": "any"},
    "Commander's Sphere": {"cmc": 3, "C": 0, "burst": False, "flex_type": "any"},
}

# --- Mana dork definitions ---

DORK_DEFS = {
    "Birds of Paradise": {"cmc": 1, "flex_type": "any"},
    "Gilded Goose":      {"cmc": 1, "flex_type": "any"},
}

# --- Creature ramp definitions ---

CREATURE_RAMP = {
    "Sakura-Tribe Elder": {"cmc": 2, "pips": {"generic": 1, "B": 0, "R": 0, "G": 1},
                           "fetch": "basic"},
}

# --- Spell ramp definitions ---

SPELL_RAMP = {
    "Nature's Lore":  {"cmc": 2, "pips": {"generic": 1, "B": 0, "R": 0, "G": 1},
                       "fetch": "forest_typed", "tapped": False},
    "Three Visits":   {"cmc": 2, "pips": {"generic": 1, "B": 0, "R": 0, "G": 1},
                       "fetch": "forest_typed", "tapped": False},
    "Farseek":        {"cmc": 2, "pips": {"generic": 1, "B": 0, "R": 0, "G": 1},
                       "fetch": "nonforest_typed", "tapped": True},
    "Cultivate":      {"cmc": 3, "pips": {"generic": 2, "B": 0, "R": 0, "G": 1},
                       "fetch": "basic_plus_hand"},
    "Kodama's Reach": {"cmc": 3, "pips": {"generic": 2, "B": 0, "R": 0, "G": 1},
                       "fetch": "basic_plus_hand"},
}

# --- Land definitions ---

# Lands with typed subtypes (for fetches and check lands)
SWAMP_TYPED_LANDS = {"Swamp", "Blood Crypt", "Overgrown Tomb"}
MOUNTAIN_TYPED_LANDS = {"Mountain", "Blood Crypt", "Stomping Ground"}
FOREST_TYPED_LANDS = {"Forest", "Overgrown Tomb", "Stomping Ground"}

BASIC_SWAMPS = {"Swamp"}
BASIC_MOUNTAINS = {"Mountain"}
BASIC_FORESTS = {"Forest"}
ALL_BASICS = BASIC_SWAMPS | BASIC_MOUNTAINS | BASIC_FORESTS

FETCH_LANDS = {"Bloodstained Mire", "Verdant Catacombs", "Wooded Foothills"}

# Lands producing exactly one color
B_ONLY_LANDS = {"Swamp"}
R_ONLY_LANDS = {"Mountain"}
G_ONLY_LANDS = {"Forest"}

# Dual-color land groups (for flex pool classification)
BR_DUAL_LANDS = {
    "Blood Crypt", "Luxury Suite", "Sulfurous Springs",
    "Blackcleave Cliffs", "Dragonskull Summit",
}
RG_DUAL_LANDS = {
    "Stomping Ground", "Spire Garden", "Karplusan Forest",
    "Copperline Gorge", "Rootbound Crag",
}
BG_DUAL_LANDS = {
    "Overgrown Tomb", "Undergrowth Stadium", "Llanowar Wastes",
    "Blooming Marsh", "Woodland Cemetery",
}
ANY_COLOR_LANDS = {"Command Tower", "Exotic Orchard"}

# Colorless-only lands
C_ONLY_LANDS = {"Fountainport", "Treasure Vault"}

# Always enters tapped
ALWAYS_TAPPED = set()  # None in this list for Jund Korvold


def land_enters_tapped(name: str, battlefield_lands: list[str], hand: list[str]) -> bool:
    """Determine if a land enters tapped given board + hand state."""
    if name in ALWAYS_TAPPED:
        return True

    # Fast lands: tapped if >= 3 lands on battlefield
    if name in {"Blackcleave Cliffs", "Copperline Gorge", "Blooming Marsh"}:
        return len(battlefield_lands) >= 3

    # Check lands: need matching typed land on board
    if name == "Dragonskull Summit":
        return not any(l in SWAMP_TYPED_LANDS or l in MOUNTAIN_TYPED_LANDS
                       for l in battlefield_lands)

    if name == "Rootbound Crag":
        return not any(l in MOUNTAIN_TYPED_LANDS or l in FOREST_TYPED_LANDS
                       for l in battlefield_lands)

    if name == "Woodland Cemetery":
        return not any(l in SWAMP_TYPED_LANDS or l in FOREST_TYPED_LANDS
                       for l in battlefield_lands)

    # Shock lands (Blood Crypt, Overgrown Tomb, Stomping Ground): always untapped (pay life)
    # Bond lands (Luxury Suite, Spire Garden, Undergrowth Stadium): always untapped (2+ opponents)
    # Pain lands (Sulfurous Springs, Karplusan Forest, Llanowar Wastes): always untapped
    # Command Tower, Exotic Orchard: always untapped
    # Fountainport, Treasure Vault: always untapped (colorless)
    return False


class ManaPool:
    """Tracks available B, R, G, C mana plus dual and tri-flex sources.

    Flex pools:
    - flex_BR: can produce B or R
    - flex_RG: can produce R or G
    - flex_BG: can produce B or G
    - flex_any: can produce B, R, or G
    - C: colorless only
    """

    def __init__(self):
        self.B = 0
        self.R = 0
        self.G = 0
        self.C = 0
        self.flex_BR = 0
        self.flex_RG = 0
        self.flex_BG = 0
        self.flex_any = 0

    @property
    def total(self):
        return (self.B + self.R + self.G + self.C
                + self.flex_BR + self.flex_RG + self.flex_BG + self.flex_any)

    def b_available(self) -> int:
        """Count of sources that can produce B."""
        return self.B + self.flex_BR + self.flex_BG + self.flex_any

    def r_available(self) -> int:
        """Count of sources that can produce R."""
        return self.R + self.flex_BR + self.flex_RG + self.flex_any

    def g_available(self) -> int:
        """Count of sources that can produce G."""
        return self.G + self.flex_RG + self.flex_BG + self.flex_any

    def _allocate(self, pips: dict) -> tuple[bool, dict | None]:
        """Greedy allocation for 3-color mana.

        1. Assign fixed B/R/G to their pips
        2. Assign dual flex to remaining colored needs (most constrained first)
        3. Assign flex_any to remaining colored needs
        4. All remaining goes to generic

        Returns (success, remaining_pool_dict) or (False, None).
        """
        need_B = pips.get("B", 0)
        need_R = pips.get("R", 0)
        need_G = pips.get("G", 0)
        need_generic = pips.get("generic", 0)

        avail = {
            "B": self.B, "R": self.R, "G": self.G, "C": self.C,
            "flex_BR": self.flex_BR, "flex_RG": self.flex_RG,
            "flex_BG": self.flex_BG, "flex_any": self.flex_any,
        }

        # Step 1: Assign fixed mono-color sources
        from_B = min(avail["B"], need_B)
        avail["B"] -= from_B
        need_B -= from_B

        from_R = min(avail["R"], need_R)
        avail["R"] -= from_R
        need_R -= from_R

        from_G = min(avail["G"], need_G)
        avail["G"] -= from_G
        need_G -= from_G

        # Step 2: Assign dual flex sources to remaining colored needs.
        # Allocate most-constrained color first to avoid deadlocks.
        # For each color, its dual flex sources are:
        #   B: flex_BR, flex_BG
        #   R: flex_BR, flex_RG
        #   G: flex_RG, flex_BG
        # Use narrowest-first: prefer the dual that helps fewer other unmet needs.

        def _supply_for(color, avail):
            """Count dual+any sources that can produce this color."""
            s = avail["flex_any"]
            if color == "B":
                s += avail["flex_BR"] + avail["flex_BG"]
            elif color == "R":
                s += avail["flex_BR"] + avail["flex_RG"]
            elif color == "G":
                s += avail["flex_RG"] + avail["flex_BG"]
            return s

        remaining = {"B": need_B, "R": need_R, "G": need_G}

        # Dual flex mapping: which duals serve which colors
        dual_for_color = {
            "B": ["flex_BR", "flex_BG"],
            "R": ["flex_BR", "flex_RG"],
            "G": ["flex_RG", "flex_BG"],
        }

        # Iteratively assign dual flex, most-constrained color first
        for _ in range(need_B + need_R + need_G):
            # Find color with most remaining need and fewest supply
            best_color = None
            best_ratio = float("inf")
            for color in ("B", "R", "G"):
                if remaining[color] <= 0:
                    continue
                supply = _supply_for(color, avail)
                if supply == 0:
                    return False, None
                ratio = supply / remaining[color]
                if ratio < best_ratio:
                    best_ratio = ratio
                    best_color = color

            if best_color is None:
                break

            # Try to use a dual source first (narrower = better)
            assigned = False
            for dual_key in dual_for_color[best_color]:
                if avail[dual_key] > 0:
                    avail[dual_key] -= 1
                    remaining[best_color] -= 1
                    assigned = True
                    break

            if not assigned:
                # Use flex_any
                if avail["flex_any"] > 0:
                    avail["flex_any"] -= 1
                    remaining[best_color] -= 1
                else:
                    return False, None

        if any(v > 0 for v in remaining.values()):
            return False, None

        # Step 3: Generic from all remaining
        leftover = sum(avail.values())
        if leftover < need_generic:
            return False, None

        # Spend generic: C first, then mono-color, then duals, then any
        spend_order = ["C", "B", "R", "G", "flex_BR", "flex_RG", "flex_BG", "flex_any"]
        gen_left = need_generic
        for key in spend_order:
            take = min(avail[key], gen_left)
            avail[key] -= take
            gen_left -= take
            if gen_left == 0:
                break

        return True, avail

    def can_cast(self, pips: dict) -> bool:
        """Check if we can cast a spell with the given pip requirements."""
        success, _ = self._allocate(pips)
        return success

    def after_spending(self, pips: dict) -> "ManaPool":
        """Return a new ManaPool after spending pips. Assumes can_cast is True."""
        success, avail = self._allocate(pips)
        if not success:
            return ManaPool()
        pool = ManaPool()
        pool.B = avail["B"]
        pool.R = avail["R"]
        pool.G = avail["G"]
        pool.C = avail["C"]
        pool.flex_BR = avail["flex_BR"]
        pool.flex_RG = avail["flex_RG"]
        pool.flex_BG = avail["flex_BG"]
        pool.flex_any = avail["flex_any"]
        return pool


def compute_land_mana(name: str, battlefield_lands: list[str]) -> tuple[int, int, int, int, int, int, int, int]:
    """Return (B, R, G, C, flex_BR, flex_RG, flex_BG, flex_any) for an untapped land."""

    # Basics
    if name == "Swamp":
        return (1, 0, 0, 0, 0, 0, 0, 0)
    if name == "Mountain":
        return (0, 1, 0, 0, 0, 0, 0, 0)
    if name == "Forest":
        return (0, 0, 1, 0, 0, 0, 0, 0)

    # BR duals
    if name in BR_DUAL_LANDS:
        return (0, 0, 0, 0, 1, 0, 0, 0)

    # RG duals
    if name in RG_DUAL_LANDS:
        return (0, 0, 0, 0, 0, 1, 0, 0)

    # BG duals
    if name in BG_DUAL_LANDS:
        return (0, 0, 0, 0, 0, 0, 1, 0)

    # Tri-color / any-color lands
    if name in ANY_COLOR_LANDS:
        return (0, 0, 0, 0, 0, 0, 0, 1)

    # Colorless-only lands
    if name in C_ONLY_LANDS:
        return (0, 0, 0, 1, 0, 0, 0, 0)

    # Fetches should be cracked; if on board treat as 0
    if name in FETCH_LANDS:
        return (0, 0, 0, 0, 0, 0, 0, 0)

    # Fallback: colorless
    return (0, 0, 0, 1, 0, 0, 0, 0)


# --- Decklist builder ---


def build_decklist(deck_data: dict) -> list[str]:
    """Build 99-card decklist from deck JSON."""
    cards = []
    for card in deck_data["decklist"]:
        qty = card.get("quantity", 1)
        cards.extend([card["name"]] * qty)
    return cards


def classify_cards(decklist: list[str], metadata: dict) -> dict:
    """Classify each card as land, rock, or spell.

    Rocks include mana rocks, dorks, creature ramp, and spell ramp.
    """
    ramp_names = set(ROCK_DEFS) | set(DORK_DEFS) | set(CREATURE_RAMP) | set(SPELL_RAMP)
    classified = {"lands": [], "rocks": [], "spells": []}
    for name in decklist:
        if name in ramp_names:
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
    """Mulligan if 0-1 mana sources (lands + rocks + dorks)."""
    ramp_names = set(ROCK_DEFS) | set(DORK_DEFS)
    sources = sum(1 for c in hand if c in land_set or c in ramp_names)
    return sources <= 1


def choose_bottom_cards(hand: list[str], count: int, metadata: dict,
                        land_set: set[str]) -> list[str]:
    """Choose cards to bottom (London mulligan). Bottom highest CMC non-source cards."""
    ramp_names = set(ROCK_DEFS) | set(DORK_DEFS) | set(CREATURE_RAMP) | set(SPELL_RAMP)
    candidates = [c for c in hand if c not in land_set and c not in ramp_names]
    candidates.sort(key=lambda c: metadata.get(c, {}).get("cmc", 0), reverse=True)
    return candidates[:count]


# --- Game state ---


class GameState:
    def __init__(self, decklist: list[str], metadata: dict, land_set: set[str]):
        self.library = list(decklist)
        random.shuffle(self.library)
        self.hand: list[str] = []
        self.battlefield_lands: list[str] = []
        self.tapped_lands: set[int] = set()  # indices into battlefield_lands
        self.battlefield_rocks: list[str] = []
        self.battlefield_dorks: list[str] = []  # dorks (produce mana next turn)
        self.dorks_active: list[str] = []  # dorks that can tap for mana this turn
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
        """Higher = play first. Untapped > tapped. Color-fixing > mono."""
        if name in FETCH_LANDS:
            return 20  # Always play and crack immediately

        tapped = land_enters_tapped(name, self.battlefield_lands, self.hand)
        base = 0 if tapped else 10

        # Tri/any-color lands get highest bonus
        if name in ANY_COLOR_LANDS:
            base += 6
        # Dual lands get moderate bonus
        elif name in BR_DUAL_LANDS or name in RG_DUAL_LANDS or name in BG_DUAL_LANDS:
            base += 4
        # Mono-color basic/utility gets small bonus
        elif name in B_ONLY_LANDS or name in R_ONLY_LANDS or name in G_ONLY_LANDS:
            base += 2

        return base

    def _color_need(self) -> tuple[int, int, int]:
        """Count B, R, G sources currently on battlefield for determining need."""
        pool = self.compute_mana_pool()
        return pool.b_available(), pool.r_available(), pool.g_available()

    def _resolve_fetch(self, fetch_name: str):
        """Resolve a fetch land: search library for appropriate typed lands.

        Bloodstained Mire -> Swamp or Mountain
        Verdant Catacombs -> Swamp or Forest
        Wooded Foothills -> Mountain or Forest
        """
        if fetch_name == "Bloodstained Mire":
            fetchable_types = SWAMP_TYPED_LANDS | MOUNTAIN_TYPED_LANDS
        elif fetch_name == "Verdant Catacombs":
            fetchable_types = SWAMP_TYPED_LANDS | FOREST_TYPED_LANDS
        elif fetch_name == "Wooded Foothills":
            fetchable_types = MOUNTAIN_TYPED_LANDS | FOREST_TYPED_LANDS
        else:
            return

        fetchable = [(i, card) for i, card in enumerate(self.library)
                     if card in fetchable_types]
        if not fetchable:
            return

        b_src, r_src, g_src = self._color_need()
        min_src = min(b_src, r_src, g_src)

        # Early game (<=2 lands): prefer shockland for dual color fixing
        if len(self.battlefield_lands) <= 2:
            # Determine which 2 colors are most needed
            color_needs = [("B", b_src), ("R", r_src), ("G", g_src)]
            color_needs.sort(key=lambda x: x[1])
            worst_two = {color_needs[0][0], color_needs[1][0]}

            # Map color pairs to shocklands
            shock_for_pair = {
                frozenset({"B", "R"}): "Blood Crypt",
                frozenset({"R", "G"}): "Stomping Ground",
                frozenset({"B", "G"}): "Overgrown Tomb",
            }
            target_shock = shock_for_pair.get(frozenset(worst_two))
            if target_shock:
                matches = [(i, c) for i, c in fetchable if c == target_shock]
                if matches:
                    idx, card = matches[0]
                    self.library.pop(idx)
                    self.battlefield_lands.append(card)
                    return

            # Try any fetchable shockland
            for shock in ("Blood Crypt", "Overgrown Tomb", "Stomping Ground"):
                matches = [(i, c) for i, c in fetchable if c == shock]
                if matches:
                    idx, card = matches[0]
                    self.library.pop(idx)
                    self.battlefield_lands.append(card)
                    return

        # Mid/late game: fetch basic of most-needed color
        color_needs = [("B", b_src, "Swamp"), ("R", r_src, "Mountain"), ("G", g_src, "Forest")]
        color_needs.sort(key=lambda x: x[1])

        for _, _, basic_name in color_needs:
            # Only fetch if this fetch can find this basic type
            if basic_name in fetchable_types:
                basics = [(i, c) for i, c in fetchable if c == basic_name]
                if basics:
                    idx, card = basics[0]
                    self.library.pop(idx)
                    self.battlefield_lands.append(card)
                    return

        # Fallback: first available
        idx, card = fetchable[0]
        self.library.pop(idx)
        self.battlefield_lands.append(card)

    def _fetch_typed_land(self, fetch_type: str, enters_tapped: bool):
        """Fetch a typed land from library for spell ramp.

        fetch_type values:
        - 'basic': basic land (Swamp/Mountain/Forest based on need)
        - 'forest_typed': Forest-subtype card (Forest, Overgrown Tomb, Stomping Ground)
        - 'nonforest_typed': non-Forest typed land (Blood Crypt, Stomping Ground, Overgrown Tomb, basics)
        - 'basic_plus_hand': basic to battlefield + basic to hand (Cultivate/Kodama's Reach)
        """
        b_src, r_src, g_src = self._color_need()

        if fetch_type == "basic":
            color_needs = [("B", b_src, "Swamp"), ("R", r_src, "Mountain"), ("G", g_src, "Forest")]
            color_needs.sort(key=lambda x: x[1])
            for _, _, basic_name in color_needs:
                targets = [i for i, c in enumerate(self.library) if c == basic_name]
                if targets:
                    idx = targets[0]
                    card = self.library.pop(idx)
                    self.battlefield_lands.append(card)
                    if enters_tapped:
                        self.tapped_lands.add(len(self.battlefield_lands) - 1)
                    return

        elif fetch_type == "forest_typed":
            # Nature's Lore / Three Visits: Forest card (untapped)
            # Early: prefer shockland for dual fixing
            if len(self.battlefield_lands) <= 3:
                # Prefer the dual that covers the most-needed non-G color
                color_needs = [("B", b_src, "Overgrown Tomb"), ("R", r_src, "Stomping Ground")]
                color_needs.sort(key=lambda x: x[1])
                for _, _, shock in color_needs:
                    targets = [i for i, c in enumerate(self.library) if c == shock]
                    if targets:
                        idx = targets[0]
                        card = self.library.pop(idx)
                        self.battlefield_lands.append(card)
                        if enters_tapped:
                            self.tapped_lands.add(len(self.battlefield_lands) - 1)
                        return
            # Fallback: basic Forest
            targets = [i for i, c in enumerate(self.library) if c == "Forest"]
            if targets:
                idx = targets[0]
                card = self.library.pop(idx)
                self.battlefield_lands.append(card)
                if enters_tapped:
                    self.tapped_lands.add(len(self.battlefield_lands) - 1)
                return

        elif fetch_type == "nonforest_typed":
            # Farseek: Plains/Island/Swamp/Mountain card (also typed duals)
            # In Jund: Swamp, Mountain, Blood Crypt, Stomping Ground, Overgrown Tomb
            fetchable_set = (SWAMP_TYPED_LANDS | MOUNTAIN_TYPED_LANDS | FOREST_TYPED_LANDS
                             | BASIC_SWAMPS | BASIC_MOUNTAINS) - {"Forest"}
            # Early: prefer shockland
            if len(self.battlefield_lands) <= 3:
                color_needs = [("B", b_src), ("R", r_src), ("G", g_src)]
                color_needs.sort(key=lambda x: x[1])
                worst_two = {color_needs[0][0], color_needs[1][0]}
                shock_for_pair = {
                    frozenset({"B", "R"}): "Blood Crypt",
                    frozenset({"R", "G"}): "Stomping Ground",
                    frozenset({"B", "G"}): "Overgrown Tomb",
                }
                target_shock = shock_for_pair.get(frozenset(worst_two))
                if target_shock and target_shock in fetchable_set:
                    targets = [i for i, c in enumerate(self.library) if c == target_shock]
                    if targets:
                        idx = targets[0]
                        card = self.library.pop(idx)
                        self.battlefield_lands.append(card)
                        if enters_tapped:
                            self.tapped_lands.add(len(self.battlefield_lands) - 1)
                        return
            # Fallback: basic of most-needed color (excluding Forest for Farseek)
            for basic in _basics_by_need(b_src, r_src, g_src, exclude_forest=True):
                targets = [i for i, c in enumerate(self.library) if c == basic]
                if targets:
                    idx = targets[0]
                    card = self.library.pop(idx)
                    self.battlefield_lands.append(card)
                    if enters_tapped:
                        self.tapped_lands.add(len(self.battlefield_lands) - 1)
                    return
            # Try any fetchable
            all_targets = [(i, c) for i, c in enumerate(self.library) if c in fetchable_set]
            if all_targets:
                idx, card = all_targets[0]
                self.library.pop(idx)
                self.battlefield_lands.append(card)
                if enters_tapped:
                    self.tapped_lands.add(len(self.battlefield_lands) - 1)

        elif fetch_type == "basic_plus_hand":
            # Cultivate / Kodama's Reach: one basic to battlefield (tapped), one to hand
            color_needs = [("B", b_src, "Swamp"), ("R", r_src, "Mountain"), ("G", g_src, "Forest")]
            color_needs.sort(key=lambda x: x[1])
            fetched_battlefield = False
            for _, _, basic_name in color_needs:
                if not fetched_battlefield:
                    targets = [i for i, c in enumerate(self.library) if c == basic_name]
                    if targets:
                        idx = targets[0]
                        card = self.library.pop(idx)
                        self.battlefield_lands.append(card)
                        self.tapped_lands.add(len(self.battlefield_lands) - 1)
                        fetched_battlefield = True
                        continue
                # Second basic goes to hand
                targets = [i for i, c in enumerate(self.library) if c == basic_name]
                if targets:
                    idx = targets[0]
                    card = self.library.pop(idx)
                    self.hand.append(card)
                    return
            # If we got battlefield but not hand, try any basic for hand
            if fetched_battlefield:
                for basic in ALL_BASICS:
                    targets = [i for i, c in enumerate(self.library) if c == basic]
                    if targets:
                        idx = targets[0]
                        card = self.library.pop(idx)
                        self.hand.append(card)
                        return

    def compute_mana_pool(self) -> ManaPool:
        """Calculate total available mana from untapped lands + rocks + dorks."""
        pool = ManaPool()

        for i, land in enumerate(self.battlefield_lands):
            if i in self.tapped_lands:
                continue
            b, r, g, c, fbr, frg, fbg, fany = compute_land_mana(land, self.battlefield_lands)
            pool.B += b
            pool.R += r
            pool.G += g
            pool.C += c
            pool.flex_BR += fbr
            pool.flex_RG += frg
            pool.flex_BG += fbg
            pool.flex_any += fany

        for rock in self.battlefield_rocks:
            rdef = ROCK_DEFS[rock]
            pool.C += rdef.get("C", 0)
            ft = rdef.get("flex_type")
            if ft == "any":
                pool.flex_any += 1

        # Active dorks (summoning sickness resolved)
        for dork in self.dorks_active:
            ddef = DORK_DEFS.get(dork)
            if ddef:
                ft = ddef.get("flex_type")
                if ft == "any":
                    pool.flex_any += 1

        return pool

    def play_turn(self, turn_number: int):
        """Simulate one turn."""
        if turn_number > 1:
            self.draw(1)

        # Untap all
        self.tapped_lands.clear()

        # Activate dorks that were on battlefield last turn
        self.dorks_active = list(self.battlefield_dorks)

        # Play best land from hand
        hand_lands = [(self._land_play_priority(c), c) for c in self.hand if self._is_land(c)]
        hand_lands.sort(reverse=True)

        if hand_lands:
            _, land_name = hand_lands[0]
            self.hand.remove(land_name)

            if land_name in FETCH_LANDS:
                self._resolve_fetch(land_name)
            else:
                tapped = land_enters_tapped(land_name, self.battlefield_lands, self.hand)
                self.battlefield_lands.append(land_name)
                if tapped:
                    self.tapped_lands.add(len(self.battlefield_lands) - 1)

        # Cast ramp from hand
        pool = self.compute_mana_pool()
        self._try_cast_ramp(pool)

        # Record final mana pool
        self.mana_per_turn.append(self.compute_mana_pool())

    def _try_cast_ramp(self, pool: ManaPool):
        """Try to cast mana rocks, dorks, spell ramp, and creature ramp from hand."""
        priority_order = [
            ("rock", "Sol Ring"),
            ("rock", "Arcane Signet"),
            ("dork", "Birds of Paradise"),
            ("dork", "Gilded Goose"),
            ("spell_ramp", "Nature's Lore"),
            ("spell_ramp", "Three Visits"),
            ("spell_ramp", "Farseek"),
            ("creature_ramp", "Sakura-Tribe Elder"),
            ("rock", "Commander's Sphere"),
            ("spell_ramp", "Cultivate"),
            ("spell_ramp", "Kodama's Reach"),
        ]

        for ramp_type, name in priority_order:
            if name not in self.hand:
                continue

            if ramp_type == "rock":
                rdef = ROCK_DEFS[name]
                pips = parse_mana_cost(self.metadata.get(name, {}).get("mana_cost", ""))
                if pool.can_cast(pips):
                    pool = pool.after_spending(pips)
                    self.hand.remove(name)
                    self.battlefield_rocks.append(name)
                    # Add rock's mana to pool for subsequent casts
                    pool.C += rdef.get("C", 0)
                    ft = rdef.get("flex_type")
                    if ft == "any":
                        pool.flex_any += 1

            elif ramp_type == "dork":
                # Dorks cost {G} (CMC 1)
                pips = {"generic": 0, "B": 0, "R": 0, "G": 1}
                if pool.can_cast(pips):
                    pool = pool.after_spending(pips)
                    self.hand.remove(name)
                    self.battlefield_dorks.append(name)
                    # Summoning sickness: mana available next turn

            elif ramp_type == "spell_ramp":
                sramp = SPELL_RAMP[name]
                pips = sramp["pips"]
                if pool.can_cast(pips):
                    pool = pool.after_spending(pips)
                    self.hand.remove(name)
                    self._fetch_typed_land(sramp["fetch"], sramp.get("tapped", True))
                    # Recompute pool after fetching
                    pool = self.compute_mana_pool()

            elif ramp_type == "creature_ramp":
                cramp = CREATURE_RAMP[name]
                pips = cramp["pips"]
                if pool.can_cast(pips):
                    pool = pool.after_spending(pips)
                    self.hand.remove(name)
                    self._fetch_typed_land(cramp["fetch"], cramp.get("tapped", False))
                    pool = self.compute_mana_pool()


def _basics_by_need(b_src: int, r_src: int, g_src: int,
                    exclude_forest: bool = False) -> list[str]:
    """Return basic land names ordered by color need (most-needed first)."""
    needs = [("Swamp", b_src), ("Mountain", r_src)]
    if not exclude_forest:
        needs.append(("Forest", g_src))
    needs.sort(key=lambda x: x[1])
    return [name for name, _ in needs]


def commander_mulligan(decklist: list[str], metadata: dict,
                       land_set: set[str]) -> GameState:
    """Commander mulligan: free first, then London."""
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
    """Return list of castable non-ramp spells from hand."""
    ramp_cards = set(ROCK_DEFS) | set(DORK_DEFS) | set(CREATURE_RAMP) | set(SPELL_RAMP)
    castable = []
    for card in state.hand:
        if card in ramp_cards or card in state.land_set:
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
                          classified: dict) -> tuple[float, int, int, int]:
    """Print pre-simulation static analysis. Returns (avg_cmc, pip_B, pip_R, pip_G)."""
    print("=" * 65)
    print("STATIC ANALYSIS — FORGE & FURY (BRACKET 4)")
    print("=" * 65)

    print(f"\n--- Deck Composition ---")
    print(f"Total cards (excl. commander): {len(decklist)}")
    print(f"Lands: {len(classified['lands'])}")
    print(f"Mana rocks/dorks/ramp: {len(classified['rocks'])}")
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

    total_B, total_R, total_G = 0, 0, 0
    for name in decklist:
        meta = metadata.get(name, {})
        mc = meta.get("mana_cost", "")
        if "Land" in meta.get("type_line", ""):
            continue
        pips = parse_mana_cost(mc)
        total_B += pips["B"]
        total_R += pips["R"]
        total_G += pips["G"]

    total_pips = total_B + total_R + total_G
    b_ratio = total_B / total_pips * 100 if total_pips > 0 else 0
    r_ratio = total_R / total_pips * 100 if total_pips > 0 else 0
    g_ratio = total_G / total_pips * 100 if total_pips > 0 else 0

    print(f"\n--- Pip Demand ---")
    print(f"  Total {{B}} pips: {total_B}")
    print(f"  Total {{R}} pips: {total_R}")
    print(f"  Total {{G}} pips: {total_G}")
    print(f"  Ratio: {b_ratio:.0f}% B / {r_ratio:.0f}% R / {g_ratio:.0f}% G")

    # Mana source inventory
    lands = classified["lands"]
    b_lands = sum(1 for l in lands if l in B_ONLY_LANDS or l in BR_DUAL_LANDS or l in BG_DUAL_LANDS or l in ANY_COLOR_LANDS)
    r_lands = sum(1 for l in lands if l in R_ONLY_LANDS or l in BR_DUAL_LANDS or l in RG_DUAL_LANDS or l in ANY_COLOR_LANDS)
    g_lands = sum(1 for l in lands if l in G_ONLY_LANDS or l in RG_DUAL_LANDS or l in BG_DUAL_LANDS or l in ANY_COLOR_LANDS)
    br_count = sum(1 for l in lands if l in BR_DUAL_LANDS)
    rg_count = sum(1 for l in lands if l in RG_DUAL_LANDS)
    bg_count = sum(1 for l in lands if l in BG_DUAL_LANDS)
    any_count = sum(1 for l in lands if l in ANY_COLOR_LANDS)
    c_count = sum(1 for l in lands if l in C_ONLY_LANDS)
    fetch_count = sum(1 for l in lands if l in FETCH_LANDS)

    print(f"\n--- Mana Source Inventory ---")
    print(f"  Lands: {len(lands)} total")
    print(f"    B-producing: {b_lands}  R-producing: {r_lands}  G-producing: {g_lands}")
    print(f"    BRG any-color: {any_count}")
    print(f"    BR duals: {br_count}  RG duals: {rg_count}  BG duals: {bg_count}")
    print(f"    C-only: {c_count}  Fetch: {fetch_count}")

    # Rock/dork inventory
    rock_count = sum(1 for r in classified["rocks"] if r in ROCK_DEFS)
    dork_count = sum(1 for r in classified["rocks"] if r in DORK_DEFS)
    creature_ramp_count = sum(1 for r in classified["rocks"] if r in CREATURE_RAMP)
    spell_ramp_count = sum(1 for r in classified["rocks"] if r in SPELL_RAMP)
    print(f"  Rocks: {rock_count}  Dorks: {dork_count}  "
          f"Creature ramp: {creature_ramp_count}  Spell ramp: {spell_ramp_count}")

    recommended = round(36 + (avg_cmc - 3.0) * 2)
    total_ramp = len(classified["rocks"])
    print(f"\n--- Land Count Heuristic ---")
    print(f"  Avg CMC: {avg_cmc:.2f}")
    print(f"  Current lands: {len(lands)}")
    print(f"  Heuristic recommendation: ~{recommended} lands")
    delta = len(lands) - recommended
    if delta >= 0:
        print(f"  Status: adequate ({len(lands)} >= {recommended})")
    else:
        print(f"  Status: light ({len(lands)} < {recommended}, delta = {abs(delta)})")
    print(f"  Note: {total_ramp} ramp pieces compensate for lower land count")

    return avg_cmc, total_B, total_R, total_G


# --- Simulation ---


def run_simulation(decklist: list[str], metadata: dict, num_games: int = NUM_GAMES) -> dict:
    """Run num_games simulations and collect stats."""
    land_set = set()
    for name in set(decklist):
        meta = metadata.get(name, {})
        if "Land" in meta.get("type_line", ""):
            land_set.add(name)

    mana_by_turn = {t: [] for t in range(1, NUM_TURNS + 1)}
    b_by_turn = {t: [] for t in range(1, NUM_TURNS + 1)}
    r_by_turn = {t: [] for t in range(1, NUM_TURNS + 1)}
    g_by_turn = {t: [] for t in range(1, NUM_TURNS + 1)}
    hand_land_counts = Counter()
    mulligan_attempts = Counter()

    zero_b_by_turn = {t: 0 for t in range(1, NUM_TURNS + 1)}
    zero_r_by_turn = {t: 0 for t in range(1, NUM_TURNS + 1)}
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
            total_mana = pool.total
            b_avail = pool.b_available()
            r_avail = pool.r_available()
            g_avail = pool.g_available()

            mana_by_turn[t].append(total_mana)
            b_by_turn[t].append(b_avail)
            r_by_turn[t].append(r_avail)
            g_by_turn[t].append(g_avail)

            if b_avail == 0:
                zero_b_by_turn[t] += 1
            if r_avail == 0:
                zero_r_by_turn[t] += 1
            if g_avail == 0:
                zero_g_by_turn[t] += 1

            # Commander: Korvold, Fae-Cursed King {2}{B}{R}{G}
            cmd_pips = {"generic": 2, "B": 1, "R": 1, "G": 1}
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
        "b_by_turn": b_by_turn,
        "r_by_turn": r_by_turn,
        "g_by_turn": g_by_turn,
        "hand_land_counts": hand_land_counts,
        "mulligan_attempts": mulligan_attempts,
        "zero_b_by_turn": zero_b_by_turn,
        "zero_r_by_turn": zero_r_by_turn,
        "zero_g_by_turn": zero_g_by_turn,
        "commander_castable_turn": commander_castable_turn,
        "commander_by_turn": commander_by_turn,
        "castable_spell_by_turn": castable_spell_by_turn,
        "curve_out_games": curve_out_games,
        "tapped_land_turns": tapped_land_turns,
    }


# --- Results ---


def print_results(stats: dict, classified: dict,
                  avg_cmc: float, pip_B: int, pip_R: int, pip_G: int):
    """Print simulation results across all three dimensions."""
    total = NUM_GAMES

    print("\n" + "=" * 65)
    print(f"MONTE CARLO SIMULATION — FORGE & FURY ({NUM_GAMES:,} games, {NUM_TURNS} turns)")
    print("=" * 65)

    # --- Dimension 1: Mana Base ---
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
    print(f"    Free mulligan used:  {mull.get(1, 0)/total*100:>5.1f}% (redraw 7, no penalty)")
    print(f"    Paid mulligan (->6): {mull.get(2, 0)/total*100:>5.1f}% (redraw 7, bottom 1)")

    print(f"\n  Opening hand (post-mulligan):")
    print(f"    Land count distribution:")
    for lands in range(8):
        count = stats["hand_land_counts"].get(lands, 0)
        if count > 0:
            bar = "#" * int(count / total * 50)
            print(f"      {lands} lands: {count/total*100:>5.1f}% {bar}")

    # --- Dimension 2: Color Balance ---
    print(f"\n--- Dimension 2: Color Balance ---")
    print(f"\n  B, R, G sources per turn (can-produce count):")
    print(f"  {'Turn':<6} {'B med':>6} {'B avg':>6} {'R med':>6} {'R avg':>6} {'G med':>6} {'G avg':>6}")
    print(f"  {'-'*42}")
    for t in range(1, NUM_TURNS + 1):
        b_med = statistics.median(stats["b_by_turn"][t])
        b_mean = statistics.mean(stats["b_by_turn"][t])
        r_med = statistics.median(stats["r_by_turn"][t])
        r_mean = statistics.mean(stats["r_by_turn"][t])
        g_med = statistics.median(stats["g_by_turn"][t])
        g_mean = statistics.mean(stats["g_by_turn"][t])
        print(f"    T{t:<4} {b_med:>6.0f} {b_mean:>6.1f} {r_med:>6.0f} {r_mean:>6.1f} {g_med:>6.0f} {g_mean:>6.1f}")

    print(f"\n  Color screw (0 sources of a color):")
    for t in range(2, NUM_TURNS + 1):
        b_pct = stats["zero_b_by_turn"][t] / total * 100
        r_pct = stats["zero_r_by_turn"][t] / total * 100
        g_pct = stats["zero_g_by_turn"][t] / total * 100
        print(f"    T{t}: 0 B = {b_pct:.1f}%, 0 R = {r_pct:.1f}%, 0 G = {g_pct:.1f}%")

    pip_total = pip_B + pip_R + pip_G
    b_demand = pip_B / pip_total * 100 if pip_total > 0 else 0
    r_demand = pip_R / pip_total * 100 if pip_total > 0 else 0
    g_demand = pip_G / pip_total * 100 if pip_total > 0 else 0

    t3_b = statistics.mean(stats["b_by_turn"][3])
    t3_r = statistics.mean(stats["r_by_turn"][3])
    t3_g = statistics.mean(stats["g_by_turn"][3])
    t3_total = t3_b + t3_r + t3_g
    b_supply = t3_b / t3_total * 100 if t3_total > 0 else 0
    r_supply = t3_r / t3_total * 100 if t3_total > 0 else 0
    g_supply = t3_g / t3_total * 100 if t3_total > 0 else 0

    print(f"\n  Pip demand vs supply ratio (T3 avg):")
    print(f"    Demand: {b_demand:.0f}% B / {r_demand:.0f}% R / {g_demand:.0f}% G")
    print(f"    Supply: {b_supply:.0f}% B / {r_supply:.0f}% R / {g_supply:.0f}% G")

    # --- Dimension 3: Curve Efficiency ---
    print(f"\n--- Dimension 3: Curve Efficiency ---")

    print(f"\n  Commander castable (Korvold, Fae-Cursed King, {{2}}{{B}}{{R}}{{G}}):")
    for t in range(3, NUM_TURNS + 1):
        count = stats["commander_by_turn"][t]
        print(f"    By T{t}: {count/total*100:.1f}%")
    if stats["commander_castable_turn"]:
        med = statistics.median(stats["commander_castable_turn"])
        print(f"    Median turn: {med:.1f}")

    print(f"\n  Castable spell from hand (non-ramp, color-aware):")
    for t in range(1, NUM_TURNS + 1):
        pct = stats["castable_spell_by_turn"][t] / total * 100
        print(f"    T{t}: {pct:.1f}%")

    print(f"\n  Curve-out rate (cast something T1-T4): "
          f"{stats['curve_out_games']/total*100:.1f}%")

    print(f"\n  ETB tapped frequency:")
    for t in [1, 2]:
        pct = stats["tapped_land_turns"][t] / total * 100
        print(f"    T{t} land entered tapped: {pct:.1f}%")

    # --- Assessment ---
    print(f"\n--- Mana Base Assessment ---")

    med_t1 = statistics.median(stats["mana_by_turn"][1])
    med_t3 = statistics.median(stats["mana_by_turn"][3])
    med_t5 = statistics.median(stats["mana_by_turn"][5])
    med_last = statistics.median(stats["mana_by_turn"][NUM_TURNS])
    mull = stats["mulligan_attempts"]
    paid_mull_rate = mull.get(2, 0) / total * 100

    print(f"\n  Median mana: T1={med_t1:.0f}, T3={med_t3:.0f}, "
          f"T5={med_t5:.0f}, T{NUM_TURNS}={med_last:.0f}")

    land_count = len(classified["lands"])
    recommended = round(36 + (avg_cmc - 3.0) * 2)
    if land_count >= recommended:
        print(f"  Land count: {land_count} (adequate for avg CMC {avg_cmc:.2f})")
    else:
        print(f"  Land count: {land_count} (light for avg CMC {avg_cmc:.2f}, "
              f"heuristic suggests ~{recommended})")

    if paid_mull_rate < 5:
        print(f"  Paid mulligan rate: {paid_mull_rate:.1f}% — acceptable")
    else:
        print(f"  Paid mulligan rate: {paid_mull_rate:.1f}% — consider adding lands/rocks")

    # Color balance assessment
    max_deficit = 0
    worst_color = ""
    for color, demand, supply in [("B", b_demand, b_supply),
                                  ("R", r_demand, r_supply),
                                  ("G", g_demand, g_supply)]:
        deficit = demand - supply
        if deficit > max_deficit:
            max_deficit = deficit
            worst_color = color

    if max_deficit < 10:
        print(f"  Color balance: well-matched (all within {max_deficit:.0f}% demand-supply gap)")
    else:
        print(f"  Color balance: {worst_color} undersupplied "
              f"({max_deficit:.0f}% gap) — consider more {worst_color} sources")

    # Commander timing (Korvold CMC 5)
    cmd_by_t4 = stats["commander_by_turn"][4] / total * 100
    cmd_by_t5 = stats["commander_by_turn"][5] / total * 100
    if cmd_by_t4 > 50:
        print(f"  Commander by T4: {cmd_by_t4:.0f}% — ahead of curve for 5-CMC")
    elif cmd_by_t5 > 50:
        print(f"  Commander by T5: {cmd_by_t5:.0f}% — on curve for 5-CMC commander")
    else:
        print(f"  Commander by T5: {cmd_by_t5:.0f}% — below 50%, ramp insufficient for 5-CMC")

    t1_tapped = stats["tapped_land_turns"][1] / total * 100
    t2_tapped = stats["tapped_land_turns"][2] / total * 100
    if t1_tapped < 10 and t2_tapped < 15:
        print(f"  ETB tapped T1/T2: {t1_tapped:.0f}%/{t2_tapped:.0f}% — minimal tempo loss")
    else:
        print(f"  ETB tapped T1/T2: {t1_tapped:.0f}%/{t2_tapped:.0f}% — significant tempo drag")


def _run_chunk(args):
    """Worker function for multiprocessing."""
    decklist, metadata, num_games = args
    return run_simulation(decklist, metadata, num_games)


def merge_stats(chunks: list[dict]) -> dict:
    """Merge stats dicts from parallel simulation chunks."""
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


# --- JSON export ---


def _pct(count: int, total: int) -> float:
    return round(count / total * 100, 1) if total > 0 else 0.0


def _r1(val: float) -> float:
    return round(val, 1)


def _mana_stats(data: list) -> dict:
    if not data:
        return {"median": 0.0, "p25": 0.0, "p75": 0.0, "mean": 0.0}
    q = statistics.quantiles(data, n=4)
    return {
        "median": _r1(statistics.median(data)),
        "p25": _r1(q[0]),
        "p75": _r1(q[2]),
        "mean": _r1(statistics.mean(data)),
    }


def _median_turn_from_cumulative(by_turn: dict) -> int | None:
    for t in range(1, NUM_TURNS + 1):
        if by_turn.get(str(t), 0) >= 50.0:
            return t
    return None


def export_json(stats: dict, classified: dict, decklist: list[str],
                metadata: dict, avg_cmc: float) -> dict:
    """Build JSON output matching simulation.json schema."""
    total = NUM_GAMES

    # manaByTurn
    mana_by_turn = {}
    for t in range(1, NUM_TURNS + 1):
        mana_by_turn[str(t)] = _mana_stats(stats["mana_by_turn"][t])

    # mulliganStats
    mull = stats["mulligan_attempts"]
    mulligan_stats = {
        "keptFirst": _pct(mull.get(0, 0), total),
        "freeMulligan": _pct(mull.get(1, 0), total),
        "paidMulligan": _pct(sum(count for attempt, count in mull.items() if attempt >= 2), total),
    }

    # openingHand
    land_dist = {}
    for n in range(8):
        count = stats["hand_land_counts"].get(n, 0)
        if count > 0:
            land_dist[str(n)] = _pct(count, total)
    opening_hand = {"landDistribution": land_dist}

    # commanderTiming
    cmd_by_turn = {}
    for t in range(1, NUM_TURNS + 1):
        cmd_by_turn[str(t)] = _pct(stats["commander_by_turn"][t], total)

    commander_timing = {
        "name": "Korvold, Fae-Cursed King",
        "cmc": 5,
        "byTurn": cmd_by_turn,
        "medianTurn": _median_turn_from_cumulative(cmd_by_turn),
    }

    # colorBalance
    colors = ["B", "R", "G"]
    color_keys = {"B": "b", "R": "r", "G": "g"}
    color_by_turn = {}
    for t in range(1, NUM_TURNS + 1):
        turn_data = {}
        for color in colors:
            key = f"{color_keys[color]}_by_turn"
            data = stats[key][t]
            turn_data[color] = {
                "median": _r1(statistics.median(data)),
                "mean": _r1(statistics.mean(data)),
            }
        color_by_turn[str(t)] = turn_data

    color_screw_by_turn = {}
    for t in range(1, NUM_TURNS + 1):
        turn_screw = {}
        for color in colors:
            key = f"zero_{color_keys[color]}_by_turn"
            turn_screw[color] = _pct(stats[key][t], total)
        color_screw_by_turn[str(t)] = turn_screw

    color_balance = {
        "colors": colors,
        "byTurn": color_by_turn,
        "colorScrewByTurn": color_screw_by_turn,
    }

    # curveEfficiency
    castable_by_turn = {}
    for t in range(1, NUM_TURNS + 1):
        castable_by_turn[str(t)] = _pct(stats["castable_spell_by_turn"][t], total)

    curve_efficiency = {
        "castableByTurn": castable_by_turn,
        "curveOutRate": _pct(stats["curve_out_games"], total),
    }

    # specialMetrics
    etb_tapped = {}
    for t in stats["tapped_land_turns"]:
        etb_tapped[str(t)] = _pct(stats["tapped_land_turns"][t], total)

    special_metrics = {
        "cascadeReadiness": None,
        "etbTapped": etb_tapped,
    }

    # assessment
    t4_median = mana_by_turn["4"]["median"]
    t5_median = mana_by_turn["5"]["median"]

    if t5_median >= avg_cmc + 2:
        mana_adequacy = "strong"
    elif t4_median >= avg_cmc:
        mana_adequacy = "adequate"
    else:
        mana_adequacy = "light"

    paid_pct = mulligan_stats["paidMulligan"]
    if paid_pct < 3:
        mulligan_verdict = "excellent"
    elif paid_pct < 5:
        mulligan_verdict = "acceptable"
    else:
        mulligan_verdict = "concerning"

    cmd_median = commander_timing["medianTurn"]
    cmd_cmc = 5
    if cmd_median is None:
        cmd_timing = "unreliable"
    elif cmd_median <= cmd_cmc - 1:
        cmd_timing = "ahead of curve"
    elif cmd_median <= cmd_cmc:
        cmd_timing = "on curve"
    else:
        cmd_timing = "behind curve"

    assessment = {
        "manaAdequacy": mana_adequacy,
        "mulliganVerdict": mulligan_verdict,
        "commanderTiming": cmd_timing,
    }

    return {
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
            "avgCmc": _r1(avg_cmc),
        },
        "manaByTurn": mana_by_turn,
        "mulliganStats": mulligan_stats,
        "openingHand": opening_hand,
        "commanderTiming": commander_timing,
        "colorBalance": color_balance,
        "curveEfficiency": curve_efficiency,
        "specialMetrics": special_metrics,
        "assessment": assessment,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Monte Carlo mana base simulation for Forge & Fury (Korvold)")
    parser.add_argument("--json", action="store_true",
                        help="Write simulation.json instead of console output")
    args = parser.parse_args()

    with open(DECK_FILE) as f:
        deck_data = json.load(f)
    with open(METADATA_FILE) as f:
        metadata = json.load(f)

    print("Building Forge & Fury decklist...")
    decklist = build_decklist(deck_data)
    print(f"Decklist: {len(decklist)} cards")

    classified = classify_cards(decklist, metadata)

    if not args.json:
        avg_cmc, pip_B, pip_R, pip_G = print_static_analysis(decklist, metadata, classified)
    else:
        cmcs = []
        for name in decklist:
            meta = metadata.get(name, {})
            if "Land" not in meta.get("type_line", ""):
                cmc = meta.get("cmc", 0)
                if isinstance(cmc, (int, float)):
                    cmcs.append(int(cmc))
        avg_cmc = statistics.mean(cmcs) if cmcs else 0
        pip_B, pip_R, pip_G = 0, 0, 0  # not needed for JSON path

    n_workers = os.cpu_count() or 4
    chunk_size = NUM_GAMES // n_workers
    remainder = NUM_GAMES % n_workers
    chunks = [chunk_size + (1 if i < remainder else 0) for i in range(n_workers)]

    print(f"Running {NUM_GAMES:,} game simulations ({n_workers} workers)...")
    with multiprocessing.Pool(n_workers) as pool:
        results = pool.map(_run_chunk, [(decklist, metadata, n) for n in chunks])
    stats = merge_stats(results)

    if args.json:
        result = export_json(stats, classified, decklist, metadata, avg_cmc)
        JSON_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        with open(JSON_OUTPUT, "w") as f:
            json.dump(result, f, indent=2)
        print(f"Written: {JSON_OUTPUT}")
        print(f"Size: {JSON_OUTPUT.stat().st_size / 1024:.1f} KB")
    else:
        print_results(stats, classified, avg_cmc, pip_B, pip_R, pip_G)
        print("\n" + "=" * 65)


if __name__ == "__main__":
    main()
