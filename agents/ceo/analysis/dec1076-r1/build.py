"""Build the expected tests/test_scryfall_pins.py of DEC-1076 fix round 1 from the DEC-1093 kill file.

Two changes, each asserted by its old text: the module docstring is replaced, and the unused
`import json` is dropped. Every other line is the reviewer's text.
"""
import sys
from pathlib import Path

SRC = Path("/tmp/dec1093/kill/test_kill_dec1093.py")
OUT = Path(sys.argv[1])
text = SRC.read_text()
old_doc = text[: text.index('"""\n\nimport contextlib') + 4]
assert old_doc.startswith('"""DEC-1093 item 10 d: kill cases'), old_doc[:60]
new_doc = (
    '"""Cases that pin what the Scryfall callers send.\n'
    "\n"
    "The review of PR #30 (DEC-1093) found six mutants that the other Scryfall test files let\n"
    "pass. Each case here kills one of them, and its docstring names the mutant.\n"
    '"""\n'
)
text = new_doc + text[len(old_doc):]
assert text.count("import json\n") == 1
text = text.replace("import json\n", "", 1)
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(text)
print(OUT)
