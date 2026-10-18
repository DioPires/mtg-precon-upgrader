"""Fix round 1 of PR #84 (DEC-1197): the 71 survivors of review DEC-1208 on the round's tree (CEO run b622726c, 2026-10-18).

Usage: uv run --no-project python -I mut.py <tree> <log folder>
Run it with the round's tests/test_auto_tag_roles.py in <tree> and scripts/auto_tag_roles.py at 4985520's bytes.

For each label of kill/survivors.txt, take its (old, new) text from mut/all_mutants.json (the reviewer's file),
write it into <tree>/scripts/auto_tag_roles.py (the old text must occur once), remove each __pycache__ under
scripts/ and tests/, run tests/test_auto_tag_roles.py with PYTHONDONTWRITEBYTECODE=1, save mut-<n>.log, and restore
the file's bytes (also on an error). It prints, for each mutant, the label, the old and the new text, the count line
and the failed tests. Expected (verdict ad4e8729, kill/killrun.log):
  baseline     139 passed, 130 subtests passed.
  69 labels    each fails at least one test (B1 to B9).
  I6-m, I9-p   each passes: 139 passed, 130 subtests passed (Q1: no test, CEO ruling on DEC-1197).
The last line counts the labels that fail and the labels that pass.
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

defs = {label: (old, new) for label, old, new in json.load(open(KIT / "mut" / "all_mutants.json"))}
labels = [line.strip() for line in open(KIT / "kill" / "survivors.txt") if line.strip()]
assert len(labels) == 71, len(labels)
env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")


def clear_cache():
    for sub in ("scripts", "tests"):
        for dirpath, dirnames, _ in os.walk(tree / sub):
            if "__pycache__" in dirnames:
                shutil.rmtree(os.path.join(dirpath, "__pycache__"))
                dirnames.remove("__pycache__")


def run(name):
    clear_cache()
    out = subprocess.run(
        ["uv", "run", "--with", "pytest", "python", "-m", "pytest", "-q", "-p", "no:cacheprovider",
         "tests/test_auto_tag_roles.py"],
        cwd=tree, env=env, capture_output=True, text=True,
    ).stdout
    clear_cache()
    (logs / f"mut-{name}.log").write_text(out)
    count = next((re.sub(r" in [0-9.]+s", "", l).strip("= ") for l in out.splitlines()
                  if re.search(r"\d+ (passed|failed)", l)), "?")
    failed = [l.split("::", 1)[1] for l in out.splitlines() if re.match(r"^(FAILED|SUBFAILED)", l)]
    return count, failed


print("baseline:", *run("baseline"))
died, lived = [], []
for n, label in enumerate(labels, 1):
    old, new = defs[label]
    assert text.count(old) == 1, f"{label}: old text found {text.count(old)} times"
    try:
        target.write_text(text.replace(old, new))
        count, failed = run(f"{n:02d}")
    finally:
        target.write_bytes(original)
    assert target.read_bytes() == original
    (died if failed else lived).append(label)
    print(f"=== {n:02d} {label}\n  old: {old!r}\n  new: {new!r}\n  {count}\n  "
          + "\n  ".join(f.split(" - ")[0][:170] for f in failed))
    sys.stdout.flush()
print(f"died {len(died)}, survived {len(lived)}: {', '.join(lived) or 'none'}")
