# The CEO's controls for core.py (fix round 1 of PR #66, DEC-1155, review DEC-1164).
# Usage: python3 -I ctl_core.py <repo>        (run `git fetch origin` first)
# Each control is a local commit that nothing pushes; no ref moves. Expected results:
#   A  ff7ead8 itself: both files DIFFERENT, NOT EQUAL.
#   B  origin/main merged into ff7ead8 plus the expected files, with a comment added above the
#      row, the B2 case's first comment reworded and its expect wrapped with a trailing comma:
#      ALL EQUAL.
#   C  B with '3 owned cards on file' changed to '2 owned cards on file' in the row: NOT EQUAL.
#   D  B with the B2 case's stored name ' Sol Ring ' changed to 'Sol Ring': NOT EQUAL.
#   E  B with one more line in Shopping.tsx: the path CHANGED, NOT EQUAL.
#   F  a simulated main with PR #65 (f1eae45) merged first, then the round merged into it:
#      ALL EQUAL (core.py run with the simulated main as its third argument).
import os, subprocess, sys, tempfile

repo = sys.argv[1]
kit = os.path.dirname(os.path.abspath(__file__))
HEAD = 'ff7ead8e028dac0c6f7353557b657a41c925ea60'
PR65 = 'f1eae45'
LAB = 'web/src/__tests__/routes/ComboLab.test.tsx'
OWN = 'web/src/__tests__/data/ownedCards.test.ts'
SHOP = 'web/src/components/organisms/Shopping.tsx'
ident = {'GIT_AUTHOR_NAME': 'ceo', 'GIT_AUTHOR_EMAIL': 'ceo@local', 'GIT_AUTHOR_DATE': '2026-10-15T23:00:00Z',
         'GIT_COMMITTER_NAME': 'ceo', 'GIT_COMMITTER_EMAIL': 'ceo@local', 'GIT_COMMITTER_DATE': '2026-10-15T23:00:00Z'}


def git(*a, env=None, inp=None, ok=(0,)):
    r = subprocess.run(['git', '-C', repo, *a], capture_output=True, text=True, input=inp,
                       env={**os.environ, **ident, **(env or {})})
    if r.returncode not in ok:
        raise SystemExit(f"git {' '.join(a)}: {r.stderr.strip()}")
    return r.stdout.strip()


def once(s, old, new):
    assert s.count(old) == 1, old
    return s.replace(old, new)


def build(tree, files):
    with tempfile.TemporaryDirectory() as d:
        env = {'GIT_INDEX_FILE': os.path.join(d, 'index')}
        git('read-tree', tree, env=env)
        for path, text in files.items():
            blob = git('hash-object', '-w', '--stdin', inp=text)
            git('update-index', '--cacheinfo', f'100644,{blob},{path}', env=env)
        return git('write-tree', env=env)


def exp(path):
    return open(os.path.join(kit, 'expected', path)).read()


def merge(a, b, msg):
    out = git('merge-tree', '--write-tree', a, b, ok=(0, 1)).splitlines()
    assert len(out) == 1, out  # a clean merge prints the tree id alone
    return git('commit-tree', out[0], '-p', a, '-p', b, '-m', msg)


def core(ref, main=None):
    args = ['python3', '-I', os.path.join(kit, 'core.py'), repo, ref] + ([main] if main else [])
    r = subprocess.run(args, capture_output=True, text=True)
    return r.stdout + r.stderr


main = git('rev-parse', 'origin/main')
fix_tree = build(HEAD, {LAB: exp(LAB), OWN: exp(OWN)})
fix = git('commit-tree', fix_tree, '-p', HEAD, '-m', 'ctl: the round as expected')
round_b0 = merge(fix, main, 'ctl: main merged into the round')

lab_b = once(exp(LAB), "    [[['Sol Ring', 2], ['Arcane Signet', 1]], '3 owned cards on file'],\n",
             "    // Two kept entries: the count is their sum (DEC-1164 B1).\n"
             "    [[['Sol Ring', 2], ['Arcane Signet', 1]], '3 owned cards on file'],\n")
own_b = once(exp(OWN), "      expect(readOwnedEntries()).toEqual([[' Sol Ring ', 1]]);\n",
             "      expect(readOwnedEntries()).toEqual([\n        [' Sol Ring ', 1],\n      ]);\n")
own_b = once(own_b, "  it('keeps a stored name with spaces around it as stored', () => {\n",
             "  // Ruling 1: names stay as stored (DEC-1164 B2).\n"
             "  it('keeps a stored name with spaces around it as stored', () => {\n")
b = git('commit-tree', build(round_b0, {LAB: lab_b, OWN: own_b}), '-p', round_b0, '-m', 'ctl B')
c = git('commit-tree', build(round_b0, {LAB: once(lab_b, "'3 owned cards on file'],", "'2 owned cards on file'],"),
                                        OWN: own_b}), '-p', round_b0, '-m', 'ctl C')
d = git('commit-tree', build(round_b0, {LAB: lab_b, OWN: once(own_b, "JSON.stringify([[' Sol Ring ', 1]])",
                                                               "JSON.stringify([['Sol Ring', 1]])")}),
        '-p', round_b0, '-m', 'ctl D')
shop = git('show', f'{round_b0}:{SHOP}') + '\n'
e = git('commit-tree', build(round_b0, {LAB: lab_b, OWN: own_b, SHOP: shop + '// ctl E\n'}),
        '-p', round_b0, '-m', 'ctl E')
sim_main = merge(main, PR65, 'ctl: simulated main with PR #65')
f = merge(fix, sim_main, 'ctl F: the round merged with the simulated main')

for name, ref, m in (('A', HEAD, None), ('B', b, None), ('C', c, None), ('D', d, None), ('E', e, None),
                     ('F', f, sim_main)):
    print(f'== control {name} ({ref[:7]}{", main " + m[:7] if m else ""})')
    print(core(ref, m), end='')
print('round_b0', round_b0)
