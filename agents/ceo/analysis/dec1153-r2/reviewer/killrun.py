"""DEC-1170: run the kill cases K1 and K2 on the head and on each surviving mutant. Run from wt-dec1170-mut/web."""
import subprocess, sys
src = open('/tmp/dec1170-review/mutants.py').read()
ns = {}
exec(src[: src.index('\ndef run(')], ns)
MUT = {m[0]: m for m in ns['MUTANTS']}
SPEC = 'src/__tests__/dec1170/dec1170-loader-scratch.test.ts'
def vitest(log):
    p = subprocess.run(['npx', 'vitest', 'run', SPEC, '-t', 'K1|K2'], capture_output=True, text=True, timeout=120)
    open(log, 'w').write(p.stdout + p.stderr)
    summary = [l.strip() for l in (p.stdout + p.stderr).splitlines() if 'Tests ' in l or l.strip().startswith(('✓', '×'))]
    return p.returncode, summary
print('head', vitest('/tmp/dec1170-review/kill/kill-head.log'))
for ident in sys.argv[1:]:
    _, path, old, new = MUT[ident]
    s = open(path).read()
    assert s.count(old) == 1, ident
    open(path, 'w').write(s.replace(old, new))
    try:
        print(ident, vitest(f'/tmp/dec1170-review/kill/kill-{ident}.log'))
    finally:
        subprocess.run(['git', 'checkout', '--', path], check=True)
