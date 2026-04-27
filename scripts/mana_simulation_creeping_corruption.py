#!/usr/bin/env python3
"""Monte Carlo mana base simulation for Creeping Corruption (WUBG).

Simulates 100,000 games measuring mana production, color balance, and curve
efficiency turns 1-10 for a 4-color mana base with mana dorks.

Commander: Atraxa, Praetors' Voice ({G}{W}{U}{B}, CMC 4)
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
METADATA_FILE = PROJECT_ROOT / "data" / "card-metadata.json"
JSON_OUTPUT = PROJECT_ROOT / "data" / "commanders" / "creeping-corruption" / "simulation.json"

NUM_GAMES = 100_000
NUM_TURNS = 10


# --- Mana cost parser ---


def parse_mana_cost(mana_cost: str) -> dict:
    if "//" in mana_cost:
        mana_cost = mana_cost.split("//")[0].strip()

    result = {"generic": 0, "W": 0, "U": 0, "B": 0, "G": 0, "total": 0, "X": False}
    symbols = re.findall(r"\{([^}]+)\}", mana_cost)
    for sym in symbols:
        if sym == "X":
            result["X"] = True
        elif sym.isdigit():
            result["generic"] += int(sym)
        elif sym in ("W", "U", "B", "G"):
            result[sym] += 1
    result["total"] = result["generic"] + result["W"] + result["U"] + result["B"] + result["G"]
    return result


# --- Rock definitions ---

ROCK_DEFS = {
    "Sol Ring":          {"cmc": 1, "colors": frozenset({"C"}), "count": 2, "burst": False},
    "Arcane Signet":     {"cmc": 2, "colors": frozenset({"W", "U", "B", "G"}), "count": 1, "burst": False},
    "Glistening Sphere": {"cmc": 3, "colors": frozenset({"W", "U", "B", "G"}), "count": 1, "burst": False},
}

# --- Dork definitions (summoning sickness: produce mana turn after cast) ---

DORK_DEFS = {
    "Birds of Paradise":    {"cast_pips": {"generic": 0, "G": 1}, "colors": frozenset({"W", "U", "B", "G"})},
    "Noble Hierarch":       {"cast_pips": {"generic": 0, "G": 1}, "colors": frozenset({"W", "U", "G"})},
    "Llanowar Elves":       {"cast_pips": {"generic": 0, "G": 1}, "colors": frozenset({"G"})},
    "Elves of Deep Shadow": {"cast_pips": {"generic": 0, "G": 1}, "colors": frozenset({"B"})},
    "Bloom Tender":         {"cast_pips": {"generic": 1, "G": 1}, "colors": frozenset({"W", "U", "B", "G"})},
    "Plague Myr":           {"cast_pips": {"generic": 2}, "colors": frozenset({"C"})},
}

# --- Land subtype definitions ---

PLAINS_TYPED = {"Plains", "Temple Garden", "Hallowed Fountain", "Godless Shrine", "Indatha Triome"}
ISLAND_TYPED = {"Island", "Breeding Pool", "Hallowed Fountain", "Watery Grave", "Zagoth Triome"}
SWAMP_TYPED = {"Swamp", "Overgrown Tomb", "Watery Grave", "Godless Shrine", "Zagoth Triome", "Indatha Triome"}
FOREST_TYPED = {"Forest", "Breeding Pool", "Temple Garden", "Overgrown Tomb", "Zagoth Triome", "Indatha Triome"}

BASIC_LANDS = {"Plains", "Island", "Swamp", "Forest"}

ALWAYS_TAPPED = {"Zagoth Triome", "Indatha Triome"}

TYPED_FETCH_LANDS = {
    "Polluted Delta":    {"targets": ISLAND_TYPED | SWAMP_TYPED},
    "Flooded Strand":    {"targets": ISLAND_TYPED | PLAINS_TYPED},
    "Verdant Catacombs": {"targets": SWAMP_TYPED | FOREST_TYPED},
    "Windswept Heath":   {"targets": FOREST_TYPED | PLAINS_TYPED},
    "Marsh Flats":       {"targets": SWAMP_TYPED | PLAINS_TYPED},
}
FETCH_LANDS = set(TYPED_FETCH_LANDS.keys())

FAST_LANDS = {
    "Darkslick Shores":  frozenset({"U", "B"}),
    "Blooming Marsh":    frozenset({"B", "G"}),
    "Razorverge Thicket": frozenset({"W", "G"}),
    "Botanical Sanctum": frozenset({"U", "G"}),
}

PAIN_LANDS = {
    "Llanowar Wastes":  frozenset({"B", "G"}),
    "Yavimaya Coast":   frozenset({"U", "G"}),
    "Underground River": frozenset({"U", "B"}),
    "Caves of Koilos":  frozenset({"W", "B"}),
    "Brushland":        frozenset({"W", "G"}),
    "City of Brass":    frozenset({"W", "U", "B", "G"}),
}


def land_enters_tapped(name: str, battlefield_lands: list[str], hand: list[str]) -> bool:
    if name in ALWAYS_TAPPED:
        return True
    if name in FAST_LANDS:
        return len(battlefield_lands) > 2
    return False


def compute_land_sources(name: str) -> list[frozenset]:
    if name == "Plains":
        return [frozenset({"W"})]
    if name == "Island":
        return [frozenset({"U"})]
    if name == "Swamp":
        return [frozenset({"B"})]
    if name == "Forest":
        return [frozenset({"G"})]

    if name in {"Command Tower", "Exotic Orchard", "Reflecting Pool", "City of Brass"}:
        return [frozenset({"W", "U", "B", "G"})]

    if name == "Breeding Pool":
        return [frozenset({"U", "G"})]
    if name == "Temple Garden":
        return [frozenset({"W", "G"})]
    if name == "Overgrown Tomb":
        return [frozenset({"B", "G"})]
    if name == "Watery Grave":
        return [frozenset({"U", "B"})]
    if name == "Hallowed Fountain":
        return [frozenset({"W", "U"})]
    if name == "Godless Shrine":
        return [frozenset({"W", "B"})]

    if name == "Zagoth Triome":
        return [frozenset({"U", "B", "G"})]
    if name == "Indatha Triome":
        return [frozenset({"W", "B", "G"})]

    if name in FAST_LANDS:
        return [FAST_LANDS[name]]

    if name in PAIN_LANDS:
        return [PAIN_LANDS[name]]

    if name in {"Karn's Bastion", "Inkmoth Nexus", "The Seedcore"}:
        return [frozenset({"C"})]

    return [frozenset({"C"})]


# --- ManaPool ---


class ManaPool:
    def __init__(self, sources=None):
        self.sources: list[frozenset] = list(sources) if sources else []

    @property
    def total(self) -> int:
        return len(self.sources)

    def count_color(self, color: str) -> int:
        return sum(1 for s in self.sources if color in s)

    def _allocate(self, pips: dict) -> tuple[bool, list[frozenset] | None]:
        needed = {c: pips.get(c, 0) for c in "WUBG"}
        generic = pips.get("generic", 0)
        total_needed = sum(needed.values()) + generic

        if self.total < total_needed:
            return False, None

        available = list(self.sources)

        for _ in range(sum(needed.values())):
            best_color = None
            best_ratio = float("inf")
            for color in "WUBG":
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

        available.sort(key=lambda s: len(s))
        if len(available) < generic:
            return False, None

        remaining = available[generic:]
        return True, remaining

    def can_cast(self, pips: dict) -> bool:
        success, _ = self._allocate(pips)
        return success

    def after_spending(self, pips: dict) -> "ManaPool":
        success, remaining = self._allocate(pips)
        if not success:
            return ManaPool()
        return ManaPool(remaining)


# --- Decklist builder ---


def build_decklist(deck_data: dict) -> list[str]:
    cards = []
    for card in deck_data["decklist"]:
        qty = card.get("quantity", 1)
        cards.extend([card["name"]] * qty)
    return cards


def classify_cards(decklist: list[str], metadata: dict) -> dict:
    classified = {"lands": [], "rocks": [], "spells": []}
    for name in decklist:
        if name in ROCK_DEFS or name in DORK_DEFS:
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
    sources = sum(1 for c in hand if c in land_set or c in ROCK_DEFS or c in DORK_DEFS)
    return sources <= 1


def choose_bottom_cards(hand: list[str], count: int, metadata: dict,
                        land_set: set[str]) -> list[str]:
    ramp_cards = set(ROCK_DEFS) | set(DORK_DEFS)
    candidates = [c for c in hand if c not in land_set and c not in ramp_cards]
    candidates.sort(key=lambda c: metadata.get(c, {}).get("cmc", 0), reverse=True)
    return candidates[:count]


# --- Game state ---


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
        tapped = land_enters_tapped(name, self.battlefield_lands, self.hand)
        base = 0 if tapped else 10

        if name in FETCH_LANDS:
            base += 5

        sources = compute_land_sources(name)
        if sources:
            n_colors = sum(1 for c in "WUBG" if c in sources[0])
            base += n_colors * 2
        return base

    def _find_best_fetchable(self, typed_set: set[str]) -> str | None:
        have_colors = set()
        for land in self.battlefield_lands:
            for s in compute_land_sources(land):
                have_colors.update(c for c in s if c != "C")

        candidates = [c for c in self.library if c in typed_set]
        if not candidates:
            return None

        def score(name: str) -> tuple[int, int, int]:
            sources = compute_land_sources(name)
            if not sources:
                return (0, 0, 0)
            colors = {c for c in sources[0] if c != "C"}
            missing_covered = len(colors - have_colors)
            tapped = 1 if name in ALWAYS_TAPPED else 0
            return (missing_covered, len(colors), -tapped)

        candidates.sort(key=score, reverse=True)
        return candidates[0]

    def compute_mana_pool(self) -> ManaPool:
        pool_sources: list[frozenset] = []

        for i, land in enumerate(self.battlefield_lands):
            if i in self.tapped_lands:
                continue
            pool_sources.extend(compute_land_sources(land))

        for rock in self.battlefield_rocks:
            rdef = ROCK_DEFS[rock]
            for _ in range(rdef["count"]):
                pool_sources.append(rdef["colors"])

        for dork in self.dorks_active:
            ddef = DORK_DEFS[dork]
            pool_sources.append(ddef["colors"])

        return ManaPool(pool_sources)

    def play_turn(self, turn_number: int):
        if turn_number > 1:
            self.draw(1)

        self.tapped_lands.clear()
        self.dorks_active = list(self.battlefield_dorks)

        hand_lands = [(self._land_play_priority(c), c) for c in self.hand if self._is_land(c)]
        hand_lands.sort(reverse=True)

        if hand_lands:
            _, land_name = hand_lands[0]
            self.hand.remove(land_name)

            if land_name in TYPED_FETCH_LANDS:
                targets = TYPED_FETCH_LANDS[land_name]["targets"]
                target = self._find_best_fetchable(targets)
                if target:
                    self.library.remove(target)
                    self.battlefield_lands.append(target)
            else:
                tapped = land_enters_tapped(land_name, self.battlefield_lands, self.hand)
                self.battlefield_lands.append(land_name)
                if tapped:
                    self.tapped_lands.add(len(self.battlefield_lands) - 1)

        pool = self.compute_mana_pool()
        self._try_cast_ramp(pool)

        self.mana_per_turn.append(self.compute_mana_pool())

    def _try_cast_ramp(self, pool: ManaPool):
        priority_order = [
            ("rock", "Sol Ring"),
            ("rock", "Arcane Signet"),
            ("dork", "Llanowar Elves"),
            ("dork", "Elves of Deep Shadow"),
            ("dork", "Noble Hierarch"),
            ("dork", "Birds of Paradise"),
            ("dork", "Plague Myr"),
            ("dork", "Bloom Tender"),
            ("rock", "Glistening Sphere"),
        ]

        for ramp_type, name in priority_order:
            if name not in self.hand:
                continue

            if ramp_type == "rock":
                pips = parse_mana_cost(
                    self.metadata.get(name, {}).get("mana_cost", ""))
                if pool.can_cast(pips):
                    pool = pool.after_spending(pips)
                    self.hand.remove(name)
                    self.battlefield_rocks.append(name)
                    rdef = ROCK_DEFS[name]
                    for _ in range(rdef["count"]):
                        pool.sources.append(rdef["colors"])

            elif ramp_type == "dork":
                ddef = DORK_DEFS[name]
                pips = ddef["cast_pips"]
                if pool.can_cast(pips):
                    pool = pool.after_spending(pips)
                    self.hand.remove(name)
                    self.battlefield_dorks.append(name)


def commander_mulligan(decklist: list[str], metadata: dict,
                       land_set: set[str]) -> GameState:
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
    ramp_cards = set(ROCK_DEFS) | set(DORK_DEFS)
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
    land_set = set()
    for name in set(decklist):
        meta = metadata.get(name, {})
        if "Land" in meta.get("type_line", ""):
            land_set.add(name)

    mana_by_turn = {t: [] for t in range(1, NUM_TURNS + 1)}
    w_by_turn = {t: [] for t in range(1, NUM_TURNS + 1)}
    u_by_turn = {t: [] for t in range(1, NUM_TURNS + 1)}
    b_by_turn = {t: [] for t in range(1, NUM_TURNS + 1)}
    g_by_turn = {t: [] for t in range(1, NUM_TURNS + 1)}
    hand_land_counts = Counter()
    mulligan_attempts = Counter()

    zero_w_by_turn = {t: 0 for t in range(1, NUM_TURNS + 1)}
    zero_u_by_turn = {t: 0 for t in range(1, NUM_TURNS + 1)}
    zero_b_by_turn = {t: 0 for t in range(1, NUM_TURNS + 1)}
    zero_g_by_turn = {t: 0 for t in range(1, NUM_TURNS + 1)}

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
            w_by_turn[t].append(pool.count_color("W"))
            u_by_turn[t].append(pool.count_color("U"))
            b_by_turn[t].append(pool.count_color("B"))
            g_by_turn[t].append(pool.count_color("G"))

            if pool.count_color("W") == 0:
                zero_w_by_turn[t] += 1
            if pool.count_color("U") == 0:
                zero_u_by_turn[t] += 1
            if pool.count_color("B") == 0:
                zero_b_by_turn[t] += 1
            if pool.count_color("G") == 0:
                zero_g_by_turn[t] += 1

            # Atraxa: {G}{W}{U}{B} = 1W 1U 1B 1G
            cmd_pips = {"W": 1, "U": 1, "B": 1, "G": 1}
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
            for future_t in range(cmd_cast_turn + 1, NUM_TURNS + 1):
                commander_by_turn[future_t] += 1

        if cast_every_turn:
            curve_out_games += 1

    return {
        "mana_by_turn": mana_by_turn,
        "w_by_turn": w_by_turn,
        "u_by_turn": u_by_turn,
        "b_by_turn": b_by_turn,
        "g_by_turn": g_by_turn,
        "hand_land_counts": hand_land_counts,
        "mulligan_attempts": mulligan_attempts,
        "zero_w_by_turn": zero_w_by_turn,
        "zero_u_by_turn": zero_u_by_turn,
        "zero_b_by_turn": zero_b_by_turn,
        "zero_g_by_turn": zero_g_by_turn,
        "commander_by_turn": commander_by_turn,
        "castable_spell_by_turn": castable_spell_by_turn,
        "curve_out_games": curve_out_games,
        "tapped_land_turns": tapped_land_turns,
    }


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


# --- Static analysis ---


def print_static_analysis(decklist: list[str], metadata: dict,
                          classified: dict) -> tuple:
    print("=" * 65)
    print("STATIC ANALYSIS — CREEPING CORRUPTION (BRACKET 4)")
    print("=" * 65)

    print(f"\n--- Deck Composition ---")
    print(f"Total cards (excl. commander): {len(decklist)}")
    print(f"Lands: {len(classified['lands'])}")
    print(f"Mana rocks/dorks: {len(classified['rocks'])}")
    print(f"Spells/creatures: {len(classified['spells'])}")

    cmcs = []
    for name in decklist:
        meta = metadata.get(name, {})
        if "Land" not in meta.get("type_line", ""):
            cmc = meta.get("cmc", 0)
            if isinstance(cmc, (int, float)):
                cmcs.append(int(cmc))

    avg_cmc = statistics.mean(cmcs) if cmcs else 0
    print(f"\nAverage CMC (non-land): {avg_cmc:.2f}")

    total_W, total_U, total_B, total_G = 0, 0, 0, 0
    for name in decklist:
        meta = metadata.get(name, {})
        mc = meta.get("mana_cost", "")
        if "Land" in meta.get("type_line", ""):
            continue
        pips = parse_mana_cost(mc)
        total_W += pips["W"]
        total_U += pips["U"]
        total_B += pips["B"]
        total_G += pips["G"]

    total_pips = total_W + total_U + total_B + total_G
    if total_pips > 0:
        print(f"\n--- Pip Demand ---")
        print(f"  {{W}}: {total_W}  {{U}}: {total_U}  {{B}}: {total_B}  {{G}}: {total_G}")
        print(f"  Ratio: {total_W/total_pips*100:.0f}% W / {total_U/total_pips*100:.0f}% U / "
              f"{total_B/total_pips*100:.0f}% B / {total_G/total_pips*100:.0f}% G")

    return avg_cmc, total_W, total_U, total_B, total_G


# --- Results ---


def print_results(stats: dict, classified: dict,
                  avg_cmc: float, pip_W: int, pip_U: int, pip_B: int, pip_G: int):
    total = NUM_GAMES

    print("\n" + "=" * 65)
    print(f"MONTE CARLO SIMULATION — CREEPING CORRUPTION ({NUM_GAMES:,} games, {NUM_TURNS} turns)")
    print("=" * 65)

    print(f"\n--- Mana Available per Turn ---")
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
    print(f"\n  Mulligan stats:")
    print(f"    Kept first hand:     {mull.get(0, 0)/total*100:>5.1f}%")
    print(f"    Free mulligan:       {mull.get(1, 0)/total*100:>5.1f}%")
    print(f"    Paid mulligan (→6):  {mull.get(2, 0)/total*100:>5.1f}%")

    print(f"\n--- Color Balance ---")
    for t in range(1, NUM_TURNS + 1):
        w = statistics.mean(stats["w_by_turn"][t])
        u = statistics.mean(stats["u_by_turn"][t])
        b = statistics.mean(stats["b_by_turn"][t])
        g = statistics.mean(stats["g_by_turn"][t])
        print(f"    T{t}: W={w:.1f} U={u:.1f} B={b:.1f} G={g:.1f}")

    print(f"\n  Color screw (0 sources):")
    for t in range(2, NUM_TURNS + 1):
        w_pct = stats["zero_w_by_turn"][t] / total * 100
        u_pct = stats["zero_u_by_turn"][t] / total * 100
        b_pct = stats["zero_b_by_turn"][t] / total * 100
        g_pct = stats["zero_g_by_turn"][t] / total * 100
        print(f"    T{t}: 0W={w_pct:.1f}% 0U={u_pct:.1f}% 0B={b_pct:.1f}% 0G={g_pct:.1f}%")

    print(f"\n--- Commander Timing (Atraxa {{W}}{{U}}{{B}}{{G}}) ---")
    for t in range(2, NUM_TURNS + 1):
        count = stats["commander_by_turn"][t]
        print(f"    By T{t}: {count/total*100:.1f}%")


def main():
    from pathlib import Path

    parser = argparse.ArgumentParser(
        description="Monte Carlo mana simulation for Creeping Corruption (Atraxa)")
    parser.add_argument("--json", action="store_true",
                        help="Write simulation.json via export pipeline")
    args = parser.parse_args()

    deck_file = PROJECT_ROOT / "data" / "commanders" / "creeping-corruption" / "deck.json"
    with open(deck_file) as f:
        deck_data = json.load(f)
    with open(METADATA_FILE) as f:
        metadata = json.load(f)

    print("Building Creeping Corruption decklist...")
    decklist = build_decklist(deck_data)
    print(f"Decklist: {len(decklist)} cards")

    classified = classify_cards(decklist, metadata)

    if args.json:
        import export_simulation_results as exporter
        result = exporter.export_wubg_poison(metadata)
        if not exporter.validate_output(result, "creeping-corruption"):
            raise ValueError("export_wubg_poison produced invalid simulation output")
        JSON_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        with open(JSON_OUTPUT, "w") as f:
            json.dump(result, f, indent=2)
        print(f"Written: {JSON_OUTPUT}")
        print(f"Size: {JSON_OUTPUT.stat().st_size / 1024:.1f} KB")
        return

    avg_cmc, pip_W, pip_U, pip_B, pip_G = print_static_analysis(decklist, metadata, classified)

    n_workers = os.cpu_count() or 4
    chunk_size = NUM_GAMES // n_workers
    remainder = NUM_GAMES % n_workers
    chunks = [chunk_size + (1 if i < remainder else 0) for i in range(n_workers)]

    print(f"\nRunning {NUM_GAMES:,} game simulations ({n_workers} workers)...")
    with multiprocessing.Pool(n_workers) as pool:
        results = pool.map(_run_chunk, [(decklist, metadata, n) for n in chunks])
    stats = merge_stats(results)

    print_results(stats, classified, avg_cmc, pip_W, pip_U, pip_B, pip_G)
    print("\n" + "=" * 65)


if __name__ == "__main__":
    main()
