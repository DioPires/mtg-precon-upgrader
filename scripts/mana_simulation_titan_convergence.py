#!/usr/bin/env python3
"""Monte Carlo mana base simulation for Titan Convergence (Zhulodok, Void Gorger).

Simulates 100,000 games measuring mana production turns 1-10 with the
Bracket 4 decklist (commander in command zone).
"""

import argparse
import itertools
import json
import multiprocessing
import os
import random
import statistics
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DECK_FILE = PROJECT_ROOT / "data" / "commanders" / "titan-convergence" / "deck.json"
METADATA_FILE = PROJECT_ROOT / "data" / "card-metadata.json"
JSON_OUTPUT = PROJECT_ROOT / "data" / "commanders" / "titan-convergence" / "simulation.json"

NUM_GAMES = 100_000
NUM_TURNS = 10

# --- Land mana production rules ---

# Lands that always produce 0 mana
ZERO_MANA_LANDS = {"Eye of Ugin"}

# Lands that produce 2+ under certain conditions (handled in code)
# Eldrazi Temple: 2 (most spells are Eldrazi)
# Ugin's Labyrinth: 2 (imprint trivial)
# Scorched Ruins: 4 (ETB sacs 2 untapped lands)
# Shrine of the Forsaken Gods: 1 until 7 lands, then 2
# Urza's Mine/Power Plant/Tower: Tron-dependent
# Planar Nexus: 1, enables Tron
# Urza's Workshop: metalcraft-dependent, scales with Urza land count

TRON_PIECES = {"Urza's Mine", "Urza's Power Plant", "Urza's Tower"}
URZA_LANDS = {"Urza's Mine", "Urza's Power Plant", "Urza's Tower", "Urza's Cave", "Urza's Workshop", "Planar Nexus"}

# --- Rock definitions ---
# (name, cmc, mana_per_turn, is_burst)
# is_burst: produces mana on cast turn only (Mana Vault, Basalt Monolith)

ROCK_DEFS = {
    "Sol Ring": {"cmc": 1, "mana": 2, "burst": False},
    "Mind Stone": {"cmc": 2, "mana": 1, "burst": False},
    "Thought Vessel": {"cmc": 2, "mana": 1, "burst": False},
    "Worn Powerstone": {"cmc": 3, "mana": 2, "burst": False},
    "Thran Dynamo": {"cmc": 4, "mana": 3, "burst": False},
    "Hedron Archive": {"cmc": 4, "mana": 2, "burst": False},
    "Darksteel Monolith": {"cmc": 4, "mana": 2, "burst": False},
    "Mana Vault": {"cmc": 1, "mana": 3, "burst": True},
    "Basalt Monolith": {"cmc": 3, "mana": 3, "burst": True},
    "Liquimetal Torque": {"cmc": 2, "mana": 1, "burst": False},
}

# --- Land-fetch artifacts (deploy cheap, crack later for a land) ---
LAND_FETCH_DEFS = {
    "Wayfarer's Bauble": {"cmc": 1, "crack_cost": 2, "fetches": "Wastes"},
}

AMPLIFIER_DEFS = {
    "Forsaken Monument": {"cmc": 5},
    "Extraplanar Lens": {"cmc": 3},
}

# --- Mulligan rules (Commander London mulligan) ---
MAX_MULLIGANS = 2  # attempt 0 = initial, 1 = free, 2 = paid (bottom 1)


def should_mulligan(hand: list[str]) -> bool:
    """Mulligan if 0-1 mana sources (lands + rocks + land-fetchers)."""
    sources = sum(1 for c in hand if c in _land_set or c in ROCK_DEFS or c in LAND_FETCH_DEFS)
    return sources <= 1


def choose_bottom_cards(hand: list[str], count: int, metadata: dict) -> list[str]:
    """Choose cards to bottom (London mulligan). Bottom highest CMC non-land, non-rock cards."""
    candidates = [c for c in hand if c not in _land_set and c not in ROCK_DEFS and c not in LAND_FETCH_DEFS]
    candidates.sort(key=lambda c: metadata.get(c, {}).get("cmc", 0), reverse=True)
    if len(candidates) < count:
        # Fall back to worst lands (e.g., all-source hands)
        land_candidates = [c for c in hand if c in _land_set and c not in [x for x in candidates]]
        land_candidates.sort(key=lambda c: land_base_mana(c, [], False, False))
        candidates.extend(land_candidates)
    return candidates[:count]


