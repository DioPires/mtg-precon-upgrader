"""DEC-1179 gate before the visibility switch (run 11ded5e2, board answer ceo_public).

Usage: python3 -I gate.py <delta_scan.log>
Exit 0 only if delta_scan.sh found nothing but the one reviewed false positive:
gitleaks generic-api-key on agents/ceo/analysis/dec1179-ceo/post.py:85 in 1433536
(the card's idempotency label, 29 characters, starts "dec1").
"""
import json
import re
import subprocess
import sys

ALLOW = {"1433536d7357c84fdc236641580308e4c8859717:agents/ceo/analysis/dec1179-ceo/post.py:generic-api-key:85"}
HERE = "/Users/dpires/Documents/Personal/code/mtg-precon-upgrader/agents/ceo/analysis/dec1179-ceo"
log = open(sys.argv[1]).read()
print(log, end="")
fail = []
m = re.search(r"^folder: (\S+)$", log, re.M)
if not m:
    sys.exit("GATE: FAIL (no folder line; the scan did not finish)")
O = m.group(1)
if "VERDICT: CLEAN" not in log:
    try:
        leaks = json.load(open(O + "/gitleaks.json"))
    except FileNotFoundError:
        leaks = []
    other = [e["Fingerprint"] for e in leaks if e["Fingerprint"] not in ALLOW]
    if other:
        fail.append(f"{len(other)} gitleaks finding(s) outside the reviewed one")
    for line in re.findall(r"^patterns in .*: (\d+)$", log, re.M):
        if line != "0":
            fail.append("a pattern hit")
    if re.search(r"^merge \S+ resolves .*: [1-9]\d* hits$", log, re.M):
        fail.append("a hit in a merge resolution")
    if json.load(open(O + "/gitleaks-gh.json")):
        fail.append("a gitleaks hit in the GitHub texts")
if "patterns in github texts: 0" not in log:
    fail.append("the GitHub text count is missing or not 0")
d = subprocess.run(["python3", "-I", HERE + "/delta_blobs.py", O.rsplit("/", 1)[0] + "/delta.git",
                    O + "/custom-delta.json"], capture_output=True, text=True)
print(d.stdout, end="")
if d.returncode != 0 or "\nfindings 0\n" not in "\n" + d.stdout:
    fail.append("custom rules: findings or an error")
fp = subprocess.run(["gh", "api", "repos/DioPires/mtg-precon-upgrader/activity?per_page=100&activity_type=force_push",
                     "--jq", '.[] | select(.timestamp >= "2026-10-16T10:28:00Z") | .ref'],
                    capture_output=True, text=True)
if fp.returncode != 0 or fp.stdout.strip():
    fail.append(f"force push since 10:28Z or the Activity API failed: {fp.stdout.strip()!r} rc={fp.returncode}")
if fail:
    sys.exit("GATE: FAIL: " + "; ".join(fail))
print("GATE: PASS (only the reviewed false positive, if any)")
