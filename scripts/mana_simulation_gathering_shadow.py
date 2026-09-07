#!/usr/bin/env python3
"""Monte Carlo mana base simulation for Gathering Shadow (Sauron, the Dark Lord).

Simulates 100,000 games measuring mana production, color balance, and curve
efficiency turns 1-10 for the Grixis amass + Ring-temptation decklist
(DEC-533 remake, bracket 4-).

Commander: Sauron, the Dark Lord ({3}{U}{B}{R}, CMC 6)
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
DECK_FILE = PROJECT_ROOT / "data" / "commanders" / "gathering-shadow" / "deck.json"
METADATA_FILE = PROJECT_ROOT / "data" / "card-metadata.json"
JSON_OUTPUT = PROJECT_ROOT / "data" / "commanders" / "gathering-shadow" / "simulation.json"

NUM_GAMES = 100_000
NUM_TURNS = 10

# --- Mana cost parser ---


def parse_mana_cost(mana_cost: str) -> dict:
    """Parse mana_cost string into pip breakdown.

    "{3}{U}{B}{R}" -> {generic: 3, U: 1, B: 1, R: 1, total: 6}
    "{U}{U}{B}" -> {generic: 0, U: 2, B: 1, R: 0, total: 3}

    Split cards (//): parse first half only.
    """
    if "//" in mana_cost:
        mana_cost = mana_cost.split("//")[0].strip()

    result = {"generic": 0, "U": 0, "B": 0, "R": 0, "total": 0, "X": False}
    symbols = re.findall(r"\{([^}]+)\}", mana_cost)
    for sym in symbols:
        if sym == "X":
            result["X"] = True
        elif sym.isdigit():
            result["generic"] += int(sym)
        elif sym in ("U", "B", "R"):
            result[sym] += 1
        # Ignore other symbols (hybrid, phyrexian, etc.)
    result["total"] = result["generic"] + result["U"] + result["B"] + result["R"]
    return result


# --- Rock definitions ---
# "count" = net mana atoms produced. Sol Ring taps for {C}{C} = 2 atoms.
# Signets ({1},{T} -> 2 colored) net +1. Talismans tap for 1 colored. Others tap for 1.

ROCK_DEFS = {
    "Sol Ring":               {"cmc": 1, "colors": frozenset({"C"}), "count": 2, "burst": False},
    "Arcane Signet":          {"cmc": 2, "colors": frozenset({"U", "B", "R"}), "count": 1, "burst": False},
    "Talisman of Indulgence": {"cmc": 2, "colors": frozenset({"B", "R"}), "count": 1, "burst": False},
    "Talisman of Dominance":  {"cmc": 2, "colors": frozenset({"U", "B"}), "count": 1, "burst": False},
    "Relic of Sauron":        {"cmc": 4, "colors": frozenset({"U", "B", "R"}), "count": 2, "burst": False},
    "Talisman of Creativity": {"cmc": 2, "colors": frozenset({"U", "R"}), "count": 1, "burst": False},
    # Chrome Mox: {0}, taps for the imprinted card's color. 49/99 colored
    # nonartifact spells make fuel near-certain (~98.7% with Mox in hand), so
    # the imprint requirement and card loss are not modeled.
    "Chrome Mox":             {"cmc": 0, "colors": frozenset({"U", "B", "R"}), "count": 1, "burst": False},
    # Dark Ritual is a one-shot ritual, not a standing source; this sim has no
    # burst-mana support, so it is deliberately left unmodeled (conservative).
}

# --- Land subtype definitions (for check lands and fetch targets) ---

ISLAND_TYPED_LANDS = {"Island", "Watery Grave", "Steam Vents", "Sunken Hollow", "Turbulent Springs"}
SWAMP_TYPED_LANDS = {"Swamp", "Watery Grave", "Blood Crypt", "Sunken Hollow", "Smoldering Marsh"}
MOUNTAIN_TYPED_LANDS = {"Mountain", "Blood Crypt", "Steam Vents", "Smoldering Marsh", "Turbulent Springs"}

FETCH_LANDS = {"Bloodstained Mire", "Polluted Delta"}

ALWAYS_TAPPED = {
    "Bojuka Bog",
    "Minas Morgul, Dark Fortress",
    "Barad-dûr",  # tapped w/o legendary creature (not tracked — conservative)
    # The Black Gate: pay 3 life to enter untapped — this deck always pays.
}


def land_enters_tapped(name: str, battlefield_lands: list[str], hand: list[str]) -> bool:
    """Determine if a land enters tapped given current board and hand."""
    if name in ALWAYS_TAPPED:
        return True

    # Check lands (need matching basic land type on board)
    if name == "Drowned Catacomb":
        return not any(l in ISLAND_TYPED_LANDS or l in SWAMP_TYPED_LANDS
                       for l in battlefield_lands)
    if name == "Dragonskull Summit":
        return not any(l in SWAMP_TYPED_LANDS or l in MOUNTAIN_TYPED_LANDS
                       for l in battlefield_lands)
    if name == "Sulfur Falls":
        return not any(l in ISLAND_TYPED_LANDS or l in MOUNTAIN_TYPED_LANDS
                       for l in battlefield_lands)
    # Fast lands: untapped if ≤2 lands on battlefield
    if name in {"Darkslick Shores", "Blackcleave Cliffs"}:
        return len(battlefield_lands) > 2
    # Slow land: untapped with two or more other lands
    if name == "Stormcarved Coast":
        return len(battlefield_lands) < 2
    # Turbulent Springs: untapped once opponents control 8+ lands. Opponent
    # boards are not tracked; under the vanilla 4-player model that holds from
    # your turn 4 in every seat (turn 3 only in seats 3-4), so gate on this
    # being at least the 4th land drop (conservative: drops the turn-3 case).
    if name == "Turbulent Springs":
        return len(battlefield_lands) < 3

    # Battle lands (need 2+ basics with the right types)
    if name == "Smoldering Marsh":
        basics = sum(1 for l in battlefield_lands
                     if l in SWAMP_TYPED_LANDS or l in MOUNTAIN_TYPED_LANDS)
        return basics < 2
    if name == "Sunken Hollow":
        basics = sum(1 for l in battlefield_lands
                     if l in ISLAND_TYPED_LANDS or l in SWAMP_TYPED_LANDS)
        return basics < 2

    # Gloomlake Verge: always enters untapped (color production is conditional, not ETB)
    # Shock lands (Watery Grave, Blood Crypt, Steam Vents): always untapped (pay 2 life)
    # Bond lands (Morphic Pool, Luxury Suite, Training Center): always untapped (2+ opponents)
    # Command Tower, Exotic Orchard, Mount Doom, utility lands: always untapped
    return False


def compute_land_sources(name: str, battlefield_lands: list[str]) -> list[frozenset]:
    """Return mana sources (frozensets of producible colors) for a single untapped land.

    Each frozenset in the returned list represents one mana atom.
    Most lands return a single atom; special lands may return 0.
    """
    # Basics
    if name == "Swamp":
        return [frozenset({"B"})]
    if name == "Island":
        return [frozenset({"U"})]
    if name == "Mountain":
        return [frozenset({"R"})]

    # Tri-color lands
    if name in {"Command Tower", "Exotic Orchard"}:
        return [frozenset({"U", "B", "R"})]

    # UB duals
    if name in {"Watery Grave", "Morphic Pool", "Drowned Catacomb", "Sunken Hollow",
                "Underground River", "Darkslick Shores"}:
        return [frozenset({"U", "B"})]

    # BR duals
    if name in {"Blood Crypt", "Luxury Suite", "Smoldering Marsh", "Sulfurous Springs",
                "Dragonskull Summit", "Blackcleave Cliffs"}:
        return [frozenset({"B", "R"})]

    # UR duals (Cascade Bluffs filters colored mana — nearly always usable with
    # 20+ colored sources in the base; the T1-only-land corner is optimistic)
    if name in {"Steam Vents", "Training Center", "Sulfur Falls", "Shivan Reef",
                "Stormcarved Coast", "Cascade Bluffs", "Turbulent Springs"}:
        return [frozenset({"U", "R"})]

    # Gloomlake Verge: {U} always; {B} only with Island or Swamp in play
    if name == "Gloomlake Verge":
        has_typed = any(l in ISLAND_TYPED_LANDS or l in SWAMP_TYPED_LANDS
                        for l in battlefield_lands if l != name)
        if has_typed:
            return [frozenset({"U", "B"})]
        return [frozenset({"U"})]

    # Single-color lands
    if name == "Bojuka Bog":
        return [frozenset({"B"})]
    # Urborg makes every land a Swamp; itself taps for {B}
    if name == "Urborg, Tomb of Yawgmoth":
        return [frozenset({"B"})]

    # LotR legendary lands — produce colored mana
    if name in {"Barad-dûr", "The Black Gate", "Minas Morgul, Dark Fortress"}:
        return [frozenset({"B"})]
    if name == "Mount Doom":
        return [frozenset({"B", "R"})]

    # Channel lands (legendary, produce colored mana)
    if name == "Otawara, Soaring City":
        return [frozenset({"U"})]
    if name == "Takenuma, Abandoned Mire":
        return [frozenset({"B"})]

    # Fetches should be cracked; if somehow on board, no mana
    if name in FETCH_LANDS:
        return []

    # Fallback: colorless
    return [frozenset({"C"})]


# --- ManaPool (source-based for 3-color mana) ---


class ManaPool:
    """Tracks available mana as a list of source atoms.

    Each source is a frozenset of colors it can produce (one mana).
    e.g. frozenset({"U","B"}) = one mana that can be U or B.
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
        needed = {"U": pips.get("U", 0), "B": pips.get("B", 0), "R": pips.get("R", 0)}
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
            for color in "UBR":
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
    """Build 99-card decklist for Gathering Shadow.

    Reads the flat decklist array directly. Each entry has {name, type} with
    optional quantity field. Commander is in the command zone (not in decklist).
    """
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

    def draw(self, n: int = 1):
        for _ in range(n):
            if self.library:
                self.hand.append(self.library.pop())

    def count_lands_in_hand(self) -> int:
        return sum(1 for c in self.hand if c in self.land_set)

    def _is_land(self, name: str) -> bool:
        return name in self.land_set

    def _land_play_priority(self, name: str) -> float:
        """Higher = play first. Untapped > tapped. Color-fixing > mono."""
        if name in FETCH_LANDS:
            return 20  # Always play and crack immediately

        tapped = land_enters_tapped(name, self.battlefield_lands, self.hand)
        base = 0 if tapped else 10

        # More colors produced = higher priority
        sources = compute_land_sources(name, self.battlefield_lands)
        if sources:
            n_colors = sum(1 for c in "UBR" if c in sources[0])
            base += n_colors * 2

        return base

    def _resolve_fetch(self, fetch_name: str):
        """Resolve Bloodstained Mire or Scalding Tarn."""
        if fetch_name == "Bloodstained Mire":
            fetchable_types = SWAMP_TYPED_LANDS | MOUNTAIN_TYPED_LANDS
        elif fetch_name == "Polluted Delta":
            fetchable_types = ISLAND_TYPED_LANDS | SWAMP_TYPED_LANDS
        else:
            return

        fetchable = [(i, card) for i, card in enumerate(self.library)
                     if card in fetchable_types]
        if not fetchable:
            return

        # Count current color sources
        pool = self.compute_mana_pool()
        u_src = pool.count_color("U")
        b_src = pool.count_color("B")
        r_src = pool.count_color("R")
        min_color = min(u_src, b_src, r_src)

        # Early game (≤2 lands): prefer shock dual for best fixing
        if len(self.battlefield_lands) <= 2:
            # Shock duals enter untapped and fix 2 colors
            if u_src == min_color:
                shock_pref = ["Watery Grave", "Steam Vents"]
            elif b_src == min_color:
                shock_pref = ["Watery Grave", "Blood Crypt"]
            else:
                shock_pref = ["Steam Vents", "Blood Crypt"]

            for target in shock_pref:
                matches = [(i, c) for i, c in fetchable if c == target]
                if matches:
                    idx, card = matches[0]
                    self.library.pop(idx)
                    self.battlefield_lands.append(card)
                    return

        # Fetch basic matching worst color deficit
        if u_src == min_color:
            basics = [(i, c) for i, c in fetchable if c == "Island"]
        elif b_src == min_color:
            basics = [(i, c) for i, c in fetchable if c == "Swamp"]
        else:
            basics = [(i, c) for i, c in fetchable if c == "Mountain"]

        if basics:
            idx, card = basics[0]
            self.library.pop(idx)
            self.battlefield_lands.append(card)
            return

        # Fallback: first available
        idx, card = fetchable[0]
        self.library.pop(idx)
        self.battlefield_lands.append(card)

    def compute_mana_pool(self) -> ManaPool:
        """Calculate total available mana from all untapped lands + rocks."""
        pool_sources: list[frozenset] = []

        for i, land in enumerate(self.battlefield_lands):
            if i in self.tapped_lands:
                continue
            sources = compute_land_sources(land, self.battlefield_lands)
            pool_sources.extend(sources)

        for rock in self.battlefield_rocks:
            rdef = ROCK_DEFS[rock]
            for _ in range(rdef["count"]):
                pool_sources.append(rdef["colors"])

        return ManaPool(pool_sources)

    def play_turn(self, turn_number: int):
        """Simulate one turn."""
        # Draw (skip T1)
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

            if land_name in FETCH_LANDS:
                self._resolve_fetch(land_name)
            else:
                tapped = land_enters_tapped(land_name, self.battlefield_lands, self.hand)
                self.battlefield_lands.append(land_name)
                if tapped:
                    self.tapped_lands.add(len(self.battlefield_lands) - 1)

        # Cast rocks from hand
        pool = self.compute_mana_pool()
        self._try_cast_rocks(pool)

        # Record final mana pool
        self.mana_per_turn.append(self.compute_mana_pool())

    def _try_cast_rocks(self, pool: ManaPool):
        """Try to cast mana rocks from hand, priority order (lowest CMC first)."""
        priority_order = [
            "Chrome Mox",  # free, so always first
            "Sol Ring",
            "Arcane Signet",
            "Talisman of Dominance", "Talisman of Indulgence", "Talisman of Creativity",
            "Relic of Sauron",
        ]

        for rock_name in priority_order:
            if rock_name not in self.hand:
                continue
            rdef = ROCK_DEFS[rock_name]
            pips = parse_mana_cost(
                self.metadata.get(rock_name, {}).get("mana_cost", ""))
            if pool.can_cast(pips):
                pool = pool.after_spending(pips)
                self.hand.remove(rock_name)
                self.battlefield_rocks.append(rock_name)
                # Add rock's mana production to pool for subsequent casts
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
    """Print pre-simulation static analysis. Returns (avg_cmc, pip_U, pip_B, pip_R)."""
    print("=" * 65)
    print("STATIC ANALYSIS — DARK DOMINION (BRACKET 4)")
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

    # Pip counts
    total_U, total_B, total_R = 0, 0, 0
    for name in decklist:
        meta = metadata.get(name, {})
        mc = meta.get("mana_cost", "")
        if "Land" in meta.get("type_line", ""):
            continue
        pips = parse_mana_cost(mc)
        total_U += pips["U"]
        total_B += pips["B"]
        total_R += pips["R"]

    total_pips = total_U + total_B + total_R
    u_ratio = total_U / total_pips * 100 if total_pips > 0 else 0
    b_ratio = total_B / total_pips * 100 if total_pips > 0 else 0
    r_ratio = total_R / total_pips * 100 if total_pips > 0 else 0

    print(f"\n--- Pip Demand ---")
    print(f"  Total {{U}} pips: {total_U}")
    print(f"  Total {{B}} pips: {total_B}")
    print(f"  Total {{R}} pips: {total_R}")
    print(f"  Ratio: {u_ratio:.0f}% U / {b_ratio:.0f}% B / {r_ratio:.0f}% R")

    # Mana source inventory
    lands = classified["lands"]
    u_lands, b_lands, r_lands, c_only = 0, 0, 0, 0
    for l in lands:
        sources = compute_land_sources(l, [])  # empty board for static count
        if not sources:
            continue
        colors = sources[0]
        if "U" in colors:
            u_lands += 1
        if "B" in colors:
            b_lands += 1
        if "R" in colors:
            r_lands += 1
        if colors == frozenset({"C"}):
            c_only += 1

    def _count_pair(pair):
        return sum(1 for l in lands
                   if compute_land_sources(l, [])
                   and pair <= compute_land_sources(l, [])[0])

    ubr_lands = _count_pair({"U", "B", "R"})
    ub_lands = _count_pair({"U", "B"}) - ubr_lands
    br_lands = _count_pair({"B", "R"}) - ubr_lands
    ur_lands = _count_pair({"U", "R"}) - ubr_lands
    fetch_count = sum(1 for l in lands if l in FETCH_LANDS)

    print(f"\n--- Mana Source Inventory ---")
    print(f"  Lands: {len(lands)} total")
    print(f"    U-producing: {u_lands}  B-producing: {b_lands}  R-producing: {r_lands}")
    print(f"    UBR tri-lands: {ubr_lands}")
    print(f"    UB duals: {ub_lands}  BR duals: {br_lands}  UR duals: {ur_lands}")
    print(f"    C-only: {c_only}  Fetch: {fetch_count}")

    # Rock inventory
    rocks = classified["rocks"]
    ubr_rocks = sum(1 for r in rocks if ROCK_DEFS[r]["colors"] >= {"U", "B", "R"})
    ub_rocks = sum(1 for r in rocks if ROCK_DEFS[r]["colors"] == frozenset({"U", "B"}))
    br_rocks = sum(1 for r in rocks if ROCK_DEFS[r]["colors"] == frozenset({"B", "R"}))
    ur_rocks = sum(1 for r in rocks if ROCK_DEFS[r]["colors"] == frozenset({"U", "R"}))
    c_rocks = sum(1 for r in rocks if ROCK_DEFS[r]["colors"] == frozenset({"C"}))
    net_mana = sum(ROCK_DEFS[r]["count"] for r in rocks)
    print(f"  Rocks: {len(rocks)} total ({net_mana} net mana)")
    print(f"    UBR-flex: {ubr_rocks}  UB: {ub_rocks}  BR: {br_rocks}  UR: {ur_rocks}  C: {c_rocks}")

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

    return avg_cmc, total_U, total_B, total_R


# --- Simulation ---


def run_simulation(decklist: list[str], metadata: dict, num_games: int = NUM_GAMES) -> dict:
    """Run num_games simulations and collect stats."""
    land_set = set()
    for name in set(decklist):
        meta = metadata.get(name, {})
        if "Land" in meta.get("type_line", ""):
            land_set.add(name)

    mana_by_turn = {t: [] for t in range(1, NUM_TURNS + 1)}
    u_by_turn = {t: [] for t in range(1, NUM_TURNS + 1)}
    b_by_turn = {t: [] for t in range(1, NUM_TURNS + 1)}
    r_by_turn = {t: [] for t in range(1, NUM_TURNS + 1)}
    hand_land_counts = Counter()
    mulligan_attempts = Counter()

    zero_u_by_turn = {t: 0 for t in range(1, NUM_TURNS + 1)}
    zero_b_by_turn = {t: 0 for t in range(1, NUM_TURNS + 1)}
    zero_r_by_turn = {t: 0 for t in range(1, NUM_TURNS + 1)}

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
            b_by_turn[t].append(pool.count_color("B"))
            r_by_turn[t].append(pool.count_color("R"))

            if pool.count_color("U") == 0:
                zero_u_by_turn[t] += 1
            if pool.count_color("B") == 0:
                zero_b_by_turn[t] += 1
            if pool.count_color("R") == 0:
                zero_r_by_turn[t] += 1

            # Commander: Sauron, the Dark Lord {3}{U}{B}{R}
            cmd_pips = {"generic": 3, "U": 1, "B": 1, "R": 1}
            if cmd_cast_turn is None and pool.can_cast(cmd_pips):
                cmd_cast_turn = t
                commander_by_turn[t] += 1

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
        "b_by_turn": b_by_turn,
        "r_by_turn": r_by_turn,
        "hand_land_counts": hand_land_counts,
        "mulligan_attempts": mulligan_attempts,
        "zero_u_by_turn": zero_u_by_turn,
        "zero_b_by_turn": zero_b_by_turn,
        "zero_r_by_turn": zero_r_by_turn,
        "commander_castable_turn": commander_castable_turn,
        "commander_by_turn": commander_by_turn,
        "castable_spell_by_turn": castable_spell_by_turn,
        "curve_out_games": curve_out_games,
        "tapped_land_turns": tapped_land_turns,
    }


