#!/usr/bin/env python3
"""Monte Carlo mana base simulation for Esika's Council (5C Superfriends).

Simulates 100,000 games measuring 5-color mana production, Esika back-side
(Prismatic Bridge) castability, counter-doubler deployment, and engine
readiness across turns 1-10.

Commander: Esika, God of the Tree // The Prismatic Bridge. Back side costs
{1}{W}{U}{B}{R}{G} (MV 6) and is the cast target. Front side (legendary
creature) is a fallback we do not separately model — the metric of interest
is the {1}{W}{U}{B}{R}{G} back-side cast.

Engine state (Esika-specific):
- esikaCastableByTurn: cumulative % of games where Esika back-side is castable
  by turn t (does not require commander to actually be cast).
- counterDoublersByTurn: median count of counter-doublers / proliferate-doublers
  in play (Doubling Season, Parallel Lives, Vorinclex, Deepglow Skate,
  Innkeeper's Talent) — measures combo-readiness scaffolding.
- engineReadyByTurn: probability Esika has been cast AND >=1 counter-doubler
  is on the battlefield. Core operating condition — Bridge active with a
  doubler accelerates walker ETBs straight into ult range.
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
JSON_OUTPUT = PROJECT_ROOT / "data" / "commanders" / "superfriends-esika" / "simulation.json"

NUM_GAMES = 100_000
NUM_TURNS = 10


# --- Mana cost parser ---

def parse_mana_cost(mana_cost: str) -> dict:
    if not mana_cost:
        return {"generic": 0, "W": 0, "U": 0, "B": 0, "R": 0, "G": 0, "total": 0, "X": False}
    if "//" in mana_cost:
        mana_cost = mana_cost.split("//")[1].strip()  # Esika back-side is the cast target

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
    "Sol Ring":          {"cmc": 1, "colors": frozenset({"C"}), "count": 2},
    "Arcane Signet":     {"cmc": 2, "colors": frozenset({"W", "U", "B", "R", "G"}), "count": 1},
    "Chromatic Lantern": {"cmc": 3, "colors": frozenset({"W", "U", "B", "R", "G"}), "count": 1},
}


# --- Ramp spell definitions ---

RAMP_DEFS = {
    "Three Visits":  {"mana_cost": "{1}{G}", "fetch_type": "forest_typed",     "tapped": False},
    "Nature's Lore": {"mana_cost": "{1}{G}", "fetch_type": "forest_typed",     "tapped": False},
    "Farseek":       {"mana_cost": "{1}{G}", "fetch_type": "non_forest_typed", "tapped": True},
    "Growth Spiral": {"mana_cost": "{G}{U}", "fetch_type": "extra_land_drop",  "tapped": False},
}


# --- Mana dork definitions (creatures that tap for mana) ---

DORK_NAMES = {
    "Birds of Paradise",
    "Delighted Halfling",
    "Paradise Druid",
    "Faeburrow Elder",
}


def dork_sources(name: str, board: dict) -> list[frozenset]:
    """Mana sources a dork produces given current board state."""
    colors_present = board.get("colors_present", set())

    if name in ("Birds of Paradise", "Delighted Halfling", "Paradise Druid"):
        return [frozenset({"W", "U", "B", "R", "G"})]
    if name == "Faeburrow Elder":
        colors = colors_present & {"W", "U", "B", "R", "G"}
        if not colors:
            colors = {"G"}
        return [frozenset({c}) for c in colors]
    return []


# --- Counter-doublers / proliferate enablers (engine readiness check) ---

COUNTER_DOUBLER_NAMES = {
    "Doubling Season",
    "Parallel Lives",
    "Vorinclex, Monstrous Raider",
    "Deepglow Skate",
    "Innkeeper's Talent",
}


# --- Land tables for Esika ---

BASIC_LANDS = {"Plains", "Island", "Swamp", "Mountain", "Forest"}

ALWAYS_TAPPED = {
    # Triomes (10)
    "Ketria Triome", "Indatha Triome", "Spara's Headquarters", "Zagoth Triome",
    "Raugrin Triome", "Raffine's Tower", "Jetmir's Garden", "Savai Triome",
    "Ziatora's Proving Ground", "Xander's Lounge",
    # Utility tapped lands
    "Great Hall of the Citadel",
}

LAND_COLORS: dict[str, frozenset] = {
    # Basics
    "Plains":   frozenset({"W"}),
    "Island":   frozenset({"U"}),
    "Swamp":    frozenset({"B"}),
    "Mountain": frozenset({"R"}),
    "Forest":   frozenset({"G"}),

    # Triomes (3 colors each, always tapped)
    "Ketria Triome":            frozenset({"G", "U", "R"}),
    "Indatha Triome":           frozenset({"W", "B", "G"}),
    "Spara's Headquarters":     frozenset({"G", "W", "U"}),
    "Zagoth Triome":            frozenset({"B", "G", "U"}),
    "Raugrin Triome":           frozenset({"U", "R", "W"}),
    "Raffine's Tower":          frozenset({"W", "U", "B"}),
    "Jetmir's Garden":          frozenset({"R", "G", "W"}),
    "Savai Triome":             frozenset({"R", "W", "B"}),
    "Ziatora's Proving Ground": frozenset({"B", "R", "G"}),
    "Xander's Lounge":          frozenset({"U", "B", "R"}),

    # Shock lands (8)
    "Breeding Pool":     frozenset({"U", "G"}),
    "Temple Garden":     frozenset({"G", "W"}),
    "Hallowed Fountain": frozenset({"W", "U"}),
    "Overgrown Tomb":    frozenset({"B", "G"}),
    "Watery Grave":      frozenset({"U", "B"}),
    "Stomping Ground":   frozenset({"R", "G"}),
    "Godless Shrine":    frozenset({"W", "B"}),
    "Steam Vents":       frozenset({"U", "R"}),

    # Rainbow / utility producers
    "City of Brass":            frozenset({"W", "U", "B", "R", "G"}),
    "Command Tower":            frozenset({"W", "U", "B", "R", "G"}),
    "Plaza of Heroes":          frozenset({"W", "U", "B", "R", "G"}),
    "The World Tree":           frozenset({"C"}),  # taps for C; 3-mana ability not modeled
    "Karn's Bastion":           frozenset({"C"}),
    "Interplanar Beacon":       frozenset({"C"}),  # 5C only for walker spells; conservative
    "Great Hall of the Citadel": frozenset({"C"}),
}

# Lands with a Forest basic type — fetchable by Three Visits / Nature's Lore
FOREST_TYPED = {
    "Forest", "Breeding Pool", "Temple Garden", "Overgrown Tomb",
    "Stomping Ground",
    "Ketria Triome", "Indatha Triome", "Spara's Headquarters",
    "Zagoth Triome", "Jetmir's Garden", "Ziatora's Proving Ground",
}

# Lands with a basic land type other than Forest — fetchable by Farseek
# (Plains / Island / Swamp / Mountain typed, including duals).
FARSEEK_TARGETS = {
    "Plains", "Island", "Swamp", "Mountain",
    "Hallowed Fountain", "Watery Grave", "Godless Shrine", "Steam Vents",
    # Shocks above already covered. Triomes have multi-basic types.
    "Raugrin Triome", "Raffine's Tower", "Savai Triome", "Xander's Lounge",
    "Indatha Triome", "Ketria Triome", "Spara's Headquarters", "Zagoth Triome",
    "Jetmir's Garden", "Ziatora's Proving Ground",
}


def land_enters_tapped(name: str, battlefield_lands: list[str]) -> bool:
    return name in ALWAYS_TAPPED


def compute_land_sources(name: str) -> list[frozenset]:
    if name in LAND_COLORS:
        return [LAND_COLORS[name]]
    return [frozenset({"C"})]


# --- ManaPool with multi-color allocator (mirrors hidden_legion) ---

class ManaPool:
    def __init__(self, sources=None):
        self.sources: list[frozenset] = list(sources) if sources else []

    @property
    def total(self) -> int:
        return len(self.sources)

    def count_color(self, color: str) -> int:
        return sum(1 for s in self.sources if color in s)

    def _allocate(self, pips: dict) -> tuple[bool, list[frozenset] | None]:
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


# --- Mulligan ---

MAX_MULLIGANS = 2


def should_mulligan(hand: list[str], land_set: set[str]) -> bool:
    lands = sum(1 for c in hand if c in land_set)
    rocks = sum(1 for c in hand if c in ROCK_DEFS)
    sources = lands + rocks
    return sources <= 1 or lands >= 6


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
        self.battlefield_dorks: list[dict] = []
        self.battlefield_permanents: list[str] = []  # non-land non-rock cast
        self.esika_in_play = False
        self.extra_land_drop = False
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

    def colors_present(self) -> set[str]:
        colors = set()
        for i, land in enumerate(self.battlefield_lands):
            for s in compute_land_sources(land):
                colors.update(c for c in s if c in "WUBRG")
        for rock in self.battlefield_rocks:
            rdef = ROCK_DEFS[rock]
            colors.update(c for c in rdef["colors"] if c in "WUBRG")
        return colors

    def counter_doublers_in_play(self) -> int:
        return sum(1 for c in self.battlefield_permanents if c in COUNTER_DOUBLER_NAMES)

    def _land_play_priority(self, name: str) -> float:
        tapped = land_enters_tapped(name, self.battlefield_lands)
        base = 0 if tapped else 10
        sources = compute_land_sources(name)
        if sources:
            n_colors = sum(1 for c in "WUBRG" if c in sources[0])
            base += n_colors * 2
        if name in {"Command Tower", "City of Brass", "Plaza of Heroes"}:
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

        board = {"colors_present": self.colors_present()}
        for dork in self.battlefield_dorks:
            if dork["ready_turn"] > turn:
                continue
            pool_sources.extend(dork_sources(dork["name"], board))

        return ManaPool(pool_sources)

    def play_turn(self, turn_number: int):
        if turn_number > 1:
            self.draw(1)

        self.tapped_lands.clear()
        self.extra_land_drop = False

        self._play_best_land()

        # Mana rocks first
        pool = self.compute_mana_pool(turn_number)
        self._try_cast_rocks(pool)

        # Ramp spells
        pool = self.compute_mana_pool(turn_number)
        self._try_cast_ramp(pool)

        # If a ramp spell granted an extra land drop (Growth Spiral), use it
        if self.extra_land_drop:
            self._play_best_land()

        # Mana dorks
        pool = self.compute_mana_pool(turn_number)
        self._try_cast_dorks(pool, turn_number)

        # Esika (priority engine piece) once castable
        pool = self.compute_mana_pool(turn_number)
        self._try_cast_esika(pool)

        # Counter-doublers
        pool = self.compute_mana_pool(turn_number)
        self._try_cast_doublers(pool)

        self.mana_per_turn.append(self.compute_mana_pool(turn_number))

    def _play_best_land(self):
        hand_lands = [(self._land_play_priority(c), c) for c in self.hand if self._is_land(c)]
        if not hand_lands:
            return
        hand_lands.sort(reverse=True)
        _, land_name = hand_lands[0]
        self.hand.remove(land_name)
        tapped = land_enters_tapped(land_name, self.battlefield_lands)
        self.battlefield_lands.append(land_name)
        if tapped:
            self.tapped_lands.add(len(self.battlefield_lands) - 1)

    def _try_cast_rocks(self, pool: ManaPool):
        priority = ["Sol Ring", "Arcane Signet", "Chromatic Lantern"]
        for name in priority:
            if name not in self.hand:
                continue
            mc = self.metadata.get(name, {}).get("mana_cost", "")
            pips = parse_mana_cost(mc)
            if pool.can_cast(pips):
                pool = pool.after_spending(pips)
                self.hand.remove(name)
                self.battlefield_rocks.append(name)

    def _try_cast_ramp(self, pool: ManaPool):
        for name in list(self.hand):
            if name not in RAMP_DEFS:
                continue
            rdef = RAMP_DEFS[name]
            pips = parse_mana_cost(rdef["mana_cost"])
            if not pool.can_cast(pips):
                continue

            fetch_type = rdef["fetch_type"]
            if fetch_type == "forest_typed":
                target = self._find_best_typed(FOREST_TYPED)
                if target is None:
                    continue
                pool = pool.after_spending(pips)
                self.hand.remove(name)
                self.library.remove(target)
                self.battlefield_lands.append(target)
                # Three Visits / Nature's Lore — untapped
            elif fetch_type == "non_forest_typed":
                target = self._find_best_typed(FARSEEK_TARGETS)
                if target is None:
                    continue
                pool = pool.after_spending(pips)
                self.hand.remove(name)
                self.library.remove(target)
                self.battlefield_lands.append(target)
                # Farseek — tapped
                self.tapped_lands.add(len(self.battlefield_lands) - 1)
            elif fetch_type == "extra_land_drop":
                pool = pool.after_spending(pips)
                self.hand.remove(name)
                self.draw(1)
                self.extra_land_drop = True
            return  # only one ramp spell per turn

    def _try_cast_dorks(self, pool: ManaPool, turn: int):
        candidates = []
        for name in self.hand:
            if name not in DORK_NAMES:
                continue
            mc = self.metadata.get(name, {}).get("mana_cost", "")
            pips = parse_mana_cost(mc)
            candidates.append((pips["total"], name, pips))
        candidates.sort()
        for _, name, pips in candidates:
            if pool.can_cast(pips):
                pool = pool.after_spending(pips)
                self.hand.remove(name)
                self.battlefield_dorks.append({"name": name, "ready_turn": turn + 1})

    def _try_cast_esika(self, pool: ManaPool):
        """Esika is the commander — always available from the command zone.

        Mirrors the hidden_legion framework's convention of independent
        per-category mana pools within a turn (each `_try_cast_*` sees fresh
        availability), so casting Esika does not consume mana that would also
        be used by `_try_cast_doublers` on the same turn.
        """
        if self.esika_in_play:
            return
        if pool.can_cast(ESIKA_PIPS):
            self.battlefield_permanents.append("Esika, God of the Tree")
            self.esika_in_play = True

    def _try_cast_doublers(self, pool: ManaPool):
        candidates = []
        for name in self.hand:
            if name not in COUNTER_DOUBLER_NAMES:
                continue
            mc = self.metadata.get(name, {}).get("mana_cost", "")
            pips = parse_mana_cost(mc)
            if pips["total"] == 0:
                continue
            candidates.append((pips["total"], name, pips))
        candidates.sort()
        for _, name, pips in candidates:
            if pool.can_cast(pips):
                pool = pool.after_spending(pips)
                self.hand.remove(name)
                self.battlefield_permanents.append(name)

    def _find_best_typed(self, typed_set: set[str]) -> str | None:
        have_colors = self.colors_present()
        candidates = [c for c in self.library if c in typed_set]
        if not candidates:
            return None

        def score(name: str) -> tuple:
            colors = LAND_COLORS.get(name, frozenset()) & frozenset("WUBRG")
            new_colors = len(colors - have_colors)
            tapped = name in ALWAYS_TAPPED
            return (-int(tapped), new_colors, len(colors))

        candidates.sort(key=score, reverse=True)
        return candidates[0]


def commander_mulligan(decklist: list[str], metadata: dict, land_set: set[str]) -> GameState:
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


# --- Simulation ---

# Esika back-side: {1}{W}{U}{B}{R}{G} = 6 mana, one of each color.
ESIKA_PIPS = {"generic": 1, "W": 1, "U": 1, "B": 1, "R": 1, "G": 1, "total": 6, "X": False}


def run_simulation(decklist: list[str], metadata: dict,
                   num_games: int = NUM_GAMES) -> dict:
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

    # Esika-specific
    esika_castable_by_turn = {t: 0 for t in range(1, NUM_TURNS + 1)}
    counter_doublers_by_turn = {t: [] for t in range(1, NUM_TURNS + 1)}
    engine_ready_by_turn = {t: 0 for t in range(1, NUM_TURNS + 1)}

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

            # Commander cast tracking: first turn Esika is castable from hand
            # (even if play_turn already cast it — recompute pre-spend pool).
            # Use post-turn pool after all casts as the available-mana snapshot,
            # which mirrors hidden_legion's commander tracking.
            if cmd_cast_turn is None and (state.esika_in_play or pool.can_cast(ESIKA_PIPS)):
                cmd_cast_turn = t
                commander_by_turn[t] += 1

            if state.esika_in_play or pool.can_cast(ESIKA_PIPS):
                esika_castable_by_turn[t] += 1

            castable = can_cast_from_hand(state, pool)
            if castable:
                castable_spell_by_turn[t] += 1
            elif t <= 4:
                cast_every_turn = False

            if t <= 2 and lands_after > lands_before:
                new_idx = lands_after - 1
                if new_idx in state.tapped_lands:
                    tapped_land_turns[t] += 1

            doublers = state.counter_doublers_in_play()
            counter_doublers_by_turn[t].append(doublers)

            if state.esika_in_play and doublers >= 1:
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
        "esika_castable_by_turn": esika_castable_by_turn,
        "counter_doublers_by_turn": counter_doublers_by_turn,
        "engine_ready_by_turn": engine_ready_by_turn,
    }


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


def export_enhanced_json(metadata: dict) -> dict:
    """Reuse bulk exporter path so standalone JSON stays schema-compatible."""
    import export_simulation_results as exporter

    result = exporter.export_superfriends_esika(metadata)
    if not exporter.validate_output(result, "superfriends-esika"):
        raise ValueError("export_superfriends_esika produced invalid simulation output")
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Monte Carlo mana base simulation for Esika's Council (5C Superfriends)")
    parser.add_argument("--json", action="store_true",
                        help="Write simulation.json instead of console output")
    args = parser.parse_args()

    with open(METADATA_FILE) as f:
        metadata = json.load(f)

    deck_file = PROJECT_ROOT / "data" / "commanders" / "superfriends-esika" / "deck.json"
    with open(deck_file) as f:
        deck_data = json.load(f)

    print("Building Esika's Council decklist...")
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
    print(f"Esika (back-side, 6 CMC WUBRG) castable by T6: "
          f"{stats['commander_by_turn'][6]/total*100:.1f}%")
    print(f"Esika castable by T7: {stats['commander_by_turn'][7]/total*100:.1f}%")
    print(f"Esika castable by T8: {stats['commander_by_turn'][8]/total*100:.1f}%")
    print(f"Engine ready (Esika in play + 1+ doubler) by T8: "
          f"{stats['engine_ready_by_turn'][8]/total*100:.1f}%")
    print(f"Engine ready by T10: {stats['engine_ready_by_turn'][10]/total*100:.1f}%")
    print(f"Median doublers in play T8: "
          f"{statistics.median(stats['counter_doublers_by_turn'][8]):.0f}")


if __name__ == "__main__":
    main()
