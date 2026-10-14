"""Mutant runner for the DEC-1094 review (DEC-1117). Applies one mutant to
Shopping.tsx, runs the given command, restores the file and checks its blob id."""
import subprocess, sys, pathlib

WEB = pathlib.Path(sys.argv[1])
LOGDIR = pathlib.Path(sys.argv[2])
WHICH = sys.argv[3].split(',')
MODE = sys.argv[4]  # unit | specs | <space-separated playwright filters>
SRC = WEB / 'src/components/organisms/Shopping.tsx'
BLOB = '6f915484'

L = "      const loadedCards = [...merged.values()].reduce((s, q) => s + q, 0);"
F = "      const fileCards = [...parsed.values()].reduce((s, q) => s + q, 0);"
MUTANTS = {
    'M1': (L, L.replace('merged.values', 'parsed.values')),
    'M2': (L, L.replace('merged.values', 'owned.values')),
    'M3': (F, F.replace('parsed.values', 'merged.values')),
    'M4': ('`Added ${parsed.size}', '`Added ${merged.size}'),
    'M5': ("cards loaded. `\n          + 'To replace the list, use Clear owned first.',", "cards loaded. `,"),
    'M6': ('`Added ${parsed.size}', '`Imported ${parsed.size}'),
    'M7': ('(${fileCards} total)', '(${loadedCards} total)'),
    'M8': ('${loadedCards} cards loaded. `', '${fileCards} cards loaded. `'),
    'M9': ('cards loaded. `', 'cards loaded.`'),
    'M10': ('ok: true,\n        text: `Added', 'ok: false,\n        text: `Added'),
    'M11': ("use Clear owned first.'", "clear owned first.'"),
    'M12': (L, L.replace(', 0);', ', 1);')),
}

def blob():
    return subprocess.run(['git', 'hash-object', str(SRC)], capture_output=True, text=True, check=True).stdout[:8]

assert blob() == BLOB, blob()
orig = SRC.read_text()
for m in WHICH:
    a, b = MUTANTS[m]
    assert orig.count(a) == 1, (m, orig.count(a))
    SRC.write_text(orig.replace(a, b))
    if MODE == 'unit':
        cmd = ['npx', 'vitest', 'run', 'src/__tests__/components/Shopping.test.tsx']
    else:
        specs = 'dec1083 dec942 dec1019 dec181 dec184 smoke' if MODE == 'specs' else MODE
        cmd = ['npx', 'playwright', 'test', *specs.split(), '--workers', '3', '--reporter=line']
    log = LOGDIR / f'{m}-{MODE.replace(" ", "_")}.log'
    try:
        with open(log, 'w') as fh:
            rc = subprocess.run(cmd, cwd=WEB, stdout=fh, stderr=subprocess.STDOUT).returncode
    finally:
        SRC.write_text(orig)
    assert blob() == BLOB, ('restore failed', blob())
    tail = [ln for ln in log.read_text().splitlines() if any(k in ln for k in ('Tests ', 'passed', 'failed'))]
    print(f'{m}\t{"KILLED" if rc else "SURVIVED"}\trc={rc}\t{log}\t{" | ".join(t.strip() for t in tail[-3:])}', flush=True)
