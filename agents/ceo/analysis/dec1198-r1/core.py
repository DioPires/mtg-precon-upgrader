"""Fix round 1 of PR #81 (DEC-1191): the CEO's file check at the hand-back (CEO run 15bb14f0, 2026-10-17).

Usage: uv run --no-project python -I core.py <repo> <ref>      (run `git fetch origin` first)

Checks the tree of <ref> (the pushed head) against this kit:
  scripts/auto_tag_roles.py, tests/test_auto_tag_roles.py: the syntax trees with every docstring removed equal
      expected/ (compare.py's rule: comments, docstrings, blank lines and wrapping are free).
  data/commanders/{anvil-chorus,stampede-acres}/candidates.json: equal expected/ as JSON with "generated_at" removed.
  every other path: the blob of `git merge-tree --write-tree <merge-base of ref and origin/main> 699cb7e`, so a merge
      of origin/main by the round is allowed and any other change reads CHANGED.
Prints one line for each checked path and ALL EQUAL or NOT EQUAL; exits 0 on ALL EQUAL.
"""
import ast
import hashlib
import json
import subprocess
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parent
repo, ref = sys.argv[1], sys.argv[2]
HEAD = "699cb7e04a89"
PY = ["scripts/auto_tag_roles.py", "tests/test_auto_tag_roles.py"]
POOLS = [f"data/commanders/{d}/candidates.json" for d in ("anvil-chorus", "stampede-acres")]


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
    a, b = stripped((KIT / "expected" / path).read_text()), stripped(got)
    same = a == b
    ok &= same
    print(f"{'EQUAL     ' if same else 'DIFFERENT '} {path}  {hashlib.sha256(b.encode()).hexdigest()[:16]}")
for path in POOLS:
    got = show(ref, path)
    if got is None:
        print(f"MISSING    {path}")
        ok = False
        continue
    a, b = json.loads((KIT / "expected" / path).read_text()), json.loads(got)
    a.pop("generated_at", None)
    b.pop("generated_at", None)
    same = a == b
    ok &= same
    print(f"{'EQUAL     ' if same else 'DIFFERENT '} {path}")

base = git("merge-base", ref, "origin/main").strip()
want = ls_tree(git("merge-tree", "--write-tree", base, HEAD).split()[0])
have = ls_tree(ref)
others = sorted((set(want) | set(have)) - set(PY) - set(POOLS))
changed = [p for p in others if want.get(p) != have.get(p)]
for p in changed:
    print(f"CHANGED    {p}")
ok &= not changed
print(f"other paths: {len(others)} checked against merge-tree({base[:7]}, {HEAD[:7]}), {len(changed)} changed")
print("ALL EQUAL" if ok else "NOT EQUAL")
sys.exit(0 if ok else 1)
