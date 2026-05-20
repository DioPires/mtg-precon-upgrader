#!/usr/bin/env python3
"""Monte Carlo mana base simulation for Hidden Legion (The Ur-Dragon).

Simulates 100,000 games measuring 5-color mana production, changeling
deployment, and Ur-Dragon castability turns 1-10 for the WUBRG
changeling-omnitype-tribal deck.

Commander: The Ur-Dragon ({4}{W}{U}{B}{R}{G}, MV 9). His eminence makes
OTHER Dragon spells (= every changeling, since changelings are Dragons)
cost {1} less to cast from anywhere — does not discount Ur-Dragon itself.

Key engine state (Hidden Legion-specific):
- engineReadiness: probability Ur-Dragon is castable AND >=1 changeling
  in play. This is the deck's core operating condition — Ur-Dragon on
  the battlefield with a tribe of Dragons (real + changeling).
- changelingsByTurn: median changelings in play across turns 1-10. Drives
  Eminence-discount value, Vanquisher's Banner draws, and Sliver Legion
  pump curve.
- urDragonCastableByTurn: cumulative % of games where Ur-Dragon is
  castable by turn t. Does not require commander to actually be cast.

Cost reduction interactions modeled:
- Ur-Dragon Eminence (always active): changeling/Dragon spells -1 generic.
- Dragonlord's Servant on battlefield: another -1 generic.
- Morophon, the Boundless on battlefield with Dragon chosen: -1 of each
  color (W,U,B,R,G) on Dragon spells; reduces only colored cost.
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
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
METADATA_FILE = PROJECT_ROOT / "data" / "card-metadata.json"
JSON_OUTPUT = PROJECT_ROOT / "data" / "commanders" / "hidden-legion" / "simulation.json"

NUM_GAMES = 100_000
NUM_TURNS = 10


# --- Mana cost parser ---

def parse_mana_cost(mana_cost: str) -> dict:
    """Parse mana_cost string into pip breakdown."""
    if not mana_cost:
        return {"generic": 0, "W": 0, "U": 0, "B": 0, "R": 0, "G": 0, "total": 0, "X": False}
    if "//" in mana_cost:
        mana_cost = mana_cost.split("//")[0].strip()

    result = {"generic": 0, "W": 0, "U": 0, "B": 0, "R": 0, "G": 0, "total": 0, "X": False}
    for sym in re.findall(r"\{([^}]+)\}", mana_cost):
        if sym == "X":
            result["X"] = True
        elif sym.isdigit():
            result["generic"] += int(sym)
        elif sym in ("W", "U", "B", "R", "G"):
            result[sym] += 1
    result["total"] = (result["generic"] + result["W"] + result["U"]
                       + result["B"] + result["R"] + result["G"])
    return result


# --- Rock definitions ---

ROCK_DEFS = {
    "Sol Ring":      {"cmc": 1, "colors": frozenset({"C"}), "count": 2},
    "Arcane Signet": {"cmc": 2, "colors": frozenset({"W", "U", "B", "R", "G"}), "count": 1},
    "Fellwar Stone": {"cmc": 2, "colors": frozenset({"W", "U", "B", "R", "G"}), "count": 1},
}


# --- Ramp spell definitions ---

RAMP_DEFS = {
    "Three Visits":   {"mana_cost": "{1}{G}", "fetch_type": "forest_typed", "tapped": False},
    "Nature's Lore":  {"mana_cost": "{1}{G}", "fetch_type": "forest_typed", "tapped": False},
}


# --- Mana dork definitions (creatures that tap for mana) ---
# Modeled as static permanents that produce mana the turn AFTER they enter
# (summoning sickness). All require >=1 changeling-or-Elf for full output;
# for simulation simplicity, Priest/Archdruid/Channeler get conservative
# estimates assuming 1 Elf-equivalent (self) at entry, growing with board.

# Three Tree Mascot is BOTH a changeling AND a 1-mana-for-1-of-any activated
# ability. Modeled here as a dork (mana source), AND ALSO tracked as a
# changeling in the simulation's changeling-count metric.

DORK_NAMES = {
    "Priest of Titania",
    "Elvish Archdruid",
    "Wirewood Channeler",
    "Bloom Tender",
    "Three Tree Mascot",
}


def dork_sources(name: str, board: dict) -> list[frozenset]:
    """Return mana sources a dork produces given current board state.

    board is a dict with keys: elves, changelings, colors_present (set).
    All dorks except Three Tree Mascot are tap-for-mana (summoning sickness applies);
    Three Tree Mascot's activated ability ({1}: add 1 of any) is modeled as a
    flexible color-fixer that contributes net 0 mana to the pool (costs 1 to
    produce 1) — but in practice it converts colorless to colored, which the
    allocator already handles via greedy color assignment. We model Three Tree
    Mascot as a Mana-Confluence-equivalent flexible source (1 mana of any color).
    """
    elves = max(1, board.get("elves", 1))
    colors_present = board.get("colors_present", set())

    if name == "Priest of Titania" or name == "Elvish Archdruid":
        return [frozenset({"G"})] * elves
    if name == "Wirewood Channeler":
        return [frozenset({"W", "U", "B", "R", "G"})] * elves
    if name == "Bloom Tender":
        colors = colors_present & {"W", "U", "B", "R", "G"}
        if not colors:
            colors = {"G"}
        return [frozenset({c}) for c in colors]
    if name == "Three Tree Mascot":
        return [frozenset({"W", "U", "B", "R", "G"})]
    return []


# --- Land tables for Hidden Legion ---

BASIC_LANDS = {"Plains", "Island", "Swamp", "Mountain", "Forest"}

# Triomes always ETB tapped
ALWAYS_TAPPED = {
    "Indatha Triome",  # WBG
    "Ketria Triome",   # GUR
    "Raugrin Triome",  # URW
    "Savai Triome",    # RWB
    "Zagoth Triome",   # BGU
    "Path of Ancestry",
}

# Land color identity
LAND_COLORS: dict[str, frozenset] = {
    # Basics
    "Plains":   frozenset({"W"}),
    "Island":   frozenset({"U"}),
    "Swamp":    frozenset({"B"}),
    "Mountain": frozenset({"R"}),
    "Forest":   frozenset({"G"}),

    # Triomes
    "Indatha Triome":  frozenset({"W", "B", "G"}),
    "Ketria Triome":   frozenset({"G", "U", "R"}),
    "Raugrin Triome":  frozenset({"U", "R", "W"}),
    "Savai Triome":    frozenset({"R", "W", "B"}),
    "Zagoth Triome":   frozenset({"B", "G", "U"}),

    # Shock lands
    "Hallowed Fountain": frozenset({"W", "U"}),
    "Watery Grave":      frozenset({"U", "B"}),
    "Blood Crypt":       frozenset({"B", "R"}),
    "Stomping Ground":   frozenset({"R", "G"}),
    "Temple Garden":     frozenset({"G", "W"}),
    "Godless Shrine":    frozenset({"W", "B"}),
    "Sacred Foundry":    frozenset({"R", "W"}),
    "Steam Vents":       frozenset({"U", "R"}),
    "Overgrown Tomb":    frozenset({"B", "G"}),
    "Breeding Pool":     frozenset({"U", "G"}),

    # Pain lands
    "Adarkar Wastes":    frozenset({"W", "U"}),
    "Battlefield Forge": frozenset({"W", "R"}),
    "Karplusan Forest":  frozenset({"R", "G"}),
    "Llanowar Wastes":   frozenset({"B", "G"}),
    "Underground River": frozenset({"U", "B"}),

    # Utility lands
    "Reflecting Pool":   frozenset({"W", "U", "B", "R", "G"}),  # any color
    "Mana Confluence":   frozenset({"W", "U", "B", "R", "G"}),
    "City of Brass":     frozenset({"W", "U", "B", "R", "G"}),
    "Cavern of Souls":   frozenset({"W", "U", "B", "R", "G"}),  # for chosen type
    "Path of Ancestry":  frozenset({"W", "U", "B", "R", "G"}),  # 5-color tribal
    "Bonders' Enclave":  frozenset({"C"}),
    "Boseiju, Who Endures": frozenset({"G"}),
    "Command Tower":     frozenset({"W", "U", "B", "R", "G"}),
}


def land_enters_tapped(name: str, battlefield_lands: list[str]) -> bool:
    """Determine if a land enters tapped given current board."""
    return name in ALWAYS_TAPPED


def compute_land_sources(name: str) -> list[frozenset]:
    """Return mana sources for a single untapped land."""
    if name in LAND_COLORS:
        return [LAND_COLORS[name]]
    return [frozenset({"C"})]


# --- ManaPool with multi-color allocator ---

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
        needed = {c: pips.get(c, 0) for c in "WUBRG"}
        generic = pips.get("generic", 0)
        total_needed = sum(needed.values()) + generic

        if self.total < total_needed:
            return False, None

        available = list(self.sources)

        for _ in range(sum(needed.values())):
            best_color = None
            best_ratio = float("inf")
            for color in "WUBRG":
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

        available.sort(key=lambda s: len(s))
        if len(available) < generic:
            return False, None

        return True, available[generic:]

    def can_cast(self, pips: dict) -> bool:
        ok, _ = self._allocate(pips)
        return ok

    def after_spending(self, pips: dict) -> "ManaPool":
        ok, remaining = self._allocate(pips)
        return ManaPool(remaining if ok else [])


# --- Decklist builder ---

def build_decklist(deck_data: dict) -> list[str]:
    cards = []
    for card in deck_data["decklist"]:
        qty = card.get("quantity", 1)
        cards.extend([card["name"]] * qty)
    return cards


def classify_cards(decklist: list[str], metadata: dict) -> dict:
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


def identify_changelings(metadata: dict) -> set[str]:
    """Cards with Changeling keyword (in oracle text)."""
    return {
        name for name, m in metadata.items()
        if "Changeling" in (m.get("oracle_text") or "")
    }


def identify_dragons(metadata: dict) -> set[str]:
    """Cards with Dragon in type_line (for Eminence-discount eligibility)."""
    return {
        name for name, m in metadata.items()
        if "Dragon" in (m.get("type_line") or "")
    }


def identify_elves(metadata: dict) -> set[str]:
    """Cards with Elf in type_line (for Priest/Archdruid scaling)."""
    return {
        name for name, m in metadata.items()
        if "Elf" in (m.get("type_line") or "") or "Changeling" in (m.get("oracle_text") or "")
    }


# --- Mulligan ---

MAX_MULLIGANS = 2


def should_mulligan(hand: list[str], land_set: set[str]) -> bool:
    """Mulligan if 0-1 lands OR 6+ lands (too few/too many)."""
    lands = sum(1 for c in hand if c in land_set)
    rocks = sum(1 for c in hand if c in ROCK_DEFS)
    sources = lands + rocks
    return sources <= 1 or lands >= 6


def choose_bottom_cards(hand: list[str], count: int, metadata: dict,
                        land_set: set[str]) -> list[str]:
    """London bottom: highest-CMC non-source cards."""
    candidates = [c for c in hand if c not in land_set and c not in ROCK_DEFS]
    candidates.sort(key=lambda c: metadata.get(c, {}).get("cmc", 0), reverse=True)
    return candidates[:count]


# --- Game state ---

class GameState:
    def __init__(self, decklist: list[str], metadata: dict, land_set: set[str],
                 changeling_set: set[str], dragon_set: set[str], elf_set: set[str]):
        self.library = list(decklist)
        random.shuffle(self.library)
        self.hand: list[str] = []
        self.battlefield_lands: list[str] = []
        self.tapped_lands: set[int] = set()
        self.battlefield_rocks: list[str] = []
        self.battlefield_dorks: list[dict] = []  # {name, ready_turn}
        self.battlefield_creatures: list[str] = []  # all creatures cast
        self.morophon_in_play = False
        self.dragonlords_servant_in_play = False
        self.metadata = metadata
        self.land_set = land_set
        self.changeling_set = changeling_set
        self.dragon_set = dragon_set
        self.elf_set = elf_set
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

    def changelings_in_play(self) -> int:
        return sum(1 for c in self.battlefield_creatures if c in self.changeling_set)

    def elves_in_play(self) -> int:
        # Elves + changelings (which are all types including Elf) + the dork itself if Elf.
        n = 0
        for c in self.battlefield_creatures:
            if c in self.elf_set or c in self.changeling_set:
                n += 1
        for d in self.battlefield_dorks:
            if d["name"] in {"Priest of Titania", "Elvish Archdruid", "Wirewood Channeler"}:
                # These ARE Elves. Already counted if also in creatures, otherwise add.
                if d["name"] not in self.battlefield_creatures:
                    n += 1
        return max(n, 1)

    def colors_present(self) -> set[str]:
        colors = set()
        for i, land in enumerate(self.battlefield_lands):
            for s in compute_land_sources(land):
                colors.update(c for c in s if c in "WUBRG")
        for rock in self.battlefield_rocks:
            rdef = ROCK_DEFS[rock]
            colors.update(c for c in rdef["colors"] if c in "WUBRG")
        return colors

    def _land_play_priority(self, name: str) -> float:
        tapped = land_enters_tapped(name, self.battlefield_lands)
        base = 0 if tapped else 10
        sources = compute_land_sources(name)
        if sources:
            n_colors = sum(1 for c in "WUBRG" if c in sources[0])
            base += n_colors * 2
        # Prefer rainbows
        if name in {"Command Tower", "Reflecting Pool", "Mana Confluence", "City of Brass"}:
            base += 3
        return base

    def compute_mana_pool(self, turn: int) -> ManaPool:
        pool_sources: list[frozenset] = []

        for i, land in enumerate(self.battlefield_lands):
            if i in self.tapped_lands:
                continue
            pool_sources.extend(compute_land_sources(land))

        for rock in self.battlefield_rocks:
            rdef = ROCK_DEFS[rock]
            for _ in range(rdef["count"]):
                pool_sources.append(rdef["colors"])

        board = {
            "elves": self.elves_in_play(),
            "colors_present": self.colors_present(),
        }
        for dork in self.battlefield_dorks:
            if dork["ready_turn"] > turn:
                continue
            pool_sources.extend(dork_sources(dork["name"], board))

        return ManaPool(pool_sources)

    def _effective_cost(self, name: str, base_pips: dict) -> dict:
        """Apply Eminence + Dragonlord's Servant + Morophon cost reductions."""
        pips = dict(base_pips)

        # Eminence (always): Other Dragon spells cost {1} less.
        # Applies to: changelings (which are Dragons) and real Dragons (not Ur-Dragon itself).
        is_dragon_spell = (name in self.changeling_set or name in self.dragon_set) and name != "The Ur-Dragon"
        if is_dragon_spell:
            pips["generic"] = max(0, pips["generic"] - 1)
        # Dragonlord's Servant: another {1} less on Dragon spells (incl. self? no — "Dragon spells you cast" includes self technically, but Servant isn't a Dragon).
        if is_dragon_spell and self.dragonlords_servant_in_play:
            pips["generic"] = max(0, pips["generic"] - 1)
        # Morophon: {WUBRG} less on chosen-type spells (Dragon). Reduces colored only.
        if is_dragon_spell and self.morophon_in_play:
            for c in "WUBRG":
                if pips[c] > 0:
                    pips[c] -= 1

        pips["total"] = (pips["generic"] + pips["W"] + pips["U"]
                         + pips["B"] + pips["R"] + pips["G"])
        return pips

    def play_turn(self, turn_number: int):
        if turn_number > 1:
            self.draw(1)

        self.tapped_lands.clear()

        # Land drop: best priority land in hand
        hand_lands = [(self._land_play_priority(c), c) for c in self.hand if self._is_land(c)]
        hand_lands.sort(reverse=True)
        if hand_lands:
            _, land_name = hand_lands[0]
            self.hand.remove(land_name)
            tapped = land_enters_tapped(land_name, self.battlefield_lands)
            self.battlefield_lands.append(land_name)
            if tapped:
                self.tapped_lands.add(len(self.battlefield_lands) - 1)

        # Mana rocks first (cheapest priority)
        pool = self.compute_mana_pool(turn_number)
        self._try_cast_rocks(pool, turn_number)

        # Ramp spells (Three Visits / Nature's Lore)
        pool = self.compute_mana_pool(turn_number)
        self._try_cast_ramp(pool, turn_number)

        # Mana dorks
        pool = self.compute_mana_pool(turn_number)
        self._try_cast_dorks(pool, turn_number)

        # Cost reducers + Morophon (these matter for engine readiness)
        pool = self.compute_mana_pool(turn_number)
        self._try_cast_cost_reducers(pool, turn_number)

        # Changelings (Dragon spells) — cast cheap ones to build tribe
        pool = self.compute_mana_pool(turn_number)
        self._try_cast_changelings(pool, turn_number)

        # Record final pool
        self.mana_per_turn.append(self.compute_mana_pool(turn_number))

    def _try_cast_rocks(self, pool: ManaPool, turn: int):
        priority = ["Sol Ring", "Arcane Signet", "Fellwar Stone"]
        for name in priority:
            if name not in self.hand:
                continue
            mc = self.metadata.get(name, {}).get("mana_cost", "")
            pips = parse_mana_cost(mc)
            if pool.can_cast(pips):
                pool = pool.after_spending(pips)
                self.hand.remove(name)
                self.battlefield_rocks.append(name)

    def _try_cast_ramp(self, pool: ManaPool, turn: int):
        for name in list(self.hand):
            if name not in RAMP_DEFS:
                continue
            rdef = RAMP_DEFS[name]
            pips = parse_mana_cost(rdef["mana_cost"])
            if not pool.can_cast(pips):
                continue
            # Fetch a Forest-typed land from library (basic Forest, or Stomping Ground / Breeding Pool / Temple Garden / Overgrown Tomb / Karplusan Forest / Llanowar Wastes / triomes-with-G).
            target = self._find_best_forest_typed()
            if target is None:
                continue
            pool = pool.after_spending(pips)
            self.hand.remove(name)
            self.library.remove(target)
            self.battlefield_lands.append(target)
            # Nature's Lore / Three Visits put land untapped
            return

    def _try_cast_dorks(self, pool: ManaPool, turn: int):
        # Sort by mana cost ascending
        candidates = []
        for name in self.hand:
            if name not in DORK_NAMES:
                continue
            mc = self.metadata.get(name, {}).get("mana_cost", "")
            pips = parse_mana_cost(mc)
            candidates.append((pips["total"], name, pips))
        candidates.sort()
        for total, name, pips in candidates:
            effective = self._effective_cost(name, pips)
            if pool.can_cast(effective):
                pool = pool.after_spending(effective)
                self.hand.remove(name)
                self.battlefield_dorks.append({"name": name, "ready_turn": turn + 1})
                self.battlefield_creatures.append(name)

    def _try_cast_cost_reducers(self, pool: ManaPool, turn: int):
        """Cast Dragonlord's Servant (2 CMC), Morophon (7 CMC) if affordable."""
        if "Dragonlord's Servant" in self.hand and not self.dragonlords_servant_in_play:
            mc = self.metadata.get("Dragonlord's Servant", {}).get("mana_cost", "")
            pips = parse_mana_cost(mc)
            effective = self._effective_cost("Dragonlord's Servant", pips)
            if pool.can_cast(effective):
                pool = pool.after_spending(effective)
                self.hand.remove("Dragonlord's Servant")
                self.battlefield_creatures.append("Dragonlord's Servant")
                self.dragonlords_servant_in_play = True

        if "Morophon, the Boundless" in self.hand and not self.morophon_in_play:
            mc = self.metadata.get("Morophon, the Boundless", {}).get("mana_cost", "")
            pips = parse_mana_cost(mc)
            # Morophon costs {7} — no discounts (it's a changeling but Eminence
            # discount of {1} applies to it as a Dragon spell).
            effective = self._effective_cost("Morophon, the Boundless", pips)
            if pool.can_cast(effective):
                pool = pool.after_spending(effective)
                self.hand.remove("Morophon, the Boundless")
                self.battlefield_creatures.append("Morophon, the Boundless")
                self.morophon_in_play = True

    def _try_cast_changelings(self, pool: ManaPool, turn: int):
        """Cast changelings from hand cheapest-first to build the tribe."""
        # Build candidate list with effective cost
        candidates = []
        for name in self.hand:
            if name not in self.changeling_set:
                continue
            if name in DORK_NAMES:
                continue  # already handled (Three Tree Mascot)
            if name == "Morophon, the Boundless":
                continue
            mc = self.metadata.get(name, {}).get("mana_cost", "")
            if not mc:
                continue
            pips = parse_mana_cost(mc)
            if pips["total"] == 0:
                continue
            effective = self._effective_cost(name, pips)
            candidates.append((effective["total"], name, effective))
        candidates.sort()
        for total, name, effective in candidates:
            if pool.can_cast(effective):
                pool = pool.after_spending(effective)
                self.hand.remove(name)
                self.battlefield_creatures.append(name)

    def _find_best_forest_typed(self) -> str | None:
        forest_typed = {
            "Forest", "Stomping Ground", "Breeding Pool", "Temple Garden",
            "Overgrown Tomb",
            "Indatha Triome", "Ketria Triome", "Zagoth Triome",
        }
        have_colors = self.colors_present()

        candidates = [c for c in self.library if c in forest_typed]
        if not candidates:
            return None

        def score(name: str) -> tuple:
            colors = LAND_COLORS.get(name, frozenset()) & frozenset("WUBRG")
            new_colors = len(colors - have_colors)
            tapped = name in ALWAYS_TAPPED
            # Prefer untapped + new colors; tiebreak by total colors.
            return (-int(tapped), new_colors, len(colors))

        candidates.sort(key=score, reverse=True)
        return candidates[0]


