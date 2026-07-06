#!/usr/bin/env python3
"""Monte Carlo mana base simulation for Tidal Legion (Namor the Sub-Mariner).

Simulates games measuring mana production and curve efficiency turns 1-10
for the Bracket 3+ mono-blue spellslinger Merfolk-tokens decklist.

Commander: Namor the Sub-Mariner ({1}{U}{U}, CMC 3). His token trigger
(one 1/1 Merfolk per blue pip on noncreature spells) is a board engine, not
a mana engine — the mana sim treats Namor as a CMC-3 commander only; the
token clock is modeled in the goldfish layer (DEC-404).

Mono-U rock-based ramp profile (v1.2, DEC-401): Arcane Signet, Thought
Vessel, Mind Stone, Commander's Sphere, Patchwork Banner. Sapphire Medallion
is a cost reducer, not a mana source (informational only, matching the
Zada/Pyre convention). Hydro-Channeler's spell-restricted dork mana and
Lórien Revealed's islandcycling are not modeled — both are minor against a
36-land base (34 real + Three Tree City + Sink into Stupor MDFC), and
omitting them keeps the estimate conservative.
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
DECK_FILE = PROJECT_ROOT / "data" / "commanders" / "tidal-legion" / "deck.json"
METADATA_FILE = PROJECT_ROOT / "data" / "card-metadata.json"
JSON_OUTPUT = PROJECT_ROOT / "data" / "commanders" / "tidal-legion" / "simulation.json"

NUM_GAMES = 100_000
NUM_TURNS = 10


# --- Mana cost parser ---

def parse_mana_cost(mana_cost: str) -> dict:
    """Parse mana_cost string into pip breakdown.

    "{1}{U}{U}" -> {generic: 1, U: 2, total: 3}
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
# v1.2 (DEC-401): Worn Powerstone, Basalt Monolith, and Everflowing Chalice
# are all cut. Commander's Sphere and Patchwork Banner tap for {U} (Sphere is
# any-CI-color; Banner is any color).

ROCK_DEFS = {
    "Arcane Signet":      {"cmc": 2, "U": 1, "C": 0, "burst": False},
    "Thought Vessel":     {"cmc": 2, "U": 0, "C": 1, "burst": False},
    "Mind Stone":         {"cmc": 2, "U": 0, "C": 1, "burst": False},
    "Commander's Sphere": {"cmc": 3, "U": 1, "C": 0, "burst": False},
    "Patchwork Banner":   {"cmc": 3, "U": 1, "C": 0, "burst": False},
}


# --- Cost reducer definitions ---
# Reduce cost but don't directly produce mana. Informational only.

COST_REDUCERS = {
    "Sapphire Medallion": {"cmc": 2, "reduction": 1, "applies_to": "blue"},
}


# --- Land definitions ---

# Lands that enter tapped unconditionally
ALWAYS_TAPPED: set[str] = {"Lonely Sandbar", "Sink into Stupor // Soporific Springs"}

# Conditional-tapped lands evaluated dynamically in land_enters_tapped()

# Static mana production for each named land (U, C). Lands that need
# board-state queries are handled inline in compute_land_mana().
U_LANDS = {
    "Island", "Mystic Sanctuary", "Rivendell", "Lonely Sandbar",
    "Cephalid Coliseum", "Seat of the Synod",
    "Sink into Stupor // Soporific Springs",
}

C_ONLY_LANDS = {
    "Fountainport", "Reliquary Tower", "Command Beacon", "Ash Barrens",
    "Three Tree City",
}

# Lands with the Island subtype (Mystic Sanctuary's own condition counts
# "other Islands", not other lands).
ISLAND_SUBTYPE = {"Island", "Mystic Sanctuary"}


def land_enters_tapped(name: str, battlefield_lands: list[str],
                       commander_in_play: bool) -> bool:
    """Determine if a land enters tapped given board state."""
    if name in ALWAYS_TAPPED:
        return True

    # Mystic Sanctuary: ETBs tapped unless you control 3+ other Islands.
    if name == "Mystic Sanctuary":
        islands = sum(1 for l in battlefield_lands if l in ISLAND_SUBTYPE)
        return islands < 3

    # Rivendell: ETBs tapped unless you control a legendary creature.
    # Commander-in-play is the dominant case (Namor median ~T3); the deck's
    # other legends (Svyelun, Kopala, Kiora, Deekah) are not tracked.
    if name == "Rivendell":
        return not commander_in_play

    # Everything else (basics, Seat of the Synod, Cephalid Coliseum,
    # Fountainport, Reliquary Tower, Command Beacon, Ash Barrens): untapped.
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
        need_U = pips.get("U", 0)
        need_generic = pips.get("generic", 0)
        if self.U < need_U:
            return False
        remaining_U = self.U - need_U
        return (remaining_U + self.C) >= need_generic

    def after_spending(self, pips: dict) -> "ManaPool":
        need_U = pips.get("U", 0)
        need_generic = pips.get("generic", 0)

        pool = ManaPool()
        pool.U = self.U - need_U
        pool.C = self.C

        from_C = min(pool.C, need_generic)
        pool.C -= from_C
        need_generic -= from_C
        pool.U -= need_generic
        return pool


