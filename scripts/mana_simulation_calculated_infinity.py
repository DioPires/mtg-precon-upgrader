#!/usr/bin/env python3
"""Monte Carlo mana base simulation for Calculated Infinity (Zimone, Infinite Analyst).

Simulates 100,000 games measuring mana production, color balance, and curve
efficiency turns 1-10 for the Bracket 4- Simic X-spell / Scepter combo decklist.

Commander: Zimone, Infinite Analyst ({1}{G}{U}, CMC 3); X-spell-payoff engine.
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
DECK_FILE = PROJECT_ROOT / "data" / "commanders" / "calculated-infinity" / "deck.json"
METADATA_FILE = PROJECT_ROOT / "data" / "card-metadata.json"
JSON_OUTPUT = PROJECT_ROOT / "data" / "commanders" / "calculated-infinity" / "simulation.json"

NUM_GAMES = 100_000
NUM_TURNS = 10


# --- Mana cost parser ---

def parse_mana_cost(mana_cost: str) -> dict:
    """Parse mana_cost string into pip breakdown."""
    if "//" in mana_cost:
        mana_cost = mana_cost.split("//")[0].strip()

    result = {"generic": 0, "U": 0, "G": 0, "total": 0, "X": False}
    symbols = re.findall(r"\{([^}]+)\}", mana_cost)
    for sym in symbols:
        if sym == "X":
            result["X"] = True
        elif sym.isdigit():
            result["generic"] += int(sym)
        elif sym == "U":
            result["U"] += 1
        elif sym == "G":
            result["G"] += 1
    result["total"] = result["generic"] + result["U"] + result["G"]
    return result


# --- Rock definitions ---
# Sol Ring (colorless), Simic Signet (UG flexible). Elementalist's Palette and
# Brass Infiniscope are 4-mana payoff artifacts: model as colorless ramp once
# in play (Palette: {C} + scaling X access; Infiniscope: {C}{C} tap). Treat both
# as flexible-C rocks for mana-pool purposes; their X-payoff text isn't simulated.

ROCK_DEFS = {
    "Sol Ring":              {"cmc": 1, "U": 0, "G": 0, "C": 2, "burst": False},
    "Simic Signet":          {"cmc": 2, "U": 1, "G": 1, "C": 0, "burst": False, "flexible": True},
    "Brass Infiniscope":     {"cmc": 4, "U": 0, "G": 0, "C": 2, "burst": False},
    "Elementalist's Palette":{"cmc": 4, "U": 0, "G": 0, "C": 1, "burst": False},
}

# --- Mana dork definitions ---
# 1-mana dorks: Birds (any color → flexible UG), Llanowar Elves ({G}).
# Troyan, Gutsy Explorer is {2}{G}{U}: legendary creature that taps for {X}{X} of
# any color in CI but only when an X-spell is being cast — too situational to
# model as standing mana. Skip from DORK_DEFS (treated as filler spell).

DORK_DEFS = {
    "Birds of Paradise": {"cmc": 1, "U": 1, "G": 1, "C": 0, "flexible": True},
    "Llanowar Elves":    {"cmc": 1, "U": 0, "G": 1, "C": 0, "flexible": False},
}

# --- Creature ramp definitions ---
# Three Visits / Nature's Lore: {1}{G} sorceries that put a Forest onto the
# battlefield untapped. Modeled as instant-land-fetch with a {1}{G} cost gate.

CREATURE_RAMP = {
    "Three Visits":  {"cmc": 2, "pips": {"generic": 1, "U": 0, "G": 1}, "fetch": "forest", "tapped": False},
    "Nature's Lore": {"cmc": 2, "pips": {"generic": 1, "U": 0, "G": 1}, "fetch": "forest", "tapped": False},
}


# --- Land definitions ---
# U-producing lands in deck (excludes pure C lands):
U_PRODUCING_LANDS = {
    "Island", "Breeding Pool", "Command Tower", "Botanical Sanctum",
    "Yavimaya Coast", "Hinterland Harbor", "Waterlogged Grove",
    "Otawara, Soaring City", "Castle Vantress", "Hall of Storm Giants",
    "Cavern of Souls",
    # Fetches: any fetch that can crack for an Island-typed land:
    "Misty Rainforest", "Scalding Tarn", "Flooded Strand",
    "Polluted Delta", "Prismatic Vista",
}

# G-producing lands in deck:
G_PRODUCING_LANDS = {
    "Forest", "Breeding Pool", "Command Tower", "Botanical Sanctum",
    "Yavimaya Coast", "Hinterland Harbor", "Waterlogged Grove",
    "Lush Portico", "Boseiju, Who Endures", "Yavimaya, Cradle of Growth",
    "Cavern of Souls",
    "Misty Rainforest", "Verdant Catacombs", "Wooded Foothills",
    "Prismatic Vista",
}

# Lands that produce only {C} when tapped:
C_ONLY_LANDS = {
    "Reliquary Tower", "Riptide Laboratory", "Strip Mine", "Wasteland",
    "Ash Barrens",
}

# Lands with Forest subtype (for ramp-fetch targeting):
FOREST_TYPED_LANDS = {"Forest", "Breeding Pool", "Lush Portico"}
# Lands with Island subtype:
ISLAND_TYPED_LANDS = {"Island", "Breeding Pool"}

BASIC_FORESTS = {"Forest"}
BASIC_ISLANDS = {"Island"}

# Fetchlands that crack for any-CI basic via search-and-sacrifice:
FETCHLANDS = {
    "Misty Rainforest":  {"targets": ("Forest", "Island")},   # Forest or Island
    "Scalding Tarn":     {"targets": ("Island",)},            # Mountain or Island; only Island in CI
    "Flooded Strand":    {"targets": ("Island",)},            # Plains or Island
    "Verdant Catacombs": {"targets": ("Forest",)},            # Swamp or Forest
    "Wooded Foothills":  {"targets": ("Forest",)},            # Mountain or Forest
    "Polluted Delta":    {"targets": ("Island",)},            # Island or Swamp
    "Prismatic Vista":   {"targets": ("Forest", "Island")},   # any basic; in CI → F or I
}


def build_decklist(deck_data: dict) -> list[str]:
    cards = []
    for card in deck_data["decklist"]:
        qty = card.get("quantity", 1)
        cards.extend([card["name"]] * qty)
    return cards


def classify_cards(decklist: list[str], metadata: dict) -> dict:
    classified = {"lands": [], "rocks": [], "spells": []}
    for name in decklist:
        if name in ROCK_DEFS or name in DORK_DEFS:
            classified["rocks"].append(name)
        else:
            meta = metadata.get(name, {})
            type_line = meta.get("type_line", "")
            if "Land" in type_line:
                classified["lands"].append(name)
            else:
                classified["spells"].append(name)
    return classified


# --- Board state helpers ---

def land_enters_tapped(name: str, battlefield_lands: list[str], hand: list[str]) -> bool:
    """ETB-tapped rules for the deck's lands."""
    other_count = len(battlefield_lands)

    if name == "Botanical Sanctum":
        # Fast land: tapped if ≥3 other lands.
        return other_count >= 3

    if name == "Hinterland Harbor":
        # Check land: untapped if you control a Forest- or Island-typed land.
        has_forest_or_island = any(
            l in FOREST_TYPED_LANDS or l in ISLAND_TYPED_LANDS
            for l in battlefield_lands
        )
        return not has_forest_or_island

    if name == "Castle Vantress":
        return not any(l in ISLAND_TYPED_LANDS for l in battlefield_lands)

    if name == "Hall of Storm Giants":
        return other_count >= 2

    if name == "Lush Portico":
        # Bond-cycle surveil land — text says "enters tapped" unconditionally.
        return True

    # Fetches go to graveyard immediately; resolved as the fetched basic, which
    # in this deck enters untapped.
    return False


