# DEC-1163: the proposed test lines in the PR's own test files, on the head and on each unit survivor.
import json, os, shutil, subprocess, sys
sys.path.insert(0, '/tmp/dec1163/mutants')
from mutants import MUTANTS
WEB = '/Users/dpires/Documents/Personal/code/mtg-precon-upgrader/wt-dec1163-review/web'
F = '/tmp/dec1163/fix'
ENV = dict(os.environ, HOME=os.environ['PAPERCLIP_GITHUB_HOST_HOME'])
TESTS = ['src/__tests__/components/Shopping.test.tsx', 'src/__tests__/components/PricePausedLine.test.tsx']
for t in TESTS: shutil.copy(os.path.join(F, os.path.basename(t)), os.path.join(WEB, t))
try:
    for mid in ['HEAD', 'S4a', 'S5a', 'S9a', 'S10a', 'P3c', 'P5a']:
        edits = [] if mid == 'HEAD' else MUTANTS[mid][0]
        paths = sorted({p for p, _, _ in edits})
        try:
            for path, old, new in edits:
                full = os.path.join(WEB, path); src = open(full).read(); assert src.count(old) == 1
                open(full, 'w').write(src.replace(old, new))
            p = subprocess.run(['npx', 'vitest', 'run'] + TESTS, cwd=WEB, env=ENV, capture_output=True, text=True)
            log = f'{F}/fix-{mid}-unit.log'; open(log, 'w').write(p.stdout + p.stderr)
            import re
            s = re.sub(r'\x1b\[[0-9;]*m', '', p.stdout + p.stderr)
            print(json.dumps({'id': mid, 'exit': p.returncode, 'tests': re.findall(r'Tests\s+.*', s)[-1:], 'fail': sorted(set(re.findall(r'^ FAIL  \S+ > (.*)$', s, re.M)))[:3], 'log': log}, ensure_ascii=False), flush=True)
        finally:
            if paths: subprocess.run(['git', 'checkout', '--'] + paths, cwd=WEB, env=ENV, check=True)
    p = subprocess.run(['npm', 'run', 'typecheck'], cwd=WEB, env=ENV, capture_output=True, text=True)
    open(f'{F}/fix-typecheck.log', 'w').write(p.stdout + p.stderr)
    print('typecheck exit', p.returncode, flush=True)
finally:
    subprocess.run(['git', 'checkout', '--'] + TESTS, cwd=WEB, env=ENV, check=True)
print(subprocess.run(['git', 'status', '--porcelain'], cwd=WEB, env=ENV, capture_output=True, text=True).stdout or 'clean')
