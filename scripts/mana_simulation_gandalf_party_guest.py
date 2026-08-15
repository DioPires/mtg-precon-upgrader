#!/usr/bin/env python3
"""Monte Carlo mana base simulation for Arcane Convocation (Gandalf, Party Guest).

Simulates 100,000 games measuring mana production, color balance, and curve
efficiency turns 1-10 for the Jeskai decklist.

Commander: Gandalf, Party Guest ({1}{U}{R}{W}, CMC 4)
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
DECK_FILE = PROJECT_ROOT / "data" / "commanders" / "gandalf-party-guest" / "deck.json"
METADATA_FILE = PROJECT_ROOT / "data" / "card-metadata.json"
JSON_OUTPUT = PROJECT_ROOT / "data" / "commanders" / "gandalf-party-guest" / "simulation.json"

NUM_GAMES = 100_000
NUM_TURNS = 10

# Commander: Gandalf, Party Guest {1}{U}{R}{W}
COMMANDER_PIPS = {"generic": 1, "U": 1, "R": 1, "W": 1}

# --- Mana cost parser ---


def parse_mana_cost(mana_cost: str) -> dict:
    """Parse mana_cost string into pip breakdown.

    "{1}{U}{R}{W}" -> {generic: 1, U: 1, R: 1, W: 1, total: 4}
    "{U}{U}{R}" -> {generic: 0, U: 2, R: 1, W: 0, total: 3}

    Split cards (//): parse first half only.
    """
    if "//" in mana_cost:
        mana_cost = mana_cost.split("//")[0].strip()

    result = {"generic": 0, "U": 0, "R": 0, "W": 0, "total": 0, "X": False}
    symbols = re.findall(r"\{([^}]+)\}", mana_cost)
    for sym in symbols:
        if sym == "X":
            result["X"] = True
        elif sym.isdigit():
            result["generic"] += int(sym)
        elif sym in ("U", "R", "W"):
            result[sym] += 1
        # Ignore other symbols (hybrid, phyrexian, etc.)
    result["total"] = result["generic"] + result["U"] + result["R"] + result["W"]
    return result


def front_face_type_line(meta: dict) -> str:
    """Front face of a type_line — split cards/MDFCs classify by face one only."""
    return meta.get("type_line", "").split("//")[0]


# --- Rock definitions ---
# "count" = net mana atoms produced. Sol Ring taps for {C}{C} = 2 atoms.
# Mox Amber is legendary-gated: it produces 0 mana until a legendary creature
# (or the commander) has resolved — see GameState.legendary_resolved.
# Lotus Petal is a one-shot: cracked the first time its mana is actually needed,
# never a persistent rock — see GameState.petal_available.

ROCK_DEFS = {
    "Sol Ring":               {"cmc": 1, "colors": frozenset({"C"}), "count": 2, "burst": False},
    "Arcane Signet":          {"cmc": 2, "colors": frozenset({"U", "R", "W"}), "count": 1, "burst": False},
    "Izzet Signet":           {"cmc": 2, "colors": frozenset({"U", "R"}), "count": 1, "burst": False},
    "Talisman of Creativity": {"cmc": 2, "colors": frozenset({"U", "R"}), "count": 1, "burst": False},
    "Talisman of Progress":   {"cmc": 2, "colors": frozenset({"W", "U"}), "count": 1, "burst": False},
    "Mox Amber":              {"cmc": 0, "colors": frozenset({"U", "R", "W"}), "count": 1, "burst": False},
    "Lotus Petal":            {"cmc": 0, "colors": frozenset({"U", "R", "W"}), "count": 1, "burst": True},
}

# --- Land subtype definitions (for check lands and the battleland) ---

PLAINS_TYPED_LANDS = {"Plains", "Prairie Stream", "Turbulent Steppe",
                      "Hallowed Fountain", "Sacred Foundry"}
ISLAND_TYPED_LANDS = {"Island", "Prairie Stream", "Turbulent Springs",
                      "Steam Vents", "Hallowed Fountain"}
MOUNTAIN_TYPED_LANDS = {"Mountain", "Turbulent Springs", "Turbulent Steppe",
                        "Steam Vents", "Sacred Foundry"}

BASIC_LANDS = {"Island", "Mountain", "Plains"}

ALWAYS_TAPPED = {"Path of Ancestry", "Temple of Epiphany"}


def land_enters_tapped(name: str, battlefield_lands: list[str], turn: int) -> bool:
    """Determine if a land enters tapped given current board and turn number."""
    if name in ALWAYS_TAPPED:
        return True

    # Battleland: untapped with 2+ basics already on the battlefield
    if name == "Prairie Stream":
        basics = sum(1 for l in battlefield_lands if l in BASIC_LANDS)
        return basics < 2

    # "Tapped unless your opponents control eight or more lands" — 4-player
    # model: 3 opponents make ~3 land drops per turn cycle, so untapped from T4.
    if name in {"Turbulent Springs", "Turbulent Steppe"}:
        return turn < 4

    # Check lands (need a matching typed land on the battlefield)
    if name == "Glacial Fortress":  # Plains or Island
        return not any(l in PLAINS_TYPED_LANDS or l in ISLAND_TYPED_LANDS
                       for l in battlefield_lands)
    if name == "Sulfur Falls":  # Island or Mountain
        return not any(l in ISLAND_TYPED_LANDS or l in MOUNTAIN_TYPED_LANDS
                       for l in battlefield_lands)
    if name == "Clifftop Retreat":  # Mountain or Plains
        return not any(l in MOUNTAIN_TYPED_LANDS or l in PLAINS_TYPED_LANDS
                       for l in battlefield_lands)

    # Shock lands (Steam Vents, Hallowed Fountain, Sacred Foundry): pay 2 life.
    # Pathways (modal DFC duals), Skycloud Expanse (filter, modeled as dual),
    # Command Tower, Exotic Orchard, Adarkar Wastes, Ancient Tomb, basics: untapped.
    return False


def compute_land_sources(name: str, battlefield_lands: list[str]) -> list[frozenset]:
    """Return mana sources (frozensets of producible colors) for a single untapped land.

    Each frozenset in the returned list represents one mana atom.
    Most lands return a single atom; Ancient Tomb returns two.
    """
    # Basics
    if name == "Island":
        return [frozenset({"U"})]
    if name == "Mountain":
        return [frozenset({"R"})]
    if name == "Plains":
        return [frozenset({"W"})]

    # Tri-color lands
    if name in {"Command Tower", "Exotic Orchard", "Path of Ancestry"}:
        return [frozenset({"U", "R", "W"})]

    # WU duals (Skycloud Expanse filter + Hengegate Pathway MDFC modeled as duals)
    if name in {"Skycloud Expanse", "Prairie Stream", "Adarkar Wastes",
                "Glacial Fortress", "Hengegate Pathway", "Hallowed Fountain"}:
        return [frozenset({"W", "U"})]

    # UR duals (Riverglide Pathway MDFC modeled as a dual)
    if name in {"Temple of Epiphany", "Turbulent Springs", "Sulfur Falls",
                "Riverglide Pathway", "Steam Vents"}:
        return [frozenset({"U", "R"})]

    # RW duals (Needleverge Pathway MDFC modeled as a dual)
    if name in {"Turbulent Steppe", "Clifftop Retreat", "Needleverge Pathway",
                "Sacred Foundry"}:
        return [frozenset({"R", "W"})]

    # Ancient Tomb: {T}: Add {C}{C} — two colorless atoms
    if name == "Ancient Tomb":
        return [frozenset({"C"}), frozenset({"C"})]

    # Fallback: colorless
    return [frozenset({"C"})]


# --- ManaPool (source-based for 3-color mana) ---


class ManaPool:
    """Tracks available mana as a list of source atoms.

    Each source is a frozenset of colors it can produce (one mana).
    e.g. frozenset({"U","R"}) = one mana that can be U or R.
    frozenset({"C"}) = one colorless mana.
    """

    def __init__(self, sources=None):
        self.sources: list[frozenset] = list(sources) if sources else []

    @property
    def total(self) -> int:
        return len(self.sources)

    def count_color(self, color: str) -> int:
        """Count sources that can produce this color."""
        return sum(1 for s in self.sources if color in s)

    def _allocate(self, pips: dict) -> tuple[bool, list[frozenset] | None]:
        """Greedy allocation of sources to a mana cost.

        Strategy: assign colored pips first (most constrained color first,
        using most constrained source for each), then generic from leftovers.

        Returns (success, remaining_sources_after_payment).
        """
        needed = {"U": pips.get("U", 0), "R": pips.get("R", 0), "W": pips.get("W", 0)}
        generic = pips.get("generic", 0)
        total_needed = sum(needed.values()) + generic

        if self.total < total_needed:
            return False, None

        available = list(self.sources)

        # Phase 1: Assign colored pips — most constrained color first
        for _ in range(sum(needed.values())):
            # Find color with fewest available sources relative to remaining need
            best_color = None
            best_ratio = float("inf")
            for color in "URW":
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

            # Find most constrained source for this color (fewest alternative colors)
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

        # Phase 2: Spend generic — use least flexible sources first (preserve tri-sources)
        available.sort(key=lambda s: len(s))
        if len(available) < generic:
            return False, None

        remaining = available[generic:]
        return True, remaining

    def can_cast(self, pips: dict) -> bool:
        """Check if this pool can pay the given mana cost."""
        success, _ = self._allocate(pips)
        return success

    def after_spending(self, pips: dict) -> "ManaPool":
        """Return a new ManaPool after spending pips. Assumes can_cast is True."""
        success, remaining = self._allocate(pips)
        if not success:
            return ManaPool()
        return ManaPool(remaining)


# --- Decklist builder ---


def build_decklist(deck_data: dict) -> list[str]:
    """Build 99-card decklist for Arcane Convocation.

    Reads the flat decklist array directly. Each entry has {name, type} with
    optional quantity field. Commander is in the command zone (not in decklist).
    """
    cards = []
    for card in deck_data["decklist"]:
        qty = card.get("quantity", 1)
        cards.extend([card["name"]] * qty)
    return cards


def classify_cards(decklist: list[str], metadata: dict) -> dict:
    """Classify each card as land, rock, or spell (front face only for // cards)."""
    classified = {"lands": [], "rocks": [], "spells": []}
    for name in decklist:
        if name in ROCK_DEFS:
            classified["rocks"].append(name)
        else:
            meta = metadata.get(name, {})
            if "Land" in front_face_type_line(meta):
                classified["lands"].append(name)
            else:
                classified["spells"].append(name)
    return classified


# --- Mulligan ---

MAX_MULLIGANS = 2  # attempt 0 = initial, 1 = free, 2 = paid (bottom 1)


def should_mulligan(hand: list[str], land_set: set[str]) -> bool:
    """Mulligan if 0-1 mana sources (lands + rocks)."""
    sources = sum(1 for c in hand if c in land_set or c in ROCK_DEFS)
    return sources <= 1


def choose_bottom_cards(hand: list[str], count: int, metadata: dict,
                        land_set: set[str]) -> list[str]:
    """Choose cards to bottom (London mulligan). Bottom highest CMC non-source cards."""
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
        self.tapped_lands: set[int] = set()  # indices into battlefield_lands
        self.battlefield_rocks: list[str] = []
        self.metadata = metadata
        self.land_set = land_set
        self.mana_per_turn: list[ManaPool] = []
        self.mulligan_attempt = 0
        # Mox Amber gate: True once the commander or any legendary creature has
        # resolved (modeled as: first turn one is castable from the pool).
        self.legendary_resolved = False
        # Lotus Petal one-shot: True while an uncracked Petal is on the battlefield.
        self.petal_available = False

    def draw(self, n: int = 1):
        for _ in range(n):
            if self.library:
                self.hand.append(self.library.pop())

    def count_lands_in_hand(self) -> int:
        return sum(1 for c in self.hand if c in self.land_set)

    def _is_land(self, name: str) -> bool:
        return name in self.land_set

    def _land_play_priority(self, name: str, turn: int) -> float:
        """Higher = play first. Untapped > tapped. Color-fixing > mono."""
        tapped = land_enters_tapped(name, self.battlefield_lands, turn)
        base = 0 if tapped else 10

        # More colors produced = higher priority
        sources = compute_land_sources(name, self.battlefield_lands)
        if sources:
            n_colors = sum(1 for c in "URW" if c in sources[0])
            base += n_colors * 2

        return base

    def compute_mana_pool(self) -> ManaPool:
        """Calculate total available mana from all untapped lands + rocks.

        Mox Amber contributes 0 mana until legendary_resolved. Lotus Petal is
        never a persistent source (handled via crack_petal_atom).
        """
        pool_sources: list[frozenset] = []

        for i, land in enumerate(self.battlefield_lands):
            if i in self.tapped_lands:
                continue
            sources = compute_land_sources(land, self.battlefield_lands)
            pool_sources.extend(sources)

        for rock in self.battlefield_rocks:
            if rock == "Mox Amber" and not self.legendary_resolved:
                continue
            rdef = ROCK_DEFS[rock]
            for _ in range(rdef["count"]):
                pool_sources.append(rdef["colors"])

        return ManaPool(pool_sources)

    def petal_atom(self) -> frozenset:
        return ROCK_DEFS["Lotus Petal"]["colors"]

    def _check_legendary_resolved(self):
        """Set the Mox Amber gate the first turn the commander or a legendary
        creature from hand is castable from the current pool (Mox excluded
        while the gate is off, so it never bootstraps itself)."""
        if self.legendary_resolved:
            return
        pool = self.compute_mana_pool()
        if pool.can_cast(COMMANDER_PIPS):
            self.legendary_resolved = True
            return
        for card in self.hand:
            meta = self.metadata.get(card, {})
            if not front_face_type_line(meta).startswith("Legendary Creature"):
                continue
            pips = parse_mana_cost(meta.get("mana_cost", ""))
            if pool.can_cast(pips):
                self.legendary_resolved = True
                return

    def play_turn(self, turn_number: int):
        """Simulate one turn."""
        # Draw (skip T1)
        if turn_number > 1:
            self.draw(1)

        # Untap all
        self.tapped_lands.clear()

        # Play best land from hand
        hand_lands = [(self._land_play_priority(c, turn_number), c)
                      for c in self.hand if self._is_land(c)]
        hand_lands.sort(reverse=True)

        if hand_lands:
            _, land_name = hand_lands[0]
            self.hand.remove(land_name)
            tapped = land_enters_tapped(land_name, self.battlefield_lands, turn_number)
            self.battlefield_lands.append(land_name)
            if tapped:
                self.tapped_lands.add(len(self.battlefield_lands) - 1)

        # Cast rocks from hand
        pool = self.compute_mana_pool()
        self._try_cast_rocks(pool)

        # Mox Amber gate check (after rocks so a T1 Mox is live if a legend lands)
        self._check_legendary_resolved()

        # Record final mana pool
        self.mana_per_turn.append(self.compute_mana_pool())

    def _try_cast_rocks(self, pool: ManaPool):
        """Try to cast mana rocks from hand, priority order (free first, then cheapest)."""
        priority_order = [
            "Mox Amber", "Lotus Petal",
            "Sol Ring",
            "Arcane Signet", "Izzet Signet",
            "Talisman of Creativity", "Talisman of Progress",
        ]

        for rock_name in priority_order:
            if rock_name not in self.hand:
                continue
            rdef = ROCK_DEFS[rock_name]
            pips = parse_mana_cost(
                self.metadata.get(rock_name, {}).get("mana_cost", ""))
            cracked_petal = False
            if not pool.can_cast(pips):
                # Crack Lotus Petal if its one flexible mana bridges the gap
                if self.petal_available:
                    boosted = ManaPool(pool.sources + [self.petal_atom()])
                    if boosted.can_cast(pips):
                        pool = boosted
                        cracked_petal = True
                    else:
                        continue
                else:
                    continue
            pool = pool.after_spending(pips)
            if cracked_petal:
                self.petal_available = False
            self.hand.remove(rock_name)
            if rock_name == "Lotus Petal":
                # One-shot: sits on the battlefield until cracked; never in the pool
                self.petal_available = True
                continue
            self.battlefield_rocks.append(rock_name)
            # Add rock's mana production to pool for subsequent casts
            if rock_name != "Mox Amber" or self.legendary_resolved:
                for _ in range(rdef["count"]):
                    pool.sources.append(rdef["colors"])


def commander_mulligan(decklist: list[str], metadata: dict,
                       land_set: set[str]) -> GameState:
    """Commander mulligan: free first, then London.

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
            continue
        if pool.can_cast(pips):
            castable.append(card)
    return castable


# --- Static analysis ---


def print_static_analysis(decklist: list[str], metadata: dict,
                          classified: dict) -> tuple[float, int, int, int]:
    """Print pre-simulation static analysis. Returns (avg_cmc, pip_U, pip_R, pip_W)."""
    print("=" * 65)
    print("STATIC ANALYSIS — ARCANE CONVOCATION (GANDALF, PARTY GUEST)")
    print("=" * 65)

    print(f"\n--- Deck Composition ---")
    print(f"Total cards (excl. commander): {len(decklist)}")
    print(f"Lands: {len(classified['lands'])}")
    print(f"Mana rocks: {len(classified['rocks'])}")
    print(f"Spells/creatures: {len(classified['spells'])}")

    # CMC histogram
    cmcs = []
    for name in decklist:
        meta = metadata.get(name, {})
        if "Land" not in front_face_type_line(meta):
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

    # Pip counts
    total_U, total_R, total_W = 0, 0, 0
    for name in decklist:
        meta = metadata.get(name, {})
        mc = meta.get("mana_cost", "")
        if "Land" in front_face_type_line(meta):
            continue
        pips = parse_mana_cost(mc)
        total_U += pips["U"]
        total_R += pips["R"]
        total_W += pips["W"]

    total_pips = total_U + total_R + total_W
    u_ratio = total_U / total_pips * 100 if total_pips > 0 else 0
    r_ratio = total_R / total_pips * 100 if total_pips > 0 else 0
    w_ratio = total_W / total_pips * 100 if total_pips > 0 else 0

    print(f"\n--- Pip Demand ---")
    print(f"  Total {{U}} pips: {total_U}")
    print(f"  Total {{R}} pips: {total_R}")
    print(f"  Total {{W}} pips: {total_W}")
    print(f"  Ratio: {u_ratio:.0f}% U / {r_ratio:.0f}% R / {w_ratio:.0f}% W")

    # Mana source inventory
    lands = classified["lands"]
    u_lands, r_lands, w_lands, c_only = 0, 0, 0, 0
    for l in lands:
        sources = compute_land_sources(l, [])  # empty board for static count
        if not sources:
            continue
        colors = sources[0]
        if "U" in colors:
            u_lands += 1
        if "R" in colors:
            r_lands += 1
        if "W" in colors:
            w_lands += 1
        if colors == frozenset({"C"}):
            c_only += 1

    def _count_pair(pair):
        return sum(1 for l in lands
                   if compute_land_sources(l, [])
                   and pair <= compute_land_sources(l, [])[0])

    urw_lands = _count_pair({"U", "R", "W"})
    ur_lands = _count_pair({"U", "R"}) - urw_lands
    wu_lands = _count_pair({"W", "U"}) - urw_lands
    rw_lands = _count_pair({"R", "W"}) - urw_lands

    print(f"\n--- Mana Source Inventory ---")
    print(f"  Lands: {len(lands)} total")
    print(f"    U-producing: {u_lands}  R-producing: {r_lands}  W-producing: {w_lands}")
    print(f"    URW tri-lands: {urw_lands}")
    print(f"    UR duals: {ur_lands}  WU duals: {wu_lands}  RW duals: {rw_lands}")
    print(f"    C-only: {c_only}")

    # Rock inventory
    rocks = classified["rocks"]
    urw_rocks = sum(1 for r in rocks if ROCK_DEFS[r]["colors"] >= {"U", "R", "W"})
    ur_rocks = sum(1 for r in rocks if ROCK_DEFS[r]["colors"] == frozenset({"U", "R"}))
    wu_rocks = sum(1 for r in rocks if ROCK_DEFS[r]["colors"] == frozenset({"W", "U"}))
    rw_rocks = sum(1 for r in rocks if ROCK_DEFS[r]["colors"] == frozenset({"R", "W"}))
    c_rocks = sum(1 for r in rocks if ROCK_DEFS[r]["colors"] == frozenset({"C"}))
    net_mana = sum(ROCK_DEFS[r]["count"] for r in rocks)
    print(f"  Rocks: {len(rocks)} total ({net_mana} net mana)")
    print(f"    URW-flex: {urw_rocks}  UR: {ur_rocks}  WU: {wu_rocks}  RW: {rw_rocks}  C: {c_rocks}")
    print(f"    (Mox Amber legendary-gated; Lotus Petal one-shot)")

    # Recommended land count heuristic
    recommended = round(36 + (avg_cmc - 3.0) * 2)
    print(f"\n--- Land Count Heuristic ---")
    print(f"  Avg CMC: {avg_cmc:.2f}")
    print(f"  Current lands: {len(lands)}")
    print(f"  Heuristic recommendation: ~{recommended} lands")
    delta = len(lands) - recommended
    if delta >= 0:
        print(f"  Status: adequate ({len(lands)} >= {recommended})")
    else:
        print(f"  Status: light ({len(lands)} < {recommended}, delta = {abs(delta)})")
    print(f"  Note: {len(rocks)} rocks ({net_mana} net mana) compensate for lower land count")

    return avg_cmc, total_U, total_R, total_W


# --- Simulation ---


def run_simulation(decklist: list[str], metadata: dict, num_games: int = NUM_GAMES) -> dict:
    """Run num_games simulations and collect stats."""
    land_set = set()
    for name in set(decklist):
        meta = metadata.get(name, {})
        if "Land" in front_face_type_line(meta):
            land_set.add(name)

    mana_by_turn = {t: [] for t in range(1, NUM_TURNS + 1)}
    u_by_turn = {t: [] for t in range(1, NUM_TURNS + 1)}
    r_by_turn = {t: [] for t in range(1, NUM_TURNS + 1)}
    w_by_turn = {t: [] for t in range(1, NUM_TURNS + 1)}
    hand_land_counts = Counter()
    mulligan_attempts = Counter()

    zero_u_by_turn = {t: 0 for t in range(1, NUM_TURNS + 1)}
    zero_r_by_turn = {t: 0 for t in range(1, NUM_TURNS + 1)}
    zero_w_by_turn = {t: 0 for t in range(1, NUM_TURNS + 1)}

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
            u_by_turn[t].append(pool.count_color("U"))
            r_by_turn[t].append(pool.count_color("R"))
            w_by_turn[t].append(pool.count_color("W"))

            if pool.count_color("U") == 0:
                zero_u_by_turn[t] += 1
            if pool.count_color("R") == 0:
                zero_r_by_turn[t] += 1
            if pool.count_color("W") == 0:
                zero_w_by_turn[t] += 1

            # Commander: Gandalf, Party Guest {1}{U}{R}{W}
            if cmd_cast_turn is None:
                castable_now = pool.can_cast(COMMANDER_PIPS)
                if not castable_now and state.petal_available:
                    # Crack Lotus Petal the turn its mana is needed for the commander
                    boosted = ManaPool(pool.sources + [state.petal_atom()])
                    if boosted.can_cast(COMMANDER_PIPS):
                        castable_now = True
                        state.petal_available = False
                if castable_now:
                    cmd_cast_turn = t
                    commander_by_turn[t] += 1
                    state.legendary_resolved = True  # commander is cast

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

        if cmd_cast_turn is not None:
            commander_castable_turn.append(cmd_cast_turn)
            for future_t in range(cmd_cast_turn + 1, NUM_TURNS + 1):
                commander_by_turn[future_t] += 1

        if cast_every_turn:
            curve_out_games += 1

    return {
        "mana_by_turn": mana_by_turn,
        "u_by_turn": u_by_turn,
        "r_by_turn": r_by_turn,
        "w_by_turn": w_by_turn,
        "hand_land_counts": hand_land_counts,
        "mulligan_attempts": mulligan_attempts,
        "zero_u_by_turn": zero_u_by_turn,
        "zero_r_by_turn": zero_r_by_turn,
        "zero_w_by_turn": zero_w_by_turn,
        "commander_castable_turn": commander_castable_turn,
        "commander_by_turn": commander_by_turn,
        "castable_spell_by_turn": castable_spell_by_turn,
        "curve_out_games": curve_out_games,
        "tapped_land_turns": tapped_land_turns,
    }


# --- Results ---


def print_results(stats: dict, classified: dict,
                  avg_cmc: float, pip_U: int, pip_R: int, pip_W: int):
    """Print simulation results across all three dimensions."""
    total = NUM_GAMES

    print("\n" + "=" * 65)
    print(f"MONTE CARLO SIMULATION — ARCANE CONVOCATION ({NUM_GAMES:,} games, {NUM_TURNS} turns)")
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
    print(f"    Paid mulligan (→6):  {mull.get(2, 0)/total*100:>5.1f}% (redraw 7, bottom 1)")

    print(f"\n  Opening hand (post-mulligan):")
    print(f"    Land count distribution:")
    for lands in range(8):
        count = stats["hand_land_counts"].get(lands, 0)
        if count > 0:
            bar = "#" * int(count / total * 50)
            print(f"      {lands} lands: {count/total*100:>5.1f}% {bar}")

    # --- Dimension 2: Color Balance ---
    print(f"\n--- Dimension 2: Color Balance ---")
    print(f"\n  U, R, W sources per turn (can-produce count):")
    print(f"  {'Turn':<6} {'U med':>6} {'U avg':>6} {'R med':>6} {'R avg':>6} {'W med':>6} {'W avg':>6}")
    print(f"  {'-'*42}")
    for t in range(1, NUM_TURNS + 1):
        u_med = statistics.median(stats["u_by_turn"][t])
        u_mean = statistics.mean(stats["u_by_turn"][t])
        r_med = statistics.median(stats["r_by_turn"][t])
        r_mean = statistics.mean(stats["r_by_turn"][t])
        w_med = statistics.median(stats["w_by_turn"][t])
        w_mean = statistics.mean(stats["w_by_turn"][t])
        print(f"    T{t:<4} {u_med:>6.0f} {u_mean:>6.1f} {r_med:>6.0f} {r_mean:>6.1f} {w_med:>6.0f} {w_mean:>6.1f}")

    print(f"\n  Color screw (0 sources of a color):")
    for t in range(2, NUM_TURNS + 1):
        u_pct = stats["zero_u_by_turn"][t] / total * 100
        r_pct = stats["zero_r_by_turn"][t] / total * 100
        w_pct = stats["zero_w_by_turn"][t] / total * 100
        print(f"    T{t}: 0 U = {u_pct:.1f}%, 0 R = {r_pct:.1f}%, 0 W = {w_pct:.1f}%")

    pip_total = pip_U + pip_R + pip_W
    u_demand = pip_U / pip_total * 100 if pip_total > 0 else 0
    r_demand = pip_R / pip_total * 100 if pip_total > 0 else 0
    w_demand = pip_W / pip_total * 100 if pip_total > 0 else 0

    t3_u = statistics.mean(stats["u_by_turn"][3])
    t3_r = statistics.mean(stats["r_by_turn"][3])
    t3_w = statistics.mean(stats["w_by_turn"][3])
    t3_total = t3_u + t3_r + t3_w
    u_supply = t3_u / t3_total * 100 if t3_total > 0 else 0
    r_supply = t3_r / t3_total * 100 if t3_total > 0 else 0
    w_supply = t3_w / t3_total * 100 if t3_total > 0 else 0

    print(f"\n  Pip demand vs supply ratio (T3 avg):")
    print(f"    Demand: {u_demand:.0f}% U / {r_demand:.0f}% R / {w_demand:.0f}% W")
    print(f"    Supply: {u_supply:.0f}% U / {r_supply:.0f}% R / {w_supply:.0f}% W")

    # --- Dimension 3: Curve Efficiency ---
    print(f"\n--- Dimension 3: Curve Efficiency ---")

    print(f"\n  Commander castable (Gandalf, Party Guest, {{1}}{{U}}{{R}}{{W}}):")
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
    for color, demand, supply in [("U", u_demand, u_supply),
                                  ("R", r_demand, r_supply),
                                  ("W", w_demand, w_supply)]:
        deficit = demand - supply
        if deficit > max_deficit:
            max_deficit = deficit
            worst_color = color

    if max_deficit < 10:
        print(f"  Color balance: well-matched (all within {max_deficit:.0f}% demand-supply gap)")
    else:
        print(f"  Color balance: {worst_color} undersupplied "
              f"({max_deficit:.0f}% gap) — consider more {worst_color} sources")

    # Commander timing (4-CMC commander)
    cmd_by_t3 = stats["commander_by_turn"][3] / total * 100
    cmd_by_t4 = stats["commander_by_turn"][4] / total * 100
    if cmd_by_t3 > 50:
        print(f"  Commander by T3: {cmd_by_t3:.0f}% — ahead of curve for 4-CMC")
    elif cmd_by_t4 > 50:
        print(f"  Commander by T4: {cmd_by_t4:.0f}% — on curve for 4-CMC commander")
    else:
        print(f"  Commander by T4: {cmd_by_t4:.0f}% — below 50%, mana insufficient for 4-CMC")

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

    result = exporter.export_gandalf_party_guest(metadata)
    if not exporter.validate_output(result, "gandalf-party-guest"):
        raise ValueError("export_gandalf_party_guest produced invalid simulation output")
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Monte Carlo mana base simulation for Arcane Convocation (Gandalf, Party Guest)")
    parser.add_argument("--json", action="store_true",
                        help="Write simulation.json instead of console output")
    args = parser.parse_args()

    with open(DECK_FILE) as f:
        deck_data = json.load(f)
    with open(METADATA_FILE) as f:
        metadata = json.load(f)

    print("Building Arcane Convocation decklist...")
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

    avg_cmc, pip_U, pip_R, pip_W = print_static_analysis(decklist, metadata, classified)

    n_workers = os.cpu_count() or 4
    chunk_size = NUM_GAMES // n_workers
    remainder = NUM_GAMES % n_workers
    chunks = [chunk_size + (1 if i < remainder else 0) for i in range(n_workers)]

    print(f"\nRunning {NUM_GAMES:,} game simulations ({n_workers} workers)...")
    with multiprocessing.Pool(n_workers) as pool:
        results = pool.map(_run_chunk, [(decklist, metadata, n) for n in chunks])
    stats = merge_stats(results)

    print_results(stats, classified, avg_cmc, pip_U, pip_R, pip_W)
    print("\n" + "=" * 65)


if __name__ == "__main__":
    main()
