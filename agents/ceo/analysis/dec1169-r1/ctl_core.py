# The CEO's controls for core.py (fix round 1 of PR #69, DEC-1146, review DEC-1169).
# Usage: python3 -I ctl_core.py <repo>        (run `git fetch origin` first)
# Each control is a local commit that nothing pushes; no ref moves. Expected results:
#   A  64f2146 itself: the file DIFFERENT, NOT EQUAL.
#   B  origin/main merged into 64f2146 plus the expected file, with the case's comment reworded,
#      the harness comment cut to one line, and the case's `it(` call wrapped over lines with a
#      trailing comma: ALL EQUAL. (JSX in parentheses is other code text: keep the field's line.)
#   C  B with the field's label 'Search' changed to 'Find' in the harness and the case: NOT EQUAL.
#   D  B with the case's name changed by one word: NOT EQUAL.
#   E  B with one more line in DeckSelector.tsx: the path CHANGED, NOT EQUAL.
#   F  a simulated main with PR #68 (fe65b82) merged first, then the round merged into it:
#      ALL EQUAL (core.py run with the simulated main as its third argument).
import os, subprocess, sys, tempfile

repo = sys.argv[1]
kit = os.path.dirname(os.path.abspath(__file__))
HEAD = '64f2146c456062a16b1b622e9599dc0d3afe6011'
PR68 = 'fe65b82'
TEST = 'web/src/__tests__/components/DeckSelector.test.tsx'
SEL = 'web/src/components/organisms/DeckSelector.tsx'
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


def merge(a, b, msg):
    out = git('merge-tree', '--write-tree', a, b, ok=(0, 1)).splitlines()
    assert len(out) == 1, out  # a clean merge prints the tree id alone
    return git('commit-tree', out[0], '-p', a, '-p', b, '-m', msg)


def core(ref, main=None):
    args = ['python3', '-I', os.path.join(kit, 'core.py'), repo, ref] + ([main] if main else [])
    r = subprocess.run(args, capture_output=True, text=True)
    return r.stdout + r.stderr


exp = open(os.path.join(kit, 'expected', TEST)).read()
main = git('rev-parse', 'origin/main')
fix = git('commit-tree', build(HEAD, {TEST: exp}), '-p', HEAD, '-m', 'ctl: the round as expected')
round_b0 = merge(fix, main, 'ctl: main merged into the round')

t_b = once(exp,
           "  // DEC-1169 B1 (mutant R1): case (a) needs focus on `body`. Here the new deck\n"
           "  // focuses its own field in the same update, and that focus stays.\n",
           "  // Mutant R1 of the DEC-1169 review: the new deck's field took focus, so keep it.\n")
t_b = once(t_b,
           "// The guide around the selector: a chip that each deck mounts anew, and a\n"
           "// field that deck 5 brings and that takes focus as it mounts (`autoFocus`).\n"
           "// The deck change removes the focused chip and focuses the field in one\n"
           "// commit, so focus does not fall to `body`.\n",
           "// Guide, plus a field that deck 5 mounts with `autoFocus`.\n")
t_b = once(t_b,
           "  it('moves no focus when the focused element left the page and another element took focus in the same update', () => {\n",
           "  it(\n"
           "    'moves no focus when the focused element left the page and another element took focus in the same update',\n"
           "    () => {\n")
t_b = once(t_b,
           "    expect(document.activeElement).toBe(getByRole('textbox', { name: 'Search' }));\n  });\n});\n",
           "    expect(document.activeElement).toBe(getByRole('textbox', { name: 'Search' }));\n  },\n  );\n});\n")
b = git('commit-tree', build(round_b0, {TEST: t_b}), '-p', round_b0, '-m', 'ctl B')
t_c = once(t_b, 'aria-label="Search"', 'aria-label="Find"')
t_c = once(t_c, "{ name: 'Search' }", "{ name: 'Find' }")
c = git('commit-tree', build(round_b0, {TEST: t_c}), '-p', round_b0, '-m', 'ctl C')
t_d = once(t_b, "another element took focus in the same update',", "another element took focus in one update',")
d = git('commit-tree', build(round_b0, {TEST: t_d}), '-p', round_b0, '-m', 'ctl D')
sel = git('show', f'{round_b0}:{SEL}') + '\n'
e = git('commit-tree', build(round_b0, {TEST: t_b, SEL: sel + '// ctl E\n'}), '-p', round_b0, '-m', 'ctl E')
sim_main = merge(main, PR68, 'ctl: simulated main with PR #68')
f = merge(fix, sim_main, 'ctl F: the round merged with the simulated main')

for name, ref, m in (('A', HEAD, None), ('B', b, None), ('C', c, None), ('D', d, None), ('E', e, None),
                     ('F', f, sim_main)):
    print(f'== control {name} ({ref[:7]}{", main " + m[:7] if m else ""})')
    print(core(ref, m), end='')
print('round_b0', round_b0)
