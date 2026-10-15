"""DEC-1139: run a kill (or evidence) file on the head and on named mutants.
The file is copied into the tree for the run and removed after it."""
import os, re, shutil, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mutants import MUTANTS, TREE, WEB, LOGS, ENV, SRC, apply, restore, git, strip

src_file, tag, ids = sys.argv[1], sys.argv[2], sys.argv[3:]
name = os.path.basename(src_file)
dest = os.path.join(WEB, 'src/__tests__/components', name)
by_id = {m[0]: m for m in MUTANTS}
for mid in ['head', *ids]:
    if git('status', '--porcelain').stdout.strip():
        sys.exit('tree not clean before ' + mid)
    if mid != 'head':
        apply(by_id[mid])
    diff = git('diff', '--', SRC).stdout
    shutil.copy(src_file, dest)
    cmd = ['npx', 'vitest', 'run', 'src/__tests__/components/' + name]
    p = subprocess.run(cmd, cwd=WEB, env=ENV, capture_output=True, text=True)
    os.remove(dest)
    restore()
    out = strip(p.stdout + p.stderr)
    log = f'{LOGS}/item3-{tag}-{mid}.log'
    with open(log, 'w') as f:
        f.write(f'# {tag} on {mid}\n# command: {" ".join(cmd)}\n# exit {p.returncode}\n{diff}\n{out}')
    count = [l.strip() for l in out.splitlines() if re.match(r'\s*Tests\s', l)]
    texts = [l.strip() for l in out.splitlines() if re.match(r'\s*E\d (message|bar)=', l)]
    print(mid, 'exit', p.returncode, ' / '.join(count), log, flush=True)
    for t in texts:
        print('   ', t)
