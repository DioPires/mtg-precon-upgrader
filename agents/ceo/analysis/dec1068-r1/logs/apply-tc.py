# Apply one of the reviewer's mutants (/tmp/dec1068-review/mutants/mutants.json) to the scratch clone.
import json, sys
TREE = '/tmp/dec1097-ceo/tc/web/src/components/organisms/Apothecary.tsx'
ORIG = '/tmp/dec1068-review/mutants/Apothecary.orig.tsx'
muts = {m[0]: m for m in json.load(open('/tmp/dec1068-review/mutants/mutants.json'))}
if sys.argv[1] == 'restore':
    open(TREE, 'w').write(open(ORIG).read()); print('restored'); sys.exit(0)
mid, line, old, new = muts[sys.argv[1]]
lines = open(ORIG).read().split('\n')
src = lines[line - 1]
assert src.count(old) == 1, (mid, line, src)
lines[line - 1] = src.replace(old, new)
open(TREE, 'w').write('\n'.join(lines))
print(f'{mid} L{line}: {src.strip()}  ->  {lines[line-1].strip()}')
