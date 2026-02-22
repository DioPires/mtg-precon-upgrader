#!/usr/bin/env python3
"""Monte Carlo mana base simulation for Eldrazi Unbound Titan Convergence tier.

Simulates 10,000 games measuring mana production turns 1-5 with the upgraded
Bracket 4 decklist (baseDeck - cuts + adds, commander in command zone).
"""

import json
import random
import statistics
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DECK_FILE = PROJECT_ROOT / "data" / "precons" / "eldrazi-unbound" / "deck.json"
METADATA_FILE = PROJECT_ROOT / "data" / "card-metadata.json"

NUM_GAMES = 10_000
NUM_TURNS = 5

# --- Land mana production rules ---

# Lands that always produce 0 mana
ZERO_MANA_LANDS = {"Eye of Ugin"}

# Lands that produce 2+ under certain conditions (handled in code)
# Eldrazi Temple: 2 (most spells are Eldrazi)
# Ugin's Labyrinth: 2 (imprint trivial)
# Scorched Ruins: 4 (ETB sacs 2 untapped lands)
# Shrine of the Forsaken Gods: 1 until 7 lands, then 2
# Urza's Mine/Power Plant/Tower: Tron-dependent
# Planar Nexus: 1, enables Tron
# Urza's Workshop: metalcraft-dependent, scales with Urza land count

TRON_PIECES = {"Urza's Mine", "Urza's Power Plant", "Urza's Tower"}
URZA_LANDS = {"Urza's Mine", "Urza's Power Plant", "Urza's Tower", "Urza's Cave", "Urza's Workshop", "Planar Nexus"}

# --- Rock definitions ---
# (name, cmc, mana_per_turn, is_burst)
# is_burst: produces mana on cast turn only (Mana Vault, Basalt Monolith)

ROCK_DEFS = {
    "Sol Ring": {"cmc": 1, "mana": 2, "burst": False},
    "Mind Stone": {"cmc": 2, "mana": 1, "burst": False},
    "Thought Vessel": {"cmc": 2, "mana": 1, "burst": False},
    "Worn Powerstone": {"cmc": 3, "mana": 2, "burst": False},
    "Thran Dynamo": {"cmc": 4, "mana": 3, "burst": False},
    "Hedron Archive": {"cmc": 4, "mana": 2, "burst": False},
    "Darksteel Monolith": {"cmc": 4, "mana": 2, "burst": False},
    "Mana Vault": {"cmc": 1, "mana": 3, "burst": True},
    "Basalt Monolith": {"cmc": 3, "mana": 3, "burst": True},
}

AMPLIFIER_DEFS = {
    "Forsaken Monument": {"cmc": 5},
    "Extraplanar Lens": {"cmc": 3},
}


def build_decklist(deck_data: dict) -> list[str]:
    """Build the 99-card decklist for Titan Convergence tier.

    baseDeck (with quantities) - commander - tier cuts + tier adds = 99 cards.
    """
    tier = deck_data["upgrades"]["full"]
    commander = tier.get("commander", deck_data.get("commander"))

    # Build base deck with quantities
    base = []
    for card in deck_data["baseDeck"]:
        qty = card.get("quantity", 1)
        base.extend([card["name"]] * qty)

    # Remove commander (in command zone)
    cards = [c for c in base]
    # Commander might be in baseDeck or not
    if commander in cards:
        cards.remove(commander)

    # Apply tier-specific cuts if they exist, otherwise top-level cuts
    cuts_list = tier.get("cuts", deck_data.get("cuts", []))
    for cut in cuts_list:
        name = cut["name"]
        qty = cut.get("quantity", 1)
        for _ in range(qty):
            if name in cards:
                cards.remove(name)

    # Add tier adds
    for add in tier.get("adds", []):
        cards.append(add["name"])

    return cards


def classify_cards(decklist: list[str], metadata: dict) -> dict:
    """Classify each card as land, rock, amplifier, or spell."""
    classified = {"lands": [], "rocks": [], "amplifiers": [], "spells": []}

    for name in decklist:
        if name in ROCK_DEFS:
            classified["rocks"].append(name)
        elif name in AMPLIFIER_DEFS:
            classified["amplifiers"].append(name)
        else:
            meta = metadata.get(name, {})
            type_line = meta.get("type_line", "")
            if "Land" in type_line:
                classified["lands"].append(name)
            else:
                classified["spells"].append(name)

    return classified


