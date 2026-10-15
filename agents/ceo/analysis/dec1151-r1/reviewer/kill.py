"""DEC-1151 kill runs: each kill file passes on the head and fails on its mutants.

The runner copies the kill files into the tree, runs each one on the head, then
on each of its mutants (from mutants.py), restores the source with
`git checkout`, runs `npm run typecheck` once with every kill file in the tree,
and deletes the kill files. Afterwards `git status --porcelain` must print nothing.
"""

import json
import re
import shutil
import subprocess
from pathlib import Path

import mutants as mu

SCRATCH = Path(__file__).resolve().parent
LOGS = mu.LOGS.parent / 'kills'

KILLS = [
    ('dec1151-kill-shopping.test.tsx', 'src/__tests__/components',
     ['S3', 'S4', 'S5', 'S6', 'S13', 'S14', 'S15', 'S16']),
    ('dec1151-kill-cardNoun.test.ts', 'src/__tests__/lib', ['H20', 'H21', 'H17']),
    ('dec1151-kill-engine.test.tsx', 'src/__tests__/components', ['E2', 'E5']),
]

BY_ID = {m[0]: m for m in mu.M}


def vitest(test):
    p = mu.sh(['npx', 'vitest', 'run', test], mu.WEB)
    out = mu.ANSI.sub('', p.stdout + p.stderr)
    m = re.search(r'^\s*Tests\s+(.+)$', out, re.M)
    return p.returncode, (m.group(1).strip() if m else '(no Tests line)'), out


def main():
    LOGS.mkdir(parents=True, exist_ok=True)
    placed = []
    res = []
    try:
        for name, folder, _ in KILLS:
            dst = mu.WEB / folder / name
            shutil.copy(SCRATCH / name, dst)
            placed.append(dst)
        for name, folder, ids in KILLS:
            test = f'{folder}/{name}'
            code, count, out = vitest(test)
            log = LOGS / f'{name}.head.log'
            log.write_text(f'# {test} on the head e882c60\n# exit {code}\n\n{out}')
            res.append({'kill': name, 'mutant': 'head', 'exit': code, 'count': count, 'log': str(log)})
            for mid in ids:
                _, path, old, new, _, note = BY_ID[mid]
                f = mu.TREE / path
                src = f.read_text()
                assert src.count(old) == 1, mid
                f.write_text(src.replace(old, new))
                try:
                    code, count, out = vitest(test)
                finally:
                    mu.sh(['git', 'checkout', '--', path], mu.TREE)
                log = LOGS / f'{name}.{mid}.log'
                log.write_text(f'# {test} on mutant {mid} ({note})\n# new: {new!r}\n# exit {code}\n\n{out}')
                res.append({'kill': name, 'mutant': mid, 'exit': code, 'count': count, 'log': str(log)})
        p = mu.sh(['npm', 'run', 'typecheck'], mu.WEB)
        log = LOGS / 'typecheck-with-kill-files.log'
        log.write_text(f'# npm run typecheck with the kill files in the tree\n# exit {p.returncode}\n\n'
                       + mu.ANSI.sub('', p.stdout + p.stderr))
        res.append({'kill': 'all', 'mutant': 'typecheck', 'exit': p.returncode, 'count': '', 'log': str(log)})
    finally:
        for dst in placed:
            dst.unlink()
    (LOGS / 'results.json').write_text(json.dumps(res, indent=2))
    for r in res:
        print(f"{r['kill']:34} {r['mutant']:9} exit={r['exit']} {r['count']}")
    print('status:', repr(mu.sh(['git', 'status', '--porcelain'], mu.TREE).stdout))


if __name__ == '__main__':
    main()
