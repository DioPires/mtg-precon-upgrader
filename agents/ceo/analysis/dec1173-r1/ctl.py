# The CEO's controls for core.py (DEC-1173 routing). Usage: python3 -I ctl.py <repo>
# Builds local commits only (git commit-tree; no ref moves, nothing is pushed):
#   A  the head 0cfe1f3 itself: the kill file is missing, so NOT EQUAL.
#   B  the round as asked: a merge of origin/main into the head, then the kill file without its
#      last header line ("Copy it to ...", stale in the tree) and with one call wrapped: ALL EQUAL.
#   C  B with the file's prices 2 days old in place of 3: DIFFERENT.
#   D  PR #74 (7cba124, Shopping.tsx and Shopping.test.tsx) merged into main first: ALL EQUAL.
#   E  PR #66 (3c3a151, Shopping.tsx and Shopping.test.tsx) merged into main first: ALL EQUAL.
import os, subprocess, sys, tempfile

repo = sys.argv[1]
here = os.path.dirname(os.path.abspath(__file__))
HEAD = '0cfe1f3d51dabdbb15e19671da9c750d5924103a'
KILL = 'web/src/__tests__/components/dec1173-stopline-date.test.tsx'
ident = {'GIT_AUTHOR_NAME': 'ceo', 'GIT_AUTHOR_EMAIL': 'ceo@local', 'GIT_AUTHOR_DATE': '2026-10-16T10:00:00Z',
         'GIT_COMMITTER_NAME': 'ceo', 'GIT_COMMITTER_EMAIL': 'ceo@local', 'GIT_COMMITTER_DATE': '2026-10-16T10:00:00Z'}


def git(*a, ok_codes=(0,), env=None, inp=None):
    r = subprocess.run(['git', '-C', repo, *a], capture_output=True, text=True, input=inp,
                       env={**os.environ, **ident, **(env or {})})
    if r.returncode not in ok_codes:
        raise SystemExit(f"git {' '.join(a)}: {r.stderr.strip()}")
    return r.stdout


def blob_of(text):
    return git('hash-object', '-w', '--stdin', inp=text).strip()


def commit(tree, parents, files, msg):
    with tempfile.TemporaryDirectory() as d:
        idx = {'GIT_INDEX_FILE': os.path.join(d, 'index')}
        git('read-tree', tree, env=idx)
        for path, text in files.items():
            git('update-index', '--add', '--cacheinfo', f'100644,{blob_of(text)},{path}', env=idx)
        t = git('write-tree', env=idx).strip()
    args = ['commit-tree', t]
    for p in parents:
        args += ['-p', p]
    return git(*args, '-m', msg).strip()


def core(ref, main=None):
    cmd = ['python3', '-I', os.path.join(here, 'core.py'), repo, ref] + ([main] if main else [])
    r = subprocess.run(cmd, capture_output=True, text=True)
    return (r.stdout + r.stderr).strip()


exp = open(os.path.join(here, 'expected', KILL)).read()
old_c = '// Copy it to web/src/__tests__/components/ to run it.\n'
old_w = '    expect(line.textContent).not.toContain(file);\n'
assert exp.count(old_c) == 1 and exp.count(old_w) == 1
reworded = exp.replace(old_c, '').replace(old_w, '    expect(line.textContent)\n      .not.toContain(file);\n')
old_v = 'const OLD = new Date(Date.now() - 3 * DAY).toISOString();'
assert reworded.count(old_v) == 1
changed = reworded.replace(old_v, 'const OLD = new Date(Date.now() - 2 * DAY).toISOString();')

main = git('rev-parse', 'origin/main').strip()
print('A  0cfe1f3 itself')
print(core(HEAD))
m1 = commit(git('merge-tree', '--write-tree', main, HEAD).split()[0], [HEAD, main], {}, 'CTL: merge origin/main')
b = commit(m1, [m1], {KILL: reworded}, 'CTL B: the kill file, header line dropped and one call wrapped')
print(f'\nB  the round as asked ({b[:7]})')
print(core(b))
c = commit(m1, [m1], {KILL: changed}, 'CTL C: the file prices 2 days old')
print(f'\nC  the file prices 2 days old ({c[:7]})')
print(core(c))
for tag, n, other in (('D', 74, '7cba124'), ('E', 66, '3c3a151')):
    sm = commit(git('merge-tree', '--write-tree', main, other).split()[0], [main, other], {}, f'CTL: simulated main with PR #{n}')
    out = git('merge-tree', '--write-tree', '--name-only', sm, HEAD, ok_codes=(0, 1)).split('\n\n')[0].splitlines()
    m2 = commit(out[0], [HEAD, sm], {}, f'CTL: merge of the simulated main with PR #{n}')
    dd = commit(m2, [m2], {KILL: reworded}, f'CTL {tag}: the kill file after PR #{n}')
    print(f'\n{tag}  PR #{n} merged first (simulated main {sm[:7]}, conflicts {out[1:]}, round {dd[:7]})')
    print(core(dd, sm))
