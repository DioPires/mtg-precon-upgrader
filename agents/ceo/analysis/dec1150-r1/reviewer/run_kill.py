#!/usr/bin/env python3
"""Run the DEC-1150 kill file on the merged head and on each survivor mutant.

Usage: run_kill.py <tree> <logdir> <killfile> [ids...]
The kill file is copied into web/src/__tests__/components/ for the run and
removed at the end. Shopping.tsx is restored after each mutant.
"""
import importlib.util
import re
import shutil
import subprocess
import sys
from pathlib import Path

TREE = Path(sys.argv[1])
LOGS = Path(sys.argv[2])
KILL = Path(sys.argv[3])
IDS = sys.argv[4:]
WEB = TREE / 'web'
DEST = WEB / 'src/__tests__/components' / KILL.name
REL = 'web/src/components/organisms/Shopping.tsx'
FILE = TREE / REL

spec = importlib.util.spec_from_file_location('rm', Path(__file__).with_name('run_mutants.py'))
sys.argv = [sys.argv[0], str(TREE), str(LOGS)]
rm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rm)
MUT = {m[0]: m for m in rm.MUTANTS}


def git(*args):
    return subprocess.run(['git', '-C', str(TREE), *args], capture_output=True, text=True).stdout


def run(label):
    res = subprocess.run(['npx', 'vitest', 'run', f'src/__tests__/components/{KILL.name}'],
                         cwd=WEB, capture_output=True, text=True)
    out = res.stdout + res.stderr
    clean = re.sub(r'\x1b\[[0-9;]*m', '', out)
    count = next((l.strip() for l in clean.splitlines() if re.match(r'\s*Tests\s', l)), '?')
    failed = sorted(set(re.findall(r'(?:FAIL|×)\s+src/__tests__/\S+ > (.+?)(?:\s+\d+ms)?$', clean, re.M)))
    (LOGS / f'kill-{label}.log').write_text(f'# {label}\n# diff:\n{git("diff", "-U0", "--", REL)}\n\n{out}')
    print(f'{label}\t{count}')
    for f in failed:
        print(f'    failed: {f}')


def main():
    assert git('status', '--porcelain') == ''
    shutil.copy(KILL, DEST)
    try:
        run('head')
        for mid in IDS:
            _, desc, old, new = MUT[mid]
            src = FILE.read_text()
            assert src.count(old) == 1
            FILE.write_text(src.replace(old, new))
            try:
                run(mid)
            finally:
                git('checkout', '--', REL)
    finally:
        DEST.unlink()
    assert git('status', '--porcelain') == '', git('status', '--porcelain')
    print('tree clean after kill runs')


if __name__ == '__main__':
    main()
