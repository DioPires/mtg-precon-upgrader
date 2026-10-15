#!/usr/bin/env python3
"""DEC-1150 review mutants on the merged head's Shopping.tsx.

Usage: run_mutants.py <tree> <logdir> [ids...]
Each mutant replaces one exact string (it must occur once), runs the unit
file, restores the file with git checkout, and checks git status each time.
"""
import re
import subprocess
import sys
from pathlib import Path

TREE = Path(sys.argv[1])
LOGS = Path(sys.argv[2])
ONLY = set(sys.argv[3:])
WEB = TREE / 'web'
REL = 'web/src/components/organisms/Shopping.tsx'
FILE = TREE / REL

CSV_READ = "const read = parseInt((r[qi] || '1').trim(), 10);"
CSV_BOUND = 'const q = read >= 1 ? read : 1;'
ARR = 'if (!Array.isArray(entry) || entry.length !== 2) return;'
NAME = "if (typeof n !== 'string' || !n.trim()) return;"
QTY = 'if (!Number.isInteger(q) || q < 1) return;'

MUTANTS = [
    ('M3', 'CSV bound becomes the old `read || 1`', CSV_BOUND, 'const q = read || 1;'),
    ('M9', 'stored-list check drops the name check (whole line)', NAME, ''),
    ('M12', 'stored-list check drops Number.isInteger', QTY, 'if (q < 1) return;'),
    ('M13', 'stored-list check drops q >= 1 (q < 1)', QTY, 'if (!Number.isInteger(q)) return;'),
    ('R1', 'CSV bound becomes Math.max(read, 1)', CSV_BOUND, 'const q = Math.max(read, 1);'),
    ('R2', 'CSV bound becomes read < 1 ? 1 : read', CSV_BOUND, 'const q = read < 1 ? 1 : read;'),
    ('R3', 'entry.length !== 2 becomes entry.length < 2', ARR,
     'if (!Array.isArray(entry) || entry.length < 2) return;'),
    ('R4', 'q < 1 becomes q <= 1', QTY, 'if (!Number.isInteger(q) || q <= 1) return;'),
    ('R5', "typeof n !== 'string' becomes typeof n === 'number'", NAME,
     "if (typeof n === 'number' || !n.trim()) return;"),
    ('R6', "CSV default cell '1' becomes '0'", CSV_READ,
     "const read = parseInt((r[qi] || '0').trim(), 10);"),
    ('R7', 'CSV read drops .trim()', CSV_READ, "const read = parseInt((r[qi] || '1'), 10);"),
    ('R8', 'CSV read drops the radix 10', CSV_READ, "const read = parseInt((r[qi] || '1').trim());"),
    ('R9', 'array check || becomes &&', ARR,
     'if (!Array.isArray(entry) && entry.length !== 2) return;'),
    ('R10', 'quantity check || becomes &&', QTY, 'if (!Number.isInteger(q) && q < 1) return;'),
    ('R11', 'name check || becomes &&', NAME, "if (typeof n !== 'string' && !n.trim()) return;"),
    ('R12', 'Number.isInteger becomes Number.isFinite', QTY,
     'if (!Number.isFinite(q) || q < 1) return;'),
    ('R13', 'q < 1 becomes q < 0', QTY, 'if (!Number.isInteger(q) || q < 0) return;'),
    ('R14', 'CSV bound >= 1 becomes >= 2', CSV_BOUND, 'const q = read >= 2 ? read : 1;'),
    ('R15', 'CSV else branch 1 becomes 0', CSV_BOUND, 'const q = read >= 1 ? read : 0;'),
    ('R16', 'entry.length !== 2 becomes entry.length > 2', ARR,
     'if (!Array.isArray(entry) || entry.length > 2) return;'),
    ('R17', 'name check !n.trim() becomes !n', NAME, "if (typeof n !== 'string' || !n) return;"),
]


def git(*args):
    return subprocess.run(['git', '-C', str(TREE), *args], capture_output=True, text=True).stdout


def main():
    assert git('status', '--porcelain') == '', 'tree not clean before start'
    rows = []
    for mid, desc, old, new in MUTANTS:
        if ONLY and mid not in ONLY:
            continue
        src = FILE.read_text()
        assert src.count(old) == 1, f'{mid}: {old!r} occurs {src.count(old)} times'
        FILE.write_text(src.replace(old, new))
        st = git('status', '--porcelain')
        assert st == f' M {REL}\n', f'{mid}: unexpected status {st!r}'
        diff = git('diff', '-U0', '--', REL)
        res = subprocess.run(
            ['npx', 'vitest', 'run', 'src/__tests__/components/Shopping.test.tsx'],
            cwd=WEB, capture_output=True, text=True)
        out = res.stdout + res.stderr
        git('checkout', '--', REL)
        after = git('status', '--porcelain')
        assert after == '', f'{mid}: tree not clean after restore: {after!r}'
        clean = re.sub(r'\x1b\[[0-9;]*m', '', out)
        count = next((l.strip() for l in clean.splitlines() if re.match(r'\s*Tests\s', l)), '?')
        failed = sorted(set(re.findall(r'(?:FAIL|×)\s+(src/__tests__/\S+ > .+?)(?:\s+\d+ms)?$', clean, re.M)))
        log = LOGS / f'mutant-{mid}.log'
        log.write_text(f'# {mid}: {desc}\n# diff:\n{diff}\n# git status after restore: {after!r}\n\n{out}')
        rows.append((mid, desc, count, failed, log))
        print(f'{mid}\t{count}\t{"killed" if "failed" in count else "SURVIVED"}\t{desc}')
        for f in failed:
            print(f'    failed: {f}')
    assert git('status', '--porcelain') == ''


if __name__ == '__main__':
    main()
