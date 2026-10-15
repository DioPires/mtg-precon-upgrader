# The CEO's mutant runs for fix round 1 of PR #65 (DEC-1154, review DEC-1163).
# Usage: python3 -I ctl.py <tree> <log dir> [ID ...]   (no ID runs HEAD and the 8 survivors)
# <tree> is a committed tree that holds the three route A files (a clean `git status`).
# Mutants: the reviewer's own list (reviewer/mutants/mutants.py, unchanged). Each mutant edits
# one product file; the script restores it with `git checkout --` after the run.
# Environment: GRIMOIRE_E2E_PORT must be set; HOME and PLAYWRIGHT_BROWSERS_PATH are set here.
import json, os, subprocess, sys

here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(here, 'reviewer', 'mutants'))
from mutants import MUTANTS  # noqa: E402

tree, logs = sys.argv[1], sys.argv[2]
WEB = os.path.join(tree, 'web')
H = os.environ['PAPERCLIP_GITHUB_HOST_HOME']
ENV = dict(os.environ, HOME=H, PLAYWRIGHT_BROWSERS_PATH=H + '/Library/Caches/ms-playwright')
assert ENV.get('GRIMOIRE_E2E_PORT'), 'set GRIMOIRE_E2E_PORT'
UNIT = ['npx', 'vitest', 'run', 'src/__tests__/components/Shopping.test.tsx',
        'src/__tests__/components/PricePausedLine.test.tsx']
E2E = ['npx', 'playwright', 'test', 'tests/dec1154-shop-summary-rule.spec.ts', '--workers', '3']
PLAN = {'HEAD': [UNIT, E2E], 'S4a': [UNIT], 'S5a': [UNIT], 'S9a': [UNIT], 'S10a': [UNIT],
        'P3c': [UNIT], 'P5a': [UNIT], 'C1b': [E2E], 'C3a': [E2E]}

status = subprocess.run(['git', 'status', '--porcelain'], cwd=tree, env=ENV, capture_output=True, text=True).stdout
assert not status.strip(), 'the tree has changes:\n' + status
os.makedirs(logs, exist_ok=True)
for mid in (sys.argv[3:] or list(PLAN)):
    edits = [] if mid == 'HEAD' else MUTANTS[mid][0]
    paths = sorted({p for p, _, _ in edits})
    try:
        for path, old, new in edits:
            full = os.path.join(WEB, path)
            src = open(full).read()
            assert src.count(old) == 1, (mid, path)
            open(full, 'w').write(src.replace(old, new))
        for cmd in PLAN[mid]:
            suite = 'unit' if 'vitest' in cmd else 'e2e'
            p = subprocess.run(cmd, cwd=WEB, env=ENV, capture_output=True, text=True)
            log = os.path.join(logs, f'{mid}-{suite}.log')
            open(log, 'w').write(p.stdout + p.stderr)
            tail = [l.strip() for l in (p.stdout + p.stderr).splitlines()
                    if l.strip().startswith(('Tests ', 'Test Files')) or ' passed (' in l or ' failed' in l]
            print(json.dumps({'id': mid, 'suite': suite, 'exit': p.returncode, 'tail': tail[-3:], 'log': log}),
                  flush=True)
    finally:
        if paths:
            subprocess.run(['git', 'checkout', '--'] + paths, cwd=WEB, env=ENV, check=True)
print(subprocess.run(['git', 'status', '--porcelain'], cwd=tree, env=ENV, capture_output=True, text=True).stdout
      or 'clean', flush=True)
