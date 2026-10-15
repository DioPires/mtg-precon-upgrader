# The CEO's copy of the DEC-1166 reviewer's run_hand.py for fix round 1 of PR #64 (DEC-1162).
# Usage: python3 -I ctl.py <tree> <log dir> <port> [ID ...]   (the tree holds the round's commit, no change)
# Changes from the reviewer's file: TREE, OUT and the port are arguments; the mutants run against the
# round's spec (NEW_SPEC) or the four specs, and BASE runs the four specs with no mutant.
# Each mutant: the file, the old text (it must occur once), the new text and
# the specs. The runner restores the file with `git checkout` after each run
# and checks `git status --porcelain` before the next.
import json, os, subprocess, sys

TREE = sys.argv[1]
WEB = TREE + '/web'
OUT = sys.argv[2]
HELPER = 'web/tests/support/test.ts'
SPEC = 'web/tests/dec1152-rate-check-post.spec.ts'
NEW_SPEC = ['tests/dec1152-rate-check-post.spec.ts']
KILLS = ['tests/dec1166-kills.spec.ts']
# The reviewer's scratch specs may sit untracked in the tree during the kill runs.
SCRATCH = {'?? web/tests/dec1166-kills.spec.ts', '?? web/tests/dec1166-forms.spec.ts'}
FOUR = ['tests/dec1152-rate-check-post.spec.ts', 'tests/dec1110-harness.spec.ts',
        'tests/dec1131-card-batches.spec.ts', 'tests/dec1102-card-data.spec.ts']

MUTANTS = {
  'BASE': ('no mutant: the four specs', SPEC, FOUR, '', ''),
  'S4': ('the real clock stamps every /cards/ request, also /cards/autocomplete', HELPER, NEW_SPEC,
         "if (url.hostname === 'api.scryfall.com' && BUCKET_ONE.test(url.pathname)) {\n              stamp(context, Date.now(), request.method());",
         "if (url.hostname === 'api.scryfall.com' && url.pathname.startsWith('/cards/')) {\n              stamp(context, Date.now(), request.method());"),
  'R1': ("the page clock: the Request's method wins over init's", HELPER, NEW_SPEC,
         "const method = init?.method ?? (input instanceof Request ? input.method : 'GET');",
         "const method = (input instanceof Request ? input.method : undefined) ?? init?.method ?? 'GET';"),
  'S4X': ('S4 against the four specs', HELPER, FOUR,
         "if (url.hostname === 'api.scryfall.com' && BUCKET_ONE.test(url.pathname)) {\n              stamp(context, Date.now(), request.method());",
         "if (url.hostname === 'api.scryfall.com' && url.pathname.startsWith('/cards/')) {\n              stamp(context, Date.now(), request.method());"),
  'R1X': ("R1 against the four specs", HELPER, FOUR,
         "const method = init?.method ?? (input instanceof Request ? input.method : 'GET');",
         "const method = (input instanceof Request ? input.method : undefined) ?? init?.method ?? 'GET';"),
}

def porcelain_of(tree):
    lines = subprocess.run(['git', 'status', '--porcelain'], cwd=tree, capture_output=True, text=True).stdout.splitlines()
    return ''.join(l + '\n' for l in lines if l not in SCRATCH)

def outcomes(path):
    d = json.load(open(path))
    bad = []
    def walk(suite, trail):
        for s in suite.get('suites', []):
            walk(s, trail + [s['title']])
        for spec in suite.get('specs', []):
            for t in spec['tests']:
                if t.get('status') not in ('expected', 'skipped'):
                    errs = [r.get('error', {}).get('message', '').splitlines()[:1] for r in t.get('results', [])]
                    first = next((e[0] for e in errs if e), '')
                    bad.append(f"{trail[0]}:{spec['line']} {' › '.join(trail[1:] + [spec['title']])} [{t.get('status')}]\n        {first[:300]}")
    for s in d['suites']:
        walk(s, [s['file']])
    return bad, d['stats']

def uptime():
    return subprocess.run(['uptime'], capture_output=True, text=True).stdout.strip()

env = dict(os.environ, PLAYWRIGHT_BROWSERS_PATH=os.environ['PAPERCLIP_GITHUB_HOST_HOME'] + '/Library/Caches/ms-playwright',
           GRIMOIRE_E2E_PORT=sys.argv[3])
ids = sys.argv[4:] or list(MUTANTS)
os.makedirs(f'{OUT}/logs', exist_ok=True)
summary = open(f'{OUT}/summary.txt', 'a')
for mid in ids:
    desc, rel, specs, old, new = MUTANTS[mid]
    porcelain = porcelain_of(TREE)
    assert porcelain == '', ('tree not clean before', mid, porcelain)
    path = f'{TREE}/{rel}'
    src = open(path).read()
    assert old == '' or src.count(old) == 1, (mid, src.count(old))
    open(path, 'w').write(src.replace(old, new))
    env['PLAYWRIGHT_JSON_OUTPUT_NAME'] = f'{OUT}/logs/{mid}.json'
    before = uptime()
    try:
        with open(f'{OUT}/logs/{mid}.log', 'w') as log:
            subprocess.run(['npx', 'playwright', 'test', *specs, '--workers', '3', '--reporter=list,json'],
                           cwd=WEB, env=env, stdout=log, stderr=subprocess.STDOUT)
    finally:
        subprocess.run(['git', 'checkout', '--', rel], cwd=TREE, check=True)
    after = uptime()
    porcelain = porcelain_of(TREE)
    bad, stats = outcomes(f'{OUT}/logs/{mid}.json')
    line = (f"{mid} ({desc}): expected {stats['expected']}, unexpected {stats['unexpected']}, flaky {stats['flaky']}; "
            f"porcelain {'empty' if not porcelain else repr(porcelain)}\n    load before: {before}\n    load after:  {after}\n"
            + ''.join(f'    {b}\n' for b in bad))
    print(line, end='', flush=True)
    summary.write(line); summary.flush()