class ManaPool:
    """Tracks available U, G, C mana and flexible sources."""
    def __init__(self):
        self.U = 0
        self.G = 0
        self.C = 0
        self.flexible = 0  # can be U or G

    @property
    def total(self):
        return self.U + self.G + self.C + self.flexible

    def can_cast(self, pips: dict) -> bool:
        need_U = pips["U"]
        need_G = pips["G"]
        need_generic = pips["generic"]

        avail_U = self.U
        avail_G = self.G
        avail_C = self.C
        avail_flex = self.flexible

        used_U = min(avail_U, need_U)
        remaining_U = need_U - used_U
        avail_U -= used_U

        used_G = min(avail_G, need_G)
        remaining_G = need_G - used_G
        avail_G -= used_G

        remaining_colored = remaining_U + remaining_G
        if avail_flex < remaining_colored:
            return False
        avail_flex -= remaining_colored

        leftover = avail_U + avail_G + avail_C + avail_flex
        return leftover >= need_generic

    def after_spending(self, pips: dict) -> "ManaPool":
        pool = ManaPool()
        pool.U = self.U
        pool.G = self.G
        pool.C = self.C
        pool.flexible = self.flexible

        need_U = pips["U"]
        need_G = pips["G"]
        need_generic = pips["generic"]

        from_U = min(pool.U, need_U)
        pool.U -= from_U
        need_U -= from_U

        from_G = min(pool.G, need_G)
        pool.G -= from_G
        need_G -= from_G

        flex_colored = need_U + need_G
        pool.flexible -= flex_colored

        remaining = need_generic
        from_C = min(pool.C, remaining)
        pool.C -= from_C
        remaining -= from_C

        from_U2 = min(pool.U, remaining)
        pool.U -= from_U2
        remaining -= from_U2

        from_G2 = min(pool.G, remaining)
        pool.G -= from_G2
        remaining -= from_G2

        from_flex = min(pool.flexible, remaining)
        pool.flexible -= from_flex

        return pool


