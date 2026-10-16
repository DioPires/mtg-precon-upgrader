# Controls for core.py (fix round 1 of PR #75, DEC-1174). Usage: python3 -I ctl.py <repo>
# Each control builds local commits (git commit-tree, no ref moves, nothing pushed) and runs core.py.
#   A  e5e95b4 itself: the kill file MISSING and three edited paths CHANGED, NOT EQUAL.
#   B  the round on today's origin/main: merge, then apply.py's edits and the kill file: ALL EQUAL.
#   B2 B with the kill file's header comment reworded and one call wrapped: ALL EQUAL.
#   C1 B with `LOOKUP_SPACING_MS + 30` in the kill file: DIFFERENT, NOT EQUAL.
#   C2 B with `waitForTimeout(300)` for N1's `waitForTimeout(3_000)`: the spec CHANGED, NOT EQUAL.
#   C3 B with N3's sentence left out of cardCache.ts: CHANGED, NOT EQUAL.
#   D  PR #70 (a75bcc2) merged into main first: the README conflict resolved with
#      pr70/README.resolved.md, then the edits: ALL EQUAL (the README read from the kit).
import os, subprocess, sys, tempfile

here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, here)
from apply import EDITS, KILL, README, edit_text  # noqa: E402

repo = sys.argv[1]
HEAD = 'e5e95b4adb0ead4a737a1d2936952ffd61790d14'
PR70 = 'a75bcc2'
ident = {'GIT_AUTHOR_NAME': 'ceo', 'GIT_AUTHOR_EMAIL': 'ceo@local', 'GIT_AUTHOR_DATE': '2026-10-16T10:30:00Z',
         'GIT_COMMITTER_NAME': 'ceo', 'GIT_COMMITTER_EMAIL': 'ceo@local', 'GIT_COMMITTER_DATE': '2026-10-16T10:30:00Z'}
quiet = lambda *_: None


def git(*a, ok_codes=(0,), env=None, inp=None):
    r = subprocess.run(['git', '-C', repo, *a], capture_output=True, input=inp,
                       env={**os.environ, **(env or {})})
    if r.returncode not in ok_codes:
        raise SystemExit(f"git {' '.join(a)}: {r.stderr.decode().strip()}")
    return r.stdout.decode('utf-8')


def show(spec):
    return git('show', spec)


def put(text):
    return git('hash-object', '-w', '--stdin', inp=text.encode('utf-8')).strip()


def commit(tree, parents, msg, files=None):
    """A commit of `tree` with `files` ({path: text}) written over it."""
    if files:
        with tempfile.TemporaryDirectory() as d:
            idx = {'GIT_INDEX_FILE': os.path.join(d, 'index')}
            git('read-tree', tree, env=idx)
            for path, text in files.items():
                git('update-index', '--add', '--cacheinfo', f'100644,{put(text)},{path}', env=idx)
            tree = git('write-tree', env=idx).strip()
    args = ['commit-tree', tree, '-m', msg]
    for p in parents:
        args += ['-p', p]
    return git(*args, env={**ident}).strip()


def merge(a, b):
    out = git('merge-tree', '--write-tree', '--name-only', a, b, ok_codes=(0, 1)).split('\n\n')[0].splitlines()
    return out[0], set(out[1:])


def round_files(at, kill_text=None):
    files = {p: edit_text(p, show(f'{at}:{p}'), log=quiet) for p in sorted({p for p, *_ in EDITS})}
    with open(os.path.join(here, 'expected', KILL), encoding='utf-8', newline='') as f:
        files[KILL] = kill_text if kill_text is not None else f.read()
    return files


def run(name, ref, main='origin/main', expect=None):
    r = subprocess.run([sys.executable, '-I', os.path.join(here, 'core.py'), repo, ref, main],
                       capture_output=True, text=True)
    last = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr.strip()
    verdict = 'as expected' if last == expect else f'UNEXPECTED (wanted {expect})'
    print(f'=== {name}: ref {ref[:7]} main {main[:7]}: {last} ({verdict})')
    print('    ' + r.stdout.strip().replace('\n', '\n    '))
    if r.stderr.strip():
        print('    stderr: ' + r.stderr.strip())


main = git('rev-parse', 'origin/main').strip()
run('A', HEAD, expect='NOT EQUAL')

t, c = merge(main, HEAD)
assert not c, c
m1 = commit(t, [HEAD, main], 'round: merge origin/main')
b = commit(m1, [m1], 'round: route A edits', round_files(m1))
run('B', b, expect='ALL EQUAL')

with open(os.path.join(here, 'expected', KILL), encoding='utf-8') as f:
    kill = f.read()
kill_b2 = kill.replace('// DEC-1174 reviewer kill case for M10', '// DEC-1172 fix round 1, the kill case for M10', 1)
kill_b2 = kill_b2.replace("    expect(cardCache.pricePending('Sol Ring')).toBe(false);",
                          "    expect(\n      cardCache.pricePending('Sol Ring'),\n    ).toBe(false);", 1)
assert kill_b2 != kill
run('B2', commit(m1, [m1], 'B2', round_files(m1, kill_b2)), expect='ALL EQUAL')

kill_c1 = kill.replace('LOOKUP_SPACING_MS + 300', 'LOOKUP_SPACING_MS + 30', 1)
assert kill_c1 != kill
run('C1', commit(m1, [m1], 'C1', round_files(m1, kill_c1)), expect='NOT EQUAL')

f2 = round_files(m1)
spec = 'web/tests/dec1102-card-data.spec.ts'
assert f2[spec].count('waitForTimeout(3_000);\n    expect((await cardKeys())') == 1
f2[spec] = f2[spec].replace('waitForTimeout(3_000);\n    expect((await cardKeys())', 'waitForTimeout(300);\n    expect((await cardKeys())')
run('C2', commit(m1, [m1], 'C2', f2), expect='NOT EQUAL')

f3 = round_files(m1)
cache = 'web/src/data/cardCache.ts'
assert f3[cache].count(', and asks for none itself.') == 1
f3[cache] = f3[cache].replace(', and asks for none itself.', '.')
run('C3', commit(m1, [m1], 'C3', f3), expect='NOT EQUAL')

t70, c70 = merge(main, PR70)
assert not c70, c70
main70 = commit(t70, [main, PR70], 'SIM main: origin/main + PR #70')
td, cd = merge(main70, HEAD)
assert cd == {README}, cd
with open(os.path.join(here, 'pr70', 'README.resolved.md'), encoding='utf-8', newline='') as f:
    resolved = f.read()
md = commit(td, [HEAD, main70], 'round: merge main with PR #70, README resolved', {README: resolved})
d = commit(md, [md], 'round: route A edits', round_files(md))
run('D', d, main70, expect='ALL EQUAL')
