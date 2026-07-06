#!/usr/bin/env python3
"""Monte Carlo mana base simulation for Armory Protocol (Tony Stark).

Simulates 100,000 games measuring mana production, color balance, and curve
efficiency turns 1-10 for the Bracket 3+ Izzet Equipment-Voltron decklist.

Commander: Tony Stark // The Invincible Iron Man (transform DFC).
- Front face: {1}{U} 1/3 with "{1}, {T}: look at the top four, reveal an
  artifact card to hand" (card selection — not modeled here).
- Transform activation: {4}{U}{R}, sorcery speed. Training Grounds cuts it to
  {2}{U}{R} (activated abilities of creatures cost {2} less; the {1} dig is
  already at the one-mana floor).

Commander modeling (DEC-405): the transform is the commander-online event.
The sim runs a two-stage state machine with real mana spending — cast the
front face at {1}{U}, then pay the transform activation on the same or a
later turn ({2}{U}{R} once Training Grounds is on the battlefield). The
commander_by_turn metric records the turn the TRANSFORM is paid, so
commanderTiming reads "suit online", not "1/3 dork in play". This matches
the Esika/Prismatic Bridge precedent (commander_cmc reported as 6).
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
DECK_FILE = PROJECT_ROOT / "data" / "commanders" / "armory-protocol" / "deck.json"
METADATA_FILE = PROJECT_ROOT / "data" / "card-metadata.json"
JSON_OUTPUT = PROJECT_ROOT / "data" / "commanders" / "armory-protocol" / "simulation.json"

NUM_GAMES = 100_000
NUM_TURNS = 10


# --- Mana cost parser ---

def parse_mana_cost(mana_cost: str) -> dict:
    """Parse mana_cost string into pip breakdown.

    "{4}{U}{R}" -> {generic: 4, U: 1, R: 1, total: 6}
    Split/DFC cards (//): parse first half only.
    """
    if "//" in mana_cost:
        mana_cost = mana_cost.split("//")[0].strip()

    result = {"generic": 0, "U": 0, "R": 0, "total": 0, "X": False}
    symbols = re.findall(r"\{([^}]+)\}", mana_cost)
    for sym in symbols:
        if sym == "X":
            result["X"] = True
        elif sym.isdigit():
            result["generic"] += int(sym)
        elif sym == "U":
            result["U"] += 1
        elif sym == "R":
            result["R"] += 1
        # Ignore other symbols (hybrid, phyrexian, etc.)
    result["total"] = result["generic"] + result["U"] + result["R"]
    return result


# --- Rock definitions ---
# Cast cost is modeled as pure generic (every rock here has a generic-only
# printed cost). Production: C = colorless, flexible = one mana of U or R.
# - Izzet Signet nets +1 with perfect fixing ({1}, {T}: add {U}{R}) — modeled
#   as one flexible source, the conservative read.
# - Fellwar Stone: 4-player table, both colors virtually always available.
# - Arc Reactor: {5} improvise, enters tapped, taps for {C}{C}{C}. Modeled at
#   an effective {4} (improvise floor of one artifact tapped) with production
#   delayed one turn for the tapped ETB.

ROCK_DEFS = {
    "Sol Ring":              {"cast_generic": 1, "C": 2, "flexible": 0, "etb_tapped": False},
    "Arcane Signet":         {"cast_generic": 2, "C": 0, "flexible": 1, "etb_tapped": False},
    "Izzet Signet":          {"cast_generic": 2, "C": 0, "flexible": 1, "etb_tapped": False},
    "Talisman of Creativity": {"cast_generic": 2, "C": 0, "flexible": 1, "etb_tapped": False},
    "Fellwar Stone":         {"cast_generic": 2, "C": 0, "flexible": 1, "etb_tapped": False},
    "Mind Stone":            {"cast_generic": 2, "C": 1, "flexible": 0, "etb_tapped": False},
    "Thought Vessel":        {"cast_generic": 2, "C": 1, "flexible": 0, "etb_tapped": False},
    "Arc Reactor":           {"cast_generic": 4, "C": 3, "flexible": 0, "etb_tapped": True},
}

# --- Cost reducer definitions ---
# Reduce artifact spell costs but produce no mana; documented, not simulated
# (their absence keeps the curve numbers floors). Sword of the Animist is
# attack-gated land ramp — treated as a plain spell.

COST_REDUCERS = {
    "Foundry Inspector":      {"cmc": 3, "reduction": 1, "applies_to": "artifact"},
    "Etherium Sculptor":      {"cmc": 2, "reduction": 1, "applies_to": "artifact"},
    "Enthusiastic Mechanaut": {"cmc": 2, "reduction": 1, "applies_to": "artifact"},
}

# Training Grounds IS simulated: it gates the transform cost ({4}{U}{R} ->
# {2}{U}{R}) and is cast on sight for {U}.
TRAINING_GROUNDS = "Training Grounds"
TRAINING_GROUNDS_PIPS = {"generic": 0, "U": 1, "R": 0}

# Commander staged costs.
COMMANDER_FRONT_PIPS = {"generic": 1, "U": 1, "R": 0}          # Tony Stark {1}{U}
TRANSFORM_PIPS = {"generic": 4, "U": 1, "R": 1}                # {4}{U}{R}
TRANSFORM_PIPS_REDUCED = {"generic": 2, "U": 1, "R": 1}        # with Training Grounds


# --- Land definitions ---

# Flexible U/R duals (produce one mana of either color):
FLEX_LANDS = {
    "Command Tower", "Steam Vents", "Shivan Reef", "Cascade Bluffs",
    "Stormcarved Coast", "Sulfur Falls", "Temple of Epiphany",
    "Exotic Orchard", "Riverpyre Verge", "Turbulent Springs",
}
# Notes: Steam Vents modeled untapped (pay 2 life). Cascade Bluffs is a filter
# land ({U/R} in, {U}{U}/{U}{R}/{R}{R} out) — modeled as one flexible source,
# the conservative net. Exotic Orchard assumes a 4-player table where some
# opponent produces U or R.

U_LANDS = {"Island", "Seat of the Synod"}
R_LANDS = {"Mountain", "Great Furnace"}
C_ONLY_LANDS = {"Fomori Vault", "Academy Ruins"}

# Spire of Industry: any color with an artifact on the battlefield, else {C}.
# Handled dynamically in compute_land_mana (artifact lands / rocks check).
SPIRE = "Spire of Industry"

# Island-typed lands (for Sulfur Falls checks):
ISLAND_TYPED = {"Island", "Steam Vents", "Turbulent Springs"}
MOUNTAIN_TYPED = {"Mountain", "Steam Vents", "Turbulent Springs"}
ARTIFACT_LANDS = {"Seat of the Synod", "Great Furnace"}

# Fetches: crack immediately for a basic, balancing U/R sources.
# Fabled Passage's basic enters untapped once you control 4+ lands.
# Riverpyre Verge: {R} always, {U} gated on controlling an Island/Mountain
# (85-99% from turn 2) — modeled flexible, consistent with Exotic Orchard's
# 4-player read. Turbulent Springs: untapped once opponents have 8+ lands
# (~their turn 3) — proxied as "our 2nd land onward", same shape as
# Stormcarved Coast.
FETCHLANDS = {"Fabled Passage"}


def land_enters_tapped(name: str, battlefield_lands: list[str]) -> bool:
    """ETB-tapped rules for the deck's lands."""
    if name == "Temple of Epiphany":
        return True

    if name == "Stormcarved Coast":
        return len(battlefield_lands) < 2

    if name == "Turbulent Springs":
        return len(battlefield_lands) < 2

    if name == "Sulfur Falls":
        has_island_or_mountain = any(
            l in ISLAND_TYPED or l in MOUNTAIN_TYPED for l in battlefield_lands
        )
        return not has_island_or_mountain

    # Steam Vents: pay 2 life, untapped. Everything else untapped.
    return False


class ManaPool:
    """Tracks available U, R, C mana and flexible (U-or-R) sources."""

    def __init__(self):
        self.U = 0
        self.R = 0
        self.C = 0
        self.flexible = 0

    @property
    def total(self):
        return self.U + self.R + self.C + self.flexible

    def can_cast(self, pips: dict) -> bool:
        need_U = pips["U"]
        need_R = pips["R"]
        need_generic = pips["generic"]

        avail_U = self.U
        avail_R = self.R
        avail_flex = self.flexible

        used_U = min(avail_U, need_U)
        remaining_U = need_U - used_U
        avail_U -= used_U

        used_R = min(avail_R, need_R)
        remaining_R = need_R - used_R
        avail_R -= used_R

        remaining_colored = remaining_U + remaining_R
        if avail_flex < remaining_colored:
            return False
        avail_flex -= remaining_colored

        leftover = avail_U + avail_R + self.C + avail_flex
        return leftover >= need_generic

    def after_spending(self, pips: dict) -> "ManaPool":
        pool = ManaPool()
        pool.U = self.U
        pool.R = self.R
        pool.C = self.C
        pool.flexible = self.flexible

        need_U = pips["U"]
        need_R = pips["R"]
        need_generic = pips["generic"]

        from_U = min(pool.U, need_U)
        pool.U -= from_U
        need_U -= from_U

        from_R = min(pool.R, need_R)
        pool.R -= from_R
        need_R -= from_R

        pool.flexible -= (need_U + need_R)

        remaining = need_generic
        from_C = min(pool.C, remaining)
        pool.C -= from_C
        remaining -= from_C

        from_U2 = min(pool.U, remaining)
        pool.U -= from_U2
        remaining -= from_U2

        from_R2 = min(pool.R, remaining)
        pool.R -= from_R2
        remaining -= from_R2

        from_flex = min(pool.flexible, remaining)
        pool.flexible -= from_flex

        return pool


def compute_land_mana(name: str, battlefield_lands: list[str],
                      battlefield_rocks: list[str]) -> tuple[int, int, int, int]:
    """Return (U, R, C, flexible) mana a single untapped land produces."""
    if name in U_LANDS:
        return (1, 0, 0, 0)
    if name in R_LANDS:
        return (0, 1, 0, 0)
    if name in C_ONLY_LANDS:
        return (0, 0, 1, 0)
    if name in FLEX_LANDS:
        return (0, 0, 0, 1)
    if name == SPIRE:
        has_artifact = bool(battlefield_rocks) or any(
            l in ARTIFACT_LANDS for l in battlefield_lands
        )
        return (0, 0, 0, 1) if has_artifact else (0, 0, 1, 0)
    # Fetches resolve as basics already; defensive fallback.
    return (0, 0, 1, 0)


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
    """Mulligan if 0-1 mana sources (lands + rocks)."""
    sources = sum(1 for c in hand if c in land_set or c in ROCK_DEFS)
    return sources <= 1


def choose_bottom_cards(hand: list[str], count: int, metadata: dict,
                        land_set: set[str]) -> list[str]:
    """London mulligan: bottom highest CMC non-land, non-ramp cards."""
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
        self.rocks_entering: list[str] = []  # tapped-ETB rocks; produce next turn
        self.training_grounds = False
        self.front_cast = False
        self.transformed = False
        self.commander_online_turn: int | None = None
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
        """Higher = play first. Fetches crack now; untapped duals preferred."""
        if name in FETCHLANDS:
            return 20

        tapped = land_enters_tapped(name, self.battlefield_lands)
        base = 0 if tapped else 10

        if name in FLEX_LANDS or name == SPIRE:
            base += 5
        elif name in U_LANDS or name in R_LANDS:
            base += 3
        # Pure C utility lands fall to the bottom.
        return base

    def _resolve_fetch(self, fetch_name: str):
        """Crack a fetch for the basic of the color we are behind on."""
        u_sources = sum(1 for l in self.battlefield_lands
                        if l in U_LANDS or l in FLEX_LANDS)
        r_sources = sum(1 for l in self.battlefield_lands
                        if l in R_LANDS or l in FLEX_LANDS)
        preferred = ["Island", "Mountain"] if u_sources <= r_sources else ["Mountain", "Island"]

        for basic in preferred:
            for i, card in enumerate(self.library):
                if card == basic:
                    self.library.pop(i)
                    self.battlefield_lands.append(card)
                    # EW/TE basics enter tapped; Fabled Passage untaps its
                    # basic once you control 4+ lands.
                    tapped = not (fetch_name == "Fabled Passage"
                                  and len(self.battlefield_lands) >= 4)
                    if tapped:
                        self.tapped_lands.add(len(self.battlefield_lands) - 1)
                    return
        # No basic left — the fetch still cracks (thins to nothing).

    def compute_mana_pool(self) -> ManaPool:
        pool = ManaPool()

        for i, land in enumerate(self.battlefield_lands):
            if i in self.tapped_lands:
                continue
            u, r, c, f = compute_land_mana(land, self.battlefield_lands,
                                           self.battlefield_rocks)
            pool.U += u
            pool.R += r
            pool.C += c
            pool.flexible += f

        for rock in self.battlefield_rocks:
            rdef = ROCK_DEFS[rock]
            pool.C += rdef["C"]
            pool.flexible += rdef["flexible"]

        return pool

    def play_turn(self, turn_number: int):
        if turn_number > 1:
            self.draw(1)

        self.tapped_lands.clear()
        # Tapped-ETB rocks come online.
        self.battlefield_rocks.extend(self.rocks_entering)
        self.rocks_entering = []

        hand_lands = [(self._land_play_priority(c), c) for c in self.hand if self._is_land(c)]
        hand_lands.sort(reverse=True)

        if hand_lands:
            _, land_name = hand_lands[0]
            self.hand.remove(land_name)

            if land_name in FETCHLANDS:
                self._resolve_fetch(land_name)
            else:
                tapped = land_enters_tapped(land_name, self.battlefield_lands)
                self.battlefield_lands.append(land_name)
                if tapped:
                    self.tapped_lands.add(len(self.battlefield_lands) - 1)

        pool = self.compute_mana_pool()
        pool = self._try_cast_ramp(pool)

        # Training Grounds on sight — it halves the transform's generic cost.
        if not self.training_grounds and TRAINING_GROUNDS in self.hand:
            if pool.can_cast(TRAINING_GROUNDS_PIPS):
                pool = pool.after_spending(TRAINING_GROUNDS_PIPS)
                self.hand.remove(TRAINING_GROUNDS)
                self.training_grounds = True

        # Commander two-stage state machine (real spending).
        if not self.front_cast and pool.can_cast(COMMANDER_FRONT_PIPS):
            pool = pool.after_spending(COMMANDER_FRONT_PIPS)
            self.front_cast = True

        if self.front_cast and not self.transformed:
            transform_pips = TRANSFORM_PIPS_REDUCED if self.training_grounds else TRANSFORM_PIPS
            if pool.can_cast(transform_pips):
                pool = pool.after_spending(transform_pips)
                self.transformed = True
                self.commander_online_turn = turn_number

        # Record the full development pool (donor convention: mana available,
        # not mana remaining after commander investment).
        self.mana_per_turn.append(self.compute_mana_pool())

    def _try_cast_ramp(self, pool: ManaPool) -> ManaPool:
        rock_priority = [
            "Sol Ring",
            "Arcane Signet",
            "Izzet Signet",
            "Talisman of Creativity",
            "Fellwar Stone",
            "Mind Stone",
            "Thought Vessel",
            "Arc Reactor",
        ]
        for rock_name in rock_priority:
            if rock_name not in self.hand:
                continue
            rdef = ROCK_DEFS[rock_name]
            pips = {"generic": rdef["cast_generic"], "U": 0, "R": 0}
            if pool.can_cast(pips):
                pool = pool.after_spending(pips)
                self.hand.remove(rock_name)
                if rdef["etb_tapped"]:
                    self.rocks_entering.append(rock_name)
                else:
                    self.battlefield_rocks.append(rock_name)
                    pool.C += rdef["C"]
                    pool.flexible += rdef["flexible"]
        return pool


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
    """Castable non-ramp spells in hand under current pool."""
    castable = []
    for card in state.hand:
        if card in ROCK_DEFS or card in state.land_set or card == TRAINING_GROUNDS:
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
    land_set = set()
    for name in set(decklist):
        meta = metadata.get(name, {})
        if "Land" in meta.get("type_line", ""):
            land_set.add(name)

    mana_by_turn = {t: [] for t in range(1, NUM_TURNS + 1)}
    u_by_turn = {t: [] for t in range(1, NUM_TURNS + 1)}
    r_by_turn = {t: [] for t in range(1, NUM_TURNS + 1)}
    hand_land_counts = Counter()
    mulligan_attempts = Counter()

    zero_u_by_turn = {t: 0 for t in range(1, NUM_TURNS + 1)}
    zero_r_by_turn = {t: 0 for t in range(1, NUM_TURNS + 1)}

    commander_castable_turn = []
    commander_by_turn = {t: 0 for t in range(1, NUM_TURNS + 1)}

    front_cast_by_turn = {t: 0 for t in range(1, NUM_TURNS + 1)}

    castable_spell_by_turn = {t: 0 for t in range(1, NUM_TURNS + 1)}
    curve_out_games = 0

    tapped_land_turns = {1: 0, 2: 0}

    for _ in range(num_games):
        state = commander_mulligan(decklist, metadata, land_set)
        mulligan_attempts[state.mulligan_attempt] += 1
        hand_land_counts[state.count_lands_in_hand()] += 1

        cast_every_turn = True
        front_turn = None

        for t in range(1, NUM_TURNS + 1):
            lands_before = len(state.battlefield_lands)
            state.play_turn(t)
            lands_after = len(state.battlefield_lands)

            pool = state.mana_per_turn[-1]
            u_avail = pool.U + pool.flexible
            r_avail = pool.R + pool.flexible

            mana_by_turn[t].append(pool.total)
            u_by_turn[t].append(u_avail)
            r_by_turn[t].append(r_avail)

            if u_avail == 0:
                zero_u_by_turn[t] += 1
            if r_avail == 0:
                zero_r_by_turn[t] += 1

            if front_turn is None and state.front_cast:
                front_turn = t

            castable = can_cast_from_hand(state, pool)
            if castable:
                castable_spell_by_turn[t] += 1
            elif t <= 4:
                cast_every_turn = False

            if t <= 2 and lands_after > lands_before:
                new_idx = lands_after - 1
                if new_idx in state.tapped_lands:
                    tapped_land_turns[t] += 1

        # Commander online = transform paid (DEC-405 modeling decision).
        if state.commander_online_turn is not None:
            commander_castable_turn.append(state.commander_online_turn)
            for future_t in range(state.commander_online_turn, NUM_TURNS + 1):
                commander_by_turn[future_t] += 1

        if front_turn is not None:
            for future_t in range(front_turn, NUM_TURNS + 1):
                front_cast_by_turn[future_t] += 1

        if cast_every_turn:
            curve_out_games += 1

    return {
        "mana_by_turn": mana_by_turn,
        "u_by_turn": u_by_turn,
        "r_by_turn": r_by_turn,
        "hand_land_counts": hand_land_counts,
        "mulligan_attempts": mulligan_attempts,
        "zero_u_by_turn": zero_u_by_turn,
        "zero_r_by_turn": zero_r_by_turn,
        "commander_castable_turn": commander_castable_turn,
        "commander_by_turn": commander_by_turn,
        "front_cast_by_turn": front_cast_by_turn,
        "castable_spell_by_turn": castable_spell_by_turn,
        "curve_out_games": curve_out_games,
        "tapped_land_turns": tapped_land_turns,
    }


# --- Parallel execution ---

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

    result = exporter.export_armory_protocol(metadata)
    if not exporter.validate_output(result, "armory-protocol"):
        raise ValueError("export_armory_protocol produced invalid simulation output")
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Monte Carlo mana base simulation for Armory Protocol (Tony Stark)")
    parser.add_argument("--json", action="store_true",
                        help="Write simulation.json instead of console output")
    args = parser.parse_args()

    with open(DECK_FILE) as f:
        deck_data = json.load(f)
    with open(METADATA_FILE) as f:
        metadata = json.load(f)

    print("Building Armory Protocol decklist...")
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
    print(f"\nFront face cast ({{1}}{{U}}):")
    for t in (1, 2, 3, 4):
        print(f"  By T{t}: {stats['front_cast_by_turn'][t]/total*100:.1f}%")
    print(f"\nSuit online (transform paid, {{4}}{{U}}{{R}} / {{2}}{{U}}{{R}} w/ Training Grounds):")
    for t in (4, 5, 6, 7, 8):
        print(f"  By T{t}: {stats['commander_by_turn'][t]/total*100:.1f}%")
    if stats["commander_castable_turn"]:
        print(f"  Median online turn: {statistics.median(stats['commander_castable_turn']):.1f}")
    print(f"\nColor screw T3: 0 U = {stats['zero_u_by_turn'][3]/total*100:.1f}%, "
          f"0 R = {stats['zero_r_by_turn'][3]/total*100:.1f}%")
    print(f"Curve-out rate: {stats['curve_out_games']/total*100:.1f}%")


if __name__ == "__main__":
    main()
