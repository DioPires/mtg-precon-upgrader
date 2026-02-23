#!/usr/bin/env python3
"""Export mana simulation results as JSON for all commander decks.

Imports each simulation module under a namespace (they share function names),
runs the simulations, and writes structured JSON to
data/commanders/{id}/simulation.json.
"""

import json
import os
import statistics
import sys
import traceback
from collections import Counter
from datetime import date
from pathlib import Path

# Add scripts dir to path for imports
SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

import mana_simulation as sim_titan
import mana_simulation_rakdos as sim_rakdos
import mana_simulation_grixis as sim_grixis

PROJECT_ROOT = SCRIPTS_DIR.parent
METADATA_FILE = PROJECT_ROOT / "data" / "card-metadata.json"

NUM_GAMES = 100_000
NUM_TURNS = 10


# --- Helpers ---


def pct(count: int, total: int) -> float:
    """Percentage rounded to 1 decimal."""
    return round(count / total * 100, 1) if total > 0 else 0.0


def r1(val: float) -> float:
    """Round to 1 decimal."""
    return round(val, 1)


def compute_avg_cmc(decklist: list[str], metadata: dict) -> float:
    """Average CMC of non-land cards."""
    cmcs = []
    for name in decklist:
        meta = metadata.get(name, {})
        if "Land" not in meta.get("type_line", ""):
            cmc = meta.get("cmc", 0)
            if isinstance(cmc, (int, float)):
                cmcs.append(cmc)
    return statistics.mean(cmcs) if cmcs else 0.0


def mana_stats(data: list) -> dict:
    """Compute median/p25/p75/mean from a list of values."""
    if not data:
        return {"median": 0.0, "p25": 0.0, "p75": 0.0, "mean": 0.0}
    q = statistics.quantiles(data, n=4)
    return {
        "median": r1(statistics.median(data)),
        "p25": r1(q[0]),
        "p75": r1(q[2]),
        "mean": r1(statistics.mean(data)),
    }


def cumulative_pct(values: list, threshold: int, total: int) -> float:
    """Percentage of values <= threshold."""
    count = sum(1 for v in values if v <= threshold)
    return pct(count, total)


def median_or_null(values: list):
    """Median of a list, or None if empty."""
    if not values:
        return None
    return r1(statistics.median(values))


def derive_assessment(result: dict) -> dict:
    """Derive qualitative assessments from simulation data."""
    # Mana adequacy: compare median mana at T4-5 to avg CMC
    avg_cmc = result["deckComposition"]["avgCmc"]
    t4_median = result["manaByTurn"]["4"]["median"]
    t5_median = result["manaByTurn"]["5"]["median"]

    if t5_median >= avg_cmc + 2:
        mana_adequacy = "strong"
    elif t4_median >= avg_cmc:
        mana_adequacy = "adequate"
    else:
        mana_adequacy = "light"

    # Mulligan verdict
    paid_pct = result["mulliganStats"]["paidMulligan"]
    if paid_pct < 3:
        mulligan_verdict = "excellent"
    elif paid_pct < 5:
        mulligan_verdict = "acceptable"
    else:
        mulligan_verdict = "concerning"

    # Commander timing
    cmd = result["commanderTiming"]
    cmd_cmc = cmd["cmc"]
    median_turn = cmd["medianTurn"]
    if median_turn is None:
        cmd_timing = "unreliable"
    elif median_turn <= cmd_cmc - 1:
        cmd_timing = "ahead of curve"
    elif median_turn <= cmd_cmc:
        cmd_timing = "on curve"
    else:
        cmd_timing = "behind curve"

    return {
        "manaAdequacy": mana_adequacy,
        "mulliganVerdict": mulligan_verdict,
        "commanderTiming": cmd_timing,
    }


def run_parallel(run_chunk_fn, merge_fn, decklist, metadata, num_games):
    """Run simulation with multiprocessing, return merged stats."""
    import multiprocessing
    n_workers = os.cpu_count() or 4
    chunk_size = num_games // n_workers
    remainder = num_games % n_workers
    chunks = [chunk_size + (1 if i < remainder else 0) for i in range(n_workers)]

    with multiprocessing.Pool(n_workers) as pool:
        results = pool.map(run_chunk_fn, [(decklist, metadata, n) for n in chunks])
    return merge_fn(results)


def validate_output(result: dict, deck_id: str) -> bool:
    """Validate required top-level keys and manaByTurn entries."""
    required_keys = [
        "metadata", "deckComposition", "manaByTurn", "mulliganStats",
        "openingHand", "commanderTiming", "colorBalance", "curveEfficiency",
        "specialMetrics", "assessment",
    ]
    for key in required_keys:
        if key not in result:
            print(f"  VALIDATION FAIL [{deck_id}]: missing key '{key}'")
            return False

    for t in range(1, NUM_TURNS + 1):
        if str(t) not in result["manaByTurn"]:
            print(f"  VALIDATION FAIL [{deck_id}]: manaByTurn missing turn {t}")
            return False

    return True


