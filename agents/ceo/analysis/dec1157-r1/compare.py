"""DEC-1078 fix round 1, route A file check (CEO, 2026-10-15; copied from dec1112-r1).

Usage: compare.py <expected.py> <actual.py>

Compares the two files' syntax trees with every docstring removed. Comments,
docstrings, blank lines and line wrapping are free; any change to the code
(names, calls, values, strings that are not docstrings) reads DIFFERENT.
Prints a 16-character digest of each side and EQUAL or DIFFERENT; exits 0
on EQUAL, 1 on DIFFERENT, 2 when a file is missing.
"""
import ast
import hashlib
import sys
from pathlib import Path


def stripped(path: Path) -> str:
    tree = ast.parse(path.read_text(), filename=str(path))
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if (isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
                and body and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str)):
            node.body = body[1:] or [ast.Pass()]
    return ast.dump(tree, include_attributes=False)


def main() -> int:
    paths = [Path(p) for p in sys.argv[1:3]]
    for p in paths:
        if not p.is_file():
            print(f"MISSING {p}")
            return 2
    dumps = [stripped(p) for p in paths]
    for p, d in zip(paths, dumps):
        print(f"{hashlib.sha256(d.encode()).hexdigest()[:16]}  {p}")
    print("EQUAL" if dumps[0] == dumps[1] else "DIFFERENT")
    return 0 if dumps[0] == dumps[1] else 1


if __name__ == "__main__":
    sys.exit(main())
