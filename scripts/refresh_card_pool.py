#!/usr/bin/env python3
"""One-shot orchestrator for the DEC-90 card-discovery pipeline.

Refreshes the local Scryfall mirror (no-op if fresh), then regenerates the
candidate pool for the requested deck(s). Idempotent end-to-end.

DEC-90 phase 4.

Usage:
    python scripts/refresh_card_pool.py [--deck DECK_ID | --all] [--limit N] [--force]
"""

import argparse
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = PROJECT_ROOT / "scripts"


def run(cmd: list[str]) -> int:
    print(f"$ {' '.join(cmd)}", file=sys.stderr)
    result = subprocess.run(cmd)
    return result.returncode


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Refresh Scryfall mirror + regenerate candidate pools")
    target = parser.add_mutually_exclusive_group()
    target.add_argument("--deck", help="Single deck id")
    target.add_argument("--all", action="store_true", help="All decks")
    parser.add_argument("--limit", type=int, default=200, help="Top-N candidates per deck (default 200)")
    parser.add_argument("--force", action="store_true", help="Force mirror re-download even if current")
    args = parser.parse_args(argv)

    if not args.deck and not args.all:
        args.all = True

    mirror_cmd = [sys.executable, str(SCRIPTS / "refresh_scryfall_mirror.py")]
    if args.force:
        mirror_cmd.append("--force")
    rc = run(mirror_cmd)
    if rc != 0:
        print("Mirror refresh failed.", file=sys.stderr)
        return rc

    gen_cmd = [
        sys.executable, str(SCRIPTS / "generate_candidate_pool.py"),
        "--limit", str(args.limit),
    ]
    if args.deck:
        gen_cmd += ["--deck", args.deck]
    else:
        gen_cmd.append("--all")
    rc = run(gen_cmd)
    if rc != 0:
        return rc

    metrics_cmd = [sys.executable, str(SCRIPTS / "compute_deck_metrics.py")]
    if args.deck:
        metrics_cmd += ["--deck", args.deck]
    else:
        metrics_cmd.append("--all")
    return run(metrics_cmd)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