# --- Deck-specific exporters ---


def export_titan(metadata: dict) -> dict:
    """Export Titan Convergence (colorless Eldrazi) simulation."""
    deck_file = PROJECT_ROOT / "data" / "commanders" / "titan-convergence" / "deck.json"
    with open(deck_file) as f:
        deck_data = json.load(f)

    decklist = sim_titan.build_decklist(deck_data)
    classified = sim_titan.classify_cards(decklist, metadata)
    avg_cmc = compute_avg_cmc(decklist, metadata)

    print(f"  Running {NUM_GAMES:,} games for Titan Convergence...")
    stats = run_parallel(sim_titan._run_chunk, sim_titan.merge_stats,
                         decklist, metadata, NUM_GAMES)
    total = NUM_GAMES

    # manaByTurn
    mana_by_turn = {}
    for t in range(1, NUM_TURNS + 1):
        mana_by_turn[str(t)] = mana_stats(stats["mana_by_turn"][t])

    # mulliganStats
    mull = stats["mulligan_attempts"]
    mulligan_stats = {
        "keptFirst": pct(mull.get(0, 0), total),
        "freeMulligan": pct(mull.get(1, 0), total),
        "paidMulligan": pct(mull.get(2, 0), total),
    }

    # openingHand
    land_dist = {}
    for n in range(8):
        count = stats["hand_land_counts"].get(n, 0)
        if count > 0:
            land_dist[str(n)] = pct(count, total)
    opening_hand = {"landDistribution": land_dist}

    # commanderTiming (Zhulodok = 6 CMC, cumulative % by turn)
    cmd_by_turn = {}
    for t in range(1, NUM_TURNS + 1):
        cmd_by_turn[str(t)] = cumulative_pct(stats["zhulodok_turns"], t, total)

    commander_timing = {
        "name": "Zhulodok, Void Gorger",
        "cmc": 6,
        "byTurn": cmd_by_turn,
        "medianTurn": median_or_null(stats["zhulodok_turns"]),
    }

    # curveEfficiency
    castable_by_turn = {}
    for t in range(1, NUM_TURNS + 1):
        castable_by_turn[str(t)] = pct(stats["castable_spell_by_turn"][t], total)

    curve_efficiency = {
        "castableByTurn": castable_by_turn,
        "curveOutRate": pct(stats["curve_out_games"], total),
    }

    # specialMetrics: cascadeReadiness
    cascade_by_turn = {}
    for t in range(1, NUM_TURNS + 1):
        cascade_by_turn[str(t)] = cumulative_pct(stats["cascade_ready_turns"], t, total)

    special_metrics = {
        "cascadeReadiness": {
            "byTurn": cascade_by_turn,
            "medianTurn": median_or_null(stats["cascade_ready_turns"]),
        },
        "etbTapped": None,
    }

    result = {
        "metadata": {
            "numGames": NUM_GAMES,
            "numTurns": NUM_TURNS,
            "generatedAt": str(date.today()),
        },
        "deckComposition": {
            "totalCards": len(decklist),
            "lands": len(classified["lands"]),
            "rocks": len(classified["rocks"]),
            "spells": len(classified["spells"]) + len(classified.get("amplifiers", [])),
            "avgCmc": r1(avg_cmc),
        },
        "manaByTurn": mana_by_turn,
        "mulliganStats": mulligan_stats,
        "openingHand": opening_hand,
        "commanderTiming": commander_timing,
        "colorBalance": None,
        "curveEfficiency": curve_efficiency,
        "specialMetrics": special_metrics,
        "assessment": {},
    }
    result["assessment"] = derive_assessment(result)
    return result