def build_decklist(deck_data: dict) -> list[str]:
    """Build the 99-card decklist for Titan Convergence.

    Reads the flat decklist array directly. Each entry has {name, type} with
    optional quantity field. Commander is in the command zone (not in decklist).
    """
    cards = []
    for card in deck_data["decklist"]:
        qty = card.get("quantity", 1)
        cards.extend([card["name"]] * qty)
    return cards


def classify_cards(decklist: list[str], metadata: dict) -> dict:
    """Classify each card as land, rock, amplifier, or spell."""
    classified = {"lands": [], "rocks": [], "amplifiers": [], "spells": []}

    for name in decklist:
        if name in ROCK_DEFS or name in LAND_FETCH_DEFS:
            classified["rocks"].append(name)
        elif name in AMPLIFIER_DEFS:
            classified["amplifiers"].append(name)
        else:
            meta = metadata.get(name, {})
            type_line = meta.get("type_line", "")
            if "Land" in type_line:
                classified["lands"].append(name)
            else:
                classified["spells"].append(name)

    return classified


def land_base_mana(name: str, battlefield_lands: list[str], has_forsaken: bool, has_lens: bool) -> int:
    """Calculate mana a land produces given current board state."""
    if name in ZERO_MANA_LANDS:
        return 0

    base = 1  # default

    if name == "Eldrazi Temple":
        base = 2
    elif name == "Ugin's Labyrinth":
        base = 2
    elif name == "Scorched Ruins":
        base = 4
    elif name == "Shrine of the Forsaken Gods":
        total_lands = len(battlefield_lands)
        base = 2 if total_lands >= 7 else 1
    elif name in TRON_PIECES:
        # Check if Tron is assembled (all 3 types present, Planar Nexus counts as all)
        has_nexus = "Planar Nexus" in battlefield_lands
        types_present = set()
        for land in battlefield_lands:
            if land in TRON_PIECES:
                types_present.add(land)
        tron_complete = (len(types_present) >= 3) or (has_nexus and len(types_present) >= 1)

        if tron_complete:
            if name == "Urza's Tower":
                base = 3
            else:
                base = 2
        else:
            base = 1
    elif name == "Planar Nexus":
        base = 1
    elif name == "Urza's Workshop":
        # Metalcraft trivial (3+ artifacts). Produces mana = number of Urza lands in play.
        urza_count = sum(1 for l in battlefield_lands if l in URZA_LANDS)
        base = max(1, urza_count)  # at least 1
    elif name == "Wastes":
        if has_lens:
            base = 2
        else:
            base = 1

    # Forsaken Monument: +1 to each colorless mana produced
    if has_forsaken and base > 0:
        base += 1

    # Extraplanar Lens only affects Wastes (handled above with has_lens)
    # Forsaken Monument already applied above

    return base


def rock_mana(name: str, has_forsaken: bool) -> int:
    """Calculate mana a rock produces per turn."""
    rock = ROCK_DEFS[name]
    base = rock["mana"]
    if has_forsaken:
        base += 1
    return base


