# The CEO's mutant runs for fix round 1 of PR #61 (DEC-1142, review DEC-1151).
# Usage: python3 -I ctl.py <tree> <log dir> [ID ...]   (no ID runs all 77 mutants)
# Runs the reviewer's mutant list (reviewer/mutants.py, unchanged) on <tree>, a detached tree of
# e882c60 with the expected unit files committed locally (never pushed). Each mutant runs its
# own unit file; the tree must be clean before each mutant, and git checkout restores it after.
import json, os, sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'reviewer'))
import mutants as mu  # noqa: E402

mu.TREE = Path(sys.argv[1])
mu.WEB = mu.TREE / 'web'
mu.LOGS = Path(sys.argv[2])
mu.LOGS.mkdir(parents=True, exist_ok=True)
want = set(sys.argv[3:])
res = [mu.run(*m) for m in mu.M if not want or m[0] in want]
(mu.LOGS / 'results.json').write_text(json.dumps(res, indent=2))
for r in res:
    print(f"{r['id']:4} {r['verdict']:8} {r['count']:40} clean={r['clean_after']} {r['note']}")
print(sum(r['verdict'] == 'killed' for r in res), 'killed,', sum(r['verdict'] == 'survived' for r in res), 'survived')
