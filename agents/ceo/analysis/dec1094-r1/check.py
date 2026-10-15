"""Route A file check for fix round 1 of PR #42 (DEC-1094, review DEC-1117).

Usage: python3 check.py <tree root>
Prints the blob id of each of the pull request's four files in the tree, the
expected id, and ALL EQUAL or NOT EQUAL at the end."""
import pathlib, subprocess, sys

EXPECTED = {
    'web/src/components/organisms/Shopping.tsx': '6f915484',
    'web/src/__tests__/components/Shopping.test.tsx': 'baaeae05',
    'web/tests/dec1083-shop-import-keyboard.spec.ts': '127a559e',
    'web/tests/dec942-owned-quota.spec.ts': '6d82efa8',
}
root = pathlib.Path(sys.argv[1])
ok = True
for path, want in EXPECTED.items():
    f = root / path
    got = subprocess.run(['git', 'hash-object', str(f)], capture_output=True, text=True).stdout[:8] if f.exists() else 'missing'
    same = got == want
    ok &= same
    print(f'{path}\t{got}\texpected {want}\t{"EQUAL" if same else "DIFFERENT"}')
print('ALL EQUAL' if ok else 'NOT EQUAL')
