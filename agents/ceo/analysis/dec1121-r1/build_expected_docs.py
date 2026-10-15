"""DEC-1078 fix round 1 (CEO, 2026-10-15): build the two expected documents for note N1.

Usage: build_expected_docs.py <head docs/discovery-playbook.md> <head AGENTS.md> <out dir>

Each edit replaces one exact span of the head's file (PR #41 at 9923959) and asserts that
the span occurs once. The output is the expected file, byte for byte.
"""
import sys
from pathlib import Path

playbook, agents, out = (Path(p) for p in sys.argv[1:4])

EDITS = {
    playbook: (
        out / "docs" / "discovery-playbook.md",
        "A pinned card sits at its score-order position, so the file stays sorted by score, and carries",
        "A pinned card sits at its score-order position, so the file stays sorted by score, except that a "
        "step-2 gap seat can outscore the cards above it (see **Gap seats**), and carries",
    ),
    agents: (
        out / "root-AGENTS.md",
        "Any high-scoring candidate that is *not* in the decklist must be explicitly considered. ",
        "Any high-scoring candidate that is *not* in the decklist must be explicitly considered. "
        "Read every entry flagged `seeded_for_gap` too: the gap seats sit after the top 200, and a "
        "step-2 seat can outscore the cut. ",
    ),
}

for src, (dst, old, new) in EDITS.items():
    text = src.read_text()
    assert text.count(old) == 1, (src, text.count(old))
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(text.replace(old, new))
    print(f"wrote {dst}")
