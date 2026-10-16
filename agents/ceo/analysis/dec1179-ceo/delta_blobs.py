"""DEC-1179: the engineer's custom rules (scan_blobs.py) on the delta only.

Usage: python3 -I delta_blobs.py <delta.git> <out.json>
Scans each blob and commit message that refs/now/* reach and that neither the
engineer's mirror (10:28Z) nor refs/new/* (10:44Z delta) reach. Prints counts
and, per finding, rule, path, first 4 characters and length only.
"""
import json
import subprocess
import sys

DELTA, OUT = sys.argv[1], sys.argv[2]
MIRROR = ("/Users/dpires/.paperclip/instances/default/workspaces/"
          "ddb8e4ee-9ec6-45ae-81b7-144c85a9b26e/dec-scan/mirror.git")

src = open(MIRROR.rsplit("/", 1)[0] + "/scan_blobs.py").read()
src = src[:src.index("def main():")].replace("MIRROR, OUT = sys.argv[1], sys.argv[2]", "")
ns = {}
exec(compile(src, "scan_blobs.py", "exec"), ns)
scan = ns["scan"]


def git(repo, *args, data=None):
    return subprocess.run(["git", "-C", repo, *args], input=data, capture_output=True, check=True).stdout


old = set(git(MIRROR, "for-each-ref", "--format=%(objectname)").decode().split())
old |= set(git(DELTA, "for-each-ref", "--format=%(objectname)", "refs/new").decode().split())
new = sorted(set(git(DELTA, "for-each-ref", "--format=%(objectname)", "refs/now").decode().split()))
objs = git(DELTA, "rev-list", "--objects", *new, "--not", *sorted(old)).decode().splitlines()
path_of = {}
for line in objs:
    sha, _, path = line.partition(" ")
    path_of.setdefault(sha, path)
types = git(DELTA, "cat-file", "--batch-check=%(objectname) %(objecttype)",
            data="\n".join(path_of).encode()).decode().split("\n")
blobs = [l.split()[0] for l in types if l.endswith(" blob")]
commits = [l.split()[0] for l in types if l.endswith(" commit")]

findings, binary, text = [], 0, 0
for sha in blobs:
    buf = git(DELTA, "cat-file", "blob", sha)
    if b"\0" in buf[:8000]:
        binary += 1
        continue
    text += len(buf)
    findings += scan(buf, {"kind": "blob", "blob": sha, "path": path_of[sha]})
for sha in commits:
    buf = git(DELTA, "cat-file", "commit", sha)
    msg = buf.split(b"\n\n", 1)[1] if b"\n\n" in buf else b""
    findings += scan(msg, {"kind": "commit-message", "commit": sha})

json.dump({"commits": len(commits), "blobs": len(blobs), "binary": binary, "text_bytes": text,
           "findings": findings}, open(OUT, "w"), indent=1)
print(f"commits {len(commits)}, blobs {len(blobs)} (binary {binary}), text bytes {text}")
print("findings", len(findings))
for f in findings:
    v = f["value"]
    print(f'  {f["rule"]} {f.get("path", f.get("commit", "")[:7])}:{f["line"]} '
          f'key={f["key"]!r} first4={v["first4"]!r} len={v["len"]} uuid={v["is_uuid"]}')
