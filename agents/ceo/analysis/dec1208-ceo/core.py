"""Fix round 1 of PR #84 (DEC-1197): the CEO's file check at the hand-back (CEO run b622726c, 2026-10-18).

Usage: uv run --no-project python -I core.py <repo> <ref>      (run `git fetch origin` first)

Checks the tree of <ref> (the pushed head) against this kit:
  tests/test_auto_tag_roles.py: the syntax tree with every docstring removed equals expected/ (comments,
      docstrings, blank lines and wrapping are free). It also prints whether the bytes are equal.
  every other path: the blob of `git merge-tree --write-tree <merge-base of ref and origin/main> 4985520`, so a merge
      of origin/main by the round is allowed and any other change reads CHANGED.
Prints one line for each checked path and ALL EQUAL or NOT EQUAL; exits 0 on ALL EQUAL.
"""
import ast
import hashlib
import subprocess
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parent
repo, ref = sys.argv[1], sys.argv[2]
HEAD = "4985520c8c03"
PY = ["tests/test_auto_tag_roles.py"]
EXPECTED = {"tests/test_auto_tag_roles.py": KIT / "expected" / "test_auto_tag_roles.py"}


def git(*args: str) -> str:
    return subprocess.run(["git", "-C", repo, *args], check=True, capture_output=True, text=True).stdout


def show(rev: str, path: str) -> str | None:
    r = subprocess.run(["git", "-C", repo, "show", f"{rev}:{path}"], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def stripped(src: str) -> str:
    tree = ast.parse(src)
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if (isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
                and body and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str)):
            node.body = body[1:] or [ast.Pass()]
    return ast.dump(tree, include_attributes=False)


def ls_tree(tree: str) -> dict[str, str]:
    out = {}
    for line in git("ls-tree", "-r", tree).splitlines():
        meta, path = line.split("\t", 1)
        out[path] = meta.split()[2]
    return out


ok = True
for path in PY:
    got = show(ref, path)
    if got is None:
        print(f"MISSING    {path}")
        ok = False
        continue
    want_src = EXPECTED[path].read_text()
    a, b = stripped(want_src), stripped(got)
    same = a == b
    ok &= same
    print(f"{'EQUAL     ' if same else 'DIFFERENT '} {path}  ast {hashlib.sha256(b.encode()).hexdigest()[:16]}"
          f"  bytes {'equal' if got == want_src else 'differ'}")

base = git("merge-base", ref, "origin/main").strip()
want = ls_tree(git("merge-tree", "--write-tree", base, HEAD).split()[0])
have = ls_tree(ref)
others = sorted((set(want) | set(have)) - set(PY))
changed = [p for p in others if want.get(p) != have.get(p)]
for p in changed:
    print(f"CHANGED    {p}")
ok &= not changed
print(f"other paths: {len(others)} checked against merge-tree({base[:7]}, {HEAD[:7]}), {len(changed)} changed")
print("ALL EQUAL" if ok else "NOT EQUAL")
sys.exit(0 if ok else 1)
