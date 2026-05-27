#!/usr/bin/env python3
"""Monte Carlo mana base simulation for Mage Tower Brigade (Aziza, Mage Tower Captain).

Simulates 100,000 games measuring mana production, color balance (R/W), and curve
efficiency turns 1-10 for the Bracket 3 Boros decklist.

Commander: Aziza, Mage Tower Captain ({R}{W}, CMC 2)
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
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DECK_FILE = PROJECT_ROOT / "data" / "commanders" / "aziza-mage-tower-captain" / "deck.json"
METADATA_FILE = PROJECT_ROOT / "data" / "card-metadata.json"
JSON_OUTPUT = PROJECT_ROOT / "data" / "commanders" / "aziza-mage-tower-captain" / "simulation.json"

NUM_GAMES = 100_000
NUM_TURNS = 10


def parse_mana_cost(mana_cost: str) -> dict:
    """Parse {R}{W} pip breakdown. Handles split cards (parses first half)."""
    if "//" in mana_cost:
        mana_cost = mana_cost.split("//")[0].strip()
    result = {"generic": 0, "R": 0, "W": 0, "total": 0, "X": False}
    for sym in re.findall(r"\{([^}]+)\}", mana_cost):
        if sym == "X":
            result["X"] = True
        elif sym.isdigit():
            result["generic"] += int(sym)
        elif sym == "R":
            result["R"] += 1
        elif sym == "W":
            result["W"] += 1
        elif sym in ("R/W", "W/R"):
            # Hybrid R/W treated as flexible — handled separately
            result["generic"] += 1  # Approximate: hybrid acts as either color
    result["total"] = result["generic"] + result["R"] + result["W"]
    return result


# --- Rock definitions (Boros ramp pieces) ---
ROCK_DEFS = {
    "Sol Ring":              {"cmc": 1, "R": 0, "W": 0, "C": 2, "flexible": False},
    "Arcane Signet":         {"cmc": 2, "R": 0, "W": 0, "C": 0, "flexible": True},
    "Boros Signet":          {"cmc": 2, "R": 0, "W": 0, "C": 0, "flexible": True},
    "Talisman of Conviction":{"cmc": 2, "R": 0, "W": 0, "C": 0, "flexible": True},
    "Mind Stone":            {"cmc": 2, "R": 0, "W": 0, "C": 1, "flexible": False},
    "Fellwar Stone":         {"cmc": 2, "R": 0, "W": 0, "C": 0, "flexible": True},
}

# --- Land definitions (Aziza's manabase) ---

# Lands producing R
R_PRODUCING_LANDS = {
    "Mountain", "Sacred Foundry", "Battlefield Forge", "Inspiring Vantage",
    "Spectator Seating", "Sundown Pass", "Rugged Prairie", "Furycalm Snarl",
    "Sunbaked Canyon", "Boros Garrison", "Command Tower", "Exotic Orchard",
    "Path of Ancestry", "Slayers' Stronghold", "Sunhome, Fortress of the Legion",
    "Arena of Glory", "Den of the Bugbear", "Sokenzan, Crucible of Defiance",
    "Needleverge Pathway",
}
# Lands producing W
W_PRODUCING_LANDS = {
    "Plains", "Sacred Foundry", "Battlefield Forge", "Inspiring Vantage",
    "Spectator Seating", "Sundown Pass", "Rugged Prairie", "Furycalm Snarl",
    "Sunbaked Canyon", "Boros Garrison", "Command Tower", "Exotic Orchard",
    "Path of Ancestry", "Eiganjo, Seat of the Empire", "Cave of the Frost Dragon",
    "Hall of Heliod's Generosity", "Needleverge Pathway", "Windbrisk Heights",
}
# Colorless-only lands
C_ONLY_LANDS = {
    "Reliquary Tower",
}
BASIC_PLAINS = {"Plains"}
BASIC_MOUNTAIN = {"Mountain"}


def land_enters_tapped(name: str, battlefield_lands: list, hand: list) -> bool:
    """Tap rules for Aziza's specific lands."""
    other_count = len(battlefield_lands)

    if name == "Boros Garrison":
        return True
    if name == "Path of Ancestry":
        return True
    if name == "Slayers' Stronghold":
        return False  # ETB untapped, activated abilities cost mana
    if name == "Arena of Glory":
        return True   # ETB tapped per Scryfall
    if name == "Eiganjo, Seat of the Empire":
        return False
    if name == "Sokenzan, Crucible of Defiance":
        return False
    if name == "Hall of Heliod's Generosity":
        return False
    if name == "Sunhome, Fortress of the Legion":
        return False
    if name == "Reliquary Tower":
        return False
    if name == "Cave of the Frost Dragon":
        return True   # ETB tapped
    if name == "Den of the Bugbear":
        return True
    if name == "Spectator Seating":
        return False  # 2+ opps (always true in commander)
    if name == "Sundown Pass":
        return other_count < 2   # slowland
    if name == "Furycalm Snarl":
        # Reveal-land: untapped if you reveal a Plains or Mountain. Assume yes if you have one.
        has_basic = any(c in BASIC_PLAINS or c in BASIC_MOUNTAIN for c in hand)
        return not has_basic
    if name == "Sunbaked Canyon":
        return False  # horizon land (untapped)
    if name == "Battlefield Forge":
        return False  # painland
    if name == "Inspiring Vantage":
        # fastland: untapped if you control 2 or fewer other lands
        return other_count > 2
    if name == "Rugged Prairie":
        return False  # filterland untapped
    if name == "Sacred Foundry":
        return False  # shockland (pay 2 life, untapped)
    if name == "Needleverge Pathway":
        return False  # modal DFC
    if name == "Windbrisk Heights":
        return True   # hideaway, ETB tapped
    return False


