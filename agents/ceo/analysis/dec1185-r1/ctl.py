# Controls for core.py (DEC-1185 route A). Usage: python3 -I ctl.py <repo>
# Builds local commits only (a temporary index; no ref moves, nothing is pushed), then runs core.py on each.
# A: the head with the expected files.            Expect ALL EQUAL.
# B: comments reworded and one call wrapped.      Expect ALL EQUAL.
# C: '24px' read as '18px' in the spec.           Expect NOT EQUAL.
# D: A merged after PR #72 merged first.          Expect ALL EQUAL (core.py's third argument is that main).
# E: A merged after PR #66 merged first.          Expect ALL EQUAL.
import os, subprocess, sys, tempfile
repo = sys.argv[1]
here = os.path.dirname(os.path.abspath(__file__))
HEAD = '3a3b8fcfeb769c36a6e4325af7e3657d8581ae4f'
SHOP = 'web/src/__tests__/components/Shopping.test.tsx'
SPEC = 'web/tests/dec1177-empty-sigils.spec.ts'
ident = {'GIT_AUTHOR_NAME': 'ceo', 'GIT_AUTHOR_EMAIL': 'ceo@local', 'GIT_AUTHOR_DATE': '2026-10-16T13:00:00Z',
         'GIT_COMMITTER_NAME': 'ceo', 'GIT_COMMITTER_EMAIL': 'ceo@local', 'GIT_COMMITTER_DATE': '2026-10-16T13:00:00Z'}

def git(*a, env=None, ok=(0,)):
    r = subprocess.run(['git', '-C', repo, *a], capture_output=True, text=True, env={**os.environ, **ident, **(env or {})})
    if r.returncode not in ok:
        raise SystemExit(f"git {' '.join(a)}: {r.stderr.strip()}")
    return r.stdout.strip()

def commit(files, msg):
    with tempfile.TemporaryDirectory() as d:
        idx = {'GIT_INDEX_FILE': os.path.join(d, 'index')}
        git('read-tree', HEAD, env=idx)
        for path, src in files.items():
            blob = git('hash-object', '-w', src)
            git('update-index', '--cacheinfo', f'100644,{blob},{path}', env=idx)
        tree = git('write-tree', env=idx)
    return git('commit-tree', tree, '-p', HEAD, '-m', msg)

def merge(a, b, msg):
    out = git('merge-tree', '--write-tree', a, b, ok=(0, 1)).split('\n')
    assert len(out) == 1, ('conflict', out[:5])
    return git('commit-tree', out[0], '-p', a, '-p', b, '-m', msg)

E = lambda p: os.path.join(here, 'expected', p)
A = commit({SHOP: E(SHOP), SPEC: E(SPEC)}, 'ctl A')
B = commit({SHOP: E(SHOP), SPEC: os.path.join(here, 'controls/B-reworded-wrapped.spec.ts')}, 'ctl B')
C = commit({SHOP: E(SHOP), SPEC: os.path.join(here, 'controls/C-figure.spec.ts')}, 'ctl C')
M72 = merge(git('rev-parse', 'origin/main'), '47d2db3', 'sim main + PR #72')
M66 = merge(git('rev-parse', 'origin/main'), '3c3a151', 'sim main + PR #66')
D = merge(A, M72, 'ctl D')
Ectl = merge(A, M66, 'ctl E')
for name, ref, main in (('A', A, 'origin/main'), ('B', B, 'origin/main'), ('C', C, 'origin/main'), ('D', D, M72), ('E', Ectl, M66)):
    r = subprocess.run([sys.executable, '-I', os.path.join(here, 'core.py'), repo, ref, main], capture_output=True, text=True)
    print(f'--- control {name} ({ref[:7]}, main {main[:7]}): exit {r.returncode}')
    print(r.stdout.strip())