def compute_land_mana(name: str) -> tuple[int, int]:
    """Return (U, C) mana production for an untapped land."""

    if name in U_LANDS:
        return (1, 0)

    # Fountainport, Reliquary Tower, Command Beacon, Ash Barrens: {C}
    return (0, 1)


# --- Decklist builder ---

def build_decklist(deck_data: dict) -> list[str]:
    """Build the 99-card decklist."""
    cards = []
    for card in deck_data["decklist"]:
        qty = card.get("quantity", 1)
        cards.extend([card["name"]] * qty)
    return cards


def is_land_card(type_line: str) -> bool:
    """Treat MDFCs by their front face only (split on //).
    Catches cases like 'Dirgur Focusmage // Braingeyser' (front = Creature).
    """
    front = type_line.split("//")[0].strip() if "//" in type_line else type_line
    return "Land" in front


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
            if is_land_card(type_line):
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
    """London mulligan bottom — highest CMC non-source cards."""
    ramp_names = set(ROCK_DEFS)
    candidates = [c for c in hand if c not in land_set and c not in ramp_names]
    candidates.sort(key=lambda c: metadata.get(c, {}).get("cmc", 0), reverse=True)
    return candidates[:count]


# --- Engine pieces (token/spell payoff permanents) ---
# Battlefield engines that convert spell velocity and the token swarm into
# cards and damage. Tracking these is informational, not used in mana modeling.

ENGINE_PAYOFFS = {
    "Curiosity Crafter", "Bident of Thassa", "Archmage Emeritus",
    "Deekah, Fractal Theorist", "Shark Typhoon",
    "Deeproot Pilgrimage",
    "Faerie Mastermind", "Kindred Discovery", "Lullmage Mentor",
    "Hullbreaker Horror", "Roaming Throne",
}


# --- Game state ---

class GameState:
    def __init__(self, decklist: list[str], metadata: dict, land_set: set[str]):
        self.library = list(decklist)
        random.shuffle(self.library)
        self.hand: list[str] = []
        self.battlefield_lands: list[str] = []
        self.tapped_lands: set[int] = set()
        self.battlefield_rocks: list[str] = []
        self.battlefield_payoffs: set[str] = set()
        self.commander_in_play = False
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
        """Higher = play first. Untapped U > untapped C > tapped lands."""
        tapped = land_enters_tapped(name, self.battlefield_lands, self.commander_in_play)
        base = 0 if tapped else 10
        if name == "Island":
            base += 5
        elif name in U_LANDS:
            base += 4
        elif name in C_ONLY_LANDS:
            base += 2
        return base

    def compute_mana_pool(self) -> ManaPool:
        pool = ManaPool()
        for i, land in enumerate(self.battlefield_lands):
            if i in self.tapped_lands:
                continue
            u, c = compute_land_mana(land)
            pool.U += u
            pool.C += c

        for rock in self.battlefield_rocks:
            rdef = ROCK_DEFS.get(rock)
            if rdef:
                pool.U += rdef.get("U", 0)
                pool.C += rdef.get("C", 0)
        return pool

    def play_turn(self, turn_number: int):
        if turn_number > 1:
            self.draw(1)

        # Untap all
        self.tapped_lands.clear()

        # Play best land from hand
        hand_lands = [(self._land_play_priority(c), c) for c in self.hand if self._is_land(c)]
        hand_lands.sort(reverse=True)

        if hand_lands:
            _, land_name = hand_lands[0]
            self.hand.remove(land_name)

            tapped = land_enters_tapped(land_name, self.battlefield_lands, self.commander_in_play)
            self.battlefield_lands.append(land_name)
            if tapped:
                self.tapped_lands.add(len(self.battlefield_lands) - 1)

        # Cast ramp from hand
        pool = self.compute_mana_pool()
        self._try_cast_ramp(pool)

        # Cast commander if available (Namor {1}{U}{U} = 3 mana, 2 U pips)
        pool = self.compute_mana_pool()
        if not self.commander_in_play and pool.can_cast({"generic": 1, "U": 2}):
            self.commander_in_play = True

        # Track payoffs on battlefield (assume played when castable on hand)
        pool = self.compute_mana_pool()
        for card in list(self.hand):
            if card in ENGINE_PAYOFFS and card not in self.battlefield_payoffs:
                mc = self.metadata.get(card, {}).get("mana_cost", "")
                if mc:
                    pips = parse_mana_cost(mc)
                    if pool.can_cast(pips):
                        self.battlefield_payoffs.add(card)
                        pool = pool.after_spending(pips)

        # Record final mana pool
        self.mana_per_turn.append(self.compute_mana_pool())

    def _try_cast_ramp(self, pool: ManaPool):
        """Cast mana rocks from hand in priority order (cheap first)."""
        rock_priority = ["Arcane Signet", "Thought Vessel", "Mind Stone",
                         "Everflowing Chalice", "Worn Powerstone", "Basalt Monolith"]
        for rock_name in rock_priority:
            if rock_name not in self.hand:
                continue
            rdef = ROCK_DEFS[rock_name]
            rock_pips = {"generic": rdef["cmc"], "U": 0}
            if pool.can_cast(rock_pips):
                self.hand.remove(rock_name)
                self.battlefield_rocks.append(rock_name)
                pool = pool.after_spending(rock_pips)
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
    """Return castable non-ramp spells from hand."""
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

