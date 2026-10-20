# Rehearsal of fix round 2 of PR #75 (DEC-1172) with git plumbing only: no checkout, no ref moves.
# Usage: python3 -I rehearse.py <repo> <main> <pr75 head>
# M = merge of <main> into <pr75 head>, web/README.md taken from pr70/README.resolved.md.
# R = M plus apply.py's edits (kill file copy is a no-op when the blob is already there).
import os, subprocess, sys, tempfile
kit = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'dec1174-r1')
sys.path.insert(0, kit)
from apply import EDITS, KILL, README, edit_text  # noqa: E402
repo, main, head = sys.argv[1:4]
def git(*a, env=None, inp=None, ok=(0,)):
    r = subprocess.run(['git', '-C', repo, *a], capture_output=True, input=inp, env={**os.environ, **(env or {})})
    if r.returncode not in ok:
        raise SystemExit(f"git {' '.join(a)}: {r.stderr.decode().strip()}")
    return r.stdout.decode()
ident = {'GIT_AUTHOR_NAME': 'ceo', 'GIT_AUTHOR_EMAIL': 'ceo@local', 'GIT_AUTHOR_DATE': '2026-10-16T14:15:00Z',
         'GIT_COMMITTER_NAME': 'ceo', 'GIT_COMMITTER_EMAIL': 'ceo@local', 'GIT_COMMITTER_DATE': '2026-10-16T14:15:00Z'}
out = git('merge-tree', '--write-tree', '--name-only', head, main, ok=(0, 1)).split('\n\n')[0].splitlines()
tree, conflicted = out[0], out[1:]
print('merge-tree', tree[:8], 'conflicted:', conflicted)
assert conflicted == [README], conflicted
with tempfile.TemporaryDirectory() as d:
    idx = {'GIT_INDEX_FILE': os.path.join(d, 'i')}
    git('read-tree', tree, env=idx)
    res = git('hash-object', '-w', os.path.join(kit, 'pr70', 'README.resolved.md')).strip()
    git('update-index', '--cacheinfo', f'100644,{res},{README}', env=idx)
    mtree = git('write-tree', env=idx).strip()
    m = git('commit-tree', mtree, '-p', head, '-p', main, '-m', 'SIM merge', env=ident).strip()
    print('M', m[:8], 'README', res[:8])
    kill = git('hash-object', '-w', os.path.join(kit, 'expected', KILL)).strip()
    print('kill file at M', git('rev-parse', f'{m}:{KILL}').strip()[:8], 'expected', kill[:8])
    for p in sorted({p for p, *_ in EDITS}):
        text = git('show', f'{m}:{p}')
        new = edit_text(p, text, log=lambda s: print(' ', s))
        b = git('hash-object', '-w', '--stdin', inp=new.encode()).strip()
        git('update-index', '--cacheinfo', f'100644,{b},{p}', env=idx)
    git('update-index', '--cacheinfo', f'100644,{kill},{KILL}', env=idx)
    rtree = git('write-tree', env=idx).strip()
r = git('commit-tree', rtree, '-p', m, '-m', 'SIM round 2', env=ident).strip()
print('R', r, 'tree', rtree[:8])
print('diff M..R:', git('diff', '--stat', m, r).strip())
print('diff main..R names:'); print(git('diff', '--name-only', main, r).strip())
