# Controls for core.py (fix round 1 of PR #80, DEC-1195). Usage: python3 -I ctl.py <repo>
# Each control builds local commits (git commit-tree, no ref moves, nothing pushed) and runs core.py.
#   A  27e34a4 itself: the test file DIFFERENT and two edited paths CHANGED, NOT EQUAL.
#   B  the round on today's origin/main: merge, then apply.py's edits and the test file: ALL EQUAL.
#   B2 B with one comment line of the test file reworded and one call wrapped: ALL EQUAL.
#   C1 B with the head's condition (no `response.status !== 429`): the limiter CHANGED, NOT EQUAL.
#   C2 B with `until: T0 + 31_000` in the 429 case: DIFFERENT, NOT EQUAL.
#   C3 B without N5's "in its tab": the README CHANGED, NOT EQUAL.
#   D  PR #78 (ed8a1a6) merged into main first: ALL EQUAL (it shares no file with PR #80).
import os, subprocess, sys, tempfile

here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, here)
from apply import EDITS, LIMITER, README, TEST, edit_text  # noqa: E402

repo = sys.argv[1]
HEAD = '27e34a4e4574ea863453c1c43cef63bc4dfdd840'
PR78 = 'ed8a1a6'
ident = {'GIT_AUTHOR_NAME': 'ceo', 'GIT_AUTHOR_EMAIL': 'ceo@local', 'GIT_AUTHOR_DATE': '2026-10-16T20:00:00Z',
         'GIT_COMMITTER_NAME': 'ceo', 'GIT_COMMITTER_EMAIL': 'ceo@local', 'GIT_COMMITTER_DATE': '2026-10-16T20:00:00Z'}
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


def round_files(at, test_text=None):
    files = {p: edit_text(p, show(f'{at}:{p}'), log=quiet) for p in sorted({p for p, *_ in EDITS})}
    with open(os.path.join(here, 'expected', TEST), encoding='utf-8', newline='') as f:
        files[TEST] = test_text if test_text is not None else f.read()
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

with open(os.path.join(here, 'expected', TEST), encoding='utf-8') as f:
    test = f.read()
old_c = "// B4: a 400 or a 422 whose body never ends is no answer either; a 429 stops at its head."
test_b2 = test.replace(old_c, "// B4: for a 400 or a 422 an open body is no answer; a 429 is a stop at its head.", 1)
old_w = "    expect(cache.get('Open Body')?.status).toBe('loaded');\n  });\n});\n"
assert test.count(old_w) == 1
test_b2 = test_b2.replace(old_w, "    expect(\n      cache.get('Open Body')?.status,\n    ).toBe('loaded');\n  });\n});\n", 1)
assert test_b2.count('\n') == test.count('\n') + 2
run('B2', commit(m1, [m1], 'B2', round_files(m1, test_b2)), expect='ALL EQUAL')

old_u = "    await advance(0);\n    expect(storedStop()).toMatchObject({ until: T0 + 30_000, ms: 30_000 });\n"
assert test.count(old_u) == 1
test_c2 = test.replace(old_u, old_u.replace('T0 + 30_000', 'T0 + 31_000'), 1)
run('C2', commit(m1, [m1], 'C2', round_files(m1, test_c2)), expect='NOT EQUAL')

f1 = round_files(m1)
new_line = "      if (response && wholeBody && response.status !== 429) {\n"
assert f1[LIMITER].count(new_line) == 1
f1[LIMITER] = f1[LIMITER].replace(new_line, "      if (response && wholeBody) {\n")
run('C1', commit(m1, [m1], 'C1', f1), expect='NOT EQUAL')

f3 = round_files(m1)
assert f3[README].count('goes first in its tab when') == 1
f3[README] = f3[README].replace('goes first in its tab when', 'goes first when')
run('C3', commit(m1, [m1], 'C3', f3), expect='NOT EQUAL')

t78, c78 = merge(main, PR78)
assert not c78, c78
main78 = commit(t78, [main, PR78], 'SIM main: origin/main + PR #78')
td, cd = merge(main78, HEAD)
assert not cd, cd
md = commit(td, [HEAD, main78], 'round: merge main with PR #78')
d = commit(md, [md], 'round: route A edits', round_files(md))
run('D', d, main78, expect='ALL EQUAL')
