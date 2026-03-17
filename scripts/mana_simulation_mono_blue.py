#!/usr/bin/env python3
"""Monte Carlo mana base simulation for Azure Dominion (Urza, Lord High Artificer).

Simulates 100,000 games measuring mana production, color balance, and curve
efficiency turns 1-10 for the Bracket 4 mono-blue artifact stax/combo decklist.

Commander: Urza, Lord High Artificer ({2}{U}{U}, CMC 4)

Key mechanic modeled: Urza lets you tap any artifact for {U}. This turns
non-mana artifacts (stax pieces, baubles) into mana sources and gives burst
rocks (Mana Vault, Basalt Monolith) utility on non-burst turns.
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
DECK_FILE = PROJECT_ROOT / "data" / "commanders" / "azure-dominion" / "deck.json"
METADATA_FILE = PROJECT_ROOT / "data" / "card-metadata.json"
JSON_OUTPUT = PROJECT_ROOT / "data" / "commanders" / "azure-dominion" / "simulation.json"

NUM_GAMES = 100_000
NUM_TURNS = 10

# --- Mana cost parser ---


def parse_mana_cost(mana_cost: str) -> dict:
    """Parse mana_cost string into pip breakdown.

    "{2}{U}{U}" -> {generic: 2, U: 3, total: 5}
    "{U}{U}" -> {generic: 0, U: 2, total: 2}

    Split cards (//): parse first half only.
    """
    if "//" in mana_cost:
        mana_cost = mana_cost.split("//")[0].strip()

    result = {"generic": 0, "U": 0, "total": 0, "X": False}
    symbols = re.findall(r"\{([^}]+)\}", mana_cost)
    for sym in symbols:
        if sym == "X":
            result["X"] = True
        elif sym.isdigit():
            result["generic"] += int(sym)
        elif sym == "U":
            result["U"] += 1
        # Ignore other symbols (hybrid, phyrexian, etc.)
    result["total"] = result["generic"] + result["U"]
    return result


# --- Rock definitions ---

ROCK_DEFS = {
    "Sol Ring":           {"cmc": 1, "C": 2, "burst": False},
    "Arcane Signet":      {"cmc": 2, "U": 1, "burst": False},
    "Mana Vault":         {"cmc": 1, "C": 3, "burst": True},
    "Basalt Monolith":    {"cmc": 3, "C": 3, "burst": True},
}

# Chrome Mox and Everflowing Chalice have special deploy logic
CHROME_MOX = "Chrome Mox"
EVERFLOWING_CHALICE = "Everflowing Chalice"
SPECIAL_ROCKS = {CHROME_MOX, EVERFLOWING_CHALICE}

# --- Amplifier definitions ---

AMPLIFIER_DEFS = {
    "Extraplanar Lens": {"cmc": 3},
}

# --- Utility artifact definitions (non-mana artifacts tracked for Urza) ---
# CMC used for deployment priority. Only mana-relevant as Urza tap targets.

UTILITY_ARTIFACTS = {
    # CMC 0
    "Mishra's Bauble":      0,
    "Urza's Bauble":        0,
    "Tormod's Crypt":       0,
    "Welding Jar":          0,
    # CMC 1
    "Grafdigger's Cage":    1,
    "Pithing Needle":       1,
    "Codex Shredder":       1,
    "Sensei's Divining Top": 1,
    "Jeweled Amulet":       1,
    # CMC 2
    "Isochron Scepter":     2,
    "Lightning Greaves":    2,
    "Rings of Brighthearth": 3,
    "Winter Orb":           2,
    # CMC 3
    "Static Orb":           3,
    "Trinisphere":          3,
    "Tangle Wire":          3,
    "Proteus Staff":        3,
    # CMC 4+
    "Mystic Forge":         4,
    "Unwinding Clock":      4,
    "Aetherflux Reservoir":  4,
    "Simulacrum Synthesizer": 3,
}

# --- Land definitions ---

FETCH_LANDS = {"Flooded Strand", "Misty Rainforest", "Polluted Delta", "Prismatic Vista"}

# Lands with Island subtype (for Mystic Sanctuary check)
ISLAND_TYPED_LANDS = {"Snow-Covered Island", "Mystic Sanctuary", "Seat of the Synod"}

ARTIFACT_LANDS = {"Seat of the Synod", "Darksteel Citadel"}

# Always enters tapped (none in this list for mono-blue Urza)
ALWAYS_TAPPED = set()


def land_enters_tapped(name: str, battlefield_lands: list[str]) -> bool:
    """Determine if a land enters tapped given board state."""
    if name in ALWAYS_TAPPED:
        return True

    # Mystic Sanctuary: enters tapped unless you control 3+ other Islands
    if name == "Mystic Sanctuary":
        island_count = sum(1 for l in battlefield_lands if l in ISLAND_TYPED_LANDS)
        return island_count < 3

    return False


# --- Mana pool ---


class ManaPool:
    """Tracks available U and C mana.

    Simplified 2-bucket pool for mono-blue:
    - U: blue mana sources
    - C: colorless-only mana sources
    """

    def __init__(self):
        self.U = 0
        self.C = 0

    @property
    def total(self):
        return self.U + self.C

    def can_cast(self, pips: dict) -> bool:
        """Check if we can cast a spell with the given pip requirements."""
        need_U = pips.get("U", 0)
        need_generic = pips.get("generic", 0)
        if self.U < need_U:
            return False
        remaining_U = self.U - need_U
        return (remaining_U + self.C) >= need_generic

    def after_spending(self, pips: dict) -> "ManaPool":
        """Return a new ManaPool after spending pips. Assumes can_cast is True."""
        need_U = pips.get("U", 0)
        need_generic = pips.get("generic", 0)

        pool = ManaPool()
        pool.U = self.U - need_U
        pool.C = self.C

        # Spend generic from C first, then U
        from_C = min(pool.C, need_generic)
        pool.C -= from_C
        need_generic -= from_C
        pool.U -= need_generic

        return pool


def compute_land_mana(name: str, has_lens: bool) -> tuple[int, int]:
    """Return (U, C) mana production for an untapped land."""

    if name == "Snow-Covered Island":
        return (2, 0) if has_lens else (1, 0)

    if name == "Seat of the Synod":
        return (1, 0)

    if name == "Darksteel Citadel":
        return (0, 1)

    if name == "Mystic Sanctuary":
        return (1, 0)

    if name == "Otawara, Soaring City":
        return (1, 0)

    if name == "Ancient Tomb":
        return (0, 2)

    if name == "Urza's Saga":
        return (0, 1)

    if name in {"Academy Ruins", "Reliquary Tower", "Inventors' Fair"}:
        return (0, 1)

    # Fetches should be cracked before mana calculation
    if name in FETCH_LANDS:
        return (0, 0)

    # Fallback: colorless
    return (0, 1)


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

    Rocks include standard mana rocks and special rocks.
    Utility artifacts and amplifiers are classified as spells.
    """
    ramp_names = set(ROCK_DEFS) | SPECIAL_ROCKS
    classified = {"lands": [], "rocks": [], "spells": []}
    for name in decklist:
        if name in ramp_names:
            classified["rocks"].append(name)
        elif name in AMPLIFIER_DEFS:
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
    """Mulligan if 0-1 mana sources (lands + rocks)."""
    ramp_names = set(ROCK_DEFS) | SPECIAL_ROCKS
    sources = sum(1 for c in hand if c in land_set or c in ramp_names)
    return sources <= 1


def choose_bottom_cards(hand: list[str], count: int, metadata: dict,
                        land_set: set[str]) -> list[str]:
    """Choose cards to bottom (London mulligan). Bottom highest CMC non-source cards."""
    ramp_names = set(ROCK_DEFS) | SPECIAL_ROCKS
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
        self.battlefield_utility_artifacts: list[str] = []
        self.metadata = metadata
        self.land_set = land_set
        self.mana_per_turn: list[ManaPool] = []
        self.mulligan_attempt = 0

        # Urza-specific state
        self.urza_on_board = False
        self.has_lens = False
        self.chalice_counters = 0  # Everflowing Chalice charge counters
        self.has_chalice = False
        self.has_chrome_mox = False  # Chrome Mox on battlefield
        self.burst_rocks_active: dict[str, bool] = {}  # name -> cast this turn
        self.saga_play_turns: dict[int, int] = {}  # land index -> turn played

    def draw(self, n: int = 1):
        for _ in range(n):
            if self.library:
                self.hand.append(self.library.pop())

    def count_lands_in_hand(self) -> int:
        return sum(1 for c in self.hand if c in self.land_set)

    def _is_land(self, name: str) -> bool:
        return name in self.land_set

    def _land_play_priority(self, name: str) -> float:
        """Higher = play first. Fetches > untapped blue > utility lands."""
        if name in FETCH_LANDS:
            return 20

        tapped = land_enters_tapped(name, self.battlefield_lands)
        base = 0 if tapped else 10

        # Blue-producing lands get highest bonus
        if name == "Snow-Covered Island":
            base += 5
        elif name == "Seat of the Synod":
            base += 5
        elif name == "Otawara, Soaring City":
            base += 4
        elif name == "Mystic Sanctuary":
            base += 3
        elif name == "Ancient Tomb":
            base += 6  # 2 mana is very valuable early
        elif name == "Urza's Saga":
            base += 4

        return base

    def _resolve_fetch(self):
        """All fetches in this deck find Snow-Covered Island."""
        targets = [i for i, c in enumerate(self.library) if c == "Snow-Covered Island"]
        if targets:
            idx = targets[0]
            self.library.pop(idx)
            self.battlefield_lands.append("Snow-Covered Island")

    def compute_mana_pool(self) -> ManaPool:
        """Calculate total available mana from untapped lands + rocks + Urza bonus."""
        pool = ManaPool()

        # Lands
        for i, land in enumerate(self.battlefield_lands):
            if i in self.tapped_lands:
                continue
            u, c = compute_land_mana(land, self.has_lens)
            pool.U += u
            pool.C += c

        # Standard rocks (non-burst produce mana; burst only on active turn)
        for rock in self.battlefield_rocks:
            rdef = ROCK_DEFS.get(rock)
            if rdef:
                if rdef["burst"]:
                    if self.burst_rocks_active.get(rock, False):
                        pool.C += rdef["C"]
                    elif self.urza_on_board:
                        # Burst rock idle: tap for U via Urza
                        pool.U += 1
                else:
                    pool.U += rdef.get("U", 0)
                    pool.C += rdef.get("C", 0)

        # Chrome Mox
        if self.has_chrome_mox:
            pool.U += 1

        # Everflowing Chalice
        if self.has_chalice and self.chalice_counters > 0:
            pool.C += self.chalice_counters
        elif self.has_chalice and self.chalice_counters == 0 and self.urza_on_board:
            # 0-counter Chalice taps for U via Urza
            pool.U += 1

        # Urza bonus: each utility artifact on battlefield taps for {U}
        if self.urza_on_board:
            pool.U += len(self.battlefield_utility_artifacts)

        return pool

    def play_turn(self, turn_number: int):
        """Simulate one turn."""
        if turn_number > 1:
            self.draw(1)

        # Untap all
        self.tapped_lands.clear()

        # Mark burst rocks as no longer active
        for name in list(self.burst_rocks_active.keys()):
            self.burst_rocks_active[name] = False

        # Saga self-destruct check (remove if 2 turns have passed)
        expired_indices = []
        for idx, play_turn in list(self.saga_play_turns.items()):
            if turn_number - play_turn >= 2:
                expired_indices.append(idx)
        # Remove expired sagas (highest index first to preserve indices)
        for idx in sorted(expired_indices, reverse=True):
            if idx < len(self.battlefield_lands) and self.battlefield_lands[idx] == "Urza's Saga":
                self.battlefield_lands.pop(idx)
                # Adjust tapped_lands indices
                new_tapped = set()
                for ti in self.tapped_lands:
                    if ti > idx:
                        new_tapped.add(ti - 1)
                    elif ti < idx:
                        new_tapped.add(ti)
                self.tapped_lands = new_tapped
                # Adjust saga_play_turns indices
                new_saga = {}
                for si, st in self.saga_play_turns.items():
                    if si == idx:
                        continue
                    new_si = si - 1 if si > idx else si
                    new_saga[new_si] = st
                self.saga_play_turns = new_saga

        # Play best land from hand
        hand_lands = [(self._land_play_priority(c), c) for c in self.hand if self._is_land(c)]
        hand_lands.sort(reverse=True)

        if hand_lands:
            _, land_name = hand_lands[0]
            self.hand.remove(land_name)

            if land_name in FETCH_LANDS:
                self._resolve_fetch()
            else:
                tapped = land_enters_tapped(land_name, self.battlefield_lands)
                self.battlefield_lands.append(land_name)
                if tapped:
                    self.tapped_lands.add(len(self.battlefield_lands) - 1)
                # Track Saga play turn
                if land_name == "Urza's Saga":
                    self.saga_play_turns[len(self.battlefield_lands) - 1] = turn_number

        # Cast ramp from hand
        pool = self.compute_mana_pool()
        self._try_cast_ramp(pool)

        # Record final mana pool
        self.mana_per_turn.append(self.compute_mana_pool())

    def _try_cast_ramp(self, pool: ManaPool):
        """Try to cast mana rocks, special rocks, amplifiers, and utility artifacts."""

        # Phase 1: Deploy mana rocks in priority order
        rock_priority = [
            "Sol Ring",         # CMC 1, +2C
            "Mana Vault",      # CMC 1, +3C (burst)
        ]

        # Chrome Mox: free if we have a blue non-land non-rock card to imprint
        if CHROME_MOX in self.hand:
            imprint_candidates = [c for c in self.hand
                                  if c != CHROME_MOX
                                  and c not in self.land_set
                                  and c not in ROCK_DEFS
                                  and c not in SPECIAL_ROCKS
                                  and c not in AMPLIFIER_DEFS]
            if imprint_candidates:
                # Imprint highest CMC card (least useful to cast)
                imprint_candidates.sort(
                    key=lambda c: self.metadata.get(c, {}).get("cmc", 0), reverse=True)
                self.hand.remove(CHROME_MOX)
                self.hand.remove(imprint_candidates[0])
                self.has_chrome_mox = True
                pool.U += 1  # Immediately available

        for name in rock_priority:
            if name not in self.hand:
                continue
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
                    pool.U += rdef.get("U", 0)
                    pool.C += rdef.get("C", 0)

        # Arcane Signet (CMC 2)
        if "Arcane Signet" in self.hand:
            pips = {"generic": 1, "U": 0}
            if pool.can_cast(pips):
                pool = pool.after_spending(pips)
                self.hand.remove("Arcane Signet")
                self.battlefield_rocks.append("Arcane Signet")
                pool.U += 1

        # Everflowing Chalice: cast for max affordable multikicker
        if EVERFLOWING_CHALICE in self.hand and not self.has_chalice:
            # Each {2} spent adds a counter. Minimum: cast for 0 (0 counters).
            max_spend = pool.total
            counters = max_spend // 2
            if counters >= 1:
                # Cast for 2*counters generic mana
                cast_pips = {"generic": counters * 2, "U": 0}
                if pool.can_cast(cast_pips):
                    pool = pool.after_spending(cast_pips)
                    self.hand.remove(EVERFLOWING_CHALICE)
                    self.has_chalice = True
                    self.chalice_counters = counters
                    pool.C += counters
            else:
                # Cast for 0 — 0 counters, no mana production
                # Still worth deploying if Urza is/will be on board
                self.hand.remove(EVERFLOWING_CHALICE)
                self.has_chalice = True
                self.chalice_counters = 0

        # Basalt Monolith (CMC 3)
        if "Basalt Monolith" in self.hand:
            pips = {"generic": 3, "U": 0}
            if pool.can_cast(pips):
                pool = pool.after_spending(pips)
                self.hand.remove("Basalt Monolith")
                self.battlefield_rocks.append("Basalt Monolith")
                self.burst_rocks_active["Basalt Monolith"] = True
                pool.C += 3

        # Phase 2: Deploy Extraplanar Lens (CMC 3, exile Snow-Covered Island)
        if "Extraplanar Lens" in self.hand and not self.has_lens:
            pips = {"generic": 3, "U": 0}
            if pool.can_cast(pips):
                # Need a Snow-Covered Island on battlefield to exile
                if "Snow-Covered Island" in self.battlefield_lands:
                    pool = pool.after_spending(pips)
                    self.hand.remove("Extraplanar Lens")
                    self.has_lens = True
                    # Exile one Snow-Covered Island
                    idx = self.battlefield_lands.index("Snow-Covered Island")
                    self.battlefield_lands.pop(idx)
                    # Adjust tapped_lands indices
                    new_tapped = set()
                    for ti in self.tapped_lands:
                        if ti > idx:
                            new_tapped.add(ti - 1)
                        elif ti < idx:
                            new_tapped.add(ti)
                    self.tapped_lands = new_tapped
                    # Adjust saga indices
                    new_saga = {}
                    for si, st in self.saga_play_turns.items():
                        if si > idx:
                            new_saga[si - 1] = st
                        elif si < idx:
                            new_saga[si] = st
                    self.saga_play_turns = new_saga
                    # Recompute pool since remaining Islands now produce double
                    pool = self.compute_mana_pool()

        # Phase 3: Deploy utility artifacts (0-cost free, then by ascending CMC)
        deployable = [(UTILITY_ARTIFACTS[name], name) for name in self.hand
                      if name in UTILITY_ARTIFACTS]
        deployable.sort()  # sort by CMC

        for cmc, name in deployable:
            if cmc == 0:
                # Free deploy
                self.hand.remove(name)
                self.battlefield_utility_artifacts.append(name)
                if self.urza_on_board:
                    pool.U += 1
            else:
                cast_pips = {"generic": cmc, "U": 0}
                if pool.can_cast(cast_pips):
                    pool = pool.after_spending(cast_pips)
                    self.hand.remove(name)
                    self.battlefield_utility_artifacts.append(name)
                    if self.urza_on_board:
                        pool.U += 1

        # Phase 4: Attempt Urza cast ({2}{U}{U})
        if not self.urza_on_board:
            cmd_pips = {"generic": 2, "U": 2}
            if pool.can_cast(cmd_pips):
                self.urza_on_board = True
                # Construct token is an artifact creature
                self.battlefield_utility_artifacts.append("Construct Token")
                # Don't spend from pool — commander cast doesn't reduce
                # available mana for recording (mana available = what you HAD)
                # Actually, we just record post-deployment pool, and Urza
                # coming online adds mana from all artifacts. The pool will
                # be recomputed at the end of the turn.


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
    ramp_cards = set(ROCK_DEFS) | SPECIAL_ROCKS | set(AMPLIFIER_DEFS)
    castable = []
    for card in state.hand:
        if card in ramp_cards or card in state.land_set or card in UTILITY_ARTIFACTS:
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
                          classified: dict) -> tuple[float, int]:
    """Print pre-simulation static analysis. Returns (avg_cmc, pip_U)."""
    print("=" * 65)
    print("STATIC ANALYSIS — AZURE DOMINION (BRACKET 4)")
    print("=" * 65)

    print(f"\n--- Deck Composition ---")
    print(f"Total cards (excl. commander): {len(decklist)}")
    print(f"Lands: {len(classified['lands'])}")
    print(f"Mana rocks: {len(classified['rocks'])}")
    print(f"Spells/other: {len(classified['spells'])}")

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

    total_U = 0
    for name in decklist:
        meta = metadata.get(name, {})
        mc = meta.get("mana_cost", "")
        if "Land" in meta.get("type_line", ""):
            continue
        pips = parse_mana_cost(mc)
        total_U += pips["U"]

    print(f"\n--- Pip Demand ---")
    print(f"  Total {{U}} pips: {total_U}")

    # Mana source inventory
    lands = classified["lands"]
    u_lands = sum(1 for l in lands if l in {"Snow-Covered Island", "Seat of the Synod",
                                             "Mystic Sanctuary", "Otawara, Soaring City"})
    c_lands = sum(1 for l in lands if l in {"Darksteel Citadel", "Academy Ruins",
                                             "Reliquary Tower", "Inventors' Fair",
                                             "Ancient Tomb", "Urza's Saga"})
    fetch_count = sum(1 for l in lands if l in FETCH_LANDS)

    print(f"\n--- Mana Source Inventory ---")
    print(f"  Lands: {len(lands)} total")
    print(f"    U-producing: {u_lands}  C-only: {c_lands}  Fetch: {fetch_count}")

    # Rock inventory
    rock_count = sum(1 for r in classified["rocks"] if r in ROCK_DEFS)
    special_count = sum(1 for r in classified["rocks"] if r in SPECIAL_ROCKS)
    amp_count = sum(1 for r in classified["rocks"] if r in AMPLIFIER_DEFS)
    print(f"  Standard rocks: {rock_count}  Special: {special_count}  Amplifiers: {amp_count}")

    # Utility artifacts
    util_count = sum(1 for name in decklist if name in UTILITY_ARTIFACTS)
    print(f"  Utility artifacts (Urza tap targets): {util_count}")

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
    print(f"  Note: {total_ramp} ramp pieces + Urza artifact tap compensate")

    return avg_cmc, total_U


