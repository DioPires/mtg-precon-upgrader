# Route A file check for fix round 1 of PR #68 (DEC-1156, review DEC-1168).
# Usage: python3 -I core.py <repo or tree> <ref>, after `git fetch origin`.
# 1. web/tests/dec1156-engine-title.spec.ts at <ref>: drop blank lines and lines that
#    hold only a // comment, drop all whitespace and a comma before ) ] or }, and compare
#    with expected/<path> (git blob 903b4583). Comments and wrapping may differ; code may not.
# 2. web/src/styles/styles.css at <ref>: drop every /* */ comment and all whitespace, and
#    compare with the same file of the merge tree below. Only comments may change (N1).
#    The line after the verdict prints whether the panel-head comment names 299px and 327px.
# 3. Every other path at <ref> keeps the blob that `git merge-tree --write-tree <base>
#    fe65b82` gives, where <base> is `git merge-base <ref> origin/main`: the branch is the
#    head merged with main, plus the two files.
import hashlib, os, re, subprocess, sys

repo, ref = sys.argv[1], sys.argv[2]
HEAD = 'fe65b829ee51e4727b78df74e825e62883e36bef'
SPEC = 'web/tests/dec1156-engine-title.spec.ts'
CSS = 'web/src/styles/styles.css'
here = os.path.dirname(os.path.abspath(__file__))


def git(*a):
    r = subprocess.run(['git', '-C', repo, *a], capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"git {' '.join(a)}: {r.stderr.strip()}")
    return r.stdout


def code(text):
    keep = [l for l in text.splitlines() if l.strip() and not l.strip().startswith('//')]
    return re.sub(r',([)\]}])', r'\1', re.sub(r'\s+', '', '\n'.join(keep)))


def css(text):
    return re.sub(r'\s+', '', re.sub(r'/\*.*?\*/', '', text, flags=re.S))


def h(s):
    return hashlib.sha256(s.encode()).hexdigest()[:16]


def blobs(treeish):
    out = {}
    for line in git('ls-tree', '-r', treeish).splitlines():
        meta, path = line.split('\t', 1)
        out[path] = meta.split()[2]
    return out


ok = True
exp = code(open(os.path.join(here, 'expected', SPEC)).read())
got = code(git('show', f'{ref}:{SPEC}'))
same = exp == got
ok &= same
print(SPEC, h(exp), h(got), 'EQUAL' if same else 'DIFFERENT')

base = git('merge-base', ref, 'origin/main').strip()
tree = git('merge-tree', '--write-tree', base, HEAD).splitlines()[0].strip()
want = blobs(tree)
have = blobs(ref)
want_css = git('cat-file', 'blob', want[CSS])
have_css = git('show', f'{ref}:{CSS}')
same_css = css(want_css) == css(have_css)
ok &= same_css
print(CSS, h(css(want_css)), h(css(have_css)), 'EQUAL (comments dropped)' if same_css else 'DIFFERENT')

others = sorted((set(want) | set(have)) - {SPEC, CSS})
changed = [p for p in others if want.get(p) != have.get(p)]
for p in changed:
    print(p, (want.get(p) or 'missing')[:8], (have.get(p) or 'missing')[:8], 'CHANGED')
print(f'base {base[:7]}, merge tree {tree[:7]}: {len(others)} other paths',
      'keep their blobs' if not changed else f'{len(changed)} CHANGED')
ok &= not changed
print('ALL EQUAL' if ok else 'NOT EQUAL')

m = re.search(r'/\*[^*]*The card count drops under a role title.*?\*/', have_css, flags=re.S)
note = m.group(0) if m else ''
print('N1 comment:', 'names 299px and 327px' if ('299px' in note and '327px' in note)
      else 'OLD OR MISSING (' + ('301px' if '301px' in note else 'no 301px') + ')')
sys.exit(0 if ok else 1)