class ManaPool:
    def __init__(self):
        self.R = 0
        self.W = 0
        self.C = 0
        self.flexible = 0  # any of R/W

    @property
    def total(self):
        return self.R + self.W + self.C + self.flexible

    def can_cast(self, pips: dict) -> bool:
        need_R = pips["R"]
        need_W = pips["W"]
        need_generic = pips["generic"]

        avail_R = self.R
        avail_W = self.W
        avail_C = self.C
        avail_flex = self.flexible

        used_R = min(avail_R, need_R)
        remaining_R = need_R - used_R
        avail_R -= used_R

        used_W = min(avail_W, need_W)
        remaining_W = need_W - used_W
        avail_W -= used_W

        remaining_colored = remaining_R + remaining_W
        if avail_flex < remaining_colored:
            return False
        avail_flex -= remaining_colored

        leftover = avail_R + avail_W + avail_C + avail_flex
        return leftover >= need_generic

    def after_spending(self, pips: dict) -> "ManaPool":
        pool = ManaPool()
        pool.R = self.R
        pool.W = self.W
        pool.C = self.C
        pool.flexible = self.flexible

        need_R = pips["R"]
        need_W = pips["W"]
        need_generic = pips["generic"]

        from_R = min(pool.R, need_R)
        pool.R -= from_R
        need_R -= from_R

        from_W = min(pool.W, need_W)
        pool.W -= from_W
        need_W -= from_W

        flex_colored = need_R + need_W
        pool.flexible -= flex_colored

        remaining = need_generic
        from_C = min(pool.C, remaining)
        pool.C -= from_C
        remaining -= from_C
        from_R2 = min(pool.R, remaining)
        pool.R -= from_R2
        remaining -= from_R2
        from_W2 = min(pool.W, remaining)
        pool.W -= from_W2
        remaining -= from_W2
        from_flex = min(pool.flexible, remaining)
        pool.flexible -= from_flex

        return pool


def compute_land_mana(name: str, battlefield_lands: list) -> tuple:
    """Return (R, W, C, flexible) mana an untapped land produces."""
    if name == "Mountain":
        return (1, 0, 0, 0)
    if name == "Plains":
        return (0, 1, 0, 0)
    if name == "Reliquary Tower":
        return (0, 0, 1, 0)
    # Dual lands that produce R or W
    if name in {
        "Sacred Foundry", "Battlefield Forge", "Inspiring Vantage",
        "Spectator Seating", "Sundown Pass", "Rugged Prairie",
        "Furycalm Snarl", "Sunbaked Canyon", "Boros Garrison",
        "Command Tower", "Exotic Orchard", "Path of Ancestry",
        "Needleverge Pathway",
    }:
        return (0, 0, 0, 1)
    # R-only utility
    if name in {"Slayers' Stronghold", "Sunhome, Fortress of the Legion",
                "Arena of Glory", "Den of the Bugbear",
                "Sokenzan, Crucible of Defiance"}:
        return (1, 0, 0, 0)
    # W-only utility
    if name in {"Eiganjo, Seat of the Empire", "Cave of the Frost Dragon",
                "Hall of Heliod's Generosity", "Windbrisk Heights"}:
        return (0, 1, 0, 0)
    return (0, 0, 1, 0)


