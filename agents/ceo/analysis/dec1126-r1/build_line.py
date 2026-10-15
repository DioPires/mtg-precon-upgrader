"""DEC-1124 fix round 1 (CEO, 2026-10-15): build the expected "Card pool" line of AGENTS.md (N1 of DEC-1126).

Usage: build_line.py <AGENTS.md of the merged tree> <out file>

Takes the one line that starts with "- **Card pool**:", asserts the anchor once, and inserts
the N1 sentences after the agent-run command's closing parenthesis. Writes the line with its newline.
"""
import sys
from pathlib import Path

PREFIX = "- **Card pool**:"
ANCHOR = "/mtg-precon-upgrader/scripts/card_lookup.py`). Nobody sends `curl`"
NEW = ("/mtg-precon-upgrader/scripts/card_lookup.py`). QUERY takes Scryfall's search syntax, "
       "`released<=YYYY-MM-DD` included. Put single quotes around a QUERY that holds a double quote. "
       "Nobody sends `curl`")

lines = [l for l in Path(sys.argv[1]).read_text().splitlines(keepends=True) if l.startswith(PREFIX)]
assert len(lines) == 1, len(lines)
line = lines[0]
assert line.count(ANCHOR) == 1, line.count(ANCHOR)
assert 'card_lookup.py --search "QUERY"` (from eternities-mtg-app' in line
Path(sys.argv[2]).write_text(line.replace(ANCHOR, NEW))
