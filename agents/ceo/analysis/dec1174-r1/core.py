# Route A file check for fix round 1 of PR #75 (DEC-1172, review DEC-1174, verdict bab1dab3).
# Usage: python3 -I core.py <repo> <ref>      (run `git fetch origin` first)
# The script builds SIM: the head e5e95b4 with the edits of apply.py and the kill file of
# expected/, as a local commit that nothing pushes. It then merges SIM with
# <base> = `git merge-base <ref> origin/main` (git merge-tree, no ref moves). So the check holds
# whatever merged into `main` before the round's merge of `main`.
# 1. The kill file at <ref> against expected/: drop blank lines and lines that hold only a //
#    comment, drop all whitespace and a comma before ) ] or }. Comments and wrapping may differ;
#    code may not.
# 2. Every other path at <ref> keeps the blob of that merge, byte for byte. That covers the
#    edits of apply.py in the spec, cardCache.ts and the README.
# 3. When PR #70 (a75bcc2) merged first, the merge leaves web/README.md in conflict. If <base>'s
#    README is the README of e886907 merged with a75bcc2 (blob 0e372b5f), the check compares
#    <ref>'s README with pr70/README.resolved.md (the reviewer's resolution, item 9) after the
#    edits of apply.py. Any other conflicted path is named for a hand read.
import hashlib, os, re, subprocess, sys, tempfile

here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, here)
from apply import EDITS, KILL, README, edit_text  # noqa: E402

repo, ref = sys.argv[1], sys.argv[2]
MAIN = sys.argv[3] if len(sys.argv) > 3 else 'origin/main'  # a third argument only for the CEO's controls
HEAD = 'e5e95b4adb0ead4a737a1d2936952ffd61790d14'
KILL_BLOB = 'b4c59efc'
PR70_BASE_README = '0e372b5fb74e623e651701a7c9821eea3164ddf0'
EDITED = sorted({p for p, *_ in EDITS})


def git(*a, ok_codes=(0,), env=None, inp=None):
    r = subprocess.run(['git', '-C', repo, *a], capture_output=True, text=inp is None,
                       input=inp, env={**os.environ, **(env or {})})
    if r.returncode not in ok_codes:
        err = r.stderr if isinstance(r.stderr, str) else r.stderr.decode()
        raise SystemExit(f"git {' '.join(a)}: {err.strip()}")
    return r.stdout if isinstance(r.stdout, str) else r.stdout.decode()


def show(spec):
    return subprocess.run(['git', '-C', repo, 'show', spec], capture_output=True, check=True).stdout.decode('utf-8')


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


def put(text):
    return git('hash-object', '-w', '--stdin', inp=text.encode('utf-8')).strip()


quiet = lambda *_: None
with tempfile.TemporaryDirectory() as d:
    idx = {'GIT_INDEX_FILE': os.path.join(d, 'index')}
    git('read-tree', HEAD, env=idx)
    kill = git('hash-object', '-w', os.path.join(here, 'expected', KILL)).strip()
    assert kill.startswith(KILL_BLOB), kill
    git('update-index', '--add', '--cacheinfo', f'100644,{kill},{KILL}', env=idx)
    for path in EDITED:
        blob = put(edit_text(path, show(f'{HEAD}:{path}'), log=quiet))
        git('update-index', '--cacheinfo', f'100644,{blob},{path}', env=idx)
    sim_tree = git('write-tree', env=idx).strip()
ident = {'GIT_AUTHOR_NAME': 'ceo', 'GIT_AUTHOR_EMAIL': 'ceo@local', 'GIT_AUTHOR_DATE': '2026-10-16T10:30:00Z',
         'GIT_COMMITTER_NAME': 'ceo', 'GIT_COMMITTER_EMAIL': 'ceo@local', 'GIT_COMMITTER_DATE': '2026-10-16T10:30:00Z'}
sim = git('commit-tree', sim_tree, '-p', HEAD, '-m', 'SIM: e5e95b4 + the DEC-1174 route A edits', env=ident).strip()

base = git('merge-base', ref, MAIN).strip()
mt = git('merge-tree', '--write-tree', '--name-only', base, sim, ok_codes=(0, 1)).split('\n\n')[0].splitlines()
tree, conflicted = mt[0], set(mt[1:])
want = blobs(tree)
have = blobs(ref)

ok = True
if KILL not in have:
    print(KILL, 'MISSING at', ref)
    ok = False
else:
    exp, got = code(show(f'{tree}:{KILL}')), code(show(f'{ref}:{KILL}'))
    ok &= exp == got
    print(KILL, h(exp), h(got), 'EQUAL' if exp == got else 'DIFFERENT')

hand = set()
if README in conflicted:
    base_readme = git('rev-parse', f'{base}:{README}').strip()
    if base_readme == PR70_BASE_README:
        with open(os.path.join(here, 'pr70', 'README.resolved.md'), encoding='utf-8', newline='') as f:
            want[README] = put(edit_text(README, f.read(), log=quiet))
        print(README, 'conflict of PR #70 (base README 0e372b5f): expected = pr70/README.resolved.md + edits',
              want[README][:8])
    else:
        hand.add(README)
for p in sorted(conflicted - {README}) + sorted(hand):
    print(p, 'CONFLICT in the merge of SIM with main: read it by hand')
others = sorted((set(want) | set(have)) - {KILL} - (conflicted - {README}) - hand)
changed = [p for p in others if want.get(p) != have.get(p)]
for p in changed:
    print(p, (want.get(p) or 'missing')[:8], (have.get(p) or 'missing')[:8], 'CHANGED')
for p in EDITED:
    if p not in changed and p not in hand:
        print(p, (have.get(p) or 'missing')[:8], 'EQUAL (byte for byte)')
print(f'base {base[:7]}, SIM {sim[:7]}: {len(others)} other paths', 'keep their blobs' if not changed else f'{len(changed)} CHANGED')
ok &= not changed and not hand and not (conflicted - {README})
print('ALL EQUAL' if ok else 'NOT EQUAL')
sys.exit(0 if ok else 1)