def build_decklist(deck_data: dict) -> list:
    cards = []
    for card in deck_data["decklist"]:
        qty = card.get("quantity", 1)
        cards.extend([card["name"]] * qty)
    return cards


def is_land_card(type_line: str) -> bool:
    """Treat MDFCs/transform cards by their front face only (split on //)."""
    front = type_line.split("//")[0].strip() if "//" in type_line else type_line
    return "Land" in front


def classify_cards(decklist: list, metadata: dict) -> dict:
    classified = {"lands": [], "rocks": [], "spells": []}
    for name in decklist:
        if name in ROCK_DEFS:
            classified["rocks"].append(name)
        else:
            meta = metadata.get(name, {})
            type_line = meta.get("type_line", "")
            if is_land_card(type_line):
                classified["lands"].append(name)
            else:
                classified["spells"].append(name)
    return classified


MAX_MULLIGANS = 2


def should_mulligan(hand: list, land_set: set) -> bool:
    sources = sum(1 for c in hand if c in land_set or c in ROCK_DEFS)
    return sources <= 1


def choose_bottom_cards(hand: list, count: int, metadata: dict, land_set: set) -> list:
    ramp_cards = set(ROCK_DEFS)
    candidates = [c for c in hand if c not in land_set and c not in ramp_cards]
    candidates.sort(key=lambda c: metadata.get(c, {}).get("cmc", 0), reverse=True)
    return candidates[:count]


class GameState:
    def __init__(self, decklist, metadata, land_set):
        self.library = list(decklist)
        random.shuffle(self.library)
        self.hand = []
        self.battlefield_lands = []
        self.tapped_lands = set()
        self.battlefield_rocks = []
        self.metadata = metadata
        self.land_set = land_set
        self.mana_per_turn = []
        self.mulligan_attempt = 0

    def draw(self, n=1):
        for _ in range(n):
            if self.library:
                self.hand.append(self.library.pop())

    def count_lands_in_hand(self) -> int:
        return sum(1 for c in self.hand if c in self.land_set)

    def _is_land(self, name: str) -> bool:
        return name in self.land_set

    def _land_play_priority(self, name: str) -> float:
        tapped = land_enters_tapped(name, self.battlefield_lands, self.hand)
        if tapped:
            base = 0
        else:
            base = 10
        if name in R_PRODUCING_LANDS and name in W_PRODUCING_LANDS:
            base += 5
        elif name in R_PRODUCING_LANDS or name in W_PRODUCING_LANDS:
            base += 2
        return base

    def compute_mana_pool(self) -> ManaPool:
        pool = ManaPool()
        for i, land in enumerate(self.battlefield_lands):
            if i in self.tapped_lands:
                continue
            r, w, c, f = compute_land_mana(land, self.battlefield_lands)
            pool.R += r
            pool.W += w
            pool.C += c
            pool.flexible += f
        for rock in self.battlefield_rocks:
            rdef = ROCK_DEFS[rock]
            pool.C += rdef.get("C", 0)
            if rdef.get("flexible"):
                pool.flexible += 1
            else:
                pool.R += rdef.get("R", 0)
                pool.W += rdef.get("W", 0)
        return pool

    def play_turn(self, turn_number: int):
        if turn_number > 1:
            self.draw(1)

        self.tapped_lands.clear()

        # Play best land
        hand_lands = [(self._land_play_priority(c), c) for c in self.hand if self._is_land(c)]
        hand_lands.sort(reverse=True)
        if hand_lands:
            _, land_name = hand_lands[0]
            self.hand.remove(land_name)
            tapped = land_enters_tapped(land_name, self.battlefield_lands, self.hand)
            self.battlefield_lands.append(land_name)
            if tapped:
                self.tapped_lands.add(len(self.battlefield_lands) - 1)

        # Try cast rocks
        pool = self.compute_mana_pool()
        self._try_cast_rocks(pool)
        self.mana_per_turn.append(self.compute_mana_pool())

    def _try_cast_rocks(self, pool):
        priority = ["Sol Ring", "Arcane Signet", "Boros Signet",
                    "Talisman of Conviction", "Fellwar Stone", "Mind Stone"]
        for name in priority:
            if name not in self.hand:
                continue
            rdef = ROCK_DEFS[name]
            pips = parse_mana_cost(self.metadata.get(name, {}).get("mana_cost", ""))
            if pool.can_cast(pips):
                pool = pool.after_spending(pips)
                self.hand.remove(name)
                self.battlefield_rocks.append(name)
                pool.C += rdef.get("C", 0)
                if rdef.get("flexible"):
                    pool.flexible += 1
                else:
                    pool.R += rdef.get("R", 0)
                    pool.W += rdef.get("W", 0)


