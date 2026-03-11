#!/usr/bin/env python3
"""Monte Carlo mana base simulation for Turtle Token Engine (WUBRG).

Simulates 100,000 games measuring mana production, color balance, and curve
efficiency turns 1-10 for a 5-color mana base.

Commander: Donatello, the Brains ({2}{U}, CMC 3)
Partner: Leonardo, the Balance
Color identity: WUBRG
"""

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

NUM_GAMES = 100_000
NUM_TURNS = 10

# --- Mana cost parser ---


def parse_mana_cost(mana_cost: str) -> dict:
    """Parse mana_cost string into pip breakdown.

    "{2}{U}" -> {generic: 2, W: 0, U: 1, B: 0, R: 0, G: 0, total: 3}
    Split cards (//): parse first half only.
    """
    if "//" in mana_cost:
        mana_cost = mana_cost.split("//")[0].strip()

    result = {"generic": 0, "W": 0, "U": 0, "B": 0, "R": 0, "G": 0, "total": 0, "X": False}
    symbols = re.findall(r"\{([^}]+)\}", mana_cost)
    for sym in symbols:
        if sym == "X":
            result["X"] = True
        elif sym.isdigit():
            result["generic"] += int(sym)
        elif sym in ("W", "U", "B", "R", "G"):
            result[sym] += 1
    result["total"] = (result["generic"] + result["W"] + result["U"]
                       + result["B"] + result["R"] + result["G"])
    return result


# --- Rock definitions ---

ROCK_DEFS = {
    "Sol Ring":          {"cmc": 1, "colors": frozenset({"C"}), "count": 2, "burst": False},
    "Arcane Signet":     {"cmc": 2, "colors": frozenset({"W", "U", "B", "R", "G"}), "count": 1, "burst": False},
    "Chromatic Lantern": {"cmc": 3, "colors": frozenset({"W", "U", "B", "R", "G"}), "count": 1, "burst": False},
}

# --- Ramp spell definitions ---

RAMP_DEFS = {
    "Nature's Lore":  {"mana_cost": "{1}{G}", "fetch_type": "forest_typed", "tapped": False},
    "Kodama's Reach": {"mana_cost": "{2}{G}", "fetch_type": "basic_plus_hand", "tapped": True},
    "Cultivate":      {"mana_cost": "{2}{G}", "fetch_type": "basic_plus_hand", "tapped": True},
}

# --- Land subtype definitions ---

PLAINS_TYPED_LANDS = {"Plains", "Temple Garden", "Canopy Vista", "Prairie Stream",
                      "Hallowed Fountain", "Spara's Headquarters"}
ISLAND_TYPED_LANDS = {"Island", "Breeding Pool", "Prairie Stream",
                      "Hallowed Fountain", "Spara's Headquarters"}
SWAMP_TYPED_LANDS = set()
FOREST_TYPED_LANDS = {"Forest", "Breeding Pool", "Temple Garden", "Canopy Vista",
                      "Spara's Headquarters"}
MOUNTAIN_TYPED_LANDS = set()

BASIC_LANDS = {"Plains", "Island", "Forest"}

ALWAYS_TAPPED = {
    "Path of Ancestry",
    "Vivid Grove", "Vivid Meadow", "Vivid Creek",
    "Thriving Grove", "Thriving Heath", "Thriving Isle",
    "Seaside Citadel", "Spara's Headquarters",
}

FETCH_LANDS = {"Evolving Wilds", "Fabled Passage"}

# Thriving lands: base color -> land name
THRIVING_LANDS = {
    "Thriving Grove": "G",
    "Thriving Heath": "W",
    "Thriving Isle": "U",
}

VIVID_LANDS = {"Vivid Grove", "Vivid Meadow", "Vivid Creek"}