def land_base_mana(name: str, battlefield_lands: list[str], has_forsaken: bool, has_lens: bool) -> int:
    """Calculate mana a land produces given current board state."""
    if name in ZERO_MANA_LANDS:
        return 0

    base = 1  # default

    if name == "Eldrazi Temple":
        base = 2
    elif name == "Ugin's Labyrinth":
        base = 2
    elif name == "Scorched Ruins":
        base = 4
    elif name == "Shrine of the Forsaken Gods":
        total_lands = len(battlefield_lands)
        base = 2 if total_lands >= 7 else 1
    elif name in TRON_PIECES:
        # Check if Tron is assembled (all 3 types present, Planar Nexus counts as all)
        has_nexus = "Planar Nexus" in battlefield_lands
        types_present = set()
        for land in battlefield_lands:
            if land in TRON_PIECES:
                types_present.add(land)
        tron_complete = (len(types_present) >= 3) or (has_nexus and len(types_present) >= 1)

        if tron_complete:
            if name == "Urza's Tower":
                base = 3
            else:
                base = 2
        else:
            base = 1
    elif name == "Planar Nexus":
        base = 1
    elif name == "Urza's Workshop":
        # Metalcraft trivial (3+ artifacts). Produces mana = number of Urza lands in play.
        urza_count = sum(1 for l in battlefield_lands if l in URZA_LANDS)
        base = max(1, urza_count)  # at least 1
    elif name == "Wastes":
        if has_lens:
            base = 2
        else:
            base = 1

    # Forsaken Monument: +1 to each colorless mana produced
    if has_forsaken and base > 0:
        base += 1

    # Extraplanar Lens only affects Wastes (handled above with has_lens)
    # Forsaken Monument already applied above

    return base


def rock_mana(name: str, has_forsaken: bool) -> int:
    """Calculate mana a rock produces per turn."""
    rock = ROCK_DEFS[name]
    base = rock["mana"]
    if has_forsaken:
        base += 1
    return base