class GameState:
    def __init__(self, decklist: list[str]):
        self.library = list(decklist)
        random.shuffle(self.library)
        self.hand: list[str] = []
        self.battlefield_lands: list[str] = []
        self.battlefield_rocks: list[str] = []
        self.has_forsaken = False
        self.has_lens = False
        self.burst_rocks_active: dict[str, bool] = {}  # name -> was cast this turn
        self.battlefield_baubles: list[str] = []  # land-fetch artifacts waiting to crack
        self.pending_lands: list[str] = []  # lands entering tapped (available next turn)
        self.mana_per_turn: list[int] = []

    def draw(self, n: int = 1):
        for _ in range(n):
            if self.library:
                self.hand.append(self.library.pop())

    def opening_hand_stats(self) -> dict:
        lands = sum(1 for c in self.hand if self._is_land(c))
        rocks = sum(1 for c in self.hand if c in ROCK_DEFS)
        fetchers = sum(1 for c in self.hand if c in LAND_FETCH_DEFS)
        return {"lands": lands, "rocks": rocks, "sources": lands + rocks + fetchers}

    def _is_land(self, name: str) -> bool:
        return name in _land_set

    def _land_priority(self, name: str) -> int:
        """Higher = play first."""
        # Scorched Ruins needs 2+ lands to sac
        if name == "Scorched Ruins":
            return 5 if len(self.battlefield_lands) >= 2 else -1

        # Tron-completing piece
        if name in TRON_PIECES:
            types_on_board = set()
            for l in self.battlefield_lands:
                if l in TRON_PIECES:
                    types_on_board.add(l)
                if l == "Planar Nexus":
                    types_on_board.update(TRON_PIECES)
            if name not in types_on_board and len(types_on_board) >= 2:
                return 10  # completing Tron

        # 2-mana lands
        if name in ("Eldrazi Temple", "Ugin's Labyrinth"):
            return 8

        # Planar Nexus (enables Tron with 1 piece)
        if name == "Planar Nexus":
            has_any_tron = any(l in TRON_PIECES for l in self.battlefield_lands)
            return 7 if has_any_tron else 4

        # Urza's Workshop scales with Urza lands
        if name == "Urza's Workshop":
            return 6

        # 0-mana utility lands are lowest
        if name in ZERO_MANA_LANDS:
            return 0

        return 3  # default 1-mana land

    def play_turn(self, turn_number: int) -> int:
        """Simulate one turn: untap, draw, play land, cast rocks/amplifiers, record mana.

        Returns pre-deployment available mana (after land drop, before casting rocks).
        """
        # Move pending lands (entered tapped last turn) to battlefield
        self.battlefield_lands.extend(self.pending_lands)
        self.pending_lands = []

        # Draw (skip on turn 1's draw since we have opening hand)
        if turn_number > 1:
            self.draw(1)

        # Mark burst rocks as no longer active
        for name in list(self.burst_rocks_active.keys()):
            self.burst_rocks_active[name] = False

        # Play best land from hand
        hand_lands = [(self._land_priority(c), c) for c in self.hand if self._is_land(c)]
        hand_lands.sort(reverse=True)

        for priority, land_name in hand_lands:
            if priority < 0:
                continue  # can't play (e.g. Scorched Ruins with <2 lands)
            self.hand.remove(land_name)
            if land_name == "Scorched Ruins":
                # Sacrifice 2 untapped lands
                sac_count = min(2, len(self.battlefield_lands))
                for _ in range(sac_count):
                    if self.battlefield_lands:
                        # Sac lowest-value land
                        worst = min(self.battlefield_lands,
                                    key=lambda l: land_base_mana(l, self.battlefield_lands, self.has_forsaken, self.has_lens))
                        self.battlefield_lands.remove(worst)
            self.battlefield_lands.append(land_name)
            break

        # Calculate available mana before casting (used for milestone checks)
        available = self._total_mana()
        pre_deployment = available

        # Try to cast rocks/amplifiers, highest value first
        castable = self._get_castable_from_hand(available)
        while castable:
            name, cmc = castable[0]
            available -= cmc
            self.hand.remove(name)
            if name in AMPLIFIER_DEFS:
                if name == "Forsaken Monument":
                    self.has_forsaken = True
                elif name == "Extraplanar Lens":
                    self.has_lens = True
                    # Exile a Wastes (imprint)
                    if "Wastes" in self.battlefield_lands:
                        self.battlefield_lands.remove("Wastes")
            elif name in ROCK_DEFS:
                self.battlefield_rocks.append(name)
                rock = ROCK_DEFS[name]
                if rock["burst"]:
                    self.burst_rocks_active[name] = True
                    # Burst rock produces mana immediately
                    available += rock_mana(name, self.has_forsaken)
                else:
                    # Non-burst rock can be tapped immediately
                    available += rock_mana(name, self.has_forsaken)
            castable = self._get_castable_from_hand(available)

        # Crack baubles on battlefield (costs 2, adds Wastes tapped — no mana this turn)
        for bname in list(self.battlefield_baubles):
            fetch = LAND_FETCH_DEFS[bname]
            if available >= fetch["crack_cost"]:
                available -= fetch["crack_cost"]
                self.battlefield_baubles.remove(bname)
                self.pending_lands.append(fetch["fetches"])

        # Deploy baubles from hand (costs 1, no immediate mana — investment)
        for card in list(self.hand):
            if card in LAND_FETCH_DEFS:
                fetch = LAND_FETCH_DEFS[card]
                if available >= fetch["cmc"]:
                    available -= fetch["cmc"]
                    self.hand.remove(card)
                    self.battlefield_baubles.append(card)

        # Record total mana available this turn (recalculate with all permanents)
        self.mana_per_turn.append(self._total_mana())
        return pre_deployment

    def _total_mana(self) -> int:
        """Calculate total mana from all sources."""
        total = 0
        for land in self.battlefield_lands:
            total += land_base_mana(land, self.battlefield_lands, self.has_forsaken, self.has_lens)

        for rock_name in self.battlefield_rocks:
            rock = ROCK_DEFS[rock_name]
            if rock["burst"]:
                # Only produces mana on cast turn
                if self.burst_rocks_active.get(rock_name, False):
                    total += rock_mana(rock_name, self.has_forsaken)
                # Basalt Monolith with Forsaken Monument: net +1/turn
                elif rock_name == "Basalt Monolith" and self.has_forsaken:
                    total += 1
            else:
                total += rock_mana(rock_name, self.has_forsaken)

        return total

    def _get_castable_from_hand(self, available_mana: int) -> list[tuple[str, int]]:
        """Return sorted list of castable rocks/amplifiers from hand."""
        castable = []
        for card in self.hand:
            if card in ROCK_DEFS:
                cmc = ROCK_DEFS[card]["cmc"]
                if cmc <= available_mana:
                    rock = ROCK_DEFS[card]
                    # Priority: output-per-cost ratio
                    ratio = rock["mana"] / max(cmc, 1)
                    castable.append((card, cmc, ratio))
            elif card in AMPLIFIER_DEFS:
                cmc = AMPLIFIER_DEFS[card]["cmc"]
                if cmc <= available_mana:
                    # Amplifiers get high priority (they boost future turns)
                    castable.append((card, cmc, 10.0))

        # Sort by ratio descending
        castable.sort(key=lambda x: x[2], reverse=True)
        return [(name, cmc) for name, cmc, _ in castable]