def compute_land_mana(name: str) -> tuple[int, int, int, int]:
    """Return (U, G, C, flexible) mana a single untapped land produces."""
    if name == "Island":
        return (1, 0, 0, 0)
    if name == "Forest":
        return (0, 1, 0, 0)

    if name in ("Otawara, Soaring City", "Castle Vantress", "Hall of Storm Giants"):
        return (1, 0, 0, 0)

    if name in ("Boseiju, Who Endures", "Lush Portico", "Yavimaya, Cradle of Growth"):
        return (0, 1, 0, 0)

    if name in C_ONLY_LANDS:
        return (0, 0, 1, 0)

    # Cavern of Souls: produces {C} or 1 of any color (creature-restricted). For
    # casting accounting we treat it as flexible {U}/{G}/{C}.
    if name == "Cavern of Souls":
        return (0, 0, 1, 0)

    # UG dual lands (Breeding Pool, Command Tower, Botanical Sanctum, Yavimaya
    # Coast, Hinterland Harbor, Waterlogged Grove) all produce flex U/G.
    if name in {
        "Breeding Pool", "Command Tower", "Botanical Sanctum",
        "Yavimaya Coast", "Hinterland Harbor", "Waterlogged Grove",
    }:
        return (0, 0, 0, 1)

    # Fetches resolved as basics already; defensive fallback for unmodeled lands.
    return (0, 0, 1, 0)


MAX_MULLIGANS = 2


def should_mulligan(hand: list[str], land_set: set[str]) -> bool:
    """Mulligan if 0-1 mana sources (lands + rocks + dorks)."""
    sources = sum(1 for c in hand if c in land_set or c in ROCK_DEFS or c in DORK_DEFS)
    return sources <= 1


