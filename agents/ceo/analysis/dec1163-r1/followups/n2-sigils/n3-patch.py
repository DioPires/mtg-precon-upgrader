# DEC-1163 N3 trial: the import message's sigils are hidden from the accessibility tree.
P = '/Users/dpires/Documents/Personal/code/mtg-precon-upgrader/wt-dec1163-review/web/src/components/organisms/Shopping.tsx'
s = open(P).read()
for sig in ['◆', '⚠']:
    old = f'              <span className="gv1-mono-xs">{sig}</span>\n'
    assert s.count(old) == 1
    s = s.replace(old, f'              <span className="gv1-mono-xs" aria-hidden="true">{sig}</span>\n')
open(P, 'w').write(s)
print('applied')
