"""DEC-1164 reviewer mutant runner for PR #66 on the merged head.

Each mutant replaces one substring on one line of a source file, runs vitest on
that file's unit file, records the count line and the failed case names, then
restores the file with `git checkout -- <file>` and checks that
`git status --porcelain` prints nothing.
Usage: python3 -I mutate.py <web dir> <log dir> [mutant id ...]
"""
import os
import re
import subprocess
import sys
from pathlib import Path

OWNED = ('src/data/ownedCards.ts', 'src/__tests__/data/ownedCards.test.ts')
SHOP = ('src/components/organisms/Shopping.tsx', 'src/__tests__/components/Shopping.test.tsx')
ATLAS = ('src/data/cardAtlas.ts', 'src/__tests__/data/cardAtlas.test.ts')
LAB = ('src/routes/ComboLab.tsx', 'src/__tests__/routes/ComboLab.test.tsx')

MUTANTS = [
    # The hand-back's mutants (check 2).
    ('O2', OWNED, 29, 'storage: Storage = localStorage', 'storage: Storage = sessionStorage'),
    ('O10c', OWNED, 41, ' || !isOwnedQuantity(q)', ''),
    ('S3', SHOP, 130, 'isOwnedQuantity(read) ? read : 1', 'read || 1'),
    ('S7', SHOP, 150, '(out.get(key) || 0) + q', 'q'),
    ('C4', LAB, 120, 'nameKeys(n)', 'nameKeys(n).slice(0, 1)'),
    # The brief's own mutants (check 3).
    ('R1', LAB, 121, 'count += q;', 'count = q;'),
    ('R2', LAB, 121, 'count += q;', 'count = Math.max(count, q);'),
    ('R3', OWNED, 39, 'continue', 'break'),
    ('R4', OWNED, 41, 'continue', 'break'),
    ('R5', OWNED, 32, "storage.getItem(OWNED_KEY) ?? ''", 'storage.getItem(OWNED_KEY) as string'),
    ('R6', SHOP, 115, 'isOwnedQuantity(read)', 'Number.isFinite(read) && read >= 1'),
    ('R7', ATLAS, 172, 'readOwnedEntries(window.localStorage)', 'readOwnedEntries()'),
    # Extra mutants on added and rewritten lines.
    ('R8', SHOP, 130, 'isOwnedQuantity(read) ? read : 1', 'read >= 1 ? read : 1'),
    ('R9', OWNED, 42, 'out.push([n, q])', 'out.push([n.trim(), q])'),
    ('R10', OWNED, 41, '!n.trim()', '!n'),
    ('R11', OWNED, 39, 'entry.length !== 2', 'entry.length > 2'),
    ('R12', OWNED, 39, '!Array.isArray(entry) || ', ''),
    ('R13', OWNED, 36, '!Array.isArray(stored)', "typeof stored !== 'object' || stored === null"),
    ('R14', OWNED, 17, '>= 1', '> 1'),
    ('R15', OWNED, 32, "?? ''", "?? '[]'"),
    ('R16', SHOP, 148, 'readOwnedEntries()', 'readOwnedEntries(sessionStorage)'),
    ('R17', LAB, 119, 'readOwnedEntries()', 'readOwnedEntries(sessionStorage)'),
    ('R18', LAB, 1803, 'cardNoun(owned.count)', 'cardNoun(owned.keys.size)'),
    ('R19', LAB, 1811, 'cardNoun(owned.count)', 'cardNoun(owned.keys.size)'),
    ('R20', SHOP, 115, '? read : 1', '? read : 0'),
    ('R21', SHOP, 130, '? read : 1', '? read : 0'),
    ('R22', SHOP, 129, 'parseInt(m[1], 10)', 'Number(m[1])'),
    # Outside the mutant rule (the brief's "Not in scope"): a note only.
    ('N1', OWNED, 17, 'Number.isInteger(q)', 'Number.isSafeInteger(q)'),
]


def git(*args, cwd):
    env = dict(os.environ, HOME=os.environ['PAPERCLIP_GITHUB_HOST_HOME'])
    return subprocess.run(['git', *args], cwd=cwd, env=env, capture_output=True, text=True)


def main() -> None:
    web = Path(sys.argv[1])
    logs = Path(sys.argv[2])
    logs.mkdir(parents=True, exist_ok=True)
    only = sys.argv[3:]
    for mid, (src, unit), line, old, new in MUTANTS:
        if only and mid not in only:
            continue
        path = web / src
        if git('status', '--porcelain', cwd=web).stdout.strip():
            raise SystemExit(f'{mid}: tree not clean before the run')
        original = path.read_text()
        lines = original.split('\n')
        target = lines[line - 1]
        if target.count(old) != 1:
            raise SystemExit(f'{mid}: line {line} holds {target.count(old)} copies of {old!r}: {target!r}')
        lines[line - 1] = target.replace(old, new)
        log = logs / f'{mid}.log'
        try:
            path.write_text('\n'.join(lines))
            diff = git('diff', '--', src, cwd=web).stdout
            proc = subprocess.run(['npx', 'vitest', 'run', unit], cwd=web,
                                  capture_output=True, text=True, timeout=900)
            out = re.sub(r'\x1b\[[0-9;]*m', '', proc.stdout + proc.stderr)
            log.write_text(diff + '\n' + out)
        finally:
            git('checkout', '--', src, cwd=web)
        status = git('status', '--porcelain', cwd=web).stdout.strip()
        counts = [l.strip() for l in out.splitlines() if re.match(r'\s*Tests\s', l)]
        failed = sorted({l.strip() for l in out.splitlines() if re.match(r'\s*(FAIL|×)\s', l)})
        verdict = 'killed' if proc.returncode != 0 else 'survived'
        print(f'{mid}\t{src}:{line}\t{counts[-1] if counts else "NO COUNT LINE"}\t{verdict}\t'
              f'clean={not status}')
        for f in failed:
            print(f'    {f}')
        sys.stdout.flush()


if __name__ == '__main__':
    main()