class GameState:
    def __init__(self, decklist: list[str]):
        self.library = list(decklist)
        random.shuffle(self.library)
        self.hand: list[str] = []
        self.battlefield_lands: list[str] = []
        self.battlefield_rocks: list[str] = []
        self.has_forsaken = False
        self.has_lens = False
        self.burst_rocks_active: dict[str, bool] = {}  # name -> was cast this turn
        self.mana_per_turn: list[int] = []

    def draw(self, n: int = 1):
        for _ in range(n):
            if self.library:
                self.hand.append(self.library.pop())

    def opening_hand_stats(self) -> dict:
        lands = sum(1 for c in self.hand if self._is_land(c))
        rocks = sum(1 for c in self.hand if c in ROCK_DEFS)
        return {"lands": lands, "rocks": rocks, "sources": lands + rocks}

    def _is_land(self, name: str) -> bool:
        return name in _land_set

    def _land_priority(self, name: str) -> int:
        """Higher = play first."""
        # Scorched Ruins needs 2+ lands to sac
        if name == "Scorched Ruins":
            return 5 if len(self.battlefield_lands) >= 2 else -1

        # Tron-completing piece
        if name in TRON_PIECES:
            types_on_board = set()
            for l in self.battlefield_lands:
                if l in TRON_PIECES:
                    types_on_board.add(l)
                if l == "Planar Nexus":
                    types_on_board.update(TRON_PIECES)
            if name not in types_on_board and len(types_on_board) >= 2:
                return 10  # completing Tron

        # 2-mana lands
        if name in ("Eldrazi Temple", "Ugin's Labyrinth"):
            return 8

        # Planar Nexus (enables Tron with 1 piece)
        if name == "Planar Nexus":
            has_any_tron = any(l in TRON_PIECES for l in self.battlefield_lands)
            return 7 if has_any_tron else 4

        # Urza's Workshop scales with Urza lands
        if name == "Urza's Workshop":
            return 6

        # 0-mana utility lands are lowest
        if name in ZERO_MANA_LANDS:
            return 0

        return 3  # default 1-mana land

    def play_turn(self, turn_number: int):
        """Simulate one turn: untap, draw, play land, cast rocks/amplifiers, record mana."""
        # Draw (skip on turn 1's draw since we have opening hand)
        if turn_number > 1:
            self.draw(1)

        # Mark burst rocks as no longer active
        for name in list(self.burst_rocks_active.keys()):
            self.burst_rocks_active[name] = False

        # Play best land from hand
        hand_lands = [(self._land_priority(c), c) for c in self.hand if self._is_land(c)]
        hand_lands.sort(reverse=True)

        land_played = False
        for priority, land_name in hand_lands:
            if priority < 0:
                continue  # can't play (e.g. Scorched Ruins with <2 lands)
            self.hand.remove(land_name)
            if land_name == "Scorched Ruins":
                # Sacrifice 2 untapped lands
                sac_count = min(2, len(self.battlefield_lands))
                for _ in range(sac_count):
                    if self.battlefield_lands:
                        # Sac lowest-value land
                        worst = min(self.battlefield_lands,
                                    key=lambda l: land_base_mana(l, self.battlefield_lands, self.has_forsaken, self.has_lens))
                        self.battlefield_lands.remove(worst)
            self.battlefield_lands.append(land_name)
            land_played = True
            break

        # Calculate available mana before casting
        available = self._total_mana()

        # Try to cast rocks/amplifiers, highest value first
        castable = self._get_castable_from_hand(available)
        while castable:
            name, cmc = castable[0]
            available -= cmc
            self.hand.remove(name)
            if name in AMPLIFIER_DEFS:
                if name == "Forsaken Monument":
                    self.has_forsaken = True
                elif name == "Extraplanar Lens":
                    self.has_lens = True
            elif name in ROCK_DEFS:
                self.battlefield_rocks.append(name)
                rock = ROCK_DEFS[name]
                if rock["burst"]:
                    self.burst_rocks_active[name] = True
                    # Burst rock produces mana immediately
                    available += rock_mana(name, self.has_forsaken)
                else:
                    # Non-burst rock can be tapped immediately
                    available += rock_mana(name, self.has_forsaken)
            castable = self._get_castable_from_hand(available)

        # Record total mana available this turn (recalculate with all permanents)
        self.mana_per_turn.append(self._total_mana())

    def _total_mana(self) -> int:
        """Calculate total mana from all sources."""
        total = 0
        for land in self.battlefield_lands:
            total += land_base_mana(land, self.battlefield_lands, self.has_forsaken, self.has_lens)

        for rock_name in self.battlefield_rocks:
            rock = ROCK_DEFS[rock_name]
            if rock["burst"]:
                # Only produces mana on cast turn
                if self.burst_rocks_active.get(rock_name, False):
                    total += rock_mana(rock_name, self.has_forsaken)
                # Basalt Monolith with Forsaken Monument: net +1/turn
                elif rock_name == "Basalt Monolith" and self.has_forsaken:
                    total += 1
            else:
                total += rock_mana(rock_name, self.has_forsaken)

        return total

    def _get_castable_from_hand(self, available_mana: int) -> list[tuple[str, int]]:
        """Return sorted list of castable rocks/amplifiers from hand."""
        castable = []
        for card in self.hand:
            if card in ROCK_DEFS:
                cmc = ROCK_DEFS[card]["cmc"]
                if cmc <= available_mana:
                    rock = ROCK_DEFS[card]
                    # Priority: output-per-cost ratio
                    ratio = rock["mana"] / max(cmc, 1)
                    castable.append((card, cmc, ratio))
            elif card in AMPLIFIER_DEFS:
                cmc = AMPLIFIER_DEFS[card]["cmc"]
                if cmc <= available_mana:
                    # Amplifiers get high priority (they boost future turns)
                    castable.append((card, cmc, 10.0))

        # Sort by ratio descending
        castable.sort(key=lambda x: x[2], reverse=True)
        return [(name, cmc) for name, cmc, _ in castable]


# Global set for fast land lookups (populated in main)
_land_set: set[str] = set()


