"""DEC-1112 B7, fix round 2 of PR #32: the file check at the hand-back (route A).

Usage: uv run python check_bump.py <repo> <head> [<pr-head-before-the-round>]

The round merges origin/main into the branch and bumps the loader's prefix by one.
This script reads the head against the merge base of <head> and origin/main:

1. Every path except the two below equals `git merge-tree --write-tree <base> <old>`,
   where <old> is the reviewed head (default f1a0c73).
2. web/src/data/loader.ts equals the base's file with `vN:` turned into `vN+1:` on the
   STORAGE_PREFIX line, once lines that hold only a `//` comment and blank lines are
   dropped. One added comment line holds `vN -> vN+1` and `DEC-1079`.
3. web/src/__tests__/data/loaderEnvelope.test.ts equals the base's file with each
   `vN` of the prefix case turned into `vN+1`, under the same normalisation.

It prints one line for each check and ALL EQUAL, or the first difference.
"""

import re
import subprocess
import sys

LOADER = "web/src/data/loader.ts"
TEST = "web/src/__tests__/data/loaderEnvelope.test.ts"


def git(repo, *args):
    return subprocess.run(["git", "-C", repo, *args], check=True, capture_output=True, text=True).stdout


def code_lines(text):
    return [line.rstrip() for line in text.splitlines() if line.strip() and not line.strip().startswith("//")]


def main(repo, head, old="f1a0c732f497a3c830416c66b0b27637b9c3d705"):
    base = git(repo, "merge-base", head, "origin/main").strip()
    expected_tree = git(repo, "merge-tree", "--write-tree", base, old).splitlines()[0]
    others = sorted(set(git(repo, "diff", "--name-only", expected_tree, head).split()) - {LOADER, TEST})
    print(f"base {base[:7]}, merge-tree of base and {old[:7]}: {expected_tree[:8]}")
    print(f"paths other than the two that differ from it: {others or 'none'}")
    ok = not others

    loader_base = git(repo, "show", f"{base}:{LOADER}")
    found = re.findall(r"^const STORAGE_PREFIX = 'gv1-deck-data-v(\d+):';$", loader_base, re.M)
    assert len(found) == 1, found
    n = int(found[0])
    loader_expected = loader_base.replace(f"'gv1-deck-data-v{n}:'", f"'gv1-deck-data-v{n + 1}:'")
    assert loader_expected.count(f"v{n + 1}:") == 1
    loader_head = git(repo, "show", f"{head}:{LOADER}")
    same = code_lines(loader_head) == code_lines(loader_expected)
    added = [l for l in loader_head.splitlines() if l.strip().startswith("//") and l not in loader_base.splitlines()]
    named = any(f"v{n} -> v{n + 1}" in l for l in added) and any("DEC-1079" in l for l in added)
    print(f"{LOADER}: prefix v{n} -> v{n + 1}: {'EQUAL' if same else 'DIFFERENT'}; "
          f"{len(added)} added comment lines, bump named with DEC-1079: {named}")
    ok = ok and same and named

    test_base = git(repo, "show", f"{base}:{TEST}")
    test_expected = test_base.replace(f"v{n}", f"v{n + 1}")
    test_head = git(repo, "show", f"{head}:{TEST}")
    same = test_base.count(f"v{n}") == 2 and code_lines(test_head) == code_lines(test_expected)
    print(f"{TEST}: base holds v{n} {test_base.count(f'v{n}')} times (2 expected): {'EQUAL' if same else 'DIFFERENT'}")
    ok = ok and same

    if not same or not ok:
        for name, h, e in ((LOADER, loader_head, loader_expected), (TEST, test_head, test_expected)):
            for a, b in zip(code_lines(h), code_lines(e)):
                if a != b:
                    print(f"  first difference in {name}:\n    head:     {a}\n    expected: {b}")
                    break
    print("ALL EQUAL" if ok else "NOT EQUAL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
