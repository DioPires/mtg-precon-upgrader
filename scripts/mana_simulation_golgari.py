#!/usr/bin/env python3
"""Monte Carlo mana base simulation for Eternal Harvest (Meren of Clan Nel Toth).

Simulates 100,000 games measuring mana production, color balance, and curve
efficiency turns 1-10 for the Bracket 3 Golgari decklist.

Commander: Meren of Clan Nel Toth ({2}{B}{G}, CMC 4)
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
DECK_FILE = PROJECT_ROOT / "data" / "commanders" / "eternal-harvest" / "deck.json"
METADATA_FILE = PROJECT_ROOT / "data" / "card-metadata.json"

NUM_GAMES = 100_000
NUM_TURNS = 10

# --- Mana cost parser ---

def parse_mana_cost(mana_cost: str) -> dict:
    """Parse mana_cost string into pip breakdown.

    "{2}{B}{G}" -> {generic: 2, B: 1, G: 1, total: 4}
    "{B}{B}{B}" -> {generic: 0, B: 3, G: 0, total: 3}
    "{X}{B}{B}" -> {generic: 0, B: 2, G: 0, total: 2, X: True}

    Split cards (//): parse first half only.
    """
    if "//" in mana_cost:
        mana_cost = mana_cost.split("//")[0].strip()

    result = {"generic": 0, "B": 0, "G": 0, "total": 0, "X": False}
    symbols = re.findall(r"\{([^}]+)\}", mana_cost)
    for sym in symbols:
        if sym == "X":
            result["X"] = True
        elif sym.isdigit():
            result["generic"] += int(sym)
        elif sym == "B":
            result["B"] += 1
        elif sym == "G":
            result["G"] += 1
        # Ignore other symbols (hybrid, phyrexian, etc.)
    result["total"] = result["generic"] + result["B"] + result["G"]
    return result


# --- Rock definitions ---

ROCK_DEFS = {
    "Sol Ring":        {"cmc": 1, "B": 0, "G": 0, "C": 2, "burst": False},
    "Arcane Signet":   {"cmc": 2, "B": 1, "G": 1, "C": 0, "burst": False, "flexible": True},
}

# --- Mana dork definitions ---
# Dorks are cast with {G} (CMC 1), produce mana from the turn AFTER they're cast.

DORK_DEFS = {
    "Birds of Paradise":    {"cmc": 1, "B": 1, "G": 1, "C": 0, "flexible": True},
    "Elves of Deep Shadow": {"cmc": 1, "B": 1, "G": 0, "C": 0, "flexible": False},
    "Llanowar Elves":       {"cmc": 1, "B": 0, "G": 1, "C": 0, "flexible": False},
    "Badgermole Cub":       {"cmc": 2, "B": 0, "G": 1, "C": 0, "flexible": False},
}

# --- Creature ramp definitions ---
# These fetch lands when cast. Modeled as delayed land additions.

CREATURE_RAMP = {
    "Sakura-Tribe Elder":  {"cmc": 2, "pips": {"generic": 1, "B": 0, "G": 1}, "fetch": "basic", "tapped": False},
    "Wood Elves":          {"cmc": 3, "pips": {"generic": 2, "B": 0, "G": 1}, "fetch": "forest", "tapped": False},
    "Solemn Simulacrum":   {"cmc": 4, "pips": {"generic": 4, "B": 0, "G": 0}, "fetch": "basic", "tapped": True},
}

# Wight of the Reliquary: treat as a dork producing {G} (too complex to model sac)
# Added to DORK_DEFS-like handling in classify_cards

WIGHT_NAME = "Wight of the Reliquary"

# --- Land definitions ---

B_PRODUCING_LANDS = {
    "Swamp", "Overgrown Tomb", "Command Tower", "Blooming Marsh",
    "Woodland Cemetery", "Llanowar Wastes", "Nurturing Peatland",
    "Darkbore Pathway", "Deathcap Glade", "Temple of Malady",
    "Castle Locthwain", "Urborg, Tomb of Yawgmoth",
}

G_PRODUCING_LANDS = {
    "Forest", "Overgrown Tomb", "Command Tower", "Blooming Marsh",
    "Woodland Cemetery", "Llanowar Wastes", "Nurturing Peatland",
    "Darkbore Pathway", "Deathcap Glade", "Temple of Malady",
    "Dryad Arbor",
}

C_ONLY_LANDS = {
    "Ancient Tomb", "Phyrexian Tower", "High Market",
}

# Lands with Swamp subtype (for Urborg, Woodland Cemetery checks)
SWAMP_TYPED_LANDS = {"Swamp", "Overgrown Tomb"}
# Lands with Forest subtype
FOREST_TYPED_LANDS = {"Forest", "Overgrown Tomb", "Dryad Arbor"}

BASIC_SWAMPS = {"Swamp"}
BASIC_FORESTS = {"Forest"}


def build_decklist(deck_data: dict) -> list[str]:
    """Build the 99-card decklist for Eternal Harvest."""
    cards = []
    for card in deck_data["decklist"]:
        qty = card.get("quantity", 1)
        cards.extend([card["name"]] * qty)
    return cards


def classify_cards(decklist: list[str], metadata: dict) -> dict:
    """Classify each card as land, rock, or spell.

    Rocks include mana rocks and mana dorks (both are ramp).
    """
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

def has_urborg(battlefield_lands: list[str]) -> bool:
    return "Urborg, Tomb of Yawgmoth" in battlefield_lands


def count_basics(battlefield_lands: list[str]) -> int:
    return sum(1 for l in battlefield_lands if l in BASIC_SWAMPS or l in BASIC_FORESTS)


def land_enters_tapped(name: str, battlefield_lands: list[str], hand: list[str]) -> bool:
    """Determine if a land enters tapped given board + hand state."""
    urborg = has_urborg(battlefield_lands)
    other_count = len(battlefield_lands)

    if name == "Bojuka Bog":
        return True

    if name == "Temple of Malady":
        return True

    if name == "Deathcap Glade":
        return other_count < 2

    if name == "Woodland Cemetery":
        if urborg:
            return False
        has_swamp_or_forest = any(
            l in SWAMP_TYPED_LANDS or l in FOREST_TYPED_LANDS
            for l in battlefield_lands
        )
        return not has_swamp_or_forest

    if name == "Blooming Marsh":
        return other_count >= 3

    if name == "Castle Locthwain":
        if urborg:
            return False
        swamp_in_play = any(l in SWAMP_TYPED_LANDS for l in battlefield_lands)
        return not swamp_in_play

    if name == "Agadeem's Awakening // Agadeem, the Undercrypt":
        return True

    return False


class ManaPool:
    """Tracks available B, G, C mana and flexible sources."""
    def __init__(self):
        self.B = 0
        self.G = 0
        self.C = 0
        self.flexible = 0  # can be B or G

    @property
    def total(self):
        return self.B + self.G + self.C + self.flexible

    def can_cast(self, pips: dict) -> bool:
        """Check if we can cast a spell with the given pip requirements."""
        need_B = pips["B"]
        need_G = pips["G"]
        need_generic = pips["generic"]

        avail_B = self.B
        avail_G = self.G
        avail_C = self.C
        avail_flex = self.flexible

        # Assign fixed B sources to B pips
        used_B = min(avail_B, need_B)
        remaining_B = need_B - used_B
        avail_B -= used_B

        # Assign fixed G sources to G pips
        used_G = min(avail_G, need_G)
        remaining_G = need_G - used_G
        avail_G -= used_G

        # Use flexible for remaining colored needs
        remaining_colored = remaining_B + remaining_G
        if avail_flex < remaining_colored:
            return False
        avail_flex -= remaining_colored

        # Remaining generic from leftover B, G, C, flexible
        leftover = avail_B + avail_G + avail_C + avail_flex
        return leftover >= need_generic

    def after_spending(self, pips: dict) -> "ManaPool":
        """Return a new ManaPool after spending pips. Assumes can_cast is True."""
        pool = ManaPool()
        pool.B = self.B
        pool.G = self.G
        pool.C = self.C
        pool.flexible = self.flexible

        need_B = pips["B"]
        need_G = pips["G"]
        need_generic = pips["generic"]

        # Spend fixed B
        from_B = min(pool.B, need_B)
        pool.B -= from_B
        need_B -= from_B

        # Spend fixed G
        from_G = min(pool.G, need_G)
        pool.G -= from_G
        need_G -= from_G

        # Spend flexible on remaining colored
        flex_colored = need_B + need_G
        pool.flexible -= flex_colored

        # Spend generic: C first, then leftover B/G, then flexible
        remaining = need_generic
        from_C = min(pool.C, remaining)
        pool.C -= from_C
        remaining -= from_C

        from_B2 = min(pool.B, remaining)
        pool.B -= from_B2
        remaining -= from_B2

        from_G2 = min(pool.G, remaining)
        pool.G -= from_G2
        remaining -= from_G2

        from_flex = min(pool.flexible, remaining)
        pool.flexible -= from_flex

        return pool


def compute_land_mana(name: str, battlefield_lands: list[str]) -> tuple[int, int, int, int]:
    """Return (B, G, C, flexible) mana a single untapped land produces."""
    urborg = has_urborg(battlefield_lands)

    if name == "Phyrexian Tower":
        return (0, 0, 1, 0)

    if name == "High Market":
        return (0, 0, 1, 0)

    if name == "Ancient Tomb":
        return (0, 0, 2, 0)

    if name == "Urborg, Tomb of Yawgmoth":
        return (1, 0, 0, 0)

    if name == "Verdant Catacombs":
        # Should already be cracked; if somehow on board, treat as 0
        return (0, 0, 0, 0)

    if name == "Castle Locthwain":
        b = 1
        return (b, 0, 0, 0)

    if name == "Boseiju, Who Endures":
        return (0, 1, 0, 0)

    if name == "Takenuma, Abandoned Mire":
        return (1, 0, 0, 0)

    if name == "Bojuka Bog":
        return (1, 0, 0, 0)

    if name == "Dryad Arbor":
        return (0, 1, 0, 0)

    if name == "Agadeem's Awakening // Agadeem, the Undercrypt":
        return (1, 0, 0, 0)

    # Dual lands (produce B or G -> flexible)
    if name in {
        "Overgrown Tomb", "Command Tower", "Blooming Marsh",
        "Woodland Cemetery", "Llanowar Wastes", "Nurturing Peatland",
        "Darkbore Pathway", "Deathcap Glade", "Temple of Malady",
    }:
        f = 1
        return (0, 0, 0, f)

    # Basic Swamp
    if name == "Swamp":
        b = 1
        if urborg:
            pass  # No Crypt Ghast in this deck
        return (b, 0, 0, 0)

    # Basic Forest
    if name == "Forest":
        g = 1
        if urborg:
            # Urborg makes Forest also a Swamp, but it still taps for G
            # Model as flexible (can produce B via Urborg or G natively)
            return (0, 0, 0, 1)
        return (0, g, 0, 0)

    # Fallback: colorless
    return (0, 0, 1, 0)


MAX_MULLIGANS = 2


def should_mulligan(hand: list[str], land_set: set[str]) -> bool:
    """Mulligan if 0-1 mana sources (lands + rocks + dorks)."""
    sources = sum(1 for c in hand if c in land_set or c in ROCK_DEFS or c in DORK_DEFS)
    return sources <= 1


def choose_bottom_cards(hand: list[str], count: int, metadata: dict, land_set: set[str]) -> list[str]:
    """Choose cards to bottom (London mulligan). Bottom highest CMC non-land, non-ramp cards."""
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
        self.tapped_lands: set[int] = set()  # indices into battlefield_lands
        self.battlefield_rocks: list[str] = []
        self.battlefield_dorks: list[str] = []  # dorks on battlefield (produce mana next turn)
        self.dorks_active: list[str] = []  # dorks that can tap for mana this turn
        self.burst_rocks_active: dict[str, bool] = {}
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

    def count_rocks_in_hand(self) -> int:
        return sum(1 for c in self.hand if c in ROCK_DEFS or c in DORK_DEFS)

    def _is_land(self, name: str) -> bool:
        return name in self.land_set

    def _land_play_priority(self, name: str) -> float:
        """Higher = play first. Untapped > tapped. Color-fixing > mono."""
        tapped = land_enters_tapped(name, self.battlefield_lands, self.hand)

        if name == "Verdant Catacombs":
            return 20  # Fetch: always play and crack immediately

        if tapped:
            base = 0
        else:
            base = 10

        # Duals (flexible color) get bonus
        if name in B_PRODUCING_LANDS and name in G_PRODUCING_LANDS:
            base += 5
        elif name == "Urborg, Tomb of Yawgmoth":
            base += 6  # Fixes all lands to Swamps
        elif name in B_PRODUCING_LANDS or name in G_PRODUCING_LANDS:
            base += 2

        return base

    def _resolve_fetch(self, fetch_name: str):
        """Resolve Verdant Catacombs: search library for Forest or Swamp card."""
        b_sources = sum(1 for l in self.battlefield_lands if l in B_PRODUCING_LANDS)
        g_sources = sum(1 for l in self.battlefield_lands if l in G_PRODUCING_LANDS)

        fetchable = []
        for i, card in enumerate(self.library):
            if card in SWAMP_TYPED_LANDS or card in FOREST_TYPED_LANDS or card in BASIC_SWAMPS or card in BASIC_FORESTS:
                fetchable.append((i, card))

        if not fetchable:
            return

        # Prefer Overgrown Tomb early (both colors), then basic matching color need
        tomb = [(i, c) for i, c in fetchable if c == "Overgrown Tomb"]
        if tomb and len(self.battlefield_lands) <= 2:
            idx, card = tomb[0]
            self.library.pop(idx)
            self.battlefield_lands.append(card)
            return

        if b_sources <= g_sources:
            swamps = [(i, c) for i, c in fetchable if c == "Swamp"]
            if swamps:
                idx, card = swamps[0]
                self.library.pop(idx)
                self.battlefield_lands.append(card)
                return
        else:
            forests = [(i, c) for i, c in fetchable if c == "Forest"]
            if forests:
                idx, card = forests[0]
                self.library.pop(idx)
                self.battlefield_lands.append(card)
                return

        # Fallback: fetch first available
        idx, card = fetchable[0]
        self.library.pop(idx)
        self.battlefield_lands.append(card)

    def _fetch_basic_land(self, fetch_type: str, enters_tapped: bool):
        """Fetch a basic land from library and put it on battlefield.

        fetch_type: 'basic' (Swamp or Forest based on need), 'forest' (Forest only)
        """
        b_sources = sum(1 for l in self.battlefield_lands if l in B_PRODUCING_LANDS)
        g_sources = sum(1 for l in self.battlefield_lands if l in G_PRODUCING_LANDS)

        if fetch_type == "forest":
            targets = [i for i, c in enumerate(self.library) if c == "Forest"]
        else:
            # Basic: choose based on color need
            if b_sources <= g_sources:
                targets = [i for i, c in enumerate(self.library) if c == "Swamp"]
                if not targets:
                    targets = [i for i, c in enumerate(self.library) if c == "Forest"]
            else:
                targets = [i for i, c in enumerate(self.library) if c == "Forest"]
                if not targets:
                    targets = [i for i, c in enumerate(self.library) if c == "Swamp"]

        if targets:
            idx = targets[0]
            card = self.library.pop(idx)
            self.battlefield_lands.append(card)
            if enters_tapped:
                self.tapped_lands.add(len(self.battlefield_lands) - 1)

    def compute_mana_pool(self) -> ManaPool:
        """Calculate total available mana from all untapped lands + rocks + dorks."""
        pool = ManaPool()

        for i, land in enumerate(self.battlefield_lands):
            if i in self.tapped_lands:
                continue
            b, g, c, f = compute_land_mana(land, self.battlefield_lands)
            pool.B += b
            pool.G += g
            pool.C += c
            pool.flexible += f

        for rock in self.battlefield_rocks:
            rdef = ROCK_DEFS[rock]
            if rdef["burst"]:
                if self.burst_rocks_active.get(rock, False):
                    pool.C += rdef["C"]
            else:
                pool.C += rdef.get("C", 0)
                if rdef.get("flexible"):
                    pool.flexible += 1
                else:
                    pool.B += rdef.get("B", 0)
                    pool.G += rdef.get("G", 0)

        # Active dorks (summoning sickness resolved)
        for dork in self.dorks_active:
            if dork == WIGHT_NAME:
                pool.G += 1
            elif dork in DORK_DEFS:
                ddef = DORK_DEFS[dork]
                if ddef.get("flexible"):
                    pool.flexible += 1
                else:
                    pool.B += ddef.get("B", 0)
                    pool.G += ddef.get("G", 0)

        return pool

    def play_turn(self, turn_number: int):
        """Simulate one turn."""
        if turn_number > 1:
            self.draw(1)

        # Untap all
        self.tapped_lands.clear()
        for name in list(self.burst_rocks_active.keys()):
            self.burst_rocks_active[name] = False

        # Activate dorks that were on battlefield last turn (summoning sickness resolved)
        self.dorks_active = list(self.battlefield_dorks)

        # Play best land from hand
        hand_lands = [(self._land_play_priority(c), c) for c in self.hand if self._is_land(c)]
        hand_lands.sort(reverse=True)

        if hand_lands:
            _, land_name = hand_lands[0]
            self.hand.remove(land_name)

            if land_name == "Verdant Catacombs":
                self._resolve_fetch(land_name)
            else:
                tapped = land_enters_tapped(land_name, self.battlefield_lands, self.hand)
                self.battlefield_lands.append(land_name)
                if tapped:
                    self.tapped_lands.add(len(self.battlefield_lands) - 1)

        # Calculate mana, try to cast rocks/dorks/creature ramp
        pool = self.compute_mana_pool()
        self._try_cast_ramp(pool)

        # Record final mana pool
        self.mana_per_turn.append(self.compute_mana_pool())

    def _try_cast_ramp(self, pool: ManaPool):
        """Try to cast mana rocks, dorks, and creature ramp from hand, priority order."""
        # Priority: Sol Ring > 2-CMC rock > 1-CMC dorks > creature ramp
        priority_order = [
            ("rock", "Sol Ring"),
            ("rock", "Arcane Signet"),
            ("dork", "Llanowar Elves"),
            ("dork", "Elves of Deep Shadow"),
            ("dork", "Birds of Paradise"),
            ("dork", WIGHT_NAME),
            ("creature_ramp", "Sakura-Tribe Elder"),
            ("creature_ramp", "Wood Elves"),
            ("creature_ramp", "Solemn Simulacrum"),
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
                    if rdef["burst"]:
                        self.burst_rocks_active[name] = True
                        pool.C += rdef["C"]
                    else:
                        pool.C += rdef.get("C", 0)
                        if rdef.get("flexible"):
                            pool.flexible += 1
                        else:
                            pool.B += rdef.get("B", 0)
                            pool.G += rdef.get("G", 0)

            elif ramp_type == "dork":
                # Dorks cost {G} (CMC 1) except Wight which costs {1}{G}
                if name == WIGHT_NAME:
                    pips = {"generic": 1, "B": 0, "G": 1}
                else:
                    pips = {"generic": 0, "B": 0, "G": 1}
                if pool.can_cast(pips):
                    pool = pool.after_spending(pips)
                    self.hand.remove(name)
                    self.battlefield_dorks.append(name)
                    # Dorks have summoning sickness — mana available next turn

            elif ramp_type == "creature_ramp":
                cramp = CREATURE_RAMP[name]
                pips = cramp["pips"]
                if pool.can_cast(pips):
                    pool = pool.after_spending(pips)
                    self.hand.remove(name)
                    self._fetch_basic_land(cramp["fetch"], cramp["tapped"])


def commander_mulligan(decklist: list[str], metadata: dict, land_set: set[str]) -> GameState:
    """Commander mulligan: free first mulligan, then London mulligan."""
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
    ramp_cards = set(ROCK_DEFS) | set(DORK_DEFS) | set(CREATURE_RAMP) | {WIGHT_NAME}
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

def print_static_analysis(decklist: list[str], metadata: dict, classified: dict):
    """Print pre-simulation static analysis."""
    print("=" * 65)
    print("STATIC ANALYSIS — ETERNAL HARVEST (BRACKET 3)")
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

    total_B = 0
    total_G = 0
    for name in decklist:
        meta = metadata.get(name, {})
        mc = meta.get("mana_cost", "")
        if "Land" in meta.get("type_line", ""):
            continue
        pips = parse_mana_cost(mc)
        total_B += pips["B"]
        total_G += pips["G"]

    total_pips = total_B + total_G
    b_ratio = total_B / total_pips * 100 if total_pips > 0 else 0
    g_ratio = total_G / total_pips * 100 if total_pips > 0 else 0

    print(f"\n--- Pip Demand ---")
    print(f"  Total {{B}} pips: {total_B}")
    print(f"  Total {{G}} pips: {total_G}")
    print(f"  Ratio: {b_ratio:.0f}% B / {g_ratio:.0f}% G")

    lands = classified["lands"]
    b_sources = sum(1 for l in lands if l in B_PRODUCING_LANDS)
    g_sources = sum(1 for l in lands if l in G_PRODUCING_LANDS)
    both_sources = sum(1 for l in lands if l in B_PRODUCING_LANDS and l in G_PRODUCING_LANDS)
    c_only = sum(1 for l in lands if l in C_ONLY_LANDS)
    special = sum(1 for l in lands if l in {"Verdant Catacombs"})

    print(f"\n--- Mana Source Inventory ---")
    print(f"  B-producing lands: {b_sources}")
    print(f"  G-producing lands: {g_sources}")
    print(f"  Dual (B+G) lands: {both_sources}")
    print(f"  C-only lands: {c_only}")
    print(f"  Fetch: {special} (Verdant Catacombs)")

    rock_flex = sum(1 for r in classified["rocks"] if r in ROCK_DEFS and ROCK_DEFS[r].get("flexible"))
    rock_c = sum(1 for r in classified["rocks"] if r in ROCK_DEFS and not ROCK_DEFS[r].get("flexible"))
    dork_count = sum(1 for r in classified["rocks"] if r in DORK_DEFS)
    print(f"  Flexible rocks (B/G): {rock_flex}")
    print(f"  Colorless rocks: {rock_c}")
    print(f"  Mana dorks: {dork_count}")

    recommended = round(36 + (avg_cmc - 3.0) * 2)
    print(f"\n--- Land Count Heuristic ---")
    print(f"  Avg CMC: {avg_cmc:.2f}")
    print(f"  Current lands: {len(lands)}")
    print(f"  Heuristic recommendation: ~{recommended} lands")
    if len(lands) >= recommended:
        print(f"  Status: adequate ({len(lands)} >= {recommended})")
    else:
        print(f"  Status: light ({len(lands)} < {recommended}, delta = {recommended - len(lands)})")

    return avg_cmc, total_B, total_G


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
    g_by_turn = {t: [] for t in range(1, NUM_TURNS + 1)}
    hand_land_counts = Counter()
    mulligan_attempts = Counter()

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
            total = pool.total
            b_avail = pool.B + pool.flexible
            g_avail = pool.G + pool.flexible

            mana_by_turn[t].append(total)
            b_by_turn[t].append(b_avail)
            g_by_turn[t].append(g_avail)

            if b_avail == 0:
                zero_b_by_turn[t] += 1
            if g_avail == 0:
                zero_g_by_turn[t] += 1

            # Commander castable: Meren {2}{B}{G} = 4 total, 1B, 1G
            cmd_pips = {"generic": 2, "B": 1, "G": 1}
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
        "g_by_turn": g_by_turn,
        "hand_land_counts": hand_land_counts,
        "mulligan_attempts": mulligan_attempts,
        "zero_b_by_turn": zero_b_by_turn,
        "zero_g_by_turn": zero_g_by_turn,
        "commander_castable_turn": commander_castable_turn,
        "commander_by_turn": commander_by_turn,
        "castable_spell_by_turn": castable_spell_by_turn,
        "curve_out_games": curve_out_games,
        "tapped_land_turns": tapped_land_turns,
    }


def print_results(stats: dict, classified: dict, avg_cmc: float, pip_B: int, pip_G: int):
    """Print simulation results."""
    total = NUM_GAMES

    print("\n" + "=" * 65)
    print(f"MONTE CARLO SIMULATION — ETERNAL HARVEST ({NUM_GAMES:,} games, {NUM_TURNS} turns)")
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
    print(f"    Free mulligan used:  {mull.get(1, 0)/total*100:>5.1f}% (redraw 7, no penalty)")
    print(f"    Paid mulligan (->6): {mull.get(2, 0)/total*100:>5.1f}% (redraw 7, bottom 1)")

    print(f"\n  Opening hand (post-mulligan):")
    print(f"    Land count distribution (kept hand):")
    for lands in range(8):
        count = stats["hand_land_counts"].get(lands, 0)
        if count > 0:
            bar = "#" * int(count / total * 50)
            print(f"      {lands} lands: {count/total*100:>5.1f}% {bar}")

    print(f"\n--- Dimension 2: Color Balance ---")
    print(f"\n  B and G available per turn (includes flexible sources):")
    print(f"  {'Turn':<6} {'B med':>7} {'B mean':>7} {'G med':>7} {'G mean':>7}")
    print(f"  {'-'*38}")
    for t in range(1, NUM_TURNS + 1):
        b_med = statistics.median(stats["b_by_turn"][t])
        b_mean = statistics.mean(stats["b_by_turn"][t])
        g_med = statistics.median(stats["g_by_turn"][t])
        g_mean = statistics.mean(stats["g_by_turn"][t])
        print(f"    T{t:<4} {b_med:>7.0f} {b_mean:>7.1f} {g_med:>7.0f} {g_mean:>7.1f}")

    print(f"\n  Color screw (0 sources of a color):")
    for t in range(2, NUM_TURNS + 1):
        b_pct = stats["zero_b_by_turn"][t] / total * 100
        g_pct = stats["zero_g_by_turn"][t] / total * 100
        print(f"    T{t}: 0 B sources = {b_pct:.1f}%, 0 G sources = {g_pct:.1f}%")

    pip_total = pip_B + pip_G
    b_demand = pip_B / pip_total * 100 if pip_total > 0 else 0
    g_demand = pip_G / pip_total * 100 if pip_total > 0 else 0

    t3_b = statistics.mean(stats["b_by_turn"][3])
    t3_g = statistics.mean(stats["g_by_turn"][3])
    t3_total = t3_b + t3_g
    b_supply = t3_b / t3_total * 100 if t3_total > 0 else 0
    g_supply = t3_g / t3_total * 100 if t3_total > 0 else 0

    print(f"\n  Pip demand vs supply ratio (T3 avg):")
    print(f"    Demand: {b_demand:.0f}% B / {g_demand:.0f}% G")
    print(f"    Supply: {b_supply:.0f}% B / {g_supply:.0f}% G")

    print(f"\n--- Dimension 3: Curve Efficiency ---")

    print(f"\n  Commander castable (Meren of Clan Nel Toth, {{2}}{{B}}{{G}}):")
    for t in range(2, NUM_TURNS + 1):
        count = stats["commander_by_turn"][t]
        print(f"    By T{t}: {count/total*100:.1f}%")
    if stats["commander_castable_turn"]:
        med = statistics.median(stats["commander_castable_turn"])
        print(f"    Median turn: {med:.1f}")

    print(f"\n  Castable spell from hand (non-ramp, color-aware):")
    for t in range(1, NUM_TURNS + 1):
        pct = stats["castable_spell_by_turn"][t] / total * 100
        print(f"    T{t}: {pct:.1f}%")

    print(f"\n  Curve-out rate (cast something T1-T4): {stats['curve_out_games']/total*100:.1f}%")

    print(f"\n  ETB tapped frequency:")
    for t in [1, 2]:
        pct = stats["tapped_land_turns"][t] / total * 100
        print(f"    T{t} land entered tapped: {pct:.1f}%")

    print(f"\n--- Mana Base Assessment ---")

    med_t1 = statistics.median(stats["mana_by_turn"][1])
    med_t3 = statistics.median(stats["mana_by_turn"][3])
    med_t5 = statistics.median(stats["mana_by_turn"][5])
    med_last = statistics.median(stats["mana_by_turn"][NUM_TURNS])
    mull = stats["mulligan_attempts"]
    paid_mull_rate = mull.get(2, 0) / total * 100

    print(f"\n  Median mana: T1={med_t1:.0f}, T3={med_t3:.0f}, T5={med_t5:.0f}, T{NUM_TURNS}={med_last:.0f}")

    land_count = len(classified["lands"])
    recommended = round(36 + (avg_cmc - 3.0) * 2)
    if land_count >= recommended:
        print(f"  Land count: {land_count} (adequate for avg CMC {avg_cmc:.2f})")
    else:
        print(f"  Land count: {land_count} (light for avg CMC {avg_cmc:.2f}, heuristic suggests ~{recommended})")

    if paid_mull_rate < 5:
        print(f"  Paid mulligan rate: {paid_mull_rate:.1f}% — acceptable")
    else:
        print(f"  Paid mulligan rate: {paid_mull_rate:.1f}% — consider adding lands/rocks")

    b_deficit = abs(b_demand - b_supply)
    if b_deficit < 10:
        print(f"  Color balance: well-matched (demand/supply within {b_deficit:.0f}%)")
    else:
        if b_supply > b_demand:
            print(f"  Color balance: B-heavy supply ({b_supply:.0f}% vs {b_demand:.0f}% demand) — consider more G sources")
        else:
            print(f"  Color balance: G-heavy supply ({g_supply:.0f}% vs {g_demand:.0f}% demand) — consider more B sources")

    cmd_by_t3 = stats["commander_by_turn"][3] / total * 100
    cmd_by_t4 = stats["commander_by_turn"][4] / total * 100
    if cmd_by_t3 > 50:
        print(f"  Commander by T3: {cmd_by_t3:.0f}% — realistic T3 Meren")
    elif cmd_by_t4 > 50:
        print(f"  Commander by T4: {cmd_by_t4:.0f}% — realistic T4 Meren (T3: {cmd_by_t3:.0f}%)")
    else:
        print(f"  Commander by T4: {cmd_by_t4:.0f}% — below 50%, ramp may be insufficient")

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


def main():
    with open(DECK_FILE) as f:
        deck_data = json.load(f)
    with open(METADATA_FILE) as f:
        metadata = json.load(f)

    print("Building Eternal Harvest decklist...")
    decklist = build_decklist(deck_data)
    print(f"Decklist: {len(decklist)} cards")

    classified = classify_cards(decklist, metadata)

    avg_cmc, pip_B, pip_G = print_static_analysis(decklist, metadata, classified)

    n_workers = os.cpu_count() or 4
    chunk_size = NUM_GAMES // n_workers
    remainder = NUM_GAMES % n_workers
    chunks = [chunk_size + (1 if i < remainder else 0) for i in range(n_workers)]

    print(f"\nRunning {NUM_GAMES:,} game simulations ({n_workers} workers)...")
    with multiprocessing.Pool(n_workers) as pool:
        results = pool.map(_run_chunk, [(decklist, metadata, n) for n in chunks])
    stats = merge_stats(results)

    print_results(stats, classified, avg_cmc, pip_B, pip_G)
    print("\n" + "=" * 65)


if __name__ == "__main__":
    main()