# Global set for fast land lookups (populated in main)
_land_set: set[str] = set()


def can_cast_from_hand(state: "GameState", available_mana: int, metadata: dict) -> list[str]:
    """Return list of castable non-rock, non-amplifier spells from hand."""
    castable = []
    for card in state.hand:
        if card in ROCK_DEFS or card in LAND_FETCH_DEFS or card in AMPLIFIER_DEFS or card in _land_set:
            continue
        meta = metadata.get(card, {})
        cmc = meta.get("cmc", 0)
        if not isinstance(cmc, (int, float)) or cmc == 0:
            continue
        if available_mana >= cmc:
            castable.append(card)
    return castable


def run_simulation(decklist: list[str], metadata: dict, num_games: int = NUM_GAMES) -> dict:
    """Run num_games simulations and collect stats."""
    global _land_set

    # Build land set from metadata
    _land_set = set()
    for name in set(decklist):
        meta = metadata.get(name, {})
        if "Land" in meta.get("type_line", ""):
            _land_set.add(name)

    # Stats collectors
    mana_by_turn = {t: [] for t in range(1, NUM_TURNS + 1)}
    hand_land_counts = Counter()
    hand_source_counts = Counter()
    mulligan_attempts = Counter()
    zhulodok_turns = []
    cascade_ready_turns = []
    t2_zhulodok = 0
    t3_zhulodok = 0

    # Castable spell tracking
    castable_spell_by_turn = {t: 0 for t in range(1, NUM_TURNS + 1)}
    curve_out_games = 0

    for _ in range(num_games):
        # Mulligan phase (Commander London mulligan)
        attempt = 0
        while True:
            state = GameState(decklist)
            state.draw(7)
            if should_mulligan(state.hand) and attempt < MAX_MULLIGANS:
                attempt += 1
                continue
            break

        # London mulligan: bottom cards if paid mulligan (attempt >= 2)
        # attempt 0 = kept first hand (7 cards)
        # attempt 1 = free mulligan (7 cards, no penalty)
        # attempt 2 = paid mulligan (bottom 1 → 6 cards)
        if attempt >= 2:
            bottom = choose_bottom_cards(state.hand, attempt - 1, metadata)
            for card in bottom:
                state.hand.remove(card)
                state.library.append(card)

        mulligan_attempts[attempt] += 1

        # Opening hand stats (on kept hand)
        hand_stats = state.opening_hand_stats()
        hand_land_counts[hand_stats["lands"]] += 1
        hand_source_counts[hand_stats["sources"]] += 1

        # Gemstone Caverns: if in opening hand, 50% chance of luck counter
        if "Gemstone Caverns" in state.hand:
            if random.random() < 0.5:  # not going first
                state.hand.remove("Gemstone Caverns")
                state.battlefield_lands.append("Gemstone Caverns")
                # Exile worst card (highest CMC non-land)
                if state.hand:
                    non_lands = [c for c in state.hand if not state._is_land(c)]
                    if non_lands:
                        worst = max(non_lands, key=lambda c: metadata.get(c, {}).get("cmc", 0))
                        state.hand.remove(worst)
                    elif state.hand:
                        state.hand.remove(state.hand[-1])

        # Simulate turns
        zhulodok_turn = None
        cascade_turn = None
        cast_every_turn = True
        for t in range(1, NUM_TURNS + 1):
            castable_mana = state.play_turn(t)
            mana_by_turn[t].append(state.mana_per_turn[-1])

            # Milestone checks use pre-deployment mana (what you could
            # actually spend on a spell instead of deploying rocks)
            if zhulodok_turn is None and castable_mana >= 6:
                zhulodok_turn = t
            if cascade_turn is None and castable_mana >= 7:
                cascade_turn = t

            # Castable spell check (use total board mana for "could I cast a spell")
            board_mana = state.mana_per_turn[-1]
            castable = can_cast_from_hand(state, board_mana, metadata)
            if castable:
                castable_spell_by_turn[t] += 1
            elif t <= 4:
                cast_every_turn = False

        if zhulodok_turn is not None:
            zhulodok_turns.append(zhulodok_turn)
            if zhulodok_turn <= 2:
                t2_zhulodok += 1
            if zhulodok_turn <= 3:
                t3_zhulodok += 1
        if cascade_turn is not None:
            cascade_ready_turns.append(cascade_turn)
        if cast_every_turn:
            curve_out_games += 1

    return {
        "mana_by_turn": mana_by_turn,
        "hand_land_counts": hand_land_counts,
        "hand_source_counts": hand_source_counts,
        "mulligan_attempts": mulligan_attempts,
        "zhulodok_turns": zhulodok_turns,
        "cascade_ready_turns": cascade_ready_turns,
        "t2_zhulodok": t2_zhulodok,
        "t3_zhulodok": t3_zhulodok,
        "castable_spell_by_turn": castable_spell_by_turn,
        "curve_out_games": curve_out_games,
    }



