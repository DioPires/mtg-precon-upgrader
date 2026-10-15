# The CEO's controls for core.py (DEC-1149 routing). Usage: python3 -I ctl.py <repo> [<resolved dir>]
# Builds local commits only (git commit-tree; no ref moves, nothing is pushed):
#   A  the head 73f6fd5 itself: the kill files are missing, so NOT EQUAL.
#   B  the round as asked: a merge of origin/main into the head, then the three files with a reworded
#      comment and a wrapped call: ALL EQUAL.
#   C  B with one price in a kill case changed ('$2.50' to '$2.51'): DIFFERENT.
#   D  PR #61 merged first: a simulated main (origin/main + e882c60), the round's merge with the
#      resolution of N8 (files in <resolved dir>), then the files: the kill files EQUAL, and
#      Shopping.tsx and Shopping.test.tsx named as conflicts to read by hand.
import os, subprocess, sys, tempfile

repo = sys.argv[1]
resolved = sys.argv[2] if len(sys.argv) > 2 else None
here = os.path.dirname(os.path.abspath(__file__))
HEAD = '73f6fd5e28e3f6f8e5126db7d0b3ca50a37c165b'
PR61 = 'e882c60'
KILLS = 'web/src/__tests__/dec1149/dec1149-kills.test.ts'
SHOP = 'web/src/__tests__/components/dec1149/dec1149-shopping-kills.test.tsx'
TILE = 'web/src/__tests__/components/dec1149/dec1149-tile-kill.test.tsx'
ident = {'GIT_AUTHOR_NAME': 'ceo', 'GIT_AUTHOR_EMAIL': 'ceo@local', 'GIT_AUTHOR_DATE': '2026-10-15T16:00:00Z',
         'GIT_COMMITTER_NAME': 'ceo', 'GIT_COMMITTER_EMAIL': 'ceo@local', 'GIT_COMMITTER_DATE': '2026-10-15T16:00:00Z'}


def git(*a, ok_codes=(0,), env=None, inp=None):
    r = subprocess.run(['git', '-C', repo, *a], capture_output=True, text=True, input=inp,
                       env={**os.environ, **ident, **(env or {})})
    if r.returncode not in ok_codes:
        raise SystemExit(f"git {' '.join(a)}: {r.stderr.strip()}")
    return r.stdout


def blob_of(text):
    return git('hash-object', '-w', '--stdin', inp=text).strip()


def commit(tree, parents, files, msg):
    with tempfile.TemporaryDirectory() as d:
        idx = {'GIT_INDEX_FILE': os.path.join(d, 'index')}
        git('read-tree', tree, env=idx)
        for path, text in files.items():
            git('update-index', '--add', '--cacheinfo', f'100644,{blob_of(text)},{path}', env=idx)
        t = git('write-tree', env=idx).strip()
    args = ['commit-tree', t]
    for p in parents:
        args += ['-p', p]
    return git(*args, '-m', msg).strip()


def core(ref, main=None):
    cmd = ['python3', '-I', os.path.join(here, 'core.py'), repo, ref] + ([main] if main else [])
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.stdout.strip()


exp = {p: open(os.path.join(here, 'expected', p)).read() for p in (KILLS, SHOP, TILE)}
reworded = dict(exp)
old_c = '    // A reload: the price stays, and nobody asks for it again.\n'
old_w = "    expect(scryA.batches()).toEqual([['Sol Ring']]);\n"
assert exp[KILLS].count(old_c) == 1 and exp[KILLS].count(old_w) == 1
reworded[KILLS] = exp[KILLS].replace(old_c, '    // After a reload the refreshed price stays,\n    // and no request goes out.\n').replace(
    old_w, "    expect(scryA.batches()).toEqual([\n      ['Sol Ring'],\n    ]);\n")
changed = dict(reworded)
assert changed[KILLS].count("priced('2.50')") >= 1
changed[KILLS] = changed[KILLS].replace("priced('2.50')", "priced('2.51')", 1)

main = git('rev-parse', 'origin/main').strip()
print('A  73f6fd5 itself')
print(core(HEAD))
m1 = commit(git('merge-tree', '--write-tree', main, HEAD).split()[0], [HEAD, main], {}, 'CTL: merge origin/main')
b = commit(m1, [m1], reworded, 'CTL B: the kill files, reworded comment and wrapped call')
print(f'\nB  the round as asked ({b[:7]})')
print(core(b))
c = commit(m1, [m1], changed, 'CTL C: one price changed')
print(f'\nC  one price changed ({c[:7]})')
print(core(c))
if resolved:
    sm_tree = git('merge-tree', '--write-tree', main, PR61).split()[0]
    sm = commit(sm_tree, [main, PR61], {}, 'CTL: simulated main with PR #61')
    out = git('merge-tree', '--write-tree', '--name-only', sm, HEAD, ok_codes=(0, 1)).split('\n\n')[0].splitlines()
    res = {p: open(os.path.join(resolved, p)).read() for p in out[1:]}
    m2 = commit(out[0], [HEAD, sm], res, 'CTL: merge of the simulated main, N8 resolution')
    dd = commit(m2, [m2], reworded, 'CTL D: the kill files after PR #61')
    print(f'\nD  PR #61 merged first (simulated main {sm[:7]}, conflicts {out[1:]}, round {dd[:7]})')
    print(core(dd, sm))
