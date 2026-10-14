# Route A file check for fix round 2 of PR #33 (DEC-1043, review DEC-1101).
# Usage: python3 -I core.py <repo> <ref>
# The new spec web/tests/dec1043-band-rules.spec.ts: drop blank lines and lines
# that hold only a // comment, drop all whitespace and a comma before ) ] or },
# and compare with the expected file (the reviewer's kill file, blob 3d1d935d).
# Comments and wrapping may differ; code may not. The pull request's other 10
# files must keep their blob ids from b89484a.
import hashlib, re, subprocess, sys, os
repo, ref = sys.argv[1], sys.argv[2]
here = os.path.dirname(os.path.abspath(__file__))
def git(*a):
    return subprocess.run(['git', '-C', repo, *a], capture_output=True, text=True)
def code(text):
    keep = [l for l in text.splitlines() if l.strip() and not l.strip().startswith('//')]
    return re.sub(r',([)\]}])', r'\1', re.sub(r'\s+', '', '\n'.join(keep)))
def h(s):
    return hashlib.sha256(s.encode()).hexdigest()[:16]
ok = True
path = 'web/tests/dec1043-band-rules.spec.ts'
exp = code(open(os.path.join(here, 'expected', path)).read())
shown = git('show', f'{ref}:{path}')
if shown.returncode != 0:
    print(path, h(exp), 'MISSING')
    ok = False
else:
    got = code(shown.stdout)
    same = exp == got
    ok &= same
    print(path, h(exp), h(got), 'EQUAL' if same else 'DIFFERENT')
blobs_ok = True
for line in open(os.path.join(here, 'head-blobs.txt')):
    blob, f = line.split()
    r = git('rev-parse', f'{ref}:{f}')
    now = r.stdout.strip()[:8] if r.returncode == 0 else 'missing'
    if now != blob:
        blobs_ok = False
        print(f, blob, now, 'CHANGED')
ok &= blobs_ok
print('10 other files keep their blobs' if blobs_ok else 'OTHER FILES CHANGED')
print('ALL EQUAL' if ok else 'NOT EQUAL')
sys.exit(0 if ok else 1)
