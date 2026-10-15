# Route A file check for fix round 1 of PR #61 (DEC-1142, review DEC-1151).
# Usage: python3 -I core.py <repo> <ref>      (run `git fetch origin` first)
# The script builds SIM: the head e882c60 with the three expected unit files (expected/web/...),
# as a local commit that nothing pushes. It then merges SIM with <base> = `git merge-base <ref>
# origin/main` (git merge-tree, no ref moves). So the check holds whether or not the round
# merged main, and in either merge order with PR #54 and PR #60.
# 1. Each unit file at <ref> against the file of that merge: drop blank lines and lines that
#    hold only a // comment, drop all whitespace and a comma before ) ] or }. Comments and
#    wrapping may differ; code may not.
# 2. Every other path at <ref> keeps the blob of that merge. A path that the merge leaves in
#    conflict is named, and the CEO reads it by hand.
import hashlib, os, re, subprocess, sys, tempfile

repo, ref = sys.argv[1], sys.argv[2]
MAIN = sys.argv[3] if len(sys.argv) > 3 else 'origin/main'  # a third argument only for the CEO's controls
HEAD = 'e882c609e98cb83b38fc65d3aa7a763d8a9f9725'
PATHS = {
    'web/src/__tests__/components/Shopping.test.tsx': 'a3cac46b',
    'web/src/__tests__/components/Engine.test.tsx': 'ce9fce8f',
    'web/src/__tests__/lib/cardNoun.test.ts': '1ad7b50b',
}
here = os.path.dirname(os.path.abspath(__file__))


def git(*a, ok_codes=(0,), env=None):
    r = subprocess.run(['git', '-C', repo, *a], capture_output=True, text=True,
                       env={**os.environ, **(env or {})})
    if r.returncode not in ok_codes:
        raise SystemExit(f"git {' '.join(a)}: {r.stderr.strip()}")
    return r.stdout


def code(text):
    keep = [l for l in text.splitlines() if l.strip() and not l.strip().startswith('//')]
    return re.sub(r',([)\]}])', r'\1', re.sub(r'\s+', '', '\n'.join(keep)))


def h(s):
    return hashlib.sha256(s.encode()).hexdigest()[:16]


def blobs(treeish):
    out = {}
    for line in git('ls-tree', '-r', treeish).splitlines():
        meta, path = line.split('\t', 1)
        out[path] = meta.split()[2]
    return out


with tempfile.TemporaryDirectory() as d:
    idx = {'GIT_INDEX_FILE': os.path.join(d, 'index')}
    git('read-tree', HEAD, env=idx)
    for path, want_id in PATHS.items():
        blob = git('hash-object', '-w', os.path.join(here, 'expected', path)).strip()
        assert blob.startswith(want_id), (path, blob)
        git('update-index', '--cacheinfo', f'100644,{blob},{path}', env=idx)
    sim_tree = git('write-tree', env=idx).strip()
ident = {'GIT_AUTHOR_NAME': 'ceo', 'GIT_AUTHOR_EMAIL': 'ceo@local', 'GIT_AUTHOR_DATE': '2026-10-15T16:00:00Z',
         'GIT_COMMITTER_NAME': 'ceo', 'GIT_COMMITTER_EMAIL': 'ceo@local', 'GIT_COMMITTER_DATE': '2026-10-15T16:00:00Z'}
sim = git('commit-tree', sim_tree, '-p', HEAD, '-m', 'SIM: e882c60 + expected unit files (DEC-1151 route A)', env=ident).strip()

base = git('merge-base', ref, MAIN).strip()
mt = git('merge-tree', '--write-tree', '--name-only', base, sim, ok_codes=(0, 1)).split('\n\n')[0].splitlines()
tree, conflicted = mt[0], set(mt[1:])
want = blobs(tree)
have = blobs(ref)

ok = True
for path in PATHS:
    if path in conflicted:
        print(path, 'CONFLICT in the merge of SIM with main: read it by hand')
        ok = False
        continue
    exp = code(git('cat-file', 'blob', want[path]))
    got = code(git('show', f'{ref}:{path}'))
    same = exp == got
    ok &= same
    print(path, h(exp), h(got), 'EQUAL' if same else 'DIFFERENT')
for p in sorted(conflicted - set(PATHS)):
    print(p, 'CONFLICT in the merge of SIM with main: read it by hand')
others = sorted((set(want) | set(have)) - set(PATHS) - conflicted)
changed = [p for p in others if want.get(p) != have.get(p)]
for p in changed:
    print(p, (want.get(p) or 'missing')[:8], (have.get(p) or 'missing')[:8], 'CHANGED')
print(f'base {base[:7]}, SIM {sim[:7]}: {len(others)} other paths', 'keep their blobs' if not changed else f'{len(changed)} CHANGED')
ok &= not changed and not conflicted
print('ALL EQUAL' if ok else 'NOT EQUAL')
sys.exit(0 if ok else 1)