# --- Simulation ---


def run_simulation(decklist: list[str], metadata: dict, num_games: int = NUM_GAMES) -> dict:
    """Run num_games simulations and collect stats."""
    land_set = set()
    for name in set(decklist):
        meta = metadata.get(name, {})
        if "Land" in meta.get("type_line", ""):
            land_set.add(name)

    mana_by_turn = {t: [] for t in range(1, NUM_TURNS + 1)}
    u_by_turn = {t: [] for t in range(1, NUM_TURNS + 1)}
    hand_land_counts = Counter()
    mulligan_attempts = Counter()

    zero_u_by_turn = {t: 0 for t in range(1, NUM_TURNS + 1)}

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
            u_avail = pool.U

            mana_by_turn[t].append(total_mana)
            u_by_turn[t].append(u_avail)

            if u_avail == 0:
                zero_u_by_turn[t] += 1

            # Commander: Urza, Lord High Artificer {2}{U}{U}
            cmd_pips = {"generic": 2, "U": 2}
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
        "hand_land_counts": hand_land_counts,
        "mulligan_attempts": mulligan_attempts,
        "zero_u_by_turn": zero_u_by_turn,
        "commander_castable_turn": commander_castable_turn,
        "commander_by_turn": commander_by_turn,
        "castable_spell_by_turn": castable_spell_by_turn,
        "curve_out_games": curve_out_games,
        "tapped_land_turns": tapped_land_turns,
    }