# --- Results ---


def print_results(stats: dict, classified: dict,
                  avg_cmc: float, pip_U: int, pip_B: int, pip_R: int):
    """Print simulation results across all three dimensions."""
    total = NUM_GAMES

    print("\n" + "=" * 65)
    print(f"MONTE CARLO SIMULATION — DARK DOMINION ({NUM_GAMES:,} games, {NUM_TURNS} turns)")
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
    print(f"\n  U, B, R sources per turn (can-produce count):")
    print(f"  {'Turn':<6} {'U med':>6} {'U avg':>6} {'B med':>6} {'B avg':>6} {'R med':>6} {'R avg':>6}")
    print(f"  {'-'*42}")
    for t in range(1, NUM_TURNS + 1):
        u_med = statistics.median(stats["u_by_turn"][t])
        u_mean = statistics.mean(stats["u_by_turn"][t])
        b_med = statistics.median(stats["b_by_turn"][t])
        b_mean = statistics.mean(stats["b_by_turn"][t])
        r_med = statistics.median(stats["r_by_turn"][t])
        r_mean = statistics.mean(stats["r_by_turn"][t])
        print(f"    T{t:<4} {u_med:>6.0f} {u_mean:>6.1f} {b_med:>6.0f} {b_mean:>6.1f} {r_med:>6.0f} {r_mean:>6.1f}")

    print(f"\n  Color screw (0 sources of a color):")
    for t in range(2, NUM_TURNS + 1):
        u_pct = stats["zero_u_by_turn"][t] / total * 100
        b_pct = stats["zero_b_by_turn"][t] / total * 100
        r_pct = stats["zero_r_by_turn"][t] / total * 100
        print(f"    T{t}: 0 U = {u_pct:.1f}%, 0 B = {b_pct:.1f}%, 0 R = {r_pct:.1f}%")

    pip_total = pip_U + pip_B + pip_R
    u_demand = pip_U / pip_total * 100 if pip_total > 0 else 0
    b_demand = pip_B / pip_total * 100 if pip_total > 0 else 0
    r_demand = pip_R / pip_total * 100 if pip_total > 0 else 0

    t3_u = statistics.mean(stats["u_by_turn"][3])
    t3_b = statistics.mean(stats["b_by_turn"][3])
    t3_r = statistics.mean(stats["r_by_turn"][3])
    t3_total = t3_u + t3_b + t3_r
    u_supply = t3_u / t3_total * 100 if t3_total > 0 else 0
    b_supply = t3_b / t3_total * 100 if t3_total > 0 else 0
    r_supply = t3_r / t3_total * 100 if t3_total > 0 else 0

    print(f"\n  Pip demand vs supply ratio (T3 avg):")
    print(f"    Demand: {u_demand:.0f}% U / {b_demand:.0f}% B / {r_demand:.0f}% R")
    print(f"    Supply: {u_supply:.0f}% U / {b_supply:.0f}% B / {r_supply:.0f}% R")

    # --- Dimension 3: Curve Efficiency ---
    print(f"\n--- Dimension 3: Curve Efficiency ---")

    print(f"\n  Commander castable (Sauron, the Dark Lord, {{3}}{{U}}{{B}}{{R}}):")
    for t in range(3, NUM_TURNS + 1):
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
                                  ("B", b_demand, b_supply),
                                  ("R", r_demand, r_supply)]:
        deficit = demand - supply
        if deficit > max_deficit:
            max_deficit = deficit
            worst_color = color

    if max_deficit < 10:
        print(f"  Color balance: well-matched (all within {max_deficit:.0f}% demand-supply gap)")
    else:
        print(f"  Color balance: {worst_color} undersupplied "
              f"({max_deficit:.0f}% gap) — consider more {worst_color} sources")

    # Commander timing
    cmd_by_t5 = stats["commander_by_turn"][5] / total * 100
    cmd_by_t6 = stats["commander_by_turn"][6] / total * 100
    if cmd_by_t5 > 50:
        print(f"  Commander by T5: {cmd_by_t5:.0f}% — ahead of curve for 6-CMC")
    elif cmd_by_t6 > 50:
        print(f"  Commander by T6: {cmd_by_t6:.0f}% — on curve for 6-CMC commander")
    else:
        print(f"  Commander by T6: {cmd_by_t6:.0f}% — below 50%, ramp insufficient for 6-CMC")

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

    result = exporter.export_grixis(metadata)
    if not exporter.validate_output(result, "gathering-shadow"):
        raise ValueError("export_grixis produced invalid simulation output")
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Monte Carlo mana base simulation for Gathering Shadow (Sauron)")
    parser.add_argument("--json", action="store_true",
                        help="Write simulation.json instead of console output")
    args = parser.parse_args()

    with open(DECK_FILE) as f:
        deck_data = json.load(f)
    with open(METADATA_FILE) as f:
        metadata = json.load(f)

    print("Building Gathering Shadow decklist...")
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

    avg_cmc, pip_U, pip_B, pip_R = print_static_analysis(decklist, metadata, classified)

    n_workers = os.cpu_count() or 4
    chunk_size = NUM_GAMES // n_workers
    remainder = NUM_GAMES % n_workers
    chunks = [chunk_size + (1 if i < remainder else 0) for i in range(n_workers)]

    print(f"\nRunning {NUM_GAMES:,} game simulations ({n_workers} workers)...")
    with multiprocessing.Pool(n_workers) as pool:
        results = pool.map(_run_chunk, [(decklist, metadata, n) for n in chunks])
    stats = merge_stats(results)

    print_results(stats, classified, avg_cmc, pip_U, pip_B, pip_R)
    print("\n" + "=" * 65)


if __name__ == "__main__":
    main()
