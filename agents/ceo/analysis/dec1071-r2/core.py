# Route A file check for fix round 2 of PR #34 (DEC-1071, review DEC-1103, B8).
# Usage: python3 -I core.py <repo> <ref>
# For each test file: drop blank lines and lines that hold only a // comment,
# drop all whitespace and a comma before ) ] or }, and compare with the expected
# file. Comments may differ; code may not.
# dec1071-moxfield-check.spec.ts: the whole file must equal the reviewer's run
# file of round 2 (blob 7dd4e117: its two cases, the B1 case and the B8 case).
# The script also prints whether the blob is that file byte for byte.
# guard.ts and test.ts: the two lines of B1 must be there (PR #38 may change the
# rest of test.ts).
# web/README.md: with whitespace collapsed, it holds the N1 sentence of round 2
# and no longer holds the old one.
import hashlib, re, subprocess, sys, os
repo, ref = sys.argv[1], sys.argv[2]
here = os.path.dirname(os.path.abspath(__file__))
def show(path):
    return subprocess.run(['git', '-C', repo, 'show', f'{ref}:{path}'], capture_output=True, text=True, check=True).stdout
def blob(path):
    r = subprocess.run(['git', '-C', repo, 'rev-parse', f'{ref}:{path}'], capture_output=True, text=True)
    return r.stdout.strip()[:8] if r.returncode == 0 else '-'
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
             'web/src/__tests__/data/e2eGuardHosts.test.ts',
             'web/tests/dec1071-moxfield-check.spec.ts']:
    exp = flat(lines(open(os.path.join(here, 'expected', path)).read()))
    text = get(path)
    got = flat(lines(text)) if text is not None else 'MISSING'
    same = exp == got
    ok &= same
    print(path, h(exp), h(got), 'EQUAL' if same else 'DIFFERENT')
print('web/tests/dec1071-moxfield-check.spec.ts blob', blob('web/tests/dec1071-moxfield-check.spec.ts'),
      '(the reviewer\'s run file is 7dd4e117)')

for path, needle in [
    ('web/tests/support/guard.ts', '[...SCRYFALL_DOMAINS,...MOXFIELD_DOMAINS].flatMap((d)=>[d,`*.${d}`])'),
    ('web/tests/support/test.ts', "elseif(outcome===NETWORK_ANSWERED||outcome==='net::ERR_NAME_NOT_RESOLVED')moxfield.push(line);"),
]:
    text = get(path)
    found = text is not None and needle in flat(lines(text))
    ok &= found
    print(path, 'B1 line', 'PRESENT' if found else 'ABSENT')

readme = get('web/README.md') or ''
prose = re.sub(r'\s+', ' ', readme)
new = 'Do not give them a Scryfall or a Moxfield URL.' in prose
old = 'Do not give them a Scryfall URL.' in prose
ok &= new and not old
print('web/README.md N1 sentence', 'PRESENT' if new else 'ABSENT', '| old sentence', 'GONE' if not old else 'STILL THERE')
print('ALL EQUAL' if ok else 'NOT EQUAL')
sys.exit(0 if ok else 1)
