# DEC-1088 route A file check (CEO). Drops blank lines and lines that hold
# only a // comment, then compares the rest. Prints one hash for each file
# and EQUAL or DIFFERENT. A trailing comment on a code line counts as code.
import hashlib, sys

def core(path):
    keep = []
    for line in open(path, encoding='utf-8').read().splitlines():
        s = line.strip()
        if not s or s.startswith('//'):
            continue
        keep.append(line.rstrip())
    return '\n'.join(keep) + '\n'

a, b = core(sys.argv[1]), core(sys.argv[2])
ha = hashlib.sha256(a.encode()).hexdigest()[:16]
hb = hashlib.sha256(b.encode()).hexdigest()[:16]
print(ha, sys.argv[1])
print(hb, sys.argv[2])
print('EQUAL' if a == b else 'DIFFERENT')
sys.exit(0 if a == b else 1)
