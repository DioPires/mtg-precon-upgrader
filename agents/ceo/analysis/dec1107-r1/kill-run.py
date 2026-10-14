"""DEC-1092 fix round 1 kit (CEO copy of the DEC-1107 reviewer's kill-run.py; the runner path now points into this kit).

DEC-1107: apply one mutant of mutants-dec1107.py to MUTANT_TREE, run a command, restore.

Usage: MUTANT_TREE=<tree> uv run --no-project python kill-run.py <ID> -- <command ...>
The tree must be clean (tracked files) before and after, and /tmp/scryfall-limit must not exist.
"""
import importlib.util, os, subprocess, sys
from pathlib import Path

spec = importlib.util.spec_from_file_location("runner", Path(__file__).resolve().parent / "reviewer" / "mutants-dec1107.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

mid, command = sys.argv[1], sys.argv[sys.argv.index("--") + 1:]
[(mid, text, target, pairs)] = [m for m in runner.MUTANTS if m[0] == mid]
assert runner.git("status", "--porcelain", "--untracked-files=no") == "", "the tree is not clean"
assert not Path("/tmp/scryfall-limit").exists()
paths = [runner.TREE / p for p in (runner.COPIES if target == runner.LIMIT else [target])]
originals = {p: p.read_text() for p in paths}
try:
    for p, original in originals.items():
        mutated = original
        for old, new in pairs:
            assert mutated.count(old) == 1, (mid, p, old[:60])
            mutated = mutated.replace(old, new)
        p.write_text(mutated)
    runner.clean_caches()
    print(f"== mutant {mid}: {text}", flush=True)
    rc = subprocess.run(command, cwd=runner.TREE, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}).returncode
finally:
    for p, original in originals.items():
        p.write_text(original)
    runner.clean_caches()
assert runner.git("status", "--porcelain", "--untracked-files=no") == ""
assert not Path("/tmp/scryfall-limit").exists()
print(f"== exit code of the command on mutant {mid}: {rc}")
