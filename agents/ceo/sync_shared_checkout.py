#!/usr/bin/env python3
"""Move the shared checkout's `main` to `origin/main` and keep every local edit (DEC-1216).

Run it in the shared mtg-precon-upgrader checkout as a run's last git step:

    python3 -I agents/ceo/sync_shared_checkout.py [--dry-run] [--drop-local-commits]

`git pull` and `git merge --ff-only` refuse when a file that `origin/main` adds is
already on disk untracked, even with the same bytes. `git reset --hard` deletes a
sibling run's unpushed edits. So the script does the fast-forward file by file:

1. It runs `git fetch origin`. It stops when `HEAD` holds commits that
   `origin/main` lacks, unless `--drop-local-commits` is given; then it keeps the
   old `HEAD` as branch `backup/shared-main-<UTC time>`.
2. For each path that differs between `HEAD` and `origin/main`:
   - the file on disk has `origin/main`'s bytes: nothing to do;
   - the file on disk has `HEAD`'s bytes, or is absent in both: it writes
     `origin/main`'s version, or deletes the file when `origin/main` has none;
   - any other file is a local edit: the script keeps it and lists it.
3. It runs `git reset --mixed origin/main`, which moves `main` and the index only.

It prints the counts and each kept file. Exit code 0 means synced, 2 means it
stopped before any write.
"""
import hashlib
import os
import subprocess
import sys
import time

TARGET = "origin/main"


def git(*args, inp=None):
    res = subprocess.run(["git", *args], input=inp, capture_output=True)
    if res.returncode != 0:
        sys.exit(f"git {' '.join(args)} failed: {res.stderr.decode().strip()}")
    return res.stdout


def tree(rev):
    """Map path -> (mode, blob id) for every blob in `rev`."""
    out = {}
    for rec in git("ls-tree", "-r", "-z", rev).split(b"\0"):
        if not rec:
            continue
        meta, path = rec.split(b"\t", 1)
        mode, kind, sha = meta.decode().split()
        if kind == "blob":
            out[path.decode()] = (mode, sha)
    return out


def disk_blob(path):
    """Blob id of the file on disk (git's hash, no filters), or None when absent."""
    if os.path.islink(path):
        data = os.readlink(path).encode()
    elif os.path.isfile(path):
        with open(path, "rb") as f:
            data = f.read()
    else:
        return None
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def main():
    dry = "--dry-run" in sys.argv
    drop = "--drop-local-commits" in sys.argv
    os.chdir(git("rev-parse", "--show-toplevel").decode().strip())
    git("fetch", "-q", "origin")
    head = git("rev-parse", "HEAD").decode().strip()
    new = git("rev-parse", TARGET).decode().strip()
    local = git("rev-list", f"{new}..{head}").decode().split()
    if local and not drop:
        print(f"STOP: HEAD holds {len(local)} commit(s) that {TARGET} lacks:")
        print(git("log", "--oneline", f"{new}..{head}").decode().rstrip())
        print("Push their content first, then run again with --drop-local-commits.")
        sys.exit(2)
    old_t, new_t = tree(head), tree(new)
    changed = sorted(p for p in set(old_t) | set(new_t) if old_t.get(p) != new_t.get(p))
    write, delete, kept, same = [], [], [], 0
    for p in changed:
        o, n = old_t.get(p), new_t.get(p)
        w = disk_blob(p)
        if (n and w == n[1] and (not o or o[0] == n[0] or w != o[1])) or (not n and w is None):
            same += 1
        elif w == (o[1] if o else None):
            (write if n else delete).append(p)
        else:
            kept.append(p)
    print(f"HEAD {head[:8]} -> {TARGET} {new[:8]}: {len(changed)} paths differ")
    print(f"  already on disk: {same}, to write: {len(write)}, to delete: {len(delete)}, kept (local edit): {len(kept)}")
    for p in kept:
        print(f"  kept: {p}")
    if dry:
        print("dry run: nothing written")
        return
    if local:
        name = "backup/shared-main-" + time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        git("branch", name, head)
        print(f"old HEAD kept as branch {name}")
    for i in range(0, len(write), 500):
        git("checkout", new, "--pathspec-from-file=-", "--pathspec-file-nul",
            inp=b"\0".join(p.encode() for p in write[i:i + 500]))
    for p in delete:
        os.remove(p)
        d = os.path.dirname(p)
        while d and not os.listdir(d):
            os.rmdir(d)
            d = os.path.dirname(d)
    git("reset", "-q", "--mixed", new)
    status = git("status", "--short").decode().splitlines()
    print(f"main is now {new[:8]}; git status --short lists {len(status)} line(s)")


if __name__ == "__main__":
    main()