def run_simulation(decklist: list[str], metadata: dict) -> dict:
    """Run NUM_GAMES simulations and collect stats."""
    global _land_set

    # Build land set from metadata
    _land_set = set()
    for name in set(decklist):
        meta = metadata.get(name, {})
        if "Land" in meta.get("type_line", ""):
            _land_set.add(name)

    # Stats collectors
    mana_by_turn = {t: [] for t in range(1, NUM_TURNS + 1)}
    hand_land_counts = Counter()
    hand_source_counts = Counter()
    mulligan_count = 0
    zhulodok_turns = []
    cascade_ready_turns = []
    t2_zhulodok = 0
    t3_zhulodok = 0

    for _ in range(NUM_GAMES):
        state = GameState(decklist)
        state.draw(7)

        # Opening hand stats
        hand_stats = state.opening_hand_stats()
        hand_land_counts[hand_stats["lands"]] += 1
        hand_source_counts[hand_stats["sources"]] += 1
        if hand_stats["lands"] <= 1:
            mulligan_count += 1

        # Gemstone Caverns: if in opening hand, 50% chance of luck counter
        if "Gemstone Caverns" in state.hand:
            if random.random() < 0.5:  # not going first
                state.hand.remove("Gemstone Caverns")
                state.battlefield_lands.append("Gemstone Caverns")
                # Exile a card from hand
                if state.hand:
                    # Exile worst card (highest CMC non-land)
                    non_lands = [c for c in state.hand if not state._is_land(c)]
                    if non_lands:
                        state.hand.remove(non_lands[-1])
                    elif state.hand:
                        state.hand.remove(state.hand[-1])

        # Simulate turns
        zhulodok_turn = None
        cascade_turn = None
        for t in range(1, NUM_TURNS + 1):
            state.play_turn(t)
            mana = state.mana_per_turn[-1]
            mana_by_turn[t].append(mana)

            if zhulodok_turn is None and mana >= 5:
                zhulodok_turn = t
            if cascade_turn is None and mana >= 7:
                cascade_turn = t

        if zhulodok_turn is not None:
            zhulodok_turns.append(zhulodok_turn)
            if zhulodok_turn <= 2:
                t2_zhulodok += 1
            if zhulodok_turn <= 3:
                t3_zhulodok += 1
        if cascade_turn is not None:
            cascade_ready_turns.append(cascade_turn)

    return {
        "mana_by_turn": mana_by_turn,
        "hand_land_counts": hand_land_counts,
        "hand_source_counts": hand_source_counts,
        "mulligan_count": mulligan_count,
        "zhulodok_turns": zhulodok_turns,
        "cascade_ready_turns": cascade_ready_turns,
        "t2_zhulodok": t2_zhulodok,
        "t3_zhulodok": t3_zhulodok,
    }


def compute_avg_cmc(decklist: list[str], metadata: dict) -> float:
    """Average CMC of non-land cards."""
    cmcs = []
    for name in decklist:
        meta = metadata.get(name, {})
        if "Land" not in meta.get("type_line", ""):
            cmc = meta.get("cmc", 0)
            if isinstance(cmc, (int, float)):
                cmcs.append(cmc)
    return statistics.mean(cmcs) if cmcs else 0


def print_results(stats: dict, decklist: list[str], metadata: dict, classified: dict):
    """Print simulation results."""
    print("=" * 60)
    print("ELDRAZI UNBOUND — TITAN CONVERGENCE MANA SIMULATION")
    print(f"({NUM_GAMES:,} games, {NUM_TURNS} turns each)")
    print("=" * 60)

    # Deck composition
    print(f"\n--- Deck Composition ---")
    print(f"Total cards (excl. commander): {len(decklist)}")
    print(f"Lands: {len(classified['lands'])}")
    print(f"Mana rocks: {len(classified['rocks'])}")
    print(f"Amplifiers: {len(classified['amplifiers'])}")
    print(f"Spells/creatures: {len(classified['spells'])}")
    print(f"Avg CMC (non-land): {compute_avg_cmc(decklist, metadata):.2f}")

    # Land breakdown
    print(f"\n--- Land Breakdown ---")
    land_counts = Counter(classified["lands"])
    for name, count in sorted(land_counts.items()):
        suffix = f" x{count}" if count > 1 else ""
        print(f"  {name}{suffix}")

    # Mana per turn
    print(f"\n--- Mana Per Turn ---")
    print(f"{'Turn':<6} {'Median':>7} {'P25':>7} {'P75':>7} {'Mean':>7}")
    print("-" * 38)
    for t in range(1, NUM_TURNS + 1):
        data = stats["mana_by_turn"][t]
        med = statistics.median(data)
        p25 = statistics.quantiles(data, n=4)[0]
        p75 = statistics.quantiles(data, n=4)[2]
        mean = statistics.mean(data)
        print(f"  T{t:<4} {med:>7.0f} {p25:>7.0f} {p75:>7.0f} {mean:>7.1f}")

    # Cascade readiness
    print(f"\n--- Cascade Readiness (7+ mana) ---")
    total = NUM_GAMES
    for t in [3, 4, 5]:
        count = sum(1 for ct in stats["cascade_ready_turns"] if ct <= t)
        print(f"  By turn {t}: {count/total*100:.1f}%")
    if stats["cascade_ready_turns"]:
        print(f"  Median turn to 7+ mana: {statistics.median(stats['cascade_ready_turns']):.1f}")

    # Commander timing
    print(f"\n--- Commander Timing (Zhulodok = 5 MV) ---")
    if stats["zhulodok_turns"]:
        print(f"  Median turn to 5+ mana: {statistics.median(stats['zhulodok_turns']):.1f}")
    print(f"  T2 Zhulodok: {stats['t2_zhulodok']/total*100:.1f}%")
    print(f"  T3 Zhulodok: {stats['t3_zhulodok']/total*100:.1f}%")

    # Hand quality
    print(f"\n--- Opening Hand Quality ---")
    print(f"  Mulligan rate (0-1 lands): {stats['mulligan_count']/total*100:.1f}%")
    print(f"\n  Land count distribution (opening 7):")
    for lands in range(8):
        count = stats["hand_land_counts"].get(lands, 0)
        bar = "#" * int(count / total * 50)
        print(f"    {lands} lands: {count/total*100:>5.1f}% {bar}")

    print(f"\n  Mana source count (lands + rocks in opening 7):")
    for sources in range(8):
        count = stats["hand_source_counts"].get(sources, 0)
        if count > 0:
            print(f"    {sources} sources: {count/total*100:>5.1f}%")

    # Mana base assessment
    print(f"\n--- Mana Base Assessment ---")
    med_t1 = statistics.median(stats["mana_by_turn"][1])
    med_t3 = statistics.median(stats["mana_by_turn"][3])
    med_t5 = statistics.median(stats["mana_by_turn"][5])
    mull_rate = stats["mulligan_count"] / total * 100

    print(f"  Median T1: {med_t1:.0f}, T3: {med_t3:.0f}, T5: {med_t5:.0f}")
    if mull_rate < 15:
        print(f"  Mulligan rate {mull_rate:.1f}% — acceptable")
    else:
        print(f"  Mulligan rate {mull_rate:.1f}% — consider adding lands")

    t3_zhulodok_pct = stats["t3_zhulodok"] / total * 100
    if t3_zhulodok_pct > 50:
        print(f"  T3 Zhulodok {t3_zhulodok_pct:.0f}% — strong acceleration")
    else:
        print(f"  T3 Zhulodok {t3_zhulodok_pct:.0f}% — may want more fast mana")


