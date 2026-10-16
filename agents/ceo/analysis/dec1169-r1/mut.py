#!/usr/bin/env python3
"""Kit runner for DEC-1148 route A (fix round 1 of PR #59): the DEC-1125 kit runner with
the DeckSelector unit file as the default command. Env: MUT_TREE (the tree's root, clean:
commit first), MUT_LOG_DIR (the log folder).

Apply one mutant to a file in the merged head's tree, run a command, restore.

Usage: mut.py <mutants.json> [name ...]
Each mutant: {"name", "file" (relative to web/), "edits": [[old, new], ...],
"cmd" (optional, default: vitest on the DeckSelector unit file)}.
Each `old` must match exactly once.
"""
import json
import os
import re
import subprocess
import sys

TREE = os.environ['MUT_TREE']
WEB = os.path.join(TREE, 'web')
DEFAULT_CMD = 'npx vitest run src/__tests__/components/DeckSelector.test.tsx'
LOG_DIR = os.environ['MUT_LOG_DIR']
os.makedirs(LOG_DIR, exist_ok=True)
ENV = dict(os.environ, HOME=os.environ['PAPERCLIP_GITHUB_HOST_HOME'])


def git(*args):
    return subprocess.run(['git', '-C', TREE, *args], capture_output=True, text=True, env=ENV)


def run(m):
    path = os.path.join(WEB, m['file'])
    src = open(path).read()
    out = src
    for old, new in m['edits']:
        n = out.count(old)
        if n != 1:
            raise SystemExit(f"{m['name']}: edit matched {n} times: {old!r}")
        out = out.replace(old, new)
    open(path, 'w').write(out)
    try:
        p = subprocess.run(m.get('cmd', DEFAULT_CMD), shell=True, cwd=WEB, capture_output=True, text=True, env=ENV)
        log = p.stdout + p.stderr
    finally:
        git('checkout', '--', os.path.join('web', m['file']))
    status = git('status', '--porcelain').stdout
    clean = 'clean' if status.strip() == '' else 'DIRTY:\n' + status
    plain = re.sub(r'\x1b\[[0-9;]*m', '', log)
    open(os.path.join(LOG_DIR, f"log-{m['name']}.txt"), 'w').write(plain)
    count = [l.strip() for l in plain.splitlines() if re.match(r'\s*Tests\s+\d', l)] or [' | '.join(l.strip() for l in plain.splitlines() if re.match(r'\s*\d+ (passed|failed|flaky|skipped)', l))]
    fails = sorted({l.strip() for l in plain.splitlines() if re.match(r'\s*(×|FAIL|✘)\s', l)})
    print(f"== {m['name']} (exit {p.returncode}, tree {clean})")
    print('   count:', count[-1] if count else '(none)')
    for f in fails:
        print('   ', f)


def main():
    mutants = json.load(open(sys.argv[1]))
    names = sys.argv[2:]
    for m in mutants:
        if not names or m['name'] in names:
            run(m)


if __name__ == '__main__':
    main()