def commander_mulligan(decklist, metadata, land_set):
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


def can_cast_from_hand(state, pool):
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


def run_simulation(decklist, metadata, num_games=NUM_GAMES):
    land_set = set()
    for name in set(decklist):
        meta = metadata.get(name, {})
        if is_land_card(meta.get("type_line", "")):
            land_set.add(name)

    mana_by_turn = {t: [] for t in range(1, NUM_TURNS + 1)}
    r_by_turn = {t: [] for t in range(1, NUM_TURNS + 1)}
    w_by_turn = {t: [] for t in range(1, NUM_TURNS + 1)}
    hand_land_counts = Counter()
    mulligan_attempts = Counter()
    zero_r_by_turn = {t: 0 for t in range(1, NUM_TURNS + 1)}
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
            total = pool.total
            r_avail = pool.R + pool.flexible
            w_avail = pool.W + pool.flexible
            mana_by_turn[t].append(total)
            r_by_turn[t].append(r_avail)
            w_by_turn[t].append(w_avail)
            if r_avail == 0:
                zero_r_by_turn[t] += 1
            if w_avail == 0:
                zero_w_by_turn[t] += 1

            # Aziza commander: {R}{W}
            cmd_pips = {"generic": 0, "R": 1, "W": 1}
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
            for ft in range(cmd_cast_turn + 1, NUM_TURNS + 1):
                commander_by_turn[ft] += 1

        if cast_every_turn:
            curve_out_games += 1

    return {
        "mana_by_turn": mana_by_turn,
        "r_by_turn": r_by_turn,
        "w_by_turn": w_by_turn,
        "hand_land_counts": hand_land_counts,
        "mulligan_attempts": mulligan_attempts,
        "zero_r_by_turn": zero_r_by_turn,
        "zero_w_by_turn": zero_w_by_turn,
        "commander_castable_turn": commander_castable_turn,
        "commander_by_turn": commander_by_turn,
        "castable_spell_by_turn": castable_spell_by_turn,
        "curve_out_games": curve_out_games,
        "tapped_land_turns": tapped_land_turns,
    }


def _run_chunk(args):
    decklist, metadata, num_games = args
    return run_simulation(decklist, metadata, num_games)


def merge_stats(chunks):
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


def compute_avg_cmc(decklist, metadata):
    cmcs = []
    for name in decklist:
        meta = metadata.get(name, {})
        if "Land" not in meta.get("type_line", ""):
            cmc = meta.get("cmc", 0)
            if isinstance(cmc, (int, float)):
                cmcs.append(int(cmc))
    return statistics.mean(cmcs) if cmcs else 0


def build_simulation_json(stats, classified, decklist, metadata):
    """Build the simulation.json output with the standard schema."""
    avg_cmc = compute_avg_cmc(decklist, metadata)
    total = NUM_GAMES

    def mana_stats(data):
        return {
            "median": statistics.median(data),
            "p25": statistics.quantiles(data, n=4)[0],
            "p75": statistics.quantiles(data, n=4)[2],
            "mean": round(statistics.mean(data), 2),
        }

    out = {
        "metadata": {
            "numGames": NUM_GAMES,
            "numTurns": NUM_TURNS,
            "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        "deckComposition": {
            "totalCards": len(decklist),
            "lands": len(classified["lands"]),
            "rocks": len(classified["rocks"]),
            "spells": len(classified["spells"]),
            "avgCmc": round(avg_cmc, 2),
        },
        "manaByTurn": {str(t): mana_stats(stats["mana_by_turn"][t]) for t in range(1, NUM_TURNS + 1)},
        "colorByTurn": {
            str(t): {
                "R": mana_stats(stats["r_by_turn"][t]),
                "W": mana_stats(stats["w_by_turn"][t]),
            } for t in range(1, NUM_TURNS + 1)
        },
        "colorScrew": {
            str(t): {
                "zeroR_pct": round(stats["zero_r_by_turn"][t] / total * 100, 2),
                "zeroW_pct": round(stats["zero_w_by_turn"][t] / total * 100, 2),
            } for t in range(2, NUM_TURNS + 1)
        },
        "mulligan": {
            "keptFirstHand_pct": round(stats["mulligan_attempts"].get(0, 0) / total * 100, 2),
            "freeMulligan_pct": round(stats["mulligan_attempts"].get(1, 0) / total * 100, 2),
            "paidMulligan_pct": round(stats["mulligan_attempts"].get(2, 0) / total * 100, 2),
        },
        "openingHandLands": {
            str(lands): round(stats["hand_land_counts"].get(lands, 0) / total * 100, 2)
            for lands in range(8)
            if stats["hand_land_counts"].get(lands, 0) > 0
        },
        "commanderCastable": {
            "byTurn": {
                str(t): round(stats["commander_by_turn"][t] / total * 100, 2)
                for t in range(1, NUM_TURNS + 1)
            },
            "medianTurn": (statistics.median(stats["commander_castable_turn"])
                          if stats["commander_castable_turn"] else None),
        },
        "castableSpellByTurn": {
            str(t): round(stats["castable_spell_by_turn"][t] / total * 100, 2)
            for t in range(1, NUM_TURNS + 1)
        },
        "curveOutRate_pct": round(stats["curve_out_games"] / total * 100, 2),
        "tappedLandTurns": {
            "T1_pct": round(stats["tapped_land_turns"][1] / total * 100, 2),
            "T2_pct": round(stats["tapped_land_turns"][2] / total * 100, 2),
        },
    }
    return out


