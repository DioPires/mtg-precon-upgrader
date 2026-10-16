"""DEC-1157 fix round 1, route A file check (CEO, 2026-10-15).

Usage: uv run --no-project python -I check.py <repo> <ref>   (run `git fetch origin` first)

1. tests/test_generate_candidate_pool.py at <ref> against expected/tests/... (git blob 7523883a):
   the syntax trees with every docstring removed (compare.py, from dec1121-r1). Comments,
   docstrings, blank lines and wrapping may differ; code may not.
2. Every other path at <ref> keeps the blob that `git merge-tree --write-tree <base> f5eda73`
   gives, where <base> is `git merge-base <ref> origin/main`: the branch is the head, merged
   with main or not, plus the one test file. So scripts/generate_candidate_pool.py keeps
   the head's blob 5d1565da unless main changed it.
Prints ALL EQUAL (exit 0) or NOT EQUAL (exit 1).
"""
import hashlib
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from compare import stripped  # noqa: E402

repo, ref = sys.argv[1], sys.argv[2]
HEAD = "f5eda73a723b027d2ba2cdf0414bdb5296c09341"
PATH = "tests/test_generate_candidate_pool.py"
here = Path(__file__).resolve().parent


def git(*a):
    r = subprocess.run(["git", "-C", repo, *a], capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"git {' '.join(a)}: {r.stderr.strip()}")
    return r.stdout


def blobs(treeish):
    out = {}
    for line in git("ls-tree", "-r", treeish).splitlines():
        meta, path = line.split("\t", 1)
        out[path] = meta.split()[2]
    return out


def h(s):
    return hashlib.sha256(s.encode()).hexdigest()[:16]


ok = True
have = blobs(ref)
if PATH not in have:
    print(PATH, "MISSING at", ref)
    ok = False
else:
    tmp = here / ".got.py"
    tmp.write_text(git("show", f"{ref}:{PATH}"))
    try:
        exp, got = stripped(here / "expected" / PATH), stripped(tmp)
    finally:
        tmp.unlink()
    same = exp == got
    ok &= same
    print(PATH, h(exp), h(got), "EQUAL" if same else "DIFFERENT")

base = git("merge-base", ref, "origin/main").strip()
want = blobs(git("merge-tree", "--write-tree", base, HEAD).strip())
others = sorted((set(want) | set(have)) - {PATH})
changed = [p for p in others if want.get(p) != have.get(p)]
for p in changed:
    print(p, (want.get(p) or "missing")[:8], (have.get(p) or "missing")[:8], "CHANGED")
print(f"base {base[:7]}: {len(others)} other paths", "keep their blobs" if not changed else f"{len(changed)} CHANGED")
ok &= not changed
print("ALL EQUAL" if ok else "NOT EQUAL")
sys.exit(0 if ok else 1)
