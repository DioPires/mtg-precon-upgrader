#!/usr/bin/env python3
"""Backward-compatible wrapper for the deck JSON validator."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.validate_deck_json import main  # noqa: E402


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
