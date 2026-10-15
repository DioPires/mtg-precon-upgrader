# Route A file check for fix round 1 of PR #60 (DEC-1141, review DEC-1150).
# Usage: python3 -I core.py <repo> <ref>      (run `git fetch origin` first)
# The script builds SIM: the head af1f93b with the reviewer's kill file at
# web/src/__tests__/dec1150/kill-shopping.test.tsx (expected/<path>), as a local commit that nothing
# pushes. It then merges SIM with <base> = `git merge-base <ref> origin/main` (git merge-tree, no ref
# moves). So the check holds whatever merged into `main` before the round's merge of `main`.
# 1. The kill file at <ref> against the file of that merge: drop blank lines and lines that hold only
#    a // comment, drop all whitespace and a comma before ) ] or }. Comments and wrapping may differ;
#    code may not.
# 2. Every other path at <ref> keeps the blob of that merge.
# 3. Shopping.test.tsx conflicts when PR #61 (DEC-1142) merged first: both pull requests add a block
#    after the same line. Then the script checks the resolution: no conflict marker, every block that
#    PR #60 adds and every block that `main` adds since the fork is in the file byte for byte, and the
#    line count is main's count plus PR #60's 70 lines. The CEO still reads the order by hand.
#    Any other conflicted path is named, and the check reads NOT EQUAL.
import hashlib, os, re, subprocess, sys, tempfile

repo, ref = sys.argv[1], sys.argv[2]
MAIN = sys.argv[3] if len(sys.argv) > 3 else 'origin/main'  # a third argument only for the CEO's controls
HEAD = 'af1f93b51d582bc04f7fb917e9b628f9b9091bf4'
PATHS = {'web/src/__tests__/dec1150/kill-shopping.test.tsx': '1901f11a'}
TEST = 'web/src/__tests__/components/Shopping.test.tsx'
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


def hunks(a, b, path):
    """The runs of added lines in `git diff -U0 a b -- path`, and the count of removed lines."""
    runs, cur, removed = [], [], 0
    for l in git('diff', '-U0', a, b, '--', path).splitlines():
        if l.startswith('+') and not l.startswith('+++'):
            cur.append(l[1:])
            continue
        if cur:
            runs.append(cur)
            cur = []
        if l.startswith('-') and not l.startswith('---'):
            removed += 1
    if cur:
        runs.append(cur)
    return runs, removed


def contains(lines, run):
    n = len(run)
    return any(lines[i:i + n] == run for i in range(len(lines) - n + 1))


def resolve_ok(base):
    fork = git('merge-base', HEAD, base).strip()
    ours, ours_removed = hunks(fork, HEAD, TEST)
    theirs, _ = hunks(fork, base, TEST)
    got = git('show', f'{ref}:{TEST}').splitlines()
    main_n = len(git('show', f'{base}:{TEST}').splitlines())
    marks = [l for l in got if re.match(r'^(<<<<<<<|=======|>>>>>>>)( |$)', l)]
    miss_o = sum(not contains(got, r) for r in ours)
    miss_t = sum(not contains(got, r) for r in theirs)
    want_n = main_n + sum(map(len, ours)) - ours_removed
    ok = not marks and not miss_o and not miss_t and len(got) == want_n
    print(TEST, f'resolution: markers {len(marks)}, PR #60 blocks missing {miss_o}/{len(ours)},',
          f"main's blocks missing {miss_t}/{len(theirs)}, lines {len(got)} (want {want_n}):",
          'KEPT BOTH, read the order by hand' if ok else 'BAD')
    return ok


with tempfile.TemporaryDirectory() as d:
    idx = {'GIT_INDEX_FILE': os.path.join(d, 'index')}
    git('read-tree', HEAD, env=idx)
    for path, prefix in PATHS.items():
        blob = git('hash-object', '-w', os.path.join(here, 'expected', path)).strip()
        assert blob.startswith(prefix), (path, blob)
        git('update-index', '--add', '--cacheinfo', f'100644,{blob},{path}', env=idx)
    sim_tree = git('write-tree', env=idx).strip()
ident = {'GIT_AUTHOR_NAME': 'ceo', 'GIT_AUTHOR_EMAIL': 'ceo@local', 'GIT_AUTHOR_DATE': '2026-10-15T16:00:00Z',
         'GIT_COMMITTER_NAME': 'ceo', 'GIT_COMMITTER_EMAIL': 'ceo@local', 'GIT_COMMITTER_DATE': '2026-10-15T16:00:00Z'}
sim = git('commit-tree', sim_tree, '-p', HEAD, '-m', 'SIM: af1f93b + the DEC-1150 kill file (route A)', env=ident).strip()

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
    if path not in have:
        print(path, 'MISSING at', ref)
        ok = False
        continue
    exp = code(git('cat-file', 'blob', want[path]))
    got = code(git('show', f'{ref}:{path}'))
    same = exp == got
    ok &= same
    print(path, h(exp), h(got), 'EQUAL' if same else 'DIFFERENT')
if TEST in conflicted:
    ok &= resolve_ok(base)
for p in sorted(conflicted - set(PATHS) - {TEST}):
    print(p, 'CONFLICT in the merge of SIM with main: read it by hand')
    ok = False
others = sorted((set(want) | set(have)) - set(PATHS) - conflicted)
changed = [p for p in others if want.get(p) != have.get(p)]
for p in changed:
    print(p, (want.get(p) or 'missing')[:8], (have.get(p) or 'missing')[:8], 'CHANGED')
print(f'base {base[:7]}, SIM {sim[:7]}: {len(others)} other paths', 'keep their blobs' if not changed else f'{len(changed)} CHANGED')
ok &= not changed
print('ALL EQUAL' if ok else 'NOT EQUAL')
sys.exit(0 if ok else 1)
