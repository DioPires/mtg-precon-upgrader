# DEC-1163 reviewer mutant runner: apply one or more exact replacements, run the named suites, restore from git.
import json, os, re, subprocess, sys
WEB = '/Users/dpires/Documents/Personal/code/mtg-precon-upgrader/wt-dec1163-review/web'
OUT = '/tmp/dec1163/mutants'
H = os.environ['PAPERCLIP_GITHUB_HOST_HOME']
ENV = dict(os.environ, HOME=H, PLAYWRIGHT_BROWSERS_PATH=H + '/Library/Caches/ms-playwright', GRIMOIRE_E2E_PORT='14866')
sys.path.insert(0, OUT)
from mutants import MUTANTS  # id -> (list of (path, old, new), list of suites)

def counts(out):
    s = re.sub(r'\x1b\[[0-9;]*m', '', out)
    lines = [l.strip() for l in s.splitlines() if re.search(r'^\s*(Test Files|Tests|\d+ (passed|failed|flaky|skipped|did not run))', l)]
    return ' | '.join(lines[-5:])

def failed_names(out):
    s = re.sub(r'\x1b\[[0-9;]*m', '', out)
    names = re.findall(r'^\s*(?:×|✗|FAIL)\s+(.*)$', s, re.M)
    pw = re.findall(r'^\s+\[chromium\] › (.*)$', s, re.M)
    return names[:30] + pw[:30]

ids = sys.argv[1:]
for mid in ids:
    edits, suites = MUTANTS[mid]
    paths = sorted({p for p, _, _ in edits})
    result = {'id': mid, 'files': paths, 'runs': []}
    try:
        for path, old, new in edits:
            full = os.path.join(WEB, path)
            src = open(full).read()
            assert src.count(old) == 1, f'{mid}: anchor found {src.count(old)} times in {path}'
            open(full, 'w').write(src.replace(old, new))
        for i, cmd in enumerate(suites):
            suite = 'unit' if 'vitest' in cmd else 'e2e'
            p = subprocess.run(cmd, cwd=WEB, env=ENV, capture_output=True, text=True)
            out = p.stdout + p.stderr
            log = f'{OUT}/{mid}-{suite}{i}.log'
            open(log, 'w').write(out)
            result['runs'].append({'suite': suite, 'exit': p.returncode, 'counts': counts(out), 'failed': failed_names(out), 'log': log})
    finally:
        if paths: subprocess.run(['git', 'checkout', '--'] + paths, cwd=WEB, env=ENV, check=True)
    st = subprocess.run(['git', 'status', '--porcelain'], cwd=WEB, env=ENV, capture_output=True, text=True).stdout
    result['clean_after'] = st.strip() == ''
    print(json.dumps(result, ensure_ascii=False), flush=True)