# --- Results ---


def print_results(stats: dict, classified: dict,
                  avg_cmc: float, pip_U: int):
    """Print simulation results."""
    total = NUM_GAMES

    print("\n" + "=" * 65)
    print(f"MONTE CARLO SIMULATION — AZURE DOMINION ({NUM_GAMES:,} games, {NUM_TURNS} turns)")
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
    print(f"\n--- Dimension 2: Color Balance (Mono-Blue) ---")
    print(f"\n  U sources per turn:")
    print(f"  {'Turn':<6} {'U med':>6} {'U avg':>6}")
    print(f"  {'-'*20}")
    for t in range(1, NUM_TURNS + 1):
        u_med = statistics.median(stats["u_by_turn"][t])
        u_mean = statistics.mean(stats["u_by_turn"][t])
        print(f"    T{t:<4} {u_med:>6.0f} {u_mean:>6.1f}")

    print(f"\n  Color screw (0 U sources):")
    for t in range(1, NUM_TURNS + 1):
        u_pct = stats["zero_u_by_turn"][t] / total * 100
        if u_pct > 0:
            print(f"    T{t}: 0 U = {u_pct:.1f}%")

    # --- Dimension 3: Curve Efficiency ---
    print(f"\n--- Dimension 3: Curve Efficiency ---")

    print(f"\n  Commander castable (Urza, Lord High Artificer, {{2}}{{U}}{{U}}):")
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

    # Commander timing (Urza CMC 4)
    cmd_by_t3 = stats["commander_by_turn"][3] / total * 100
    cmd_by_t4 = stats["commander_by_turn"][4] / total * 100
    if cmd_by_t3 > 50:
        print(f"  Commander by T3: {cmd_by_t3:.0f}% — ahead of curve for 4-CMC")
    elif cmd_by_t4 > 50:
        print(f"  Commander by T4: {cmd_by_t4:.0f}% — on curve for 4-CMC commander")
    else:
        print(f"  Commander by T4: {cmd_by_t4:.0f}% — below 50%, ramp insufficient for 4-CMC")

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
        "paidMulligan": _pct(mull.get(2, 0), total),
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
        "name": "Urza, Lord High Artificer",
        "cmc": 4,
        "byTurn": cmd_by_turn,
        "medianTurn": _median_turn_from_cumulative(cmd_by_turn),
    }

    # colorBalance (mono-blue: single color)
    color_by_turn = {}
    for t in range(1, NUM_TURNS + 1):
        data = stats["u_by_turn"][t]
        color_by_turn[str(t)] = {
            "U": {
                "median": _r1(statistics.median(data)),
                "mean": _r1(statistics.mean(data)),
            }
        }

    color_screw_by_turn = {}
    for t in range(1, NUM_TURNS + 1):
        color_screw_by_turn[str(t)] = {
            "U": _pct(stats["zero_u_by_turn"][t], total),
        }

    color_balance = {
        "colors": ["U"],
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
    cmd_cmc = 4
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
        description="Monte Carlo mana base simulation for Azure Dominion (Urza)")
    parser.add_argument("--json", action="store_true",
                        help="Write simulation.json instead of console output")
    args = parser.parse_args()

    with open(DECK_FILE) as f:
        deck_data = json.load(f)
    with open(METADATA_FILE) as f:
        metadata = json.load(f)

    print("Building Azure Dominion decklist...")
    decklist = build_decklist(deck_data)
    print(f"Decklist: {len(decklist)} cards")

    classified = classify_cards(decklist, metadata)

    if not args.json:
        avg_cmc, pip_U = print_static_analysis(decklist, metadata, classified)
    else:
        cmcs = []
        for name in decklist:
            meta = metadata.get(name, {})
            if "Land" not in meta.get("type_line", ""):
                cmc = meta.get("cmc", 0)
                if isinstance(cmc, (int, float)):
                    cmcs.append(int(cmc))
        avg_cmc = statistics.mean(cmcs) if cmcs else 0
        pip_U = 0

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
        print_results(stats, classified, avg_cmc, pip_U)
        print("\n" + "=" * 65)


if __name__ == "__main__":
    main()
