# Route A file check for fix round 1 of PR #48 (DEC-1032, review DEC-1129).
# Usage: python3 -I core.py <repo> <ref>
# 1. The spec web/tests/dec1032-lab-rail-pin.spec.ts at <ref>: drop blank
#    lines and lines that hold only a // comment, drop all whitespace and a comma before
#    ) ] or }, and compare with expected/<path> (git blob 44e45d93). Comments and wrapping
#    may differ; code may not.
# 2. Every other path at <ref> keeps the blob that `git merge-tree --write-tree <base>
#    7d38c7b` gives, where <base> is `git merge-base <ref> origin/main`: the branch is the
#    head merged with main, plus the one file. Run `git fetch origin` first.
import hashlib, os, re, subprocess, sys

repo, ref = sys.argv[1], sys.argv[2]
HEAD = '7d38c7bfcba5777067f7a38089f6cccb4406498d'
PATH = 'web/tests/dec1032-lab-rail-pin.spec.ts'
here = os.path.dirname(os.path.abspath(__file__))


def git(*a):
    r = subprocess.run(['git', '-C', repo, *a], capture_output=True, text=True)
    if r.returncode != 0:
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


ok = True
exp = code(open(os.path.join(here, 'expected', PATH)).read())
got = code(git('show', f'{ref}:{PATH}'))
same = exp == got
ok &= same
print(PATH, h(exp), h(got), 'EQUAL' if same else 'DIFFERENT')

base = git('merge-base', ref, 'origin/main').strip()
want = blobs(git('merge-tree', '--write-tree', base, HEAD).strip())
have = blobs(ref)
others = sorted((set(want) | set(have)) - {PATH})
changed = [p for p in others if want.get(p) != have.get(p)]
for p in changed:
    print(p, (want.get(p) or 'missing')[:8], (have.get(p) or 'missing')[:8], 'CHANGED')
print(f'base {base[:7]}: {len(others)} other paths', 'keep their blobs' if not changed else f'{len(changed)} CHANGED')
ok &= not changed
print('ALL EQUAL' if ok else 'NOT EQUAL')
sys.exit(0 if ok else 1)
