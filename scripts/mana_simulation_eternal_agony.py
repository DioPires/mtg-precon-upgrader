#!/usr/bin/env python3
"""Monte Carlo mana base simulation for Eternal Agony (The Lord of Pain).

Simulates 100,000 games measuring mana production, color balance, and curve
efficiency turns 1-10 for the Bracket 4 Rakdos decklist.

Commander: The Lord of Pain ({3}{B}{R}, CMC 5)
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
DECK_FILE = PROJECT_ROOT / "data" / "commanders" / "eternal-agony" / "deck.json"
METADATA_FILE = PROJECT_ROOT / "data" / "card-metadata.json"
JSON_OUTPUT = PROJECT_ROOT / "data" / "commanders" / "eternal-agony" / "simulation.json"

NUM_GAMES = 100_000
NUM_TURNS = 10

# --- Mana cost parser ---

def parse_mana_cost(mana_cost: str) -> dict:
    """Parse mana_cost string into pip breakdown.

    "{3}{B}{R}" -> {generic: 3, B: 1, R: 1, total: 5}
    "{B}{B}{B}" -> {generic: 0, B: 3, R: 0, total: 3}
    "{X}{B}{B}" -> {generic: 0, B: 2, R: 0, total: 2, X: True}

    Split cards (//): parse first half only.
    """
    if "//" in mana_cost:
        mana_cost = mana_cost.split("//")[0].strip()

    result = {"generic": 0, "B": 0, "R": 0, "total": 0, "X": False}
    symbols = re.findall(r"\{([^}]+)\}", mana_cost)
    for sym in symbols:
        if sym == "X":
            result["X"] = True
        elif sym.isdigit():
            result["generic"] += int(sym)
        elif sym == "B":
            result["B"] += 1
        elif sym == "R":
            result["R"] += 1
        # Ignore other symbols (hybrid, phyrexian, etc.)
    result["total"] = result["generic"] + result["B"] + result["R"]
    return result


# --- Rock definitions ---

ROCK_DEFS = {
    "Sol Ring":              {"cmc": 1, "B": 0, "R": 0, "C": 2, "burst": False},
    "Arcane Signet":         {"cmc": 2, "B": 1, "R": 1, "C": 0, "burst": False, "flexible": True},
    "Mind Stone":            {"cmc": 2, "B": 0, "R": 0, "C": 1, "burst": False},
    "Rakdos Signet":         {"cmc": 2, "B": 1, "R": 1, "C": 0, "burst": False, "flexible": True},
    "Talisman of Indulgence": {"cmc": 2, "B": 1, "R": 1, "C": 0, "burst": False, "flexible": True},
    "Cursed Mirror":         {"cmc": 3, "B": 0, "R": 1, "C": 0, "burst": False},
}

# --- Land definitions ---

ALWAYS_UNTAPPED_DUALS = {"Blood Crypt", "Command Tower", "Luxury Suite", "Sulfurous Springs", "Blightstep Pathway"}

BASIC_SWAMPS = {"Swamp"}
BASIC_MOUNTAINS = {"Mountain"}

# Lands with Swamp subtype (for Urborg/Coffers counting)
SWAMP_TYPED_LANDS = {"Swamp", "Blood Crypt", "Smoldering Marsh"}
MOUNTAIN_TYPED_LANDS = {"Mountain", "Blood Crypt", "Smoldering Marsh"}

# Lands that produce B
B_PRODUCING_LANDS = {
    "Swamp", "Blood Crypt", "Command Tower", "Luxury Suite", "Sulfurous Springs",
    "Blackcleave Cliffs", "Dragonskull Summit", "Foreboding Ruins", "Smoldering Marsh",
    "Haunted Ridge", "Blightstep Pathway", "Castle Locthwain",
    "Urborg, Tomb of Yawgmoth",
}

# Lands that produce R
R_PRODUCING_LANDS = {
    "Mountain", "Blood Crypt", "Command Tower", "Luxury Suite", "Sulfurous Springs",
    "Blackcleave Cliffs", "Dragonskull Summit", "Foreboding Ruins", "Smoldering Marsh",
    "Haunted Ridge", "Blightstep Pathway", "Mount Doom",
}

# Colorless-only lands
C_ONLY_LANDS = {
    "Ash Barrens", "Graven Cairns", "Phyrexian Tower",
    "Cabal Coffers",
}

# Tainted Peak: C always, B/R only with Swamp in play
# Bloodstained Mire: fetches, handled specially


def build_decklist(deck_data: dict) -> list[str]:
    """Build the 99-card decklist for Eternal Agony.

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

def has_urborg(battlefield_lands: list[str]) -> bool:
    return "Urborg, Tomb of Yawgmoth" in battlefield_lands


def count_swamps(battlefield_lands: list[str]) -> int:
    """Count lands with Swamp subtype on battlefield."""
    if has_urborg(battlefield_lands):
        return len(battlefield_lands)
    count = 0
    for land in battlefield_lands:
        if land in SWAMP_TYPED_LANDS:
            count += 1
    return count


def count_basics(battlefield_lands: list[str]) -> int:
    return sum(1 for l in battlefield_lands if l in BASIC_SWAMPS or l in BASIC_MOUNTAINS)


def land_enters_tapped(name: str, battlefield_lands: list[str], hand: list[str]) -> bool:
    """Determine if a land enters tapped given board + hand state."""
    urborg = has_urborg(battlefield_lands)
    other_count = len(battlefield_lands)  # the new land isn't on board yet
    basics = count_basics(battlefield_lands)

    # Urborg makes all lands Swamps, satisfying "Swamp or Mountain" checks
    has_swamp_or_mountain = urborg or any(
        l in SWAMP_TYPED_LANDS or l in MOUNTAIN_TYPED_LANDS
        for l in battlefield_lands
    )

    if name == "Blackcleave Cliffs":
        return other_count >= 3

    if name == "Dragonskull Summit":
        if urborg:
            return False
        return not has_swamp_or_mountain

    if name == "Foreboding Ruins":
        # Must reveal a card with Swamp or Mountain subtype from hand
        can_reveal = any(
            h in SWAMP_TYPED_LANDS or h in MOUNTAIN_TYPED_LANDS
            for h in hand if h != name
        )
        return not can_reveal

    if name == "Smoldering Marsh":
        return basics < 2

    if name == "Haunted Ridge":
        return other_count < 2

    if name == "Castle Locthwain":
        if urborg:
            return False
        swamp_in_play = any(l in SWAMP_TYPED_LANDS for l in battlefield_lands)
        return not swamp_in_play

    return False  # All other lands enter untapped


class ManaPool:
    """Tracks available B, R, C mana and flexible sources."""
    def __init__(self):
        self.B = 0
        self.R = 0
        self.C = 0
        self.flexible = 0  # can be B or R

    @property
    def total(self):
        return self.B + self.R + self.C + self.flexible

    def can_cast(self, pips: dict) -> bool:
        """Check if we can cast a spell with the given pip requirements."""
        need_B = pips["B"]
        need_R = pips["R"]
        need_generic = pips["generic"]

        avail_B = self.B
        avail_R = self.R
        avail_C = self.C
        avail_flex = self.flexible

        # Assign fixed B sources to B pips
        used_B = min(avail_B, need_B)
        remaining_B = need_B - used_B
        avail_B -= used_B

        # Assign fixed R sources to R pips
        used_R = min(avail_R, need_R)
        remaining_R = need_R - used_R
        avail_R -= used_R

        # Use flexible for remaining colored needs
        remaining_colored = remaining_B + remaining_R
        if avail_flex < remaining_colored:
            return False
        avail_flex -= remaining_colored

        # Remaining generic from leftover B, R, C, flexible
        leftover = avail_B + avail_R + avail_C + avail_flex
        return leftover >= need_generic

    def after_spending(self, pips: dict) -> "ManaPool":
        """Return a new ManaPool after spending pips. Assumes can_cast is True."""
        pool = ManaPool()
        pool.B = self.B
        pool.R = self.R
        pool.C = self.C
        pool.flexible = self.flexible

        need_B = pips["B"]
        need_R = pips["R"]
        need_generic = pips["generic"]

        # Spend fixed B
        from_B = min(pool.B, need_B)
        pool.B -= from_B
        need_B -= from_B

        # Spend fixed R
        from_R = min(pool.R, need_R)
        pool.R -= from_R
        need_R -= from_R

        # Spend flexible on remaining colored
        flex_colored = need_B + need_R
        pool.flexible -= flex_colored

        # Spend generic: C first, then leftover B/R, then flexible
        remaining = need_generic
        from_C = min(pool.C, remaining)
        pool.C -= from_C
        remaining -= from_C

        from_B2 = min(pool.B, remaining)
        pool.B -= from_B2
        remaining -= from_B2

        from_R2 = min(pool.R, remaining)
        pool.R -= from_R2
        remaining -= from_R2

        from_flex = min(pool.flexible, remaining)
        pool.flexible -= from_flex

        return pool


def compute_land_mana(name: str, battlefield_lands: list[str], has_crypt_ghast: bool) -> tuple[int, int, int, int]:
    """Return (B, R, C, flexible) mana a single untapped land produces.

    flexible = can produce B or R (dual lands, Command Tower, etc.)
    """
    urborg = has_urborg(battlefield_lands)

    # Special cases first
    if name == "Cabal Coffers":
        swamps = count_swamps(battlefield_lands)
        net = max(0, swamps - 2)
        if has_crypt_ghast:
            net *= 2  # Crypt Ghast doubles each Swamp's B production, but Coffers isn't a Swamp...
            # Actually: Crypt Ghast triggers per Swamp, Coffers adds B per Swamp.
            # Coffers itself is not a Swamp (unless Urborg). Model: Coffers produces net B.
            # If Urborg active, Coffers IS a Swamp, so Crypt Ghast would add extra B.
            # Simplification: Coffers produces net B = swamps - 2.
            # Crypt Ghast adds 1 extra B per Swamp tapped for mana, not per Coffers activation.
            # Don't double Coffers output. Reset.
            net = max(0, swamps - 2)
        return (net, 0, 0, 0)

    if name == "Graven Cairns":
        # Default: {C}. Filter mode requires B/R input from elsewhere.
        # Model as C-only for simplicity (conservative).
        return (0, 0, 1, 0)

    if name == "Phyrexian Tower":
        # {C} only (sac mode excluded)
        return (0, 0, 1, 0)

    if name == "Urborg, Tomb of Yawgmoth":
        # Produces {B}
        b = 1
        if has_crypt_ghast:
            b += 1
        return (b, 0, 0, 0)

    if name == "Tainted Peak":
        # Always untapped. {C} always; {B} or {R} only if Swamp in play.
        swamp_in_play = any(l in SWAMP_TYPED_LANDS for l in battlefield_lands) or urborg
        if swamp_in_play:
            return (0, 0, 0, 1)  # flexible B/R
        return (0, 0, 1, 0)

    if name == "Bloodstained Mire":
        # Should already be cracked; if somehow on board, treat as 0
        return (0, 0, 0, 0)

    if name == "Ash Barrens":
        return (0, 0, 1, 0)

    if name == "Castle Locthwain":
        # Produces {B}. With Urborg, Castle is a Swamp -> Crypt Ghast adds extra {B}.
        b = 1
        if urborg and has_crypt_ghast:
            b += 1
        return (b, 0, 0, 0)

    # Dual lands (produce B or R -> flexible)
    if name in ALWAYS_UNTAPPED_DUALS or name in {
        "Blackcleave Cliffs", "Dragonskull Summit", "Foreboding Ruins",
        "Smoldering Marsh", "Haunted Ridge",
    }:
        f = 1
        if urborg and has_crypt_ghast:
            f += 1  # Urborg makes it a Swamp -> Crypt Ghast bonus
        return (0, 0, 0, f)

    # Basic Swamp
    if name == "Swamp":
        b = 1
        if has_crypt_ghast:
            b += 1
        return (b, 0, 0, 0)

    # Basic Mountain
    if name == "Mountain":
        r = 1
        if urborg and has_crypt_ghast:
            # Urborg makes Mountain a Swamp -> Crypt Ghast adds B
            return (1, r, 0, 0)  # 1B from Crypt Ghast + 1R from Mountain
        return (0, r, 0, 0)

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
        self.has_crypt_ghast = False
        self.metadata = metadata
        self.land_set = land_set
        self.mana_per_turn: list[ManaPool] = []
        self.mulligan_attempt = 0  # 0=kept, 1=free, 2=paid

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

        if name == "Bloodstained Mire":
            return 20  # Fetch: always play and crack immediately

        if tapped:
            base = 0
        else:
            base = 10

        # Duals (flexible color) get bonus
        if name in ALWAYS_UNTAPPED_DUALS:
            base += 5
        elif name in B_PRODUCING_LANDS and name in R_PRODUCING_LANDS:
            base += 4
        elif name == "Urborg, Tomb of Yawgmoth":
            base += 6  # Fixes all lands to Swamps
        elif name == "Tainted Peak":
            # Flexible if Swamp in play
            if any(l in SWAMP_TYPED_LANDS for l in self.battlefield_lands) or has_urborg(self.battlefield_lands):
                base += 4
            else:
                base += 1

        return base

    def _resolve_fetch(self, fetch_name: str):
        """Resolve Bloodstained Mire: search library for Swamp or Mountain card."""
        # Determine color need
        b_sources = sum(1 for l in self.battlefield_lands
                       if l in B_PRODUCING_LANDS or l in SWAMP_TYPED_LANDS)
        r_sources = sum(1 for l in self.battlefield_lands
                       if l in R_PRODUCING_LANDS or l in MOUNTAIN_TYPED_LANDS)

        # Fetchable targets in library
        fetchable = []
        for i, card in enumerate(self.library):
            if card in SWAMP_TYPED_LANDS or card in MOUNTAIN_TYPED_LANDS or card in BASIC_SWAMPS or card in BASIC_MOUNTAINS:
                fetchable.append((i, card))

        if not fetchable:
            return  # Nothing to fetch

        # Prefer Blood Crypt early (both colors), then basic matching color need
        blood_crypt = [(i, c) for i, c in fetchable if c == "Blood Crypt"]
        if blood_crypt and len(self.battlefield_lands) <= 2:
            idx, card = blood_crypt[0]
            self.library.pop(idx)
            self.battlefield_lands.append(card)
            return

        # Fetch basic matching color deficit
        if b_sources <= r_sources:
            # Need B: fetch Swamp
            swamps = [(i, c) for i, c in fetchable if c == "Swamp"]
            if swamps:
                idx, card = swamps[0]
                self.library.pop(idx)
                self.battlefield_lands.append(card)
                return
        else:
            # Need R: fetch Mountain
            mountains = [(i, c) for i, c in fetchable if c == "Mountain"]
            if mountains:
                idx, card = mountains[0]
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
            b, r, c, f = compute_land_mana(land, self.battlefield_lands, self.has_crypt_ghast)
            pool.B += b
            pool.R += r
            pool.C += c
            pool.flexible += f

        for rock in self.battlefield_rocks:
            rdef = ROCK_DEFS[rock]
            if rdef["burst"]:
                if self.burst_rocks_active.get(rock, False):
                    pool.C += rdef["C"]
                # Burst rocks don't produce on subsequent turns
            else:
                pool.B += rdef.get("B", 0) if not rdef.get("flexible") else 0
                pool.R += rdef.get("R", 0) if not rdef.get("flexible") else 0
                pool.C += rdef.get("C", 0)
                if rdef.get("flexible"):
                    pool.flexible += 1  # Arcane Signet / Talisman produce 1 colored

        return pool

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

            if land_name == "Bloodstained Mire":
                # Crack immediately
                self._resolve_fetch(land_name)
            else:
                tapped = land_enters_tapped(land_name, self.battlefield_lands, self.hand)
                self.battlefield_lands.append(land_name)
                if tapped:
                    self.tapped_lands.add(len(self.battlefield_lands) - 1)

        # Calculate mana, try to cast rocks/Crypt Ghast
        pool = self.compute_mana_pool()
        self._try_cast_rocks(pool)

        # Record final mana pool
        self.mana_per_turn.append(self.compute_mana_pool())

    def _try_cast_rocks(self, pool: ManaPool):
        """Try to cast mana rocks and Crypt Ghast from hand, priority order."""
        # Priority: Sol Ring > 2-CMC rocks > Cursed Mirror > Crypt Ghast
        priority_order = ["Sol Ring", "Arcane Signet", "Rakdos Signet", "Talisman of Indulgence", "Mind Stone", "Cursed Mirror"]

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
                        pool.B += rdef.get("B", 0)
                        pool.R += rdef.get("R", 0)

        # Try Crypt Ghast (4 CMC, {3}{B})
        if "Crypt Ghast" in self.hand:
            pips = {"generic": 3, "B": 1, "R": 0}
            if pool.can_cast(pips):
                pool = pool.after_spending(pips)
                self.hand.remove("Crypt Ghast")
                self.has_crypt_ghast = True


def commander_mulligan(decklist: list[str], metadata: dict, land_set: set[str]) -> GameState:
    """Commander mulligan: free first mulligan, then London mulligan.

    attempt 0 = kept first hand (7 cards)
    attempt 1 = free mulligan (7 cards, no penalty)
    attempt 2 = paid mulligan (bottom 1 → 6 cards)
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
        if card in ROCK_DEFS or card in state.land_set or card == "Crypt Ghast":
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
    print("STATIC ANALYSIS — ETERNAL AGONY (BRACKET 4)")
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
    total_B = 0
    total_R = 0
    for name in decklist:
        meta = metadata.get(name, {})
        mc = meta.get("mana_cost", "")
        if "Land" in meta.get("type_line", ""):
            continue
        pips = parse_mana_cost(mc)
        total_B += pips["B"]
        total_R += pips["R"]

    total_pips = total_B + total_R
    b_ratio = total_B / total_pips * 100 if total_pips > 0 else 0
    r_ratio = total_R / total_pips * 100 if total_pips > 0 else 0

    print(f"\n--- Pip Demand ---")
    print(f"  Total {{B}} pips: {total_B}")
    print(f"  Total {{R}} pips: {total_R}")
    print(f"  Ratio: {b_ratio:.0f}% B / {r_ratio:.0f}% R")

    # Mana source inventory
    lands = classified["lands"]
    b_sources = sum(1 for l in lands if l in B_PRODUCING_LANDS)
    r_sources = sum(1 for l in lands if l in R_PRODUCING_LANDS)
    both_sources = sum(1 for l in lands if l in B_PRODUCING_LANDS and l in R_PRODUCING_LANDS)
    c_only = sum(1 for l in lands if l in C_ONLY_LANDS)
    # Tainted Peak, Bloodstained Mire are special
    special = sum(1 for l in lands if l in {"Tainted Peak", "Bloodstained Mire"})

    print(f"\n--- Mana Source Inventory ---")
    print(f"  B-producing lands: {b_sources}")
    print(f"  R-producing lands: {r_sources}")
    print(f"  Dual (B+R) lands: {both_sources}")
    print(f"  C-only lands: {c_only}")
    print(f"  Conditional/fetch: {special} (Tainted Peak, Bloodstained Mire)")

    rock_b = sum(1 for r in classified["rocks"] if ROCK_DEFS[r].get("flexible"))
    rock_c = sum(1 for r in classified["rocks"] if not ROCK_DEFS[r].get("flexible"))
    print(f"  Flexible rocks (B/R): {rock_b}")
    print(f"  Colorless rocks: {rock_c}")

    # Recommended land count heuristic
    # Frank Karsten heuristic for Commander: ~38 lands for avg CMC 3.0, -1 per 0.2 below
    # Adjusted: 36 + (avg_cmc - 3.0) * 2
    recommended = round(36 + (avg_cmc - 3.0) * 2)
    print(f"\n--- Land Count Heuristic ---")
    print(f"  Avg CMC: {avg_cmc:.2f}")
    print(f"  Current lands: {len(lands)}")
    print(f"  Heuristic recommendation: ~{recommended} lands")
    if len(lands) >= recommended:
        print(f"  Status: adequate ({len(lands)} >= {recommended})")
    else:
        print(f"  Status: light ({len(lands)} < {recommended}, delta = {recommended - len(lands)})")

    return avg_cmc, total_B, total_R


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
    b_by_turn = {t: [] for t in range(1, NUM_TURNS + 1)}
    r_by_turn = {t: [] for t in range(1, NUM_TURNS + 1)}
    hand_land_counts = Counter()
    mulligan_attempts = Counter()

    # Color screw tracking
    zero_b_by_turn = {t: 0 for t in range(1, NUM_TURNS + 1)}
    zero_r_by_turn = {t: 0 for t in range(1, NUM_TURNS + 1)}

    # Commander timing
    commander_castable_turn = []
    commander_by_turn = {t: 0 for t in range(1, NUM_TURNS + 1)}

    # Curve efficiency
    castable_spell_by_turn = {t: 0 for t in range(1, NUM_TURNS + 1)}
    curve_out_games = 0

    # ETB tapped tracking
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
            b_avail = pool.B + pool.flexible  # flexible can be B
            r_avail = pool.R + pool.flexible  # flexible can be R

            mana_by_turn[t].append(total)
            b_by_turn[t].append(b_avail)
            r_by_turn[t].append(r_avail)

            if b_avail == 0:
                zero_b_by_turn[t] += 1
            if r_avail == 0:
                zero_r_by_turn[t] += 1

            # Commander castable: 5+ total AND 1+ B AND 1+ R
            cmd_pips = {"generic": 3, "B": 1, "R": 1}
            if cmd_cast_turn is None and pool.can_cast(cmd_pips):
                cmd_cast_turn = t
                commander_by_turn[t] += 1

            # Castable spell check
            castable = can_cast_from_hand(state, pool)
            if castable:
                castable_spell_by_turn[t] += 1
            elif t <= 4:
                cast_every_turn = False

            # ETB tapped tracking (approximate: if a new land was added and it was tapped)
            if t <= 2 and lands_after > lands_before:
                new_idx = lands_after - 1
                if new_idx in state.tapped_lands:
                    tapped_land_turns[t] += 1

        if cmd_cast_turn is not None:
            commander_castable_turn.append(cmd_cast_turn)
            # Also count for turns after first castable
            for future_t in range(cmd_cast_turn + 1, NUM_TURNS + 1):
                commander_by_turn[future_t] += 1

        if cast_every_turn:
            curve_out_games += 1

    return {
        "mana_by_turn": mana_by_turn,
        "b_by_turn": b_by_turn,
        "r_by_turn": r_by_turn,
        "hand_land_counts": hand_land_counts,
        "mulligan_attempts": mulligan_attempts,
        "zero_b_by_turn": zero_b_by_turn,
        "zero_r_by_turn": zero_r_by_turn,
        "commander_castable_turn": commander_castable_turn,
        "commander_by_turn": commander_by_turn,
        "castable_spell_by_turn": castable_spell_by_turn,
        "curve_out_games": curve_out_games,
        "tapped_land_turns": tapped_land_turns,
    }


def print_results(stats: dict, classified: dict, avg_cmc: float, pip_B: int, pip_R: int):
    """Print simulation results."""
    total = NUM_GAMES

    print("\n" + "=" * 65)
    print(f"MONTE CARLO SIMULATION — ETERNAL AGONY ({NUM_GAMES:,} games, {NUM_TURNS} turns)")
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
    print(f"    Paid mulligan (→6):  {mull.get(2, 0)/total*100:>5.1f}% (redraw 7, bottom 1)")

    print(f"\n  Opening hand (post-mulligan):")
    print(f"    Land count distribution (kept hand):")
    for lands in range(8):
        count = stats["hand_land_counts"].get(lands, 0)
        if count > 0:
            bar = "#" * int(count / total * 50)
            print(f"      {lands} lands: {count/total*100:>5.1f}% {bar}")

    # Dimension 2: Color Balance
    print(f"\n--- Dimension 2: Color Balance ---")
    print(f"\n  B and R available per turn (includes flexible sources):")
    print(f"  {'Turn':<6} {'B med':>7} {'B mean':>7} {'R med':>7} {'R mean':>7}")
    print(f"  {'-'*38}")
    for t in range(1, NUM_TURNS + 1):
        b_med = statistics.median(stats["b_by_turn"][t])
        b_mean = statistics.mean(stats["b_by_turn"][t])
        r_med = statistics.median(stats["r_by_turn"][t])
        r_mean = statistics.mean(stats["r_by_turn"][t])
        print(f"    T{t:<4} {b_med:>7.0f} {b_mean:>7.1f} {r_med:>7.0f} {r_mean:>7.1f}")

    print(f"\n  Color screw (0 sources of a color):")
    for t in range(2, NUM_TURNS + 1):
        b_pct = stats["zero_b_by_turn"][t] / total * 100
        r_pct = stats["zero_r_by_turn"][t] / total * 100
        print(f"    T{t}: 0 B sources = {b_pct:.1f}%, 0 R sources = {r_pct:.1f}%")

    pip_total = pip_B + pip_R
    b_demand = pip_B / pip_total * 100 if pip_total > 0 else 0
    r_demand = pip_R / pip_total * 100 if pip_total > 0 else 0

    t3_b = statistics.mean(stats["b_by_turn"][3])
    t3_r = statistics.mean(stats["r_by_turn"][3])
    t3_total = t3_b + t3_r
    b_supply = t3_b / t3_total * 100 if t3_total > 0 else 0
    r_supply = t3_r / t3_total * 100 if t3_total > 0 else 0

    print(f"\n  Pip demand vs supply ratio (T3 avg):")
    print(f"    Demand: {b_demand:.0f}% B / {r_demand:.0f}% R")
    print(f"    Supply: {b_supply:.0f}% B / {r_supply:.0f}% R")

    # Dimension 3: Curve Efficiency
    print(f"\n--- Dimension 3: Curve Efficiency ---")

    print(f"\n  Commander castable (The Lord of Pain, {{3}}{{B}}{{R}}):")
    for t in range(3, NUM_TURNS + 1):
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

    # Paid mulligan rate (games actually starting with <7 cards)
    if paid_mull_rate < 5:
        print(f"  Paid mulligan rate: {paid_mull_rate:.1f}% — acceptable")
    else:
        print(f"  Paid mulligan rate: {paid_mull_rate:.1f}% — consider adding lands/rocks")

    # Color ratio
    b_deficit = abs(b_demand - b_supply)
    if b_deficit < 10:
        print(f"  Color balance: well-matched (demand/supply within {b_deficit:.0f}%)")
    else:
        if b_supply > b_demand:
            print(f"  Color balance: B-heavy supply ({b_supply:.0f}% vs {b_demand:.0f}% demand) — consider more R sources")
        else:
            print(f"  Color balance: R-heavy supply ({r_supply:.0f}% vs {r_demand:.0f}% demand) — consider more B sources")

    # Commander timing
    cmd_by_t4 = stats["commander_by_turn"][4] / total * 100
    if cmd_by_t4 > 50:
        print(f"  Commander by T4: {cmd_by_t4:.0f}% — realistic T4 Lord of Pain")
    else:
        print(f"  Commander by T4: {cmd_by_t4:.0f}% — below 50%, ramp may be insufficient")

    # ETB tapped
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


def export_enhanced_json(metadata: dict) -> dict:
    """Reuse bulk exporter path so standalone JSON stays schema-compatible."""
    import export_simulation_results as exporter

    result = exporter.export_rakdos(metadata)
    if not exporter.validate_output(result, "eternal-agony"):
        raise ValueError("export_rakdos produced invalid simulation output")
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Monte Carlo mana base simulation for Eternal Agony (The Lord of Pain)")
    parser.add_argument("--json", action="store_true",
                        help="Write simulation.json instead of console output")
    args = parser.parse_args()

    with open(DECK_FILE) as f:
        deck_data = json.load(f)
    with open(METADATA_FILE) as f:
        metadata = json.load(f)

    print("Building Eternal Agony decklist...")
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

    avg_cmc, pip_B, pip_R = print_static_analysis(decklist, metadata, classified)

    n_workers = os.cpu_count() or 4
    chunk_size = NUM_GAMES // n_workers
    remainder = NUM_GAMES % n_workers
    chunks = [chunk_size + (1 if i < remainder else 0) for i in range(n_workers)]

    print(f"\nRunning {NUM_GAMES:,} game simulations ({n_workers} workers)...")
    with multiprocessing.Pool(n_workers) as pool:
        results = pool.map(_run_chunk, [(decklist, metadata, n) for n in chunks])
    stats = merge_stats(results)

    print_results(stats, classified, avg_cmc, pip_B, pip_R)
    print("\n" + "=" * 65)


if __name__ == "__main__":
    main()
