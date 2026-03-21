#!/usr/bin/env python3
"""Monte Carlo mana base simulation for Genesis Protocol (Shorikai, Genesis Engine).

Simulates 100,000 games measuring mana production, color balance, and curve
efficiency turns 1-10 for the Bracket 4 Azorius decklist.

Commander: Shorikai, Genesis Engine ({2}{W}{U}, CMC 4)
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
DECK_FILE = PROJECT_ROOT / "data" / "commanders" / "genesis-protocol" / "deck.json"
METADATA_FILE = PROJECT_ROOT / "data" / "card-metadata.json"
JSON_OUTPUT = PROJECT_ROOT / "data" / "commanders" / "genesis-protocol" / "simulation.json"

NUM_GAMES = 100_000
NUM_TURNS = 10

# --- Mana cost parser ---

def parse_mana_cost(mana_cost: str) -> dict:
    """Parse mana_cost string into pip breakdown.

    "{2}{W}{U}" -> {generic: 2, W: 1, U: 1, total: 4}
    "{W}{W}{W}" -> {generic: 0, W: 3, U: 0, total: 3}
    "{X}{U}{U}" -> {generic: 0, W: 0, U: 2, total: 2, X: True}

    Split cards (//): parse first half only.
    """
    if "//" in mana_cost:
        mana_cost = mana_cost.split("//")[0].strip()

    result = {"generic": 0, "W": 0, "U": 0, "total": 0, "X": False}
    symbols = re.findall(r"\{([^}]+)\}", mana_cost)
    for sym in symbols:
        if sym == "X":
            result["X"] = True
        elif sym.isdigit():
            result["generic"] += int(sym)
        elif sym == "W":
            result["W"] += 1
        elif sym == "U":
            result["U"] += 1
        # Ignore other symbols (hybrid, phyrexian, etc.)
    result["total"] = result["generic"] + result["W"] + result["U"]
    return result


# --- Rock definitions ---

ROCK_DEFS = {
    "Sol Ring":              {"cmc": 1, "W": 0, "U": 0, "C": 2, "burst": False},
    "Mana Vault":            {"cmc": 1, "W": 0, "U": 0, "C": 3, "burst": True},
    "Chrome Mox":            {"cmc": 0, "W": 0, "U": 0, "C": 0, "burst": False, "flexible": True},
    "Arcane Signet":         {"cmc": 2, "W": 1, "U": 1, "C": 0, "burst": False, "flexible": True},
    "Azorius Signet":        {"cmc": 2, "W": 1, "U": 1, "C": 0, "burst": False, "flexible": True},
    "Talisman of Progress":  {"cmc": 2, "W": 1, "U": 1, "C": 0, "burst": False, "flexible": True},
    "Fellwar Stone":         {"cmc": 2, "W": 0, "U": 0, "C": 0, "burst": False, "flexible": True},
    "Mind Stone":            {"cmc": 2, "W": 0, "U": 0, "C": 1, "burst": False},
    "Thought Vessel":        {"cmc": 2, "W": 0, "U": 0, "C": 1, "burst": False},
    "Basalt Monolith":       {"cmc": 3, "W": 0, "U": 0, "C": 3, "burst": False},
}

# --- Land definitions ---

ALWAYS_UNTAPPED_DUALS = {
    "Hallowed Fountain", "Command Tower", "Adarkar Wastes", "Mystic Gate",
    "Mana Confluence", "Exotic Orchard",
}

BASIC_PLAINS = {"Plains"}
BASIC_ISLANDS = {"Island"}

# Lands with Plains subtype (for checkland conditions)
PLAINS_TYPED_LANDS = {"Plains", "Hallowed Fountain"}
# Lands with Island subtype
ISLAND_TYPED_LANDS = {"Island", "Hallowed Fountain"}

# Lands that produce W
W_PRODUCING_LANDS = {
    "Plains", "Hallowed Fountain", "Command Tower", "Adarkar Wastes",
    "Seachrome Coast", "Glacial Fortress", "Mystic Gate",
    "Eiganjo, Seat of the Empire", "Castle Ardenvale",
    "Nimbus Maze", "Mana Confluence", "Exotic Orchard",
}

# Lands that produce U
U_PRODUCING_LANDS = {
    "Island", "Hallowed Fountain", "Command Tower", "Adarkar Wastes",
    "Seachrome Coast", "Glacial Fortress", "Mystic Gate",
    "Otawara, Soaring City",
    "Sea Gate Restoration // Sea Gate, Reborn",
    "Nimbus Maze", "Mana Confluence", "Exotic Orchard",
}

# Colorless-only lands
C_ONLY_LANDS = {
    "Academy Ruins", "Urza's Saga", "Ancient Tomb", "Reliquary Tower",
}

# Fetchlands in deck (can find Plains/Island typed lands)
FETCHLANDS = {
    "Flooded Strand", "Misty Rainforest", "Polluted Delta", "Prismatic Vista",
}


def build_decklist(deck_data: dict) -> list[str]:
    """Build the 99-card decklist for Genesis Protocol.

    Reads the flat decklist array directly. Each entry has {name, type} with
    optional quantity field. Commander is in the command zone (not in decklist).
    """
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


# --- Board state helpers ---

def count_basics(battlefield_lands: list[str]) -> int:
    return sum(1 for l in battlefield_lands if l in BASIC_PLAINS or l in BASIC_ISLANDS)


def has_plains_or_island(battlefield_lands: list[str]) -> bool:
    return any(
        l in PLAINS_TYPED_LANDS or l in ISLAND_TYPED_LANDS
        for l in battlefield_lands
    )


def land_enters_tapped(name: str, battlefield_lands: list[str], hand: list[str]) -> bool:
    """Determine if a land enters tapped given board + hand state."""
    other_count = len(battlefield_lands)  # the new land isn't on board yet

    if name == "Sea Gate Restoration // Sea Gate, Reborn":
        # Enters tapped unless you pay 3 life. Model as untapped (aggressive play).
        return False

    if name == "Glacial Fortress":
        # Enters tapped unless you control a Plains or Island
        return not any(
            l in PLAINS_TYPED_LANDS or l in ISLAND_TYPED_LANDS
            for l in battlefield_lands
        )

    if name == "Castle Ardenvale":
        # Enters tapped unless you control a Plains
        return not any(l in PLAINS_TYPED_LANDS for l in battlefield_lands)

    if name == "Seachrome Coast":
        # Enters tapped if you control 3+ other lands
        return other_count >= 3

    return False  # All other lands enter untapped


class ManaPool:
    """Tracks available W, U, C mana and flexible sources."""
    def __init__(self):
        self.W = 0
        self.U = 0
        self.C = 0
        self.flexible = 0  # can be W or U

    @property
    def total(self):
        return self.W + self.U + self.C + self.flexible

    def can_cast(self, pips: dict) -> bool:
        """Check if we can cast a spell with the given pip requirements."""
        need_W = pips["W"]
        need_U = pips["U"]
        need_generic = pips["generic"]

        avail_W = self.W
        avail_U = self.U
        avail_C = self.C
        avail_flex = self.flexible

        # Assign fixed W sources to W pips
        used_W = min(avail_W, need_W)
        remaining_W = need_W - used_W
        avail_W -= used_W

        # Assign fixed U sources to U pips
        used_U = min(avail_U, need_U)
        remaining_U = need_U - used_U
        avail_U -= used_U

        # Use flexible for remaining colored needs
        remaining_colored = remaining_W + remaining_U
        if avail_flex < remaining_colored:
            return False
        avail_flex -= remaining_colored

        # Remaining generic from leftover W, U, C, flexible
        leftover = avail_W + avail_U + avail_C + avail_flex
        return leftover >= need_generic

    def after_spending(self, pips: dict) -> "ManaPool":
        """Return a new ManaPool after spending pips. Assumes can_cast is True."""
        pool = ManaPool()
        pool.W = self.W
        pool.U = self.U
        pool.C = self.C
        pool.flexible = self.flexible

        need_W = pips["W"]
        need_U = pips["U"]
        need_generic = pips["generic"]

        # Spend fixed W
        from_W = min(pool.W, need_W)
        pool.W -= from_W
        need_W -= from_W

        # Spend fixed U
        from_U = min(pool.U, need_U)
        pool.U -= from_U
        need_U -= from_U

        # Spend flexible on remaining colored
        flex_colored = need_W + need_U
        pool.flexible -= flex_colored

        # Spend generic: C first, then leftover W/U, then flexible
        remaining = need_generic
        from_C = min(pool.C, remaining)
        pool.C -= from_C
        remaining -= from_C

        from_W2 = min(pool.W, remaining)
        pool.W -= from_W2
        remaining -= from_W2

        from_U2 = min(pool.U, remaining)
        pool.U -= from_U2
        remaining -= from_U2

        from_flex = min(pool.flexible, remaining)
        pool.flexible -= from_flex

        return pool


def compute_land_mana(name: str, battlefield_lands: list[str]) -> tuple[int, int, int, int]:
    """Return (W, U, C, flexible) mana a single untapped land produces.

    flexible = can produce W or U (dual lands, Command Tower, etc.)
    """
    # Special cases first
    if name == "Academy Ruins":
        return (0, 0, 1, 0)

    if name == "Urza's Saga":
        return (0, 0, 1, 0)

    if name == "Ancient Tomb":
        return (0, 0, 2, 0)

    if name == "Reliquary Tower":
        return (0, 0, 1, 0)

    # Fetchlands should already be cracked; if somehow on board, treat as 0
    if name in FETCHLANDS:
        return (0, 0, 0, 0)

    # Nimbus Maze: {C} always; {W} if you control Island; {U} if you control Plains
    if name == "Nimbus Maze":
        has_island = any(l in ISLAND_TYPED_LANDS for l in battlefield_lands)
        has_plains = any(l in PLAINS_TYPED_LANDS for l in battlefield_lands)
        if has_island and has_plains:
            return (0, 0, 0, 1)  # flexible W/U
        elif has_island:
            return (1, 0, 0, 0)  # W only
        elif has_plains:
            return (0, 1, 0, 0)  # U only
        else:
            return (0, 0, 1, 0)  # {C} only

    # Mana Confluence: any color (pay 1 life)
    if name == "Mana Confluence":
        return (0, 0, 0, 1)

    # Exotic Orchard: produces any color opponents could produce; assume W/U in multiplayer
    if name == "Exotic Orchard":
        return (0, 0, 0, 1)

    # Dual lands (produce W or U -> flexible)
    if name in ALWAYS_UNTAPPED_DUALS or name in {
        "Seachrome Coast", "Glacial Fortress",
    }:
        return (0, 0, 0, 1)

    # Castle Ardenvale: produces {W}
    if name == "Castle Ardenvale":
        return (1, 0, 0, 0)

    # Eiganjo, Seat of the Empire: produces {W}
    if name == "Eiganjo, Seat of the Empire":
        return (1, 0, 0, 0)

    # Otawara, Soaring City: produces {U}
    if name == "Otawara, Soaring City":
        return (0, 1, 0, 0)

    # Sea Gate Restoration // Sea Gate, Reborn: produces {U}
    if name == "Sea Gate Restoration // Sea Gate, Reborn":
        return (0, 1, 0, 0)

    # Basic Plains
    if name == "Plains":
        return (1, 0, 0, 0)

    # Basic Island
    if name == "Island":
        return (0, 1, 0, 0)

    # Fallback: colorless
    return (0, 0, 1, 0)


MAX_MULLIGANS = 2  # attempt 0 = initial, 1 = free, 2 = paid (bottom 1)


def should_mulligan(hand: list[str], land_set: set[str]) -> bool:
    """Mulligan if 0-1 mana sources (lands + rocks)."""
    sources = sum(1 for c in hand if c in land_set or c in ROCK_DEFS)
    return sources <= 1


def choose_bottom_cards(hand: list[str], count: int, metadata: dict, land_set: set[str]) -> list[str]:
    """Choose cards to bottom (London mulligan). Bottom highest CMC non-land, non-rock cards."""
    candidates = [c for c in hand if c not in land_set and c not in ROCK_DEFS]
    candidates.sort(key=lambda c: metadata.get(c, {}).get("cmc", 0), reverse=True)
    return candidates[:count]


class GameState:
    def __init__(self, decklist: list[str], metadata: dict, land_set: set[str]):
        self.library = list(decklist)
        random.shuffle(self.library)
        self.hand: list[str] = []
        self.battlefield_lands: list[str] = []
        self.tapped_lands: set[int] = set()  # indices into battlefield_lands
        self.battlefield_rocks: list[str] = []
        self.burst_rocks_active: dict[str, bool] = {}
        self.metadata = metadata
        self.land_set = land_set
        self.mana_per_turn: list[ManaPool] = []
        self.mulligan_attempt = 0  # 0=kept, 1=free, 2=paid
        # Shorikai-specific tracking
        self.shorikai_on_board = False  # whether Shorikai has been cast
        self.shorikai_cast_turn = None  # turn Shorikai was cast
        self.shorikai_activations = 0  # cumulative activations after casting
        self.shorikai_activations_per_turn: list[int] = []  # activations possible per turn
        self.nonland_mana_per_turn: list[int] = []  # mana from nonland permanents per turn

    def draw(self, n: int = 1):
        for _ in range(n):
            if self.library:
                self.hand.append(self.library.pop())

    def count_lands_in_hand(self) -> int:
        return sum(1 for c in self.hand if c in self.land_set)

    def count_rocks_in_hand(self) -> int:
        return sum(1 for c in self.hand if c in ROCK_DEFS)

    def _is_land(self, name: str) -> bool:
        return name in self.land_set

    def _land_play_priority(self, name: str) -> float:
        """Higher = play first. Untapped > tapped. Color-fixing > mono."""
        tapped = land_enters_tapped(name, self.battlefield_lands, self.hand)

        if name in FETCHLANDS:
            return 20  # Fetch: always play and crack immediately

        if tapped:
            base = 0
        else:
            base = 10

        # Duals (flexible color) get bonus
        if name in ALWAYS_UNTAPPED_DUALS:
            base += 5
        elif name in W_PRODUCING_LANDS and name in U_PRODUCING_LANDS:
            base += 4

        return base

    def _resolve_fetch(self, fetch_name: str):
        """Resolve a fetchland: search library for Plains or Island card.

        Flooded Strand: Plains or Island
        Misty Rainforest: Forest or Island (we fetch Island)
        Polluted Delta: Island or Swamp (we fetch Island)
        Prismatic Vista: any basic land
        """
        # Determine color need
        w_sources = sum(1 for l in self.battlefield_lands if l in W_PRODUCING_LANDS)
        u_sources = sum(1 for l in self.battlefield_lands if l in U_PRODUCING_LANDS)

        # Fetchable targets in library
        fetchable = []
        for i, card in enumerate(self.library):
            if fetch_name == "Flooded Strand":
                # Can fetch Plains or Island typed
                if card in PLAINS_TYPED_LANDS or card in ISLAND_TYPED_LANDS:
                    fetchable.append((i, card))
            elif fetch_name == "Misty Rainforest":
                # Forest or Island — we only have Islands as Forest-typed
                if card in ISLAND_TYPED_LANDS or card in BASIC_ISLANDS:
                    fetchable.append((i, card))
            elif fetch_name == "Polluted Delta":
                # Island or Swamp — we only have Islands
                if card in ISLAND_TYPED_LANDS or card in BASIC_ISLANDS:
                    fetchable.append((i, card))
            elif fetch_name == "Prismatic Vista":
                # Any basic land
                if card in BASIC_PLAINS or card in BASIC_ISLANDS:
                    fetchable.append((i, card))

        if not fetchable:
            return  # Nothing to fetch

        # Prefer Hallowed Fountain early (both colors), then basic matching color need
        fountain = [(i, c) for i, c in fetchable if c == "Hallowed Fountain"]
        if fountain and len(self.battlefield_lands) <= 2:
            idx, card = fountain[0]
            self.library.pop(idx)
            self.battlefield_lands.append(card)
            return

        # Fetch basic matching color deficit
        if w_sources <= u_sources:
            # Need W: fetch Plains
            plains = [(i, c) for i, c in fetchable if c == "Plains"]
            if plains:
                idx, card = plains[0]
                self.library.pop(idx)
                self.battlefield_lands.append(card)
                return
        else:
            # Need U: fetch Island
            islands = [(i, c) for i, c in fetchable if c == "Island"]
            if islands:
                idx, card = islands[0]
                self.library.pop(idx)
                self.battlefield_lands.append(card)
                return

        # Fallback: fetch first available
        idx, card = fetchable[0]
        self.library.pop(idx)
        self.battlefield_lands.append(card)

    def compute_mana_pool(self) -> ManaPool:
        """Calculate total available mana from all untapped lands + rocks."""
        pool = ManaPool()

        for i, land in enumerate(self.battlefield_lands):
            if i in self.tapped_lands:
                continue
            w, u, c, f = compute_land_mana(land, self.battlefield_lands)
            pool.W += w
            pool.U += u
            pool.C += c
            pool.flexible += f

        for rock in self.battlefield_rocks:
            rdef = ROCK_DEFS[rock]
            if rdef["burst"]:
                if self.burst_rocks_active.get(rock, False):
                    pool.C += rdef["C"]
                # Burst rocks don't produce on subsequent turns
            else:
                pool.W += rdef.get("W", 0) if not rdef.get("flexible") else 0
                pool.U += rdef.get("U", 0) if not rdef.get("flexible") else 0
                pool.C += rdef.get("C", 0)
                if rdef.get("flexible"):
                    pool.flexible += 1  # Arcane Signet / Talisman produce 1 colored

        return pool

    def compute_nonland_mana(self) -> int:
        """Calculate mana from nonland permanents (rocks only).

        Used for Isochron combo threshold: need 3+ mana from nonland permanents.
        """
        total = 0
        for rock in self.battlefield_rocks:
            rdef = ROCK_DEFS[rock]
            if rdef["burst"]:
                if self.burst_rocks_active.get(rock, False):
                    total += rdef["C"]
            else:
                total += rdef.get("W", 0) + rdef.get("U", 0) + rdef.get("C", 0)
                if rdef.get("flexible"):
                    # Flexible rocks produce 1 mana (already counted W/U above if non-flexible)
                    # For flexible rocks like Arcane Signet: W=1,U=1,C=0 but they produce 1 of either
                    # We already set W/U to 0 for flexible in compute_mana_pool.
                    # Here we just count the rock as producing 1 mana.
                    total += 1
        return total

    def compute_shorikai_activations(self, pool: ManaPool) -> int:
        """How many times Shorikai can be activated this turn.

        Shorikai costs {1}, {T}. After first activation, it's tapped.
        With Unwinding Clock or Voltaic Key on the battlefield, it can untap.
        For base simulation: 1 activation per turn if we have {1} available.
        """
        # Base: 1 activation if we have at least 1 total mana
        if pool.total >= 1:
            return 1
        return 0

    def play_turn(self, turn_number: int):
        """Simulate one turn."""
        # Draw (skip T1)
        if turn_number > 1:
            self.draw(1)

        # Untap all (mark burst rocks inactive)
        self.tapped_lands.clear()
        for name in list(self.burst_rocks_active.keys()):
            self.burst_rocks_active[name] = False

        # Play best land from hand
        hand_lands = [(self._land_play_priority(c), c) for c in self.hand if self._is_land(c)]
        hand_lands.sort(reverse=True)

        if hand_lands:
            _, land_name = hand_lands[0]
            self.hand.remove(land_name)

            if land_name in FETCHLANDS:
                # Crack immediately
                self._resolve_fetch(land_name)
            else:
                tapped = land_enters_tapped(land_name, self.battlefield_lands, self.hand)
                self.battlefield_lands.append(land_name)
                if tapped:
                    self.tapped_lands.add(len(self.battlefield_lands) - 1)

        # Calculate mana, try to cast rocks
        pool = self.compute_mana_pool()
        self._try_cast_rocks(pool)

        # Try to cast Shorikai from command zone if not yet on board
        # Shorikai = {2}{W}{U}, CMC 4
        if not self.shorikai_on_board:
            cast_pool = self.compute_mana_pool()
            cmd_pips = {"generic": 2, "W": 1, "U": 1}
            if cast_pool.can_cast(cmd_pips):
                self.shorikai_on_board = True
                self.shorikai_cast_turn = turn_number

        # Record final mana pool
        final_pool = self.compute_mana_pool()
        self.mana_per_turn.append(final_pool)

        # Shorikai-specific tracking: activations only count if Shorikai is on board.
        # Shorikai costs {1}, {T} to activate. On the cast turn, it has summoning
        # sickness as a Vehicle... but Vehicles don't have summoning sickness for
        # tap abilities (they're artifacts, not creatures). So Shorikai can activate
        # the turn it's cast.
        if self.shorikai_on_board:
            activations = self.compute_shorikai_activations(final_pool)
        else:
            activations = 0
        self.shorikai_activations += activations
        self.shorikai_activations_per_turn.append(activations)
        self.nonland_mana_per_turn.append(self.compute_nonland_mana())

    def _try_cast_rocks(self, pool: ManaPool):
        """Try to cast mana rocks from hand, priority order."""
        # Priority: Sol Ring > Mana Vault > Chrome Mox > 2-CMC rocks > Basalt Monolith
        priority_order = [
            "Sol Ring", "Mana Vault", "Chrome Mox",
            "Arcane Signet", "Azorius Signet", "Talisman of Progress",
            "Fellwar Stone", "Mind Stone", "Thought Vessel",
            "Basalt Monolith",
        ]

        for rock_name in priority_order:
            if rock_name not in self.hand:
                continue
            rdef = ROCK_DEFS[rock_name]
            pips = parse_mana_cost(self.metadata.get(rock_name, {}).get("mana_cost", ""))
            if pool.can_cast(pips):
                pool = pool.after_spending(pips)
                self.hand.remove(rock_name)
                self.battlefield_rocks.append(rock_name)
                if rdef["burst"]:
                    self.burst_rocks_active[rock_name] = True
                    pool.C += rdef["C"]
                else:
                    pool.C += rdef.get("C", 0)
                    if rdef.get("flexible"):
                        pool.flexible += 1
                    else:
                        pool.W += rdef.get("W", 0)
                        pool.U += rdef.get("U", 0)


def commander_mulligan(decklist: list[str], metadata: dict, land_set: set[str]) -> GameState:
    """Commander mulligan: free first mulligan, then London mulligan.

    attempt 0 = kept first hand (7 cards)
    attempt 1 = free mulligan (7 cards, no penalty)
    attempt 2 = paid mulligan (bottom 1 -> 6 cards)
    """
    attempt = 0
    while True:
        state = GameState(decklist, metadata, land_set)
        state.draw(7)
        if should_mulligan(state.hand, land_set) and attempt < MAX_MULLIGANS:
            attempt += 1
            continue
        break

    # London mulligan: bottom cards if paid mulligan (attempt >= 2)
    if attempt >= 2:
        bottom = choose_bottom_cards(state.hand, attempt - 1, metadata, land_set)
        for card in bottom:
            state.hand.remove(card)
            state.library.append(card)

    state.mulligan_attempt = attempt
    return state


def can_cast_from_hand(state: GameState, pool: ManaPool) -> list[str]:
    """Return list of castable non-rock spells from hand."""
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
            continue  # Skip 0-cost cards that aren't X spells
        if pool.can_cast(pips):
            castable.append(card)
    return castable


# --- Static analysis ---

def print_static_analysis(decklist: list[str], metadata: dict, classified: dict):
    """Print pre-simulation static analysis."""
    print("=" * 65)
    print("STATIC ANALYSIS — GENESIS PROTOCOL (BRACKET 4)")
    print("=" * 65)

    # Deck composition
    print(f"\n--- Deck Composition ---")
    print(f"Total cards (excl. commander): {len(decklist)}")
    print(f"Lands: {len(classified['lands'])}")
    print(f"Mana rocks: {len(classified['rocks'])}")
    print(f"Spells/creatures: {len(classified['spells'])}")

    # CMC histogram
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

    # Pip counts
    total_W = 0
    total_U = 0
    for name in decklist:
        meta = metadata.get(name, {})
        mc = meta.get("mana_cost", "")
        if "Land" in meta.get("type_line", ""):
            continue
        pips = parse_mana_cost(mc)
        total_W += pips["W"]
        total_U += pips["U"]

    total_pips = total_W + total_U
    w_ratio = total_W / total_pips * 100 if total_pips > 0 else 0
    u_ratio = total_U / total_pips * 100 if total_pips > 0 else 0

    print(f"\n--- Pip Demand ---")
    print(f"  Total {{W}} pips: {total_W}")
    print(f"  Total {{U}} pips: {total_U}")
    print(f"  Ratio: {w_ratio:.0f}% W / {u_ratio:.0f}% U")

    # Mana source inventory
    lands = classified["lands"]
    w_sources = sum(1 for l in lands if l in W_PRODUCING_LANDS)
    u_sources = sum(1 for l in lands if l in U_PRODUCING_LANDS)
    both_sources = sum(1 for l in lands if l in W_PRODUCING_LANDS and l in U_PRODUCING_LANDS)
    c_only = sum(1 for l in lands if l in C_ONLY_LANDS)
    fetch_count = sum(1 for l in lands if l in FETCHLANDS)

    print(f"\n--- Mana Source Inventory ---")
    print(f"  W-producing lands: {w_sources}")
    print(f"  U-producing lands: {u_sources}")
    print(f"  Dual (W+U) lands: {both_sources}")
    print(f"  C-only lands: {c_only}")
    print(f"  Fetchlands: {fetch_count}")

    rock_flex = sum(1 for r in classified["rocks"] if ROCK_DEFS[r].get("flexible"))
    rock_c = sum(1 for r in classified["rocks"] if not ROCK_DEFS[r].get("flexible"))
    print(f"  Flexible rocks (W/U): {rock_flex}")
    print(f"  Colorless rocks: {rock_c}")

    # Recommended land count heuristic
    recommended = round(36 + (avg_cmc - 3.0) * 2)
    print(f"\n--- Land Count Heuristic ---")
    print(f"  Avg CMC: {avg_cmc:.2f}")
    print(f"  Current lands: {len(lands)}")
    print(f"  Heuristic recommendation: ~{recommended} lands")
    if len(lands) >= recommended:
        print(f"  Status: adequate ({len(lands)} >= {recommended})")
    else:
        print(f"  Status: light ({len(lands)} < {recommended}, delta = {recommended - len(lands)})")

    return avg_cmc, total_W, total_U


# --- Simulation ---

def run_simulation(decklist: list[str], metadata: dict, num_games: int = NUM_GAMES) -> dict:
    """Run num_games simulations and collect stats."""
    land_set = set()
    for name in set(decklist):
        meta = metadata.get(name, {})
        if "Land" in meta.get("type_line", ""):
            land_set.add(name)

    # Stats collectors
    mana_by_turn = {t: [] for t in range(1, NUM_TURNS + 1)}
    w_by_turn = {t: [] for t in range(1, NUM_TURNS + 1)}
    u_by_turn = {t: [] for t in range(1, NUM_TURNS + 1)}
    hand_land_counts = Counter()
    mulligan_attempts = Counter()

    # Color screw tracking
    zero_w_by_turn = {t: 0 for t in range(1, NUM_TURNS + 1)}
    zero_u_by_turn = {t: 0 for t in range(1, NUM_TURNS + 1)}

    # Commander timing
    commander_castable_turn = []
    commander_by_turn = {t: 0 for t in range(1, NUM_TURNS + 1)}

    # Curve efficiency
    castable_spell_by_turn = {t: 0 for t in range(1, NUM_TURNS + 1)}
    curve_out_games = 0

    # ETB tapped tracking
    tapped_land_turns = {1: 0, 2: 0}

    # Shorikai-specific: crew readiness (3+ cumulative activations by turn)
    crew_ready_by_turn = {t: 0 for t in range(1, NUM_TURNS + 1)}

    # Isochron combo threshold: 3+ mana from nonland permanents
    isochron_ready_by_turn = {t: 0 for t in range(1, NUM_TURNS + 1)}

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
            w_avail = pool.W + pool.flexible  # flexible can be W
            u_avail = pool.U + pool.flexible  # flexible can be U

            mana_by_turn[t].append(total)
            w_by_turn[t].append(w_avail)
            u_by_turn[t].append(u_avail)

            if w_avail == 0:
                zero_w_by_turn[t] += 1
            if u_avail == 0:
                zero_u_by_turn[t] += 1

            # Commander castable: Shorikai = {2}{W}{U} = 4 total with 1W and 1U
            cmd_pips = {"generic": 2, "W": 1, "U": 1}
            if cmd_cast_turn is None and pool.can_cast(cmd_pips):
                cmd_cast_turn = t
                commander_by_turn[t] += 1

            # Castable spell check
            castable = can_cast_from_hand(state, pool)
            if castable:
                castable_spell_by_turn[t] += 1
            elif t <= 4:
                cast_every_turn = False

            # ETB tapped tracking
            if t <= 2 and lands_after > lands_before:
                new_idx = lands_after - 1
                if new_idx in state.tapped_lands:
                    tapped_land_turns[t] += 1

            # Crew readiness: cumulative Shorikai activations >= 3 by turn t
            if state.shorikai_activations >= 3:
                crew_ready_by_turn[t] += 1

            # Isochron combo threshold: 3+ mana from nonland permanents
            if state.nonland_mana_per_turn[-1] >= 3:
                isochron_ready_by_turn[t] += 1

        if cmd_cast_turn is not None:
            commander_castable_turn.append(cmd_cast_turn)
            # Also count for turns after first castable
            for future_t in range(cmd_cast_turn + 1, NUM_TURNS + 1):
                commander_by_turn[future_t] += 1

        if cast_every_turn:
            curve_out_games += 1

    return {
        "mana_by_turn": mana_by_turn,
        "w_by_turn": w_by_turn,
        "u_by_turn": u_by_turn,
        "hand_land_counts": hand_land_counts,
        "mulligan_attempts": mulligan_attempts,
        "zero_w_by_turn": zero_w_by_turn,
        "zero_u_by_turn": zero_u_by_turn,
        "commander_castable_turn": commander_castable_turn,
        "commander_by_turn": commander_by_turn,
        "castable_spell_by_turn": castable_spell_by_turn,
        "curve_out_games": curve_out_games,
        "tapped_land_turns": tapped_land_turns,
        "crew_ready_by_turn": crew_ready_by_turn,
        "isochron_ready_by_turn": isochron_ready_by_turn,
    }


def print_results(stats: dict, classified: dict, avg_cmc: float, pip_W: int, pip_U: int):
    """Print simulation results."""
    total = NUM_GAMES

    print("\n" + "=" * 65)
    print(f"MONTE CARLO SIMULATION — GENESIS PROTOCOL ({NUM_GAMES:,} games, {NUM_TURNS} turns)")
    print("=" * 65)

    # Dimension 1: Mana Base
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
    print(f"    Land count distribution (kept hand):")
    for lands in range(8):
        count = stats["hand_land_counts"].get(lands, 0)
        if count > 0:
            bar = "#" * int(count / total * 50)
            print(f"      {lands} lands: {count/total*100:>5.1f}% {bar}")

    # Dimension 2: Color Balance
    print(f"\n--- Dimension 2: Color Balance ---")
    print(f"\n  W and U available per turn (includes flexible sources):")
    print(f"  {'Turn':<6} {'W med':>7} {'W mean':>7} {'U med':>7} {'U mean':>7}")
    print(f"  {'-'*38}")
    for t in range(1, NUM_TURNS + 1):
        w_med = statistics.median(stats["w_by_turn"][t])
        w_mean = statistics.mean(stats["w_by_turn"][t])
        u_med = statistics.median(stats["u_by_turn"][t])
        u_mean = statistics.mean(stats["u_by_turn"][t])
        print(f"    T{t:<4} {w_med:>7.0f} {w_mean:>7.1f} {u_med:>7.0f} {u_mean:>7.1f}")

    print(f"\n  Color screw (0 sources of a color):")
    for t in range(2, NUM_TURNS + 1):
        w_pct = stats["zero_w_by_turn"][t] / total * 100
        u_pct = stats["zero_u_by_turn"][t] / total * 100
        print(f"    T{t}: 0 W sources = {w_pct:.1f}%, 0 U sources = {u_pct:.1f}%")

    pip_total = pip_W + pip_U
    w_demand = pip_W / pip_total * 100 if pip_total > 0 else 0
    u_demand = pip_U / pip_total * 100 if pip_total > 0 else 0

    t3_w = statistics.mean(stats["w_by_turn"][3])
    t3_u = statistics.mean(stats["u_by_turn"][3])
    t3_total = t3_w + t3_u
    w_supply = t3_w / t3_total * 100 if t3_total > 0 else 0
    u_supply = t3_u / t3_total * 100 if t3_total > 0 else 0

    print(f"\n  Pip demand vs supply ratio (T3 avg):")
    print(f"    Demand: {w_demand:.0f}% W / {u_demand:.0f}% U")
    print(f"    Supply: {w_supply:.0f}% W / {u_supply:.0f}% U")

    # Dimension 3: Curve Efficiency
    print(f"\n--- Dimension 3: Curve Efficiency ---")

    print(f"\n  Commander castable (Shorikai, Genesis Engine, {{2}}{{W}}{{U}}):")
    for t in range(2, NUM_TURNS + 1):
        count = stats["commander_by_turn"][t]
        print(f"    By T{t}: {count/total*100:.1f}%")
    if stats["commander_castable_turn"]:
        med = statistics.median(stats["commander_castable_turn"])
        print(f"    Median turn: {med:.1f}")

    print(f"\n  Castable spell from hand (non-rock, color-aware):")
    for t in range(1, NUM_TURNS + 1):
        pct = stats["castable_spell_by_turn"][t] / total * 100
        print(f"    T{t}: {pct:.1f}%")

    print(f"\n  Curve-out rate (cast something T1-T4): {stats['curve_out_games']/total*100:.1f}%")

    print(f"\n  ETB tapped frequency:")
    for t in [1, 2]:
        pct = stats["tapped_land_turns"][t] / total * 100
        print(f"    T{t} land entered tapped: {pct:.1f}%")

    # Shorikai-specific metrics
    print(f"\n--- Dimension 4: Shorikai-Specific Metrics ---")

    print(f"\n  Crew readiness (3+ cumulative Shorikai activations):")
    for t in range(2, NUM_TURNS + 1):
        pct = stats["crew_ready_by_turn"][t] / total * 100
        print(f"    By T{t}: {pct:.1f}%")

    print(f"\n  Isochron combo threshold (3+ mana from nonland permanents):")
    for t in range(1, NUM_TURNS + 1):
        pct = stats["isochron_ready_by_turn"][t] / total * 100
        print(f"    By T{t}: {pct:.1f}%")

    # Assessment
    print(f"\n--- Mana Base Assessment ---")

    med_t1 = statistics.median(stats["mana_by_turn"][1])
    med_t3 = statistics.median(stats["mana_by_turn"][3])
    med_t5 = statistics.median(stats["mana_by_turn"][5])
    med_last = statistics.median(stats["mana_by_turn"][NUM_TURNS])
    mull = stats["mulligan_attempts"]
    paid_mull_rate = mull.get(2, 0) / total * 100

    print(f"\n  Median mana: T1={med_t1:.0f}, T3={med_t3:.0f}, T5={med_t5:.0f}, T{NUM_TURNS}={med_last:.0f}")

    # Land count vs heuristic
    land_count = len(classified["lands"])
    recommended = round(36 + (avg_cmc - 3.0) * 2)
    if land_count >= recommended:
        print(f"  Land count: {land_count} (adequate for avg CMC {avg_cmc:.2f})")
    else:
        print(f"  Land count: {land_count} (light for avg CMC {avg_cmc:.2f}, heuristic suggests ~{recommended})")

    # Paid mulligan rate
    if paid_mull_rate < 5:
        print(f"  Paid mulligan rate: {paid_mull_rate:.1f}% — acceptable")
    else:
        print(f"  Paid mulligan rate: {paid_mull_rate:.1f}% — consider adding lands/rocks")

    # Color ratio
    w_deficit = abs(w_demand - w_supply)
    if w_deficit < 10:
        print(f"  Color balance: well-matched (demand/supply within {w_deficit:.0f}%)")
    else:
        if w_supply > w_demand:
            print(f"  Color balance: W-heavy supply ({w_supply:.0f}% vs {w_demand:.0f}% demand) — consider more U sources")
        else:
            print(f"  Color balance: U-heavy supply ({u_supply:.0f}% vs {u_demand:.0f}% demand) — consider more W sources")

    # Commander timing
    cmd_by_t3 = stats["commander_by_turn"][3] / total * 100
    cmd_by_t4 = stats["commander_by_turn"][4] / total * 100
    if cmd_by_t3 > 50:
        print(f"  Commander by T3: {cmd_by_t3:.0f}% — realistic T3 Shorikai (ahead of curve)")
    elif cmd_by_t4 > 50:
        print(f"  Commander by T4: {cmd_by_t4:.0f}% — on-curve T4 Shorikai")
    else:
        print(f"  Commander by T4: {cmd_by_t4:.0f}% — below 50%, ramp may be insufficient")

    # ETB tapped
    t1_tapped = stats["tapped_land_turns"][1] / total * 100
    t2_tapped = stats["tapped_land_turns"][2] / total * 100
    if t1_tapped < 10 and t2_tapped < 15:
        print(f"  ETB tapped T1/T2: {t1_tapped:.0f}%/{t2_tapped:.0f}% — minimal tempo loss")
    else:
        print(f"  ETB tapped T1/T2: {t1_tapped:.0f}%/{t2_tapped:.0f}% — significant tempo drag")

    # Isochron combo
    iso_t4 = stats["isochron_ready_by_turn"][4] / total * 100
    iso_t5 = stats["isochron_ready_by_turn"][5] / total * 100
    print(f"  Isochron combo ready by T4: {iso_t4:.0f}%, by T5: {iso_t5:.0f}%")


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


def export_enhanced_json(metadata: dict) -> dict:
    """Reuse bulk exporter path so standalone JSON stays schema-compatible."""
    import export_simulation_results as exporter

    result = exporter.export_azorius(metadata)
    if not exporter.validate_output(result, "genesis-protocol"):
        raise ValueError("export_azorius produced invalid simulation output")
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Monte Carlo mana base simulation for Genesis Protocol (Shorikai)")
    parser.add_argument("--json", action="store_true",
                        help="Write simulation.json instead of console output")
    args = parser.parse_args()

    with open(DECK_FILE) as f:
        deck_data = json.load(f)
    with open(METADATA_FILE) as f:
        metadata = json.load(f)

    print("Building Genesis Protocol decklist...")
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

    avg_cmc, pip_W, pip_U = print_static_analysis(decklist, metadata, classified)

    n_workers = os.cpu_count() or 4
    chunk_size = NUM_GAMES // n_workers
    remainder = NUM_GAMES % n_workers
    chunks = [chunk_size + (1 if i < remainder else 0) for i in range(n_workers)]

    print(f"\nRunning {NUM_GAMES:,} game simulations ({n_workers} workers)...")
    with multiprocessing.Pool(n_workers) as pool:
        results = pool.map(_run_chunk, [(decklist, metadata, n) for n in chunks])
    stats = merge_stats(results)

    print_results(stats, classified, avg_cmc, pip_W, pip_U)
    print("\n" + "=" * 65)


if __name__ == "__main__":
    main()
