"""DEC-1139 mutant runner. Applies one mutant at a time to Shopping.tsx in the
review tree, runs the unit file (or the e2e specs), saves a log, restores the file."""
import json, os, re, subprocess, sys

TREE = '/Users/dpires/Documents/Personal/code/mtg-precon-upgrader/wt-dec1139-review'
WEB = TREE + '/web'
SRC = 'web/src/components/organisms/Shopping.tsx'
LOGS = '/Users/dpires/.paperclip/instances/default/workspaces/6ba3ac88-12e8-41a7-834f-98e3d92dae78/dec1139-logs'
ENV = dict(os.environ, HOME=os.environ['PAPERCLIP_GITHUB_HOST_HOME'])

L492 = '        text: `Added ${parsed.size} unique ${cardNoun(parsed.size)} (${fileCards} total). `'
L493 = '          + `${loadedCards} ${cardNoun(loadedCards)} loaded. `'
L665 = '              ? `${ownedCards} ${cardNoun(ownedCards)} loaded — `'

# (id, line, old fragment, new fragment, description)
MUTANTS = [
    ('M0', 53, 'cardNoun(count: number): string', 'cardNoun(count: any): string', 'signature: count typed any (type only)'),
    ('M1', 54, "count === 1 ? 'card' : 'cards'", "'cards'", 'helper always returns cards'),
    ('M1b', 54, "count === 1 ? 'card' : 'cards'", "'card'", 'helper always returns card'),
    ('M1c', 54, "count === 1 ? 'card' : 'cards'", "count !== 1 ? 'card' : 'cards'", 'helper condition negated'),
    ('M1d', 54, "count === 1 ? 'card' : 'cards'", "count <= 1 ? 'card' : 'cards'", 'count <= 1 (rule 3)'),
    ('M1e', 54, "count === 1 ? 'card' : 'cards'", "count < 2 ? 'card' : 'cards'", 'count < 2'),
    ('M1f', 54, "count === 1 ? 'card' : 'cards'", "count > 1 ? 'cards' : 'card'", 'count > 1 gives cards'),
    ('M1g', 54, "count === 1 ? 'card' : 'cards'", "Math.abs(count) === 1 ? 'card' : 'cards'", 'Math.abs(count) === 1'),
    ('M1h', 54, "count === 1 ? 'card' : 'cards'", "count == 1 ? 'card' : 'cards'", 'loose equality'),
    ('M1i', 54, "count === 1 ? 'card' : 'cards'", "count === 2 ? 'card' : 'cards'", 'count === 2'),
    ('M1j', 54, "return count === 1", "count === 1", 'return dropped (helper returns undefined)'),
    ('M1k', 54, "? 'card' : 'cards'", "? '' : 'cards'", 'singular literal emptied'),
    ('M1l', 54, "? 'card' : 'cards'", "? 'card' : ''", 'plural literal emptied'),
    ('M2', 492, 'unique ${cardNoun(parsed.size)}', 'unique ${cardNoun(fileCards)}', 'unique noun reads fileCards'),
    ('M2b', 492, 'unique ${cardNoun(parsed.size)}', 'unique ${cardNoun(loadedCards)}', 'unique noun reads loadedCards'),
    ('M2c', 492, 'unique ${cardNoun(parsed.size)}', 'unique cards', 'unique noun literal cards'),
    ('M2d', 492, 'unique ${cardNoun(parsed.size)}', 'unique card', 'unique noun literal card'),
    ('M2e', 492, 'unique ${cardNoun(parsed.size)}', 'unique ${cardNoun(merged.size)}', 'unique noun reads merged.size'),
    ('M2f', 492, 'unique ${cardNoun(parsed.size)}', 'unique ${cardNoun(owned.size)}', 'unique noun reads owned.size (list before the import)'),
    ('M2g', 492, 'Added ${parsed.size} unique', 'Added ${merged.size} unique', 'unique number reads merged.size'),
    ('M2h', 492, 'Added ${parsed.size} unique', 'Added ${fileCards} unique', 'unique number reads fileCards'),
    ('M2i', 492, '(${fileCards} total)', '(${loadedCards} total)', 'total reads loadedCards'),
    ('M2j', 492, '`Added ${parsed.size}', '`${parsed.size}', 'word Added dropped'),
    ('M2k', 492, 'total). `', 'total).`', 'separator space after total dropped'),
    ('M2l', 492, L492.strip()[len('text: '):], '``', 'line 492 template emptied'),
    ('M3', 493, '${cardNoun(loadedCards)} loaded', '${cardNoun(fileCards)} loaded', 'loaded noun reads fileCards'),
    ('M3b', 493, '${cardNoun(loadedCards)} loaded', '${cardNoun(parsed.size)} loaded', 'loaded noun reads parsed.size'),
    ('M3c', 493, '${cardNoun(loadedCards)} loaded', 'cards loaded', 'loaded noun literal cards'),
    ('M3d', 493, '${cardNoun(loadedCards)} loaded', 'card loaded', 'loaded noun literal card'),
    ('M3e', 493, '${cardNoun(loadedCards)} loaded', '${cardNoun(merged.size)} loaded', 'loaded noun reads merged.size'),
    ('M3f', 493, '${cardNoun(loadedCards)} loaded', '${cardNoun(ownedCards)} loaded', 'loaded noun reads ownedCards (render value before the import)'),
    ('M3g', 493, '`${loadedCards} ${cardNoun', '`${fileCards} ${cardNoun', 'loaded number reads fileCards'),
    ('M3h', 493, '`${loadedCards} ${cardNoun', '`${ownedCards} ${cardNoun', 'loaded number reads ownedCards'),
    ('M3i', 493, 'loaded. `', 'loaded.`', 'separator space after loaded dropped'),
    ('M3j', 493, L493.strip()[2:], '``', 'line 493 template emptied'),
    ('M5a', 531, '[...owned.values()].reduce((s, q) => s + q, 0)', 'owned.size', 'ownedCards reads owned.size'),
    ('M5b', 531, 's + q, 0)', 's + q, 1)', 'ownedCards reduce starts at 1'),
    ('M5c', 531, '(s, q) => s + q', '(s, q) => Math.max(s, q)', 'ownedCards takes the largest quantity'),
    ('M4', 665, '${ownedCards} ${cardNoun(ownedCards)} loaded — ', '${ownedCards} cards loaded — ', 'bar keeps its plural text'),
    ('M4b', 665, '${cardNoun(ownedCards)}', '${cardNoun(owned.size)}', 'bar noun reads owned.size'),
    ('M4c', 665, '`${ownedCards} ${cardNoun', '`${owned.size} ${cardNoun', 'bar number reads owned.size'),
    ('M4d', 665, '${ownedCards} ${cardNoun(ownedCards)} loaded — ', '${ownedCards} card loaded — ', 'bar literal card'),
    ('M4e', 665, 'loaded — `', 'loaded - `', 'bar dash changed'),
    ('M4f', 665, L665.strip()[2:], '``', 'line 665 template emptied'),
]