def choose_bottom_cards(hand: list[str], count: int, metadata: dict, land_set: set[str]) -> list[str]:
    """London mulligan: bottom highest CMC non-land, non-ramp cards."""
    ramp_cards = set(ROCK_DEFS) | set(DORK_DEFS)
    candidates = [c for c in hand if c not in land_set and c not in ramp_cards]
    candidates.sort(key=lambda c: metadata.get(c, {}).get("cmc", 0), reverse=True)
    return candidates[:count]


class GameState:
    def __init__(self, decklist: list[str], metadata: dict, land_set: set[str]):
        self.library = list(decklist)
        random.shuffle(self.library)
        self.hand: list[str] = []
        self.battlefield_lands: list[str] = []
        self.tapped_lands: set[int] = set()
        self.battlefield_rocks: list[str] = []
        self.battlefield_dorks: list[str] = []
        self.dorks_active: list[str] = []
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
        """Higher = play first. Untapped > tapped; UG duals preferred."""
        tapped = land_enters_tapped(name, self.battlefield_lands, self.hand)

        if name in FETCHLANDS:
            return 20  # always crack fetches immediately

        base = 0 if tapped else 10

        # Duals (both colors) get the highest non-fetch bonus.
        if name in U_PRODUCING_LANDS and name in G_PRODUCING_LANDS:
            base += 5
        elif name == "Yavimaya, Cradle of Growth":
            base += 4  # makes every land also a Forest — helps fix later G drops
        elif name in U_PRODUCING_LANDS or name in G_PRODUCING_LANDS:
            base += 2
        # Pure C utility lands fall to the bottom.

        return base

    def _resolve_fetch(self, fetch_name: str):
        """Resolve a fetchland: search library for a matching basic and put it onto battlefield untapped."""
        targets = FETCHLANDS[fetch_name]["targets"]
        u_sources = sum(1 for l in self.battlefield_lands if l in U_PRODUCING_LANDS)
        g_sources = sum(1 for l in self.battlefield_lands if l in G_PRODUCING_LANDS)

        # Prefer the color we're behind on.
        if "Island" in targets and "Forest" in targets:
            preferred = ["Island", "Forest"] if u_sources <= g_sources else ["Forest", "Island"]
        elif "Island" in targets:
            preferred = ["Island"]
        elif "Forest" in targets:
            preferred = ["Forest"]
        else:
            preferred = []

        for basic in preferred:
            for i, card in enumerate(self.library):
                if card == basic:
                    self.library.pop(i)
                    self.battlefield_lands.append(card)
                    return

        # Library empty of preferred basic — fetch nothing (still cracks).

    def _fetch_basic_land(self, fetch_type: str, enters_tapped: bool):
        """Ramp-spell fetch (Three Visits / Nature's Lore)."""
        u_sources = sum(1 for l in self.battlefield_lands if l in U_PRODUCING_LANDS)
        g_sources = sum(1 for l in self.battlefield_lands if l in G_PRODUCING_LANDS)

        if fetch_type == "forest":
            targets = [i for i, c in enumerate(self.library) if c == "Forest"]
        else:
            if u_sources <= g_sources:
                targets = [i for i, c in enumerate(self.library) if c == "Island"]
                if not targets:
                    targets = [i for i, c in enumerate(self.library) if c == "Forest"]
            else:
                targets = [i for i, c in enumerate(self.library) if c == "Forest"]
                if not targets:
                    targets = [i for i, c in enumerate(self.library) if c == "Island"]

        if targets:
            idx = targets[0]
            card = self.library.pop(idx)
            self.battlefield_lands.append(card)
            if enters_tapped:
                self.tapped_lands.add(len(self.battlefield_lands) - 1)

    def compute_mana_pool(self) -> ManaPool:
        pool = ManaPool()

        for i, land in enumerate(self.battlefield_lands):
            if i in self.tapped_lands:
                continue
            u, g, c, f = compute_land_mana(land)
            pool.U += u
            pool.G += g
            pool.C += c
            pool.flexible += f

        for rock in self.battlefield_rocks:
            rdef = ROCK_DEFS[rock]
            pool.C += rdef.get("C", 0)
            if rdef.get("flexible"):
                pool.flexible += 1
            else:
                pool.U += rdef.get("U", 0)
                pool.G += rdef.get("G", 0)

        for dork in self.dorks_active:
            if dork in DORK_DEFS:
                ddef = DORK_DEFS[dork]
                if ddef.get("flexible"):
                    pool.flexible += 1
                else:
                    pool.U += ddef.get("U", 0)
                    pool.G += ddef.get("G", 0)

        return pool

    def play_turn(self, turn_number: int):
        if turn_number > 1:
            self.draw(1)

        self.tapped_lands.clear()
        self.dorks_active = list(self.battlefield_dorks)

        hand_lands = [(self._land_play_priority(c), c) for c in self.hand if self._is_land(c)]
        hand_lands.sort(reverse=True)

        if hand_lands:
            _, land_name = hand_lands[0]
            self.hand.remove(land_name)

            if land_name in FETCHLANDS:
                self._resolve_fetch(land_name)
            else:
                tapped = land_enters_tapped(land_name, self.battlefield_lands, self.hand)
                self.battlefield_lands.append(land_name)
                if tapped:
                    self.tapped_lands.add(len(self.battlefield_lands) - 1)

        pool = self.compute_mana_pool()
        self._try_cast_ramp(pool)

        self.mana_per_turn.append(self.compute_mana_pool())

    def _try_cast_ramp(self, pool: ManaPool):
        priority_order = [
            ("rock", "Sol Ring"),
            ("dork", "Birds of Paradise"),
            ("dork", "Llanowar Elves"),
            ("rock", "Simic Signet"),
            ("creature_ramp", "Three Visits"),
            ("creature_ramp", "Nature's Lore"),
            ("rock", "Brass Infiniscope"),
            ("rock", "Elementalist's Palette"),
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
                    pool.C += rdef.get("C", 0)
                    if rdef.get("flexible"):
                        pool.flexible += 1
                    else:
                        pool.U += rdef.get("U", 0)
                        pool.G += rdef.get("G", 0)

            elif ramp_type == "dork":
                pips = {"generic": 0, "U": 0, "G": 1}
                if pool.can_cast(pips):
                    pool = pool.after_spending(pips)
                    self.hand.remove(name)
                    self.battlefield_dorks.append(name)
                    # Summoning sickness — produces mana from next turn.

            elif ramp_type == "creature_ramp":
                cramp = CREATURE_RAMP[name]
                pips = cramp["pips"]
                if pool.can_cast(pips):
                    pool = pool.after_spending(pips)
                    self.hand.remove(name)
                    self._fetch_basic_land(cramp["fetch"], cramp["tapped"])


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
    """Castable non-ramp spells in hand under current pool."""
    ramp_cards = set(ROCK_DEFS) | set(DORK_DEFS) | set(CREATURE_RAMP)
    castable = []
    for card in state.hand:
        if card in ramp_cards or card in state.land_set:
            continue
        meta = state.metadata.get(card, {})
        mc = meta.get("mana_cost", "")
        if not mc:
            continue
        pips = parse_mana_cost(mc)
        # X-spells: cost only the colored pips + 0 generic at minimum.
        if pips["total"] == 0 and not pips["X"]:
            continue
        if pool.can_cast(pips):
            castable.append(card)
    return castable


# --- Static analysis ---

def print_static_analysis(decklist: list[str], metadata: dict, classified: dict):
    print("=" * 65)
    print("STATIC ANALYSIS — CALCULATED INFINITY (BRACKET 4-)")
    print("=" * 65)

    print(f"\n--- Deck Composition ---")
    print(f"Total cards (excl. commander): {len(decklist)}")
    print(f"Lands: {len(classified['lands'])}")
    print(f"Mana rocks/dorks: {len(classified['rocks'])}")
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
        bar = "#" * count
        if count > 0:
            print(f"    {cmc_val:>2} CMC: {count:>2} {bar}")

    total_U = 0
    total_G = 0
    for name in decklist:
        meta = metadata.get(name, {})
        mc = meta.get("mana_cost", "")
        if "Land" in meta.get("type_line", ""):
            continue
        pips = parse_mana_cost(mc)
        total_U += pips["U"]
        total_G += pips["G"]

    total_pips = total_U + total_G
    u_ratio = total_U / total_pips * 100 if total_pips > 0 else 0
    g_ratio = total_G / total_pips * 100 if total_pips > 0 else 0

    print(f"\n--- Pip Demand ---")
    print(f"  Total {{U}} pips: {total_U}")
    print(f"  Total {{G}} pips: {total_G}")
    print(f"  Ratio: {u_ratio:.0f}% U / {g_ratio:.0f}% G")

    lands = classified["lands"]
    u_sources = sum(1 for l in lands if l in U_PRODUCING_LANDS)
    g_sources = sum(1 for l in lands if l in G_PRODUCING_LANDS)
    both_sources = sum(1 for l in lands if l in U_PRODUCING_LANDS and l in G_PRODUCING_LANDS)
    c_only = sum(1 for l in lands if l in C_ONLY_LANDS)
    fetch_count = sum(1 for l in lands if l in FETCHLANDS)

    print(f"\n--- Mana Source Inventory ---")
    print(f"  U-producing lands: {u_sources}")
    print(f"  G-producing lands: {g_sources}")
    print(f"  Dual (U+G) lands: {both_sources}")
    print(f"  C-only lands: {c_only}")
    print(f"  Fetchlands: {fetch_count}")

    rock_flex = sum(1 for r in classified["rocks"] if r in ROCK_DEFS and ROCK_DEFS[r].get("flexible"))
    rock_c = sum(1 for r in classified["rocks"] if r in ROCK_DEFS and not ROCK_DEFS[r].get("flexible"))
    dork_count = sum(1 for r in classified["rocks"] if r in DORK_DEFS)
    print(f"  Flexible rocks (U/G): {rock_flex}")
    print(f"  Colorless rocks: {rock_c}")
    print(f"  Mana dorks: {dork_count}")

    recommended = round(36 + (avg_cmc - 3.0) * 2)
    print(f"\n--- Land Count Heuristic ---")
    print(f"  Avg CMC: {avg_cmc:.2f}")
    print(f"  Current lands: {len(lands)}")
    print(f"  Heuristic recommendation: ~{recommended} lands")

    return avg_cmc, total_U, total_G


# --- Simulation ---

def run_simulation(decklist: list[str], metadata: dict, num_games: int = NUM_GAMES) -> dict:
    land_set = set()
    for name in set(decklist):
        meta = metadata.get(name, {})
        if "Land" in meta.get("type_line", ""):
            land_set.add(name)

    mana_by_turn = {t: [] for t in range(1, NUM_TURNS + 1)}
    u_by_turn = {t: [] for t in range(1, NUM_TURNS + 1)}
    g_by_turn = {t: [] for t in range(1, NUM_TURNS + 1)}
    hand_land_counts = Counter()
    mulligan_attempts = Counter()

    zero_u_by_turn = {t: 0 for t in range(1, NUM_TURNS + 1)}
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
            total = pool.total
            u_avail = pool.U + pool.flexible
            g_avail = pool.G + pool.flexible

            mana_by_turn[t].append(total)
            u_by_turn[t].append(u_avail)
            g_by_turn[t].append(g_avail)

            if u_avail == 0:
                zero_u_by_turn[t] += 1
            if g_avail == 0:
                zero_g_by_turn[t] += 1

            # Commander: Zimone, Infinite Analyst {1}{G}{U} = 3 total, 1 U, 1 G.
            cmd_pips = {"generic": 1, "U": 1, "G": 1}
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
        "u_by_turn": u_by_turn,
        "g_by_turn": g_by_turn,
        "hand_land_counts": hand_land_counts,
        "mulligan_attempts": mulligan_attempts,
        "zero_u_by_turn": zero_u_by_turn,
        "zero_g_by_turn": zero_g_by_turn,
        "commander_castable_turn": commander_castable_turn,
        "commander_by_turn": commander_by_turn,
        "castable_spell_by_turn": castable_spell_by_turn,
        "curve_out_games": curve_out_games,
        "tapped_land_turns": tapped_land_turns,
    }