def print_static_analysis(decklist: list[str], metadata: dict, classified: dict) -> float:
    """Print pre-simulation static analysis. Returns avg CMC."""
    print("=" * 60)
    print("STATIC ANALYSIS — TITAN CONVERGENCE (BRACKET 4)")
    print("=" * 60)

    # Deck composition
    print(f"\n--- Deck Composition ---")
    print(f"Total cards (excl. commander): {len(decklist)}")
    print(f"Lands: {len(classified['lands'])}")
    print(f"Mana rocks: {len(classified['rocks'])}")
    print(f"Amplifiers: {len(classified['amplifiers'])}")
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
        if count > 0:
            bar = "#" * count
            print(f"    {cmc_val:>2} CMC: {count:>2} {bar}")

    # Mana source inventory
    lands = classified["lands"]
    land_counts = Counter(lands)

    two_plus_lands = []
    one_mana_lands = []
    zero_mana_lands = []
    special_lands = []

    for name in sorted(set(lands)):
        count = land_counts[name]
        suffix = f" x{count}" if count > 1 else ""
        if name in ZERO_MANA_LANDS:
            zero_mana_lands.append(f"    {name}{suffix}")
        elif name in ("Eldrazi Temple", "Ugin's Labyrinth", "Scorched Ruins") or name in TRON_PIECES:
            two_plus_lands.append(f"    {name}{suffix}")
        elif name in ("Planar Nexus", "Urza's Workshop", "Shrine of the Forsaken Gods", "Urza's Cave"):
            special_lands.append(f"    {name}{suffix}")
        else:
            one_mana_lands.append(f"    {name}{suffix}")

    print(f"\n--- Mana Source Inventory ---")
    print(f"  2+ mana lands ({len(two_plus_lands)}):")
    for line in two_plus_lands:
        print(line)
    print(f"  Conditional/scaling lands ({len(special_lands)}):")
    for line in special_lands:
        print(line)
    print(f"  1-mana lands ({len(one_mana_lands)}):")
    for line in one_mana_lands:
        print(line)
    if zero_mana_lands:
        print(f"  0-mana lands ({len(zero_mana_lands)}):")
        for line in zero_mana_lands:
            print(line)

    # Rock inventory
    rocks = classified["rocks"]
    rock_counts = Counter(rocks)
    print(f"\n  Mana rocks/fetchers ({len(rocks)}):")
    for name in sorted(set(rocks)):
        count = rock_counts[name]
        suffix = f" x{count}" if count > 1 else ""
        if name in ROCK_DEFS:
            r = ROCK_DEFS[name]
            tag = f"(CMC {r['cmc']}, +{r['mana']}{'⚡' if r['burst'] else ''})"
        elif name in LAND_FETCH_DEFS:
            f = LAND_FETCH_DEFS[name]
            tag = f"(CMC {f['cmc']}, crack {f['crack_cost']} → {f['fetches']})"
        else:
            tag = ""
        print(f"    {name}{suffix} {tag}")

    # Amplifiers
    if classified["amplifiers"]:
        print(f"\n  Amplifiers ({len(classified['amplifiers'])}):")
        for name in classified["amplifiers"]:
            print(f"    {name} (CMC {AMPLIFIER_DEFS[name]['cmc']})")

    # Land count heuristic (Frank Karsten adapted for Commander)
    # Count total mana sources: lands + rocks + fetchers
    rocks = classified["rocks"]
    total_sources = len(lands) + len(rocks)
    recommended = round(36 + (avg_cmc - 3.0) * 2)
    print(f"\n--- Mana Source Heuristic ---")
    print(f"  Avg CMC: {avg_cmc:.2f}")
    print(f"  Lands: {len(lands)}, Rocks/fetchers: {len(rocks)}, Total sources: {total_sources}")
    print(f"  Heuristic recommendation: ~{recommended} mana sources")
    if total_sources >= recommended:
        print(f"  Status: adequate ({total_sources} >= {recommended})")
    else:
        print(f"  Status: light ({total_sources} < {recommended}, delta = {recommended - total_sources})")

    return avg_cmc


