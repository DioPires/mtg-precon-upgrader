# Route A file check for fix round 1 of PR #29 (DEC-1074, review DEC-1095).
# Usage: python3 -I core.py <repo> <ref>
# The spec: drop blank lines and lines that hold only a // comment, drop all
# whitespace and a comma before ) ] or }, and compare with the expected file.
# Comments may differ; code may not. The other 14 files of the pull request
# must keep their blob ids from 0c10193.
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
blobs_ok = True
path = 'web/tests/dec1064-role-chart.spec.ts'
exp = code(open(os.path.join(here, 'expected', path)).read())
got = code(git('show', f'{ref}:{path}'))
same = exp == got
ok &= same
print(path, h(exp), h(got), 'EQUAL' if same else 'DIFFERENT')
for line in open(os.path.join(here, 'head-blobs.txt')):
    blob, f = line.split()
    if f == path:
        continue
    now = git('rev-parse', f'{ref}:{f}').strip()[:8]
    same = now == blob
    ok &= same
    blobs_ok &= same
    if not same:
        print(f, blob, now, 'CHANGED')
print('14 other files keep their blobs' if blobs_ok else 'OTHER FILES CHANGED')
print('ALL EQUAL' if ok else 'NOT EQUAL')
sys.exit(0 if ok else 1)
