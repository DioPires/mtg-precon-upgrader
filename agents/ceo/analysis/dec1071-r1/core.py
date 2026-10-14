# Route A file check for fix round 1 of PR #34 (DEC-1071, review DEC-1103).
# Usage: python3 -I core.py <repo> <ref>
# For each test file: drop blank lines and lines that hold only a // comment,
# drop all whitespace and a comma before ) ] or }, and compare with the expected
# file. Comments may differ; code may not.
# dec1071-moxfield-check.spec.ts: the reviewer's two cases must stand as written,
# and one block that starts with test( may follow them, before the last two
# lines (the close of the describe block and of the for loop). That block is the
# B1 kill case; the delta re-read reads it. The script prints its hash.
# guard.ts and test.ts: the two lines of B1 must be there (the rest of both files
# is the delta re-read's, and PR #38 may change test.ts).
import hashlib, re, subprocess, sys, os
repo, ref = sys.argv[1], sys.argv[2]
here = os.path.dirname(os.path.abspath(__file__))
def show(path):
    return subprocess.run(['git', '-C', repo, 'show', f'{ref}:{path}'], capture_output=True, text=True, check=True).stdout
def lines(text):
    return [l for l in text.splitlines() if l.strip() and not l.strip().startswith('//')]
def flat(ls):
    return re.sub(r',([)\]}])', r'\1', re.sub(r'\s+', '', '\n'.join(ls)))
def h(s):
    return hashlib.sha256(s.encode()).hexdigest()[:16]
def get(path):
    try:
        return show(path)
    except subprocess.CalledProcessError:
        return None
ok = True
for path in ['web/tests/dec181-qa.spec.ts',
             'web/tests/dec184-visual-qa.spec.ts',
             'web/tests/combo-lab.spec.ts',
             'web/src/__tests__/data/e2eGuardHosts.test.ts']:
    exp = flat(lines(open(os.path.join(here, 'expected', path)).read()))
    text = get(path)
    got = flat(lines(text)) if text is not None else 'MISSING'
    same = exp == got
    ok &= same
    print(path, h(exp), h(got), 'EQUAL' if same else 'DIFFERENT')

path = 'web/tests/dec1071-moxfield-check.spec.ts'
el = lines(open(os.path.join(here, 'expected', path)).read())
pre, suf = flat(el[:-2]), flat(el[-2:])
text = get(path)
got = flat(lines(text)) if text is not None else 'MISSING'
mid = got[len(pre):len(got) - len(suf)] if got.startswith(pre) and got.endswith(suf) and len(got) > len(pre) + len(suf) else None
same = mid is not None and mid.startswith('test(') and 'route.continue()' in mid and 'test.fail(' in mid
ok &= same
print(path, h(pre + suf), 'added block', h(mid) if mid else '-', 'EQUAL' if same else 'DIFFERENT')

for path, needle in [
    ('web/tests/support/guard.ts', '[...SCRYFALL_DOMAINS,...MOXFIELD_DOMAINS].flatMap((d)=>[d,`*.${d}`])'),
    ('web/tests/support/test.ts', "elseif(outcome===NETWORK_ANSWERED||outcome==='net::ERR_NAME_NOT_RESOLVED')moxfield.push(line);"),
]:
    text = get(path)
    found = text is not None and needle in flat(lines(text))
    ok &= found
    print(path, 'B1 line', 'PRESENT' if found else 'ABSENT')
print('ALL EQUAL' if ok else 'NOT EQUAL')
sys.exit(0 if ok else 1)