def print_results(stats: dict, decklist: list[str], metadata: dict, classified: dict, avg_cmc: float):
    """Print simulation results."""
    total = NUM_GAMES

    print("\n" + "=" * 60)
    print(f"MONTE CARLO SIMULATION — TITAN CONVERGENCE ({NUM_GAMES:,} games, {NUM_TURNS} turns)")
    print("=" * 60)

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
    print(f"    Land count distribution:")
    for lands in range(8):
        count = stats["hand_land_counts"].get(lands, 0)
        if count > 0:
            bar = "#" * int(count / total * 50)
            print(f"      {lands} lands: {count/total*100:>5.1f}% {bar}")

    print(f"\n    Mana source count (lands + rocks + fetchers):")
    for sources in range(8):
        count = stats["hand_source_counts"].get(sources, 0)
        if count > 0:
            print(f"      {sources} sources: {count/total*100:>5.1f}%")

    # Dimension 2: Commander & Cascade Timing
    print(f"\n--- Dimension 2: Commander & Cascade Timing ---")

    print(f"\n  Commander castable (Zhulodok = 6 MV):")
    reached_z = len(stats["zhulodok_turns"])
    never_z = total - reached_z
    for t in range(2, NUM_TURNS + 1):
        count = sum(1 for zt in stats["zhulodok_turns"] if zt <= t)
        print(f"    By T{t}: {count/total*100:.1f}%")
    if reached_z:
        print(f"    Median (among {reached_z/total*100:.0f}% that reached): T{statistics.median(stats['zhulodok_turns']):.0f}")
    print(f"    Never by T{NUM_TURNS}: {never_z/total*100:.1f}%")

    print(f"\n  Cascade readiness (7+ mana):")
    for t in range(3, NUM_TURNS + 1):
        count = sum(1 for ct in stats["cascade_ready_turns"] if ct <= t)
        print(f"    By T{t}: {count/total*100:.1f}%")
    reached = len(stats["cascade_ready_turns"])
    never = total - reached
    if reached:
        print(f"    Median (among {reached/total*100:.0f}% that reached): T{statistics.median(stats['cascade_ready_turns']):.0f}")
    print(f"    Never by T{NUM_TURNS}: {never/total*100:.1f}%")

    # Dimension 3: Curve Efficiency
    print(f"\n--- Dimension 3: Curve Efficiency ---")

    print(f"\n  Castable spell from hand (non-rock/amplifier):")
    for t in range(1, NUM_TURNS + 1):
        pct = stats["castable_spell_by_turn"][t] / total * 100
        print(f"    T{t}: {pct:.1f}%")

    print(f"\n  Curve-out rate (cast something T1-T4): {stats['curve_out_games']/total*100:.1f}%")

    # Assessment
    print(f"\n--- Mana Base Assessment ---")
    med_t1 = statistics.median(stats["mana_by_turn"][1])
    med_t3 = statistics.median(stats["mana_by_turn"][3])
    med_t5 = statistics.median(stats["mana_by_turn"][5])
    med_last = statistics.median(stats["mana_by_turn"][NUM_TURNS])
    paid_mull_rate = mull.get(2, 0) / total * 100

    print(f"\n  Median mana: T1={med_t1:.0f}, T3={med_t3:.0f}, T5={med_t5:.0f}, T{NUM_TURNS}={med_last:.0f}")

    # Mana sources vs heuristic
    total_sources = len(classified["lands"]) + len(classified["rocks"])
    recommended = round(36 + (avg_cmc - 3.0) * 2)
    if total_sources >= recommended:
        print(f"  Mana sources: {total_sources} (adequate for avg CMC {avg_cmc:.2f})")
    else:
        print(f"  Mana sources: {total_sources} (light for avg CMC {avg_cmc:.2f}, heuristic suggests ~{recommended})")

    if paid_mull_rate < 5:
        print(f"  Paid mulligan rate: {paid_mull_rate:.1f}% — acceptable")
    else:
        print(f"  Paid mulligan rate: {paid_mull_rate:.1f}% — consider adding lands/rocks")

    t3_zhulodok_pct = stats["t3_zhulodok"] / total * 100
    if t3_zhulodok_pct > 50:
        print(f"  T3 Zhulodok: {t3_zhulodok_pct:.0f}% — strong acceleration")
    else:
        print(f"  T3 Zhulodok: {t3_zhulodok_pct:.0f}% — may want more fast mana")


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

    result = exporter.export_titan(metadata)
    if not exporter.validate_output(result, "titan-convergence"):
        raise ValueError("export_titan produced invalid simulation output")
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Monte Carlo mana base simulation for Titan Convergence (Zhulodok)")
    parser.add_argument("--json", action="store_true",
                        help="Write simulation.json instead of console output")
    args = parser.parse_args()

    with open(DECK_FILE) as f:
        deck_data = json.load(f)

    with open(METADATA_FILE) as f:
        metadata = json.load(f)

    print("Building Titan Convergence decklist...")
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

    avg_cmc = print_static_analysis(decklist, metadata, classified)

    n_workers = os.cpu_count() or 4
    chunk_size = NUM_GAMES // n_workers
    remainder = NUM_GAMES % n_workers
    chunks = [chunk_size + (1 if i < remainder else 0) for i in range(n_workers)]

    print(f"\nRunning {NUM_GAMES:,} game simulations ({n_workers} workers)...")
    with multiprocessing.Pool(n_workers) as pool:
        results = pool.map(_run_chunk, [(decklist, metadata, n) for n in chunks])
    stats = merge_stats(results)

    print_results(stats, decklist, metadata, classified, avg_cmc)
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
