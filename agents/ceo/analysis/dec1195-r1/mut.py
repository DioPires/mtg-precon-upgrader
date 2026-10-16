import subprocess, sys, shutil, re
F = 'src/data/scryfallLimiter.ts'
L = sys.argv[1]
orig = open(F, encoding='utf-8').read()
NEW = "      if (response && wholeBody && response.status !== 429) {\n"
READ = "await Promise.race([response.clone().arrayBuffer().catch(() => undefined), timeout]);"
MUTS = {
  'C1-head-line': (NEW, "      if (response && wholeBody) {\n"),
  'R1-first-chunk': (READ, "await Promise.race([response.clone().body?.getReader().read().catch(() => undefined), timeout]);"),
  'R3-ok': (NEW, "      if (response && wholeBody && response.ok) {\n"),
  'M503': (NEW, "      if (response && wholeBody && response.status !== 503) {\n"),
}
try:
  for name, (old, new) in MUTS.items():
    assert orig.count(old) == 1, name
    open(F, 'w', encoding='utf-8').write(orig.replace(old, new))
    r = subprocess.run(['npx', 'vitest', 'run', 'src/__tests__/dec1188/body-timeout.test.ts'], capture_output=True, text=True)
    out = r.stdout + r.stderr
    open(f'{L}/mut-{name}.log', 'w').write(out)
    counts = [l.strip() for l in re.sub(r'\x1b\[[0-9;]*m', '', out).splitlines() if l.strip().startswith('Tests ')]
    fails = [l.strip() for l in re.sub(r'\x1b\[[0-9;]*m', '', out).splitlines() if l.strip().startswith('×') or l.strip().startswith('FAIL ')]
    print(name, counts, fails[:4])
finally:
  open(F, 'w', encoding='utf-8').write(orig)