def commander_mulligan(decklist: list[str], metadata: dict, land_set: set[str],
                       changeling_set: set[str], dragon_set: set[str],
                       elf_set: set[str]) -> GameState:
    attempt = 0
    while True:
        state = GameState(decklist, metadata, land_set, changeling_set, dragon_set, elf_set)
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
        effective = state._effective_cost(card, pips)
        if pool.can_cast(effective):
            castable.append(card)
    return castable


# --- Simulation ---

UR_DRAGON_PIPS = {"generic": 4, "W": 1, "U": 1, "B": 1, "R": 1, "G": 1, "total": 9, "X": False}


def run_simulation(decklist: list[str], metadata: dict,
                   changeling_set: set[str], dragon_set: set[str],
                   elf_set: set[str], num_games: int = NUM_GAMES) -> dict:
    land_set = set()
    for name in set(decklist):
        meta = metadata.get(name, {})
        if "Land" in meta.get("type_line", ""):
            land_set.add(name)

    mana_by_turn = {t: [] for t in range(1, NUM_TURNS + 1)}
    w_by_turn = {t: [] for t in range(1, NUM_TURNS + 1)}
    u_by_turn = {t: [] for t in range(1, NUM_TURNS + 1)}
    b_by_turn = {t: [] for t in range(1, NUM_TURNS + 1)}
    r_by_turn = {t: [] for t in range(1, NUM_TURNS + 1)}
    g_by_turn = {t: [] for t in range(1, NUM_TURNS + 1)}
    hand_land_counts = Counter()
    mulligan_attempts = Counter()

    zero_w_by_turn = {t: 0 for t in range(1, NUM_TURNS + 1)}
    zero_u_by_turn = {t: 0 for t in range(1, NUM_TURNS + 1)}
    zero_b_by_turn = {t: 0 for t in range(1, NUM_TURNS + 1)}
    zero_r_by_turn = {t: 0 for t in range(1, NUM_TURNS + 1)}
    zero_g_by_turn = {t: 0 for t in range(1, NUM_TURNS + 1)}

    commander_castable_turn = []
    commander_by_turn = {t: 0 for t in range(1, NUM_TURNS + 1)}

    castable_spell_by_turn = {t: 0 for t in range(1, NUM_TURNS + 1)}
    curve_out_games = 0

    tapped_land_turns = {1: 0, 2: 0}

    # Hidden Legion-specific:
    changelings_by_turn = {t: [] for t in range(1, NUM_TURNS + 1)}
    ur_castable_by_turn = {t: 0 for t in range(1, NUM_TURNS + 1)}
    engine_ready_by_turn = {t: 0 for t in range(1, NUM_TURNS + 1)}

    for _ in range(num_games):
        state = commander_mulligan(decklist, metadata, land_set, changeling_set, dragon_set, elf_set)
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
            r_by_turn[t].append(pool.count_color("R"))
            g_by_turn[t].append(pool.count_color("G"))

            if pool.count_color("W") == 0:
                zero_w_by_turn[t] += 1
            if pool.count_color("U") == 0:
                zero_u_by_turn[t] += 1
            if pool.count_color("B") == 0:
                zero_b_by_turn[t] += 1
            if pool.count_color("R") == 0:
                zero_r_by_turn[t] += 1
            if pool.count_color("G") == 0:
                zero_g_by_turn[t] += 1

            # Commander: Ur-Dragon ({4}{WUBRG}, 9 mana). Eminence doesn't reduce Ur-Dragon itself.
            if cmd_cast_turn is None and pool.can_cast(UR_DRAGON_PIPS):
                cmd_cast_turn = t
                commander_by_turn[t] += 1

            if pool.can_cast(UR_DRAGON_PIPS):
                ur_castable_by_turn[t] += 1

            castable = can_cast_from_hand(state, pool)
            if castable:
                castable_spell_by_turn[t] += 1
            elif t <= 4:
                cast_every_turn = False

            if t <= 2 and lands_after > lands_before:
                new_idx = lands_after - 1
                if new_idx in state.tapped_lands:
                    tapped_land_turns[t] += 1

            chg_count = state.changelings_in_play()
            changelings_by_turn[t].append(chg_count)

            # Engine ready: Ur-Dragon castable AND >=1 changeling in play
            if pool.can_cast(UR_DRAGON_PIPS) and chg_count >= 1:
                engine_ready_by_turn[t] += 1

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
        "r_by_turn": r_by_turn,
        "g_by_turn": g_by_turn,
        "hand_land_counts": hand_land_counts,
        "mulligan_attempts": mulligan_attempts,
        "zero_w_by_turn": zero_w_by_turn,
        "zero_u_by_turn": zero_u_by_turn,
        "zero_b_by_turn": zero_b_by_turn,
        "zero_r_by_turn": zero_r_by_turn,
        "zero_g_by_turn": zero_g_by_turn,
        "commander_castable_turn": commander_castable_turn,
        "commander_by_turn": commander_by_turn,
        "castable_spell_by_turn": castable_spell_by_turn,
        "curve_out_games": curve_out_games,
        "tapped_land_turns": tapped_land_turns,
        "changelings_by_turn": changelings_by_turn,
        "ur_castable_by_turn": ur_castable_by_turn,
        "engine_ready_by_turn": engine_ready_by_turn,
    }


