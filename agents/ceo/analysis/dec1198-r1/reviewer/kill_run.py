"""kill_run.py TREE: run the DEC-1198 kill file on the head, on each surviving mutant, and on the P2 fix.

For each mutant: apply it to TREE/scripts/auto_tag_roles.py, remove each __pycache__ under scripts/ and
tests/, run the kill file with PYTHONDONTWRITEBYTECODE=1, then restore with `git checkout` and check
`git diff --quiet`. The P2 fix runs from /tmp/dec1198/fixroot (a copy of the fix file and of the
test file), so the tree is not touched for it.
"""
import json
import os
import re
import shutil
import subprocess
import sys

tree = sys.argv[1]
T = "/tmp/dec1198"
KILL = f"{T}/kill/test_dec1198_kill.py"
target = os.path.join(tree, "scripts", "auto_tag_roles.py")
env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", HOME=os.environ["PAPERCLIP_GITHUB_HOST_HOME"])
SURVIVORS = {
    "X1": "A1 drop (?! for each)",
    "X3": "A3 drop at the beginning of",
    "X4": "A4 cantrip reads 'a card' only",
    "X5": "A5 drop 'draw cards equal to'",
    "X6": "A6 drop 'discard this' from the cost lookahead",
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
defs = {}
for p in ("mutants_item1.json", "mutants_item1b.json", "mutants_item2.json"):
    for label, old, new in json.load(open(f"{T}/{p}")):
        defs[label] = (old, new)


def clear_cache(root):
    for sub in ("scripts", "tests"):
        for dirpath, dirnames, _ in os.walk(os.path.join(root, sub)):
            if "__pycache__" in dirnames:
                shutil.rmtree(os.path.join(dirpath, "__pycache__"))
                dirnames.remove("__pycache__")


def run(root, files):
    clear_cache(root)
    out = subprocess.run(
        ["uv", "run", "--with", "pytest", "python", "-m", "pytest", "-q", "-p", "no:cacheprovider", *files],
        cwd=root, env=dict(env, ATR_ROOT=root), capture_output=True, text=True,
    ).stdout
    clear_cache(root)
    return [re.sub(r" in [0-9.]+s", "", l) for l in out.splitlines()
            if re.match(r"^(FAILED|SUBFAILED)|.* (passed|failed)", l)]


print("=== head 699cb7e: the kill file")
for l in run(tree, [KILL]):
    print("  " + l)
original = open(target).read()
for short, label in SURVIVORS.items():
    old, new = defs[label]
    assert original.count(old) == 1, label
    open(target, "w").write(original.replace(old, new))
    lines = run(tree, [KILL])
    subprocess.run(["git", "checkout", "--", "scripts/auto_tag_roles.py"], cwd=tree, env=env, check=True)
    ok = subprocess.run(["git", "diff", "--quiet"], cwd=tree, env=env).returncode == 0
    print(f"=== {short} ({label})")
    for l in lines:
        if "GraveyardCostFault" not in l:
            print("  " + l)
    print(f"  restored: {'ok' if ok else 'FAILED'}")
    sys.stdout.flush()

fixroot = f"{T}/fixroot"
shutil.rmtree(fixroot, ignore_errors=True)
os.makedirs(f"{fixroot}/scripts")
os.makedirs(f"{fixroot}/tests")
shutil.copy(f"{T}/snap/atr_fix_p2.py", f"{fixroot}/scripts/auto_tag_roles.py")
shutil.copy(os.path.join(tree, "tests", "test_auto_tag_roles.py"), f"{fixroot}/tests/")
print("=== the P2 fix (fixroot): the suite's test file and the kill file")
for l in run(fixroot, ["tests/test_auto_tag_roles.py", KILL]):
    print("  " + l)