def land_enters_tapped(name: str, battlefield_lands: list[str], hand: list[str]) -> bool:
    """Determine if a land enters tapped given current board and hand."""
    if name in ALWAYS_TAPPED:
        return True
    if name == "Simic Growth Chamber":
        return True

    # BFZ duals: tapped unless 2+ basics on board
    if name in ("Canopy Vista", "Prairie Stream"):
        basic_count = sum(1 for l in battlefield_lands if l in BASIC_LANDS)
        return basic_count < 2

    # Check lands
    if name == "Sunpetal Grove":
        return not any(l in FOREST_TYPED_LANDS or l in PLAINS_TYPED_LANDS
                       for l in battlefield_lands)
    if name == "Hinterland Harbor":
        return not any(l in FOREST_TYPED_LANDS or l in ISLAND_TYPED_LANDS
                       for l in battlefield_lands)
    if name == "Glacial Fortress":
        return not any(l in PLAINS_TYPED_LANDS or l in ISLAND_TYPED_LANDS
                       for l in battlefield_lands)

    # Reveal land: tapped unless reveal Forest or Plains from hand
    if name == "Fortified Village":
        return not any(l in FOREST_TYPED_LANDS or l in PLAINS_TYPED_LANDS
                       for l in hand)

    # Shock lands, pain lands, Command Tower, etc. — always untapped
    return False


def compute_land_sources(name: str) -> list[frozenset]:
    """Return mana sources for a single untapped land (no Chromatic Lantern)."""
    # Basics
    if name == "Plains":
        return [frozenset({"W"})]
    if name == "Island":
        return [frozenset({"U"})]
    if name == "Forest":
        return [frozenset({"G"})]

    # Rainbow lands
    if name in {"Command Tower", "Exotic Orchard", "Path of Ancestry"}:
        return [frozenset({"W", "U", "B", "R", "G"})]

    # Shock lands
    if name == "Temple Garden":
        return [frozenset({"W", "G"})]
    if name == "Breeding Pool":
        return [frozenset({"U", "G"})]
    if name == "Hallowed Fountain":
        return [frozenset({"W", "U"})]

    # BFZ duals
    if name == "Canopy Vista":
        return [frozenset({"W", "G"})]
    if name == "Prairie Stream":
        return [frozenset({"W", "U"})]

    # Check lands
    if name == "Sunpetal Grove":
        return [frozenset({"W", "G"})]
    if name == "Hinterland Harbor":
        return [frozenset({"U", "G"})]
    if name == "Glacial Fortress":
        return [frozenset({"W", "U"})]

    # Reveal land
    if name == "Fortified Village":
        return [frozenset({"W", "G"})]

    # Pain lands
    if name == "Adarkar Wastes":
        return [frozenset({"W", "U"})]
    if name == "Yavimaya Coast":
        return [frozenset({"U", "G"})]

    # Vivid lands (simplified: treat as any-color source)
    if name in VIVID_LANDS:
        return [frozenset({"W", "U", "B", "R", "G"})]

    # Bounce land (produces 2 mana atoms)
    if name == "Simic Growth Chamber":
        return [frozenset({"U"}), frozenset({"G"})]

    # Channel land
    if name == "Otawara, Soaring City":
        return [frozenset({"U"})]

    # Trilands
    if name == "Seaside Citadel":
        return [frozenset({"W", "U", "G"})]
    if name == "Spara's Headquarters":
        return [frozenset({"W", "U", "G"})]

    # Utility lands (colorless)
    if name in {"Rogue's Passage", "Reliquary Tower", "Scavenger Grounds"}:
        return [frozenset({"C"})]

    # Thriving lands without stored choice — return base color only
    if name in THRIVING_LANDS:
        return [frozenset({THRIVING_LANDS[name]})]

    # Fallback: colorless
    return [frozenset({"C"})]


WUBRG = frozenset({"W", "U", "B", "R", "G"})


# --- ManaPool ---


