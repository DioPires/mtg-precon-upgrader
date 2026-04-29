#!/usr/bin/env python3
"""Monte Carlo mana base simulation for The White Forge (Gandalf the White).

Simulates 100,000 games measuring mana production, color balance, and curve
efficiency turns 1-10 for the Bracket 4 mono-white artifact ETB/LTB decklist.

Commander: Gandalf the White ({3}{W}{W}, CMC 5)

Key mechanic modeled: Gandalf grants flash to legendary and artifact spells,
and doubles triggered abilities from legendary/artifact ETB/LTB. The flash
ability means we model instant-speed deployment but for mana sim purposes
this is equivalent to sorcery-speed casting (same mana requirement).
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
DECK_FILE = PROJECT_ROOT / "data" / "commanders" / "the-white-forge" / "deck.json"
METADATA_FILE = PROJECT_ROOT / "data" / "card-metadata.json"
JSON_OUTPUT = PROJECT_ROOT / "data" / "commanders" / "the-white-forge" / "simulation.json"

NUM_GAMES = 100_000
NUM_TURNS = 10

# --- Mana cost parser ---


def parse_mana_cost(mana_cost: str) -> dict:
    """Parse mana_cost string into pip breakdown.

    "{3}{W}{W}" -> {generic: 3, W: 2, total: 5}
    "{W}{W}" -> {generic: 0, W: 2, total: 2}

    Split cards (//): parse first half only.
    """
    if "//" in mana_cost:
        mana_cost = mana_cost.split("//")[0].strip()

    result = {"generic": 0, "W": 0, "total": 0, "X": False}
    symbols = re.findall(r"\{([^}]+)\}", mana_cost)
    for sym in symbols:
        if sym == "X":
            result["X"] = True
        elif sym.isdigit():
            result["generic"] += int(sym)
        elif sym == "W":
            result["W"] += 1
        # Ignore other symbols (hybrid, phyrexian, etc.)
    result["total"] = result["generic"] + result["W"]
    return result


# --- Rock definitions ---

ROCK_DEFS = {
    "Sol Ring":           {"cmc": 1, "C": 2, "burst": False},
    "Arcane Signet":      {"cmc": 2, "W": 1, "burst": False},
    "Mind Stone":         {"cmc": 2, "C": 1, "burst": False},
    "Thought Vessel":     {"cmc": 2, "C": 1, "burst": False},
    "Pearl Medallion":    {"cmc": 2, "C": 0, "burst": False},  # cost reducer, not mana
    "Basalt Monolith":    {"cmc": 3, "C": 3, "burst": False},  # doesn't untap normally, but sim treats all rocks as available each turn
}


# --- Cost reducer definitions ---
# These reduce artifact costs but don't produce mana directly
COST_REDUCERS = {
    "Foundry Inspector": {"cmc": 3, "reduction": 1, "applies_to": "artifact"},
    "Cloud Key":         {"cmc": 3, "reduction": 1, "applies_to": "artifact"},
    "Jhoira's Familiar": {"cmc": 4, "reduction": 1, "applies_to": "historic"},
    "Pearl Medallion":   {"cmc": 2, "reduction": 1, "applies_to": "white"},
}

# --- Land definitions ---

ARTIFACT_LANDS = {"Ancient Den", "Darksteel Citadel"}

ALWAYS_TAPPED = {"Emeria, the Sky Ruin", "Mistveil Plains"}


def land_enters_tapped(name: str, battlefield_lands: list[str]) -> bool:
    """Determine if a land enters tapped given board state."""
    if name in ALWAYS_TAPPED:
        return True

    # Monumental Henge: enters tapped unless you control a legendary creature
    # For sim purposes, assume untapped (Gandalf is often out before this matters)
    if name == "Monumental Henge":
        return False

    # Minas Tirith: enters tapped unless you control a legendary creature
    if name == "Minas Tirith":
        return False  # Same assumption as Henge

    return False


# --- Mana pool ---


class ManaPool:
    """Tracks available W and C mana.

    Simplified 2-bucket pool for mono-white:
    - W: white mana sources
    - C: colorless-only mana sources
    """

    def __init__(self):
        self.W = 0
        self.C = 0

    @property
    def total(self):
        return self.W + self.C

    def can_cast(self, pips: dict) -> bool:
        """Check if we can cast a spell with the given pip requirements."""
        need_W = pips.get("W", 0)
        need_generic = pips.get("generic", 0)
        if self.W < need_W:
            return False
        remaining_W = self.W - need_W
        return (remaining_W + self.C) >= need_generic

    def after_spending(self, pips: dict) -> "ManaPool":
        """Return a new ManaPool after spending pips. Assumes can_cast is True."""
        need_W = pips.get("W", 0)
        need_generic = pips.get("generic", 0)

        pool = ManaPool()
        pool.W = self.W - need_W
        pool.C = self.C

        # Spend generic from C first, then W
        from_C = min(pool.C, need_generic)
        pool.C -= from_C
        need_generic -= from_C
        pool.W -= need_generic

        return pool


def compute_land_mana(name: str) -> tuple[int, int]:
    """Return (W, C) mana production for an untapped land."""

    if name == "Plains":
        return (1, 0)

    if name == "Ancient Den":
        return (1, 0)  # Artifact land that taps for W

    if name == "Darksteel Citadel":
        return (0, 1)

    if name == "Eiganjo, Seat of the Empire":
        return (1, 0)

    if name == "Minas Tirith":
        return (1, 0)  # Legendary, taps for W

    if name == "Monumental Henge":
        return (1, 0)  # Taps for W (or 3 life + draw with WWW)

    if name == "Nykthos, Shrine to Nyx":
        return (0, 1)  # Default C; devotion ability modeled as C

    if name == "Emeria, the Sky Ruin":
        return (1, 0)

    if name == "Urza's Saga":
        return (0, 1)

    if name in {"Buried Ruin", "Inventors' Fair", "War Room", "Scavenger Grounds"}:
        return (0, 1)

    if name == "Mistveil Plains":
        return (1, 0)

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
    """Classify each card as land, rock, or spell."""
    ramp_names = set(ROCK_DEFS)
    classified = {"lands": [], "rocks": [], "spells": []}
    for name in decklist:
        if name in ramp_names:
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
    ramp_names = set(ROCK_DEFS)
    sources = sum(1 for c in hand if c in land_set or c in ramp_names)
    return sources <= 1


def choose_bottom_cards(hand: list[str], count: int, metadata: dict,
                        land_set: set[str]) -> list[str]:
    """Choose cards to bottom (London mulligan). Bottom highest CMC non-source cards."""
    ramp_names = set(ROCK_DEFS)
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
        self.metadata = metadata
        self.land_set = land_set
        self.mana_per_turn: list[ManaPool] = []
        self.mulligan_attempt = 0

        self.burst_rocks_active: dict[str, bool] = {}
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
        """Higher = play first. W-producing > utility lands."""
        tapped = land_enters_tapped(name, self.battlefield_lands)
        base = 0 if tapped else 10

        if name == "Plains":
            base += 5
        elif name == "Ancient Den":
            base += 5  # W-producing artifact land
        elif name == "Emeria, the Sky Ruin":
            base += 3  # W-producing but always tapped
        elif name == "Eiganjo, Seat of the Empire":
            base += 4
        elif name == "Minas Tirith":
            base += 4
        elif name == "Monumental Henge":
            base += 4
        elif name == "Nykthos, Shrine to Nyx":
            base += 3
        elif name == "Urza's Saga":
            base += 4
        elif name in {"Buried Ruin", "Inventors' Fair"}:
            base += 2
        elif name == "Mistveil Plains":
            base += 3  # W-producing but always tapped

        return base

    def compute_mana_pool(self) -> ManaPool:
        """Calculate total available mana from untapped lands + rocks."""
        pool = ManaPool()

        # Lands
        for i, land in enumerate(self.battlefield_lands):
            if i in self.tapped_lands:
                continue
            w, c = compute_land_mana(land)
            pool.W += w
            pool.C += c

        # Standard rocks
        for rock in self.battlefield_rocks:
            rdef = ROCK_DEFS.get(rock)
            if rdef:
                if rdef["burst"]:
                    if self.burst_rocks_active.get(rock, False):
                        pool.C += rdef.get("C", 0)
                        pool.W += rdef.get("W", 0)
                else:
                    pool.W += rdef.get("W", 0)
                    pool.C += rdef.get("C", 0)

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
        for idx in sorted(expired_indices, reverse=True):
            if idx < len(self.battlefield_lands) and self.battlefield_lands[idx] == "Urza's Saga":
                self.battlefield_lands.pop(idx)
                new_tapped = set()
                for ti in self.tapped_lands:
                    if ti > idx:
                        new_tapped.add(ti - 1)
                    elif ti < idx:
                        new_tapped.add(ti)
                self.tapped_lands = new_tapped
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

            tapped = land_enters_tapped(land_name, self.battlefield_lands)
            self.battlefield_lands.append(land_name)
            if tapped:
                self.tapped_lands.add(len(self.battlefield_lands) - 1)
            if land_name == "Urza's Saga":
                self.saga_play_turns[len(self.battlefield_lands) - 1] = turn_number

        # Cast ramp from hand
        pool = self.compute_mana_pool()
        self._try_cast_ramp(pool)

        # Record final mana pool
        self.mana_per_turn.append(self.compute_mana_pool())

    def _try_cast_ramp(self, pool: ManaPool):
        """Try to cast mana rocks from hand."""

        # Priority order for rocks
        rock_priority = [
            "Sol Ring",         # CMC 1, +2C
            "Arcane Signet",    # CMC 2, +1W
            "Mind Stone",       # CMC 2, +1C
            "Thought Vessel",   # CMC 2, +1C
            "Pearl Medallion",  # CMC 2, cost reducer
            "Basalt Monolith",  # CMC 3, +3C
        ]

        for rock_name in rock_priority:
            if rock_name not in self.hand:
                continue
            rdef = ROCK_DEFS[rock_name]
            rock_pips = {"generic": rdef["cmc"], "W": 0}
            if pool.can_cast(rock_pips):
                self.hand.remove(rock_name)
                self.battlefield_rocks.append(rock_name)
                pool = pool.after_spending(rock_pips)
                if rdef["burst"]:
                    self.burst_rocks_active[rock_name] = True
                    pool = self.compute_mana_pool()
                else:
                    pool = self.compute_mana_pool()


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
    ramp_cards = set(ROCK_DEFS)
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
        if "Land" in meta.get("type_line", ""):
            land_set.add(name)

    mana_by_turn = {t: [] for t in range(1, NUM_TURNS + 1)}
    w_by_turn = {t: [] for t in range(1, NUM_TURNS + 1)}
    hand_land_counts = Counter()
    mulligan_attempts = Counter()

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
            total_mana = pool.total
            w_avail = pool.W

            mana_by_turn[t].append(total_mana)
            w_by_turn[t].append(w_avail)

            if w_avail == 0:
                zero_w_by_turn[t] += 1

            # Commander: Gandalf the White {3}{W}{W}
            cmd_pips = {"generic": 3, "W": 2}
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
        "w_by_turn": w_by_turn,
        "hand_land_counts": hand_land_counts,
        "mulligan_attempts": mulligan_attempts,
        "zero_w_by_turn": zero_w_by_turn,
        "commander_castable_turn": commander_castable_turn,
        "commander_by_turn": commander_by_turn,
        "castable_spell_by_turn": castable_spell_by_turn,
        "curve_out_games": curve_out_games,
        "tapped_land_turns": tapped_land_turns,
    }


# --- Parallel execution ---


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


# --- JSON export helpers ---


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


def main():
    parser = argparse.ArgumentParser(
        description="Monte Carlo mana base simulation for The White Forge (Gandalf)")
    parser.add_argument("--json", action="store_true",
                        help="Write simulation.json instead of console output")
    args = parser.parse_args()

    with open(DECK_FILE) as f:
        deck_data = json.load(f)
    with open(METADATA_FILE) as f:
        metadata = json.load(f)

    print("Building Gandalf the White decklist...")
    decklist = build_decklist(deck_data)
    print(f"Decklist: {len(decklist)} cards")

    classified = classify_cards(decklist, metadata)

    if args.json:
        import export_simulation_results as exporter
        result = exporter.export_mono_white(metadata)
        if not exporter.validate_output(result, "the-white-forge"):
            raise ValueError("export_mono_white produced invalid simulation output")
        JSON_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        with open(JSON_OUTPUT, "w") as f:
            json.dump(result, f, indent=2)
        print(f"Written: {JSON_OUTPUT}")
        print(f"Size: {JSON_OUTPUT.stat().st_size / 1024:.1f} KB")
        return

    n_workers = os.cpu_count() or 4
    chunk_size = NUM_GAMES // n_workers
    remainder = NUM_GAMES % n_workers
    chunks = [chunk_size + (1 if i < remainder else 0) for i in range(n_workers)]

    print(f"Running {NUM_GAMES:,} game simulations ({n_workers} workers)...")
    with multiprocessing.Pool(n_workers) as pool:
        results = pool.map(_run_chunk, [(decklist, metadata, n) for n in chunks])
    stats = merge_stats(results)

    total = NUM_GAMES
    print(f"\n--- Results ({total:,} games) ---")

    # Quick summary
    for t in [3, 4, 5]:
        med = statistics.median(stats["mana_by_turn"][t])
        print(f"  T{t} median mana: {med:.0f}")

    mull = stats["mulligan_attempts"]
    print(f"  Kept first hand: {mull.get(0, 0)/total*100:.1f}%")

    cmd_by_t4 = stats["commander_by_turn"][4] / total * 100
    cmd_by_t5 = stats["commander_by_turn"][5] / total * 100
    print(f"  Commander by T4: {cmd_by_t4:.1f}%")
    print(f"  Commander by T5: {cmd_by_t5:.1f}%")

    if stats["commander_castable_turn"]:
        med = statistics.median(stats["commander_castable_turn"])
        print(f"  Commander median turn: {med:.1f}")


if __name__ == "__main__":
    main()