def print_sire_swap_analysis(decklist: list[str], metadata: dict):
    """Print the Sire of Seven Deaths swap analysis."""
    print("\n" + "=" * 60)
    print("SIRE OF SEVEN DEATHS SWAP ANALYSIS")
    print("=" * 60)

    target = "Ulamog, the Infinite Gyre"
    replacement = "Sire of Seven Deaths"

    print(f"\n  CUT:  {target} (MV 11, $25-35)")
    print(f"  ADD:  {replacement} (MV 7, $0 — owned)")

    print(f"\n  Why cut {target}:")
    print(f"    - Most redundant Eldrazi: Ceaseless Hunger does same job better")
    print(f"      (exile 2 > destroy 1, exile 20 on attack)")
    print(f"    - Annihilator 4 still available on Kozilek, Butcher of Truth")
    print(f"    - Graveyard shuffle safety net is overkill with 9 other big threats")
    print(f"    - 'Destroy permanent' on cast doesn't hit indestructible")

    print(f"\n  What {replacement} brings:")
    print(f"    - 6 combat keywords (first strike, vigilance, menace, trample, reach, lifelink)")
    print(f"    - Only lifegain source in a colorless deck")
    print(f"    - Ward 7 life — extremely resilient to removal")
    print(f"    - MV 7 = double cascade (same as Infinite Gyre) but 4 cheaper to hardcast")
    print(f"    - Reach: blocks flyers (colorless decks struggle here)")

    print(f"\n  What you lose:")
    print(f"    - Annihilator 4 (still on Butcher of Truth)")
    print(f"    - Indestructible (still on Ceaseless Hunger, Blightsteel)")
    print(f"    - Higher MV cascade hits (11 vs 7)")
    print(f"    - Graveyard shuffle (Butcher of Truth also has this)")

    print(f"\n  Savings: $25-35")

    # Cascade impact comparison
    print(f"\n  Cascade Impact:")
    print(f"    MV 11 cascades hit MV ≤10 → virtually any non-commander card")
    print(f"    MV 7 cascades hit MV ≤6 → misses titans but hits rocks, utility")
    print(f"    Net: Infinite Gyre's higher cascade ceiling is its only real advantage")


def main():
    with open(DECK_FILE) as f:
        deck_data = json.load(f)

    with open(METADATA_FILE) as f:
        metadata = json.load(f)

    print("Building Titan Convergence decklist...")
    decklist = build_decklist(deck_data)
    print(f"Decklist: {len(decklist)} cards")

    classified = classify_cards(decklist, metadata)

    print(f"\nRunning {NUM_GAMES:,} game simulations...\n")
    stats = run_simulation(decklist, metadata)

    print_results(stats, decklist, metadata, classified)
    print_sire_swap_analysis(decklist, metadata)

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
