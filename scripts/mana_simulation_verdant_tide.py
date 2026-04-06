#!/usr/bin/env python3
"""Monte Carlo mana base simulation for Verdant Tide (Eladamri, Korvecdal).

Simulates 100,000 games measuring mana production and curve efficiency
turns 1-10 for the Bracket 4 mono-green elfball decklist.

Commander: Eladamri, Korvecdal ({1}{G}{G}, CMC 3)

Key mechanic modeled: Eladamri lets you see and cast creatures from the
top of your library. Creature-on-top probability is tracked as a special
metric (topcast rate).
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
DECK_FILE = PROJECT_ROOT / "data" / "commanders" / "verdant-tide" / "deck.json"
METADATA_FILE = PROJECT_ROOT / "data" / "card-metadata.json"
JSON_OUTPUT = PROJECT_ROOT / "data" / "commanders" / "verdant-tide" / "simulation.json"

NUM_GAMES = 100_000
NUM_TURNS = 10

# --- Mana cost parser ---


def parse_mana_cost(mana_cost: str) -> dict:
    """Parse mana_cost string into pip breakdown.

    "{1}{G}{G}" -> {generic: 1, G: 2, total: 3}

    Split cards (//): parse first half only.
    """
    if "//" in mana_cost:
        mana_cost = mana_cost.split("//")[0].strip()

    result = {"generic": 0, "G": 0, "total": 0, "X": False}
    symbols = re.findall(r"\{([^}]+)\}", mana_cost)
    for sym in symbols:
        if sym == "X":
            result["X"] = True
        elif sym.isdigit():
            result["generic"] += int(sym)
        elif sym == "G":
            result["G"] += 1
        # Ignore other symbols (hybrid, phyrexian, etc.)
    result["total"] = result["generic"] + result["G"]
    return result


# --- Rock definitions ---

ROCK_DEFS = {
    "Sol Ring":       {"cmc": 1, "C": 2, "burst": False},
}

# --- Mana dork definitions ---
# Dorks produce mana from the turn AFTER they're cast (summoning sickness).
# Priest of Titania and Elvish Archdruid scale with elf count; modeled as
# producing 2G (conservative average with 2-3 other elves in play).

DORK_DEFS = {
    "Llanowar Elves":    {"cmc": 1, "pips": {"generic": 0, "G": 1}, "produces": 1},
    "Elvish Mystic":     {"cmc": 1, "pips": {"generic": 0, "G": 1}, "produces": 1},
    "Delighted Halfling": {"cmc": 1, "pips": {"generic": 0, "G": 1}, "produces": 1},
    "Priest of Titania":  {"cmc": 2, "pips": {"generic": 1, "G": 1}, "produces": 2},
    "Elvish Archdruid":  {"cmc": 3, "pips": {"generic": 1, "G": 2}, "produces": 2},
}

# --- Creature ramp definitions ---
# Creatures that fetch lands when cast or sacrificed.

CREATURE_RAMP = {
    "Sakura-Tribe Elder":  {"cmc": 2, "pips": {"generic": 1, "G": 1}, "fetch": "forest", "tapped": False},
}

# --- Sorcery ramp definitions ---

SORCERY_RAMP = {
    "Nature's Lore":  {"cmc": 2, "pips": {"generic": 1, "G": 1}, "fetch": "forest", "tapped": False},
    "Three Visits":   {"cmc": 2, "pips": {"generic": 1, "G": 1}, "fetch": "forest", "tapped": False},
}

# --- Land definitions ---

ALWAYS_TAPPED = {"Three Tree City"}  # ETB tapped unless you control a 6+ power commander


def land_enters_tapped(name: str, battlefield_lands: list[str]) -> bool:
    """Determine if a land enters tapped given board state."""
    if name in ALWAYS_TAPPED:
        return True
    return False


# --- Mana pool ---


class ManaPool:
    """Tracks available G and C mana for mono-green.

    Simplified 2-bucket pool:
    - G: green mana sources
    - C: colorless-only mana sources
    """

    def __init__(self):
        self.G = 0
        self.C = 0

    @property
    def total(self):
        return self.G + self.C

    def can_cast(self, pips: dict) -> bool:
        """Check if we can cast a spell with the given pip requirements."""
        need_G = pips.get("G", 0)
        need_generic = pips.get("generic", 0)
        if self.G < need_G:
            return False
        remaining_G = self.G - need_G
        return (remaining_G + self.C) >= need_generic

    def after_spending(self, pips: dict) -> "ManaPool":
        """Return a new ManaPool after spending pips. Assumes can_cast is True."""
        need_G = pips.get("G", 0)
        need_generic = pips.get("generic", 0)

        pool = ManaPool()
        pool.G = self.G - need_G
        pool.C = self.C

        # Spend generic from C first, then G
        from_C = min(pool.C, need_generic)
        pool.C -= from_C
        need_generic -= from_C
        pool.G -= need_generic

        return pool


def compute_land_mana(name: str) -> tuple[int, int]:
    """Return (G, C) mana production for an untapped land."""

    if name == "Forest":
        return (1, 0)

    if name == "Command Tower":
        return (1, 0)  # Mono-green: produces G

    if name == "The Shire":
        return (1, 0)  # Legendary land, taps for G

    if name == "Three Tree City":
        return (1, 0)  # Legendary land, taps for G

    if name == "Nykthos, Shrine to Nyx":
        return (1, 0)  # Conservative: devotion activation yields G in mono-green

    if name in {"Rogue's Passage", "Bonders' Enclave"}:
        return (0, 1)

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

    Rocks include mana rocks and mana dorks (both are ramp).
    """
    ramp_names = set(ROCK_DEFS) | set(DORK_DEFS)
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
    """Mulligan if 0-1 mana sources (lands + rocks + dorks)."""
    ramp_names = set(ROCK_DEFS) | set(DORK_DEFS)
    sources = sum(1 for c in hand if c in land_set or c in ramp_names)
    return sources <= 1


def choose_bottom_cards(hand: list[str], count: int, metadata: dict,
                        land_set: set[str]) -> list[str]:
    """Choose cards to bottom (London mulligan). Bottom highest CMC non-source cards."""
    ramp_names = set(ROCK_DEFS) | set(DORK_DEFS)
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
        self.battlefield_dorks: list[str] = []  # dorks on battlefield (summoning sick)
        self.dorks_active: list[str] = []  # dorks that can tap for mana this turn
        self.metadata = metadata
        self.land_set = land_set
        self.mana_per_turn: list[ManaPool] = []
        self.mulligan_attempt = 0
        self.burst_rocks_active: dict[str, bool] = {}

    def draw(self, n: int = 1):
        for _ in range(n):
            if self.library:
                self.hand.append(self.library.pop())

    def count_lands_in_hand(self) -> int:
        return sum(1 for c in self.hand if c in self.land_set)

    def _is_land(self, name: str) -> bool:
        return name in self.land_set

    def _land_play_priority(self, name: str) -> float:
        """Higher = play first. Untapped G-producing > utility lands."""
        tapped = land_enters_tapped(name, self.battlefield_lands)
        base = 0 if tapped else 10

        if name == "Forest":
            base += 5
        elif name == "Command Tower":
            base += 5
        elif name == "The Shire":
            base += 4
        elif name == "Three Tree City":
            base += 4
        elif name == "Nykthos, Shrine to Nyx":
            base += 3  # High-value mana land in devotion-heavy deck
        elif name in {"Rogue's Passage", "Bonders' Enclave"}:
            base += 1

        return base

    def _fetch_forest(self, enters_tapped: bool):
        """Fetch a Forest from library and put on battlefield."""
        targets = [i for i, c in enumerate(self.library) if c == "Forest"]
        if targets:
            idx = targets[0]
            card = self.library.pop(idx)
            self.battlefield_lands.append(card)
            if enters_tapped:
                self.tapped_lands.add(len(self.battlefield_lands) - 1)

    def compute_mana_pool(self) -> ManaPool:
        """Calculate total available mana from untapped lands + rocks + dorks."""
        pool = ManaPool()

        # Lands
        for i, land in enumerate(self.battlefield_lands):
            if i in self.tapped_lands:
                continue
            g, c = compute_land_mana(land)
            pool.G += g
            pool.C += c

        # Standard rocks
        for rock in self.battlefield_rocks:
            rdef = ROCK_DEFS.get(rock)
            if rdef:
                if rdef["burst"]:
                    if self.burst_rocks_active.get(rock, False):
                        pool.C += rdef.get("C", 0)
                        pool.G += rdef.get("G", 0)
                else:
                    pool.G += rdef.get("G", 0)
                    pool.C += rdef.get("C", 0)

        # Active dorks (summoning sickness resolved)
        for dork in self.dorks_active:
            ddef = DORK_DEFS.get(dork)
            if ddef:
                pool.G += ddef["produces"]

        return pool

    def play_turn(self, turn_number: int):
        """Simulate one turn."""
        if turn_number > 1:
            self.draw(1)

        # Untap all
        self.tapped_lands.clear()
        for name in list(self.burst_rocks_active.keys()):
            self.burst_rocks_active[name] = False

        # Activate dorks from previous turn (summoning sickness resolved)
        self.dorks_active = list(self.battlefield_dorks)

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

        # Cast ramp from hand
        pool = self.compute_mana_pool()
        self._try_cast_ramp(pool)

        # Record final mana pool
        self.mana_per_turn.append(self.compute_mana_pool())

    def _try_cast_ramp(self, pool: ManaPool):
        """Try to cast ramp from hand in priority order.

        Priority: Sol Ring > 1-CMC dorks > 2-CMC sorcery ramp >
        Priest of Titania > Sakura-Tribe Elder > Elvish Archdruid
        """
        priority_order = [
            ("rock", "Sol Ring"),
            ("dork", "Llanowar Elves"),
            ("dork", "Elvish Mystic"),
            ("dork", "Delighted Halfling"),
            ("sorcery_ramp", "Nature's Lore"),
            ("sorcery_ramp", "Three Visits"),
            ("dork", "Priest of Titania"),
            ("creature_ramp", "Sakura-Tribe Elder"),
            ("dork", "Elvish Archdruid"),
        ]

        for ramp_type, name in priority_order:
            if name not in self.hand:
                continue

            if ramp_type == "rock":
                rdef = ROCK_DEFS[name]
                rock_pips = {"generic": rdef["cmc"], "G": 0}
                if pool.can_cast(rock_pips):
                    self.hand.remove(name)
                    self.battlefield_rocks.append(name)
                    pool = pool.after_spending(rock_pips)
                    if rdef["burst"]:
                        self.burst_rocks_active[name] = True
                    pool = self.compute_mana_pool()

            elif ramp_type == "dork":
                ddef = DORK_DEFS[name]
                pips = ddef["pips"]
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
                    self._fetch_forest(cramp["tapped"])

            elif ramp_type == "sorcery_ramp":
                sramp = SORCERY_RAMP[name]
                pips = sramp["pips"]
                if pool.can_cast(pips):
                    pool = pool.after_spending(pips)
                    self.hand.remove(name)
                    self._fetch_forest(sramp["tapped"])


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
    ramp_cards = set(ROCK_DEFS) | set(DORK_DEFS) | set(CREATURE_RAMP) | set(SORCERY_RAMP)
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
    g_by_turn = {t: [] for t in range(1, NUM_TURNS + 1)}
    hand_land_counts = Counter()
    mulligan_attempts = Counter()

    zero_g_by_turn = {t: 0 for t in range(1, NUM_TURNS + 1)}

    commander_castable_turn = []
    commander_by_turn = {t: 0 for t in range(1, NUM_TURNS + 1)}

    castable_spell_by_turn = {t: 0 for t in range(1, NUM_TURNS + 1)}
    curve_out_games = 0

    tapped_land_turns = {1: 0, 2: 0}

    # Eladamri-specific: creature on top of library after each turn
    creature_on_top_by_turn = {t: 0 for t in range(1, NUM_TURNS + 1)}

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
            g_avail = pool.G

            mana_by_turn[t].append(total_mana)
            g_by_turn[t].append(g_avail)

            if g_avail == 0:
                zero_g_by_turn[t] += 1

            # Commander: Eladamri, Korvecdal {1}{G}{G}
            cmd_pips = {"generic": 1, "G": 2}
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

            # Check creature on top of library (Eladamri topcast ability)
            if state.library:
                top_card = state.library[-1]
                top_meta = metadata.get(top_card, {})
                top_type = top_meta.get("type_line", "")
                if "Creature" in top_type:
                    creature_on_top_by_turn[t] += 1

        if cmd_cast_turn is not None:
            commander_castable_turn.append(cmd_cast_turn)
            for future_t in range(cmd_cast_turn + 1, NUM_TURNS + 1):
                commander_by_turn[future_t] += 1

        if cast_every_turn:
            curve_out_games += 1

    return {
        "mana_by_turn": mana_by_turn,
        "g_by_turn": g_by_turn,
        "hand_land_counts": hand_land_counts,
        "mulligan_attempts": mulligan_attempts,
        "zero_g_by_turn": zero_g_by_turn,
        "commander_castable_turn": commander_castable_turn,
        "commander_by_turn": commander_by_turn,
        "castable_spell_by_turn": castable_spell_by_turn,
        "curve_out_games": curve_out_games,
        "tapped_land_turns": tapped_land_turns,
        "creature_on_top_by_turn": creature_on_top_by_turn,
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


# --- Main ---


def main():
    parser = argparse.ArgumentParser(
        description="Monte Carlo mana base simulation for Verdant Tide (Eladamri)")
    parser.add_argument("--json", action="store_true",
                        help="Write simulation.json instead of console output")
    args = parser.parse_args()

    with open(DECK_FILE) as f:
        deck_data = json.load(f)
    with open(METADATA_FILE) as f:
        metadata = json.load(f)

    print("Building Verdant Tide decklist...")
    decklist = build_decklist(deck_data)
    print(f"Decklist: {len(decklist)} cards")

    classify_cards(decklist, metadata)

    if args.json:
        import export_simulation_results as exporter
        result = exporter.export_verdant_tide(metadata)
        if not exporter.validate_output(result, "verdant-tide"):
            raise ValueError("export_verdant_tide produced invalid simulation output")
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
    for t in [2, 3, 4]:
        med = statistics.median(stats["mana_by_turn"][t])
        print(f"  T{t} median mana: {med:.0f}")

    mull = stats["mulligan_attempts"]
    print(f"  Kept first hand: {mull.get(0, 0)/total*100:.1f}%")

    cmd_by_t2 = stats["commander_by_turn"][2] / total * 100
    cmd_by_t3 = stats["commander_by_turn"][3] / total * 100
    print(f"  Commander by T2: {cmd_by_t2:.1f}%")
    print(f"  Commander by T3: {cmd_by_t3:.1f}%")

    if stats["commander_castable_turn"]:
        med = statistics.median(stats["commander_castable_turn"])
        print(f"  Commander median turn: {med:.1f}")

    print(f"\n  Creature on top of library (Eladamri topcast rate):")
    for t in [1, 2, 3, 4, 5]:
        pct = stats["creature_on_top_by_turn"][t] / total * 100
        print(f"    T{t}: {pct:.1f}%")


if __name__ == "__main__":
    main()