def main():
    parser = argparse.ArgumentParser(description="Monte Carlo mana sim — Aziza")
    parser.add_argument("--json", action="store_true", help="Write simulation.json")
    args = parser.parse_args()

    with open(DECK_FILE) as f:
        deck_data = json.load(f)
    with open(METADATA_FILE) as f:
        metadata = json.load(f)

    decklist = build_decklist(deck_data)
    classified = classify_cards(decklist, metadata)

    print(f"Decklist: {len(decklist)} cards (lands={len(classified['lands'])}, "
          f"rocks={len(classified['rocks'])}, spells={len(classified['spells'])})")

    n_workers = os.cpu_count() or 4
    chunk_size = NUM_GAMES // n_workers
    remainder = NUM_GAMES % n_workers
    chunks = [chunk_size + (1 if i < remainder else 0) for i in range(n_workers)]

    print(f"Running {NUM_GAMES:,} games on {n_workers} workers...")
    with multiprocessing.Pool(n_workers) as pool:
        results = pool.map(_run_chunk, [(decklist, metadata, n) for n in chunks])
    stats = merge_stats(results)

    if args.json:
        result = build_simulation_json(stats, classified, decklist, metadata)
        JSON_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        with open(JSON_OUTPUT, "w") as f:
            json.dump(result, f, indent=2)
        print(f"Written: {JSON_OUTPUT}")
        return

    # Console summary
    total = NUM_GAMES
    print("\n--- Mana Per Turn ---")
    print(f"{'Turn':<6} {'Med':>5} {'P25':>5} {'P75':>5} {'Mean':>6}")
    for t in range(1, NUM_TURNS + 1):
        d = stats["mana_by_turn"][t]
        print(f"T{t:<5} {statistics.median(d):>5.0f} {statistics.quantiles(d, n=4)[0]:>5.0f} "
              f"{statistics.quantiles(d, n=4)[2]:>5.0f} {statistics.mean(d):>6.2f}")

    mull = stats["mulligan_attempts"]
    print(f"\nMulligan: kept={mull.get(0, 0)/total*100:.1f}% free={mull.get(1, 0)/total*100:.1f}% "
          f"paid={mull.get(2, 0)/total*100:.1f}%")

    print(f"\nAziza ({{R}}{{W}}) castable by T2: "
          f"{stats['commander_by_turn'][2]/total*100:.1f}%")
    print(f"Aziza castable by T3: {stats['commander_by_turn'][3]/total*100:.1f}%")

    print(f"\nColor screw (no R available): T2={stats['zero_r_by_turn'][2]/total*100:.1f}% "
          f"T3={stats['zero_r_by_turn'][3]/total*100:.1f}%")
    print(f"Color screw (no W available): T2={stats['zero_w_by_turn'][2]/total*100:.1f}% "
          f"T3={stats['zero_w_by_turn'][3]/total*100:.1f}%")

    print(f"\nCurve-out rate (cast something T1-T4): "
          f"{stats['curve_out_games']/total*100:.1f}%")
    print(f"ETB tapped T1: {stats['tapped_land_turns'][1]/total*100:.1f}%, "
          f"T2: {stats['tapped_land_turns'][2]/total*100:.1f}%")


if __name__ == "__main__":
    main()
