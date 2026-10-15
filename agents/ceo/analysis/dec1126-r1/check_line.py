"""DEC-1124 fix round 1 (CEO, 2026-10-15): check the "Card pool" line of AGENTS.md byte for byte.

Usage: check_line.py <expected line file> <AGENTS.md>

Prints a 16-character digest of each side and EQUAL or DIFFERENT; exits 0 on EQUAL, 1 on
DIFFERENT, 2 when the file has no such line or more than one.
"""
import hashlib
import sys
from pathlib import Path

PREFIX = "- **Card pool**:"
expected = Path(sys.argv[1]).read_text()
lines = [l for l in Path(sys.argv[2]).read_text().splitlines(keepends=True) if l.startswith(PREFIX)]
if len(lines) != 1:
    print(f"FOUND {len(lines)} lines that start with {PREFIX!r}")
    sys.exit(2)
for name, text in (("expected", expected), (sys.argv[2], lines[0])):
    print(f"{hashlib.sha256(text.encode()).hexdigest()[:16]}  {name}")
print("EQUAL" if expected == lines[0] else "DIFFERENT")
sys.exit(0 if expected == lines[0] else 1)