def print_results(stats: dict, classified: dict, avg_cmc: float, pip_U: int, pip_G: int):
    total = NUM_GAMES

    print("\n" + "=" * 65)
    print(f"MONTE CARLO SIMULATION — CALCULATED INFINITY ({NUM_GAMES:,} games, {NUM_TURNS} turns)")
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
    print(f"    Paid mulligan (->6): {mull.get(2, 0)/total*100:>5.1f}%")

    print(f"\n--- Dimension 2: Color Balance ---")
    print(f"\n  U and G available per turn (includes flexible):")
    print(f"  {'Turn':<6} {'U med':>7} {'U mean':>7} {'G med':>7} {'G mean':>7}")
    print(f"  {'-'*38}")
    for t in range(1, NUM_TURNS + 1):
        u_med = statistics.median(stats["u_by_turn"][t])
        u_mean = statistics.mean(stats["u_by_turn"][t])
        g_med = statistics.median(stats["g_by_turn"][t])
        g_mean = statistics.mean(stats["g_by_turn"][t])
        print(f"    T{t:<4} {u_med:>7.0f} {u_mean:>7.1f} {g_med:>7.0f} {g_mean:>7.1f}")

    print(f"\n  Color screw (0 sources of a color):")
    for t in range(2, NUM_TURNS + 1):
        u_pct = stats["zero_u_by_turn"][t] / total * 100
        g_pct = stats["zero_g_by_turn"][t] / total * 100
        print(f"    T{t}: 0 U = {u_pct:.1f}%, 0 G = {g_pct:.1f}%")

    print(f"\n--- Dimension 3: Curve Efficiency ---")
    print(f"\n  Commander castable (Zimone, {{1}}{{G}}{{U}}):")
    for t in range(2, NUM_TURNS + 1):
        count = stats["commander_by_turn"][t]
        print(f"    By T{t}: {count/total*100:.1f}%")

    print(f"\n  Curve-out rate (T1-T4): {stats['curve_out_games']/total*100:.1f}%")


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
    import export_simulation_results as exporter

    result = exporter.export_calculated_infinity(metadata)
    if not exporter.validate_output(result, "calculated-infinity"):
        raise ValueError("export_calculated_infinity produced invalid simulation output")
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Monte Carlo mana base simulation for Calculated Infinity (Zimone)")
    parser.add_argument("--json", action="store_true",
                        help="Write simulation.json instead of console output")
    args = parser.parse_args()

    with open(DECK_FILE) as f:
        deck_data = json.load(f)
    with open(METADATA_FILE) as f:
        metadata = json.load(f)

    print("Building Calculated Infinity decklist...")
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

    avg_cmc, pip_U, pip_G = print_static_analysis(decklist, metadata, classified)

    n_workers = os.cpu_count() or 4
    chunk_size = NUM_GAMES // n_workers
    remainder = NUM_GAMES % n_workers
    chunks = [chunk_size + (1 if i < remainder else 0) for i in range(n_workers)]

    print(f"\nRunning {NUM_GAMES:,} games ({n_workers} workers)...")
    with multiprocessing.Pool(n_workers) as pool:
        results = pool.map(_run_chunk, [(decklist, metadata, n) for n in chunks])
    stats = merge_stats(results)

    print_results(stats, classified, avg_cmc, pip_U, pip_G)
    print("\n" + "=" * 65)


if __name__ == "__main__":
    main()
