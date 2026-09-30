#!/usr/bin/env python3
"""Strategy-ceiling check (DEC-309).

Detects mismatches between a deck's *shell* (manabase + interaction density)
and its *payoff* (combo or combat lethality from the goldfish simulation).

Two warnings:

- **shell-exceeds-payoff**: deck pays B4 shell tax (`shell >= 80`) but the
  wincon is sub-B4 (`payoff < 15`). The shell is over-invested relative to
  what it's protecting. ScryCheck-style downgrade signal.
- **payoff-exceeds-shell**: deck has a fast combo line (`comboLethal@T6 >=
  50%`) but a weak shell (`shell < 60`). The combo exists but won't survive a
  contested table.

Non-blocking: warnings go to stdout, exit code is 0 even if warnings fire.

Turn reads (DEC-939): payoff is `comboLethal@T7` / `lethalProxy@T8`, fast
payoff is `comboLethal@T6`. These moved one turn later from the original
DEC-309 reads (CL@T6 / LP@T7, fast CL@T5) when DEC-937 fixed the goldfish's
mana double-spend and every fast deck's lethal curve slid one turn; the
re-fitted bracket bands read True B4 at T7 and the fleet body at T8. The
percentage thresholds themselves are unchanged.

Thresholds were calibrated against the 15 production decks; see
`data/bracket-philosophy.md` "B4 Reality Check" for the table and rationale.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
COMMANDERS_DIR = PROJECT_ROOT / "data" / "commanders"

SHELL_FLOOR = 80
PAYOFF_FLOOR = 15.0
FAST_PAYOFF = 50.0
WEAK_SHELL = 60


@dataclass(frozen=True)
class DeckSnapshot:
    deck_id: str
    bracket: str | None
    wincon_style: str | None
    card_styles: frozenset[str]
    manabase_health: int
    interaction_density: int
    combo_lethal_t6: float
    combo_lethal_t7: float
    lethal_proxy_t8: float

    @property
    def shell(self) -> int:
        return min(self.manabase_health, self.interaction_density)

    @property
    def is_multi_kind(self) -> bool:
        non_combo = {"combat", "drain", "drain-x", "discrete-threats", "tokens", "mill", "alt"}
        return "combo" in self.card_styles and bool(self.card_styles & non_combo)

    @property
    def payoff(self) -> tuple[float, str]:
        ws = self.wincon_style
        if self.is_multi_kind or ws == "value-incremental" or ws is None:
            val = max(self.combo_lethal_t7, self.lethal_proxy_t8)
            src = "max(CL@T7, LP@T8)"
            return val, src
        if ws == "combo":
            return self.combo_lethal_t7, "CL@T7"
        if ws in {"combat", "drain", "drain-x", "discrete-threats"}:
            return self.lethal_proxy_t8, "LP@T8"
        # Unknown style — fall back to max for safety.
        return max(self.combo_lethal_t7, self.lethal_proxy_t8), "max(CL@T7, LP@T8) [unknown style]"


def load_snapshot(deck_dir: Path) -> DeckSnapshot | None:
    deck_path = deck_dir / "deck.json"
    metrics_path = deck_dir / "metrics.json"
    sim_path = deck_dir / "simulation.json"
    if not (deck_path.exists() and metrics_path.exists() and sim_path.exists()):
        return None
    deck = json.loads(deck_path.read_text())
    metrics = json.loads(metrics_path.read_text())
    sim = json.loads(sim_path.read_text())

    card_styles = frozenset(
        c["wincon_style"] for c in deck.get("decklist", []) if c.get("wincon_style")
    )
    by_turn = sim["goldfish"]["byTurn"]
    return DeckSnapshot(
        deck_id=deck_dir.name,
        bracket=deck.get("bracket"),
        wincon_style=deck.get("wincon_style"),
        card_styles=card_styles,
        manabase_health=int(metrics["metrics"]["manabase_health"]["score"]),
        interaction_density=int(metrics["metrics"]["interaction_density"]["score"]),
        combo_lethal_t6=float(by_turn["6"]["comboLethal"]),
        combo_lethal_t7=float(by_turn["7"]["comboLethal"]),
        lethal_proxy_t8=float(by_turn["8"]["lethalProxy"]),
    )


def evaluate(snap: DeckSnapshot) -> list[str]:
    warnings: list[str] = []
    payoff, payoff_src = snap.payoff
    if snap.shell >= SHELL_FLOOR and payoff < PAYOFF_FLOOR:
        warnings.append(
            f"shell-exceeds-payoff: shell={snap.shell} (manaH={snap.manabase_health}, "
            f"intD={snap.interaction_density}), payoff={payoff:.1f}% [{payoff_src}]. "
            "Bracket 4 shell, sub-B4 payoff. Either reduce shell investment or upgrade wincon."
        )
    if snap.combo_lethal_t6 >= FAST_PAYOFF and snap.shell < WEAK_SHELL:
        warnings.append(
            f"payoff-exceeds-shell: shell={snap.shell}, comboLethal@T6={snap.combo_lethal_t6:.1f}%. "
            "Fast wincon, weak shell — combo line exists but won't survive a contested table."
        )
    return warnings


def discover_deck_ids(only: list[str] | None) -> list[Path]:
    if only:
        return [COMMANDERS_DIR / d for d in only]
    return sorted(p for p in COMMANDERS_DIR.iterdir() if p.is_dir())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--deck",
        action="append",
        help="Limit to one or more deck IDs (repeatable). Default: all decks.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit a JSON report instead of human-readable output.",
    )
    args = parser.parse_args(argv)

    deck_dirs = discover_deck_ids(args.deck)
    report: list[dict[str, object]] = []
    total_warnings = 0
    skipped: list[str] = []

    for deck_dir in deck_dirs:
        snap = load_snapshot(deck_dir)
        if snap is None:
            skipped.append(deck_dir.name)
            continue
        warnings = evaluate(snap)
        payoff, payoff_src = snap.payoff
        report.append(
            {
                "deck_id": snap.deck_id,
                "bracket": snap.bracket,
                "wincon_style": snap.wincon_style,
                "manabase_health": snap.manabase_health,
                "interaction_density": snap.interaction_density,
                "shell": snap.shell,
                "combo_lethal_t6": snap.combo_lethal_t6,
                "combo_lethal_t7": snap.combo_lethal_t7,
                "lethal_proxy_t8": snap.lethal_proxy_t8,
                "payoff": payoff,
                "payoff_source": payoff_src,
                "warnings": warnings,
            }
        )
        total_warnings += len(warnings)

    if args.json:
        json.dump(
            {
                "thresholds": {
                    "shell_floor": SHELL_FLOOR,
                    "payoff_floor": PAYOFF_FLOOR,
                    "fast_payoff": FAST_PAYOFF,
                    "weak_shell": WEAK_SHELL,
                },
                "decks": report,
                "skipped": skipped,
                "total_warnings": total_warnings,
            },
            sys.stdout,
            indent=2,
        )
        sys.stdout.write("\n")
        return 0

    print("=== Strategy-Ceiling Check (DEC-309) ===")
    print(
        f"Thresholds: shell_floor={SHELL_FLOOR}, payoff_floor={PAYOFF_FLOOR}%, "
        f"fast_payoff(CL@T6)={FAST_PAYOFF}%, weak_shell={WEAK_SHELL}"
    )
    print()
    print(f"{'deck':<32} {'bracket':<8} {'shell':>5} {'payoff':>7} {'source':<22} flags")
    for row in report:
        flag = "WARN" if row["warnings"] else "ok"
        print(
            f"{row['deck_id']:<32} {str(row['bracket']):<8} {row['shell']:>5} "
            f"{row['payoff']:>6.1f}% {row['payoff_source']:<22} {flag}"
        )

    if total_warnings:
        print()
        print(f"=== {total_warnings} warning(s) ===")
        for row in report:
            for w in row["warnings"]:
                print(f"  [{row['deck_id']}] {w}")
    else:
        print()
        print("No strategy-ceiling warnings.")
    if skipped:
        print()
        print(f"Skipped (missing files): {', '.join(skipped)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
