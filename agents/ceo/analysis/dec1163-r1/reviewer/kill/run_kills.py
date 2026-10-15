# DEC-1163: run the kill files on the head and on each surviving mutant. Copies the kill files into
# the tree for the run, then removes them and restores every mutated file from git.
import json, os, shutil, subprocess, sys
sys.path.insert(0, '/tmp/dec1163/mutants')
from mutants import MUTANTS
WEB = '/Users/dpires/Documents/Personal/code/mtg-precon-upgrader/wt-dec1163-review/web'
K = '/tmp/dec1163/kill'
H = os.environ['PAPERCLIP_GITHUB_HOST_HOME']
ENV = dict(os.environ, HOME=H, PLAYWRIGHT_BROWSERS_PATH=H + '/Library/Caches/ms-playwright', GRIMOIRE_E2E_PORT='14866')
FILES = {
  'dec1163-kill-import-style.test.tsx': 'src/__tests__/components/',
  'dec1163-kill-paused-line.test.tsx': 'src/__tests__/components/',
  'dec1163-kill-summary.spec.ts': 'tests/',
}
UNIT = ['npx', 'vitest', 'run', 'src/__tests__/components/dec1163-kill-import-style.test.tsx', 'src/__tests__/components/dec1163-kill-paused-line.test.tsx']
E2E = ['npx', 'playwright', 'test', 'tests/dec1163-kill-summary.spec.ts', '--workers', '3']
PLAN = {'HEAD': [UNIT, E2E], 'S4a': [UNIT], 'S5a': [UNIT], 'S9a': [UNIT], 'S10a': [UNIT], 'P3c': [UNIT], 'P5a': [UNIT], 'C1b': [E2E], 'C3a': [E2E]}
placed = []
for name, d in FILES.items():
    dst = os.path.join(WEB, d, name); shutil.copy(os.path.join(K, name), dst); placed.append(dst)
try:
    for mid in (sys.argv[1:] or list(PLAN)):
        edits = [] if mid == 'HEAD' else MUTANTS[mid][0]
        paths = sorted({p for p, _, _ in edits})
        try:
            for path, old, new in edits:
                full = os.path.join(WEB, path); src = open(full).read()
                assert src.count(old) == 1, (mid, path)
                open(full, 'w').write(src.replace(old, new))
            for cmd in PLAN[mid]:
                suite = 'unit' if 'vitest' in cmd else 'e2e'
                p = subprocess.run(cmd, cwd=WEB, env=ENV, capture_output=True, text=True)
                log = f'{K}/kill-{mid}-{suite}.log'
                open(log, 'w').write(p.stdout + p.stderr)
                print(json.dumps({'id': mid, 'suite': suite, 'exit': p.returncode, 'log': log}), flush=True)
        finally:
            if paths: subprocess.run(['git', 'checkout', '--'] + paths, cwd=WEB, env=ENV, check=True)
finally:
    for f in placed: os.remove(f)
print(subprocess.run(['git', 'status', '--porcelain'], cwd=WEB, env=ENV, capture_output=True, text=True).stdout or 'clean', flush=True)