def _export_colored(sim_module, deck_id: str, deck_name: str,
                    commander_name: str, commander_cmc: int,
                    colors: list[str], metadata: dict) -> dict:
    """Export a colored (Rakdos/Grixis) simulation."""
    deck_file = PROJECT_ROOT / "data" / "commanders" / deck_id / "deck.json"
    with open(deck_file) as f:
        deck_data = json.load(f)

    decklist = sim_module.build_decklist(deck_data)
    classified = sim_module.classify_cards(decklist, metadata)
    avg_cmc = compute_avg_cmc(decklist, metadata)

    print(f"  Running {NUM_GAMES:,} games for {deck_name}...")
    stats = run_parallel(sim_module._run_chunk, sim_module.merge_stats,
                         decklist, metadata, NUM_GAMES)
    total = NUM_GAMES

    # manaByTurn
    mana_by_turn = {}
    for t in range(1, NUM_TURNS + 1):
        mana_by_turn[str(t)] = mana_stats(stats["mana_by_turn"][t])

    # mulliganStats
    mull = stats["mulligan_attempts"]
    mulligan_stats = {
        "keptFirst": pct(mull.get(0, 0), total),
        "freeMulligan": pct(mull.get(1, 0), total),
        "paidMulligan": pct(mull.get(2, 0), total),
    }

    # openingHand
    land_dist = {}
    for n in range(8):
        count = stats["hand_land_counts"].get(n, 0)
        if count > 0:
            land_dist[str(n)] = pct(count, total)
    opening_hand = {"landDistribution": land_dist}

    # commanderTiming (cumulative from commander_by_turn)
    cmd_by_turn = {}
    for t in range(1, NUM_TURNS + 1):
        cmd_by_turn[str(t)] = pct(stats["commander_by_turn"][t], total)

    commander_timing = {
        "name": commander_name,
        "cmc": commander_cmc,
        "byTurn": cmd_by_turn,
        "medianTurn": median_or_null(stats["commander_castable_turn"]),
    }

    # colorBalance
    color_keys = {c: c.lower() for c in colors}
    color_by_turn = {}
    for t in range(1, NUM_TURNS + 1):
        turn_data = {}
        for color in colors:
            key = f"{color_keys[color]}_by_turn"
            data = stats[key][t]
            turn_data[color] = {
                "median": r1(statistics.median(data)),
                "mean": r1(statistics.mean(data)),
            }
        color_by_turn[str(t)] = turn_data

    color_screw_by_turn = {}
    for t in range(1, NUM_TURNS + 1):
        turn_screw = {}
        for color in colors:
            key = f"zero_{color_keys[color]}_by_turn"
            turn_screw[color] = pct(stats[key][t], total)
        color_screw_by_turn[str(t)] = turn_screw

    color_balance = {
        "colors": colors,
        "byTurn": color_by_turn,
        "colorScrewByTurn": color_screw_by_turn,
    }

    # curveEfficiency
    castable_by_turn = {}
    for t in range(1, NUM_TURNS + 1):
        castable_by_turn[str(t)] = pct(stats["castable_spell_by_turn"][t], total)

    curve_efficiency = {
        "castableByTurn": castable_by_turn,
        "curveOutRate": pct(stats["curve_out_games"], total),
    }

    # specialMetrics: etbTapped
    etb_tapped = {}
    for t in stats["tapped_land_turns"]:
        etb_tapped[str(t)] = pct(stats["tapped_land_turns"][t], total)

    special_metrics = {
        "cascadeReadiness": None,
        "etbTapped": etb_tapped,
    }

    result = {
        "metadata": {
            "numGames": NUM_GAMES,
            "numTurns": NUM_TURNS,
            "generatedAt": str(date.today()),
        },
        "deckComposition": {
            "totalCards": len(decklist),
            "lands": len(classified["lands"]),
            "rocks": len(classified["rocks"]),
            "spells": len(classified["spells"]),
            "avgCmc": r1(avg_cmc),
        },
        "manaByTurn": mana_by_turn,
        "mulliganStats": mulligan_stats,
        "openingHand": opening_hand,
        "commanderTiming": commander_timing,
        "colorBalance": color_balance,
        "curveEfficiency": curve_efficiency,
        "specialMetrics": special_metrics,
        "assessment": {},
    }
    result["assessment"] = derive_assessment(result)
    return result


def export_rakdos(metadata: dict) -> dict:
    """Export Eternal Agony (Rakdos) simulation."""
    return _export_colored(
        sim_module=sim_rakdos,
        deck_id="eternal-agony",
        deck_name="Eternal Agony",
        commander_name="The Lord of Pain",
        commander_cmc=5,
        colors=["B", "R"],
        metadata=metadata,
    )


def export_grixis(metadata: dict) -> dict:
    """Export Dark Dominion (Grixis) simulation."""
    return _export_colored(
        sim_module=sim_grixis,
        deck_id="sauron-the-dark-lord",
        deck_name="Dark Dominion",
        commander_name="Sauron, the Dark Lord",
        commander_cmc=6,
        colors=["U", "B", "R"],
        metadata=metadata,
    )


# --- Main ---


DECKS = [
    ("titan-convergence", "Titan Convergence", export_titan),
    ("eternal-agony", "Eternal Agony", export_rakdos),
    ("sauron-the-dark-lord", "Dark Dominion", export_grixis),
]


def main():
    with open(METADATA_FILE) as f:
        metadata = json.load(f)

    print(f"Loaded card metadata ({len(metadata)} cards)")
    print(f"Exporting simulation results for {len(DECKS)} decks...\n")

    for deck_id, deck_name, export_fn in DECKS:
        try:
            print(f"[{deck_name}]")
            result = export_fn(metadata)

            if not validate_output(result, deck_id):
                print(f"  SKIPPED: validation failed\n")
                continue

            out_path = PROJECT_ROOT / "data" / "commanders" / deck_id / "simulation.json"
            with open(out_path, "w") as f:
                json.dump(result, f, indent=2)
            print(f"  Written: {out_path}")
            print(f"  Size: {out_path.stat().st_size / 1024:.1f} KB\n")

        except Exception:
            print(f"  ERROR processing {deck_name}:")
            traceback.print_exc()
            print()

    print("Done.")


if __name__ == "__main__":
    main()