class ManaPool:
    """Tracks available mana as a list of source atoms."""

    def __init__(self, sources=None):
        self.sources: list[frozenset] = list(sources) if sources else []

    @property
    def total(self) -> int:
        return len(self.sources)

    def count_color(self, color: str) -> int:
        return sum(1 for s in self.sources if color in s)

    def _allocate(self, pips: dict) -> tuple[bool, list[frozenset] | None]:
        """Greedy allocation: colored pips first (most constrained), then generic."""
        needed = {c: pips.get(c, 0) for c in "WUBRG"}
        generic = pips.get("generic", 0)
        total_needed = sum(needed.values()) + generic

        if self.total < total_needed:
            return False, None

        available = list(self.sources)

        # Phase 1: Assign colored pips
        for _ in range(sum(needed.values())):
            best_color = None
            best_ratio = float("inf")
            for color in "WUBRG":
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

        # Phase 2: Generic
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
    """Build 99-card decklist from deck JSON."""
    cards = []
    for card in deck_data["decklist"]:
        qty = card.get("quantity", 1)
        cards.extend([card["name"]] * qty)
    return cards


def classify_cards(decklist: list[str], metadata: dict) -> dict:
    """Classify each card as land, rock, or spell."""
    classified = {"lands": [], "rocks": [], "spells": []}
    for name in decklist:
        if name in ROCK_DEFS:
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
    sources = sum(1 for c in hand if c in land_set or c in ROCK_DEFS)
    return sources <= 1


