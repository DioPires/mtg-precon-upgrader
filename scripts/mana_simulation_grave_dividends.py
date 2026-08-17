#!/usr/bin/env python3
"""Monte Carlo mana base simulation for Grave Dividends (Bartolomé del Presidio).

Simulates 100,000 games measuring mana production, color balance, and curve
efficiency turns 1-10 for the Bracket 4 Orzhov aristocrats sacrifice-loop decklist.

Commander: Bartolomé del Presidio ({W}{B}, CMC 2); a free, instant-speed, repeatable
sacrifice outlet. The sacrifice ability costs no mana, so the simulation only models
vanilla mana production and curve-out behavior (a 2-drop commander cast is the metric).
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
DECK_FILE = PROJECT_ROOT / "data" / "commanders" / "grave-dividends" / "deck.json"
METADATA_FILE = PROJECT_ROOT / "data" / "card-metadata.json"
JSON_OUTPUT = PROJECT_ROOT / "data" / "commanders" / "grave-dividends" / "simulation.json"

NUM_GAMES = 100_000
NUM_TURNS = 10

# --- Mana cost parser ---

def parse_mana_cost(mana_cost: str) -> dict:
    """Parse mana_cost string into pip breakdown.

    "{2}{W}{B}" -> {generic: 2, B: 1, W: 1, total: 4}
    "{B}{B}{B}" -> {generic: 0, B: 3, W: 0, total: 3}
    "{X}{B}{B}" -> {generic: 0, B: 2, W: 0, total: 2, X: True}

    Split cards (//): parse first half only.
    """
    if "//" in mana_cost:
        mana_cost = mana_cost.split("//")[0].strip()

    result = {"generic": 0, "B": 0, "W": 0, "total": 0, "X": False}
    symbols = re.findall(r"\{([^}]+)\}", mana_cost)
    for sym in symbols:
        if sym == "X":
            result["X"] = True
        elif sym.isdigit():
            result["generic"] += int(sym)
        elif sym == "B":
            result["B"] += 1
        elif sym == "W":
            result["W"] += 1
        # Ignore other symbols (hybrid, phyrexian, etc.)
    result["total"] = result["generic"] + result["B"] + result["W"]
    return result


# --- Rock definitions ---
# From Grave Dividends deck.json: Sol Ring, Arcane Signet, Talisman of Hierarchy,
# Orzhov Signet. Skullclamp is equipment (card-draw, not mana). No mana dorks.

ROCK_DEFS = {
    "Sol Ring":              {"cmc": 1, "B": 0, "W": 0, "C": 2, "burst": False},
    "Arcane Signet":         {"cmc": 2, "B": 1, "W": 1, "C": 0, "burst": False, "flexible": True},
    "Talisman of Hierarchy": {"cmc": 2, "B": 1, "W": 1, "C": 0, "burst": False, "flexible": True},
    "Orzhov Signet":         {"cmc": 2, "B": 1, "W": 1, "C": 0, "burst": False, "flexible": True},
}

# --- Mana dork definitions ---
# No mana dorks in Grave Dividends.

DORK_DEFS: dict = {}

# --- Creature ramp definitions ---
# No land-fetch creature ramp in Grave Dividends.

CREATURE_RAMP: dict = {}

# Placeholder retained for interface parity with the shared engine.
WIGHT_NAME = "__no_dork_placeholder__"

# --- Land definitions ---
# B-producing lands (includes flexible duals + fetches that hit a B source):
B_PRODUCING_LANDS = {
    "Swamp", "Godless Shrine", "Command Tower", "Isolated Chapel",
    "Concealed Courtyard", "Caves of Koilos", "Brightclimb Pathway",
    "Silent Clearing", "Takenuma, Abandoned Mire", "Witch's Cottage",
    "Bojuka Bog", "Castle Locthwain", "Dakmor Salvage", "Memorial to Folly",
    "Marsh Flats", "Bloodstained Mire", "Verdant Catacombs", "Polluted Delta",
}

# W-producing lands (includes flexible duals + Marsh Flats which can fetch Plains):
W_PRODUCING_LANDS = {
    "Plains", "Godless Shrine", "Command Tower", "Isolated Chapel",
    "Concealed Courtyard", "Caves of Koilos", "Brightclimb Pathway",
    "Silent Clearing", "Marsh Flats",
}

# Colorless-only utility lands:
C_ONLY_LANDS = {
    "High Market", "Volrath's Stronghold", "Conduit Pylons", "Mariposa Military Base",
}

# Lands with the Plains subtype (fetch targets, check-land untap conditions):
PLAINS_TYPED_LANDS = {"Plains", "Godless Shrine"}
# Lands with the Swamp subtype:
SWAMP_TYPED_LANDS = {"Swamp", "Godless Shrine", "Witch's Cottage"}

BASIC_PLAINS = {"Plains"}
BASIC_SWAMPS = {"Swamp"}


def build_decklist(deck_data: dict) -> list[str]:
    """Build the 99-card decklist for Grave Dividends."""
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
            # Front-face land detection (Dusk // Dawn is a Sorcery, not a land).
            front = type_line.split("//")[0]
            if "Land" in front:
                classified["lands"].append(name)
            else:
                classified["spells"].append(name)
    return classified


# --- Board state helpers ---

def count_basics(battlefield_lands: list[str]) -> int:
    return sum(1 for l in battlefield_lands if l in BASIC_PLAINS or l in BASIC_SWAMPS)


def land_enters_tapped(name: str, battlefield_lands: list[str], hand: list[str]) -> bool:
    """Determine if a land enters tapped given board + hand state."""
    other_count = len(battlefield_lands)

    # Unconditionally tapped utility / recursion lands.
    if name in {"Bojuka Bog", "Dakmor Salvage", "Memorial to Folly", "Witch's Cottage"}:
        # Witch's Cottage is untapped only with 3+ other Swamps — rare; model as tapped.
        return True

    if name == "Concealed Courtyard":
        # Fast land — untapped if you have <= 2 other lands.
        return other_count > 2

    if name == "Isolated Chapel":
        # Check land — untapped if you control a Plains or Swamp.
        has_p_or_s = any(l in PLAINS_TYPED_LANDS or l in SWAMP_TYPED_LANDS for l in battlefield_lands)
        return not has_p_or_s

    if name == "Castle Locthwain":
        # Untapped only if you control a Swamp.
        has_swamp = any(l in SWAMP_TYPED_LANDS for l in battlefield_lands)
        return not has_swamp

    # Godless Shrine (pay 2 life), Caves of Koilos, Silent Clearing, Brightclimb Pathway,
    # Command Tower, Takenuma, Volrath's Stronghold, High Market, Conduit Pylons,
    # Mariposa Military Base, basics: all enter untapped.
    return False


class ManaPool:
    """Tracks available B, W, C mana and flexible sources."""
    def __init__(self):
        self.B = 0
        self.W = 0
        self.C = 0
        self.flexible = 0  # can be B or W

    @property
    def total(self):
        return self.B + self.W + self.C + self.flexible

    def can_cast(self, pips: dict) -> bool:
        """Check if we can cast a spell with the given pip requirements."""
        need_B = pips["B"]
        need_W = pips["W"]
        need_generic = pips["generic"]

        avail_B = self.B
        avail_W = self.W
        avail_C = self.C
        avail_flex = self.flexible

        used_B = min(avail_B, need_B)
        remaining_B = need_B - used_B
        avail_B -= used_B

        used_W = min(avail_W, need_W)
        remaining_W = need_W - used_W
        avail_W -= used_W

        remaining_colored = remaining_B + remaining_W
        if avail_flex < remaining_colored:
            return False
        avail_flex -= remaining_colored

        leftover = avail_B + avail_W + avail_C + avail_flex
        return leftover >= need_generic

    def after_spending(self, pips: dict) -> "ManaPool":
        """Return a new ManaPool after spending pips. Assumes can_cast is True."""
        pool = ManaPool()
        pool.B = self.B
        pool.W = self.W
        pool.C = self.C
        pool.flexible = self.flexible

        need_B = pips["B"]
        need_W = pips["W"]
        need_generic = pips["generic"]

        from_B = min(pool.B, need_B)
        pool.B -= from_B
        need_B -= from_B

        from_W = min(pool.W, need_W)
        pool.W -= from_W
        need_W -= from_W

        flex_colored = need_B + need_W
        pool.flexible -= flex_colored

        remaining = need_generic
        from_C = min(pool.C, remaining)
        pool.C -= from_C
        remaining -= from_C

        from_B2 = min(pool.B, remaining)
        pool.B -= from_B2
        remaining -= from_B2

        from_W2 = min(pool.W, remaining)
        pool.W -= from_W2
        remaining -= from_W2

        from_flex = min(pool.flexible, remaining)
        pool.flexible -= from_flex

        return pool


def compute_land_mana(name: str, battlefield_lands: list[str]) -> tuple[int, int, int, int]:
    """Return (B, W, C, flexible) mana a single untapped land produces."""

    # C-only utility lands
    if name in {"High Market", "Volrath's Stronghold", "Conduit Pylons", "Mariposa Military Base"}:
        return (0, 0, 1, 0)

    # B-only lands
    if name in {"Bojuka Bog", "Castle Locthwain", "Memorial to Folly",
                "Witch's Cottage", "Dakmor Salvage", "Takenuma, Abandoned Mire"}:
        return (1, 0, 0, 0)

    # Fetches: should already be cracked; if somehow on board, treat as 0
    if name in {"Marsh Flats", "Bloodstained Mire", "Verdant Catacombs", "Polluted Delta"}:
        return (0, 0, 0, 0)

    # Dual / any-color lands (produce B or W -> flexible)
    if name in {
        "Godless Shrine", "Command Tower", "Isolated Chapel", "Concealed Courtyard",
        "Caves of Koilos", "Silent Clearing", "Brightclimb Pathway",
    }:
        return (0, 0, 0, 1)

    # Basic Plains
    if name == "Plains":
        return (0, 1, 0, 0)

    # Basic Swamp
    if name == "Swamp":
        return (1, 0, 0, 0)

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
        self.tapped_lands: set[int] = set()
        self.battlefield_rocks: list[str] = []
        self.battlefield_dorks: list[str] = []
        self.dorks_active: list[str] = []
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

        # Fetches: always play and crack immediately
        if name in {"Marsh Flats", "Bloodstained Mire", "Verdant Catacombs", "Polluted Delta"}:
            return 20

        if tapped:
            base = 0
        else:
            base = 10

        # Duals (flexible color) get bonus
        if name in B_PRODUCING_LANDS and name in W_PRODUCING_LANDS:
            base += 5
        elif name in B_PRODUCING_LANDS or name in W_PRODUCING_LANDS:
            base += 2

        return base

    def _resolve_fetch(self, fetch_name: str):
        """Resolve a fetch land: search library for a land card matching needed colors."""
        b_sources = sum(1 for l in self.battlefield_lands if l in B_PRODUCING_LANDS)
        w_sources = sum(1 for l in self.battlefield_lands if l in W_PRODUCING_LANDS)

        # Fetch valid targets per fetch name.
        # Marsh Flats: Plains or Swamp.  Bloodstained Mire: Swamp or Mountain (-> Swamp here).
        # Verdant Catacombs: Forest or Swamp (-> Swamp). Polluted Delta: Island or Swamp (-> Swamp).
        if fetch_name == "Marsh Flats":
            valid = SWAMP_TYPED_LANDS | PLAINS_TYPED_LANDS
        else:  # Bloodstained Mire / Verdant Catacombs / Polluted Delta
            valid = SWAMP_TYPED_LANDS

        fetchable = [(i, card) for i, card in enumerate(self.library) if card in valid]
        if not fetchable:
            return

        # Prefer Godless Shrine (both colors) early
        shrine = [(i, c) for i, c in fetchable if c == "Godless Shrine"]
        if shrine and len(self.battlefield_lands) <= 2:
            idx, card = shrine[0]
            self.library.pop(idx)
            self.battlefield_lands.append(card)
            return

        # Color need: fetch underrepresented color
        if b_sources <= w_sources:
            swamps = [(i, c) for i, c in fetchable if c == "Swamp"]
            if swamps:
                idx, card = swamps[0]
                self.library.pop(idx)
                self.battlefield_lands.append(card)
                return
        else:
            plains = [(i, c) for i, c in fetchable if c == "Plains"]
            if plains:
                idx, card = plains[0]
                self.library.pop(idx)
                self.battlefield_lands.append(card)
                return

        # Fallback: first fetchable target
        idx, card = fetchable[0]
        self.library.pop(idx)
        self.battlefield_lands.append(card)

    def compute_mana_pool(self) -> ManaPool:
        """Calculate total available mana from all untapped lands + rocks + dorks."""
        pool = ManaPool()

        for i, land in enumerate(self.battlefield_lands):
            if i in self.tapped_lands:
                continue
            b, w, c, f = compute_land_mana(land, self.battlefield_lands)
            pool.B += b
            pool.W += w
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
                    pool.W += rdef.get("W", 0)

        for dork in self.dorks_active:
            if dork in DORK_DEFS:
                ddef = DORK_DEFS[dork]
                if ddef.get("flexible"):
                    pool.flexible += 1
                else:
                    pool.B += ddef.get("B", 0)
                    pool.W += ddef.get("W", 0)

        return pool

    def play_turn(self, turn_number: int):
        """Simulate one turn."""
        if turn_number > 1:
            self.draw(1)

        # Untap all
        self.tapped_lands.clear()
        for name in list(self.burst_rocks_active.keys()):
            self.burst_rocks_active[name] = False

        self.dorks_active = list(self.battlefield_dorks)

        # Play best land from hand
        hand_lands = [(self._land_play_priority(c), c) for c in self.hand if self._is_land(c)]
        hand_lands.sort(reverse=True)

        if hand_lands:
            _, land_name = hand_lands[0]
            self.hand.remove(land_name)

            if land_name in {"Marsh Flats", "Bloodstained Mire", "Verdant Catacombs", "Polluted Delta"}:
                self._resolve_fetch(land_name)
            else:
                tapped = land_enters_tapped(land_name, self.battlefield_lands, self.hand)
                self.battlefield_lands.append(land_name)
                if tapped:
                    self.tapped_lands.add(len(self.battlefield_lands) - 1)

        # Calculate mana, try to cast rocks
        pool = self.compute_mana_pool()
        self._try_cast_ramp(pool)

        # Record final mana pool
        self.mana_per_turn.append(self.compute_mana_pool())

    def _try_cast_ramp(self, pool: ManaPool):
        """Try to cast mana rocks from hand, priority order."""
        priority_order = [
            ("rock", "Sol Ring"),
            ("rock", "Arcane Signet"),
            ("rock", "Talisman of Hierarchy"),
            ("rock", "Orzhov Signet"),
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
                            pool.W += rdef.get("W", 0)


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
        if pips["total"] == 0 and not pips["X"]:
            continue
        if pool.can_cast(pips):
            castable.append(card)
    return castable


# --- Simulation ---

def run_simulation(decklist: list[str], metadata: dict, num_games: int = NUM_GAMES) -> dict:
    """Run num_games simulations and collect stats."""
    land_set = set()
    for name in set(decklist):
        meta = metadata.get(name, {})
        front = meta.get("type_line", "").split("//")[0]
        if "Land" in front:
            land_set.add(name)

    mana_by_turn = {t: [] for t in range(1, NUM_TURNS + 1)}
    b_by_turn = {t: [] for t in range(1, NUM_TURNS + 1)}
    w_by_turn = {t: [] for t in range(1, NUM_TURNS + 1)}
    hand_land_counts = Counter()
    mulligan_attempts = Counter()

    zero_b_by_turn = {t: 0 for t in range(1, NUM_TURNS + 1)}
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
            total = pool.total
            b_avail = pool.B + pool.flexible
            w_avail = pool.W + pool.flexible

            mana_by_turn[t].append(total)
            b_by_turn[t].append(b_avail)
            w_by_turn[t].append(w_avail)

            if b_avail == 0:
                zero_b_by_turn[t] += 1
            if w_avail == 0:
                zero_w_by_turn[t] += 1

            # Commander castable: Bartolomé del Presidio {W}{B} = CMC 2, vanilla mana.
            cmd_pips = {"generic": 0, "B": 1, "W": 1}
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
        "w_by_turn": w_by_turn,
        "hand_land_counts": hand_land_counts,
        "mulligan_attempts": mulligan_attempts,
        "zero_b_by_turn": zero_b_by_turn,
        "zero_w_by_turn": zero_w_by_turn,
        "commander_castable_turn": commander_castable_turn,
        "commander_by_turn": commander_by_turn,
        "castable_spell_by_turn": castable_spell_by_turn,
        "curve_out_games": curve_out_games,
        "tapped_land_turns": tapped_land_turns,
    }


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

    result = exporter.export_grave_dividends(metadata)
    if not exporter.validate_output(result, "grave-dividends"):
        raise ValueError("export_grave_dividends produced invalid simulation output")
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Monte Carlo mana base simulation for Bartolomé del Presidio")
    parser.add_argument("--json", action="store_true",
                        help="Write simulation.json instead of console output")
    args = parser.parse_args()

    with open(DECK_FILE) as f:
        deck_data = json.load(f)
    with open(METADATA_FILE) as f:
        metadata = json.load(f)

    print("Building Grave Dividends decklist...")
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
    print(f"Commander by T2: {stats['commander_by_turn'][2]/total*100:.1f}%")
    print(f"Curve-out rate: {stats['curve_out_games']/total*100:.1f}%")


if __name__ == "__main__":
    main()
