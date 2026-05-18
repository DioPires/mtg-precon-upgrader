#!/usr/bin/env python3
"""Monte Carlo mana base simulation for Pyre & Panic (Norin the Wary).

Simulates games measuring mana production and curve efficiency turns 1-10
for the Bracket 3 mono-red ETB-flicker / static-damage-stack decklist.

Commander: Norin the Wary ({R}, CMC 1). His static ability flickers himself
at the start of every combat and on opponent creature ETBs. For mana sim
purposes this matters only insofar as he's a 1-mana commander always
castable from T1.

Special metrics (Norin-specific):
- engineReadiness: probability a Norin-flicker payoff is on battlefield
  with Norin (Impact Tremors / Purphoros / Witty Roastmaster / Molten Gatekeeper
  / Warstorm Surge / Pandemonium / Terror of the Peaks / Genesis Chamber /
  Electrostatic Field / Agate Instigator / Young Pyromancer).
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
DECK_FILE = PROJECT_ROOT / "data" / "commanders" / "pyre-and-panic" / "deck.json"
METADATA_FILE = PROJECT_ROOT / "data" / "card-metadata.json"
JSON_OUTPUT = PROJECT_ROOT / "data" / "commanders" / "pyre-and-panic" / "simulation.json"

NUM_GAMES = 100_000
NUM_TURNS = 10


# --- Mana cost parser ---

def parse_mana_cost(mana_cost: str) -> dict:
    """Parse mana_cost string into pip breakdown.

    "{1}{R}{R}" -> {generic: 1, R: 2, total: 3}
    Split cards (//): parse first half only.
    """
    if "//" in mana_cost:
        mana_cost = mana_cost.split("//")[0].strip()

    result = {"generic": 0, "R": 0, "total": 0, "X": False}
    symbols = re.findall(r"\{([^}]+)\}", mana_cost)
    for sym in symbols:
        if sym == "X":
            result["X"] = True
        elif sym.isdigit():
            result["generic"] += int(sym)
        elif sym == "R":
            result["R"] += 1
        # Ignore other symbols (hybrid, phyrexian, etc.)
    result["total"] = result["generic"] + result["R"]
    return result


# --- Rock definitions ---
# Mana-producing rocks in Pyre & Panic. Hazoret's Monument is a cost-reducer
# for red creatures, not a mana source — modeled below in COST_REDUCERS.
# Ruby Medallion likewise reduces red spell cost by 1, not a mana source.

ROCK_DEFS = {
    "Sol Ring":         {"cmc": 1, "R": 0, "C": 2, "burst": False},
    "Arcane Signet":    {"cmc": 2, "R": 1, "C": 0, "burst": False},
    "Mind Stone":       {"cmc": 2, "R": 0, "C": 1, "burst": False},
    "Worn Powerstone":  {"cmc": 3, "R": 0, "C": 2, "burst": False},  # ETBs tapped; modeled untapped for simplicity
    "Thought Vessel":   {"cmc": 2, "R": 0, "C": 1, "burst": False},
    "Hedron Archive":   {"cmc": 4, "R": 0, "C": 2, "burst": False},
}


# --- Cost reducer definitions ---
# Reduce cost but don't directly produce mana.

COST_REDUCERS = {
    "Ruby Medallion":     {"cmc": 2, "reduction": 1, "applies_to": "red"},
    "Hazoret's Monument": {"cmc": 3, "reduction": 1, "applies_to": "red_creature"},
}


# --- Land definitions ---

# Lands that enter tapped unconditionally
ALWAYS_TAPPED: set[str] = set()

# Conditional-tapped lands evaluated dynamically in land_enters_tapped()

# Static mana production for each named land (R, C). Lands that need
# board-state queries are handled inline in compute_land_mana().
R_LANDS = {
    "Mountain", "Dwarven Mine", "Castle Embereth", "Den of the Bugbear",
    "Sokenzan, Crucible of Defiance", "Mines of Moria", "Kher Keep",
    "Shinka, the Bloodsoaked Keep", "Valakut Awakening // Valakut Stoneforge",
}

C_ONLY_LANDS = {
    "Hanweir Battlements", "Buried Ruin", "Cavern of Souls",
    "Nykthos, Shrine to Nyx", "War Room",
}


def land_enters_tapped(name: str, battlefield_lands: list[str], hand: list[str]) -> bool:
    """Determine if a land enters tapped given board + hand state."""
    if name in ALWAYS_TAPPED:
        return True

    other_lands = len(battlefield_lands)

    # Dwarven Mine: ETBs as 1/1 (and tapped) unless you control 3+ other Mountains
    if name == "Dwarven Mine":
        mountain_count = sum(
            1 for l in battlefield_lands
            if l == "Mountain" or l == "Dwarven Mine"
        )
        return mountain_count < 3

    # Den of the Bugbear: ETBs untapped if you control 2+ other lands
    if name == "Den of the Bugbear":
        return other_lands < 2

    # Mines of Moria: ETBs tapped unless an opponent controls a Legendary creature.
    # We can't easily model opponent boards; assume untapped (favorable assumption
    # for sim; if anything we'd over-count tapped events).
    if name == "Mines of Moria":
        return False

    # Sokenzan: ETBs untapped (channel ability only relevant for activation).
    if name == "Sokenzan, Crucible of Defiance":
        return False

    # Shinka, the Bloodsoaked Keep: ETBs untapped
    if name == "Shinka, the Bloodsoaked Keep":
        return False

    # Castle Embereth: untapped only if you control a Plains... actually Mountain (different castle).
    # Castle Embereth: ETBs untapped if you control a Mountain.
    if name == "Castle Embereth":
        has_mountain = any(
            l == "Mountain" or l == "Dwarven Mine" for l in battlefield_lands
        )
        return not has_mountain

    # Kher Keep: ETBs untapped
    if name == "Kher Keep":
        return False

    # Hanweir Battlements (meld land): ETBs untapped, taps for C
    if name == "Hanweir Battlements":
        return False

    # Valakut Awakening MDFC back face (Valakut Stoneforge): ETBs tapped.
    # Modeled below — for the front-face land, if played as a land it's
    # Valakut Stoneforge which always ETBs tapped.
    if name == "Valakut Awakening // Valakut Stoneforge":
        return True

    # Buried Ruin: ETBs untapped, taps for C
    if name == "Buried Ruin":
        return False

    # Cavern of Souls / Nykthos / War Room: untapped C
    if name in {"Cavern of Souls", "Nykthos, Shrine to Nyx", "War Room"}:
        return False

    # Basic Mountain: untapped
    return False


# --- Mana pool ---

class ManaPool:
    """Tracks available R and C mana.

    Simplified 2-bucket pool for mono-red:
    - R: red mana sources
    - C: colorless-only mana sources
    """

    def __init__(self):
        self.R = 0
        self.C = 0

    @property
    def total(self):
        return self.R + self.C

    def can_cast(self, pips: dict) -> bool:
        need_R = pips.get("R", 0)
        need_generic = pips.get("generic", 0)
        if self.R < need_R:
            return False
        remaining_R = self.R - need_R
        return (remaining_R + self.C) >= need_generic

    def after_spending(self, pips: dict) -> "ManaPool":
        need_R = pips.get("R", 0)
        need_generic = pips.get("generic", 0)

        pool = ManaPool()
        pool.R = self.R - need_R
        pool.C = self.C

        from_C = min(pool.C, need_generic)
        pool.C -= from_C
        need_generic -= from_C
        pool.R -= need_generic
        return pool


def compute_land_mana(name: str, battlefield_lands: list[str]) -> tuple[int, int]:
    """Return (R, C) mana production for an untapped land."""

    if name == "Mountain":
        return (1, 0)

    if name in {"Dwarven Mine", "Castle Embereth", "Den of the Bugbear",
                "Sokenzan, Crucible of Defiance", "Kher Keep",
                "Shinka, the Bloodsoaked Keep"}:
        return (1, 0)

    # Mines of Moria: taps for {C}, can sac to make {R}{R}. Modeled as 1 R.
    if name == "Mines of Moria":
        return (1, 0)

    # Hanweir Battlements: taps for {C}
    if name == "Hanweir Battlements":
        return (0, 1)

    # Valakut Stoneforge (back face): taps for {R}. Always ETBs tapped, so this
    # production only matters on subsequent turns.
    if name == "Valakut Awakening // Valakut Stoneforge":
        return (1, 0)

    # Buried Ruin / Cavern of Souls / Nykthos / War Room: tap for {C}
    if name in {"Buried Ruin", "Cavern of Souls", "Nykthos, Shrine to Nyx",
                "War Room"}:
        return (0, 1)

    # Fallback: colorless
    return (0, 1)


# --- Decklist builder ---

def build_decklist(deck_data: dict) -> list[str]:
    """Build the 99-card decklist."""
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
    """London mulligan bottom — highest CMC non-source cards."""
    ramp_names = set(ROCK_DEFS)
    candidates = [c for c in hand if c not in land_set and c not in ramp_names]
    candidates.sort(key=lambda c: metadata.get(c, {}).get("cmc", 0), reverse=True)
    return candidates[:count]


# --- Engine pieces (Norin payoffs) ---

ENGINE_PAYOFFS = {
    "Impact Tremors", "Purphoros, God of the Forge", "Witty Roastmaster",
    "Molten Gatekeeper", "Warstorm Surge", "Pandemonium",
    "Terror of the Peaks", "Genesis Chamber", "Electrostatic Field",
    "Agate Instigator", "Young Pyromancer",
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
        """Higher = play first. Untapped R > untapped C > tapped lands."""
        tapped = land_enters_tapped(name, self.battlefield_lands, self.hand)
        base = 0 if tapped else 10
        if name == "Mountain":
            base += 5
        elif name in R_LANDS:
            base += 4
        elif name in {"Cavern of Souls", "Buried Ruin"}:
            base += 2
        elif name in {"Nykthos, Shrine to Nyx", "War Room", "Hanweir Battlements"}:
            base += 1
        return base

    def compute_mana_pool(self) -> ManaPool:
        pool = ManaPool()
        for i, land in enumerate(self.battlefield_lands):
            if i in self.tapped_lands:
                continue
            r, c = compute_land_mana(land, self.battlefield_lands)
            pool.R += r
            pool.C += c

        for rock in self.battlefield_rocks:
            rdef = ROCK_DEFS.get(rock)
            if rdef:
                pool.R += rdef.get("R", 0)
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

            tapped = land_enters_tapped(land_name, self.battlefield_lands, self.hand)
            self.battlefield_lands.append(land_name)
            if tapped:
                self.tapped_lands.add(len(self.battlefield_lands) - 1)

        # Cast ramp from hand
        pool = self.compute_mana_pool()
        self._try_cast_ramp(pool)

        # Cast commander if available (Norin {R} = 1 mana — always lowest priority)
        pool = self.compute_mana_pool()
        if not self.commander_in_play and pool.can_cast({"generic": 0, "R": 1}):
            self.commander_in_play = True
            # Note: we don't track this as a "cast" for mana spending — Norin is
            # always castable on T1 in goldfish mode, so the modeling is the
            # commander_castable_turn metric.

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
        """Cast mana rocks from hand in priority order."""
        rock_priority = [
            "Sol Ring",
            "Arcane Signet",
            "Mind Stone",
            "Thought Vessel",
            "Worn Powerstone",
            "Hedron Archive",
        ]
        for rock_name in rock_priority:
            if rock_name not in self.hand:
                continue
            rdef = ROCK_DEFS[rock_name]
            rock_pips = {"generic": rdef["cmc"], "R": 0}
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
        if "Land" in meta.get("type_line", ""):
            land_set.add(name)

    mana_by_turn = {t: [] for t in range(1, NUM_TURNS + 1)}
    r_by_turn = {t: [] for t in range(1, NUM_TURNS + 1)}
    hand_land_counts = Counter()
    mulligan_attempts = Counter()

    zero_r_by_turn = {t: 0 for t in range(1, NUM_TURNS + 1)}

    commander_castable_turn = []
    commander_by_turn = {t: 0 for t in range(1, NUM_TURNS + 1)}

    castable_spell_by_turn = {t: 0 for t in range(1, NUM_TURNS + 1)}
    curve_out_games = 0

    tapped_land_turns = {1: 0, 2: 0}

    # Norin-specific: flicker triggers per game (proxy = number of turns Norin
    # is in play after he was cast, since he triggers every combat).
    # Engine readiness: % games where T6 has 3+ engine pieces on battlefield.
    flicker_triggers_per_game = []
    engine_ready_by_turn = {t: 0 for t in range(1, NUM_TURNS + 1)}

    for _ in range(num_games):
        state = commander_mulligan(decklist, metadata, land_set)
        mulligan_attempts[state.mulligan_attempt] += 1
        hand_land_counts[state.count_lands_in_hand()] += 1

        cmd_cast_turn = None
        cast_every_turn = True
        flicker_count = 0

        for t in range(1, NUM_TURNS + 1):
            lands_before = len(state.battlefield_lands)
            state.play_turn(t)
            lands_after = len(state.battlefield_lands)

            pool = state.mana_per_turn[-1]
            total_mana = pool.total
            r_avail = pool.R

            mana_by_turn[t].append(total_mana)
            r_by_turn[t].append(r_avail)

            if r_avail == 0:
                zero_r_by_turn[t] += 1

            # Commander: Norin the Wary {R} = CMC 1
            cmd_pips = {"generic": 0, "R": 1}
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

            # Count flicker triggers: each turn Norin is alive he triggers
            # at start of combat. Approximate 1 self-flicker per turn after cast.
            if cmd_cast_turn is not None and t > cmd_cast_turn:
                flicker_count += 1

            # Track engine-readiness on this turn
            if len(state.battlefield_payoffs) >= 3:
                engine_ready_by_turn[t] += 1

        flicker_triggers_per_game.append(flicker_count)

        if cmd_cast_turn is not None:
            commander_castable_turn.append(cmd_cast_turn)
            for future_t in range(cmd_cast_turn + 1, NUM_TURNS + 1):
                commander_by_turn[future_t] += 1

        if cast_every_turn:
            curve_out_games += 1

    return {
        "mana_by_turn": mana_by_turn,
        "r_by_turn": r_by_turn,
        "hand_land_counts": hand_land_counts,
        "mulligan_attempts": mulligan_attempts,
        "zero_r_by_turn": zero_r_by_turn,
        "commander_castable_turn": commander_castable_turn,
        "commander_by_turn": commander_by_turn,
        "castable_spell_by_turn": castable_spell_by_turn,
        "curve_out_games": curve_out_games,
        "tapped_land_turns": tapped_land_turns,
        "flicker_triggers_per_game": flicker_triggers_per_game,
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

    result = exporter.export_mono_red(metadata)
    if not exporter.validate_output(result, "pyre-and-panic"):
        raise ValueError("export_mono_red produced invalid simulation output")
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Monte Carlo mana base simulation for Pyre & Panic (Norin)")
    parser.add_argument("--json", action="store_true",
                        help="Write simulation.json instead of console output")
    args = parser.parse_args()

    with open(DECK_FILE) as f:
        deck_data = json.load(f)
    with open(METADATA_FILE) as f:
        metadata = json.load(f)

    print("Building Pyre & Panic decklist...")
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
    print(f"Commander by T1: {stats['commander_by_turn'][1]/total*100:.1f}%")
    print(f"Commander by T2: {stats['commander_by_turn'][2]/total*100:.1f}%")
    print(f"Curve-out rate: {stats['curve_out_games']/total*100:.1f}%")
    print(f"Engine ready (3+ payoffs) by T6: {stats['engine_ready_by_turn'][6]/total*100:.1f}%")


if __name__ == "__main__":
    main()