def choose_bottom_cards(hand: list[str], count: int, metadata: dict,
                        land_set: set[str]) -> list[str]:
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
        self.tapped_lands: set[int] = set()
        self.battlefield_rocks: list[str] = []
        self.metadata = metadata
        self.land_set = land_set
        self.mana_per_turn: list[ManaPool] = []
        self.mulligan_attempt = 0
        self.thriving_choices: dict[int, str] = {}  # land_index -> chosen 2nd color

    def draw(self, n: int = 1):
        for _ in range(n):
            if self.library:
                self.hand.append(self.library.pop())

    def count_lands_in_hand(self) -> int:
        return sum(1 for c in self.hand if c in self.land_set)

    def _is_land(self, name: str) -> bool:
        return name in self.land_set

    def _has_chromatic_lantern(self) -> bool:
        return "Chromatic Lantern" in self.battlefield_rocks

    def _choose_thriving_color(self, base_color: str) -> str:
        """Choose 2nd color for Thriving land: pick the color with fewest sources."""
        color_counts = {}
        for c in "WUBRG":
            if c == base_color:
                continue
            count = 0
            for i, land in enumerate(self.battlefield_lands):
                if i in self.tapped_lands:
                    continue
                sources = self._land_sources(land, i)
                for s in sources:
                    if c in s:
                        count += 1
                        break
            color_counts[c] = count
        return min(color_counts, key=color_counts.get)

    def _land_sources(self, land: str, index: int) -> list[frozenset]:
        """Get mana sources for a land at given index, respecting Chromatic Lantern."""
        # Chromatic Lantern overrides everything
        if self._has_chromatic_lantern():
            # Simic Growth Chamber still produces 2 atoms, both upgraded to WUBRG
            if land == "Simic Growth Chamber":
                return [WUBRG, WUBRG]
            return [WUBRG]

        # Thriving lands: use stored choice
        if land in THRIVING_LANDS and index in self.thriving_choices:
            base = THRIVING_LANDS[land]
            chosen = self.thriving_choices[index]
            return [frozenset({base, chosen})]

        return compute_land_sources(land)

    def _land_play_priority(self, name: str) -> float:
        tapped = land_enters_tapped(name, self.battlefield_lands, self.hand)
        base = 0 if tapped else 10

        # Fetch lands get a small bonus (fix colors)
        if name in FETCH_LANDS:
            base += 3

        has_lantern = self._has_chromatic_lantern()
        if has_lantern:
            sources = [WUBRG]
        else:
            sources = compute_land_sources(name)
        if sources:
            n_colors = sum(1 for c in "WUBRG" if c in sources[0])
            base += n_colors * 2
        return base

    def compute_mana_pool(self) -> ManaPool:
        pool_sources: list[frozenset] = []

        for i, land in enumerate(self.battlefield_lands):
            if i in self.tapped_lands:
                continue
            sources = self._land_sources(land, i)
            pool_sources.extend(sources)

        for rock in self.battlefield_rocks:
            rdef = ROCK_DEFS[rock]
            for _ in range(rdef["count"]):
                pool_sources.append(rdef["colors"])

        return ManaPool(pool_sources)

    def _find_best_fetchable_basic(self) -> str | None:
        """Find the best basic land in library (for Evolving Wilds etc.)."""
        have_colors = set()
        for i, land in enumerate(self.battlefield_lands):
            sources = self._land_sources(land, i)
            for s in sources:
                have_colors.update(c for c in s if c != "C")

        candidates = [c for c in self.library if c in BASIC_LANDS]
        if not candidates:
            return None

        def score(name: str) -> tuple[int, int]:
            sources = compute_land_sources(name)
            if not sources:
                return (0, 0)
            colors = {c for c in sources[0] if c != "C"}
            missing_covered = len(colors - have_colors)
            return (missing_covered, len(colors))

        candidates.sort(key=score, reverse=True)
        return candidates[0]

    def _find_best_fetchable(self, typed_set: set[str]) -> str | None:
        """Find the best fetchable land in library from a typed set."""
        have_colors = set()
        for i, land in enumerate(self.battlefield_lands):
            sources = self._land_sources(land, i)
            for s in sources:
                have_colors.update(c for c in s if c != "C")

        candidates = [c for c in self.library if c in typed_set]
        if not candidates:
            return None

        def score(name: str) -> tuple[int, int]:
            sources = compute_land_sources(name)
            if not sources:
                return (0, 0)
            colors = {c for c in sources[0] if c != "C"}
            missing_covered = len(colors - have_colors)
            return (missing_covered, len(colors))

        candidates.sort(key=score, reverse=True)
        return candidates[0]

    def _reindex_after_removal(self, removed_idx: int):
        """Fix tapped_lands and thriving_choices after removing a land at index."""
        new_tapped = set()
        for t in self.tapped_lands:
            if t == removed_idx:
                continue
            new_tapped.add(t - 1 if t > removed_idx else t)
        self.tapped_lands = new_tapped

        new_choices = {}
        for idx, color in self.thriving_choices.items():
            if idx == removed_idx:
                continue
            new_choices[idx - 1 if idx > removed_idx else idx] = color
        self.thriving_choices = new_choices

    def play_turn(self, turn_number: int):
        if turn_number > 1:
            self.draw(1)

        self.tapped_lands.clear()

        hand_lands = [(self._land_play_priority(c), c) for c in self.hand if self._is_land(c)]
        hand_lands.sort(reverse=True)

        if hand_lands:
            _, land_name = hand_lands[0]
            self.hand.remove(land_name)

            # Fetch lands: crack immediately, fetch best basic
            # Fabled Passage: untapped if 4+ lands (3 others + the fetched one)
            if land_name in FETCH_LANDS:
                target = self._find_best_fetchable_basic()
                if target:
                    self.library.remove(target)
                    self.battlefield_lands.append(target)
                    if land_name == "Fabled Passage" and len(self.battlefield_lands) >= 4:
                        pass  # enters untapped
                    else:
                        self.tapped_lands.add(len(self.battlefield_lands) - 1)

            # Simic Growth Chamber: ETB tapped, bounce worst land
            elif land_name == "Simic Growth Chamber":
                self.battlefield_lands.append(land_name)
                self.tapped_lands.add(len(self.battlefield_lands) - 1)
                if len(self.battlefield_lands) > 1:
                    worst_idx = 0
                    worst_score = float("inf")
                    for i, l in enumerate(self.battlefield_lands[:-1]):
                        sources = self._land_sources(l, i)
                        n_colors = sum(1 for c in "WUBRG"
                                       if any(c in s for s in sources))
                        if n_colors < worst_score:
                            worst_score = n_colors
                            worst_idx = i
                    bounced = self.battlefield_lands.pop(worst_idx)
                    self.hand.append(bounced)
                    self._reindex_after_removal(worst_idx)

            # Normal land play
            else:
                tapped = land_enters_tapped(land_name, self.battlefield_lands, self.hand)
                self.battlefield_lands.append(land_name)
                if tapped:
                    self.tapped_lands.add(len(self.battlefield_lands) - 1)

                # Assign Thriving land color on ETB
                if land_name in THRIVING_LANDS:
                    idx = len(self.battlefield_lands) - 1
                    base_color = THRIVING_LANDS[land_name]
                    chosen = self._choose_thriving_color(base_color)
                    self.thriving_choices[idx] = chosen

        pool = self.compute_mana_pool()
        self._try_cast_rocks(pool)

        pool = self.compute_mana_pool()
        self._try_cast_ramp(pool)

        self.mana_per_turn.append(self.compute_mana_pool())

    def _try_cast_ramp(self, pool: ManaPool):
        """Try to cast one ramp spell from hand, fetching a land to battlefield."""
        ramp_in_hand = [(name, RAMP_DEFS[name]) for name in self.hand
                        if name in RAMP_DEFS]
        ramp_in_hand.sort(key=lambda x: parse_mana_cost(x[1]["mana_cost"])["total"])

        for ramp_name, rdef in ramp_in_hand:
            pips = parse_mana_cost(rdef["mana_cost"])
            if not pool.can_cast(pips):
                continue

            fetch_type = rdef["fetch_type"]

            if fetch_type == "forest_typed":
                target = self._find_best_fetchable(FOREST_TYPED_LANDS)
            elif fetch_type == "basic_plus_hand":
                target = self._find_best_fetchable(BASIC_LANDS)
            else:
                continue

            if target is None:
                continue

            pool = pool.after_spending(pips)
            self.hand.remove(ramp_name)
            self.library.remove(target)
            self.battlefield_lands.append(target)
            if rdef["tapped"]:
                self.tapped_lands.add(len(self.battlefield_lands) - 1)

            # basic_plus_hand: also fetch a second basic to hand
            if fetch_type == "basic_plus_hand":
                second = self._find_best_fetchable(BASIC_LANDS)
                if second:
                    self.library.remove(second)
                    self.hand.append(second)

            return

    def _try_cast_rocks(self, pool: ManaPool):
        priority_order = [
            "Sol Ring",
            "Arcane Signet",
            "Chromatic Lantern",
        ]

        for rock_name in priority_order:
            if rock_name not in self.hand or rock_name not in ROCK_DEFS:
                continue
            rdef = ROCK_DEFS[rock_name]

            pips = parse_mana_cost(
                self.metadata.get(rock_name, {}).get("mana_cost", ""))
            if pool.can_cast(pips):
                pool = pool.after_spending(pips)
                self.hand.remove(rock_name)
                self.battlefield_rocks.append(rock_name)
                for _ in range(rdef["count"]):
                    pool.sources.append(rdef["colors"])


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
                          classified: dict, deck_name: str) -> tuple:
    print("=" * 65)
    print(f"STATIC ANALYSIS — {deck_name.upper()}")
    print("=" * 65)

    print(f"\n--- Deck Composition ---")
    print(f"Total cards (excl. commander): {len(decklist)}")
    print(f"Lands: {len(classified['lands'])}")
    print(f"Mana rocks: {len(classified['rocks'])}")
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

    cmc_hist = Counter(cmcs)
    print(f"\n  CMC histogram:")
    max_cmc = max(cmc_hist.keys()) if cmc_hist else 0
    for cmc_val in range(0, max_cmc + 1):
        count = cmc_hist.get(cmc_val, 0)
        if count > 0:
            bar = "#" * count
            print(f"    {cmc_val:>2} CMC: {count:>2} {bar}")

    total_W, total_U, total_B, total_R, total_G = 0, 0, 0, 0, 0
    for name in decklist:
        meta = metadata.get(name, {})
        mc = meta.get("mana_cost", "")
        if "Land" in meta.get("type_line", ""):
            continue
        pips = parse_mana_cost(mc)
        total_W += pips["W"]
        total_U += pips["U"]
        total_B += pips["B"]
        total_R += pips["R"]
        total_G += pips["G"]

    total_pips = total_W + total_U + total_B + total_R + total_G
    if total_pips > 0:
        print(f"\n--- Pip Demand ---")
        print(f"  Total {{W}}: {total_W}  {{U}}: {total_U}  {{B}}: {total_B}"
              f"  {{R}}: {total_R}  {{G}}: {total_G}")
        print(f"  Ratio: {total_W/total_pips*100:.0f}% W / {total_U/total_pips*100:.0f}% U / "
              f"{total_B/total_pips*100:.0f}% B / {total_R/total_pips*100:.0f}% R / "
              f"{total_G/total_pips*100:.0f}% G")

    lands = classified["lands"]
    w_lands, u_lands, b_lands, r_lands, g_lands, c_only = 0, 0, 0, 0, 0, 0
    for l in lands:
        sources = compute_land_sources(l)
        if not sources:
            continue
        colors = sources[0]
        if "W" in colors:
            w_lands += 1
        if "U" in colors:
            u_lands += 1
        if "B" in colors:
            b_lands += 1
        if "R" in colors:
            r_lands += 1
        if "G" in colors:
            g_lands += 1
        if colors == frozenset({"C"}):
            c_only += 1

    print(f"\n--- Mana Source Inventory ---")
    print(f"  Lands: {len(lands)} total")
    print(f"    W: {w_lands}  U: {u_lands}  B: {b_lands}  R: {r_lands}  G: {g_lands}"
          f"  C-only: {c_only}")

    return avg_cmc, total_W, total_U, total_B, total_R, total_G


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
    r_by_turn = {t: [] for t in range(1, NUM_TURNS + 1)}
    g_by_turn = {t: [] for t in range(1, NUM_TURNS + 1)}
    hand_land_counts = Counter()
    mulligan_attempts = Counter()

    zero_w_by_turn = {t: 0 for t in range(1, NUM_TURNS + 1)}
    zero_u_by_turn = {t: 0 for t in range(1, NUM_TURNS + 1)}
    zero_b_by_turn = {t: 0 for t in range(1, NUM_TURNS + 1)}
    zero_r_by_turn = {t: 0 for t in range(1, NUM_TURNS + 1)}
    zero_g_by_turn = {t: 0 for t in range(1, NUM_TURNS + 1)}

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
            w_by_turn[t].append(pool.count_color("W"))
            u_by_turn[t].append(pool.count_color("U"))
            b_by_turn[t].append(pool.count_color("B"))
            r_by_turn[t].append(pool.count_color("R"))
            g_by_turn[t].append(pool.count_color("G"))

            if pool.count_color("W") == 0:
                zero_w_by_turn[t] += 1
            if pool.count_color("U") == 0:
                zero_u_by_turn[t] += 1
            if pool.count_color("B") == 0:
                zero_b_by_turn[t] += 1
            if pool.count_color("R") == 0:
                zero_r_by_turn[t] += 1
            if pool.count_color("G") == 0:
                zero_g_by_turn[t] += 1

            # Commander: Donatello, the Brains {2}{U}
            cmd_pips = {"generic": 2, "U": 1}
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
        "u_by_turn": u_by_turn,
        "b_by_turn": b_by_turn,
        "r_by_turn": r_by_turn,
        "g_by_turn": g_by_turn,
        "hand_land_counts": hand_land_counts,
        "mulligan_attempts": mulligan_attempts,
        "zero_w_by_turn": zero_w_by_turn,
        "zero_u_by_turn": zero_u_by_turn,
        "zero_b_by_turn": zero_b_by_turn,
        "zero_r_by_turn": zero_r_by_turn,
        "zero_g_by_turn": zero_g_by_turn,
        "commander_castable_turn": commander_castable_turn,
        "commander_by_turn": commander_by_turn,
        "castable_spell_by_turn": castable_spell_by_turn,
        "curve_out_games": curve_out_games,
        "tapped_land_turns": tapped_land_turns,
    }


