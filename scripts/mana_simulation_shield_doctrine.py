#!/usr/bin/env python3
"""Monte Carlo mana base simulation for Shield Doctrine (Jeskai equipment voltron).

Simulates 100,000 games measuring Jeskai (W/U/R) mana production and Captain
America, First Avenger castability across turns 1-10.

Commander: Captain America, First Avenger — {R}{W}{U} (MV 3), the cast target.
All three pips are colored, so the commander metric is purely a fixing check:
the first turn one each of R/W/U is payable from available mana.

This is a thin colored-mana sim (no bespoke engine-readiness block): the
exporter calls `_export_colored`, which consumes the standard stats keys
(mana / color / commander castability / curve / tapped-land). Equipment
attach/Throw lines are out of scope here.

Manabase model (36 lands, unchanged in tuning round v1.2 — DEC-421):
- 14 untapped Jeskai duals: shocks (Hallowed Fountain, Sacred Foundry, Steam
  Vents), fastlands (Spirebluff Canal, Inspiring Vantage, Seachrome Coast),
  painlands (Shivan Reef, Battlefield Forge, Adarkar Wastes), bondlands
  (Spectator Seating, Training Center, Sea of Clouds) — all modeled untapped:
  pay-2-life, on-curve, and two-or-more-opponents conditions are effectively
  free in a goldfish, the same precedent as the shockland treatment in the
  other sims.
- 3 checklands (Clifftop Retreat, Glacial Fortress, Sulfur Falls) — modeled
  honestly: enter tapped unless a Plains/Island/Mountain-typed land (basics
  or the three typed shocks) is already on the battlefield (armory-protocol
  Sulfur Falls precedent).
- Flooded Strand — fetches any Plains/Island-typed land, which includes all
  three typed shocks, so it fixes into any of the three color pairs; modeled
  as a W/U/R source (silverquill Marsh Flats precedent).
- 2 commander-CI rainbow producers (Command Tower, Exotic Orchard) modeled
  as W/U/R.
- Utility lands: Axgard Armory (W; enters tapped — the deck's only
  always-tapped land), Rogue's Passage (C), Buried Ruin (C).
- 15 basics (Plains x5, Island x5, Mountain x5).
- Ramp: rocks only — Sol Ring (x2 C), Arcane Signet (W/U/R), Talismans of
  Conviction/Progress/Creativity (C or their two colors),
  Fellwar Stone (modeled W/U/R, Exotic Orchard precedent); Dalakos taps for
  {C}{C} restricted to artifacts — modeled as 2x C, safe for the commander
  metric (all-colored cost never uses C) and a fair approximation for generic
  costs in a 25+-artifact deck.

Tuning round v1.2 (9 spell swaps, board-approved) left the mana model
untouched: none of the nine adds produces mana, and the two cut cards with
mana notes (Codsworth — restricted {W}{W}, deliberately unmodeled; Sword of
the Animist — combat-gated land ramp, unmodeled) were never sources here.
All adds/cuts flow through deck.json + card-metadata.json automatically.
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
JSON_OUTPUT = PROJECT_ROOT / "data" / "commanders" / "shield-doctrine" / "simulation.json"

NUM_GAMES = 100_000
NUM_TURNS = 10


# --- Mana cost parser ---

def parse_mana_cost(mana_cost: str) -> dict:
    result = {"generic": 0, "W": 0, "U": 0, "B": 0, "R": 0, "G": 0, "total": 0, "X": False}
    if not mana_cost:
        return result
    if "//" in mana_cost:
        mana_cost = mana_cost.split("//")[0].strip()

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
    "Sol Ring":               {"cmc": 1, "colors": frozenset({"C"}), "count": 2},
    "Arcane Signet":          {"cmc": 2, "colors": frozenset({"W", "U", "R"}), "count": 1},
    # Talismans add {C} or one of two colors — a single flexible source.
    "Talisman of Conviction": {"cmc": 2, "colors": frozenset({"C", "R", "W"}), "count": 1},
    "Talisman of Progress":   {"cmc": 2, "colors": frozenset({"C", "W", "U"}), "count": 1},
    "Talisman of Creativity": {"cmc": 2, "colors": frozenset({"C", "U", "R"}), "count": 1},
    # Fellwar Stone: opponent-land dependent — modeled as commander CI
    # (Exotic Orchard precedent).
    "Fellwar Stone":          {"cmc": 2, "colors": frozenset({"W", "U", "R"}), "count": 1},
}


# --- Ramp spell definitions ---

# No land-ramp spells in the 99 (Sword of the Animist cut in v1.2).
RAMP_DEFS: dict = {}


# --- Mana dork definitions (creatures that tap for mana) ---

# Dalakos taps for {C}{C} (artifact spells / artifact abilities only).
# Modeled as two colorless sources — see module docstring.
DORK_DEFS = {
    "Dalakos, Crafter of Wonders": [frozenset({"C"}), frozenset({"C"})],
}
DORK_NAMES = set(DORK_DEFS)


def dork_sources(name: str, board: dict) -> list[frozenset]:
    """Mana sources a dork produces (one tap yields the whole list)."""
    if name in DORK_DEFS:
        return list(DORK_DEFS[name])
    return []


# --- Land tables ---

BASIC_LANDS = {"Plains", "Island", "Swamp", "Mountain", "Forest"}

ALWAYS_TAPPED = {
    "Axgard Armory",
}

LAND_COLORS: dict[str, frozenset] = {
    # Basics
    "Plains":   frozenset({"W"}),
    "Island":   frozenset({"U"}),
    "Mountain": frozenset({"R"}),

    # Shocks / fastlands / painlands / bondlands — all modeled untapped
    # (pay-2-life / on-curve / two-or-more-opponents are free in a goldfish;
    # same precedent as the shockland treatment in other sims).
    "Hallowed Fountain":  frozenset({"W", "U"}),
    "Sacred Foundry":     frozenset({"R", "W"}),
    "Steam Vents":        frozenset({"U", "R"}),
    "Spirebluff Canal":   frozenset({"U", "R"}),
    "Inspiring Vantage":  frozenset({"R", "W"}),
    "Seachrome Coast":    frozenset({"W", "U"}),
    "Shivan Reef":        frozenset({"U", "R"}),
    "Battlefield Forge":  frozenset({"R", "W"}),
    "Adarkar Wastes":     frozenset({"W", "U"}),
    "Spectator Seating":  frozenset({"R", "W"}),
    "Training Center":    frozenset({"U", "R"}),
    "Sea of Clouds":      frozenset({"W", "U"}),

    # Checklands — ETB-tapped condition handled in land_enters_tapped.
    "Clifftop Retreat":   frozenset({"R", "W"}),
    "Glacial Fortress":   frozenset({"W", "U"}),
    "Sulfur Falls":       frozenset({"U", "R"}),

    # Flooded Strand fetches any Plains/Island-typed land — basics or the
    # three typed shocks — so it fixes into any of the deck's three color
    # pairs. Modeled as a flexible W/U/R source (Marsh Flats precedent in
    # the silverquill sim: fetches produce the color identity of their
    # fetchable targets).
    "Flooded Strand":     frozenset({"W", "U", "R"}),

    # Rainbow / commander-CI producers — modeled as Jeskai (W/U/R)
    "Command Tower":  frozenset({"W", "U", "R"}),
    "Exotic Orchard": frozenset({"W", "U", "R"}),

    # Mono / colorless utility lands
    "Axgard Armory":   frozenset({"W"}),
    "Rogue's Passage": frozenset({"C"}),
    "Buried Ruin":     frozenset({"C"}),
}

# No green land-ramp package — typed-fetch tables are empty.
FOREST_TYPED: set[str] = set()
FARSEEK_TARGETS: set[str] = set()
BASIC_TYPED = set(BASIC_LANDS)

# Basic-typed lands on the battlefield that satisfy checkland conditions
# (basics + the three typed shocks).
PLAINS_TYPED = {"Plains", "Hallowed Fountain", "Sacred Foundry"}
ISLAND_TYPED = {"Island", "Hallowed Fountain", "Steam Vents"}
MOUNTAIN_TYPED = {"Mountain", "Sacred Foundry", "Steam Vents"}

CHECKLAND_TYPES = {
    "Clifftop Retreat": (MOUNTAIN_TYPED, PLAINS_TYPED),
    "Glacial Fortress": (PLAINS_TYPED, ISLAND_TYPED),
    "Sulfur Falls": (ISLAND_TYPED, MOUNTAIN_TYPED),
}


def land_enters_tapped(name: str, battlefield_lands: list[str]) -> bool:
    if name in CHECKLAND_TYPES:
        type_a, type_b = CHECKLAND_TYPES[name]
        return not any(l in type_a or l in type_b for l in battlefield_lands)
    return name in ALWAYS_TAPPED


def compute_land_sources(name: str) -> list[frozenset]:
    if name in LAND_COLORS:
        return [LAND_COLORS[name]]
    return [frozenset({"C"})]


# --- ManaPool with multi-color allocator (mirrors superfriends-esika) ---

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
            # Use the FRONT face for MDFCs (a Creature // Land card is a
            # creature we cast, not a land we play).
            front = type_line.split("//")[0]
            if "Land" in front:
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
        for land in self.battlefield_lands:
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
        if name in {"Command Tower", "Exotic Orchard"}:
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

        self._play_best_land()

        # Mana rocks first
        pool = self.compute_mana_pool(turn_number)
        self._try_cast_rocks(pool)

        # Ramp spells
        pool = self.compute_mana_pool(turn_number)
        self._try_cast_ramp(pool)

        # Mana dorks
        pool = self.compute_mana_pool(turn_number)
        self._try_cast_dorks(pool, turn_number)

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
        # Cheapest / most impactful first; multiple rocks per turn allowed.
        priority = ["Sol Ring", "Arcane Signet", "Talisman of Conviction",
                    "Talisman of Progress", "Talisman of Creativity",
                    "Fellwar Stone", "Mind Stone"]
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
            elif fetch_type == "non_forest_typed":
                target = self._find_best_typed(FARSEEK_TARGETS)
                if target is None:
                    continue
                pool = pool.after_spending(pips)
                self.hand.remove(name)
                self.library.remove(target)
                self.battlefield_lands.append(target)
                self.tapped_lands.add(len(self.battlefield_lands) - 1)
            elif fetch_type == "basic_tapped":
                target = self._find_best_typed(BASIC_TYPED)
                if target is None:
                    continue
                pool = pool.after_spending(pips)
                self.hand.remove(name)
                self.library.remove(target)
                self.battlefield_lands.append(target)
                self.tapped_lands.add(len(self.battlefield_lands) - 1)
                extra = next((c for c in self.library if c in BASIC_TYPED), None)
                if extra is not None:
                    self.library.remove(extra)
                    self.hand.append(extra)
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

# Captain America, First Avenger: {R}{W}{U} = 3 mana, one each of red/white/blue.
CAPTAIN_PIPS = {"generic": 0, "W": 1, "U": 1, "B": 0, "R": 1, "G": 0, "total": 3, "X": False}


def run_simulation(decklist: list[str], metadata: dict,
                   num_games: int = NUM_GAMES) -> dict:
    land_set = set()
    for name in set(decklist):
        meta = metadata.get(name, {})
        # Front face only — an MDFC spell//land counts as a spell here.
        front = meta.get("type_line", "").split("//")[0]
        if "Land" in front:
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

            # Commander cast tracking: first turn Captain America is castable.
            if cmd_cast_turn is None and pool.can_cast(CAPTAIN_PIPS):
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

    result = exporter.export_shield_doctrine(metadata)
    if not exporter.validate_output(result, "shield-doctrine"):
        raise ValueError("export_shield_doctrine produced invalid simulation output")
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Monte Carlo mana base simulation for Shield Doctrine (Jeskai equipment voltron)")
    parser.add_argument("--json", action="store_true",
                        help="Write simulation.json instead of console output")
    args = parser.parse_args()

    with open(METADATA_FILE) as f:
        metadata = json.load(f)

    deck_file = PROJECT_ROOT / "data" / "commanders" / "shield-doctrine" / "deck.json"
    with open(deck_file) as f:
        deck_data = json.load(f)

    print("Building Shield Doctrine decklist...")
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
    print(f"Captain America ({{R}}{{W}}{{U}}, 3 CMC) castable by T3: "
          f"{stats['commander_by_turn'][3]/total*100:.1f}%")
    print(f"Captain America castable by T4: {stats['commander_by_turn'][4]/total*100:.1f}%")
    print(f"Captain America castable by T5: {stats['commander_by_turn'][5]/total*100:.1f}%")


if __name__ == "__main__":
    main()
