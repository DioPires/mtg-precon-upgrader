"""Fix round 1 of PR #81 (DEC-1191): the mutants of review DEC-1198 on the round's tree (CEO run 15bb14f0, 2026-10-17).

Usage: uv run --no-project python -I mut.py <tree> <log folder>
Run it after apply.py, with the round's scripts/auto_tag_roles.py and tests/test_auto_tag_roles.py in <tree>.

For each mutant: write it into <tree>/scripts/auto_tag_roles.py (its old text must occur once), remove each
__pycache__ under scripts/ and tests/, run tests/test_auto_tag_roles.py with PYTHONDONTWRITEBYTECODE=1, save
mut-<id>.log, and restore the file's bytes (also on an error). It prints one line for each mutant: the count line and
the failed tests. Expected:
  the 25 survivors of the verdict (B1, B2, B3): each fails its own kill case (the reviewer's names, X*, XW-*, Y*).
  G1  the head's lookahead (the graveyard alternative dropped): fails the B4 case (GraveyardCostFaultTests).
  G2  "from your hand" for "from your graveyard": fails the B4 case.
  G3  "exile this card" for "exile this card from your graveyard": SURVIVES. Its only kill case would pin a fault
      that the head shares (a draw behind "exile this card from your hand:" reads card-draw), so it goes to DEC-1197
      item 3 as a candidate rule (ruling on DEC-1191, CEO run 15bb14f0).
  G4  "from a graveyard" for "from your graveyard": fails the B4 case.
"""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parent
tree = Path(sys.argv[1]).resolve()
logs = Path(sys.argv[2]).resolve()
logs.mkdir(parents=True, exist_ok=True)
target = tree / "scripts" / "auto_tag_roles.py"
original = target.read_bytes()
text = original.decode()

defs = {}
for p in ("mutants_item1.json", "mutants_item1b.json", "mutants_item2.json"):
    for label, old, new in json.load(open(KIT / "reviewer" / p)):
        defs[label] = (old, new)

# The verdict's survivors, by the reviewer's labels (kill_run.py). A6 moves to the round's line.
SURVIVORS = {
    "X1": "A1 drop (?! for each)",
    "X3": "A3 drop at the beginning of",
    "X4": "A4 cantrip reads 'a card' only",
    "X5": "A5 drop 'draw cards equal to'",
    "X7": "A7 (?!the next) as (?!the next end step)",
    "X9": "A9 cantrip reads 'draw' only, not 'draws'",
    "X10": "A10 _DRAW reads 'draw' only, not 'draws'",
    "XW-one": "D-one drop 'one' from _DRAW",
    "XW-three": "D-three drop 'three' from _DRAW",
    "XW-four": "D-four drop 'four' from _DRAW",
    "XW-five": "D-five drop 'five' from _DRAW",
    "XW-six": "D-six drop 'six' from _DRAW",
    "XW-seven": "D-seven drop 'seven' from _DRAW",
    "XW-eight": "D-eight drop 'eight' from _DRAW",
    "XW-nine": "D-nine drop 'nine' from _DRAW",
    "XW-ten": "D-ten drop 'ten' from _DRAW",
    "XW-x": "D-x drop 'x' from _DRAW",
    "XW-that many": "D-that many drop 'that many' from _DRAW",
    "XW-digits": "D-digits drop \\d+ from _DRAW",
    "Y1": "B1 {1,40} as {1,20}",
    "Y2": "B2 drop ; from the qualifier",
    "Y4": "B4 destroy (?:it|that creature) as destroy it",
    "Y6": "B6 drop x of the power cut kill",
    "Y7": "B7 the guard without the qualifier",
}
MUTANTS = [(k, *defs[v]) for k, v in SURVIVORS.items()]
LOOK = "(?!sacrifice this|discard this|exile this card from your graveyard)"
MUTANTS += [
    ("X6", LOOK, "(?!sacrifice this|exile this card from your graveyard)"),
    ("M3", LOOK + "[^(\\n])*:", "[^(\\n])*:"),
    ("A11", 'r"^(?:(?!sacrifice this', 'r"(?:(?!sacrifice this'),
    ("G1", "|exile this card from your graveyard)", ")"),
    ("G2", "exile this card from your graveyard", "exile this card from your hand"),
    ("G3", "exile this card from your graveyard", "exile this card"),
    ("G4", "exile this card from your graveyard", "exile this card from a graveyard"),
]
env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")


def clear_cache():
    for sub in ("scripts", "tests"):
        for dirpath, dirnames, _ in os.walk(tree / sub):
            if "__pycache__" in dirnames:
                shutil.rmtree(os.path.join(dirpath, "__pycache__"))
                dirnames.remove("__pycache__")


def run(label):
    clear_cache()
    out = subprocess.run(
        ["uv", "run", "--with", "pytest", "python", "-m", "pytest", "-q", "-p", "no:cacheprovider",
         "tests/test_auto_tag_roles.py"],
        cwd=tree, env=env, capture_output=True, text=True,
    ).stdout
    clear_cache()
    (logs / f"mut-{label.replace(' ', '_')}.log").write_text(out)
    count = next((re.sub(r" in [0-9.]+s", "", l).strip("= ") for l in out.splitlines()
                  if re.search(r"\d+ (passed|failed)", l)), "?")
    failed = [l.split("::", 1)[1] for l in out.splitlines() if re.match(r"^(FAILED|SUBFAILED)", l)]
    return count, failed


print("baseline:", *run("baseline"))
for label, old, new in MUTANTS:
    assert text.count(old) == 1, f"{label}: old text found {text.count(old)} times"
    try:
        target.write_text(text.replace(old, new))
        count, failed = run(label)
    finally:
        target.write_bytes(original)
    assert target.read_bytes() == original
    print(f"{label}: {count} | " + "; ".join(f.split(" - ")[0] for f in failed))
    sys.stdout.flush()