# --- Results ---


def print_results(stats: dict, classified: dict,
                  avg_cmc: float, pip_W: int, pip_U: int, pip_B: int,
                  pip_R: int, pip_G: int, deck_name: str):
    total = NUM_GAMES

    print("\n" + "=" * 65)
    print(f"MONTE CARLO SIMULATION — {deck_name.upper()} ({NUM_GAMES:,} games, {NUM_TURNS} turns)")
    print("=" * 65)

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
    print(f"    Free mulligan used:  {mull.get(1, 0)/total*100:>5.1f}%")
    print(f"    Paid mulligan (→6):  {mull.get(2, 0)/total*100:>5.1f}%")

    print(f"\n--- Dimension 2: Color Balance ---")
    print(f"\n  W, U, B, R, G sources per turn (median):")
    print(f"  {'Turn':<6} {'W':>4} {'U':>4} {'B':>4} {'R':>4} {'G':>4}")
    print(f"  {'-'*30}")
    for t in range(1, NUM_TURNS + 1):
        w_med = statistics.median(stats["w_by_turn"][t])
        u_med = statistics.median(stats["u_by_turn"][t])
        b_med = statistics.median(stats["b_by_turn"][t])
        r_med = statistics.median(stats["r_by_turn"][t])
        g_med = statistics.median(stats["g_by_turn"][t])
        print(f"    T{t:<4} {w_med:>4.0f} {u_med:>4.0f} {b_med:>4.0f} {r_med:>4.0f} {g_med:>4.0f}")

    print(f"\n  Color screw (0 sources of a color):")
    for t in range(2, NUM_TURNS + 1):
        w_pct = stats["zero_w_by_turn"][t] / total * 100
        u_pct = stats["zero_u_by_turn"][t] / total * 100
        b_pct = stats["zero_b_by_turn"][t] / total * 100
        r_pct = stats["zero_r_by_turn"][t] / total * 100
        g_pct = stats["zero_g_by_turn"][t] / total * 100
        print(f"    T{t}: 0W={w_pct:.1f}% 0U={u_pct:.1f}% 0B={b_pct:.1f}%"
              f" 0R={r_pct:.1f}% 0G={g_pct:.1f}%")

    print(f"\n--- Dimension 3: Curve Efficiency ---")
    print(f"\n  Commander castable (Donatello, {{2}}{{U}}):")
    for t in range(2, NUM_TURNS + 1):
        count = stats["commander_by_turn"][t]
        print(f"    By T{t}: {count/total*100:.1f}%")
    if stats["commander_castable_turn"]:
        med = statistics.median(stats["commander_castable_turn"])
        print(f"    Median turn: {med:.1f}")

    print(f"\n  ETB tapped frequency:")
    for t in [1, 2]:
        pct_val = stats["tapped_land_turns"][t] / total * 100
        print(f"    T{t} land entered tapped: {pct_val:.1f}%")


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


