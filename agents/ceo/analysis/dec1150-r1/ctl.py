# The CEO's mutant runs for fix round 1 of PR #60 (DEC-1141, review DEC-1150).
# Usage: python3 -I ctl.py <tree> <log dir> [ID ...]   (no ID runs all 21 of the reviewer's mutants)
# <tree> is a tree of PR #60's branch (or a scratch merge of it) with the kill file
# web/src/__tests__/dec1150/kill-shopping.test.tsx committed. The tree must be clean.
# The script runs the head first, then each mutant of the reviewer's list (reviewer/run_mutants.py,
# unchanged) on Shopping.tsx. Each run is one vitest call on the kill file and on Shopping.test.tsx.
# git checkout restores Shopping.tsx after each mutant, and the tree must be clean again.
import os, re, subprocess, sys
from pathlib import Path

TREE, LOGS = Path(sys.argv[1]), Path(sys.argv[2])
WANT = sys.argv[3:]
here = os.path.dirname(os.path.abspath(__file__))
argv, sys.argv = sys.argv, [sys.argv[0], str(TREE), str(LOGS)]
sys.path.insert(0, os.path.join(here, 'reviewer'))
import run_mutants as rm  # noqa: E402  (reads sys.argv at import)
sys.argv = argv

REL = 'web/src/components/organisms/Shopping.tsx'
FILE = TREE / REL
KILL = 'src/__tests__/dec1150/kill-shopping.test.tsx'
UNIT = 'src/__tests__/components/Shopping.test.tsx'
LOGS.mkdir(parents=True, exist_ok=True)


def git(*a):
    return subprocess.run(['git', '-C', str(TREE), *a], capture_output=True, text=True).stdout


def run(label, diff=''):
    res = subprocess.run(['npx', 'vitest', 'run', KILL, UNIT], cwd=TREE / 'web', capture_output=True, text=True)
    out = res.stdout + res.stderr
    clean = re.sub(r'\x1b\[[0-9;]*m', '', out)
    count = next((l.strip() for l in clean.splitlines() if re.match(r'\s*Tests\s', l)), '?')
    failed = sorted(set(re.findall(r'(?:FAIL|×)\s+(src/__tests__/\S+ > .+?)(?:\s+\d+ms)?$', clean, re.M)))
    (LOGS / f'{label}.log').write_text(f'# {label}\n# diff:\n{diff}\n\n{out}')
    return count, failed


assert (TREE / 'web' / KILL).exists(), 'kill file missing'
assert git('status', '--porcelain') == '', 'tree not clean before start'
count, failed = run('head')
print(f'head  {count}')
for f in failed:
    print('    failed:', f)
for mid, desc, old, new in rm.MUTANTS:
    if WANT and mid not in WANT:
        continue
    src = FILE.read_text()
    assert src.count(old) == 1, (mid, src.count(old))
    FILE.write_text(src.replace(old, new))
    assert git('status', '--porcelain') == f' M {REL}\n', mid
    try:
        count, failed = run(mid, git('diff', '-U0', '--', REL))
    finally:
        git('checkout', '--', REL)
    assert git('status', '--porcelain') == '', f'{mid}: tree not clean after restore'
    print(f'{mid:4} {"killed" if "failed" in count else "SURVIVED":8} {count:40} {desc}')
    for f in failed:
        print('    failed:', f)
print('tree clean after all runs')