def run_simulation(decklist: list[str], metadata: dict,
                   num_games: int = NUM_GAMES) -> dict:
    """Run num_games simulations and collect stats."""
    land_set = set()
    for name in set(decklist):
        meta = metadata.get(name, {})
        if is_land_card(meta.get("type_line", "")):
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

    # Engine readiness: % games with 2+ token/spell payoff permanents out.
    engine_ready_by_turn = {t: 0 for t in range(1, NUM_TURNS + 1)}

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

            # Commander: Namor the Sub-Mariner {1}{U}{U} = CMC 3
            cmd_pips = {"generic": 1, "U": 2}
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

            # Track engine-readiness on this turn
            if len(state.battlefield_payoffs) >= 2:
                engine_ready_by_turn[t] += 1

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
        "engine_ready_by_turn": engine_ready_by_turn,
    }


# --- Parallel ---

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
    """Reuse the bulk exporter path so the JSON stays schema-compatible."""
    import sys
    sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
    import export_simulation_results as exporter

    result = exporter.export_tidal_legion(metadata)
    if not exporter.validate_output(result, "tidal-legion"):
        raise ValueError("export_tidal_legion produced invalid simulation output")
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Monte Carlo mana base simulation for Tidal Legion (Namor)")
    parser.add_argument("--json", action="store_true",
                        help="Write simulation.json instead of console output")
    parser.add_argument("--games", type=int, default=NUM_GAMES,
                        help=f"Number of games (default: {NUM_GAMES})")
    args = parser.parse_args()

    with open(DECK_FILE) as f:
        deck_data = json.load(f)
    with open(METADATA_FILE) as f:
        metadata = json.load(f)

    print("Building Tidal Legion decklist...")
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

    num_games = args.games
    n_workers = os.cpu_count() or 4
    chunk_size = num_games // n_workers
    remainder = num_games % n_workers
    chunks = [chunk_size + (1 if i < remainder else 0) for i in range(n_workers)]

    print(f"\nRunning {num_games:,} game simulations ({n_workers} workers)...")
    with multiprocessing.Pool(n_workers) as pool:
        results = pool.map(_run_chunk, [(decklist, metadata, n) for n in chunks])
    stats = merge_stats(results)

    total = num_games
    print(f"\nMana medians: " + ", ".join(
        f"T{t}={statistics.median(stats['mana_by_turn'][t]):.0f}" for t in range(1, NUM_TURNS + 1)
    ))
    print(f"Commander by T2: {stats['commander_by_turn'][2]/total*100:.1f}%")
    print(f"Commander by T3: {stats['commander_by_turn'][3]/total*100:.1f}%")
    print(f"Commander by T4: {stats['commander_by_turn'][4]/total*100:.1f}%")
    print(f"Zero-U by T2: {stats['zero_u_by_turn'][2]/total*100:.1f}%")
    print(f"Curve-out rate: {stats['curve_out_games']/total*100:.1f}%")
    print(f"Engine ready (2+ payoffs) by T6: {stats['engine_ready_by_turn'][6]/total*100:.1f}%")


if __name__ == "__main__":
    main()