def main():
    with open(METADATA_FILE) as f:
        metadata = json.load(f)

    deck_id = "mutant-multiplication"
    deck_name = "Mutant Multiplication"
    deck_file = PROJECT_ROOT / "data" / "commanders" / deck_id / "deck.json"

    with open(deck_file) as f:
        deck_data = json.load(f)

    print(f"\nBuilding {deck_name} decklist...")
    decklist = build_decklist(deck_data)
    print(f"Decklist: {len(decklist)} cards")

    classified = classify_cards(decklist, metadata)
    result = print_static_analysis(decklist, metadata, classified, deck_name)
    avg_cmc, pip_W, pip_U, pip_B, pip_R, pip_G = result

    n_workers = os.cpu_count() or 4
    chunk_size = NUM_GAMES // n_workers
    remainder = NUM_GAMES % n_workers
    chunks = [chunk_size + (1 if i < remainder else 0) for i in range(n_workers)]

    print(f"\nRunning {NUM_GAMES:,} game simulations ({n_workers} workers)...")
    with multiprocessing.Pool(n_workers) as pool:
        results = pool.map(_run_chunk, [(decklist, metadata, n) for n in chunks])
    stats = merge_stats(results)

    print_results(stats, classified, avg_cmc, pip_W, pip_U, pip_B, pip_R, pip_G,
                  deck_name)
    print("\n" + "=" * 65)


if __name__ == "__main__":
    main()
