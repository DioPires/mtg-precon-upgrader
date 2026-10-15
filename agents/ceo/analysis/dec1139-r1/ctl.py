# CEO controls for route A, fix round 1 of PR #53 (DEC-1139). Usage:
#   python3 -I ctl.py <tree> <logdir> <id> [<id> ...]   (id: head, or a mutant id of reviewer/mutants.py)
# Applies one mutant at a time to Shopping.tsx in <tree>, runs the unit file
# src/__tests__/components/Shopping.test.tsx, saves a log, restores the file.
import os, re, subprocess, sys
here = os.path.dirname(os.path.abspath(__file__))
tree, logs, ids = sys.argv[1], sys.argv[2], sys.argv[3:]
SRC = 'web/src/components/organisms/Shopping.tsx'
# Reviewer's table, read as text (mutants.py imports paths of the reviewer's removed tree).
txt = open(os.path.join(here, 'reviewer', 'mutants.py')).read()
ns = {}
exec(txt.split('MUTANTS = [')[0].split('TREE =')[0] + '\n'.join(
    l for l in txt.splitlines() if l.startswith(('L492', 'L493', 'L665'))) + '\nMUTANTS = [' +
    txt.split('MUTANTS = [', 1)[1].split('\n]\n', 1)[0] + '\n]\n', ns)
by_id = {m[0]: m for m in ns['MUTANTS']}
env = dict(os.environ, HOME=os.environ['PAPERCLIP_GITHUB_HOST_HOME'])
strip = lambda s: re.sub(r'\x1b\[[0-9;]*m', '', s)
def git(*a):
    return subprocess.run(['git', '-C', tree, *a], capture_output=True, text=True, env=env)
for mid in ids:
    assert not git('status', '--porcelain').stdout.strip(), 'tree not clean before ' + mid
    if mid != 'head':
        _, line, old, new, desc = by_id[mid]
        p = os.path.join(tree, SRC); s = open(p).read()
        assert s.count(old) == 1, (mid, s.count(old)); open(p, 'w').write(s.replace(old, new))
    diff = git('diff', '--', SRC).stdout
    cmd = ['npx', 'vitest', 'run', 'src/__tests__/components/Shopping.test.tsx']
    r = subprocess.run(cmd, cwd=os.path.join(tree, 'web'), env=env, capture_output=True, text=True)
    git('checkout', '--', SRC)
    out = strip(r.stdout + r.stderr)
    log = os.path.join(logs, f'unit-{mid}.log')
    open(log, 'w').write(f'# {mid}\n# command: {" ".join(cmd)}\n# exit {r.returncode}\n{diff}\n{out}')
    count = [l.strip() for l in out.splitlines() if re.match(r'\s*Tests\s', l)]
    fails = sorted(set(re.findall(r'FAIL .*?> (.*?)(?:\n| \d+ms)', out)))
    print(mid, 'exit', r.returncode, ' / '.join(count), os.path.basename(log), flush=True)
    for f in fails: print('    FAIL', f[:150])
