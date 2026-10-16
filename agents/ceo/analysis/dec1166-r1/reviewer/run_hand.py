# DEC-1166 reviewer's mutant runner (scratch, outside the tree), after the
# implementer's run_mutants.py. Usage: python3 -I run_hand.py [ID ...]
# Each mutant: the file, the old text (it must occur once), the new text and
# the specs. The runner restores the file with `git checkout` after each run
# and checks `git status --porcelain` before the next.
import json, os, subprocess, sys

TREE = '/Users/dpires/Documents/Personal/code/mtg-precon-upgrader/wt-dec1166-review'
WEB = TREE + '/web'
OUT = '/Users/dpires/.paperclip/instances/default/workspaces/6ba3ac88-12e8-41a7-834f-98e3d92dae78/dec1166-review/hand'
HELPER = 'web/tests/support/test.ts'
SPEC = 'web/tests/dec1152-rate-check-post.spec.ts'
NEW_SPEC = ['tests/dec1152-rate-check-post.spec.ts']
KILLS = ['tests/dec1166-kills.spec.ts']
# The reviewer's scratch specs may sit untracked in the tree during the kill runs.
SCRATCH = {'?? web/tests/dec1166-kills.spec.ts', '?? web/tests/dec1166-forms.spec.ts'}
FOUR = ['tests/dec1152-rate-check-post.spec.ts', 'tests/dec1110-harness.spec.ts',
        'tests/dec1131-card-batches.spec.ts', 'tests/dec1102-card-data.spec.ts']

MUTANTS = {
  # Item 5: the control.
  'C600': ('LOOKUP_SPACING_MS at 600', 'web/src/data/scryfallLimiter.ts',
           ['tests/dec1131-card-batches.spec.ts', 'tests/dec1102-card-data.spec.ts'],
           'export const LOOKUP_SPACING_MS = 1_200;', 'export const LOOKUP_SPACING_MS = 600;'),
  # Item 3: the two cases that read the fixture's error.
  'T1': ('readRateCheck does not mark the test as expected to fail', SPEC, NEW_SPEC,
         '    testInfo.fail();\n', ''),
  'T2': ("the expected message names the real clock", SPEC, NEW_SPEC,
         "rateCheckFailure(sends, 4, 'page')", "rateCheckFailure(sends, 4, 'real')"),
  'T3': ('sendTwoBatches sends one batch', SPEC, NEW_SPEC,
         '\n  await page.clock.pauseAt(Date.now() + 10_000);\n  for (let i = 0; i < 2; i += 1) {',
         '\n  await page.clock.pauseAt(Date.now() + 10_000);\n  for (let i = 0; i < 1; i += 1) {'),
  # Item 6: the CEO's new mutants.
  'R1': ("the page clock: the Request's method wins over init's", HELPER, FOUR,
         "const method = init?.method ?? (input instanceof Request ? input.method : 'GET');",
         "const method = (input instanceof Request ? input.method : undefined) ?? init?.method ?? 'GET';"),
  'R2': ("a POST's second start falls one window later", HELPER, FOUR,
         "(send.method === 'POST' ? [send.time, send.time] : [send.time])",
         "(send.method === 'POST' ? [send.time, send.time + RATE_WINDOW_MS] : [send.time])"),
  'R3': ('the peak drops the first start', HELPER, FOUR,
         'peakPerWindow(startTimes(sends))', 'peakPerWindow(startTimes(sends).slice(1))'),
  'R4': ('the error lists the sends sorted by time', HELPER, FOUR,
         'sends.map((send) => `${send.method} ${send.time - first}`)',
         '[...sends].sort((a, b) => a.time - b.time).map((send) => `${send.method} ${send.time - first}`)'),
  # Item 6: the reviewer's own mutants of added or rewritten lines.
  'S1': ("the page clock: a call with no method reads POST, not GET", HELPER, FOUR,
         "(input instanceof Request ? input.method : 'GET')",
         "(input instanceof Request ? input.method : 'POST')"),
  'S2': ("the page clock's binding stamps real time, not the page's time", HELPER, FOUR,
         'stamp(context, time, method),', 'stamp(context, Date.now(), method),'),
  'S3': ('the real clock stamps every request as a POST', HELPER, FOUR,
         'stamp(context, Date.now(), request.method());', "stamp(context, Date.now(), 'POST');"),
  'S4': ('the real clock stamps every /cards/ request, also /cards/autocomplete', HELPER, FOUR,
         "if (url.hostname === 'api.scryfall.com' && BUCKET_ONE.test(url.pathname)) {\n              stamp(context, Date.now(), request.method());",
         "if (url.hostname === 'api.scryfall.com' && url.pathname.startsWith('/cards/')) {\n              stamp(context, Date.now(), request.method());"),
  'S4F': ('S4 against the whole e2e suite', HELPER, [],
         "if (url.hostname === 'api.scryfall.com' && BUCKET_ONE.test(url.pathname)) {\n              stamp(context, Date.now(), request.method());",
         "if (url.hostname === 'api.scryfall.com' && url.pathname.startsWith('/cards/')) {\n              stamp(context, Date.now(), request.method());"),
  'R1K': ("R1 against the reviewer's kill file", HELPER, KILLS,
          "const method = init?.method ?? (input instanceof Request ? input.method : 'GET');",
          "const method = (input instanceof Request ? input.method : undefined) ?? init?.method ?? 'GET';"),
  'S4K': ("S4 against the reviewer's kill file", HELPER, KILLS,
         "if (url.hostname === 'api.scryfall.com' && BUCKET_ONE.test(url.pathname)) {\n              stamp(context, Date.now(), request.method());",
         "if (url.hostname === 'api.scryfall.com' && url.pathname.startsWith('/cards/')) {\n              stamp(context, Date.now(), request.method());"),
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
           GRIMOIRE_E2E_PORT='14841')
ids = sys.argv[1:] or list(MUTANTS)
os.makedirs(f'{OUT}/logs', exist_ok=True)
summary = open(f'{OUT}/summary.txt', 'a')
for mid in ids:
    desc, rel, specs, old, new = MUTANTS[mid]
    porcelain = porcelain_of(TREE)
    assert porcelain == '', ('tree not clean before', mid, porcelain)
    path = f'{TREE}/{rel}'
    src = open(path).read()
    assert src.count(old) == 1, (mid, src.count(old))
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
