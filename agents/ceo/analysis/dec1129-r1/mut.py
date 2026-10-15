#!/usr/bin/env python3
"""DEC-1129 route A control mutants on combo-lab.css.

Usage: python3 -I mut.py <tree root> <log folder> <port> [name ...]
Applies one mutant to web/src/styles/combo-lab.css, runs
tests/dec1032-lab-rail-pin.spec.ts in Chromium, restores the file and checks
that its blob id reads bf20f2a3 again. The tree must hold the file at that id.
"""
import os, re, subprocess, sys

FILE = 'web/src/styles/combo-lab.css'
BLOB = 'bf20f2a35958cdb06b631ff09d88f8d824e0d53e'
OLD = '  @media (min-height:700px){\n'
MUTANTS = {
    'M2': '  @media (min-height:650px){\n',
    'M3': '  @media (min-height:760px){\n',
    'M4': '  @media (min-height:695px){\n',
    'M14': '  @media (min-width:700px){\n',
}
tree, logs, port = sys.argv[1], sys.argv[2], sys.argv[3]
names = sys.argv[4:] or list(MUTANTS)
env = dict(os.environ, GRIMOIRE_E2E_PORT=port,
           PLAYWRIGHT_BROWSERS_PATH=os.path.join(os.environ['PAPERCLIP_GITHUB_HOST_HOME'], 'Library/Caches/ms-playwright'))
path = os.path.join(tree, FILE)


def blob():
    return subprocess.run(['git', '-C', tree, 'hash-object', FILE], capture_output=True, text=True).stdout.strip()


assert blob() == BLOB, f'{FILE} does not read {BLOB[:8]} before the run'
src = open(path).read()
assert src.count(OLD) == 1
for name in names:
    open(path, 'w').write(src.replace(OLD, MUTANTS[name]))
    try:
        p = subprocess.run(['npx', 'playwright', 'test', 'tests/dec1032-lab-rail-pin.spec.ts', '--project', 'chromium', '--reporter', 'line'],
                           cwd=os.path.join(tree, 'web'), capture_output=True, text=True, env=env)
    finally:
        open(path, 'w').write(src)
    out = re.sub(r'\x1b\[[0-9;]*[A-Za-z]', '', p.stdout + p.stderr)
    open(os.path.join(logs, f'{name}.log'), 'w').write(f'{name}: {OLD.strip()} -> {MUTANTS[name].strip()}\n\n{out}')
    counts = [l.strip() for l in out.splitlines() if re.match(r'\s*\d+ (passed|failed|flaky)', l)]
    fails = [l.strip() for l in out.splitlines() if re.match(r'\s*\d+\) \[chromium\]', l)]
    restored = 'restored' if blob() == BLOB else 'NOT RESTORED'
    print(f"{name}: {'KILLED' if p.returncode else 'SURVIVED'} | {' | '.join(counts)} | {restored}")
    for f in sorted(set(fails)):
        print('   ', f)