def git(*args):
    return subprocess.run(['git', *args], cwd=TREE, env=ENV, capture_output=True, text=True)


def apply(m):
    mid, line, old, new, _ = m
    path = os.path.join(TREE, SRC)
    lines = open(path).read().split('\n')
    text = lines[line - 1]
    if text.count(old) != 1:
        sys.exit(f'{mid}: fragment {old!r} occurs {text.count(old)} times on line {line}: {text!r}')
    lines[line - 1] = text.replace(old, new)
    open(path, 'w').write('\n'.join(lines))


def restore():
    git('checkout', '--', SRC)
    st = git('status', '--porcelain').stdout
    if st.strip():
        sys.exit('tree not clean after restore:\n' + st)


def strip(s):
    return re.sub(r'\x1b\[[0-9;]*m', '', s)


def run(mode, ids):
    rows = []
    for m in MUTANTS:
        if ids and m[0] not in ids:
            continue
        if git('status', '--porcelain').stdout.strip():
            sys.exit('tree not clean before ' + m[0])
        apply(m)
        diff = git('diff', '--', SRC).stdout
        if mode == 'unit':
            cmd = ['npx', 'vitest', 'run', 'src/__tests__/components/Shopping.test.tsx']
            env = ENV
        else:
            cmd = ['npx', 'playwright', 'test', 'dec1083', 'dec942', 'dec1019', 'dec181', 'dec184',
                   'smoke', 'dec1102', 'dec1110', '--workers', '3']
            env = dict(ENV, GRIMOIRE_E2E_PORT='14741',
                       PLAYWRIGHT_BROWSERS_PATH=os.environ['PAPERCLIP_GITHUB_HOST_HOME'] + '/Library/Caches/ms-playwright')
        p = subprocess.run(cmd, cwd=WEB, env=env, capture_output=True, text=True)
        out = strip(p.stdout + p.stderr)
        log = f'{LOGS}/item3-{mode}-{m[0]}.log'
        with open(log, 'w') as f:
            f.write(f'# mutant {m[0]} (line {m[1]}): {m[4]}\n# command: {" ".join(cmd)}\n# exit {p.returncode}\n')
            f.write(diff + '\n' + out)
        restore()
        if mode == 'unit':
            count = [l.strip() for l in out.splitlines() if re.match(r'\s*Tests\s', l)]
        else:
            count = [l.strip() for l in out.splitlines() if re.search(r'^\s*\d+ (passed|failed|flaky|skipped|did not run)', l)]
        verdict = 'survived' if p.returncode == 0 else 'killed'
        rows.append({'id': m[0], 'line': m[1], 'desc': m[4], 'count': ' / '.join(count), 'exit': p.returncode,
                     'verdict': verdict, 'log': log})
        print(json.dumps(rows[-1]), flush=True)
    with open(f'{LOGS}/item3-{mode}-summary.json', 'w') as f:
        json.dump(rows, f, indent=1)


if __name__ == '__main__':
    run(sys.argv[1], sys.argv[2:])
