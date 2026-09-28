#!/usr/bin/env python3
"""Monte Carlo mana base simulation for Hoard and Bleed (Smaug, Wicked Worm).

Simulates 100,000 games measuring mana production, color balance, and curve
efficiency turns 1-10 for the Bracket 4- Rakdos Treasure-aristocrats decklist.

Commander: Smaug, Wicked Worm ({3}{B}{R}, CMC 5). Its ETB makes X Treasures where
X counts artifacts OPPONENTS control, so a solitaire model cannot credit it any
mana; the commander is measured for cast timing only. Its cast trigger (draw a
card and lose 1 life when Treasure mana pays for a spell) is likewise outside a
mana model.

Modeling choices that are deliberately conservative, so the deck is never
credited with mana it may not have:

- Treasure tokens are NOT modeled as mana. The deck makes many of them, but they
  come from spells this simulation only checks for castability, not resolution.
  Read every mana number here as the floor the land base alone supports.
- Lotus Petal is a one-shot. It is credited on the turn it is played and never
  again. Holding it for a later turn is the stronger real line, so this
  understates it rather than crediting a permanent +1.
- Turbulent Crater (DEC-929) enters tapped unless opponents control eight or
  more lands; modeled as untapped from the 4th land drop, conservative.
- Mines of Moria enters tapped unless you control a legendary creature. This
  model does not track the commander on the battlefield, so it always enters
  tapped.
- Exotic Orchard and Fellwar Stone read an opponent's board. In a four-player
  pod at least one opponent almost always controls a land that makes {B} or {R},
  so both are modeled as flexible B/R sources.
- Shadowblood Ridge costs {1} to make {B}{R}, a net gain of one colored mana. It
  produces nothing unless another untapped source can pay the {1}.
- Spire of Industry needs an artifact for its any-color mode. It is flexible
  while a rock is on the battlefield and colorless otherwise.
- The Mycosynth Gardens and Treasure Vault are counted as one colorless each.
  Their any-color and Treasure modes cost mana, so they add no net mana.
- Life payments (City of Brass, Mana Confluence, Sulfurous Springs, Mount Doom,
  Blood Crypt, Bloodstained Mire, Prismatic Vista, Spire of Industry) are not
  tracked. This deck runs a real life clock; see the guide's life-budget note.
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
DECK_FILE = PROJECT_ROOT / "data" / "commanders" / "hoard-and-bleed" / "deck.json"
METADATA_FILE = PROJECT_ROOT / "data" / "card-metadata.json"
JSON_OUTPUT = PROJECT_ROOT / "data" / "commanders" / "hoard-and-bleed" / "simulation.json"

NUM_GAMES = 100_000
NUM_TURNS = 10

# --- Mana cost parser ---

def parse_mana_cost(mana_cost: str) -> dict:
    """Parse mana_cost string into pip breakdown.

    "{3}{B}{R}" -> {generic: 3, B: 1, R: 1, total: 5}
    "{B}{B}{R}" -> {generic: 0, B: 2, R: 1, total: 3}
    "{X}{B}{B}" -> {generic: 0, B: 2, R: 0, total: 2, X: True}

    Split cards (//): parse first half only.
    """
    if "//" in mana_cost:
        mana_cost = mana_cost.split("//")[0].strip()

    result = {"generic": 0, "B": 0, "R": 0, "total": 0, "X": False}
    symbols = re.findall(r"\{([^}]+)\}", mana_cost)
    for sym in symbols:
        if sym == "X":
            result["X"] = True
        elif sym.isdigit():
            result["generic"] += int(sym)
        elif sym == "B":
            result["B"] += 1
        elif sym == "R":
            result["R"] += 1
        # Ignore other symbols (hybrid, phyrexian, etc.)
    result["total"] = result["generic"] + result["B"] + result["R"]
    return result


# --- Rock definitions ---
# Fellwar Stone reads an opponent's lands; modeled flexible (see module docstring).
# Lotus Petal is a one-shot, handled by PETAL_NAME below rather than as a
# standing source.

PETAL_NAME = "Lotus Petal"

ROCK_DEFS = {
    "Sol Ring":               {"cmc": 1, "B": 0, "R": 0, "C": 2, "burst": False},
    "Arcane Signet":          {"cmc": 2, "B": 1, "R": 1, "C": 0, "burst": False, "flexible": True},
    "Talisman of Indulgence": {"cmc": 2, "B": 1, "R": 1, "C": 0, "burst": False, "flexible": True},
    "Fellwar Stone":          {"cmc": 2, "B": 1, "R": 1, "C": 0, "burst": False, "flexible": True},
    PETAL_NAME:               {"cmc": 0, "B": 0, "R": 0, "C": 0, "burst": False, "oneshot": True},
}

# --- Mana dork / creature ramp definitions ---
# Hoard and Bleed runs neither. Placeholders retained for interface parity with
# the shared engine.

DORK_DEFS: dict = {}
CREATURE_RAMP: dict = {}
WIGHT_NAME = "__no_dork_placeholder__"

# --- Land definitions ---

# No MDFC lands in this deck.
MDFC_LAND_NAMES: set[str] = set()

FETCH_LANDS = {"Bloodstained Mire", "Prismatic Vista", "Fabled Passage"}

BASIC_SWAMPS = {"Swamp"}
BASIC_MOUNTAINS = {"Mountain"}

# Subtype membership, used for fetch targeting and check-land conditions.
SWAMP_TYPED_LANDS = {"Swamp", "Blood Crypt", "Smoldering Marsh", "Turbulent Crater"}
MOUNTAIN_TYPED_LANDS = {"Mountain", "Blood Crypt", "Smoldering Marsh", "Turbulent Crater"}

# Untapped B/R duals and any-color lands.
FLEXIBLE_LANDS = {
    "Blood Crypt", "Command Tower", "Luxury Suite", "Sulfurous Springs",
    "Blackcleave Cliffs", "Dragonskull Summit", "Smoldering Marsh",
    "Foreboding Ruins", "Mount Doom", "City of Brass", "Mana Confluence",
    "Exotic Orchard", "Turbulent Crater",
}

# Lands that produce B (used for land-play priority and fetch colour need).
B_PRODUCING_LANDS = FLEXIBLE_LANDS | {
    "Swamp", "Vault of Whispers", "Bojuka Bog", "Shadowblood Ridge",
    "Reflecting Pool", "Spire of Industry",
}

# Lands that produce R.
R_PRODUCING_LANDS = FLEXIBLE_LANDS | {
    "Mountain", "Great Furnace", "Mines of Moria", "Shadowblood Ridge",
    "Reflecting Pool", "Spire of Industry",
}

# Colorless-only utility lands.
C_ONLY_LANDS = {
    "High Market", "Fountainport", "Treasure Vault", "The Mycosynth Gardens",
    "Volatile Fault",
}

# Lands that always enter tapped in this model.
ALWAYS_TAPPED_LANDS = {"Bojuka Bog", "Mines of Moria"}


def build_decklist(deck_data: dict) -> list[str]:
    """Build the 99-card decklist for Hoard and Bleed."""
    cards = []
    for card in deck_data["decklist"]:
        qty = card.get("quantity", 1)
        cards.extend([card["name"]] * qty)
    return cards


def classify_cards(decklist: list[str], metadata: dict) -> dict:
    """Classify each card as land, rock, or spell."""
    classified = {"lands": [], "rocks": [], "spells": []}
    for name in decklist:
        if name in ROCK_DEFS or name in DORK_DEFS:
            classified["rocks"].append(name)
        else:
            meta = metadata.get(name, {})
            type_line = meta.get("type_line", "")
            front = type_line.split("//")[0]
            if "Land" in front:
                classified["lands"].append(name)
            else:
                classified["spells"].append(name)
    return classified


# --- Board state helpers ---

def count_basics(battlefield_lands: list[str]) -> int:
    return sum(1 for l in battlefield_lands
               if l in BASIC_SWAMPS or l in BASIC_MOUNTAINS)


def land_enters_tapped(name: str, battlefield_lands: list[str], hand: list[str]) -> bool:
    """Determine if a land enters tapped given board + hand state."""
    other_count = len(battlefield_lands)

    if name in ALWAYS_TAPPED_LANDS:
        # Bojuka Bog is unconditional. Mines of Moria is untapped only with a
        # legendary creature out, which this model does not track.
        return True

    if name == "Dragonskull Summit":
        # Check land — untapped if you control a Swamp or a Mountain.
        return not any(l in SWAMP_TYPED_LANDS or l in MOUNTAIN_TYPED_LANDS
                       for l in battlefield_lands)

    if name == "Smoldering Marsh":
        # Battle land — untapped with two or more basic lands.
        return count_basics(battlefield_lands) < 2

    if name == "Blackcleave Cliffs":
        # Fast land — untapped with two or fewer other lands.
        return other_count > 2

    if name == "Foreboding Ruins":
        # Reveal land — untapped if a Swamp or Mountain card is in hand.
        return not any(l in SWAMP_TYPED_LANDS or l in MOUNTAIN_TYPED_LANDS
                       for l in hand)

    if name == "Luxury Suite":
        # Untapped with two or more opponents; a four-player pod always qualifies.
        return False

    if name == "Turbulent Crater":
        # Untapped once opponents control 8+ lands. Opponent boards are not
        # tracked; under the vanilla 4-player model that holds from your turn 4
        # in every seat (turn 3 only in seats 3-4), so gate on this being at
        # least the 4th land drop (conservative; same model as Turbulent
        # Springs in gathering-shadow, DEC-688).
        return other_count < 3

    # Blood Crypt (pay 2 life), Command Tower, Sulfurous Springs, Mount Doom,
    # City of Brass, Mana Confluence, Exotic Orchard, Reflecting Pool,
    # Spire of Industry, Shadowblood Ridge, The Mycosynth Gardens, Great Furnace,
    # Vault of Whispers, High Market, Fountainport, Treasure Vault, basics:
    # all enter untapped.
    return False


class ManaPool:
    """Tracks available B, R, C mana and flexible (B-or-R) sources."""

    def __init__(self):
        self.B = 0
        self.R = 0
        self.C = 0
        self.flexible = 0

    @property
    def total(self):
        return self.B + self.R + self.C + self.flexible

    def can_cast(self, pips: dict) -> bool:
        need_B = pips["B"]
        need_R = pips["R"]
        need_generic = pips["generic"]

        avail_B = self.B
        avail_R = self.R
        avail_C = self.C
        avail_flex = self.flexible

        used_B = min(avail_B, need_B)
        remaining_B = need_B - used_B
        avail_B -= used_B

        used_R = min(avail_R, need_R)
        remaining_R = need_R - used_R
        avail_R -= used_R

        remaining_colored = remaining_B + remaining_R
        if avail_flex < remaining_colored:
            return False
        avail_flex -= remaining_colored

        leftover = avail_B + avail_R + avail_C + avail_flex
        return leftover >= need_generic

    def after_spending(self, pips: dict) -> "ManaPool":
        """Return a new ManaPool after spending pips. Assumes can_cast is True."""
        pool = ManaPool()
        pool.B = self.B
        pool.R = self.R
        pool.C = self.C
        pool.flexible = self.flexible

        need_B = pips["B"]
        need_R = pips["R"]
        need_generic = pips["generic"]

        from_B = min(pool.B, need_B)
        pool.B -= from_B
        need_B -= from_B

        from_R = min(pool.R, need_R)
        pool.R -= from_R
        need_R -= from_R

        pool.flexible -= (need_B + need_R)

        remaining = need_generic
        from_C = min(pool.C, remaining)
        pool.C -= from_C
        remaining -= from_C

        from_B2 = min(pool.B, remaining)
        pool.B -= from_B2
        remaining -= from_B2

        from_R2 = min(pool.R, remaining)
        pool.R -= from_R2
        remaining -= from_R2

        from_flex = min(pool.flexible, remaining)
        pool.flexible -= from_flex

        return pool


def compute_land_mana(name: str, battlefield_lands: list[str],
                      has_rock: bool) -> tuple[int, int, int, int]:
    """Return (B, R, C, flexible) mana a single untapped land produces.

    ``has_rock`` gates Spire of Industry's any-color mode, which needs an
    artifact. Shadowblood Ridge and Reflecting Pool are handled by the caller,
    which knows the rest of the board.
    """
    if name in C_ONLY_LANDS:
        return (0, 0, 1, 0)

    if name in FETCH_LANDS:
        # Cracked on the turn it is played; if somehow still around, no mana.
        return (0, 0, 0, 0)

    if name == "Spire of Industry":
        return (0, 0, 0, 1) if has_rock else (0, 0, 1, 0)

    if name in FLEXIBLE_LANDS:
        return (0, 0, 0, 1)

    if name in {"Swamp", "Vault of Whispers", "Bojuka Bog"}:
        return (1, 0, 0, 0)

    if name in {"Mountain", "Great Furnace", "Mines of Moria"}:
        return (0, 1, 0, 0)

    # Shadowblood Ridge and Reflecting Pool are resolved in compute_mana_pool.
    if name in {"Shadowblood Ridge", "Reflecting Pool"}:
        return (0, 0, 0, 0)

    # Fallback: colorless.
    return (0, 0, 1, 0)


MAX_MULLIGANS = 2


def should_mulligan(hand: list[str], land_set: set[str]) -> bool:
    """Mulligan if 0-1 mana sources (lands + rocks)."""
    sources = sum(1 for c in hand if c in land_set or c in ROCK_DEFS or c in DORK_DEFS)
    return sources <= 1


def choose_bottom_cards(hand: list[str], count: int, metadata: dict,
                        land_set: set[str]) -> list[str]:
    """Choose cards to bottom (London mulligan): highest-CMC non-land, non-ramp."""
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
        self.petal_turn: int | None = None  # turn Lotus Petal was played
        self.current_turn = 0
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
        """Higher = play first. Fetches first, then untapped, then fixing."""
        if name in FETCH_LANDS:
            return 20

        tapped = land_enters_tapped(name, self.battlefield_lands, self.hand)
        base = 0 if tapped else 10

        if name in B_PRODUCING_LANDS and name in R_PRODUCING_LANDS:
            base += 5
        elif name in B_PRODUCING_LANDS or name in R_PRODUCING_LANDS:
            base += 2

        return base

    def _resolve_fetch(self, fetch_name: str):
        """Resolve a fetch land: search for a land matching the colour we need."""
        b_sources = sum(1 for l in self.battlefield_lands if l in B_PRODUCING_LANDS)
        r_sources = sum(1 for l in self.battlefield_lands if l in R_PRODUCING_LANDS)

        if fetch_name == "Bloodstained Mire":
            # Any Swamp or Mountain card, so the duals are legal targets.
            valid = SWAMP_TYPED_LANDS | MOUNTAIN_TYPED_LANDS
        else:
            # Prismatic Vista and Fabled Passage fetch a basic only.
            valid = BASIC_SWAMPS | BASIC_MOUNTAINS

        fetchable = [(i, card) for i, card in enumerate(self.library) if card in valid]
        if not fetchable:
            return

        # Blood Crypt fetches both colours; take it early when Mire allows.
        crypt = [(i, c) for i, c in fetchable if c == "Blood Crypt"]
        if crypt and len(self.battlefield_lands) <= 2:
            idx, card = crypt[0]
            self.library.pop(idx)
            self._put_fetched(card, fetch_name)
            return

        want_basics = BASIC_SWAMPS if b_sources <= r_sources else BASIC_MOUNTAINS
        preferred = [(i, c) for i, c in fetchable if c in want_basics]
        idx, card = preferred[0] if preferred else fetchable[0]
        self.library.pop(idx)
        self._put_fetched(card, fetch_name)

    def _put_fetched(self, card: str, fetch_name: str):
        self.battlefield_lands.append(card)
        # Fabled Passage puts the land in tapped, then untaps it with 4+ lands.
        if fetch_name == "Fabled Passage" and len(self.battlefield_lands) < 4:
            self.tapped_lands.add(len(self.battlefield_lands) - 1)

    def compute_mana_pool(self) -> ManaPool:
        """Total available mana from untapped lands + rocks."""
        pool = ManaPool()
        has_rock = bool(self.battlefield_rocks)

        untapped = [l for i, l in enumerate(self.battlefield_lands)
                    if i not in self.tapped_lands]

        ridge_count = 0
        pool_count = 0
        for land in untapped:
            if land == "Shadowblood Ridge":
                ridge_count += 1
                continue
            if land == "Reflecting Pool":
                pool_count += 1
                continue
            b, r, c, f = compute_land_mana(land, self.battlefield_lands, has_rock)
            pool.B += b
            pool.R += r
            pool.C += c
            pool.flexible += f

        for rock in self.battlefield_rocks:
            rdef = ROCK_DEFS[rock]
            if rdef.get("oneshot"):
                continue  # Lotus Petal is credited below, on its own turn only.
            pool.C += rdef.get("C", 0)
            if rdef.get("flexible"):
                pool.flexible += 1
            else:
                pool.B += rdef.get("B", 0)
                pool.R += rdef.get("R", 0)

        # Reflecting Pool copies a type another land could produce. It is a
        # flexible B/R source as long as one other colored source is untapped.
        if pool_count:
            if pool.B or pool.R or pool.flexible:
                pool.flexible += pool_count
            else:
                pool.C += pool_count

        # Shadowblood Ridge converts {1} into {B}{R}: net one extra colored
        # mana, and only when something else can pay the {1}.
        if ridge_count and pool.total > 0:
            for _ in range(ridge_count):
                if pool.total <= 0:
                    break
                pool.flexible += 1

        # Lotus Petal: one flexible mana, on the turn it was played only.
        if self.petal_turn is not None and self.petal_turn == self.current_turn:
            pool.flexible += 1

        return pool

    def play_turn(self, turn_number: int):
        """Simulate one turn."""
        self.current_turn = turn_number
        if turn_number > 1:
            self.draw(1)

        self.tapped_lands.clear()
        for name in list(self.burst_rocks_active.keys()):
            self.burst_rocks_active[name] = False
        self.dorks_active = list(self.battlefield_dorks)

        hand_lands = [(self._land_play_priority(c), c)
                      for c in self.hand if self._is_land(c)]
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

        pool = self.compute_mana_pool()
        self._try_cast_ramp(pool, turn_number)

        self.mana_per_turn.append(self.compute_mana_pool())

    def _try_cast_ramp(self, pool: ManaPool, turn_number: int):
        """Cast mana rocks from hand in priority order."""
        priority_order = [
            PETAL_NAME,           # free, so always first
            "Sol Ring",
            "Arcane Signet",
            "Talisman of Indulgence",
            "Fellwar Stone",
        ]

        for name in priority_order:
            if name not in self.hand:
                continue

            rdef = ROCK_DEFS[name]
            pips = parse_mana_cost(self.metadata.get(name, {}).get("mana_cost", ""))
            if not pool.can_cast(pips):
                continue

            pool = pool.after_spending(pips)
            self.hand.remove(name)
            self.battlefield_rocks.append(name)

            if rdef.get("oneshot"):
                self.petal_turn = turn_number
                pool.flexible += 1
            else:
                pool.C += rdef.get("C", 0)
                if rdef.get("flexible"):
                    pool.flexible += 1
                else:
                    pool.B += rdef.get("B", 0)
                    pool.R += rdef.get("R", 0)


def commander_mulligan(decklist: list[str], metadata: dict,
                       land_set: set[str]) -> GameState:
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
    """Return castable non-ramp spells from hand."""
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

def run_simulation(decklist: list[str], metadata: dict,
                   num_games: int = NUM_GAMES) -> dict:
    """Run num_games simulations and collect stats."""
    land_set = set()
    for name in set(decklist):
        meta = metadata.get(name, {})
        front = meta.get("type_line", "").split("//")[0]
        if "Land" in front:
            land_set.add(name)

    mana_by_turn = {t: [] for t in range(1, NUM_TURNS + 1)}
    b_by_turn = {t: [] for t in range(1, NUM_TURNS + 1)}
    r_by_turn = {t: [] for t in range(1, NUM_TURNS + 1)}
    hand_land_counts = Counter()
    mulligan_attempts = Counter()

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
            total = pool.total
            b_avail = pool.B + pool.flexible
            r_avail = pool.R + pool.flexible

            mana_by_turn[t].append(total)
            b_by_turn[t].append(b_avail)
            r_by_turn[t].append(r_avail)

            if b_avail == 0:
                zero_b_by_turn[t] += 1
            if r_avail == 0:
                zero_r_by_turn[t] += 1

            # Smaug, Wicked Worm — {3}{B}{R}, CMC 5.
            cmd_pips = {"generic": 3, "B": 1, "R": 1}
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
        "r_by_turn": r_by_turn,
        "hand_land_counts": hand_land_counts,
        "mulligan_attempts": mulligan_attempts,
        "zero_b_by_turn": zero_b_by_turn,
        "zero_r_by_turn": zero_r_by_turn,
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

    result = exporter.export_hoard_and_bleed(metadata)
    if not exporter.validate_output(result, "hoard-and-bleed"):
        raise ValueError("export_hoard_and_bleed produced invalid simulation output")
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Monte Carlo mana base simulation for Smaug, Wicked Worm")
    parser.add_argument("--json", action="store_true",
                        help="Write simulation.json instead of console output")
    args = parser.parse_args()

    with open(DECK_FILE) as f:
        deck_data = json.load(f)
    with open(METADATA_FILE) as f:
        metadata = json.load(f)

    print("Building Hoard and Bleed decklist...")
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
    print("\nMana medians: " + ", ".join(
        f"T{t}={statistics.median(stats['mana_by_turn'][t]):.0f}"
        for t in range(1, NUM_TURNS + 1)
    ))
    print(f"Commander by T5: {stats['commander_by_turn'][5]/total*100:.1f}%")
    print(f"Curve-out rate: {stats['curve_out_games']/total*100:.1f}%")


if __name__ == "__main__":
    main()
