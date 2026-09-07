#!/usr/bin/env python3
"""Monte Carlo mana base simulation for Anvil Chorus (Fíli the Pathfinder).

Simulates 100,000 games measuring mana production, color balance, and curve
efficiency turns 1-10 for the Bracket 4- mono-white Dwarf ETB/token decklist.

Commander: Fíli the Pathfinder ({3}{W}, CMC 4)

Manabase model notes (DEC-686 board-approved 38-land plan):
- 36 real lands plus 3 pay-life modal MDFCs (Emeria's Call, Witch Enchanter,
  Razorgrass Ambush). The MDFCs are classified as lands and modeled entering
  untapped (their back faces enter untapped for 3 life; the sim does not track
  life). This matches the deck's "39 land-playable cards" design intent.
- Castle Ardenvale enters untapped once a Plains is on the battlefield
  (29 Plains in the deck — nearly always true from turn 2).
- Minas Tirith enters tapped unless you control a legendary creature; the sim
  proxies that with "fewer than 2 lands on battlefield = tapped" (the deck's
  14 legendaries include several 1-3 drops, so the condition is usually met
  from turn 3 on).
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
DECK_FILE = PROJECT_ROOT / "data" / "commanders" / "anvil-chorus" / "deck.json"
METADATA_FILE = PROJECT_ROOT / "data" / "card-metadata.json"
JSON_OUTPUT = PROJECT_ROOT / "data" / "commanders" / "anvil-chorus" / "simulation.json"

NUM_GAMES = 100_000
NUM_TURNS = 10

# --- Mana cost parser ---


def parse_mana_cost(mana_cost: str) -> dict:
    """Parse mana_cost string into pip breakdown.

    "{3}{W}" -> {generic: 3, W: 1, total: 4}
    "{W}{W}" -> {generic: 0, W: 2, total: 2}

    Split/adventure/MDFC cards (//): parse first half only.
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
    "Sol Ring":      {"cmc": 1, "C": 2, "burst": False},
    "Arcane Signet": {"cmc": 2, "W": 1, "burst": False},
}


# --- Land definitions ---

ALWAYS_TAPPED = {"Emeria, the Sky Ruin", "Windbrisk Heights"}

# Pay-life MDFCs: back face enters untapped for 3 life (life untracked in sim).
MDFC_LANDS = {
    "Emeria's Call // Emeria, Shattered Skyclave",
    "Witch Enchanter // Witch-Blessed Meadow",
    "Razorgrass Ambush // Razorgrass Field",
}


def land_enters_tapped(name: str, battlefield_lands: list[str]) -> bool:
    """Determine if a land enters tapped given board state."""
    if name in ALWAYS_TAPPED:
        return True

    # Castle Ardenvale: enters tapped unless you control a Plains
    if name == "Castle Ardenvale":
        return "Plains" not in battlefield_lands

    # Minas Tirith: enters tapped unless you control a legendary creature.
    # Proxy: tapped while fewer than 2 lands are on the battlefield (turns 1-2
    # rarely have a legendary out; from turn 3 the deck usually does).
    if name == "Minas Tirith":
        return len(battlefield_lands) < 2

    # MDFC back faces enter untapped for 3 life
    if name in MDFC_LANDS:
        return False

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

    if name in {"Eiganjo, Seat of the Empire", "Minas Tirith",
                "Windbrisk Heights", "Emeria, the Sky Ruin", "Castle Ardenvale"}:
        return (1, 0)

    if name in MDFC_LANDS:
        return (1, 0)  # All three back faces tap for {W}

    if name in {"Three Tree City", "War Room"}:
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

    The 3 pay-life MDFCs ("Sorcery // Land" etc.) intentionally classify as
    lands — they sit in land slots in the board-approved 38-land plan.
    """
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

    def draw(self, n: int = 1):
        for _ in range(n):
            if self.library:
                self.hand.append(self.library.pop())

    def count_lands_in_hand(self) -> int:
        return sum(1 for c in self.hand if c in self.land_set)

    def _is_land(self, name: str) -> bool:
        return name in self.land_set

    def _land_play_priority(self, name: str) -> float:
        """Higher = play first. Untapped W-producing > utility > MDFCs."""
        tapped = land_enters_tapped(name, self.battlefield_lands)
        base = 0 if tapped else 10

        if name == "Plains":
            base += 5
        elif name == "Castle Ardenvale":
            base += 4
        elif name in {"Eiganjo, Seat of the Empire", "Minas Tirith"}:
            base += 4
        elif name in {"Emeria, the Sky Ruin", "Windbrisk Heights"}:
            base += 3  # W-producing but always tapped
        elif name in MDFC_LANDS:
            base += 2  # Real lands first; hold MDFCs for spell-mode flexibility
        elif name in {"Three Tree City", "War Room"}:
            base += 2

        return base

    def compute_mana_pool(self) -> ManaPool:
        """Calculate total available mana from untapped lands + rocks."""
        pool = ManaPool()

        for i, land in enumerate(self.battlefield_lands):
            if i in self.tapped_lands:
                continue
            w, c = compute_land_mana(land)
            pool.W += w
            pool.C += c

        for rock in self.battlefield_rocks:
            rdef = ROCK_DEFS.get(rock)
            if rdef:
                pool.W += rdef.get("W", 0)
                pool.C += rdef.get("C", 0)

        return pool

    def play_turn(self, turn_number: int):
        """Simulate one turn."""
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
        """Try to cast mana rocks from hand."""
        for rock_name in ("Sol Ring", "Arcane Signet"):
            if rock_name not in self.hand:
                continue
            rdef = ROCK_DEFS[rock_name]
            rock_pips = {"generic": rdef["cmc"], "W": 0}
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
            mana_by_turn[t].append(pool.total)
            w_by_turn[t].append(pool.W)

            if pool.W == 0:
                zero_w_by_turn[t] += 1

            # Commander: Fíli the Pathfinder {3}{W}
            cmd_pips = {"generic": 3, "W": 1}
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


def main():
    parser = argparse.ArgumentParser(
        description="Monte Carlo mana base simulation for Anvil Chorus (Fíli the Pathfinder)")
    parser.add_argument("--json", action="store_true",
                        help="Write simulation.json instead of console output")
    args = parser.parse_args()

    with open(DECK_FILE) as f:
        deck_data = json.load(f)
    with open(METADATA_FILE) as f:
        metadata = json.load(f)

    print("Building Fíli the Pathfinder decklist...")
    decklist = build_decklist(deck_data)
    print(f"Decklist: {len(decklist)} cards")

    classified = classify_cards(decklist, metadata)
    print(f"Lands: {len(classified['lands'])} (incl. 3 MDFCs), "
          f"rocks: {len(classified['rocks'])}, spells: {len(classified['spells'])}")

    if args.json:
        import export_simulation_results as exporter
        result = exporter.export_anvil_chorus(metadata)
        if not exporter.validate_output(result, "anvil-chorus"):
            raise ValueError("export_anvil_chorus produced invalid simulation output")
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