def _run_chunk(args):
    decklist, metadata, num_games = args
    changeling_set = identify_changelings(metadata)
    dragon_set = identify_dragons(metadata)
    elf_set = identify_elves(metadata)
    return run_simulation(decklist, metadata, changeling_set, dragon_set, elf_set, num_games)


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


def export_enhanced_json(metadata: dict) -> dict:
    """Reuse bulk exporter path so standalone JSON stays schema-compatible."""
    import export_simulation_results as exporter

    result = exporter.export_hidden_legion(metadata)
    if not exporter.validate_output(result, "hidden-legion"):
        raise ValueError("export_hidden_legion produced invalid simulation output")
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Monte Carlo mana base simulation for Hidden Legion (Ur-Dragon)")
    parser.add_argument("--json", action="store_true",
                        help="Write simulation.json instead of console output")
    args = parser.parse_args()

    with open(METADATA_FILE) as f:
        metadata = json.load(f)

    deck_file = PROJECT_ROOT / "data" / "commanders" / "hidden-legion" / "deck.json"
    with open(deck_file) as f:
        deck_data = json.load(f)

    print("Building Hidden Legion decklist...")
    decklist = build_decklist(deck_data)
    print(f"Decklist: {len(decklist)} cards")

    classified = classify_cards(decklist, metadata)

    if args.json:
        result = export_enhanced_json(metadata)
        JSON_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        with open(JSON_OUTPUT, "w") as f:
            json.dump(result, f, indent=2)
        print(f"Written: {JSON_OUTPUT}")
        print(f"Size: {JSON_OUTPUT.stat().st_size / 1024:.1f} KB")
        return

    print(f"Lands: {len(classified['lands'])}, Rocks: {len(classified['rocks'])}, "
          f"Spells: {len(classified['spells'])}")

    n_workers = os.cpu_count() or 4
    chunk_size = NUM_GAMES // n_workers
    remainder = NUM_GAMES % n_workers
    chunks = [chunk_size + (1 if i < remainder else 0) for i in range(n_workers)]

    print(f"\nRunning {NUM_GAMES:,} game simulations ({n_workers} workers)...")
    with multiprocessing.Pool(n_workers) as pool:
        results = pool.map(_run_chunk, [(decklist, metadata, n) for n in chunks])
    stats = merge_stats(results)

    total = NUM_GAMES
    print(f"\nMana medians: " + ", ".join(
        f"T{t}={statistics.median(stats['mana_by_turn'][t]):.0f}" for t in range(1, NUM_TURNS + 1)
    ))
    print(f"Commander (Ur-Dragon, 9 CMC) castable by T7: "
          f"{stats['commander_by_turn'][7]/total*100:.1f}%")
    print(f"Commander castable by T8: {stats['commander_by_turn'][8]/total*100:.1f}%")
    print(f"Commander castable by T9: {stats['commander_by_turn'][9]/total*100:.1f}%")
    print(f"Engine ready (Ur-Dragon castable + 1+ changeling) by T8: "
          f"{stats['engine_ready_by_turn'][8]/total*100:.1f}%")
    print(f"Engine ready by T10: {stats['engine_ready_by_turn'][10]/total*100:.1f}%")
    print(f"Median changelings in play T6: "
          f"{statistics.median(stats['changelings_by_turn'][6]):.0f}")
    print(f"Median changelings in play T10: "
          f"{statistics.median(stats['changelings_by_turn'][10]):.0f}")


if __name__ == "__main__":
    main()
