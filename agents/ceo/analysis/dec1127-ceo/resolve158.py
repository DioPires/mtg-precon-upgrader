# Run in wt-dec1127 after `git merge --no-ff --no-edit origin/main` stops on loader.ts.
import subprocess, sys
REF = sys.argv[1] if len(sys.argv)>1 else 'origin/main'
def sh(*a): return subprocess.run(a, check=True, capture_output=True, text=True).stdout
L='web/src/data/loader.ts'; T='web/src/__tests__/data/loaderEnvelope.test.ts'
main_loader = sh('git','show',f'{REF}:{L}')
assert main_loader.count("// v156 -> v157 (DEC-1079 2026-10-15)")==1
old = "const STORAGE_PREFIX = 'gv1-deck-data-v157:';\n"
assert main_loader.count(old)==1
new = ("// v157 -> v158 (DEC-1127 2026-10-15): slivers and stampede-acres winConditions and\n"
       "// witherbloom-the-balancer synergies gained `title` (8 renamed from `name`, 2 new).\n"
       "// deck.json is persisted, so an older copy keeps the empty titles until its TTL ends.\n"
       "const STORAGE_PREFIX = 'gv1-deck-data-v158:';\n")
open(L,'w').write(main_loader.replace(old,new))
t = open(T).read()
assert '<<<<<<<' not in t and t.count('v157')==2 and 'v156' not in t, 'test file state'
open(T,'w').write(t.replace('v157','v158'))
sh('git','add',L,T)
print(sh('git','status','--short'))
