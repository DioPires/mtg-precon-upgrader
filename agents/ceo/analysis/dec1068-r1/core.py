# Route A file check for fix round 1 of PR #31 (DEC-1068, review DEC-1097).
# Usage: python3 -I core.py <repo> <ref>
# The spec: drop blank lines and lines that hold only a // comment, drop all
# whitespace and a comma before ) ] or }, and compare with the expected file.
# Comments may differ; code may not. The other two files of the pull request
# must keep their blob ids from ab90e26.
import hashlib, re, subprocess, sys, os
repo, ref = sys.argv[1], sys.argv[2]
here = os.path.dirname(os.path.abspath(__file__))
def git(*a):
    return subprocess.run(['git', '-C', repo, *a], capture_output=True, text=True, check=True).stdout
def code(text):
    keep = [l for l in text.splitlines() if l.strip() and not l.strip().startswith('//')]
    return re.sub(r',([)\]}])', r'\1', re.sub(r'\s+', '', '\n'.join(keep)))
def h(s):
    return hashlib.sha256(s.encode()).hexdigest()[:16]
ok = True
path = 'web/src/__tests__/components/Apothecary.test.tsx'
exp = code(open(os.path.join(here, 'expected', path)).read())
got = code(git('show', f'{ref}:{path}'))
same = exp == got
ok &= same
print(path, h(exp), h(got), 'EQUAL' if same else 'DIFFERENT')
for blob, f in [('b8dccc24', 'web/src/components/organisms/Apothecary.tsx'),
                ('033b0f77', 'web/tests/dec1068-apothecary-filter-status.spec.ts')]:
    now = git('rev-parse', f'{ref}:{f}').strip()[:8]
    same = now == blob
    ok &= same
    print(f, blob, now, 'KEPT' if same else 'CHANGED')
print('ALL EQUAL' if ok else 'NOT EQUAL')
sys.exit(0 if ok else 1)
