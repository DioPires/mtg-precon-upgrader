# Route A file check for fix round 1 of PR #25 (DEC-1073).
# Usage: python3 -I core.py <repo> <ref>
# For each test file: drop blank lines and lines that hold only a // comment,
# drop all whitespace and trailing commas, and compare with the expected file. Comments may differ;
# code may not. For the README: collapse whitespace and compare the whole text.
import hashlib, re, subprocess, sys, os
repo, ref = sys.argv[1], sys.argv[2]
here = os.path.dirname(os.path.abspath(__file__))
def show(path):
    return subprocess.run(['git', '-C', repo, 'show', f'{ref}:{path}'], capture_output=True, text=True, check=True).stdout
def code(text):
    keep = [l for l in text.splitlines() if l.strip() and not l.strip().startswith('//')]
    return re.sub(r',([)\]}])', r'\1', re.sub(r'\s+', '', '\n'.join(keep)))
def h(s):
    return hashlib.sha256(s.encode()).hexdigest()[:16]
ok = True
for path in ['web/tests/dec1073-stub-options-per-test.spec.ts',
             'web/tests/dec1073-own-route-named.spec.ts',
             'web/src/__tests__/data/e2eCardCacheSeed.test.ts']:
    exp = code(open(os.path.join(here, 'expected', path)).read())
    try:
        got = code(show(path))
    except subprocess.CalledProcessError:
        got = 'MISSING'
    same = exp == got
    ok &= same
    print(path, h(exp), h(got), 'EQUAL' if same else 'DIFFERENT')
exp = open(os.path.join(here, 'expected', 'README.flat.txt')).read()
got = re.sub(r'\s+', ' ', show('web/README.md'))
same = exp == got
ok &= same
print('web/README.md', h(exp), h(got), 'EQUAL' if same else 'DIFFERENT')
print('ALL EQUAL' if ok else 'NOT EQUAL')
sys.exit(0 if ok else 1)
