"""DEC-1078 fix round 1, route A file check (CEO, 2026-10-15).

Usage: check.py <tree root>   (run with the kit folder as this script's folder)

Test files: compare.py (syntax trees with docstrings removed) against expected/tests/<file>.
Documents: the bytes must equal expected/<path> (git hash-object on both sides). The root
AGENTS.md is kept as expected/root-AGENTS.md, so that no tool reads the kit copy as an instruction file.
Prints one line for each file and ALL EQUAL or NOT EQUAL; exits 0 on ALL EQUAL.
"""
import subprocess
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parent
tree = Path(sys.argv[1]).resolve()
ok = True
for rel in ("tests/test_generate_candidate_pool.py", "tests/test_write_metrics.py"):
    proc = subprocess.run([sys.executable, str(KIT / "compare.py"), str(KIT / "expected" / rel), str(tree / rel)],
                          capture_output=True, text=True)
    verdict = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else proc.stderr.strip()
    print(f"{rel}: {verdict}")
    ok = ok and proc.returncode == 0
for rel in ("docs/discovery-playbook.md", "AGENTS.md"):
    want = KIT / "expected" / ("root-AGENTS.md" if rel == "AGENTS.md" else rel)
    have = tree / rel
    if not have.is_file():
        print(f"{rel}: MISSING")
        ok = False
        continue
    blobs = subprocess.run(["git", "hash-object", str(want), str(have)], capture_output=True, text=True).stdout.split()
    print(f"{rel}: expected {blobs[0][:8]} actual {blobs[1][:8]} {'EQUAL' if blobs[0] == blobs[1] else 'DIFFERENT'}")
    ok = ok and blobs[0] == blobs[1]
print("ALL EQUAL" if ok else "NOT EQUAL")
sys.exit(0 if ok else 1)
